from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from server.config import EmbeddingSettings, RAGSettings
from server.models import RAGChunk
from server.rag.embedder import Embedder
from server.storage.file_store import FileStore


TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml"}
PDF_SUFFIXES = {".pdf"}
WORD_SUFFIXES = {".docx", ".doc"}
ALL_SUPPORTED_SUFFIXES = TEXT_SUFFIXES | PDF_SUFFIXES | WORD_SUFFIXES


class DocumentIndexer:
    def __init__(self, file_store: FileStore, settings: RAGSettings, embedding: EmbeddingSettings | None = None):
        self.file_store = file_store
        self.settings = settings
        self.embedder = Embedder(
            model_name=embedding.model if embedding else "BAAI/bge-small-zh-v1.5",
            device=embedding.device if embedding else "cpu",
        ) if embedding else Embedder()

    @property
    def index_path(self) -> Path:
        return self.file_store.data_dir / "index" / "docs_chunks.jsonl"

    @property
    def faiss_index_path(self) -> Path:
        return self.file_store.data_dir / "index" / "docs.faiss"

    def index_document(self, document_id: str, path: Path) -> list[RAGChunk]:
        text = self.extract_text(path)
        chunks = [
            RAGChunk(
                id=f"chunk-{uuid4().hex[:12]}",
                document_id=document_id,
                source_file=path.name,
                position=index,
                text=chunk,
            )
            for index, chunk in enumerate(self.chunk_text(text))
        ]
        if not chunks:
            return []

        existing = [chunk for chunk in self.load_chunks() if chunk.document_id != document_id]
        self.write_chunks([*existing, *chunks])
        return chunks

    def rebuild(self) -> list[RAGChunk]:
        chunks: list[RAGChunk] = []
        for path in sorted((self.file_store.data_dir / "documents").glob("*")):
            if path.is_file() and path.suffix.lower() in ALL_SUPPORTED_SUFFIXES:
                document_id = path.stem
                for index, chunk in enumerate(self.chunk_text(self.extract_text(path))):
                    chunks.append(
                        RAGChunk(
                            id=f"chunk-{uuid4().hex[:12]}",
                            document_id=document_id,
                            source_file=path.name,
                            position=index,
                            text=chunk,
                        )
                    )
        self.write_chunks(chunks)
        return chunks

    def load_chunks(self) -> list[RAGChunk]:
        if not self.index_path.exists():
            return []
        chunks: list[RAGChunk] = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                chunks.append(RAGChunk.model_validate(json.loads(line)))
        return chunks

    def write_chunks(self, chunks: list[RAGChunk]) -> None:
        lines = [json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) for chunk in chunks]
        self.file_store.write_text(self.index_path, "\n".join(lines) + ("\n" if lines else ""))
        self._rebuild_faiss(chunks)

    def extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix in PDF_SUFFIXES:
            return self._extract_pdf(path)
        if suffix in WORD_SUFFIXES:
            return self._extract_word(path)
        return ""

    def chunk_text(self, text: str) -> list[str]:
        normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not normalized:
            return []
        size = max(self.settings.chunk_size, 128)
        overlap = min(max(self.settings.chunk_overlap, 0), size // 2)
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + size, len(normalized))
            chunks.append(normalized[start:end].strip())
            if end == len(normalized):
                break
            start = end - overlap
        return [chunk for chunk in chunks if chunk]

    def _extract_pdf(self, path: Path) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n\n".join(page for page in pages if page.strip())
        except ImportError:
            return ""
        except Exception:
            return ""

    def _extract_word(self, path: Path) -> str:
        try:
            from docx import Document
            doc = Document(str(path))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n\n".join(paragraphs)
        except ImportError:
            return ""
        except Exception:
            return ""

    def _rebuild_faiss(self, chunks: list[RAGChunk]) -> None:
        if not self.embedder.available or not chunks:
            return
        try:
            import faiss
            import numpy as np

            texts = [chunk.text for chunk in chunks]
            vecs = self.embedder.encode(texts)
            dim = vecs.shape[1]

            index = faiss.IndexFlatIP(dim)
            index.add(vecs)

            self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(self.faiss_index_path))
        except Exception:
            pass
