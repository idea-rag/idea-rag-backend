import os

from dotenv import load_dotenv
from typing import TypeVar, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo.database import Database

from database import get_db
from exceptions import InvalidTokenException, UserNotFoundException
from logger import create_logger

load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

logger = create_logger(__name__)

USER_ID = TypeVar("USER_ID", str, None)
security = HTTPBearer()


class AuthService:
    def __init__(self):
        self.hashed_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @staticmethod
    async def create_access_token(user_id: str) -> str:
        logger.info(f"Creating access token for userID: {user_id}")
        encoded_jwt = jwt.encode(
            {
                "uid": str(user_id),
            },
            JWT_SECRET_KEY,
            algorithm="HS256",
        )
        logger.info(f"Access token created (user_id={user_id})")
        return encoded_jwt

    @staticmethod
    async def get_user_id_by_token(token: str) -> str:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("uid")
            return user_id
        except JWTError as e:
            logger.warning(f"Token decode failed: {e}")
            raise InvalidTokenException()

    @staticmethod
    async def verify_user_exists(user_id: str, db: Database) -> bool:
        users_collection = db["user_db"]
        user = await users_collection.find_one({"userID": user_id})
        exists = user is not None
        return exists

    @staticmethod
    async def get_user_by_id(user_id: str, db: Database) -> dict | None:
        users_collection = db["user_db"]
        user = await users_collection.find_one({"userID": user_id})
        if not user:
            logger.warning(f"User not found for userID: {user_id}")
        return user

    @staticmethod
    def hash_password(password: str) -> str:
        crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return crypt_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        is_valid = crypt_context.verify(plain_password, hashed_password)
        return is_valid


def get_auth_service() -> AuthService:
    return AuthService()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Database = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> USER_ID:
    try:
        token = credentials.credentials

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

        user_id: str | None = payload.get("uid")
        if user_id is None:
            logger.warning("Token payload missing user ID")
            raise InvalidTokenException()

        user_exists = await auth_service.verify_user_exists(user_id, db)
        if not user_exists:
            logger.warning(f"Token user not found in database: {user_id}")
            raise UserNotFoundException(user_id)

        logger.info(f"Authentication successful for userID: {user_id}")
        return user_id

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenException()


async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    db: Database = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    user = await auth_service.get_user_by_id(current_user_id, db)
    if not user:
        logger.warning(f"Session user not found: {current_user_id}")
        raise UserNotFoundException(current_user_id)
    return user
