from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterDto(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginDto(BaseModel):
    email: EmailStr
    password: str


class RefreshDto(BaseModel):
    refresh_token: str


class LogoutDto(BaseModel):
    refresh_token: str


class UserResponseDto(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime


class TokenPairDto(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponseDto(BaseModel):
    user: UserResponseDto
    tokens: TokenPairDto


class MessageResponseDto(BaseModel):
    message: str
