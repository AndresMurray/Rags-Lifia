"""
title: Odontología Legal RAG
author: Lifia-RAG
version: 1.0
license: MIT
description: RAG sobre documentos de odontología legal usando pgvector y Ollama.
requirements: markitdown,pdfminer.six,haystack-ai,ollama-haystack,psycopg2-binary
"""

from typing import List
from pydantic import BaseModel
import hashlib
import os
import psycopg2
from markitdown import MarkItDown
from haystack import Document
from haystack.components.preprocessors import DocumentSplitter
from haystack_integrations.components.embedders.ollama import OllamaDocumentEmbedder, OllamaTextEmbedder
from haystack_integrations.components.generators.ollama import OllamaChatGenerator
from haystack.dataclasses import ChatMessage


class Pipeline:
    class Valves(BaseModel):
        VDB_HOST: str = os.environ.get("VDB_HOST", "vdb")
        VDB_PORT: int = int(os.environ.get("VDB_PORT", "5432"))
        VDB_DB: str = os.environ.get("VDB_DBNAME", "pgvdb")
        VDB_USER: str = os.environ.get("VDB_USER", "")
        VDB_PASSWORD: str = os.environ.get("VDB_PASSWORD", "")
        OLLAMA_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
        EMBED_MODEL: str = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
        CHAT_MODEL: str = os.environ.get("CHAT_MODEL", "llama3.2")
        TOP_K: int = 4
        PDF_PATH: str = "/app/pipelines/rawdata/OdontologiaLegal2pags.pdf"

    def __init__(self):
        self.valves = self.Valves()
        self.conn = None
        self.name = "Odontología Legal RAG"

    def on_startup(self):
        self.conn = psycopg2.connect(
            host=self.valves.VDB_HOST,
            port=self.valves.VDB_PORT,
            dbname=self.valves.VDB_DB,
            user=self.valves.VDB_USER,
            password=self.valves.VDB_PASSWORD,
        )
        self._init_db()
        self._ingest_if_needed()

    def on_shutdown(self):
        if self.conn:
            self.conn.close()

    def _init_db(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS odonto_knowledge (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT,
                    embedding vector(768),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS odonto_knowledge_embedding_idx
                ON odonto_knowledge USING hnsw (embedding vector_cosine_ops)
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS odonto_ingestion_state (
                    id INT PRIMARY KEY,
                    checksum TEXT,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        self.conn.commit()

    def _file_checksum(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                h.update(block)
        return h.hexdigest()

    def _ingest_if_needed(self):
        checksum = self._file_checksum(self.valves.PDF_PATH)
        with self.conn.cursor() as cur:
            cur.execute("SELECT checksum FROM odonto_ingestion_state WHERE id = 1")
            row = cur.fetchone()
            if row and row[0] == checksum:
                return

        md = MarkItDown()
        text = md.convert(self.valves.PDF_PATH).text_content

        splitter = DocumentSplitter(split_by="word", split_length=500, split_overlap=50)
        docs = splitter.run(documents=[Document(content=text)])["documents"]

        embedder = OllamaDocumentEmbedder(
            model=self.valves.EMBED_MODEL,
            url=self.valves.OLLAMA_URL,
        )
        embedded_docs = embedder.run(documents=docs)["documents"]

        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM odonto_knowledge")
            for doc in embedded_docs:
                cur.execute(
                    "INSERT INTO odonto_knowledge (content, embedding) VALUES (%s, %s)",
                    (doc.content, doc.embedding),
                )
            cur.execute("""
                INSERT INTO odonto_ingestion_state (id, checksum, updated_at)
                VALUES (1, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET checksum = EXCLUDED.checksum, updated_at = NOW()
            """, (checksum,))
        self.conn.commit()

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> str:
        text_embedder = OllamaTextEmbedder(
            model=self.valves.EMBED_MODEL,
            url=self.valves.OLLAMA_URL,
        )
        query_embedding = text_embedder.run(text=user_message)["embedding"]

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT content FROM odonto_knowledge
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, self.valves.TOP_K))
            rows = cur.fetchall()

        context = "\n\n".join(r[0] for r in rows)
        prompt = f"""Sos un experto en odontología legal. Respondé únicamente basándote en el contexto provisto.

Contexto:
{context}

Pregunta: {user_message}

Respuesta:"""

        generator = OllamaChatGenerator(
            model=self.valves.CHAT_MODEL,
            url=self.valves.OLLAMA_URL,
        )
        response = generator.run(messages=[ChatMessage.from_user(prompt)])
        return response["replies"][0].content
