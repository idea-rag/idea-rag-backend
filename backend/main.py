from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI, Query
from typing import List, Optional
import uvicorn

app = FastAPI()
uri = "mongodb+srv://24sunrin084:sunrinchan@fycus.qx0per4.mongodb.net/?retryWrites=true&w=majority&appName=fycus"

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


@app.post("/signup")
def signup(
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
        "subjects": subjects
    }
    if not data.get("userID") or not data.get("password"):
        return {"error": "UserID and password are required."}
        
    existing_user = users_collection.find_one({"userID": data.get("userID")})
    
    if existing_user:
        return {"error": "UserID already exists."}
    users_collection.insert_one(data)
    return {"message": f"User {data.get('userID')} signed up successfully!"}

@app.post("/signin")
def signin(userID: str = Query(...), password: str = Query(None)):
    if not userID or not password:
        return {"error": "UserID and password are required."}

    user = users_collection.find_one({"userID": userID})

    if user and user.get("password") == password:
        return {"message": f"User {userID} signed in successfully!"}
    elif user:
        return {"error": "Invalid password."}
    else:
        return {"error": "UserID not found."}
