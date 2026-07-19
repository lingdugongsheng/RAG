import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

from contextlib import asynccontextmanager
import uuid
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog
from core.config import settings
from core.logger import logger
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from storage.graph_store import GraphStore
from retrieval.graph_retriever import GraphRetriever
from api.routes import router

GRAPH_PERSIST_PATH = "chroma_db/graph.gpickle"
import os
os.makedirs("chroma_db", exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store = VectorStore(collection_name="rag_demo")
    bm25_index = BM25Index()
    graph_store = GraphStore(persist_path=GRAPH_PERSIST_PATH)
    graph_retriever = GraphRetriever(graph_store)
    app.state.vector_store = vector_store
    app.state.bm25_index = bm25_index
    app.state.graph_store = graph_store
    app.state.graph_retriever = graph_retriever
    logger.info("storage_initialized_empty")
    yield
    if graph_store:
        graph_store.save()
    logger.info("app_shutdown")

app = FastAPI(
    title="Advanced RAG System",
    version="0.1.0",
    description="基于智谱 AI 的生产级 RAG 智能问答系统",
    lifespan=lifespan,
)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("request_started", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_finished", status_code=response.status_code)
        return response
    finally:
        structlog.contextvars.unbind_contextvars("request_id")

@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"}
        )

app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health(request: Request):
    health_status = {"status": "ok", "checks": {}}

    vs = request.app.state.vector_store
    try:
        health_status["checks"]["chromadb"] = "ok"
        health_status["doc_count"] = vs.count()
    except Exception as e:
        health_status["checks"]["chromadb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    bm = request.app.state.bm25_index
    try:
        health_status["checks"]["bm25_index"] = "ok"
        health_status["bm25_doc_count"] = bm.count()
    except Exception as e:
        health_status["checks"]["bm25_index"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.head(
                settings.llm.base_url.rstrip("/") + "/models",
                headers={"Authorization": f"Bearer {settings.llm.api_key.get_secret_value()}"},
                timeout=5.0
            )
            if resp.status_code < 500:
                health_status["checks"]["llm_api"] = "ok"
            else:
                health_status["checks"]["llm_api"] = f"status {resp.status_code}"
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["llm_api"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    health_status["llm_model"] = settings.llm.llm_model
    health_status["embedding_model"] = settings.llm.embedding_model
    return health_status