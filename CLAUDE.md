# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Infrastructure ready to run private RAG (Retrieval-Augmented Generation) systems locally, without cloud dependencies. Any user can create their own RAG pipelines using any framework (HayStack, LlamaIndex, LangChain), and they live either outside `infrastructure/` or inside `infrastructure/appdata/pipelines/`.

## Stack

Five Docker services orchestrated via `docker-compose.yml`:

| Service | Port | Role |
|---------|------|------|
| **Ollama** | 11434 | Local LLM + embedding model runner (OpenAI-compatible API) |
| **PostgreSQL** | 5432 | Relational data storage |
| **pgvector** | 5433 | PostgreSQL + vector extension — semantic search store |
| **OpenWebUI** | 8180 | ChatGPT-like frontend, connects to Ollama and Pipelines |
| **Pipelines** | 9099 | Python pipeline executor for OpenWebUI |

## Commands

```bash
# Start all services
cd infrastructure
docker compose pull   # download images
docker compose up -d  # start in background

# Stop services
docker compose down

# View logs
docker compose logs -f <service>   # e.g., pipelines, open-webui
```

**No build step.** There are no test runners, linters, or CI scripts in this repo. Python scripts under `examples/` can be run directly:

```bash
cd examples/SevenWonders
pip install -r requirements.txt
python seven_wonders_ollama.py
```

## Configuration

Copy the example files before starting:

```bash
cp infrastructure/.env.example infrastructure/.env
cp infrastructure/env/db.env.example infrastructure/env/db.env
cp infrastructure/env/vdb.env.example infrastructure/env/vdb.env
cp infrastructure/env/openwebui.env.example infrastructure/env/openwebui.env
cp infrastructure/env/pipelines.env.example infrastructure/env/pipelines.env
```

The `.gitignore` tracks `*.env.example` files but ignores real `*.env` files.

## RAG Architecture

```
User (OpenWebUI :8180)
       │
       ▼
Pipelines (:9099)        ←── Python RAG pipeline
       │
       ├──► Ollama (:11434)      # embeddings + generation
       └──► pgvector (:5433)     # vector similarity search
```

**RAG flow (pipeline example)**:
1. On startup: download dataset from Hugging Face, generate embeddings via Ollama, store in pgvector with deduplication by content hash. Checksum is saved to skip re-ingestion if dataset hasn't changed.
2. On query: embed user question → cosine similarity search in pgvector (TOP_K=4) → build prompt with context → Ollama generates response → return answer + TPS metrics.

## Pipeline Interface

Pipelines must follow the OpenWebUI contract:

```python
class Pipeline:
    class Valves(BaseModel):  # configurable from UI
        ...

    def on_startup(self): ...   # called when service starts
    def on_shutdown(self): ...
    def pipe(self, user_message, model_id, messages, body) -> str: ...
```

Pipelines live in `infrastructure/appdata/pipelines/`. This directory is mounted into the `pipelines` container and hot-reloaded. Only the example file (`seven_wonders_rag.py`) is version-controlled; other files in `appdata/` are `.gitignore`d.

## pgvector Schema Pattern

```sql
-- Knowledge table
CREATE TABLE IF NOT EXISTS <prefix>_knowledge (
    id BIGSERIAL PRIMARY KEY,
    source TEXT, content TEXT, content_hash TEXT,
    meta JSONB, embedding vector(<dim>), created_at TIMESTAMPTZ
);

-- HNSW index for fast cosine search
CREATE INDEX IF NOT EXISTS <prefix>_knowledge_embedding_idx
ON <prefix>_knowledge USING hnsw (embedding vector_cosine_ops);

-- Ingestion state (checksum-based re-sync guard)
CREATE TABLE IF NOT EXISTS <prefix>_ingestion_state (
    id INT PRIMARY KEY, checksum TEXT, updated_at TIMESTAMPTZ
);
```

Embedding dimension must match the Ollama model: `nomic-embed-text` → 768, `bge-m3` → 1024.

## Adding a New RAG Pipeline

1. Create a Python file implementing the Pipeline interface above.
2. Drop it in `infrastructure/appdata/pipelines/`.
3. Configure its `Valves` from the OpenWebUI admin UI or via `pipelines.env`.
4. If it should be version-controlled, add an exception to `.gitignore` (see existing example).
