import os

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
JWT_SECRET = os.environ["JWT_SECRET"]  # no default: startup fails when it is missing
JWT_ALGORITHM = "HS256"
TOKEN_HEADER_NAME = "X-Auth-Token"


def hash_pw(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def make_token(subject: str, purpose: str, ttl: int) -> str: ...


def verify_token(token: str, purpose: str) -> str: ...
