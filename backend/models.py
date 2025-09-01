from pydantic import BaseModel


class RegisterDTO(BaseModel):
    userID: str
    name: str
    school: str
    grade : str
    email: str
    password: str
    subject_name: list[str]
    subject_publish: list[str]
    subject_BookList : list[str]
    focus_Grade: list[str]
    Subject_Module: list[dict]
    Focus_Subject : str
    WhatWeek : str


class LoginDTO(BaseModel):
    userID: str
    password: str


class ScopeModifyDTO(BaseModel):
    subject_name: str
    subject_publish: str
    subject_workbook: str
    new_scope: str


class FocusStartDTO(BaseModel):
    focusTime: str
    measureTime: int = 0
    whenTime: int = 0
    whenDay: int = 0


class FocusFeedbackDTO(BaseModel):
    whenTime: int
    focus_data: dict


class NeurofeedbackSendDTO(BaseModel):
    when: int
    find_dog: dict
    select_square: dict


class FindDogImageLoadDTO(BaseModel):
    number: list[int]

class ScheduleDTO(BaseModel):
    when : int
    subjects : list[dict]

class AIResponseDTO(BaseModel):
    userID: str
    date : str
    startingTime : int
    currentSubject: dict
