import os
from typing import List, Optional
from app.core.config import settings


class ChromaVectorStore:
    """Chroma-based vector store with embedding generation."""

    def __init__(self, persist_dir: str, collection_name: str):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._collection = None

    def _get_collection(self):
        """Lazy-init Chroma collection — ensures cosine space is used."""
        if self._collection is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings

                client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )

                # Ensure the collection uses cosine distance (not L2 default).
                # get_or_create_collection won't update metadata for existing
                # collections, so we must delete + recreate when wrong.
                try:
                    existing = client.get_collection(name=self.collection_name)
                    existing_space = (
                        existing.metadata.get("hnsw:space", "")
                        if existing.metadata else ""
                    )
                    if existing_space != "cosine":
                        import logging
                        logging.getLogger(__name__).warning(
                            "Collection '%s' uses '%s' space, not 'cosine'. "
                            "Deleting and recreating with cosine space.",
                            self.collection_name, existing_space or "l2 (default)",
                        )
                        client.delete_collection(name=self.collection_name)
                        raise ValueError("recreate")  # jump to create branch
                    self._collection = existing
                except (Exception, ValueError):
                    # Collection doesn't exist or needs recreation
                    self._collection = client.create_collection(
                        name=self.collection_name,
                        metadata={"hnsw:space": "cosine"},
                    )
            except ImportError:
                self._collection = _SimpleVectorStore()
        return self._collection

    async def add_chunks(self, chunks: List[dict]) -> None:
        """Add document chunks to vector store."""
        collection = self._get_collection()

        texts = [c["content"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Generate embeddings using sentence-transformers
        from app.services.ai.embedding_service import get_embedding_service
        emb_service = get_embedding_service()
        embeddings = await emb_service.encode(texts)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.5,
    ) -> List[dict]:
        """Search for similar documents."""
        collection = self._get_collection()

        # Generate query embedding using sentence-transformers
        from app.services.ai.embedding_service import get_embedding_service
        emb_service = get_embedding_service()
        query_embedding = await emb_service.encode_query(query)

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "ChromaDB query failed: %s. Returning empty results.", e
            )
            return []

        output = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                score = 1.0
                if results.get("distances") and results["distances"][0]:
                    dist = results["distances"][0][i]
                    # Works for both cosine [0,2] and L2 [0,2] on normalized vectors
                    score = max(0.0, 1.0 - dist / 2.0)

                output.append({
                    "content": doc,
                    "score": score,
                    "metadata": metadata,
                })

        # Filter by score threshold
        filtered = [r for r in output if r["score"] >= score_threshold]
        if output and not filtered:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(
                "All %d results below threshold %.2f (best=%.4f). "
                "Returning top-1 as fallback.",
                len(output), score_threshold, output[0]["score"],
            )
            # Return at least the best match as fallback to prevent hallucination
            return [output[0]]
        return filtered

    async def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a document."""
        collection = self._get_collection()
        try:
            # Try to delete by metadata filter
            collection.delete(where={"doc_id": document_id})
        except Exception:
            pass  # Simple store may not support metadata filtering


class _SimpleVectorStore:
    """In-memory fallback vector store (no external deps)."""
    import hashlib

    def __init__(self):
        self._documents: List[dict] = []

    def add(self, ids, embeddings, documents, metadatas):
        for i, id_ in enumerate(ids):
            self._documents.append({
                "id": id_,
                "embedding": embeddings[i] if embeddings else [],
                "document": documents[i] if documents else "",
                "metadata": metadatas[i] if metadatas else {},
            })

    def query(self, query_embeddings, n_results=5):
        if not self._documents:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        import math
        query_emb = query_embeddings[0]
        scored = []
        for doc in self._documents:
            if doc["embedding"]:
                score = _cosine_similarity(query_emb, doc["embedding"])
            else:
                score = 0.5  # Default for docs without embeddings
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:n_results]

        return {
            "documents": [[t[1]["document"] for t in top]],
            "metadatas": [[t[1]["metadata"] for t in top]],
            "distances": [[1.0 - t[0] for t in top]],
        }

    def delete(self, where=None):
        if where and "doc_id" in where:
            doc_id = where["doc_id"]
            self._documents = [d for d in self._documents if d["metadata"].get("doc_id") != doc_id]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_vector_store: Optional[ChromaVectorStore] = None


def get_vector_store() -> ChromaVectorStore:
    """Get the vector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = ChromaVectorStore(
            persist_dir=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
        )
    return _vector_store
