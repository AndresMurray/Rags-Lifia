"""
title: Seven Wonders RAG (Real Dataset + PGVector)
author: Lifia-RAG
date: 2026-04-07
version: 2.0
license: MIT
description: Downloads Seven Wonders from Hugging Face and indexes them in pgvector for real RAG.
requirements: requests,pydantic,psycopg[binary]
"""

import hashlib
import json
import os
from typing import Any, Dict, List

import psycopg
import requests
from pydantic import BaseModel, Field


class Pipeline:
	class Valves(BaseModel):
		OLLAMA_BASE_URL: str = Field(default=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
		CHAT_MODEL: str = Field(default=os.getenv("CHAT_MODEL", "llama3"))
		EMBEDDING_MODEL: str = Field(default=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"))
		DATASET_URL: str = Field(
			default=os.getenv(
				"DATASET_URL",
				"https://datasets-server.huggingface.co/rows"
				"?dataset=bilgeyucel/seven-wonders&config=default&split=train&offset=0&length=100",
			)
		)
		VDB_HOST: str = Field(default=os.getenv("VDB_HOST", "vdb"))
		VDB_PORT: int = Field(default=int(os.getenv("VDB_PORT", "5432")))
		VDB_DBNAME: str = Field(default=os.getenv("VDB_DBNAME", "postgres"))
		VDB_USER: str = Field(default=os.getenv("VDB_USER", "postgres"))
		VDB_PASSWORD: str = Field(default=os.getenv("VDB_PASSWORD", "pass456"))
		TOP_K: int = Field(default=4)
		MAX_CONTEXT_CHARS: int = Field(default=5000)
		REQUEST_TIMEOUT_SECONDS: int = Field(default=450)

	def __init__(self):
		self.id = "seven_wonders_rag"
		self.name = "Seven Wonders RAG"
		self.valves = self.Valves()
		self._session = requests.Session()

	async def on_startup(self):
		try:
			self._sync_dataset_to_pgvector()
		except Exception:
			# Preventing startup crash keeps Pipelines online so model can still be selected,
			# and sync is retried on each user request.
			return

	async def on_shutdown(self):
		self._session.close()

	def _get_conn(self):
		return psycopg.connect(
			host=self.valves.VDB_HOST,
			port=self.valves.VDB_PORT,
			dbname=self.valves.VDB_DBNAME,
			user=self.valves.VDB_USER,
			password=self.valves.VDB_PASSWORD,
		)

	def _ollama_embedding(self, text: str) -> List[float]:
		# Try modern /api/embed first
		url_embed = f"{self.valves.OLLAMA_BASE_URL.rstrip('/')}/api/embed"
		try:
			response = self._session.post(
				url_embed,
				json={"model": self.valves.EMBEDDING_MODEL, "input": text},
				timeout=self.valves.REQUEST_TIMEOUT_SECONDS,
			)
			if response.status_code != 404:
				response.raise_for_status()
				return response.json().get("embeddings", [[]])[0]
		except Exception:
			pass

		# Fallback to legacy /api/embeddings
		url_legacy = f"{self.valves.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
		response = self._session.post(
			url_legacy,
			json={"model": self.valves.EMBEDDING_MODEL, "prompt": text},
			timeout=self.valves.REQUEST_TIMEOUT_SECONDS,
		)
		response.raise_for_status()
		return response.json().get("embedding", [])

	def _ollama_generate(self, prompt: str) -> dict:
		url = f"{self.valves.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
		payload = {
			"model": self.valves.CHAT_MODEL,
			"prompt": prompt,
			"stream": False,
			"options": {"temperature": 0.3},
		}
		response = self._session.post(
			url,
			json=payload,
			timeout=self.valves.REQUEST_TIMEOUT_SECONDS,
		)
		response.raise_for_status()
		data = response.json()

		eval_count = data.get("eval_count", 0)
		eval_duration = data.get("eval_duration", 1)
		tps = (eval_count / eval_duration) * 1_000_000_000

		return {
			"answer": data.get("response", "No se pudo generar respuesta."),
			"tps": tps
		}

	def _vector_literal(self, embedding: List[float]) -> str:
		return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

	def _fetch_remote_dataset(self) -> List[Dict[str, Any]]:
		response = self._session.get(
			self.valves.DATASET_URL,
			timeout=self.valves.REQUEST_TIMEOUT_SECONDS,
		)
		response.raise_for_status()
		payload = response.json()
		rows = payload.get("rows", [])

		docs: List[Dict[str, Any]] = []
		for row in rows:
			row_data = row.get("row", {})
			content = (row_data.get("content") or "").strip()
			if not content:
				continue
			meta = row_data.get("meta") or {}
			title = meta.get("title") or "seven_wonders_dataset"
			docs.append({"source": title, "content": content, "meta": meta})
		return docs

	def _ensure_vector_schema(self, conn, embedding_dim: int):
		with conn.cursor() as cur:
			cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
			cur.execute("DROP TABLE IF EXISTS sw_knowledge")
			cur.execute(
				f"""
				CREATE TABLE sw_knowledge (
					id BIGSERIAL PRIMARY KEY,
					source TEXT NOT NULL,
					content TEXT NOT NULL,
					content_hash TEXT NOT NULL UNIQUE,
					meta JSONB,
					embedding vector({embedding_dim}) NOT NULL,
					created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
				)
				"""
			)
			cur.execute(
				"CREATE INDEX IF NOT EXISTS sw_knowledge_embedding_idx "
				"ON sw_knowledge USING hnsw (embedding vector_cosine_ops)"
			)
			cur.execute(
				"CREATE TABLE IF NOT EXISTS sw_ingestion_state "
				"(id INT PRIMARY KEY, checksum TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
			)
		conn.commit()

	def _dataset_checksum(self, docs: List[Dict[str, Any]]) -> str:
		canonical = json.dumps(docs, sort_keys=True, ensure_ascii=True)
		return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

	def _is_dataset_current(self, conn, checksum: str) -> bool:
		with conn.cursor() as cur:
			cur.execute("SELECT checksum FROM sw_ingestion_state WHERE id = 1")
			row = cur.fetchone()
		return bool(row and row[0] == checksum)

	def _save_dataset_checksum(self, conn, checksum: str):
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO sw_ingestion_state (id, checksum, updated_at)
				VALUES (1, %s, NOW())
				ON CONFLICT (id)
				DO UPDATE SET checksum = EXCLUDED.checksum, updated_at = NOW()
				""",
				(checksum,),
			)
		conn.commit()

	def _sync_dataset_to_pgvector(self):
		docs = self._fetch_remote_dataset()
		if not docs:
			raise RuntimeError("No se descargaron documentos desde Hugging Face.")

		checksum = self._dataset_checksum(docs)

		with self._get_conn() as conn:
			with conn.cursor() as cur:
				cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
				cur.execute(
					"CREATE TABLE IF NOT EXISTS sw_ingestion_state "
					"(id INT PRIMARY KEY, checksum TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
				)
			conn.commit()

			if self._is_dataset_current(conn, checksum):
				return

			first_embedding = self._ollama_embedding(docs[0]["content"])
			if not first_embedding:
				raise RuntimeError("No se pudo generar embedding del dataset remoto.")

			embedding_dim = len(first_embedding)
			self._ensure_vector_schema(conn, embedding_dim)

			with conn.cursor() as cur:
				for idx, doc in enumerate(docs):
					embedding = first_embedding if idx == 0 else self._ollama_embedding(doc["content"])
					if not embedding:
						continue

					content_hash = hashlib.sha256(doc["content"].encode("utf-8")).hexdigest()
					cur.execute(
						"""
						INSERT INTO sw_knowledge (source, content, content_hash, meta, embedding)
						VALUES (%s, %s, %s, %s::jsonb, %s::vector)
						ON CONFLICT (content_hash) DO UPDATE
						SET source = EXCLUDED.source,
							content = EXCLUDED.content,
							meta = EXCLUDED.meta,
							embedding = EXCLUDED.embedding
						""",
						(
							doc["source"],
							doc["content"],
							content_hash,
							json.dumps(doc["meta"], ensure_ascii=True),
							self._vector_literal(embedding),
						),
					)
			conn.commit()
			self._save_dataset_checksum(conn, checksum)

	def _retrieve_context(self, query: str) -> List[Dict[str, Any]]:
		query_embedding = self._ollama_embedding(query)
		if not query_embedding:
			return []

		query_vector = self._vector_literal(query_embedding)
		with self._get_conn() as conn:
			with conn.cursor() as cur:
				cur.execute(
					"""
					SELECT source, content, 1 - (embedding <=> %s::vector) AS score
					FROM sw_knowledge
					ORDER BY embedding <=> %s::vector
					LIMIT %s
					""",
					(query_vector, query_vector, max(1, self.valves.TOP_K)),
				)
				rows = cur.fetchall()

		return [
			{
				"source": row[0],
				"content": row[1],
				"score": float(row[2]) if row[2] is not None else 0.0,
			}
			for row in rows
		]

	def _build_prompt(self, question: str, context_items: List[Dict[str, Any]]) -> str:
		context_blocks: List[str] = []
		total = 0

		for item in context_items:
			block = f"[Fuente: {item['source']}]\n{item['content']}"
			if total + len(block) > self.valves.MAX_CONTEXT_CHARS:
				break
			context_blocks.append(block)
			total += len(block)

		if not context_blocks:
			context_blocks.append("No se recupero contexto de la base vectorial.")

		context_text = "\n\n".join(context_blocks)
		return (
			"Eres un asistente RAG especializado en Seven Wonders. "
			"Responde en espanol, de forma clara, y cita la evidencia del contexto.\n\n"
			f"Contexto recuperado:\n{context_text}\n\n"
			f"Pregunta del usuario: {question}\n"
			"Respuesta:"
		)

	def pipe(
		self,
		user_message: str,
		model_id: str,
		messages: List[Dict[str, Any]],
		body: Dict[str, Any],
	) -> str:
		try:
			self._sync_dataset_to_pgvector()
			context_items = self._retrieve_context(user_message)
			prompt = self._build_prompt(user_message, context_items)
			
			result = self._ollama_generate(prompt)
			answer = result["answer"]
			tps = result["tps"]

			used_sources = sorted({item["source"] for item in context_items})
			
			metrics_footer = f"\n\n---"
			metrics_footer += f"\n⚡ Velocidad: {tps:.2f} tokens/s"
			if used_sources:
				metrics_footer += f"\n📚 Fuentes usadas: {', '.join(used_sources)}"
				
			return f"{answer}{metrics_footer}"
		except Exception as exc:  # pylint: disable=broad-except
			return f"Error en pipeline seven_wonders_rag: {exc}"

