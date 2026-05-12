from fastapi import HTTPException, status
from src.repo.user_repo import UserRepo
from src.security.o_auth import auth_dependency
from src.utils.hash_util import verify_password
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class AuthService:

    def __init__(self, session):
        self.repo = UserRepo(session)

    async def login(self, email: str, password: str):
        logger.info(f"Login attempt for email: {email}")

        user = await self.repo.get_user_by_email(email)

        if not user:
            logger.warning(f"Login failed - user not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not verify_password(password, user.password):
            logger.warning(f"Login failed - wrong password for: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        token = auth_dependency.create_access_token({"sub": str(user.id)})

        logger.info(f"Login successful for user: {email}")

        return {
            "message": "Login Successful",
            "access_token": token,
            "token_type": "bearer"
        }