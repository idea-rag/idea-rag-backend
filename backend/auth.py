import os

from dotenv import load_dotenv
from typing import TypeVar
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")


USER_ID = TypeVar("USER_ID", str, None)
security = HTTPBearer()


class AuthService:
    def __init__(
        self,
    ):
        self.hashed_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    async def create_access_token(user_id: str) -> str:
        encoded_jwt = jwt.encode(
            {
                "uid": str(user_id),
            },
            JWT_SECRET_KEY,
            algorithm="HS256",
        )
        return encoded_jwt

    @staticmethod
    async def get_user_id_by_token(token: str) -> str:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        except JWTError:
            raise HTTPException(status_code=400, detail="Token is invalid.")
        return payload.get("uid")


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> USER_ID:
    try:
        token = credentials.credentials

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

        user_id: str = payload.get("uid")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
