from fastapi import HTTPException, status
from src.model import User
from src.schema.user_schema import UserCreate
from src.repo.user_repo import UserRepo
from src.utils.hash_util import get_password_hash
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class UserService:

    def __init__(self, session):
        self.repo = UserRepo(session)

    async def create_user(self, user: UserCreate):
        logger.info(f"Creating user with email: {user.email}")

        existing_user = await self.repo.get_user_by_email(user.email)

        if existing_user:
            logger.warning(f"User already exists with email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )

        hashed_pwd = get_password_hash(user.password)

        user_obj = User(
            name=user.name,
            email=user.email,
            phone=user.phone,
            password=hashed_pwd
        )

        created_user = await self.repo.create_user(user_obj)

        logger.info(f"User created successfully: {user.email}")

        return {
            "message": "User created successfully",
            "user": created_user
        }


    async def get_users(self):
        logger.info("Fetching users from database")

        users = await self.repo.get_users()

        logger.info("Users fetched successfully")

        return users