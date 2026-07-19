from typing import List, Dict
import numpy as np
from core.config import settings
from core.llm import get_embeddings
from core.logger import logger

class Reranker:
    def __init__(self):
        self.embeddings = get_embeddings()
        logger.info("reranker_initialized", method="batch_embedding_similarity")

    def rerank(self, query: str, documents: List[Dict], top_k: int = None) -> List[Dict]:
        top_k = top_k or settings.retrieval.rerank_top_k
        if not documents:
            return []

        texts = [doc["text"] for doc in documents]
        try:
            doc_embeddings = self.embeddings.embed_documents(texts)
        except Exception as e:
            logger.error("batch_embedding_failed", error=str(e))
            return documents[:top_k]

        query_emb = np.array(self.embeddings.embed_query(query))
        scores = []
        for doc_emb in doc_embeddings:
            emb_arr = np.array(doc_emb)
            cos_sim = np.dot(query_emb, emb_arr) / (np.linalg.norm(query_emb) * np.linalg.norm(emb_arr))
            scores.append(float(cos_sim))

        for i, doc in enumerate(documents):
            doc["rerank_score"] = scores[i]

        sorted_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        logger.info("rerank_done", query=query, input_count=len(documents), output_count=min(top_k, len(sorted_docs)))
        return sorted_docs[:top_k]