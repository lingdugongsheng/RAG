import uuid
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from core.logger import logger

class VectorStore:
    def __init__(self, collection_name: str = "default", persist_dir: Optional[str] = None):
        if persist_dir:
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.EphemeralClient(
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info("vector_store_initialized", collection=collection_name, persist=bool(persist_dir))

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict]] = None):
        ids = [str(uuid.uuid4()) for _ in texts]
        if metadatas:
            self.collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        else:
            self.collection.add(ids=ids, embeddings=embeddings, documents=texts)
        logger.info("documents_added", count=len(texts))

    def delete_by_source(self, source: str):
        results = self.collection.get(where={"source": source})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info("documents_deleted_by_source", source=source, count=len(results["ids"]))

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        docs = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                docs.append({
                    "id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i]
                })
        return docs

    def count(self) -> int:
        return self.collection.count()