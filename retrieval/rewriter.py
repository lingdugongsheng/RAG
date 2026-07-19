from core.llm import get_llm
from core.logger import logger


class QueryRewriter:
    """使用 LLM 改写用户查询，使其更适合检索"""

    def __init__(self):
        self.llm = get_llm()

    def rewrite(self, query: str) -> str:
        prompt = (
            "你是一个查询改写助手。你的任务是把用户的口语化、模糊的问题，"
            "改写成更精准、包含关键词的搜索查询。\n"
            "只输出改写后的查询，不要输出任何解释或额外内容。\n\n"
            f"用户问题：{query}\n改写后："
        )
        try:
            response = self.llm.invoke(prompt)
            rewritten = response.content.strip() if hasattr(response, "content") else str(response).strip()
            rewritten = rewritten.split("\n")[0].strip()
            logger.info("query_rewritten", original=query, rewritten=rewritten)
            return rewritten if rewritten else query
        except Exception as e:
            logger.error("query_rewrite_failed", error=str(e))
            return query