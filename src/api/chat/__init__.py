from fastapi import APIRouter, Depends, HTTPException, Request, status
from src.services.chat_service import chat_service
from src.security.o_auth import auth_dependency
from src.schema.chat_schema import ChatRequest
from src.utils.limiter import limiter
from src.utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])

router = APIRouter(tags=["Chat"])


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user=Depends(auth_dependency.get_current_active_user)
):
    logger.info(f"Chat request received | user_id={user.id} | query={chat_request.query}")

    if not chat_request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )

    result = await chat_service.ask(chat_request.query, user.id)

    return {
        "query": chat_request.query,
        "answer": result["answer"],
        "sources": result["sources"]
    }