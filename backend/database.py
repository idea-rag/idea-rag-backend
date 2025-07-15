from fastapi import FastAPI
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.server_api import ServerApi
from contextlib import asynccontextmanager
import os
from typing import Optional

from logger import create_logger

logger = create_logger(__name__)


class DatabaseManager:
    def __init__(self):
        self.client: Optional[AsyncMongoClient] = None
        self.db: Optional[AsyncDatabase] = None

    async def connect(self):
        uri = os.getenv("MONGODB_URI")
        if not uri:
            logger.error("MONGODB_URI environment variable is not set")
            raise ValueError("MONGODB_URI environment variable is not set")

        self.client = AsyncMongoClient(uri, server_api=ServerApi("1"))
        await self.client.aconnect()
        self.db = self.client["user"]

        try:
            await self.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()
            logger.info("MongoDB connection closed.")

    def get_db(self) -> AsyncDatabase:
        if not self.db is not None:
            logger.error("Database not connected. Call connect() first.")
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db


db_manager = DatabaseManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting application...")
    await db_manager.connect()
    yield
    logger.info("Shutting down application...")
    await db_manager.disconnect()


def get_db() -> AsyncDatabase:
    return db_manager.get_db()
