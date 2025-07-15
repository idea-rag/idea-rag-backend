from pydantic import BaseModel


class RegisterDTO(BaseModel):
    userID: str
    name: str
    school: str
    gmail: str
    password: str
    grade: str
    subject_name: list[str]
    subject_publish: list[str]
    subject_workbook: list[str]
    subject_scope: list[str]


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
