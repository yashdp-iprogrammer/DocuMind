import asyncio
import numpy as np
import re
import cohere
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
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

        self.db = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=self.embeddings
        )

        # Cohere client
        self.cohere_client = cohere.Client(api_key=config.RERANK_API_KEY)

        # BM25 CACHE
        self.user_docs_cache = {}
        self.user_token_cache = {}
        self.user_bm25_cache = {}


    async def add_documents(self, docs):
        logger.info(f"Adding {len(docs)} documents to vector DB")

        try:
            db = self.db
            await asyncio.to_thread(db.add_documents, docs)

            # Invalidate cache for affected users
            user_ids = {doc.metadata.get("user_id") for doc in docs if doc.metadata.get("user_id")}
            for uid in user_ids:
                self._invalidate_user_cache(uid)

        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store documents"
            )

        logger.info("Documents added successfully")


    def _invalidate_user_cache(self, user_id):
        logger.info(f"Invalidating BM25 cache for user_id={user_id}")

        self.user_docs_cache.pop(str(user_id), None)
        self.user_token_cache.pop(str(user_id), None)
        self.user_bm25_cache.pop(str(user_id), None)


    def tokenize(self, text: str):
        return re.findall(r"\w+", text.lower())

    
    async def search(self, query: str, user_id: int, k=5):
        db = self.db
        user_id_str = str(user_id)

        TOP_K_RETRIEVAL = 20
        RRF_K = 60

        logger.info(f"Hybrid search started | user_id={user_id} | query='{query}'")

        # VECTOR SEARCH
        vector_results = await asyncio.to_thread(
            db.similarity_search,
            query,
            k=TOP_K_RETRIEVAL,
            filter={"user_id": user_id_str}
        )
        logger.info(f"Vector search retrieved {len(vector_results)} documents")

        # BM25 CACHE CHECK
        if user_id_str not in self.user_bm25_cache:

            logger.info(f"BM25 cache MISS for user_id={user_id}")

            all_docs_data = await asyncio.to_thread(
                db.get,
                where={"user_id": user_id_str}
            )

            if not all_docs_data or not all_docs_data.get("documents"):
                logger.warning("No documents found in vector DB")
                return vector_results[:k]

            documents = [
                Document(
                    page_content=all_docs_data["documents"][i],
                    metadata=all_docs_data["metadatas"][i]
                )
                for i in range(len(all_docs_data["documents"]))
            ]

            tokenized_corpus = [self.tokenize(doc.page_content) for doc in documents]

            bm25 = BM25Okapi(tokenized_corpus)

            # Cache everything
            self.user_docs_cache[user_id_str] = documents
            self.user_token_cache[user_id_str] = tokenized_corpus
            self.user_bm25_cache[user_id_str] = bm25

            logger.info(f"BM25 cache BUILT | docs={len(documents)}")

        else:
            logger.info(f"BM25 cache HIT for user_id={user_id}")

            documents = self.user_docs_cache[user_id_str]
            bm25 = self.user_bm25_cache[user_id_str]

        if not documents:
            logger.warning("No documents found for BM25, falling back to vector results")
            return vector_results[:k]

        # BM25 SEARCH
        tokenized_query = self.tokenize(query)
        scores = bm25.get_scores(tokenized_query)

        top_indices = np.argsort(scores)[::-1][:TOP_K_RETRIEVAL]
        keyword_results = [documents[i] for i in top_indices]

        logger.info(f"BM25 retrieved top {len(keyword_results)} documents")

        # RRF FUSION
        rrf_scores = {}

        def get_doc_id(doc):
            return (
                doc.metadata.get("file_id"),
                doc.metadata.get("page"),
                hash(doc.page_content[:100])
            )

        # Vector scores
        for rank, doc in enumerate(vector_results):
            doc_id = get_doc_id(doc)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)

        # BM25 scores
        for rank, doc in enumerate(keyword_results):
            doc_id = get_doc_id(doc)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)

        # Deduplicate
        doc_map = {}
        for doc in vector_results + keyword_results:
            doc_map[get_doc_id(doc)] = doc

        # Sort by RRF
        sorted_docs = sorted(
            doc_map.items(),
            key=lambda x: rrf_scores.get(x[0], 0),
            reverse=True
        )

        fused_results = [doc for _, doc in sorted_docs[:TOP_K_RETRIEVAL]]

        logger.info(f"RRF fusion completed | fused_docs={len(fused_results)}")

        if not fused_results:
            logger.warning("No fused results, returning empty list")
            return []

        # COHERE RERANK
        try:
            logger.info(f"Sending {len(fused_results)} docs to Cohere reranker")

            rerank_response = await asyncio.to_thread(
                self.cohere_client.rerank,
                model="rerank-english-v3.0",
                query=query,
                documents=[doc.page_content for doc in fused_results],
                top_n=k
            )

            final_docs = [
                fused_results[result.index]
                for result in rerank_response.results
            ]

            logger.info(f"Cohere rerank successful | returned_top_k={len(final_docs)}")

        except Exception as e:
            logger.error(f"Cohere rerank failed: {str(e)}", exc_info=True)
            logger.warning("Falling back to RRF results")
            final_docs = fused_results[:k]

        # FINAL OUTPUT
        logger.info(f"Hybrid search completed | final_docs={len(final_docs)}")

        return final_docs


    async def delete_by_file_id(self, file_id: int):
        logger.info(f"Deleting embeddings for file_id={file_id}")

        try:
            db = self.db

            before = await asyncio.to_thread(db.get, where={"file_id": str(file_id)})
            logger.info(f"Before delete: {len(before['ids'])}")

            # Collect affected user_ids before deletion
            user_ids = set()
            for meta in before.get("metadatas", []):
                if meta.get("user_id"):
                    user_ids.add(meta.get("user_id"))

            await asyncio.to_thread(db.delete, where={"file_id": str(file_id)})

            after = await asyncio.to_thread(db.get, where={"file_id": str(file_id)})
            logger.info(f"After delete: {len(after['ids'])}")

            # Invalidate cache for affected users
            for uid in user_ids:
                self._invalidate_user_cache(uid)

        except Exception as e:
            logger.error(f"Delete failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete document embeddings"
            )

        logger.info(f"Embeddings deleted for file_id={file_id}")


vectordb_service = VectorDBService()