import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./notes.db")
    jwt_secret: str = "change-me-super-secret-jwt-key-2024"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 30


DEBUG = True

settings = Settings()
