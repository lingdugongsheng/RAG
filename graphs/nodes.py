"""
自适应 Agent 图的所有节点实现。
重构点：
1. 移除全局变量，通过 LangGraph 的 config 传入依赖。
2. JSON 计划解析支持 Markdown 代码块。
3. 反思死循环保护：首次重试扩大搜索范围，二次重试强制生成。
4. 真流式支持：generate_answer 节点可标记 pending，由 API 层流式输出。
5. 配置路径更新为 settings.llm.*, settings.retrieval.* 等。
"""

from typing import Dict, Any, List, Optional
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from langchain_core.runnables import RunnableConfig

from core.config import settings
from core.llm import get_llm
from core.logger import logger
from graphs.states import AgentState
from retrieval.web_search import search_web
from retrieval.searchers import HybridSearcher
from retrieval.reranker import Reranker
from retrieval.rewriter import QueryRewriter
from retrieval.graph_retriever import GraphRetriever
from generation.generator import Generator
from core.cache import MemoryCache


# ---------- 从 config 中获取依赖的辅助函数 ----------
def _get_searcher(config: RunnableConfig) -> HybridSearcher:
    return config["configurable"]["searcher"]

def _get_graph_retriever(config: RunnableConfig) -> Optional[GraphRetriever]:
    return config["configurable"].get("graph_retriever")

def _get_reranker(config: RunnableConfig) -> Reranker:
    return config["configurable"].get("reranker", Reranker())

def _get_generator(config: RunnableConfig) -> Generator:
    return config["configurable"].get("generator", Generator())

def _get_cache(config: RunnableConfig) -> MemoryCache:
    return config["configurable"].get("cache", MemoryCache(max_size=settings.cache.max_size))

def _get_rewriter(config: RunnableConfig) -> QueryRewriter:
    return config["configurable"].get("rewriter", QueryRewriter())


