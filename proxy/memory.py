import json
import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import Optional
from .config import resolve_path

logger = logging.getLogger(__name__)


def _create_embedding_function():
    """Create best available embedding function, preferring offline options."""
    # Try ONNX first (bundled, no network needed)
    try:
        ef = embedding_functions.ONNXMiniLM_L6_V2()
        logger.info("Memory: using ONNX embedding (offline)")
        return ef
    except Exception:
        pass

    # Fall back to DefaultEmbeddingFunction (bundled with chromadb)
    try:
        ef = embedding_functions.DefaultEmbeddingFunction()
        logger.info("Memory: using default embedding")
        return ef
    except Exception:
        pass

    # Last resort — SentenceTransformer (needs network on first run)
    try:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        logger.info("Memory: using SentenceTransformer embedding")
        return ef
    except Exception as e:
        logger.error(f"Memory: no embedding function available: {e}")
        raise


class Memory:
    def __init__(self, chroma_path: str):
        self.db_path = str(resolve_path(chroma_path))
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.ef = _create_embedding_function()
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.collection = self.client.get_collection(
                "conversations", embedding_function=self.ef
            )
        except Exception:
            self.collection = self.client.create_collection(
                "conversations", embedding_function=self.ef
            )

    def add(self, request_id: str, messages: list[dict], response: Optional[dict] = None):
        user_text = " ".join(
            m.get("content", "") for m in messages
            if isinstance(m.get("content"), str) and m.get("role") == "user"
        )
        if not user_text.strip():
            return

        metadata = {
            "request_id": request_id,
            "message_count": len(messages),
            "has_response": response is not None,
        }

        self.collection.add(
            ids=[request_id],
            documents=[user_text],
            metadatas=[metadata],
        )

    def search(self, query: str, limit: int = 20) -> list[dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        output = []
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "request_id": doc_id,
                "document": results["documents"][0][i] if results["documents"] else "",
                "distance": results["distances"][0][i] if results["distances"] else 0,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            })
        return output
