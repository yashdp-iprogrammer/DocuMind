from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Annotated
from src.services.user_service import UserService
from src.database import get_session
from src.schema.user_schema import UserCreate, UserRead, UserResponseList
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

router = APIRouter(prefix="/users")


def get_user_session(session: AsyncSession = Depends(get_session)):
    return UserService(session)


user_session = Annotated[UserService, Depends(get_user_session)]


@router.post("/create")
async def create_user(user: UserCreate, user_service: user_session):
    logger.info(f"Creating user with email: {user.email}")

    result = await user_service.create_user(user)

    logger.info(f"User created successfully: {user.email}")

    return result


@router.get("/get_users", response_model=UserResponseList)
async def get_users(user_service: user_session):
    logger.info("Fetching users")

    users = await user_service.get_users()

    logger.info("Users fetched successfully")

    return {
        "data": users
    }