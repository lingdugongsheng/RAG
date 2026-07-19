from typing import List, Dict
import jieba
from rank_bm25 import BM25Okapi
from core.logger import logger

class BM25Index:
    def __init__(self):
        self.texts: List[str] = []
        self._pending_texts: List[str] = []
        self.bm25 = None
        self._dirty = True

    def add_documents(self, texts: List[str]):
        if not texts:
            return
        self._pending_texts.extend(texts)
        self._dirty = True
        logger.info("bm25_documents_buffered", count=len(texts), pending=len(self._pending_texts))

    def _rebuild_if_needed(self):
        if self._dirty:
            self.texts.extend(self._pending_texts)
            self._pending_texts.clear()
            if self.texts:
                tokenized_corpus = [list(jieba.cut(text)) for text in self.texts]
                self.bm25 = BM25Okapi(tokenized_corpus)
            else:
                self.bm25 = None
            self._dirty = False
            logger.info("bm25_index_rebuilt", total_docs=len(self.texts))

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        self._rebuild_if_needed()
        if not self.bm25 or not self.texts:
            return []
        tokenized_query = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_query)
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = indexed_scores[:top_k]

        results = []
        for idx, score in top_indices:
            results.append({
                "text": self.texts[idx],
                "score": float(score)
            })
        return results

    def count(self) -> int:
        return len(self.texts) + len(self._pending_texts)