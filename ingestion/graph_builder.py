import json
import difflib
from typing import List, Tuple, Set
from core.llm import get_llm
from core.logger import logger
from core.config import settings


def _extract_from_text(text: str) -> List[Tuple[str, str, str]]:
    llm = get_llm()
    prompt = f"""从以下文本中抽取所有重要的实体和关系，以 JSON 数组格式输出。
每个元素为一个对象，包含 "subject"、"relation"、"object" 三个字段。
只输出 JSON 数组，不要其他内容。

文本：{text}"""

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        start = content.find('[')
        end = content.rfind(']') + 1
        if start == -1 or end <= start:
            return []
        json_str = content[start:end]
        triplets = json.loads(json_str)
        result = [(t["subject"], t["relation"], t["object"]) for t in triplets if "subject" in t]
        return result
    except Exception as e:
        logger.error("triplet_extraction_failed", error=str(e), text_preview=text[:100])
        return []


def _entity_similarity(a: str, b: str) -> float:
    a_clean = a.strip().lower()
    b_clean = b.strip().lower()
    if a_clean == b_clean:
        return 1.0
    if a_clean in b_clean or b_clean in a_clean:
        return 0.95
    return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()


def _normalize_entities(triplets: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    entities: Set[str] = set()
    for s, r, o in triplets:
        entities.add(s)
        entities.add(o)

    clusters = []
    for ent in entities:
        found = False
        for cluster in clusters:
            if _entity_similarity(ent, cluster[0]) > 0.8:
                cluster.append(ent)
                found = True
                break
        if not found:
            clusters.append([ent])

    entity_map = {}
    for cluster in clusters:
        canonical = max(cluster, key=len)
        for ent in cluster:
            entity_map[ent] = canonical

    normalized = []
    for s, r, o in triplets:
        new_s = entity_map.get(s, s)
        new_o = entity_map.get(o, o)
        normalized.append((new_s, r, new_o))

    logger.info(f"entity_normalization_done, original_unique={len(entities)}, after_clusters={len(clusters)}")
    return normalized


def extract_triplets(chunks: List[str]) -> List[Tuple[str, str, str]]:
    if not chunks:
        return []

    if not settings.ingestion.enable_graph_builder:
        logger.info("graph_builder_disabled")
        return []

    raw = []
    for chunk in chunks:
        if len(chunk.strip()) < 10:
            continue
        extracted = _extract_from_text(chunk)
        raw.extend(extracted)

    unique_raw = list(set(raw))
    logger.info(f"triplets_raw_count={len(raw)}, unique={len(unique_raw)}")

    if not unique_raw:
        return []

    normalized = _normalize_entities(unique_raw)
    return normalized