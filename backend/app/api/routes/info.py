"""
Info and root routes.
"""

from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

from app.api.dependencies import get_rag_module

router = APIRouter()


@router.get("/")
async def root():
    """Redirect to frontend."""
    return RedirectResponse(url="/frontend/index.html")


@router.get("/frontend/")
async def frontend_root():
    """Serve frontend index."""
    frontend_path = Path(__file__).parent.parent.parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="index.html not found")


@router.get("/api/info")
async def get_project_info():
    """Get project information."""
    rag_module = get_rag_module()
    
    return {
        "name": "Asistente Inteligente de Integración Cultural",
        "institution": "Kubán State University (KubGU)",
        "version": "0.5.0",
        "features": [
            "Semantic search with sentence-transformers",
            "LLM integration with Ollama (llama3, qwen2, mistral)",
            "Streaming chat via SSE",
            "Conversation memory per session",
            "Keyword fallback search",
            "Búsqueda RAG en documentos oficiales",
            "Base de 200+ frases contextualizadas",
            "Personalización por perfil de usuario",
            "Traducción multiidioma",
            "TTS (Text-to-Speech) via gTTS",
            "STT (Speech-to-Text) via Google Speech Recognition",
            "Interfaz web + Telegram bot"
        ],
        "search_mode": rag_module.document_library.get_search_mode()
    }
