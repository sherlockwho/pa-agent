from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from server.api.deps import get_document_indexer, get_document_retriever, get_document_store
from server.models import DocumentRecord, RAGSearchResult
from server.rag.indexer import DocumentIndexer
from server.rag.retriever import DocumentRetriever
from server.storage.document_store import DocumentStore

router = APIRouter()


@router.get("/", response_model=list[DocumentRecord])
def list_files(store: DocumentStore = Depends(get_document_store)) -> list[DocumentRecord]:
    return store.list()


@router.post("/", response_model=DocumentRecord, status_code=201)
def upload_file(
    upload: UploadFile = File(...),
    store: DocumentStore = Depends(get_document_store),
    indexer: DocumentIndexer = Depends(get_document_indexer),
) -> DocumentRecord:
    record = store.save_upload(upload)
    path = store.get_path(record.id)
    if path:
        indexer.index_document(record.id, path)
    return record


@router.get("/search", response_model=list[RAGSearchResult])
def search_files(
    q: str,
    top_k: int | None = None,
    retriever: DocumentRetriever = Depends(get_document_retriever),
) -> list[RAGSearchResult]:
    return retriever.search(q, top_k=top_k)


@router.post("/reindex", response_model=dict[str, int])
def reindex_files(indexer: DocumentIndexer = Depends(get_document_indexer)) -> dict[str, int]:
    chunks = indexer.rebuild()
    return {"chunks": len(chunks)}


@router.get("/{document_id}")
def download_file(document_id: str, store: DocumentStore = Depends(get_document_store)) -> FileResponse:
    path = store.get_path(document_id)
    if not path:
        raise HTTPException(status_code=404, detail="Document not found")
    filename = path.name.split("__", 1)[1] if "__" in path.name else path.name
    return FileResponse(path, filename=filename)
