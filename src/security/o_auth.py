from fastapi import Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt
from jose.exceptions import JWTError
from src.security.dependencies import oauth2_scheme, invalidated_tokens
from src.model import User
from src.setting.config import config
from src.utils.logger import get_logger
from src.schema.user_schema import CurrentUser
from src.database import get_session

logger = get_logger(__name__.split(".")[-1])


class AuthDependency:

    def __init__(
        self,
        secret_key: str = config.HASH_SECRET_KEY,
        algorithm: str = config.HASH_ALGORITHM,
        access_token_expiry_time: int = config.TOKEN_EXPIRY_TIME,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expiry_time = int(access_token_expiry_time)


    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.access_token_expiry_time)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)


    def decode_jwt_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError as e:
            logger.warning(f"JWT decode failed | error={str(e)}")
            return None


    async def get_current_active_user(
        self,
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_session),
    ) -> CurrentUser:

        if token in invalidated_tokens:
            logger.warning("Invalidated token used")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated",
            )

        payload = self.decode_jwt_token(token)

        if not payload or "sub" not in payload:
            logger.warning("Invalid or malformed JWT token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        try:
            user_id = int(payload["sub"])
        except ValueError:
            logger.warning("Invalid user_id in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        try:
            statement = select(User).where(User.id == user_id)
            result = await session.exec(statement)
            user = result.first()
        except Exception as e:
            logger.error(
                f"Database error while fetching user from token | error={str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch user"
            )

        if not user:
            logger.warning("User not found for token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        return CurrentUser(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone
        )


auth_dependency = AuthDependency()