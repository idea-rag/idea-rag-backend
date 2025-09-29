from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from AI.SDM import SDM
import logging
import requests
import os
import uvicorn
import json
from datetime import datetime

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
        "subject_book_list": data.subject_book_list,
        "Subject_Module": data.subject_module,
        "focus_Grade": data.focus_Grade,
        "WhatWeek": data.what_week
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


@app.post("/schedule-modify")
async def modify_schedule(
        data: dict,
        current_user: dict = Depends(get_current_user),
        db: AsyncDatabase = Depends(get_db),
):
    """
    기존 스케줄과 사용자 피드백을 받아 새로운 스케줄을 생성합니다.
    
    요청 데이터 형식:
    {
        "existing_schedule": {...},  # 기존 스케줄 데이터
        "feedback": "사용자 피드백 텍스트"  # 수정 요청사항
    }
    """
    try:
        user_id = current_user.get("userID")
        grade = current_user.get("grade")
        
        # 1. 필수 데이터 검증
        existing_schedule = data.get("existing_schedule")
        feedback = data.get("feedback", "")
        
        if not existing_schedule:
            raise HTTPException(
                status_code=400,
                detail="기존 스케줄 데이터(existing_schedule)가 필요합니다."
            )
        
        if not feedback.strip():
            raise HTTPException(
                status_code=400,
                detail="수정 요청사항(feedback)이 필요합니다."
            )
        
        # 2. 학생 데이터 구성
        student_data = {
            "user_id": user_id,
            "grade": grade,
            "name": current_user.get("name", ""),
            "school": current_user.get("school", "")
        }
        
        # 3. dict.json에서 문제집 데이터 로드
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dict_path = os.path.join(current_dir, 'dict.json')
            dict_path = os.path.normpath(dict_path)
            logger.info(f"dict.json 경로: {dict_path}")  # 디버깅용 로그 추가
            
            with open(dict_path, 'r', encoding='utf-8') as f:
                all_workbooks_data = json.load(f)
                
            logger.info(f"문제집 데이터 로드 완료: {len(all_workbooks_data)}개 항목")
                
        except FileNotFoundError:
            logger.error(f"dict.json 파일을 찾을 수 없습니다: {dict_path}")
            raise HTTPException(
                status_code=500,
                detail="문제집 데이터를 로드할 수 없습니다."
            )
        except json.JSONDecodeError as e:
            logger.error(f"dict.json 파싱 오류: {e}")
            raise HTTPException(
                status_code=500,
                detail="문제집 데이터 형식이 올바르지 않습니다."
            )
        
        # 4. 기존 스케줄에서 사용된 문제집 정보 추출
        relevant_workbooks = []
        try:
            # 기존 스케줄 구조 로깅 (디버깅용)
            logger.info(f"기존 스케줄 구조: {json.dumps(existing_schedule, ensure_ascii=False, indent=2)[:500]}...")
            
            # 사용 가능한 문제집 목록 로깅 (디버깅용)
            logger.info(f"사용 가능한 학년: {grade}의 문제집 목록:")
            available_workbooks = [f"{wb.get('publish')} - {wb.get('workbook')}" 
                                for wb in all_workbooks_data 
                                if wb.get('grade') == grade]
            logger.info("\n".join(available_workbooks))
            
            # 기존 스케줄에서 사용된 문제집들을 찾아서 관련 데이터 추출
            found_workbooks = set()  # 중복 제거를 위해 set 사용
            
            # existing_schedule을 순회하며 문제집 정보 수집
            def collect_workbooks(data):
                if isinstance(data, dict):
                    # 현재 레벨에서 publish와 workbook이 있는지 확인
                    if 'publish' in data and 'workbook' in data:
                        publish = data['publish']
                        workbook = data['workbook']
                        if publish and workbook:
                            found_workbooks.add((publish, workbook))
                    # 모든 값에 대해 재귀적으로 탐색
                    for value in data.values():
                        collect_workbooks(value)
                elif isinstance(data, list):
                    for item in data:
                        collect_workbooks(item)
            
            # 문제집 정보 수집 실행
            collect_workbooks(existing_schedule)
            
            # 찾은 문제집 정보 로깅
            logger.info(f"스케줄에서 찾은 문제집 정보: {found_workbooks}")
            
            # dict.json에서 해당하는 문제집 데이터 찾기
            for publish, workbook in found_workbooks:
                logger.info(f"\n찾고 있는 문제집 - 출판사: '{publish}', 문제집: '{workbook}', 학년: '{grade}'")
                
                # 정확히 일치하는 문제집 찾기
                found = False
                for db_entry in all_workbooks_data:
                    db_publish = db_entry.get('publish', '')
                    db_workbook = db_entry.get('workbook', '')
                    db_grade = db_entry.get('grade', '')
                    
                    if (db_grade == grade and 
                        db_publish == publish and 
                        db_workbook == workbook):
                        
                        logger.info(f"일치하는 문제집 찾음: {db_publish} - {db_workbook}")
                        if db_entry not in relevant_workbooks:
                            relevant_workbooks.append(db_entry)
                        found = True
                
                if not found:
                    logger.warning(f"일치하는 문제집을 찾지 못했습니다: {publish} - {workbook}")
            
            # 여전히 문제집을 찾지 못한 경우, 해당 학년의 모든 문제집을 사용
            if not relevant_workbooks:
                logger.warning(f"관련 문제집을 찾을 수 없어 해당 학년({grade})의 모든 문제집을 사용합니다.")
                relevant_workbooks = [wb for wb in all_workbooks_data if wb.get('grade') == grade]
        except Exception as e:
            logger.warning(f"기존 스케줄에서 문제집 정보 추출 중 오류: {e}")
            # 오류가 있어도 계속 진행하되, 모든 문제집 데이터를 사용
            relevant_workbooks = [wb for wb in all_workbooks_data if wb.get('grade') == grade]
        
        if not relevant_workbooks:
            logger.warning(f"관련 문제집을 찾을 수 없음. 해당 학년의 모든 문제집 사용: {grade}")
            # 해당 학년의 모든 문제집 데이터를 사용
            relevant_workbooks = [wb for wb in all_workbooks_data if wb.get('grade') == grade]
            
        if not relevant_workbooks:
            raise HTTPException(
                status_code=400,
                detail=f"해당 학년({grade})에 대한 문제집 데이터를 찾을 수 없습니다."
            )
        
        logger.info(f"관련 문제집 {len(relevant_workbooks)}개 발견")
        
        # 5. SDM을 사용하여 스케줄 수정
        logger.info(f"사용자 {user_id}의 스케줄 수정 시작")
        modified_schedule = sdm.modify_ai_schedule(
            student_data=student_data,
            relevant_workbooks=relevant_workbooks,
            existing_schedule=existing_schedule,
            feedback=feedback
        )
        
        # 6. 에러 체크
        if "error" in modified_schedule:
            logger.error(f"SDM 스케줄 수정 실패: {modified_schedule['error']}")
            raise HTTPException(
                status_code=400,
                detail=modified_schedule["error"]
            )
        
        # 7. 수정된 스케줄을 데이터베이스에 저장
        schedule_collection = db["schedule"]
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 기존 스케줄을 업데이트하거나 새로 삽입
        await schedule_collection.update_one(
            {"userID": user_id, "created_date": current_date},
            {"$set": {
                "modified_at": datetime.now(),
                "modified_schedule_data": modified_schedule,
                "original_schedule_data": existing_schedule,
                "feedback_applied": feedback,
                "modification_count": 1  # 추후 수정 횟수 추적을 위해
            }},
            upsert=True
        )
        
        logger.info(f"사용자 {user_id}의 스케줄 수정 완료")
        
        return {
            "success": True,
            "message": "스케줄이 성공적으로 수정되었습니다.",
            "modified_schedule": modified_schedule,
            "applied_feedback": feedback,
            "modified_at": datetime.now().isoformat()
        }
        
    except HTTPException as he:
        # HTTP 예외는 그대로 재발생
        raise he
        
    except Exception as e:
        logger.error(f"스케줄 수정 중 예기치 않은 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"스케줄 수정 중 오류가 발생했습니다: {str(e)}"
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