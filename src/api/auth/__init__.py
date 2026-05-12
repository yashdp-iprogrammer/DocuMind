from fastapi import APIRouter, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Annotated
from src.services.auth_service import AuthService
from src.schema.auth_schema import LoginRequest
from src.database import get_session
from src.utils.limiter import limiter
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

router = APIRouter(tags=["Auth"])


def get_auth_session(session: AsyncSession = Depends(get_session)):
    return AuthService(session)


auth_session = Annotated[AuthService, Depends(get_auth_session)]


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, auth_service: auth_session):
    logger.info(f"Login request received for email: {data.email}")

    result = await auth_service.login(data.email, data.password)

    logger.info(f"Login successful for email: {data.email}")

    return result