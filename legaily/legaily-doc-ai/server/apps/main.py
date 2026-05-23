import sys
from pathlib import Path

_server_root = Path(__file__).resolve().parent.parent
if str(_server_root) not in sys.path:
    sys.path.insert(0, str(_server_root))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

# Load environment variables from server/.env
load_dotenv(_server_root / ".env")

logger = logging.getLogger(__name__)

from apps.routes import router

# ---------------------------------------------------------------------------
# Startup: pre-warm SLRE singleton so the first user request is instant
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server startup: pre-warming SLRE models...")
    try:
        from apps.services.slre import _get_embeddings, _get_vectorstore
        _get_embeddings()
        vs = _get_vectorstore()
        logger.info("SLRE ready: %d vectors loaded.", vs.index.ntotal)
    except Exception as e:
        logger.warning("SLRE pre-warm failed (non-fatal): %s", e)
    yield  # server runs here
    logger.info("Server shutdown.")

# ✅ Create the FastAPI instance only once
app = FastAPI(
    title="Legaily Doc AI API",
    description="API for OCR, Summarization, and Translation of uploaded documents",
    version="1.0.0",
    lifespan=lifespan,
)

from apps.config.settings import get_settings

_cfg = get_settings()
_cors = _cfg.cors_origins if _cfg.cors_origins != ["*"] else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route
@app.get("/")
async def root():
    return {"message": "Welcome to Legaily Doc AI API"}

# ✅ Register router with prefix
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    _s = get_settings()
    uvicorn.run("apps.main:app", host=_s.host, port=_s.port, reload=True)
