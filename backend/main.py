from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI
import uvicorn

app = FastAPI()
uri = "mongodb+srv://24sunrin084:<db_password>@fycus.qx0per4.mongodb.net/?retryWrites=true&w=majority&appName=fycus"

client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

@app.get("/") #기본 url
def main():
    return "Hello world!"

@app.post("/signup")
def signup(request: dict):

    data = {
        "userID": request.get("userID"),  # 사용자 ID
        "name": request.get("name"),  # 사용자 이름
        "school": request.get("school"),  # 학교 이름
        "gmail": request.get("gmail"),  # Gmail 주소
        "password": request.get("password"),  # 비밀번호 (정규식으로 검증
        "grade": request.get("grade"),  # 학년 (1~3)
        "subjects": [
            {
                "name": name,
                "publish": publish,
                "workbook": workbook,
                "scope": scope
            }

            for name,publish,workbook,scope in zip(
                request.get("subject_name", []),
                request.get("subject_publish", []),
                request.get("subject_workbook", []),
                request.get("subject_scope", [])
            )
        ]
    }

    if not data.get("userID") or not data.get("password"):
        return {"error": "UserID and password are required."}

    db = client["fycus"]
    users_collection = db["users"]
    existing_user = users_collection.find_one({"userID": data.get("userID")})
    if existing_user:
        return {"error": "UserID already exists."}
    users_collection.insert_one(data)
    return {"message": f"User {data.get('userID')} signed up successfully!"}

@app.post("/signin")
def signin(request):
    userID = request.get("userID")
    password = request.get("password")

    if not userID or not password:
        return {"error": "UserID and password are required."}

    db = client["fycus"]
    users_collection = db["users"]
    user = users_collection.find_one({"userID": userID, "password": password})

    if user:
        return {"message": f"User {userID} signed in successfully!"}
    else:
        return {"error": "Invalid UserID or password."}