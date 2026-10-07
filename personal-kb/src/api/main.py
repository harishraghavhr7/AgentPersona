from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from api.routes import health_router, ingest_router, query_router, documents_router
from api.ui import HTML_UI
from config.settings import get_settings
from storage.qdrant import get_qdrant_client, ensure_collection_and_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    Initializes Qdrant connection and verifies temporal payload indexes on startup.
    """
    settings = get_settings()
    print("=" * 60, flush=True)
    print("[STARTUP] Personal Knowledge Base API starting up...", flush=True)
    print(f"[STARTUP] Qdrant URL: {settings.qdrant_url}", flush=True)
    print(f"[STARTUP] Qdrant Collection: {settings.qdrant_collection}", flush=True)
    print(f"[STARTUP] Qdrant API Key configured: {bool(settings.qdrant_api_key)}", flush=True)
    print(f"[STARTUP] LLM Fallback chain: {' -> '.join(settings.llm_fallback_order)}", flush=True)
    print(f"[STARTUP] Groq configured: {bool(settings.groq_api_key)}", flush=True)
    print(f"[STARTUP] Gemini configured: {bool(settings.gemini_api_key)}", flush=True)
    print(f"[STARTUP] OpenRouter configured: {bool(settings.openrouter_api_key)}", flush=True)
    print(f"[STARTUP] Embedding Provider: {settings.embedding_provider} / {settings.embedding_model}", flush=True)
    print("=" * 60, flush=True)

    try:
        client = get_qdrant_client()
        ensure_collection_and_indexes(client, settings.qdrant_collection)
        print(f"[STARTUP] Successfully verified Qdrant collection '{settings.qdrant_collection}' and payload indexes.", flush=True)
        logger.info(f"Verified Qdrant collection '{settings.qdrant_collection}' and temporal payload indexes.")
    except Exception as e:
        detail = ""
        if hasattr(e, "content") and e.content:
            try:
                detail = f" - Details: {e.content.decode('utf-8', errors='ignore')}"
            except Exception:
                detail = f" - Details: {e.content}"
        print(f"[STARTUP NOTICE] Qdrant initialization issue: {e}{detail}", flush=True)
        logger.warning(f"Qdrant initialization notice on startup: {e}{detail}")
    yield
    print("[SHUTDOWN] Personal Knowledge Base API shutting down...", flush=True)


app = FastAPI(
    title="Personal Knowledge Base with Temporal Memory",
    description="Local-first grounded RAG system with temporal indexing, versioning, supersession, and provenance.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local UI and tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(documents_router)


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    """Serve the interactive Temporal Knowledge Base Web UI."""
    return HTMLResponse(content=HTML_UI, status_code=200)


@app.get("/api")
def api_info():
    return {
        "service": "Personal Knowledge Base with Temporal Memory",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ui": "/ui",
    }
