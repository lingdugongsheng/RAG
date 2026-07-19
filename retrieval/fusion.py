from typing import List, Dict

def _doc_id(doc: Dict) -> str:
    source = (doc.get("metadata") or {}).get("source", "")
    text = doc.get("text", "")
    return f"{text}||{source}"

def rrf_fusion(
    list_a: List[Dict],
    list_b: List[Dict],
    k: int = 60,
    top_k: int = 10
) -> List[Dict]:
    rrf_scores = {}
    doc_map = {}

    for rank, item in enumerate(list_a):
        did = _doc_id(item)
        rrf_scores[did] = rrf_scores.get(did, 0) + 1 / (k + rank + 1)
        if did not in doc_map:
            doc_map[did] = item

    for rank, item in enumerate(list_b):
        did = _doc_id(item)
        rrf_scores[did] = rrf_scores.get(did, 0) + 1 / (k + rank + 1)
        if did not in doc_map:
            doc_map[did] = item

    sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    fused = []
    for did, score in sorted_ids[:top_k]:
        item = doc_map[did].copy()
        item["rrf_score"] = score
        fused.append(item)

    return fused