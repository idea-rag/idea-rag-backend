from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from AI.SDM import SDM
import logging
import requests
import os
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from pymongo.asynchronous.database import AsyncDatabase

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
    ScheduleDTO
)
from AI.SDM import SDM
from AI.FFBM import FFBM

load_dotenv()

app = FastAPI(name="RAG API", lifespan=lifespan)
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)
logger = create_logger("app")

# SDM, FFBM 인스턴스 생성
sdm = SDM()
ffbm = FFBM()


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

    hashed_password = auth_service.hash_password(data.password)

    data = {
        "userID": data.userID,
        "name": data.name,
        "school": data.school,
        "grade": data.grade,
        "email": data.email,
        "password": hashed_password,
        "subject_name": data.subject_name,
        "subject_publish": data.subject_publish,
        "subject_BookList": data.subject_BookList,
        "Subject_Module": data.Subject_Module,
        "focus_Grade": data.focus_Grade,
        "WhatWeek": data.WhatWeek
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
        data: ScheduleDTO,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db)
):
    user_id = current_user.get("userID")
    schedule_collection = db["schedule"]

    # --- 데이터베이스 저장 로직 (기존과 동일) ---
    # Convert Pydantic model to dict
    schedule_data_to_db = {
        "userID": user_id,
        "when": data.when,
        "subjects": data.subjects,
        "goal": data.goal,
    }
    await schedule_collection.insert_one(schedule_data_to_db)
    # ---------------------------------------------

    # [수정 1] AI 모듈에 전달할 payload를 올바른 형식으로 재구성합니다.
    # 로그인된 사용자 정보에서 'grade'를 가져옵니다.
    grade = current_user.get("grade")
    if not grade:
        # 사용자의 학년 정보가 없는 경우 예외 처리
        raise HTTPException(status_code=400, detail="User grade information is missing.")

    # [수정 2] sdm.get_ai_schedule가 요구하는 형식에 맞게 payload를 생성합니다.
    payload_for_ai = {
        "user_id": user_id,
        "grade": grade,
        "subjects": data.subjects,  # API로 받은 subjects를 workbooks 키에 할당
        "goal": data.goal,
        "when": data.when
    }

    print(f"Sending to get_ai_schedule: {payload_for_ai}")  # Debug log

    # 수정된 payload로 AI 함수를 호출합니다.
    ai_schedule = sdm.get_ai_schedule(payload_for_ai)

    return {"message": "Schedule created successfully!", "ai_schedule": ai_schedule}


