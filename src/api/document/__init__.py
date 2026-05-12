from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from src.services.document_service import document_service
from src.security.o_auth import auth_dependency
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

router = APIRouter(tags=["Documents"])


@router.post("/embed")
async def embed_documents(
    files: List[UploadFile] = File(...),
    user=Depends(auth_dependency.get_current_active_user)
):
    logger.info(f"Embedding documents for user_id={user.id}")

    results = []

    for file in files:
        try:
            result = await document_service.process_and_store(file, user.id)
            results.append(result)

        except HTTPException as e:
            logger.warning(f"Failed to process file: {file.filename} | {e.detail}")
            results.append({
                "file": file.filename,
                "status": "failed",
                "error": e.detail
            })

        except Exception as e:
            logger.error(f"Unexpected error for file: {file.filename} | {str(e)}", exc_info=True)
            results.append({
                "file": file.filename,
                "status": "failed",
                "error": "Unexpected error occurred"
            })

    return {
        "message": "Embedding completed",
        "results": results
    }