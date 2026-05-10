"""Knowledge Hub helpers for Qdrant-backed book search and ingestion."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


DEFAULT_COLLECTION = "valtyk_knowledge"
DEFAULT_QDRANT_URL = "http://qdrant:6333"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
MAX_SEARCH_LIMIT = 12
MAX_CHUNKS_PER_UPSERT = 64


class KnowledgeError(RuntimeError):
    """Raised for recoverable Knowledge Hub errors."""


@dataclass(frozen=True)
class KnowledgeConfig:
    qdrant_url: str
    api_key: str
    collection: str = DEFAULT_COLLECTION
    embedding_model: str = DEFAULT_EMBEDDING_MODEL

    @classmethod
    def from_env(cls) -> "KnowledgeConfig":
        api_key = (
            os.environ.get("QDRANT_API_KEY")
            or os.environ.get("QDRANT__SERVICE__API_KEY")
            or ""
        ).strip()
        return cls(
            qdrant_url=(os.environ.get("QDRANT_URL") or DEFAULT_QDRANT_URL).strip().rstrip("/"),
            api_key=api_key,
            collection=(os.environ.get("QDRANT_KNOWLEDGE_COLLECTION") or DEFAULT_COLLECTION).strip(),
            embedding_model=(os.environ.get("OPENAI_EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL).strip(),
        )

    def require_ready(self) -> None:
        if not self.qdrant_url:
            raise KnowledgeError("QDRANT_URL no configurado")
        if not self.api_key:
            raise KnowledgeError("QDRANT_API_KEY no configurado")
        if not self.collection:
            raise KnowledgeError("QDRANT_KNOWLEDGE_COLLECTION no configurado")


class QdrantKnowledgeClient:
    def __init__(self, config: KnowledgeConfig | None = None, timeout: int = 30):
        self.config = config or KnowledgeConfig.from_env()
        self.timeout = timeout
        self.config.require_ready()

    @property
    def headers(self) -> dict[str, str]:
        return {"api-key": self.config.api_key, "content-type": "application/json"}

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.config.qdrant_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise KnowledgeError(f"Qdrant no disponible: {exc}") from exc
        if resp.status_code >= 400:
            raise KnowledgeError(f"Qdrant {resp.status_code}: {resp.text[:220]}")
        if not resp.text:
            return {}
        return resp.json()

    def collection_info(self) -> dict[str, Any]:
        return self._request("GET", f"/collections/{quote_collection(self.config.collection)}").get("result", {})

    def scroll(
        self,
        *,
        limit: int = 256,
        offset: Any = None,
        payload_filter: dict[str, Any] | None = None,
        with_payload: bool | dict[str, Any] = True,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "limit": max(1, min(1024, int(limit or 256))),
            "with_payload": with_payload,
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset
        if payload_filter:
            body["filter"] = payload_filter
        return self._request("POST", f"/collections/{quote_collection(self.config.collection)}/points/scroll", body).get("result", {})

    def count(self, payload_filter: dict[str, Any] | None = None) -> int:
        body: dict[str, Any] = {"exact": True}
        if payload_filter:
            body["filter"] = payload_filter
        result = self._request("POST", f"/collections/{quote_collection(self.config.collection)}/points/count", body).get("result", {})
        return int(result.get("count") or 0)

    def search(
        self,
        vector: list[float],
        *,
        limit: int = 6,
        payload_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "vector": vector,
            "limit": max(1, min(MAX_SEARCH_LIMIT, int(limit or 6))),
            "with_payload": True,
            "with_vector": False,
        }
        if payload_filter:
            body["filter"] = payload_filter
        return self._request("POST", f"/collections/{quote_collection(self.config.collection)}/points/search", body).get("result", [])

    def upsert_points(self, points: list[dict[str, Any]]) -> None:
        if not points:
            return
        for start in range(0, len(points), MAX_CHUNKS_PER_UPSERT):
            batch = points[start : start + MAX_CHUNKS_PER_UPSERT]
            self._request(
                "PUT",
                f"/collections/{quote_collection(self.config.collection)}/points?wait=true",
                {"points": batch},
            )

    def delete_by_filter(self, payload_filter: dict[str, Any]) -> None:
        self._request(
            "POST",
            f"/collections/{quote_collection(self.config.collection)}/points/delete?wait=true",
            {"filter": payload_filter},
        )


def quote_collection(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def stable_book_id(collection: str, title: str, category: str) -> str:
    raw = f"{collection}|{normalize_text(title).lower()}|{normalize_text(category).lower()}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:28]


def stable_point_id(collection: str, title: str, category: str, chunk_index: int, text: str) -> str:
    raw = f"{collection}|{title}|{category}|{chunk_index}|{normalize_text(text)}"
    digest = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def payload_book_title(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    return normalize_text(metadata.get("book_title") or metadata.get("title") or payload.get("book_title") or "Unknown")


def payload_category(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    return normalize_text(metadata.get("category") or payload.get("category") or "General")


def payload_content(payload: dict[str, Any], limit: int = 420) -> str:
    content = normalize_text(payload.get("content") or payload.get("text") or "")
    return content[:limit] + ("..." if len(content) > limit else "")


def book_filter(title: str, category: str | None = None) -> dict[str, Any]:
    must: list[dict[str, Any]] = [{"key": "metadata.book_title", "match": {"value": title}}]
    if category:
        must.append({"key": "metadata.category", "match": {"value": category}})
    return {"must": must}


def search_filter(category: str | None = None, book_title: str | None = None) -> dict[str, Any] | None:
    must: list[dict[str, Any]] = []
    if category:
        must.append({"key": "metadata.category", "match": {"value": category}})
    if book_title:
        must.append({"key": "metadata.book_title", "match": {"value": book_title}})
    return {"must": must} if must else None


def scan_book_index(
    client: QdrantKnowledgeClient,
    *,
    page_limit: int = 512,
    max_points: int = 300_000,
) -> dict[str, dict[str, Any]]:
    books: dict[str, dict[str, Any]] = {}
    offset = None
    scanned = 0
    while True:
        result = client.scroll(
            limit=page_limit,
            offset=offset,
            with_payload={"include": ["content", "metadata.book_title", "metadata.category", "metadata.source", "metadata.blobType"]},
        )
        points = result.get("points") or []
        if not points:
            break
        for point in points:
            payload = point.get("payload") or {}
            title = payload_book_title(payload)
            category = payload_category(payload)
            book_id = stable_book_id(client.config.collection, title, category)
            item = books.setdefault(
                book_id,
                {
                    "bookId": book_id,
                    "title": title,
                    "category": category,
                    "collection": client.config.collection,
                    "chunksCount": 0,
                    "sample": "",
                    "source": ((payload.get("metadata") or {}).get("source") or ""),
                },
            )
            item["chunksCount"] += 1
            if not item["sample"]:
                item["sample"] = payload_content(payload, limit=320)
        scanned += len(points)
        offset = result.get("next_page_offset")
        if not offset or scanned >= max_points:
            break
    return books


def extract_pdf_text(path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - dependency guard.
        raise KnowledgeError("pypdf no instalado") from exc

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts).strip()


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    clean = normalize_text(text)
    if not clean:
        return []
    chunk_size = max(400, int(chunk_size or 1200))
    overlap = max(0, min(int(overlap or 0), chunk_size // 2))
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        if end < len(clean):
            boundary = max(clean.rfind(". ", start, end), clean.rfind("? ", start, end), clean.rfind("! ", start, end))
            if boundary > start + chunk_size * 0.55:
                end = boundary + 1
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def embed_texts(texts: list[str], *, model: str = DEFAULT_EMBEDDING_MODEL) -> list[list[float]]:
    if not texts:
        return []
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - dependency guard.
        raise KnowledgeError("openai package no instalado") from exc
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise KnowledgeError("OPENAI_API_KEY no configurado")
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def build_points(
    *,
    collection: str,
    title: str,
    category: str,
    chunks: list[str],
    vectors: list[list[float]],
    source: str,
    start_index: int = 0,
) -> list[dict[str, Any]]:
    if len(chunks) != len(vectors):
        raise KnowledgeError("chunks y vectores no coinciden")
    points: list[dict[str, Any]] = []
    for offset, (chunk, vector) in enumerate(zip(chunks, vectors)):
        index = start_index + offset
        points.append(
            {
                "id": stable_point_id(collection, title, category, index, chunk),
                "vector": vector,
                "payload": {
                    "content": chunk,
                    "metadata": {
                        "book_title": title,
                        "category": category,
                        "source": source,
                        "blobType": "application/pdf",
                        "chunk_index": index,
                    },
                },
            }
        )
    return points


def safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
