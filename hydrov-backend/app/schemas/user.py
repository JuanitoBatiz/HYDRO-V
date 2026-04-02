# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreateSchema(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(max_length=150)
    role_id: int = Field(default=3) # Viewer by default
    zone_id: Optional[int] = None


class UserLoginSchema(BaseModel):
    email:    EmailStr
    password: str


class UserResponseSchema(BaseModel):
    id:         int
    email:      str
    full_name:  str
    role_id:    int
    zone_id:    Optional[int]
    is_active:  bool
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TokenSchema(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   int = 86400


class TokenPayloadSchema(BaseModel):
    sub:  Optional[int] = None   # user_id
    exp:  Optional[int] = None