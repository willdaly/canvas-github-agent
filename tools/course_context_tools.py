"""Course document ingestion and retrieval backed by Docling and Chroma."""

import os
import re
from pathlib import Path
from typing import Any, Optional

from scaffolding.templates import normalize_slug


def _build_chunk_payload(section_title: str, text: str, chunk_index: int) -> dict[str, Any]:
    clean_text = text.strip()
    title = section_title.strip() or f"Chunk {chunk_index + 1}"
    if not clean_text:
        return {}
    return {
        "chunk_index": chunk_index,
        "section_title": title,
        "text": f"Section: {title}\n\n{clean_text}",
    }


def chunk_markdown_document(markdown: str, max_chars: int = 1200) -> list[dict[str, Any]]:
    """Chunk markdown content into retrieval-friendly sections."""
    normalized = markdown.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    sections: list[tuple[str, str]] = []
    current_title = "Overview"
    current_lines: list[str] = []

    for line in normalized.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_title, body))
            current_title = stripped.lstrip("#").strip() or current_title
            current_lines = []
            continue
        current_lines.append(line)

    trailing = "\n".join(current_lines).strip()
    if trailing:
        sections.append((current_title, trailing))

    if not sections:
        sections = [("Overview", normalized)]

    chunks: list[dict[str, Any]] = []
    chunk_index = 0
    for section_title, section_text in sections:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section_text) if part.strip()]
        if not paragraphs:
            paragraphs = [section_text.strip()]

        current_chunk = ""
        for paragraph in paragraphs:
            candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph
            if len(candidate) <= max_chars:
                current_chunk = candidate
                continue

            if current_chunk:
                payload = _build_chunk_payload(section_title, current_chunk, chunk_index)
                if payload:
                    chunks.append(payload)
                    chunk_index += 1

            remaining = paragraph.strip()
            while len(remaining) > max_chars:
                split_at = remaining.rfind(" ", 0, max_chars)
                if split_at < max_chars // 2:
                    split_at = max_chars
                payload = _build_chunk_payload(section_title, remaining[:split_at], chunk_index)
                if payload:
                    chunks.append(payload)
                    chunk_index += 1
                remaining = remaining[split_at:].strip()

            current_chunk = remaining

        if current_chunk:
            payload = _build_chunk_payload(section_title, current_chunk, chunk_index)
            if payload:
                chunks.append(payload)
                chunk_index += 1

    return chunks


