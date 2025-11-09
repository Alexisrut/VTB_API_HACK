from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import re

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email адрес")
    phone_number: str = Field(..., description="Номер телефона в формате +7XXXXXXXXXX")
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r'^\+7\d{10}$', v):
            raise ValueError("Номер телефона должен быть в формате +7XXXXXXXXXX")
        return v

class UserRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=50)
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r'[a-z]', v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r'\d', v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_email_verified: bool
    is_phone_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserInDB(UserResponse):
    hashed_password: str

class SMSVerificationRequest(BaseModel):
    phone_number: str
    
class SMSVerificationConfirm(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)
