import os
from dotenv import load_dotenv
from src.utils.logger import logger

load_dotenv()


class Config:

    def __init__(self):
        self.DATABASE_USER = os.getenv("MY_SQL_USER")
        self.DATABASE_PASSWORD = os.getenv("MY_SQL_PASSWORD")
        self.DATABASE_HOST = os.getenv("MY_SQL_HOST")
        self.DATABASE_PORT = os.getenv("MY_SQL_PORT")
        self.DATABASE_NAME = os.getenv("MY_SQL_DB")

        self.DATABASE_URL = (
            f"mysql+aiomysql://{self.DATABASE_USER}:"
            f"{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:"
            f"{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

        self.HASH_SECRET_KEY = os.getenv("HASH_SECRET_KEY")
        self.HASH_ALGORITHM = os.getenv("HASH_ALGORITHM")
        self.TOKEN_EXPIRY_TIME = int(os.getenv("TOKEN_EXPIRY_TIME", 30))

        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
        self.LLM_MODEL = os.getenv("LLM_MODEL")
        self.RERANK_API_KEY = os.getenv("COHERE_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")

        self._validate()

    def _validate(self):
        required_fields = [
            self.DATABASE_USER,
            self.DATABASE_PASSWORD,
            self.DATABASE_HOST,
            self.DATABASE_PORT,
            self.DATABASE_NAME,
        ]

        if not all(required_fields):
            raise ValueError("Missing required database environment variables")


config = Config()

logger.info(
    f"Config loaded | DB Host={config.DATABASE_HOST}, DB Name={config.DATABASE_NAME}, "
    f"Embedding Model={config.EMBEDDING_MODEL}, LLM Model={config.LLM_MODEL}"
)