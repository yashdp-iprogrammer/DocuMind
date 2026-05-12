from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from src.utils.limiter import limiter
from src.api.chat import router as chat_router
from src.api.user import router as user_router
from src.api.auth import router as auth_router
from src.api.document import router as document_router
from src.api.evaluation import router as evaluation_router
from src.database import init_db
from src.utils.logger import logger


async def lifespan(app):
    await init_db()
    yield


app = FastAPI(title="LLM Doc Chatbot", lifespan=lifespan)

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded | path={request.url} | limit={exc.detail}")
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": f"Rate limit exceeded. Please slow down.",
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP error occurred: {exc.detail} | Path: {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()} | Path: {request.url}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "Validation Error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {str(exc)} | Path: {request.url}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
        },
    )


app.include_router(chat_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(document_router)
app.include_router(evaluation_router)