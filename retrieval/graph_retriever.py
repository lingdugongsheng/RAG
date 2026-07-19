from typing import List, Dict
from storage.graph_store import GraphStore
from core.logger import logger

class GraphRetriever:
    """基于知识图谱的检索器"""

    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索图谱中与查询相关的内容"""
        # 尝试直接匹配实体
        entities = self.graph_store.search_entity(query)
        if not entities:
            # 如果匹配不到，使用整个查询作为实体（可能不准确）
            entities = [query]
        results = []
        for ent in entities[:3]:
            neighbors = self.graph_store.get_neighbors(ent)
            results.extend(neighbors)
        logger.info("graph_retrieval_done", query=query, results=len(results))
        return results[:top_k]