from fastapi import HTTPException, status
from langchain_groq import ChatGroq
from src.setting.config import config
from src.services.vectordb_service import vectordb_service
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class ChatService:

    def __init__(self):
        self.llm = ChatGroq(
            model=config.LLM_MODEL,
            api_key=config.GROQ_API_KEY
        )
        self.vectordb_service = vectordb_service

    async def ask(self, query: str, user_id: int):
        logger.info(f"Processing chat query for user_id={user_id}")

        docs = await self.vectordb_service.search(query, user_id)

        if not docs:
            logger.warning("No relevant documents found for query")
            return {
                "answer": "I couldn't find relevant information in your uploaded documents. Try rephrasing your question or upload more documents.",
                "sources": []
            }

        context = "\n".join([doc.page_content for doc in docs])

        prompt = f"""
        Answer only from the context.

        Context:
        {context}

        Question:
        {query}
        """

        logger.info("Sending request to LLM")

        try:
            response = await self.llm.ainvoke(prompt)
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response from LLM"
            )

        logger.info("LLM response received")

        sources = [
            {
                "content": doc.page_content,
                "file_name": doc.metadata.get("file_name"),
                "page": doc.metadata.get("page")
            }
            for doc in docs
        ]

        return {
            "answer": response.content,
            "sources": sources
        }


chat_service = ChatService()