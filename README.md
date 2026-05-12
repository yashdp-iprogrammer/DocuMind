# DocuMind — RAG-Powered Document Q&A

A fully async backend API and Streamlit frontend that lets users upload documents and query them using Retrieval-Augmented Generation. Built with FastAPI, LangChain, ChromaDB, and Groq LLM.

---

## Features

- **Multi-tenant vector store** — ChromaDB queries are filtered by `user_id` metadata, ensuring complete document isolation between users with no cross-user data leakage
- **Hybrid search pipeline** — combines dense vector search, BM25 keyword search, Reciprocal Rank Fusion (RRF), and Cohere reranking for high-quality retrieval
- **BM25 cache** — per-user BM25 index is built once and cached in memory; automatically invalidated when documents are added or deleted
- **Duplicate detection** — SHA-256 file hashing prevents re-embedding the same document per user
- **Document management** — list and delete uploaded documents via API; deletions cascade to the database record, the file on disk, and ChromaDB embeddings
- **Per-file error handling** — a single failing PDF does not abort the entire embed request; each file reports its own status (`embedded`, `skipped`, `failed`)
- **Rate limiting** — SlowAPI enforces per-IP limits: 5/min on `/login` and `/documents/embed`, 10/min on `/chat`
- **JWT authentication** — stateless auth with in-memory token invalidation
- **Streamlit frontend** — register, login, upload and manage documents, and chat with your documents in a single-page UI with client-side validation and standardized error handling

---

## Project Structure
```
DocuMind/
│
├── main.py                        # App entry point; registers routers, initializes DB, rate limiter
├── app.py                         # Streamlit frontend
├── pyproject.toml                 # Project metadata and dependencies (uv)
├── uv.lock                        # Locked dependency versions
├── Dockerfile                     # Multi-stage image build for API and frontend
├── compose.yml                    # Docker Compose — mysql, api, and frontend services
├── .dockerignore                  # Excludes .venv, logs, uploads, and chroma_db from image
├── .env.example                   # Environment variable template
├── .gitignore                     # Ignored paths
├── .python-version                # Pinned Python version
│
├── logs/
│   └── app.log
│
└── src/
    ├── api/                       # Route handlers
    │   ├── auth/                  # POST /login
    │   ├── chat/                  # POST /chat
    │   ├── document/              # POST /documents/embed, GET /documents/, DELETE /documents/{id}
    │   └── user/                  # POST /users/create, GET /users/get_users
    │
    ├── database/                  # Async engine setup, session factory, DB initializer
    │
    ├── model/                     # SQLModel ORM table definitions (User, Document)
    │
    ├── repo/
    │   ├── user_repo.py           # DB queries for User
    │   └── document_repo.py       # DB queries for Document
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
    │   ├── chat_service.py        # Vector search + Groq LLM orchestration
    │   ├── document_service.py    # PDF ingestion pipeline coordinator
    │   ├── user_service.py        # User creation and listing
    │   └── vectordb_service.py    # Hybrid search (BM25 + vector + RRF + Cohere rerank), ChromaDB CRUD, BM25 cache
    │
    ├── setting/
    │   └── config.py              # Loads and validates all environment variables at startup
    │
    ├── utils/
    │   ├── document_processor.py  # PDF loading (PyPDFLoader) and text chunking
    │   ├── limiter.py             # configures rate limiter
    │   ├── file_util.py           # File save, SHA-256 hashing, UPLOAD_DIR/CHROMA_DIR setup
    │   ├── hash_util.py           # Argon2 password hashing and verification
    │   └── logger.py              # Rotating file + console logger factory
    │
    └── vector_store/
        ├── chroma_db/             # ChromaDB persistent index
        └── uploads/               # Uploaded PDFs (uuid-prefixed filenames)
```

---

## RAG Pipeline

### Ingestion

PDF uploaded → SHA-256 hash checked for duplicates → loaded via `PyPDFLoader` → split into 500-token chunks (50-token overlap) → `user_id`, `file_id`, and `file_name` injected into chunk metadata → record saved to MySQL → chunks stored in ChromaDB → user's BM25 cache invalidated

### Retrieval — Hybrid Search

