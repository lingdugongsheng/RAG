from typing import List, Dict, TypedDict, Optional, Tuple, Any


class AgentState(TypedDict):
    query: str
    rewritten_query: Optional[str]
    plan: List[str]
    step_index: int
    local_documents: List[Dict]
    web_documents: List[Dict]
    final_documents: List[Dict]
    answer: str
    citation_map: Dict[int, Dict]
    need_retry: bool
    retry_count: int
    from_cache: bool
    chat_history: List[Tuple[str, str]]
    search_scope_expanded: bool
    force_generate_with_warning: bool
    retrieval_top_k_override: Optional[int]
    generate_pending: bool
    generation_params: Optional[Dict[str, Any]]