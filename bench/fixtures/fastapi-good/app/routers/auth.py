from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.mail import send_mail
from app.security import hash_pw, make_token, verify_token

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, email: str, password: str): ...


@router.post("/auth/password-reset/request")
@limiter.limit("3/minute")
def request_password_reset(request: Request, email: str):
    token = make_token(email, purpose="password_reset", ttl=900)
    send_mail(email, "reset_password.html", token=token)


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(token: str, new_password: str):
    email = verify_token(token, purpose="password_reset")
    hash_pw(new_password)