# ---------- 工具调用重试 ----------
def _execute_with_retry(func, *args, max_attempts=None, **kwargs):
    attempts = max_attempts if max_attempts is not None else settings.agent.tool_retry_attempts
    last_exception = None
    for attempt in range(attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < attempts:
                logger.warning(f"tool_retry_{attempt+1}", error=str(e))
                time.sleep(settings.agent.tool_retry_delay)
            else:
                logger.error("tool_all_retries_failed", error=str(e))
                raise last_exception


def _single_local_search(query: str, searcher: HybridSearcher, top_k: int = None) -> List[Dict]:
    if top_k is None:
        top_k = settings.retrieval.top_k
    try:
        return _execute_with_retry(searcher.search, query, top_k=top_k)
    except Exception:
        logger.error("local_search_failed_finally", query=query)
        return []


def _single_web_search(query: str) -> List[Dict]:
    if not settings.agent.web_search_enabled:
        return []
    try:
        return _execute_with_retry(search_web, query)
    except Exception:
        logger.warning("web_search_failed", query=query)
        return []


def _single_graph_search(query: str, graph_retriever: GraphRetriever) -> List[Dict]:
    if not graph_retriever:
        return []
    try:
        return _execute_with_retry(graph_retriever.search, query)
    except Exception:
        logger.warning("graph_search_failed", query=query)
        return []


# ---------- 节点函数 ----------
def plan_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """生成执行计划，检查缓存。"""
    cache = _get_cache(config)
    rewriter = _get_rewriter(config)
    llm = get_llm()

    query = state["query"]
    cached = cache.get(query)
    if cached:
        logger.info("cache_hit")
        return {"answer": cached, "from_cache": True, "plan": []}

    if state.get("plan") and len(state["plan"]) > 0:
        return {}

    rewritten = state.get("rewritten_query")
    if not rewritten:
        rewritten = rewriter.rewrite(query)
        logger.info("query_rewritten_in_plan", original=query, rewritten=rewritten)

    history_text = ""
    history = state.get("chat_history", [])
    if history:
        history_text = "对话历史：\n" + "\n".join(
            [f"{role}: {content}" for role, content in history[-6:]]
        ) + "\n\n"

    extra_hint = ""
    if state.get("search_scope_expanded"):
        extra_hint = "（注意：之前本地检索信息不足，请尝试 web_search 或 graph_search）"

    prompt = f"""{history_text}你是一个任务规划助手。根据对话历史和用户当前问题，生成步骤列表。{extra_hint}
可用工具：
- local_search: 搜索本地知识库（已上传的文档）
- web_search: 联网搜索
- graph_search: 搜索知识图谱（实体关系，支持多跳推理）
- generate: 生成最终答案

**规划原则**：
1. 如果问题涉及实体之间的关系，优先使用 graph_search。
2. 其他问题优先使用 local_search。
3. 仅当本地信息不足时才考虑 web_search。
4. 多个步骤可并行（用列表包裹），例如 ["graph_search", "generate"] 或 [["local_search", "graph_search"], "generate"]。

当前问题：{query}
请输出 JSON 数组，只输出 JSON，不要其他内容。"""

    plan = ["local_search", "generate"]
    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        json_str = json_match.group(1) if json_match else content
        start = json_str.find('[')
        end = json_str.rfind(']') + 1
        if start != -1 and end > start:
            json_str = json_str[start:end]
        parsed = json.loads(json_str)

        if isinstance(parsed, list):
            plan = parsed
        else:
            logger.warning("plan_not_list", content=content)
    except Exception as e:
        logger.warning("plan_parse_failed", error=str(e), content=content[:200])

    if "generate" not in plan:
        plan.append("generate")

    logger.info("plan_generated", plan=plan)
    return {
        "plan": plan,
        "step_index": 0,
        "retry_count": state.get("retry_count", 0),
        "rewritten_query": rewritten
    }


def tool_selector(state: AgentState) -> str:
    """根据计划选择下一个工具节点。"""
    if state.get("from_cache"):
        return "end"
    plan = state.get("plan", [])
    idx = state.get("step_index", 0)
    if idx >= len(plan):
        return "prepare_docs"

    action = plan[idx]
    if isinstance(action, list):
        return "parallel_search"
    elif action == "local_search":
        return "local_search"
    elif action == "web_search" and settings.agent.web_search_enabled:
        return "web_search"
    elif action == "graph_search":
        return "graph_search"
    else:
        state["step_index"] = idx + 1
        return tool_selector(state)


def local_search_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    searcher = _get_searcher(config)
    query = state.get("rewritten_query") or state["query"]
    top_k = state.get("retrieval_top_k_override", settings.retrieval.top_k)
    docs = _single_local_search(query, searcher, top_k=top_k)
    merged = state.get("local_documents", []) + docs
    return {"local_documents": merged, "step_index": state["step_index"] + 1}


def web_search_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    query = state.get("rewritten_query") or state["query"]
    docs = _single_web_search(query)
    merged = state.get("web_documents", []) + docs
    return {"web_documents": merged, "step_index": state["step_index"] + 1}


def graph_search_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    graph_retriever = _get_graph_retriever(config)
    query = state.get("rewritten_query") or state["query"]
    docs = _single_graph_search(query, graph_retriever)
    merged = state.get("local_documents", []) + docs
    return {"local_documents": merged, "step_index": state["step_index"] + 1}


def parallel_search_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    searcher = _get_searcher(config)
    graph_retriever = _get_graph_retriever(config)

    plan = state.get("plan", [])
    idx = state.get("step_index", 0)
    if idx >= len(plan) or not isinstance(plan[idx], list):
        return {"step_index": idx + 1}

    actions = plan[idx]
    query = state.get("rewritten_query") or state["query"]
    top_k = state.get("retrieval_top_k_override", settings.retrieval.top_k)
    local_docs = state.get("local_documents", [])
    web_docs = state.get("web_documents", [])

    def run_single(action):
        if action == "local_search":
            return ("local", _single_local_search(query, searcher, top_k=top_k))
        elif action == "web_search":
            return ("web", _single_web_search(query))
        elif action == "graph_search":
            return ("local", _single_graph_search(query, graph_retriever))
        else:
            return (None, [])

    TIMEOUT = 10.0
    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        futures = {executor.submit(run_single, act): act for act in actions}
        for future in as_completed(futures):
            act = futures[future]
            try:
                typ, docs = future.result(timeout=TIMEOUT)
                if typ == "local":
                    local_docs.extend(docs)
                elif typ == "web":
                    web_docs.extend(docs)
            except TimeoutError:
                logger.error("parallel_subtask_timeout", action=act)
                future.cancel()
            except Exception as e:
                logger.error("parallel_subtask_failed", action=act, error=str(e))

    return {
        "local_documents": local_docs,
        "web_documents": web_docs,
        "step_index": idx + 1
    }


def prepare_documents(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    reranker = _get_reranker(config)
    all_docs = state.get("local_documents", []) + state.get("web_documents", [])
    if not all_docs:
        return {"final_documents": []}
    query = state.get("rewritten_query") or state["query"]
    ranked = reranker.rerank(query, all_docs, top_k=settings.retrieval.rerank_top_k)
    return {"final_documents": ranked}


def generate_answer(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """生成答案，或标记为待流式生成。"""
    stream_mode = config.get("configurable", {}).get("stream_mode", False)

    if state.get("from_cache"):
        return {}

    query = state["query"]
    docs = state.get("final_documents", [])
    history = state.get("chat_history", [])
    history_text = ""
    if history:
        history_text = "对话历史：\n" + "\n".join(
            [f"{role}: {content}" for role, content in history[-6:]]
        ) + "\n"

    if state.get("force_generate_with_warning"):
        history_text += "\n注意：请如实告知信息不足，但给出已有相关内容的总结。\n"

    if stream_mode:
        return {
            "generate_pending": True,
            "generation_params": {
                "query": query,
                "documents": docs,
                "history_text": history_text,
            }
        }
    else:
        generator = _get_generator(config)
        cache = _get_cache(config)
        result = generator.generate(query, docs, history_text)
        cache.set(query, result["answer"])
        return {
            "answer": result["answer"],
            "citation_map": result["citation_map"]
        }


def reflection_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """反思答案质量，决定是否重试。"""
    if state.get("generate_pending"):
        return {"need_retry": False}

    llm = get_llm()
    answer = state.get("answer", "")
    query = state["query"]
    retry_count = state.get("retry_count", 0)

    if retry_count >= settings.agent.max_retries:
        return {"need_retry": False}

    prompt = f"""你是一个严格的评估助手。检查以下答案是否充分回答了用户问题。
如果答案包含"抱歉"、"无法回答"等不确定表述，或缺乏具体信息，请返回 "retry"。
否则返回 "ok"。

用户问题：{query}
生成答案：{answer}

只返回 "retry" 或 "ok"："""

    try:
        resp = llm.invoke(prompt)
        verdict = (resp.content if hasattr(resp, "content") else str(resp)).strip().lower()
    except Exception:
        verdict = "ok"

    logger.info("reflection_verdict", verdict=verdict, retry_count=retry_count)

    if verdict == "retry":
        if retry_count == 0:
            return {
                "need_retry": True,
                "retry_count": retry_count + 1,
                "search_scope_expanded": True,
                "plan": [],
                "step_index": 0,
                "retrieval_top_k_override": settings.retrieval.top_k * 2
            }
        else:
            return {
                "need_retry": False,
                "force_generate_with_warning": True
            }
    return {"need_retry": False}