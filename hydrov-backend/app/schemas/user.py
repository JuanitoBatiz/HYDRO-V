# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreateSchema(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=8)
    name:     str = Field(max_length=100)


class UserLoginSchema(BaseModel):
    email:    EmailStr
    password: str


class UserResponseSchema(BaseModel):
    id:         int
    email:      str
    name:       str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenSchema(BaseModel):
    access_token: str
    token_type:   str = "bearer"


class TokenPayloadSchema(BaseModel):
    sub:  Optional[int] = None   # user_id
    exp:  Optional[int] = None