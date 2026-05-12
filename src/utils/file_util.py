import os
import shutil
from uuid import uuid4
from fastapi import UploadFile
from src.setting.config import config
import hashlib
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

BASE_DIR = config.VECTOR_DB_PATH
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)


def save_file(file: UploadFile) -> str:
    """
    Save uploaded file with a unique name and return file path.
    """

    logger.info(f"Saving file: {file.filename}")

    try:
        original_name = os.path.basename(file.filename)

        unique_filename = f"{uuid4().hex}_{original_name}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    except Exception as e:
        logger.error(
            f"Failed to save file: {file.filename} | error={str(e)}",
            exc_info=True
        )
        raise

    logger.info(f"File saved successfully: {file_path}")

    return file_path

def get_file_hash(file: UploadFile) -> str:
    """
    Generate SHA-256 hash for file content
    """

    hasher = hashlib.sha256()

    content = file.file.read()
    hasher.update(content)

    file.file.seek(0)

    return hasher.hexdigest()