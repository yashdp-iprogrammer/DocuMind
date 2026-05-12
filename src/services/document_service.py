from fastapi import HTTPException, status
from src.utils.document_processor import document_processor
from src.services.vectordb_service import vectordb_service
from src.utils.file_util import save_file
from src.repo.document_repo import DocumentRepo
from src.model import Document
from src.utils.file_util import get_file_hash
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class DocumentService:

    def __init__(self, session):
        self.doc_repo = DocumentRepo(session)
        self.vectordb_service = vectordb_service

    async def process_and_store(self, file, user_id: int):
        logger.info(f"Processing file: {file.filename}")

        file_hash = get_file_hash(file)

        existing_doc = await self.doc_repo.get_by_hash_and_user(file_hash, user_id)

        if existing_doc:
            logger.info(f"Duplicate file skipped: {file.filename}")
            return {
                "file": file.filename,
                "status": "skipped",
                "message": "File already uploaded"
            }

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


        doc_entry = await self.doc_repo.create(Document(
        file_name=file.filename,
        file_path=file_path,
        user_id=user_id,
        file_hash=file_hash
        ))

        file_id = str(doc_entry.id)

        for chunk in chunks:
            chunk.metadata["user_id"] = str(user_id)
            chunk.metadata["file_name"] = str(file.filename)
            chunk.metadata["file_id"] = file_id

        await vectordb_service.add_documents(chunks)

        logger.info(f"File embedded successfully: {file.filename}")

        return {
            "file": file.filename,
            "status": "embedded",
            "chunks": len(chunks)
        }