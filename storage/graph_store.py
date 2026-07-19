import networkx as nx
import os
from typing import List, Dict, Tuple
from core.logger import logger

class GraphStore:
    def __init__(self, persist_path: str = None):
        self.graph = nx.DiGraph()
        self.persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self.load()

    def add_triplet(self, subject: str, relation: str, object: str, metadata: Dict = None):
        if not self.graph.has_node(subject):
            self.graph.add_node(subject, type="entity")
        if not self.graph.has_node(object):
            self.graph.add_node(object, type="entity")
        self.graph.add_edge(subject, object, relation=relation, metadata=metadata or {})

    def add_triplets(self, triplets: List[Tuple[str, str, str]]):
        for sub, rel, obj in triplets:
            self.add_triplet(sub, rel, obj)
        logger.info("graph_triplets_added", count=len(triplets))
        self.save()

    def get_neighbors(self, entity: str, hops: int = 1) -> List[Dict]:
        if not self.graph.has_node(entity):
            return []

        results = []
        seen = set()
        for neighbor in self.graph.successors(entity):
            data = self.graph[entity][neighbor]
            text = f"{entity} {data['relation']} {neighbor}"
            if text not in seen:
                seen.add(text)
                results.append({"text": text, "metadata": {"source": "graph", "type": "triplet"}})
        for neighbor in self.graph.predecessors(entity):
            data = self.graph[neighbor][entity]
            text = f"{neighbor} {data['relation']} {entity}"
            if text not in seen:
                seen.add(text)
                results.append({"text": text, "metadata": {"source": "graph", "type": "triplet"}})

        return results[:10]

    def search_entity(self, entity: str) -> List[str]:
        matches = []
        for node in self.graph.nodes:
            if entity.lower() in node.lower():
                matches.append(node)
        return matches[:5]

    def count(self) -> int:
        return self.graph.number_of_nodes()

    def save(self):
        if self.persist_path:
            try:
                nx.write_gpickle(self.graph, self.persist_path)
                logger.info("graph_saved", path=self.persist_path)
            except Exception as e:
                logger.error("graph_save_failed", error=str(e))

    def load(self):
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                self.graph = nx.read_gpickle(self.persist_path)
                logger.info("graph_loaded", nodes=self.graph.number_of_nodes())
            except Exception as e:
                logger.error("graph_load_failed", error=str(e))
                self.graph = nx.DiGraph()