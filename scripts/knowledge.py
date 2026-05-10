"""Knowledge Hub helpers for Qdrant-backed book search and ingestion."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import uuid
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from xml.etree import ElementTree as ET

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
    return normalize_text(
        metadata.get("book_title")
        or metadata.get("bookTitle")
        or metadata.get("title")
        or metadata.get("file_name")
        or metadata.get("filename")
        or payload.get("book_title")
        or payload.get("bookTitle")
        or payload.get("title")
        or payload.get("file_name")
        or payload.get("filename")
        or "Unknown"
    )


def payload_category(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    return normalize_text(metadata.get("category") or payload.get("category") or "General")


def payload_blob_type(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") or {}
    return normalize_text(
        metadata.get("blobType")
        or metadata.get("blob_type")
        or metadata.get("mimeType")
        or metadata.get("mime_type")
        or payload.get("blobType")
        or payload.get("blob_type")
        or payload.get("mimeType")
        or payload.get("mime_type")
        or ""
    )


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
                    "blobType": payload_blob_type(payload),
                },
            )
            item["chunksCount"] += 1
            if not item["sample"]:
                item["sample"] = payload_content(payload, limit=320)
            if not item.get("blobType"):
                item["blobType"] = payload_blob_type(payload)
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


class _EpubTextParser(HTMLParser):
    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg"}:
            self._skip_depth += 1
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean = normalize_text(html.unescape(data))
        if clean:
            self.parts.append(clean)
            self.parts.append(" ")

    def text(self) -> str:
        raw = "".join(self.parts)
        lines = [normalize_text(line) for line in raw.splitlines()]
        return "\n\n".join(line for line in lines if line).strip()


def _epub_join_path(base: str, href: str) -> str:
    base_dir = str(Path(base).parent).replace("\\", "/")
    if base_dir == ".":
        base_dir = ""
    combined = f"{base_dir}/{href}" if base_dir else href
    parts: list[str] = []
    for part in unquote(combined).replace("\\", "/").split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def _epub_spine_paths(zf: zipfile.ZipFile) -> list[str]:
    try:
        container_xml = zf.read("META-INF/container.xml")
        container = ET.fromstring(container_xml)
        rootfile = container.find(".//{*}rootfile")
        opf_path = rootfile.attrib.get("full-path", "") if rootfile is not None else ""
    except Exception:
        opf_path = ""

    if not opf_path:
        return []

    try:
        package = ET.fromstring(zf.read(opf_path))
    except Exception:
        return []

    manifest: dict[str, dict[str, str]] = {}
    for item in package.findall(".//{*}manifest/{*}item"):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        if not item_id or not href:
            continue
        manifest[item_id] = {
            "href": _epub_join_path(opf_path, href),
            "media_type": item.attrib.get("media-type", ""),
            "properties": item.attrib.get("properties", ""),
        }

    ordered: list[str] = []
    for itemref in package.findall(".//{*}spine/{*}itemref"):
        item = manifest.get(itemref.attrib.get("idref") or "")
        if not item:
            continue
        media_type = item.get("media_type") or ""
        if media_type in {"application/xhtml+xml", "text/html"}:
            ordered.append(item["href"])
    return ordered


def extract_epub_text(path: str | Path) -> str:
    epub_path = Path(path)
    try:
        zf = zipfile.ZipFile(epub_path)
    except Exception as exc:
        raise KnowledgeError("EPUB invalido o corrupto") from exc

    with zf:
        names = set(zf.namelist())
        html_paths = [p for p in _epub_spine_paths(zf) if p in names]
        if not html_paths:
            html_paths = sorted(
                name for name in names
                if name.lower().endswith((".xhtml", ".html", ".htm"))
                and not name.lower().endswith(("nav.xhtml", "toc.xhtml"))
            )
        parts: list[str] = []
        for name in html_paths:
            try:
                raw = zf.read(name)
            except Exception:
                continue
            parser = _EpubTextParser()
            try:
                parser.feed(raw.decode("utf-8", errors="replace"))
                parser.close()
            except Exception:
                continue
            text = parser.text()
            if text:
                parts.append(text)
    return "\n\n".join(parts).strip()


def document_blob_type(path: str | Path, filename: str | None = None) -> str:
    value = str(filename or path or "").lower()
    if value.endswith(".epub"):
        return "application/epub+zip"
    if value.endswith(".pdf"):
        return "application/pdf"
    return "application/octet-stream"


def extract_document_text(path: str | Path, *, blob_type: str | None = None) -> str:
    kind = (blob_type or document_blob_type(path)).lower()
    suffix = Path(path).suffix.lower()
    if "epub" in kind or suffix == ".epub":
        return extract_epub_text(path)
    if "pdf" in kind or suffix == ".pdf":
        return extract_pdf_text(path)
    raise KnowledgeError("formato no soportado")


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
    blob_type: str = "application/octet-stream",
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
                        "blobType": blob_type,
                        "chunk_index": index,
                    },
                },
            }
        )
    return points


def safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
