from typing import List, Dict
from ddgs import DDGS
from core.logger import logger

def search_web(query: str, max_results: int = 3) -> List[Dict]:
    """使用 DuckDuckGo 进行文本搜索，返回文档列表"""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        docs = []
        for r in results:
            docs.append({
                "text": r.get("body", ""),
                "metadata": {
                    "source": r.get("href", ""),
                    "title": r.get("title", "")
                }
            })
        return docs