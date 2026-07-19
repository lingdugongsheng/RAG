from typing import List, Dict
from core.config import settings
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from retrieval.fusion import rrf_fusion
from retrieval.graph_retriever import GraphRetriever
from core.llm import get_embeddings
from core.logger import logger

class HybridSearcher:
    def __init__(self, vector_store: VectorStore, bm25_index: BM25Index, graph_retriever: GraphRetriever = None):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.graph_retriever = graph_retriever
        self.embeddings = get_embeddings()

    def search(self, query: str, top_k: int = None, fusion_k: int = None) -> List[Dict]:
        top_k = top_k or settings.retrieval.top_k
        fusion_k = fusion_k or settings.retrieval.fusion_k

        query_embedding = self.embeddings.embed_query(query)
        vector_results = self.vector_store.search(query_embedding, top_k=top_k)
        logger.debug("vector_search_done", count=len(vector_results))

        bm25_results = self.bm25_index.search(query, top_k=top_k)
        logger.debug("bm25_search_done", count=len(bm25_results))

        graph_results = []
        if self.graph_retriever:
            graph_results = self.graph_retriever.search(query, top_k=top_k)
            logger.debug("graph_search_done", count=len(graph_results))

        all_lists = [lst for lst in [vector_results, bm25_results, graph_results] if lst]
        if not all_lists:
            return []
        combined = all_lists[0]
        for lst in all_lists[1:]:
            combined = rrf_fusion(combined, lst, k=fusion_k, top_k=top_k)

        logger.info("hybrid_search_done", query=query, result_count=len(combined))
        return combined