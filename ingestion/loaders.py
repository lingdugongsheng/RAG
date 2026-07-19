from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from core.logger import logger

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}

def load_document(file_path: str) -> List[Document]:
    suffix = Path(file_path).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持的文件格式：{suffix}，目前支持 {SUPPORTED_SUFFIXES}")

    if suffix == ".pdf":
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path, encoding="utf-8")

    docs = loader.load()
    logger.info("document_loaded", file_path=file_path, pages_or_sections=len(docs))
    return docs