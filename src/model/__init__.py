from sqlmodel import SQLModel, Field
from pydantic import field_validator
from typing import Optional
import re


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    phone: str = Field(unique=True)
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if not re.fullmatch(r"\d{10}", value):
            raise ValueError("Phone number must be exactly 10 digits")
        return value