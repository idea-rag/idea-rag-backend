from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import requests
import os
import uvicorn
from pymongo.asynchronous.database import AsyncDatabase
import time

from database import lifespan, get_db
from auth import AuthService, get_current_user, get_auth_service
from exceptions import (
    BaseHTTPException,
    UserAlreadyExistsException,
    UserNotFoundException,
    InvalidPasswordException,
    SubjectNotFoundException,
    MissingRequiredFieldException,
    FileNotFoundException,
)
from logger import create_logger
from models import (
    RegisterDTO,
    LoginDTO,
    ScopeModifyDTO,
    FocusStartDTO,
    FocusFeedbackDTO,
    NeurofeedbackSendDTO,
    FindDogImageLoadDTO,
    ScheduleDTO,
    AIResponseDTO
)

load_dotenv()

app = FastAPI(name="RAG API", lifespan=lifespan)
logger = create_logger("app")


@app.exception_handler(BaseHTTPException)
async def unknown_http_exception_handler(_request: Request, exc: BaseHTTPException):
    logger.warning(f"Unknown HTTP Exception: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}},
    )


@app.exception_handler(Exception)
async def general_exception_handler(_request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
            "details": {"error": str(exc)},
        },
    )


@app.get("/")
def main() -> dict:
    return {"message": "hello world!"}


