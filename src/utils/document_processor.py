from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.utils.logger import get_logger
import os

logger = get_logger(__name__.split(".")[-1])


class DocumentProcessor:

    def load_pdf(self, file_path: str):
        logger.info(f"Loading PDF: {file_path}")

        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        except Exception as e:
            logger.error(f"Failed to load PDF: {file_path} | error={str(e)}", exc_info=True)
            raise

        if not docs:
            logger.warning(f"No content found in PDF: {file_path}")
            return []

        file_name = os.path.basename(file_path)

        for doc in docs:
            doc.metadata["file_name"] = file_name

        return docs

    def split_documents(self, docs):
        if not docs:
            logger.warning("No documents provided for splitting")
            return []

        logger.info(f"Splitting {len(docs)} documents")

        try:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )

            chunks = splitter.split_documents(docs)

        except Exception as e:
            logger.error(f"Document splitting failed | error={str(e)}", exc_info=True)
            raise

        logger.info(f"Generated {len(chunks)} chunks")

        return chunks


document_processor = DocumentProcessor()