Queries go through a 3-stage pipeline before reaching the LLM:

1. **Vector search** — top-20 chunks retrieved from ChromaDB using dense embedding similarity, filtered strictly by `user_id`
2. **BM25 keyword search** — all of the user's documents are loaded once, tokenized, and indexed with BM25Okapi; subsequent queries hit the in-memory cache (cache miss triggers a rebuild). Top-20 BM25 results are retrieved
3. **RRF fusion** — Reciprocal Rank Fusion merges and deduplicates the two result lists into a unified ranking (k=60)
4. **Cohere reranking** — top-20 fused documents are reranked by Cohere's `rerank-english-v3.0` model; final top-5 are returned to the LLM

### Generation

Retrieved context + query sent to Groq LLM via `ainvoke` → response returned with source attribution (filename + page number)

### Deletion

Document deleted from MySQL → ChromaDB embeddings deleted by `file_id` → file removed from disk → user's BM25 cache invalidated

---

## API Reference

### Auth

```
POST /login                                   Rate limit: 5/min per IP
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
POST /documents/embed                         Bearer token required | Rate limit: 5/min per IP
Body: multipart/form-data — one or more PDF files
Returns: { "message", "results": [{ "file", "status", "chunks" | "message" }] }
  status values: "embedded" | "skipped" | "failed"

GET /documents/                               Bearer token required
Query params: page (default 1), size (default 10)
Returns: { "data": [...], "page", "size", "total" }

DELETE /documents/{doc_id}                    Bearer token required
Returns: { "message": "Document deleted successfully" }
```

### Chat

```
POST /chat                                    Bearer token required | Rate limit: 10/min per IP
Body: { "query": "..." }
Returns: { "query", "answer", "sources": [{ "content", "file_name", "page" }] }
```

---

## Streamlit Frontend

The frontend is a single-page Streamlit app (`app.py`) that covers the full user flow.

**Auth (unauthenticated view)**
- Tabbed layout with Login and Register on the same page
- Registration includes client-side validation before hitting the API: name required, valid email format, 10-digit phone, minimum 6-character password
- Inline field-level error messages displayed beneath each input
- API errors (duplicate email, invalid credentials) are surfaced using the standardized FastAPI error response shape

**Main app (authenticated view)**
- Sidebar shows the logged-in user's email, a logout button, and a PDF uploader with an embed trigger
- Document manager expander lists all uploaded documents with a per-row delete button
- Chat interface with persistent session history for the current session

---

## Setup

### Prerequisites

- Python 3.12+
- MySQL instance
- Groq API key — [get one here](https://console.groq.com)
- Cohere API key — [get one here](https://dashboard.cohere.com) (used for reranking)

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
COHERE_API_KEY=

# Storage
VECTOR_DB_PATH=src/vector_store
```

### Run

```bash
# Start the API
uvicorn main:app --reload

# Start the Streamlit frontend (in a separate terminal)
streamlit run app.py
```

### Docker

```bash
docker compose up --build
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (async) |
| Frontend | Streamlit |
| Database | MySQL via `aiomysql` + SQLModel |
| Vector Store | ChromaDB |
| Embeddings | HuggingFace Sentence Transformers |
| Retrieval | ChromaDB (vector) + BM25 (`rank-bm25`) |
| Reranking | Cohere `rerank-english-v3.0` |
| LLM | Groq (`langchain-groq`) |
| Rate Limiting | SlowAPI |
| Auth | JWT (`python-jose`) |
| Password Hashing | Argon2 (`passlib`) |
| PDF Processing | LangChain `PyPDFLoader` |
| Package Manager | `uv` |

---

## Evaluation

The RAG pipeline was benchmarked using [RAGAS](https://docs.ragas.io) across 10 domain-specific
query–ground-truth pairs on a real PDF document. Metrics were computed using
`llama-3.3-70b-versatile` via Groq and `all-MiniLM-L6-v2` embeddings.

| Metric | Score |
|---|---|
| Faithfulness | 0.921 |
| Answer Relevancy | 0.916 |
| Context Precision | 0.928 |
| Context Recall | 0.967 |
| **Composite** | **0.933** |