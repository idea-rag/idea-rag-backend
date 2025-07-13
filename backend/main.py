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
def focus_start(focusTime = Query(...), 
                userID: str = Query(...), 
                measureTime: int = Query(0), 
                whenTime: int = Query(0), 
                whenDay: int = Query(0)):
    if not userID:
        return {"error": "UserID is required."}
    
    user = users_collection.find_one({"userID": userID})
    if not user:
        return {"error": "UserID not found."}
    data = {
        "userID": userID,
        "focusTime": focusTime,
        "measureTime": measureTime,
        "whenTime": whenTime,
        "whenDay": whenDay,
    }

    db["focus"].insert_one(data)

    return {"message": "Focus started successfully!"}

@app.post("/focus-feedback")
def focus_feedback(
    userID: str = Query(...),
    whenTime: int = Query(...),
    focus_data: dict = Query(...)
):
    if not userID or not focus_data:
        return {"error": "UserID and focus data are required."}
    
    user = users_collection.find_one({"userID": userID})
    if not user:
        return {"error": "UserID not found."}
    
    focus_collection = db["focus"]
    
    for i in focus_data:
        focus_collection.insert_one({userID,whenTime,{ 
            "userID": userID,
            "focusTime": focus_data[i].get("focusTime", 0),
            "measureTime": focus_data[i].get("measureTime", 0)
        }})

    return {"message": "Focus feedback recorded successfully!"}
