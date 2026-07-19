import hashlib
from typing import List, Set
from langchain_core.documents import Document
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from storage.graph_store import GraphStore
from core.config import settings
from core.llm import get_embeddings
from core.logger import logger
from ingestion.loaders import load_document
from ingestion.splitter import split_documents
from ingestion.graph_builder import extract_triplets

def _compute_content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def run_ingestion(file_path: str, vector_store: VectorStore, bm25_index: BM25Index,
                  graph_store: GraphStore = None, chunk_size: int = None, chunk_overlap: int = None):
    chunk_size = chunk_size or settings.ingestion.chunk_size
    chunk_overlap = chunk_overlap or settings.ingestion.chunk_overlap

    docs = load_document(file_path)
    if not docs:
        logger.warning("empty_document", file_path=file_path)
        return

    chunks = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    seen_hashes: Set[str] = set()
    unique_chunks: List[Document] = []
    for chunk in chunks:
        h = _compute_content_hash(chunk.page_content)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_chunks.append(chunk)
    logger.info("deduplication_done", original=len(chunks), unique=len(unique_chunks))

    if not unique_chunks:
        logger.warning("all_chunks_duplicated", file_path=file_path)
        return

    texts = [chunk.page_content for chunk in unique_chunks]
    metadatas = [chunk.metadata for chunk in unique_chunks]

    if graph_store and settings.ingestion.enable_graph_builder:
        triplets = extract_triplets(texts)
        graph_store.add_triplets(triplets)
        logger.info("graph_built", triplets=len(triplets))
    else:
        logger.info("graph_builder_skipped")

    try:
        embed_model = get_embeddings()
        embeddings = [embed_model.embed_query(text) for text in texts]
        logger.info("embeddings_generated", count=len(embeddings))
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e))
        raise

    vector_store.add_documents(texts, embeddings, metadatas)
    bm25_index.add_documents(texts)

    logger.info("ingestion_complete", file_path=file_path, chunks_stored=len(unique_chunks))
    return len(unique_chunks)