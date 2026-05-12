import os
from typing import List
from fastapi import APIRouter, Request, UploadFile, File, Depends, HTTPException
from src.security.o_auth import auth_dependency
from sqlmodel.ext.asyncio.session import AsyncSession
from src.database import get_session
from typing import Annotated
from src.services.document_service import DocumentService
from src.utils.limiter import limiter
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

router = APIRouter(tags=["Documents"], prefix="/documents")

def get_document_service(session: AsyncSession = Depends(get_session)):
    return DocumentService(session)

document_service_dep = Annotated[DocumentService, Depends(get_document_service)]


@router.post("/embed")
@limiter.limit("5/minute")
async def embed_documents(
    request: Request,
    document_service: document_service_dep,
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


@router.get("/")
async def list_documents(
    document_service: document_service_dep,
    page: int = 1,
    size: int = 10,
    user=Depends(auth_dependency.get_current_active_user),
):
    offset = (page - 1) * size

    docs = await document_service.doc_repo.get_by_user(user.id, offset, size)
    total = await document_service.doc_repo.count_by_user(user.id)

    return {
        "data": docs,
        "page": page,
        "size": size,
        "total": total
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    document_service: document_service_dep,
    user=Depends(auth_dependency.get_current_active_user),
):
    doc = await document_service.doc_repo.get_by_id(doc_id)

    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    await document_service.vectordb_service.delete_by_file_id(doc.id)

    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await document_service.doc_repo.delete(doc)

    return {"message": "Document deleted successfully"}