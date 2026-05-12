import re
from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if not re.fullmatch(r"\d{10}", value):
            raise ValueError("Phone number must be exactly 10 digits")
        return value


class UserRead(BaseModel):
    name: str
    email: EmailStr
    phone: str


class UserResponseList(BaseModel):
    data: list[UserRead]


class CurrentUser(BaseModel):
    id: int
    name: str
    email: str
    phone: str