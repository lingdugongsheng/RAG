from typing import List, Dict, Iterator
from core.llm import get_llm
from core.logger import logger
from retrieval.context import build_context

class Generator:
    def __init__(self):
        self.llm = get_llm()

    def _build_prompt(self, query: str, documents: List[Dict], history_text: str = "") -> str:
        context_text, _ = build_context(documents)
        system_prompt = (
            "你是一个严谨的知识问答助手。"
            "请严格根据以下提供的背景知识回答用户问题。"
            "如果背景知识不足以回答，请如实告知。"
            "回答时请直接给出答案，不需要标注引用编号。"
        )
        if history_text:
            system_prompt = history_text + "\n" + system_prompt
        return f"{system_prompt}\n\n背景知识：\n{context_text}\n\n用户问题：{query}\n回答："

    def generate(self, query: str, documents: List[Dict], history_text: str = "") -> Dict:
        prompt = self._build_prompt(query, documents, history_text)
        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error("llm_generation_failed", error=str(e))
            answer = "抱歉，生成回答时出现错误，请稍后重试。"

        context_text, citation_map = build_context(documents)
        logger.info("generation_done", query=query, answer_length=len(answer))
        return {
            "answer": answer,
            "context": context_text,
            "citation_map": citation_map
        }

    def generate_stream(self, query: str, documents: List[Dict], history_text: str = "") -> Iterator[str]:
        prompt = self._build_prompt(query, documents, history_text)
        try:
            for chunk in self.llm.stream(prompt):
                token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if token:
                    yield token
        except Exception as e:
            logger.error("llm_stream_failed", error=str(e))
            yield "抱歉，生成回答时出现错误。"