"""ChromaDB client wrapper."""

from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_chroma_client: Optional[chromadb.Client] = None
_collection: Optional[Collection] = None


async def init_chroma() -> None:
    """Initialize ChromaDB client."""
    global _chroma_client, _collection

    try:
        # Create persist directory
        persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
        persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize client
        _chroma_client = chromadb.PersistentClient(path=str(persist_dir))

        # Get or create collection
        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "ChromaDB initialized",
            collection=settings.CHROMA_COLLECTION_NAME,
            persist_dir=str(persist_dir),
        )
    except Exception as e:
        logger.error("Failed to initialize ChromaDB", error=str(e))
        raise


def get_chroma_client() -> Optional[chromadb.Client]:
    """Get ChromaDB client."""
    return _chroma_client


def get_collection() -> Optional[Collection]:
    """Get ChromaDB collection."""
    return _collection


class VectorStore:
    """Vector store for document embeddings."""

    def __init__(self, collection: Optional[Collection] = None) -> None:
        """Initialize vector store."""
        self._collection = collection or _collection

    async def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[dict]] = None,
    ) -> bool:
        """Add documents to vector store."""
        if not self._collection:
            logger.error("Collection not initialized")
            return False

        try:
            import uuid

            ids = ids or [str(uuid.uuid4()) for _ in documents]
            self._collection.add(
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas,
            )
            return True
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            return False

    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        filter_dict: Optional[dict] = None,
    ) -> List[dict]:
        """Search for similar documents."""
        if not self._collection:
            logger.error("Collection not initialized")
            return []

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_dict,
            )

            # Format results
            formatted = []
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results["documents"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })
            return formatted
        except Exception as e:
            logger.error("Search failed", error=str(e))
            return []

    async def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        if not self._collection:
            return False

        try:
            self._collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error("Delete failed", error=str(e))
            return False
