from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.setting.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

DATABASE_URL = config.DATABASE_URL

logger.info("Initializing database engine")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_session():
    logger.debug("Creating new database session")

    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}", exc_info=True)
            raise


async def init_db():
    logger.info("Initializing database schema")

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    logger.info("Database schema initialized successfully")