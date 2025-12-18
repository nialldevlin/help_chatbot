"""Lightweight RAG utilities (embeddings + vector store + retrieval)."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from math import sqrt
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib import request as urlrequest
from urllib.error import URLError

logger = logging.getLogger(__name__)


# ---------- Embeddings ----------


class OllamaEmbeddingProvider:
    """Call Ollama's /api/embeddings endpoint."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.model = model
        host = os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
        resolved = base_url or _normalize_ollama_base(host)
        self.base_url = resolved.rstrip("/")
        env_timeout = os.environ.get("OLLAMA_EMBED_TIMEOUT")
        if env_timeout:
            try:
                timeout = int(env_timeout)
            except Exception:
                timeout = timeout
        self.timeout = timeout or 60

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        batch_size = 100
        total = len(texts)

        for batch_start in range(0, total, batch_size):
            batch = texts[batch_start : batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            batch_total = (total - 1) // batch_size + 1

            # Show progress only for large batches
            if batch_total > 1:
                print(f"  Embedding batch {batch_num}/{batch_total}...")

            for text in batch:
                payload = json.dumps({"model": self.model, "prompt": text}).encode("utf-8")
                req = urlrequest.Request(
                    self.base_url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                        data = json.loads(resp.read().decode("utf-8")) if resp else {}
                except URLError as exc:
                    raise RuntimeError(f"Ollama embedding request failed: {exc}") from exc
                vec = _parse_embedding_response(data)
                if vec is not None:
                    vectors.append(vec)

        return vectors


def _parse_embedding_response(data: Any) -> Optional[List[float]]:
    if not data:
        return None
    if isinstance(data, dict) and "embedding" in data:
        return data["embedding"]
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        first = data["data"][0] if data["data"] else None
        if isinstance(first, dict) and "embedding" in first:
            return first["embedding"]
    return None


def _normalize_ollama_base(host: str) -> str:
    """Normalize OLLAMA_HOST to a full embeddings URL."""
    h = host.strip()
    if not h.startswith("http://") and not h.startswith("https://"):
        h = f"http://{h}"
    h = h.rstrip("/")
    return f"{h}/api/embeddings"


# ---------- Vector store ----------


@dataclass
class Chunk:
    id: str
    path: str
    start_line: int
    end_line: int
    text: str
    embedding: List[float]
    score: float = 0.0
    modified_time: float = 0.0


def get_rag_index_path(workspace_root: str) -> str:
    """Get RAG index path as hidden file in workspace."""
    return os.path.join(workspace_root, ".ask_rag_index.json")


class SimpleVectorStore:
    """JSON-backed vector store at .agent_engine/rag_index.json."""

    def __init__(self, path: str | None = None) -> None:
        if path is None:
            path = get_rag_index_path(os.getcwd())
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def load(self) -> List[Chunk]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Chunk(**item) for item in data]

    def save(self, chunks: Iterable[Chunk]) -> None:
        serializable = [
            {
                "id": c.id,
                "path": c.path,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "text": c.text,
                "embedding": c.embedding,
                "score": c.score,
                "modified_time": c.modified_time,
            }
            for c in chunks
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)


# ---------- Retriever ----------


class Retriever:
    def __init__(
        self,
        workspace_root: str,
        embedder: OllamaEmbeddingProvider,
        store: SimpleVectorStore,
        include_ext: Optional[Sequence[str]] = None,
        chunk_lines: int = 120,
    ) -> None:
        self.workspace_root = workspace_root
        self.embedder = embedder
        self.store = store
        self.include_ext = include_ext or [".py", ".md", ".txt", ".json", ".yaml", ".yml"]
        self.chunk_lines = chunk_lines

    def build_index(self) -> List[Chunk]:
        chunks: List[Chunk] = []
        for root, _, files in os.walk(self.workspace_root):
            if ".git" in root or "venv" in root or "__pycache__" in root:
                continue
            for fname in files:
                if not any(fname.endswith(ext) for ext in self.include_ext):
                    continue
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, self.workspace_root)
                modified_time = os.path.getmtime(path)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                for i in range(0, len(lines), self.chunk_lines):
                    chunk_lines = lines[i : i + self.chunk_lines]
                    text = "".join(chunk_lines)
                    if not text.strip():
                        continue
                    chunks.append(
                        Chunk(
                            id=f"{rel}:{i+1}-{min(i+self.chunk_lines,len(lines))}",
                            path=rel,
                            start_line=i + 1,
                            end_line=min(i + self.chunk_lines, len(lines)),
                            text=text,
                            embedding=[],
                            modified_time=modified_time,
                        )
                    )

        embeddings = self.embedder.embed([c.text for c in chunks])
        for chunk, vec in zip(chunks, embeddings):
            chunk.embedding = vec

        self.store.save(chunks)
        return chunks

    def build_index_incremental(self) -> List[Chunk]:
        """Build or update index, skipping unchanged files."""
        chunks: List[Chunk] = []
        existing_store = self.store.load()

        # Group existing chunks by file path and track mtimes
        indexed_mtimes: Dict[str, float] = {}
        for chunk in existing_store:
            if chunk.path not in indexed_mtimes:
                indexed_mtimes[chunk.path] = chunk.modified_time

        new_or_modified: List[Chunk] = []

        for root, _, files in os.walk(self.workspace_root):
            if any(skip in root for skip in [".git", "venv", "__pycache__"]):
                continue

            for fname in files:
                if not any(fname.endswith(ext) for ext in self.include_ext):
                    continue

                path = os.path.join(root, fname)
                rel = os.path.relpath(path, self.workspace_root)
                current_mtime = os.path.getmtime(path)

                # Check if file is already indexed and unchanged
                if rel in indexed_mtimes:
                    old_mtime = indexed_mtimes[rel]
                    if current_mtime <= old_mtime:
                        # Unchanged - reuse ALL existing chunks from this file
                        chunks.extend([c for c in existing_store if c.path == rel])
                        continue

                # File is new or modified - re-chunk and mark for re-embedding
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                for i in range(0, len(lines), self.chunk_lines):
                    chunk_lines = lines[i : i + self.chunk_lines]
                    text = "".join(chunk_lines)
                    if not text.strip():
                        continue

                    new_chunk = Chunk(
                        id=f"{rel}:{i+1}-{min(i+self.chunk_lines, len(lines))}",
                        path=rel,
                        start_line=i + 1,
                        end_line=min(i + self.chunk_lines, len(lines)),
                        text=text,
                        embedding=[],
                        modified_time=current_mtime,
                    )
                    chunks.append(new_chunk)
                    new_or_modified.append(new_chunk)

        # Only embed new/modified chunks
        if new_or_modified:
            embeddings = self.embedder.embed([c.text for c in new_or_modified])
            for chunk, embedding in zip(new_or_modified, embeddings):
                chunk.embedding = embedding

        self.store.save(chunks)
        return chunks

    def _maybe_load_index(self) -> List[Chunk]:
        chunks = self.store.load()
        if not chunks:
            chunks = self.build_index()
        return chunks

    def retrieve(self, query: str, top_k: int = 6) -> List[Chunk]:
        chunks = self._maybe_load_index()
        query_vecs = self.embedder.embed([query])
        if not query_vecs:
            return []
        qv = query_vecs[0]
        for chunk in chunks:
            chunk.score = cosine_similarity(qv, chunk.embedding)
        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
        return ranked[:top_k]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
