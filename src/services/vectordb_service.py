import asyncio
from fastapi import HTTPException, status
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src.utils.file_util import CHROMA_DIR
from src.setting.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class VectorDBService:

    def __init__(self):
        logger.info("Initializing VectorDBService")

        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL
        )


    def _get_db(self):
        return Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=self.embeddings
        )


    async def add_documents(self, docs):
        logger.info(f"Adding {len(docs)} documents to vector DB")

        try:
            db = self._get_db()
            await asyncio.to_thread(
                db.add_documents, docs
            )
        except Exception as e:
            logger.error(f"Failed to add documents to vector DB: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store documents"
            )

        logger.info("Documents added successfully")


    async def search(self, query: str, user_id: int, k=3):
        logger.info(f"Searching vector DB for query with user_id={user_id}")

        try:
            db = self._get_db()

            results = await asyncio.to_thread(
                db.similarity_search, query, k=k, filter={"user_id": str(user_id)}
            )
        except Exception as e:
            logger.error(
                f"Vector DB search failed | query={query} | user_id={user_id} | error={str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )

        logger.info(f"Retrieved {len(results)} documents")

        return results
    
    
    async def delete_by_file_id(self, file_id: int):
        logger.info(f"Deleting embeddings for file_id={file_id}")

        try:
            db = self._get_db()

            before = await asyncio.to_thread(db.get, where={"file_id": str(file_id)})
            logger.info(f"Before delete: {len(before['ids'])}")

            await asyncio.to_thread(db.delete, where={"file_id": str(file_id)})

            after = await asyncio.to_thread(db.get, where={"file_id": str(file_id)})
            logger.info(f"After delete: {len(after['ids'])}")

        except Exception as e:
            logger.error(
                f"Failed to delete embeddings for file_id={file_id} | error={str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document embeddings"
            )

        logger.info(f"Embeddings deleted for file_id={file_id}")


vectordb_service = VectorDBService()