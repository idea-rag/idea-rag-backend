from fastapi import FastAPI
app = FastAPI()

@app.get("/") #기본 url
def 함수이름():
    return "Hello world!"