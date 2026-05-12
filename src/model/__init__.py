from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phone: str = Field(unique=True)
    password: str
    

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_name: str
    file_path: str
    file_hash: str = Field(index=True)
    user_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)