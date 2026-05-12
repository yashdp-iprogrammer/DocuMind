from passlib.context import CryptContext
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed | error={str(e)}")
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(str(password))