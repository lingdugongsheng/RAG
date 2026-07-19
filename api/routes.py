import os
import uuid
import tempfile
import json
import time
from threading import Thread
from typing import List, Tuple
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from graphs.agentic_rag import agentic_graph
from core.logger import logger
from ingestion.pipeline import run_ingestion
from core.config import settings

router = APIRouter()
task_store = {}
TASK_TTL = 600

def clean_expired_tasks():
    while True:
        time.sleep(300)
        now = time.time()
        expired = [tid for tid, task in task_store.items() if now - task.get("created_at", 0) > TASK_TTL]
        for tid in expired:
            del task_store[tid]

cleaner_thread = Thread(target=clean_expired_tasks, daemon=True)
cleaner_thread.start()

from retrieval.rewriter import QueryRewriter
_stream_rewriter = QueryRewriter()

class ChatRequest(BaseModel):
    query: str
    history: List[Tuple[str, str]] = []

class ChatResponse(BaseModel):
    answer: str
    from_cache: bool
    citation_map: dict

class TaskStatus(BaseModel):
    task_id: str
    status: str
    message: str = ""
    chunks_stored: int = 0

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    try:
        logger.info("chat_request_received", query=request.query)
        result = await agentic_graph.ainvoke(
            {
                "query": request.query,
                "chat_history": request.history
            },
            config={
                "configurable": {
                    "searcher": req.app.state.searcher,
                    "graph_retriever": req.app.state.graph_retriever,
                    "reranker": req.app.state.reranker,
                    "generator": req.app.state.generator,
                    "stream_mode": False
                }
            }
        )
        return ChatResponse(
            answer=result.get("answer", ""),
            from_cache=result.get("from_cache", False),
            citation_map=result.get("citation_map", {})
        )
    except Exception as e:
        logger.exception("chat_error")
        raise HTTPException(status_code=500, detail=f"生成回答时出错: {str(e)}")

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    searcher = req.app.state.searcher
    if not searcher:
        raise HTTPException(status_code=503, detail="检索服务未就绪")

    async def event_generator():
        try:
            result = await agentic_graph.ainvoke(
                {
                    "query": request.query,
                    "chat_history": request.history
                },
                config={
                    "configurable": {
                        "searcher": req.app.state.searcher,
                        "graph_retriever": req.app.state.graph_retriever,
                        "reranker": req.app.state.reranker,
                        "generator": req.app.state.generator,
                        "stream_mode": True
                    }
                }
            )
            if result.get("from_cache"):
                answer = result["answer"]
                for char in answer:
                    yield f"data: {json.dumps({'token': char})}\n\n"
                yield "data: [DONE]\n\n"
                return

            if result.get("generate_pending"):
                params = result["generation_params"]
                generator = req.app.state.generator
                from core.cache import MemoryCache
                cache = MemoryCache(max_size=settings.cache.max_size)
                full_answer = ""
                for token in generator.generate_stream(**params):
                    full_answer += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                cache.set(params["query"], full_answer)
                yield "data: [DONE]\n\n"
            else:
                answer = result.get("answer", "")
                for char in answer:
                    yield f"data: {json.dumps({'token': char})}\n\n"
                yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("stream_error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, req: Request = None):
    allowed_extensions = {".pdf", ".txt", ".md"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，仅支持 {', '.join(allowed_extensions)}")

    task_id = str(uuid.uuid4())
    task_store[task_id] = {"status": "processing", "message": "", "chunks_stored": 0, "created_at": time.time()}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
    except Exception as e:
        task_store[task_id] = {"status": "failed", "message": f"文件保存失败: {str(e)}", "chunks_stored": 0, "created_at": time.time()}
        raise HTTPException(status_code=500, detail="文件保存失败")

    def process_document(file_path: str, task_id: str):
        vs = req.app.state.vector_store
        bm = req.app.state.bm25_index
        gs = req.app.state.graph_store
        try:
            chunks_stored = run_ingestion(file_path, vs, bm, gs)
            task_store[task_id] = {"status": "completed", "message": "", "chunks_stored": chunks_stored, "created_at": time.time()}
        except Exception as e:
            logger.exception("ingestion_task_failed", task_id=task_id)
            task_store[task_id] = {"status": "failed", "message": str(e), "chunks_stored": 0, "created_at": time.time()}
        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

    background_tasks.add_task(process_document, tmp_path, task_id)
    return {"task_id": task_id, "status": "processing"}

@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(task_id=task_id, **task)