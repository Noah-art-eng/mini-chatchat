# Mini ChatChat RAG

Mini ChatChat RAG is a lightweight ChatChat-inspired RAG project that demonstrates the core workflow of knowledge base management, vector retrieval, and LLM-powered question answering.

The project supports document upload, local vector indexing, knowledge-base-grounded chat, and source chunk display in the frontend.

## Tech Stack

### Backend

- Python
- FastAPI: HTTP API server
- OpenAI Python SDK: LLM answer generation
- Sentence Transformers: text embedding generation
- FAISS: local vector similarity search
- SQLite: metadata storage for knowledge bases, files, and chunks
- pypdf: PDF text extraction
- python-dotenv: environment variable loading from `.env`

### Frontend

- HTML
- CSS
- Vanilla JavaScript
- Fetch API for backend requests
- localStorage for frontend chat history

## Features

- Knowledge-base-grounded RAG chat
- Multiple knowledge bases
- Create a knowledge base
- Switch the active knowledge base
- Upload `.txt` and `.pdf` files
- Automatically extract PDF text before indexing
- Split documents into chunks
- Generate embeddings with `all-MiniLM-L6-v2`
- Build an in-memory FAISS vector index
- Retrieve relevant chunks for each user question
- Generate answers with an OpenAI-compatible LLM when API access is available
- Display answer sources, chunk IDs, and similarity distances
- View knowledge base stats: file count, chunk count, and embedding model
- View document list
- Search documents by filename
- View chunks for each document
- Preview chunk content
- Delete documents and rebuild the index
- Manually rebuild the index

## Project Structure

```text
.
├── backend
│   ├── app.py                  # FastAPI application entry point
│   ├── rag.py                  # Document loading, chunking, indexing, retrieval, answer generation
│   ├── db.py                   # SQLite metadata storage
│   ├── services
│   │   └── kb_service.py       # Knowledge base service layer
│   └── data
│       └── {kb_name}
│           ├── content         # Source .txt files used for retrieval
│           ├── uploads         # Original uploaded files
│           └── vector_store    # Reserved for future vector store persistence
├── frontend
│   ├── index.html              # Frontend page
│   ├── app.js                  # Frontend interaction logic
│   └── style.css               # Page styles
├── requirements.txt
└── README.md
```

## Setup

Python 3.10+ is recommended.

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install fastapi uvicorn python-multipart openai python-dotenv sentence-transformers faiss-cpu numpy pypdf
```

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your OpenAI API key
```

## Run the Backend

Start the backend from the `backend` directory because the project manages knowledge base files relative to `backend/data`.

```bash
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Backend API:

```text
http://127.0.0.1:8000
```

FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

## Run the Frontend

Open a new terminal and run this from the project root:

```bash
cd frontend
python -m http.server 5500
```

Then open:

```text
http://127.0.0.1:5500
```

The frontend uses this backend URL by default:

```js
const API_BASE = "http://127.0.0.1:8000";
```

If the backend port changes, update `API_BASE` in `frontend/app.js`.

## Usage

1. Start the backend server.
2. Start the frontend server.
3. Select or create a knowledge base.
4. Upload `.txt` or `.pdf` files.
5. Wait for parsing, chunking, and indexing.
6. Ask a question in the chat input.
7. Review the generated answer and retrieved source chunks.

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/chat` | Run RAG chat against the active knowledge base |
| `POST` | `/upload` | Upload a `.txt` or `.pdf` file |
| `GET` | `/documents` | List documents in the active knowledge base |
| `DELETE` | `/documents/{filename}` | Delete a document |
| `GET` | `/stats` | Get active knowledge base stats |
| `POST` | `/reload` | Manually rebuild the index |
| `GET` | `/knowledge_bases` | List knowledge bases |
| `POST` | `/knowledge_bases` | Create a knowledge base |
| `POST` | `/switch_kb` | Switch the active knowledge base |
| `GET` | `/file_docs/{filename}` | List chunks for a file |
| `GET` | `/chunk/{chunk_id}` | Get chunk content |

## Notes

- The FAISS index is currently built in memory and rebuilt after document upload or deletion.
- `.txt` files in `backend/data/{kb_name}/content` are the main source files used for retrieval.
- SQLite stores only metadata for knowledge bases, files, and chunks. It does not store vectors.
- If the OpenAI API call fails, the backend falls back to returning the most relevant retrieved chunk when available.
