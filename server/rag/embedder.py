from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np


class Embedder:
    """Local sentence embedding with optional sentence-transformers + FAISS.

    Falls back gracefully when dependencies are not installed, allowing the
    rest of the RAG pipeline to degrade to keyword cosine similarity.
    """

    _model: Any = None
    _loaded_model_name: str | None = None

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import faiss  # noqa: F401
                import sentence_transformers  # noqa: F401
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def _get_model(self) -> Any:
        import os
        # OMP_NUM_THREADS=1 prevents FAISS OpenMP threads from conflicting with
        # the HuggingFace Rust tokenizer on macOS ARM (causes SIGABRT/segfault)
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        cls = type(self)
        if cls._model is None or cls._loaded_model_name != self.model_name:
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(self.model_name, device=self.device)
            cls._loaded_model_name = self.model_name
        return cls._model

    def encode(self, texts: list[str]) -> "np.ndarray":
        import numpy as np
        model = self._get_model()
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32)
        return np.array(vecs, dtype=np.float32)

    def encode_single(self, text: str) -> "np.ndarray":
        return self.encode([text])[0]
