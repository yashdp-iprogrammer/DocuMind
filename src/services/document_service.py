from fastapi import HTTPException, status
from src.utils.document_processor import document_processor
from src.services.vectordb_service import vectordb_service
from src.utils.file_util import save_file
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class DocumentService:

    async def process_and_store(self, file, user_id: int):
        logger.info(f"Processing file: {file.filename}")

        file_path = save_file(file)

        docs = document_processor.load_pdf(file_path)

        if not docs:
            logger.warning(f"Empty or unreadable file: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{file.filename} is empty or unreadable"
            )

        chunks = document_processor.split_documents(docs)

        if not chunks:
            logger.warning(f"No chunks generated for file: {file.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process {file.filename}"
            )

        for chunk in chunks:
            chunk.metadata["user_id"] = user_id

        await vectordb_service.add_documents(chunks)

        logger.info(f"File embedded successfully: {file.filename}")

        return {
            "file": file.filename,
            "status": "embedded",
            "chunks": len(chunks)
        }


document_service = DocumentService()