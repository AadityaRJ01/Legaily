"""
Project-relative paths for legaily-doc-ai server scripts.
Works on Windows, Linux, and macOS — no machine-specific absolute paths.
"""
from pathlib import Path

# legaily-doc-ai/server/
SERVER_ROOT = Path(__file__).resolve().parent

# legaily/ (repo root containing BharatLAW, src, legailybackend, etc.)
PROJECT_ROOT = SERVER_ROOT.parent.parent

BHARAT_LAW_DATA_DIR = PROJECT_ROOT / "BharatLAW" / "data"
LEGAL_STATUTES_INDEX_DIR = SERVER_ROOT / "legal_statutes_index"
IPC_INDEX_DIR = SERVER_ROOT / "ipc_index"
IPC_INDEX_SAMPLE_DIR = SERVER_ROOT / "ipc_index_sample"
IPC_LAW_FILE = BHARAT_LAW_DATA_DIR / "ipc_law.txt"
