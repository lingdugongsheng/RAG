from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from core.config import settings


@lru_cache(maxsize=1)
def get_llm():
    return ChatOpenAI(
        model=settings.llm.llm_model,
        api_key=settings.llm.api_key.get_secret_value(),
        base_url=settings.llm.base_url,
        temperature=0.1,
        streaming=True,
    )


@lru_cache(maxsize=1)
def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.llm.embedding_model,
        api_key=settings.llm.api_key.get_secret_value(),
        base_url=settings.llm.base_url,
    )