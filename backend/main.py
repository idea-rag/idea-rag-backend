from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI, Query
from typing import List, Optional
from dotenv import load_dotenv
import uvicorn
import os
import time
load_dotenv() 

app = FastAPI()
uri = os.getenv("MONGODB_URI")

client = MongoClient(uri, server_api=ServerApi('1'))
db = client["user"]
users_collection = db["user_db"]
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

@app.get("/") #기본 url
def main():
    return {"message": "hello world!"}


@app.post("/register")
def register(
    userID: str = Query(...),
    name: Optional[str] = Query(None),
    school: Optional[str] = Query(None),
    gmail: Optional[str] = Query(None),
    password: str = Query(...),
    grade: Optional[str] = Query(None),
    subject_name: List[str] = Query([]),
    subject_publish: List[str] = Query([]),
    subject_workbook: List[str] = Query([]),
    subject_scope: List[str] = Query([])
):
    subjects = [
        {"name": n, "publish": p, "workbook": w, "scope": s}
        for n, p, w, s in zip(subject_name, subject_publish, subject_workbook, subject_scope)
    ]
    data = {
        "userID": userID,
        "name": name,
        "school": school,
        "gmail": gmail,
        "password": password,
        "grade": grade,
        "subjects": subjects,
    }
    if not data.get("userID") or not data.get("password"):
        return {"error": "UserID and password are required."}
        
    existing_user = users_collection.find_one({"userID": data.get("userID")})
    
    if existing_user:
        return {"error": "UserID already exists."}
    users_collection.insert_one(data)
    return {"message": f"User {data.get('userID')} signed up successfully!"}

@app.post("/login")
def login(userID: str = Query(...), password: str = Query(None)):
    if not userID or not password:
        return {"error": "UserID and password are required."}

    user = users_collection.find_one({"userID": userID})



    if user and user.get("password") == password:
        return {"message": f"User {userID} signed in successfully!"}
    elif user:
        return {"error": "Invalid password."}
    else:
        return {"error": "UserID not found."}

@app.get("/userInfo")
def get_user_info(userID: str = Query(...)):
    user = users_collection.find_one({"userID": userID})

    if not user:
        return {"error": "UserID not found."}
    else:
        user_data = {
            "userID": user.get("userID"),
            "name": user.get("name"),
            "school": user.get("school"),
            "gmail": user.get("gmail"),
            "grade": user.get("grade"),
            "subjects": user.get("subjects", []),
        }
        return {"userInfo": user_data}

@app.post("/schedule-create")
def create_schedule():
    pass

@app.post("/scope-modify")
def modify_scope(
    userID: str = Query(...),
    subject_name: str = Query(...),
    subject_publish: str = Query(...),
    subject_workbook: str = Query(...),
    new_scope: str = Query(...)
):
    if not userID:
        return {"error": "UserID is required."}

    user = users_collection.find_one({"userID": userID})
    if not user:
        return {"error": "UserID not found."}
    subjects = user.get("subjects", [])
    
    for subject in subjects:
        if (subject["name"] == subject_name and 
            subject["publish"] == subject_publish and 
            subject["workbook"] == subject_workbook):
            subject["scope"] = new_scope
            break
    else:
        return {"error": "Subject not found."}
    
    users_collection.update_one({"userID": userID}, {"$set": {"subjects": subjects}})

@app.post("/focus-start")
    

# 1. 스케줄 짜주기

# /schedule-create

# send : {
# 	when : 1 || 2 || 3 || 4 //week 1주, 2주, 3주, 4주....
# 	subjects : [{
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	},{
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	}...]
# }
#
#
# response : 
# {
#   1720508580: {
#     1: [
#     {
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	}
#     , importance : string , isFinished : boolean
#     ],
#     2: [
#     {
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	}
#     , importance : string , isFinished : boolean
#     ],
#   },
#   ...
#   1720508580: {
#     1: [
#     {
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	}
#     , importance : string , isFinished : boolean
#     ],
#     2: [
#     {
# 		name : string;
# 		publish : <김해찬이 만든 문제집 딕셔너리 중 출판사>
# 		workbook : <김해찬이 만든 문제집 딕셔너리 중 문제집 이름>
# 		scope : <김해찬이 만든 문제집 딕셔너리 중 문제집 범위 설정>
# 	}
#     , importance : string , isFinished : boolean
#     ],
#   },
#   }
# };
