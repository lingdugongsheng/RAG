from typing import List, Dict, Tuple
from core.config import settings

def build_context(documents: List[Dict], max_tokens: int = None) -> Tuple[str, Dict[int, Dict]]:
    max_tokens = max_tokens or settings.retrieval.max_context_chars
    if not documents:
        return "暂无相关背景知识。", {}

    context_parts = []
    citation_map = {}
    current_length = 0

    for i, doc in enumerate(documents):
        text = doc.get("text", "")
        addition = f"[{i+1}] {text}\n\n"
        if current_length + len(addition) > max_tokens:
            break

        context_parts.append(addition)
        current_length += len(addition)

        meta = doc.get("metadata") or {}
        citation_map[i+1] = {
            "text": text,
            "source": meta.get("source", ""),
            "page": meta.get("page", ""),
        }

    context_text = "".join(context_parts).strip()
    return context_text, citation_map