class CourseContextTools:
    """Ingest course PDFs into Chroma and retrieve relevant assignment context."""

    def __init__(self):
        self.storage_path = Path(
            os.getenv("COURSE_CONTEXT_CHROMA_PATH", ".chroma").strip() or ".chroma"
        ).expanduser()
        self.collection_name = (
            os.getenv("COURSE_CONTEXT_COLLECTION", "course-context").strip() or "course-context"
        )
        self.default_limit = max(
            int(os.getenv("COURSE_CONTEXT_DEFAULT_LIMIT", "5") or "5"),
            1,
        )
        self.chunk_size = max(
            int(os.getenv("COURSE_CONTEXT_CHUNK_SIZE", "1200") or "1200"),
            400,
        )

    @staticmethod
    def _require_docling():
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as error:
            raise RuntimeError(
                "Course context ingestion requires docling. Install project dependencies first."
            ) from error
        return DocumentConverter

    @staticmethod
    def _require_chroma():
        try:
            import chromadb
        except ImportError as error:
            raise RuntimeError(
                "Course context retrieval requires chromadb. Install project dependencies first."
            ) from error
        return chromadb

    def _get_collection(self):
        chromadb = self._require_chroma()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        try:
            client = chromadb.PersistentClient(path=str(self.storage_path))
        except BaseException as error:
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            raise RuntimeError(
                "Course context retrieval unavailable: local Chroma store could not be opened."
            ) from error
        return client.get_or_create_collection(name=self.collection_name)

    def _parse_pdf(self, file_path: str) -> dict[str, Any]:
        path = Path(file_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Course document not found: {path}")

        DocumentConverter = self._require_docling()
        converter = DocumentConverter()
        result = converter.convert(path)
        markdown = result.document.export_to_markdown().strip()
        chunks = chunk_markdown_document(markdown, max_chars=self.chunk_size)
        if not chunks:
            raise ValueError("No retrievable text could be extracted from the document.")

        return {
            "document_id": normalize_slug(path.stem) or "course-document",
            "document_name": path.name,
            "source_path": str(path),
            "chunks": chunks,
        }

    def ingest_pdf(
        self,
        course_id: int,
        file_path: str,
        document_name: Optional[str] = None,
    ) -> dict[str, Any]:
        parsed = self._parse_pdf(file_path)
        if document_name:
            parsed["document_name"] = document_name.strip()
            parsed["document_id"] = normalize_slug(Path(document_name).stem) or parsed["document_id"]

        collection = self._get_collection()
        ids: list[str] = []
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []
        course_key = str(course_id)

        for chunk in parsed["chunks"]:
            chunk_id = f"course-{course_key}:{parsed['document_id']}:{int(chunk['chunk_index']):04d}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(
                {
                    "course_id": course_key,
                    "document_id": parsed["document_id"],
                    "document_name": parsed["document_name"],
                    "source_path": parsed["source_path"],
                    "section_title": chunk["section_title"],
                    "chunk_index": int(chunk["chunk_index"]),
                }
            )

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        return {
            "status": "ingested",
            "course_id": course_id,
            "document_id": parsed["document_id"],
            "document_name": parsed["document_name"],
            "chunk_count": len(documents),
            "collection": self.collection_name,
            "storage_path": str(self.storage_path),
        }

    def list_documents(self, course_id: int) -> list[dict[str, Any]]:
        collection = self._get_collection()
        records = collection.get(where={"course_id": str(course_id)}, include=["metadatas"])
        grouped: dict[str, dict[str, Any]] = {}

        for metadata in records.get("metadatas") or []:
            if not metadata:
                continue
            document_id = str(metadata.get("document_id") or "unknown-document")
            entry = grouped.setdefault(
                document_id,
                {
                    "course_id": course_id,
                    "document_id": document_id,
                    "document_name": metadata.get("document_name"),
                    "source_path": metadata.get("source_path"),
                    "chunk_count": 0,
                },
            )
            entry["chunk_count"] += 1

        return sorted(grouped.values(), key=lambda item: item.get("document_name") or item["document_id"])

    def search_context(self, course_id: int, query: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
        clean_query = query.strip()
        if not clean_query:
            return []

        if not self.list_documents(course_id):
            return []

        collection = self._get_collection()
        n_results = max(limit or self.default_limit, 1)
        raw = collection.query(
            query_texts=[clean_query],
            n_results=n_results,
            where={"course_id": str(course_id)},
        )

        raw_documents = (raw.get("documents") or [[]])[0]
        raw_metadatas = (raw.get("metadatas") or [[]])[0]
        raw_distances = (raw.get("distances") or [[]])[0]
        raw_ids = (raw.get("ids") or [[]])[0]

        results: list[dict[str, Any]] = []
        for index, text in enumerate(raw_documents):
            metadata = raw_metadatas[index] if index < len(raw_metadatas) else {}
            results.append(
                {
                    "id": raw_ids[index] if index < len(raw_ids) else None,
                    "course_id": course_id,
                    "document_id": metadata.get("document_id"),
                    "document_name": metadata.get("document_name"),
                    "source_path": metadata.get("source_path"),
                    "section_title": metadata.get("section_title"),
                    "chunk_index": metadata.get("chunk_index"),
                    "distance": raw_distances[index] if index < len(raw_distances) else None,
                    "text": text,
                }
            )

        return results