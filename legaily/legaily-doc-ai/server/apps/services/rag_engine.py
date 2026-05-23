"""
Unified RAG layer: HuggingFace embeddings + FAISS + optional Cohere rerank.
Used by statute search (SLRE) and uploaded-document Q&A.
"""
from __future__ import annotations

import hashlib
import logging
import pickle
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

import cohere
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from apps.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_embeddings: HuggingFaceEmbeddings | None = None
_ephemeral_cache: OrderedDict[str, FAISS] = OrderedDict()


def get_embeddings(settings: Settings | None = None) -> HuggingFaceEmbeddings:
    global _embeddings
    settings = settings or get_settings()
    if _embeddings is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return _embeddings


def load_faiss_index(index_dir: Path, settings: Settings | None = None) -> FAISS:
    settings = settings or get_settings()
    index_dir = Path(index_dir)
    if not index_dir.is_dir():
        raise FileNotFoundError(
            f"FAISS index not found at {index_dir}. "
            f"Run: python ingest_legal_data.py"
        )
    embeddings = get_embeddings(settings)
    return FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )


def load_bm25_bundle(index_dir: Path) -> dict[str, Any]:
    bm25_path = Path(index_dir) / "bm25_index.pkl"
    if not bm25_path.is_file():
        raise FileNotFoundError(f"BM25 index not found at {bm25_path}")
    with open(bm25_path, "rb") as f:
        return pickle.load(f)


def save_faiss_index(vectorstore: FAISS, index_dir: Path) -> None:
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_dir))


def build_faiss_from_documents(docs, settings: Settings | None = None) -> FAISS:
    settings = settings or get_settings()
    embeddings = get_embeddings(settings)
    return FAISS.from_documents(docs, embeddings)


def build_faiss_from_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    settings: Settings | None = None,
) -> FAISS:
    settings = settings or get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text.strip())
    if not chunks:
        chunks = [text.strip()]
    embeddings = get_embeddings(settings)
    return FAISS.from_texts(chunks, embeddings)


def get_ephemeral_vectorstore(
    document_text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    cache_max: int,
    settings: Settings | None = None,
) -> FAISS:
    """LRU-cached FAISS index per document hash (for PDF Q&A)."""
    settings = settings or get_settings()
    cache_key = hashlib.sha256(document_text.encode("utf-8")).hexdigest()[:16]

    if cache_key in _ephemeral_cache:
        vs = _ephemeral_cache.pop(cache_key)
        _ephemeral_cache[cache_key] = vs
        return vs

    vs = build_faiss_from_text(
        document_text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        settings=settings,
    )
    _ephemeral_cache[cache_key] = vs
    while len(_ephemeral_cache) > cache_max:
        _ephemeral_cache.popitem(last=False)
    return vs


def retrieve_similar(
    vectorstore: FAISS,
    query: str,
    k: int,
) -> list[str]:
    docs = vectorstore.similarity_search(query, k=k)
    return [d.page_content for d in docs]


def rerank_chunks(
    co_client: cohere.ClientV2,
    query: str,
    chunks: list[str],
    *,
    model: str,
    top_n: int,
) -> list[str]:
    if not chunks:
        return []
    top_n = min(top_n, len(chunks))
    response = co_client.rerank(
        model=model,
        query=query,
        documents=chunks,
        top_n=top_n,
    )
    return [chunks[r.index] for r in response.results]


def retrieve_with_rerank(
    vectorstore: FAISS,
    query: str,
    co_client: cohere.ClientV2,
    *,
    retrieve_k: int,
    rerank_top_n: int,
    rerank_model: str,
) -> str:
    candidates = retrieve_similar(vectorstore, query, retrieve_k)
    if not candidates:
        return ""
    ranked = rerank_chunks(
        co_client,
        query,
        candidates,
        model=rerank_model,
        top_n=rerank_top_n,
    )
    return "\n\n---\n\n".join(ranked)


_STOPWORDS = frozenset(
    {
        "what", "does", "mean", "about", "this", "that", "with", "from", "have",
        "been", "were", "will", "would", "could", "should", "tell", "please",
        "document", "case", "file", "second", "third", "first", "only", "also",
        "but", "the", "pdf", "means", "mean", "your", "question", "asked",
    }
)


def _terms_from_question(question: str) -> list[str]:
    """Important tokens/acronyms from the user's question for literal PDF search."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(t: str) -> None:
        t = t.strip()
        if len(t) < 2:
            return
        key = t.lower()
        if key in seen or key in _STOPWORDS:
            return
        seen.add(key)
        terms.append(t)

    for acr in re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", question):
        add(acr)
    for word in re.findall(r"\b[A-Za-z][A-Za-z0-9&.'-]{2,}\b", question):
        add(word)
    return terms


def keyword_windows(
    full_text: str,
    question: str,
    *,
    window: int = 550,
    max_hits: int = 8,
) -> list[str]:
    """
    Find passages in the PDF text that literally contain words from the question
    (e.g. SEML, NCLAT) — works for any uploaded document.
    """
    if not full_text or not question:
        return []

    snippets: list[str] = []
    seen_span: set[tuple[int, int]] = set()

    for term in _terms_from_question(question):
        for m in re.finditer(re.escape(term), full_text, re.IGNORECASE):
            start = max(0, m.start() - window)
            end = min(len(full_text), m.end() + window)
            span_key = (start // 200, end // 200)
            if span_key in seen_span:
                continue
            seen_span.add(span_key)
            snippet = full_text[start:end].strip()
            if snippet and snippet not in snippets:
                snippets.append(snippet)
            if len(snippets) >= max_hits:
                return snippets
    return snippets


def retrieve_for_document(
    full_text: str,
    question: str,
    co_client: cohere.ClientV2,
    settings: Settings | None = None,
) -> str:
    """
    Hybrid retrieval for open-ended PDF Q&A: literal keyword hits + FAISS + rerank.
    """
    settings = settings or get_settings()
    parts: list[str] = []

    kw = keyword_windows(full_text, question)
    if kw:
        parts.append(
            "=== PDF PASSAGES (matched words from your question) ===\n"
            + "\n\n---\n\n".join(kw)
        )

    vs = get_ephemeral_vectorstore(
        full_text,
        chunk_size=settings.qa_chunk_size,
        chunk_overlap=settings.qa_chunk_overlap,
        cache_max=settings.qa_cache_max,
        settings=settings,
    )
    faiss_hits = retrieve_similar(vs, question, settings.qa_retrieve_k)
    if faiss_hits:
        ranked = rerank_chunks(
            co_client,
            question,
            faiss_hits,
            model=settings.cohere_rerank_model,
            top_n=settings.qa_rerank_top_n,
        )
        if ranked:
            parts.append(
                "=== PDF PASSAGES (semantic search) ===\n" + "\n\n---\n\n".join(ranked)
            )

    return "\n\n".join(parts) if parts else full_text[:25000]
