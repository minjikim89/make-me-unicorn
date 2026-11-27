from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class NoteIn(BaseModel):
    title: str = Field(max_length=200)
    body: str


class SummarizeIn(BaseModel):
    note_id: int
