import urllib.request
from fastapi import APIRouter
from config.settings import get_settings
from storage.qdrant import get_qdrant_client
from api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    settings = get_settings()
    
    # Check Qdrant
    qdrant_status = "unknown"
    try:
        client = get_qdrant_client()
        info = client.get_collection(settings.qdrant_collection)
        qdrant_status = "healthy" if info.status else "unhealthy"
    except Exception as e:
        qdrant_status = f"unhealthy ({e})"

    # Check Ollama
    ollama_status = "unknown"
    try:
        req = urllib.request.Request(f"{settings.ollama_base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                ollama_status = "healthy"
    except Exception as e:
        ollama_status = f"unhealthy ({e})"

    overall = "healthy" if ("healthy" in qdrant_status and "healthy" in ollama_status) else "degraded"

    # Status of fallback providers
    providers_configured = {
        "groq": bool(settings.groq_api_key and settings.groq_api_key.strip()),
        "gemini": bool(settings.gemini_api_key and settings.gemini_api_key.strip()),
        "openrouter": bool(settings.openrouter_api_key and settings.openrouter_api_key.strip()),
    }

    return HealthResponse(
        status=overall,
        qdrant_status=qdrant_status,
        ollama_status=ollama_status,
        collection=settings.qdrant_collection,
        active_models={
            "llm_fallback_order": " -> ".join(settings.llm_fallback_order),
            "groq": settings.groq_model,
            "gemini": settings.gemini_model,
            "openrouter": settings.openrouter_model,
            "embedding": settings.embedding_model,
        },
        llm_fallback_chain=settings.llm_fallback_order,
        providers_configured=providers_configured,
    )