@app.post("/scope-modify")
async def modify_scope(
        data: ScopeModifyDTO,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db),
):
    try:
        # 1. Initialize SDM instance
        sdm = SDM()
        
        # 2. Get the original schedule from the request
        original_schedule = data.original_schedule
        if not isinstance(original_schedule, dict):
            raise HTTPException(
                status_code=400,
                detail="original_schedule must be a valid JSON object"
            )
        
        # 3. Prepare modification request
        modification_request = {
            "request": data.new_scope
        }
        
        # 4. Call SDM to modify the schedule
        logger.info(f"Modifying schedule for user {current_user.get('userID')}")
        modified_schedule = sdm.modify_ai_schedule(
            original_schedule=original_schedule,
            modification_request=modification_request
        )
        
        # 5. Check for errors in the response
        if "error" in modified_schedule:
            logger.error(f"SDM modification failed: {modified_schedule['error']}")
            raise HTTPException(
                status_code=400,
                detail=modified_schedule["error"]
            )
            
        # 6. Update user's schedule in the database
        user_id = current_user.get("userID")
        users_collection = db["user_db"]
        
        update_result = await users_collection.update_one(
            {"userID": user_id},
            {"$set": {"schedule": modified_schedule}}
        )
        
        if update_result.modified_count == 0:
            logger.warning(f"No documents were updated for user {user_id}")
            
        logger.info(f"Successfully updated schedule for user {user_id}")
        
        return {
            "success": True,
            "message": "Schedule modified successfully",
            "modified_schedule": modified_schedule
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
        
    except Exception as e:
        logger.error(f"Unexpected error in modify_scope: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request"
        )


@app.get("/focus-data")
async def get_focus_data(
        when_day: str,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    focus_collection = db["focus"]
    
    # 해당 날짜의 문서 조회
    focus_data = await focus_collection.find_one(
        {"userID": user_id, "whenDay": when_day},
        {"_id": 0}  # _id 필드 제외
    )
    
    if not focus_data:
        return {
            "message": "No data found for the specified date",
            "data": {
                "userID": user_id,
                "whenDay": when_day,
                "timeSlots": {},
                "totalMeasureTime": 0,
                "totalFocusTime": 0
            }
        }
    
    return {
        "message": "Focus data retrieved successfully",
        "data": focus_data
    }


@app.post("/focus-start")
async def focus_start(
        data: FocusStartDTO,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    focus_collection = db["focus"]
    
    # 기존 문서 조회
    existing_doc = await focus_collection.find_one({"userID": user_id, "whenDay": data.whenDay})
    
    # 시간대별 데이터 생성
    time_slot_data = {
        "measureTime": data.measureTime,
        "focusTime": data.focusTime
    }
    
    if existing_doc:
        # 기존 문서가 있으면 시간대별 데이터 업데이트
        update_data = {}
        update_data[f"timeSlots.{data.timeSlot}"] = time_slot_data
        
        await focus_collection.update_one(
            {"userID": user_id, "whenDay": data.whenDay},
            {
                "$set": update_data,
                "$inc": {
                    "totalMeasureTime": data.measureTime,
                    "totalFocusTime": data.focusTime
                }
            },
            upsert=True
        )
    else:
        # 새 문서 생성
        new_doc = {
            "userID": user_id,
            "whenDay": data.whenDay,
            "timeSlots": {
                data.timeSlot: time_slot_data
            },
            "totalMeasureTime": data.measureTime,
            "totalFocusTime": data.focusTime
        }
        await focus_collection.insert_one(new_doc)
    
    return {
        "message": "Focus data saved successfully!",
        "data": {
            "userID": user_id,
            "whenDay": data.whenDay,
            data.timeSlot: time_slot_data
        }
    }


@app.post("/focus-feedback")
async def focus_feedback(
        data: FocusFeedbackDTO,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db),
):
    user_id = current_user.get("userID")
    focus_collection = db["focus"]
    
    if not data.timeSlots:
        logger.warning(f"Focus feedback failed: Missing timeSlots for userID: {user_id}")
        raise MissingRequiredFieldException(["timeSlots"])

    # Prepare focus data for database and FFBM
    focus_data = {
        "whenDay": data.whenDay,
        "timeSlots": {},
        "totalMeasureTime": 0,
        "totalFocusTime": 0
    }

    # Process each time slot
    for time_slot, slot_data in data.timeSlots.items():
        measure_time = slot_data.get("measureTime", 0)
        focus_time = slot_data.get("focusTime", 0)
        
        # Save to database
        await focus_collection.insert_one({
            "userID": user_id,
            "whenDay": data.whenDay,
            "timeSlot": time_slot,
            "measureTime": measure_time,
            "focusTime": focus_time,
        })

        # Update focus data for FFBM
        focus_data["timeSlots"][time_slot] = {
            "measureTime": measure_time,
            "focusTime": focus_time
        }
        focus_data["totalMeasureTime"] += measure_time
        focus_data["totalFocusTime"] += focus_time

    # Get AI feedback with both study and focus data
    ai_feedback = ffbm.get_ai_feedback(
        study_data_payload=data.studyData,  # 프론트엔드에서 전달받은 studyData 전달
        focus_data_payload=focus_data
    )
    
    return {
        "message": "Focus feedback recorded successfully!", 
        "ai_feedback": ai_feedback
    }


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
            error_msg = f"이미지 번호가 범위를 벗어났습니다. (사용 가능 범위: 0-{len(image_list) - 1})"
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