@app.post("/register")
async def register(
    data: RegisterDTO,
    db: AsyncDatabase = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    users_collection = db["user_db"]

    if not data.userID or not data.password:
        logger.warning(
            f"Registration failed: Missing required fields for userID: {data.userID}"
        )
        raise MissingRequiredFieldException(["userID", "password"])

    subjects = [
        {"name": n, "publish": p, "workbook": w, "scope": s}
        for n, p, w, s in zip(
            data.subject_name,
            data.subject_publish,
            data.subject_workbook,
            data.subject_scope,
        )
    ]

    hashed_password = auth_service.hash_password(data.password)

    data = {
        "userID": data.userID,
        "name": data.name,
        "school": data.school,
        "gmail": data.gmail,
        "password": hashed_password,
        "grade": data.grade,
        "subjects": subjects,
    }

    existing_user = await users_collection.find_one({"userID": data.get("userID")})

    if existing_user:
        logger.warning(
            f"Registration failed: User already exists - userID: {data.userID}"
        )
        raise UserAlreadyExistsException(data.userID)

    await users_collection.insert_one(data)
    return {"message": f"User {data.get('userID')} signed up successfully!"}


@app.post("/login")
async def login(
    data: LoginDTO,
    db: AsyncDatabase = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    users_collection = db["user_db"]

    if not data.userID or not data.password:
        logger.warning(f"Login failed: Missing credentials for userID: {data.userID}")
        raise MissingRequiredFieldException(["userID", "password"])

    user = await users_collection.find_one({"userID": data.userID})

    if not user:
        logger.warning(f"Login failed: User not found - userID: {data.userID}")
        raise UserNotFoundException(data.userID)

    if not auth_service.verify_password(data.password, user.get("password")):
        logger.warning(f"Login failed: Invalid password for userID: {data.userID}")
        raise InvalidPasswordException()

    token = await auth_service.create_access_token(data.userID)
    return {
        "message": f"{data.userID} signed in successfully!",
        "access_token": token,
    }


@app.get("/userInfo")
async def get_user_info(
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_data = {
        "userID": current_user.get("userID"),
        "name": current_user.get("name"),
        "school": current_user.get("school"),
        "gmail": current_user.get("gmail"),
        "grade": current_user.get("grade"),
        "subjects": current_user.get("subjects", []),
    }
    return {"userInfo": user_data}


@app.post("/schedule-create")
async def create_schedule(
    data : ScheduleDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db)
):
    user_id = current_user.get("userID")
    schedule_collection = db["schedule"]

    schedule_data = {
        "userID": user_id,
        "when": data.when,
        "subjects": data.subjects,
    }
    await schedule_collection.insert_one(schedule_data)

    return {"message": "Schedule created successfully!"}


@app.post("/scope-modify")
async def modify_scope(
    data: ScopeModifyDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    users_collection = db["user_db"]
    subjects = current_user.get("subjects", [])
    for subject in subjects:
        if (
            subject["name"] == data.subject_name
            and subject["publish"] == data.subject_publish
            and subject["workbook"] == data.subject_workbook
        ):
            subject["scope"] = data.new_scope
            break
    else:
        logger.warning(
            f"Scope modification failed: Subject not found - userID: {user_id}, subject: {data.subject_name}"
        )
        raise SubjectNotFoundException(
            data.subject_name, data.subject_publish, data.subject_workbook
        )
    await users_collection.update_one(
        {"userID": user_id}, {"$set": {"subjects": subjects}}
    )
    return {"message": "Scope modified successfully!"}


@app.post("/focus-start")
async def focus_start(
    data: FocusStartDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    focus_collection = db["focus"]
    data = {
        "userID": user_id,
        "focusTime": data.focusTime,
        "measureTime": data.measureTime,
        "whenTime": data.whenTime,
        "whenDay": data.whenDay,
    }
    await focus_collection.insert_one(data)
    return {"message": "Focus started successfully!"}


@app.post("/focus-feedback")
async def focus_feedback(
    data: FocusFeedbackDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    focus_collection = db["focus"]
    if not data.focus_data:
        logger.warning(f"Focus feedback failed: Missing data for userID: {user_id}")
        raise MissingRequiredFieldException(["focus_data"])
    for i in data.focus_data:
        await focus_collection.insert_one(
            {
                "userID": user_id,
                "whenTime": data.whenTime,
                "focusTime": data.focus_data[i].get("focusTime", 0),
                "measureTime": data.focus_data[i].get("measureTime", 0),
            }
        )
    return {"message": "Focus feedback recorded successfully!"}


@app.post("/neurofeedback_send")
async def neurofeedback_send(
    data: NeurofeedbackSendDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    neurofeedback_collection = db["neurofeedback"]
    if not data.when:
        logger.warning(
            f"Neurofeedback failed: Missing when parameter for userID: {user_id}"
        )
        raise MissingRequiredFieldException(["when"])
    neurofeedback_data = {
        "userID": user_id,
        "when": data.when,
        "find_dog": data.find_dog,
        "select_square": data.select_square,
    }
    await neurofeedback_collection.insert_one(neurofeedback_data)
    return {"message": "Neurofeedback data sent successfully!"}


@app.get("/neurofeedback_load")
async def neurofeedback_load(
    current_user: dict = Depends(get_current_user), db: AsyncDatabase = Depends(get_db)
):
    user_id = current_user.get("userID")

    neurofeedback_collection = db["neurofeedback"]

    neurofeedback_data = neurofeedback_collection.find({"userID": user_id})
    data_list = []
    async for data in neurofeedback_data:
        data_list.append(
            {
                "when": data.get("when"),
                "find_dog": data.get("find_dog"),
                "select_square": data.get("select_square"),
            }
        )
    return {"neurofeedback_data": data_list}


@app.post("/find_dog_image_load")
def find_dog_image_load(data: FindDogImageLoadDTO):

    IMAGE_DIRECTORY = os.getenv("Find_Dog_Image_URL")
    UPLOAD_URL = os.getenv("UPLOAD_URL")

    if not os.path.isdir(IMAGE_DIRECTORY):
        logger.error(f"Image directory not found: {IMAGE_DIRECTORY}")
        raise FileNotFoundException(IMAGE_DIRECTORY)

    image_list = sorted(os.listdir(IMAGE_DIRECTORY))

    upload_results = []
    errors = []

    for num in data.number:
        if 0 <= num < len(image_list):
            filename = image_list[num]
            image_path = os.path.join(IMAGE_DIRECTORY, filename)

            try:
                with open(image_path, "rb") as image_file:
                    files = {"file": (filename, image_file, "image/jpeg")}

                    response = requests.post(UPLOAD_URL, files=files)
                    response.raise_for_status()

                    upload_results.append(response.json())

            except FileNotFoundError:
                error_msg = f"파일을 찾을 수 없습니다: {image_path}"
                logger.error(error_msg)
                errors.append({"number": num, "error": error_msg})
            except requests.exceptions.RequestException as e:
                error_msg = f"업로드 실패: {e}"
                logger.error(f"Upload failed for {filename}: {e}")
                errors.append({"number": num, "filename": filename, "error": error_msg})
        else:
            error_msg = f"이미지 번호가 범위를 벗어났습니다. (사용 가능 범위: 0-{len(image_list)-1})"
            logger.warning(f"Image number out of range: {num}")
            errors.append({"number": num, "error": error_msg})

    logger.info(
        f"Find dog image load completed. Successes: {len(upload_results)}, Errors: {len(errors)}"
    )
    return {"successes": upload_results, "errors": errors}

# @app.get("/AI")
# async def ai_response(
#     data : AIResponseDTO,
#     current_user: dict = Depends(get_current_user),
# ):
#     user_id = current_user.get("userID")
#
# 합치고 해야 될 듯



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
