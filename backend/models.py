from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# RegisterDTO: Python의 snake_case 네이밍 컨벤션에 맞게 필드명을 수정했습니다.
class RegisterDTO(BaseModel):
    userID: str
    name: str
    school: str
    grade: str
    email: str
    password: str
    subject_name: List[str]
    subject_publish: List[str]
    subject_book_list: List[str]      # subject_BookList -> subject_book_list
    focus_Grade: List[str]            # (이 필드는 의도에 따라 focus_grade로 변경 가능)
    subject_module: List[Dict[str, Any]] # Subject_Module -> subject_module
    focus_subject: str                # Focus_Subject -> focus_subject
    what_week: str                    # WhatWeek -> what_week


class LoginDTO(BaseModel):
    userID: str
    password: str


class ScopeModifyDTO(BaseModel):
    original_schedule: Any
    new_scope: str


class FocusStartDTO(BaseModel):
    focusTime: int  # 집중 시간 (분 단위)
    measureTime: int  # 측정 시간 (분 단위)
    whenDay: str    # 날짜 (YYYY-MM-DD 형식)
    timeSlot: str   # 시간대 (예: '10-20'은 10시 20분대를 의미)


class TimeSlotData(BaseModel):
    measureTime: int
    focusTime: int

class FocusFeedbackDTO(BaseModel):
    whenDay: str  # YYYY-MM-DD format
    timeSlots: Dict[str, Dict[str, int]]  # Key is time slot like "10-20"
    studyData: Dict[str, Any]  # 추가된 필드: 학습 데이터

class NeurofeedbackSendDTO(BaseModel):
    when: int
    find_dog: Dict[str, Any]
    select_square: Dict[str, Any]


class FindDogImageLoadDTO(BaseModel):
    number: List[int]

# ScheduleDTO: 학습 목표(goal)를 받을 수 있도록 Optional 필드를 추가했습니다.
class ScheduleDTO(BaseModel):
    when: int
    subjects: List[Dict[str, Any]]
    goal: Optional[str] = None  # [핵심 수정] AI에게 전달할 학습 목표(goal) 필드 추가


class AIResponseDTO(BaseModel):
    userID: str
    date: str
    currentSubject: Dict[str, Any]