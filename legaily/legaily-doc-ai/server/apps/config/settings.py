"""
Central configuration — all paths, models, and RAG parameters from environment.
No machine-specific hardcoded paths.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from project_paths import (
    BHARAT_LAW_DATA_DIR,
    IPC_INDEX_DIR,
    IPC_INDEX_SAMPLE_DIR,
    IPC_LAW_FILE,
    LEGAL_STATUTES_INDEX_DIR,
    PROJECT_ROOT,
    SERVER_ROOT,
)


def _env_path(key: str, default: Path) -> Path:
    raw = os.getenv(key, "").strip()
    return Path(raw).expanduser().resolve() if raw else default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_list(key: str, default: str) -> list[str]:
    raw = os.getenv(key, default).strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


class Settings:
    # ── Paths (override via .env on any machine) ─────────────────────────────
    server_root: Path = SERVER_ROOT
    project_root: Path = PROJECT_ROOT
    data_dir: Path = _env_path("LEGAILY_DATA_DIR", BHARAT_LAW_DATA_DIR)
    statutes_index_dir: Path = _env_path(
        "LEGAILY_STATUTES_INDEX_DIR", LEGAL_STATUTES_INDEX_DIR
    )
    ipc_index_dir: Path = _env_path("LEGAILY_IPC_INDEX_DIR", IPC_INDEX_DIR)
    ipc_sample_index_dir: Path = _env_path(
        "LEGAILY_IPC_SAMPLE_INDEX_DIR", IPC_INDEX_SAMPLE_DIR
    )
    ipc_law_file: Path = _env_path("LEGAILY_IPC_LAW_FILE", IPC_LAW_FILE)
    logs_dir: Path = _env_path("LEGAILY_LOGS_DIR", SERVER_ROOT / "logs")
    kb_misses_log: Path = logs_dir / "kb_misses.log"
    uploads_dir: Path = _env_path("LEGAILY_UPLOADS_DIR", SERVER_ROOT / "uploads")

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _env_int("PORT", 8000)
    cors_origins: list[str] = _env_list("CORS_ORIGINS", "*")

    # ── Models & API keys ────────────────────────────────────────────────────
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "law-ai/InLegalBERT")
    cohere_api_key: str = os.getenv("COHERE_API_KEY", "")
    cohere_chat_model: str = os.getenv("COHERE_CHAT_MODEL", "command-a-03-2025")
    cohere_rerank_model: str = os.getenv("COHERE_RERANK_MODEL", "rerank-english-v3.0")
    slre_rerank_model: str = os.getenv("SLRE_RERANK_MODEL", "rerank-v3.5")
    slre_expand_model: str = os.getenv("SLRE_EXPAND_MODEL", "command-r7b-12-2024")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    hf_token: str = os.getenv("HF_TOKEN", "")

    # ── Statute ingest / FAISS (legal_statutes_index) ────────────────────────
    ingest_chunk_size: int = _env_int("INGEST_CHUNK_SIZE", 1200)
    ingest_chunk_overlap: int = _env_int("INGEST_CHUNK_OVERLAP", 200)

    # ── Document Q&A RAG (uploaded PDFs) ─────────────────────────────────────
    qa_full_context_limit: int = _env_int("QA_FULL_CONTEXT_LIMIT", 80000)
    qa_chunk_size: int = _env_int("QA_CHUNK_SIZE", 350)
    qa_chunk_overlap: int = _env_int("QA_CHUNK_OVERLAP", 150)
    qa_retrieve_k: int = _env_int("QA_RETRIEVE_K", 40)
    qa_rerank_top_n: int = _env_int("QA_RERANK_TOP_N", 15)
    qa_temperature: float = _env_float("QA_TEMPERATURE", 0.1)
    qa_cache_max: int = _env_int("QA_CACHE_MAX", 50)

    # ── SLRE retrieval ───────────────────────────────────────────────────────
    slre_faiss_k: int = _env_int("SLRE_FAISS_K", 10)
    slre_rerank_top_n: int = _env_int("SLRE_RERANK_TOP_N", 8)

    # ── Summarization ────────────────────────────────────────────────────────
    summary_max_chars: int = _env_int("SUMMARY_MAX_CHARS", 20000)

    def ensure_dirs(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
