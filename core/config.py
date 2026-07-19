from pydantic_settings import BaseSettings
from pydantic import SecretStr


class LLMSettings(BaseSettings):
    """LLM 配置，从环境变量 LLM_ 前缀读取"""
    model_config = {"env_prefix": "LLM_", "extra": "ignore"}

    api_key: SecretStr
    base_url: str
    llm_model: str
    embedding_model: str


class RetrievalSettings(BaseSettings):
    """检索配置，从环境变量 RETRIEVAL_ 前缀读取"""
    model_config = {"env_prefix": "RETRIEVAL_", "extra": "ignore"}

    top_k: int = 10
    rerank_top_k: int = 5
    fusion_k: int = 60
    max_context_chars: int = 3000


class IngestionSettings(BaseSettings):
    """摄入配置，从环境变量 INGESTION_ 前缀读取"""
    model_config = {"env_prefix": "INGESTION_", "extra": "ignore"}

    chunk_size: int = 500
    chunk_overlap: int = 50
    enable_graph_builder: bool = True


class CacheSettings(BaseSettings):
    """缓存配置，从环境变量 CACHE_ 前缀读取"""
    model_config = {"env_prefix": "CACHE_", "extra": "ignore"}

    max_size: int = 1000


class AgentSettings(BaseSettings):
    """Agent 配置，从环境变量 AGENT_ 前缀读取"""
    model_config = {"env_prefix": "AGENT_", "extra": "ignore"}

    max_retries: int = 2
    web_search_enabled: bool = True
    tool_retry_attempts: int = 2
    tool_retry_delay: float = 1.0


class AppSettings(BaseSettings):
    """应用配置，从环境变量 APP_ 前缀读取"""
    model_config = {"env_prefix": "APP_", "extra": "ignore"}

    log_level: str = "INFO"
    environment: str = "dev"


class Settings(BaseSettings):
    """顶层配置聚合"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    llm: LLMSettings = LLMSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    ingestion: IngestionSettings = IngestionSettings()
    cache: CacheSettings = CacheSettings()
    agent: AgentSettings = AgentSettings()
    app: AppSettings = AppSettings()


settings = Settings()