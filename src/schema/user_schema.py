from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str


class UserRead(BaseModel):
    name: str
    email: EmailStr
    phone: str


# class UserResponse(BaseModel):
#     user: UserRead


class UserResponseList(BaseModel):
    data: list[UserRead]


class CurrentUser(BaseModel):
    id: int
    name: str
    email: str
    phone: str
