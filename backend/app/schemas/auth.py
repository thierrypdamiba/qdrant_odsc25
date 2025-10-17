"""Authentication schemas"""
from pydantic import BaseModel
from app.core.auth import UserPermissions


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    user_id: str
    username: str
    role: str
    permissions: UserPermissions


