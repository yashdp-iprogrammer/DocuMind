# DocuMind — RAG-Powered Document Q&A API

A fully async backend API that lets users upload documents and query them using Retrieval-Augmented Generation. Built with FastAPI, LangChain, ChromaDB, and Groq LLM.

---

## Features

- **Multi-tenant vector store** — ChromaDB queries are filtered by `user_id` metadata, ensuring complete document isolation between users with no cross-user data leakage
- **Per-file error handling** — a single failing PDF does not abort the entire embed request; each file reports its own status
- **JWT authentication** — stateless auth with in-memory token invalidation

---

## Project Structure

```
DocuMind/
│
├── main.py                        # App entry point; registers routers and initializes DB
├── pyproject.toml                 # Project metadata and dependencies (uv)
├── uv.lock                        # Locked dependency versions
├── .env.example                   # Environment variable template
├── .python-version                # Pinned Python version
│
├── logs/
│   └── app.log                 
│
└── src/
    ├── api/                       # Route handlers
    │   ├── auth/                  # POST /login
    │   ├── chat/                  # POST /chat
    │   ├── document/              # POST /embed
    │   └── user/                  # POST /users/create, GET /users/get_users
    │
    ├── database/                  # Async engine setup, session factory, DB initializer
    │
    ├── model/                     # SQLModel ORM table definitions
    │
    ├── repo/
    │   └── user_repo.py           # DB queries for user
    │
    ├── schema/
    │   ├── auth_schema.py         # LoginRequest
    │   ├── chat_schema.py         # ChatRequest
    │   └── user_schema.py         # UserCreate, UserRead, CurrentUser, UserResponseList
    │
    ├── security/
    │   ├── dependencies.py        # OAuth2 scheme and in-memory token invalidation set
    │   └── o_auth.py              # JWT encode/decode, auth middleware
    │
    ├── services/
    │   ├── auth_service.py        # Credential validation, token generation
    │   ├── chat_service.py        # Vector search + Groq orchestration
    │   ├── document_service.py    # PDF ingestion pipeline coordinator
    │   ├── user_service.py        # User services
    │   └── vectordb_service.py    # ChromaDB add/search with per-user metadata filtering
    │
    ├── setting/
    │   └── config.py              # Loads and validates all environment variables at startup
    │
    ├── utils/
    │   ├── document_processor.py  # PDF loading (PyPDFLoader) and text chunking
    │   ├── file_util.py           # Saves uploaded files to disk, defines UPLOAD_DIR/CHROMA_DIR
    │   ├── hash_util.py           # Argon2 password hashing and verification
    │   └── logger.py              # Rotating file + console logger factory
    │
    └── vector_store/             
        ├── chroma_db/             # ChromaDB persistent index
        └── uploads/               # Uploaded PDFs (uuid-prefixed filenames)
```

---

## RAG Pipeline

1. **Ingestion** — PDF uploaded → loaded via `PyPDFLoader` → split into 500-token chunks (50-token overlap) → `user_id` injected into chunk metadata → stored in ChromaDB
2. **Retrieval** — Query embedded → top-3 chunks fetched from ChromaDB filtered strictly by `user_id`
3. **Generation** — Retrieved context + query sent to Groq LLM via `ainvoke` → response returned with source attribution (filename + page number)

---

## API Reference

### Auth

```
POST /login
Body: { "email": "...", "password": "..." }
Returns: { "access_token", "token_type" }
```

### Users

```
POST /users/create
Body: { "name", "email", "phone", "password" }

GET /users/get_users
```

### Documents

```
POST /embed                                   Bearer token required
Body: multipart/form-data — one or more PDF files
Returns: { "message", "results": [{ "file", "status", "chunks" }] }
```

### Chat

```
POST /chat                                    Bearer token required
Body: { "query": "..." }
Returns: { "query", "answer", "sources": [{ "content", "file_name", "page" }] }
```

---

## Setup

### Prerequisites

- Python 3.12+
- MySQL instance
- Groq API key — [get one here](https://console.groq.com)

### Installation

```bash
git clone https://github.com/yash2k02/DocuMind.git
cd DocuMind
pip install uv
uv sync
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```env
# Database
MY_SQL_USER=
MY_SQL_PASSWORD=
MY_SQL_HOST=
MY_SQL_PORT=3306
MY_SQL_DB=

# Auth
HASH_SECRET_KEY=
HASH_ALGORITHM=HS256
TOKEN_EXPIRY_TIME=30

# Models
EMBEDDING_MODEL=
LLM_MODEL=
GROQ_API_KEY=

# Storage
VECTOR_DB_PATH=src/vector_store
```

### Run

```bash
uvicorn main:app --reload
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (async) |
| Database | MySQL via `aiomysql` + SQLModel |
| Vector Store | ChromaDB |
| Embeddings | HuggingFace Sentence Transformers |
| LLM | Groq (`langchain-groq`) |
| Auth | JWT (`python-jose`) |
| Password Hashing | Argon2 (`passlib`) |
| PDF Processing | LangChain `PyPDFLoader` |
| Package Manager | `uv` |

---