from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
from pathlib import Path
from enhanced_rag import EnhancedRAGModule
from translator import create_translator

app = FastAPI(
    title="Asistente de Integración Cultural - KubGU",
    description="Backend para soporte inteligente a estudiantes extranjeros",
    version="0.2.0"
)

# Inicializar módulo RAG mejorado e traductor multiidioma
rag_module = EnhancedRAGModule()
translator = create_translator()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta raíz: redireccionar a frontend
@app.get("/")
async def root():
    return RedirectResponse(url="/frontend/index.html")

# Ruta para /frontend/: servir index.html
@app.get("/frontend/")
async def frontend_root():
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="index.html not found")

# Servir archivos estáticos (frontend)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")

# Modelos Pydantic
class UserProfile(BaseModel):
    user_id: str
    name: str
    country: str
    native_language: str
    visa_type: str  # "student", "study_visit"
    academic_level: str  # "bachelor", "master", "phd"
    housing_type: str  # "dorm", "private_apartment"
    russian_level: str  # "A1", "A2", "B1", "B2", "C1"

class PhraseResponse(BaseModel):
    id: int
    russian: str
    transliteration: str
    english: str
    audio_url: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    user_id: str
    language: str = "es"  # Idioma de respuesta deseado
    target_language: Optional[str] = None  # Idioma adicional para traducción

class ChatResponse(BaseModel):
    query: str
    answer: str  # Respuesta en idioma solicitado
    answer_original: str  # Respuesta original en español
    translations: Optional[Dict[str, str]] = None  # Traducciones adicionales
    context: List[str]
    personalized_tips: List[str]
    language: str  # Idioma de la respuesta
    available_languages: List[str] = None  # Idiomas disponibles

class TranslationRequest(BaseModel):
    text: str
    source_language: str = "es"
    target_language: str = "en"

# Cargar frases base
def load_phrases():
    phrases_file = Path(__file__).parent.parent / "data" / "phrases" / "base_phrases.json"
    if phrases_file.exists():
        with open(phrases_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

phrases_db = load_phrases()

# Rutas de salud
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Asistente de Integración Cultural activo"}

# Rutas de frases
@app.get("/api/phrases", response_model=List[PhraseResponse])
async def get_phrases(category: Optional[str] = None, limit: int = 10):
    """Obtener frases contextualizadas"""
    filtered = phrases_db
    
    if category:
        filtered = [p for p in filtered if p.get("category") == category]
    
    return filtered[:limit]

@app.get("/api/phrases/{phrase_id}")
async def get_phrase(phrase_id: int):
    """Obtener una frase específica"""
    for phrase in phrases_db:
        if phrase.get("id") == phrase_id:
            return phrase
    raise HTTPException(status_code=404, detail="Frase no encontrada")

# Rutas de usuario
@app.post("/api/users/profile")
async def create_user_profile(profile: UserProfile):
    """Crear perfil de usuario personalizado"""
    return {
        "message": "Perfil creado exitosamente",
        "profile": profile,
        "personalization_factors": {
            "country": profile.country,
            "visa_type": profile.visa_type,
            "language_support": "Soportado",
            "recommended_phrases_count": 50
        }
    }

# Rutas de búsqueda RAG
@app.post("/api/search")
async def search_documents(query: QueryRequest):
    """Búsqueda en documentos oficiales usando RAG mejorado"""
    result = rag_module.search_and_generate(
        query.query,
        context_type=f"lang_{query.language}"
    )
    return result

@app.get("/api/search/sources")
async def get_rag_sources():
    """Obtener fuentes oficiales disponibles"""
    return {
        "sources": rag_module.document_library.list_sources(),
        "description": "Fuentes de documentos oficiales integradas"
    }

# Rutas de chat
@app.post("/api/chat")
async def chat(request: QueryRequest):
    """Chat principal con soporte multiidioma y RAG"""
    try:
        # Idioma de respuesta (default: español)
        target_lang = request.language if request.language != "ru" else "es"
        
        # Buscar en el RAG (siempre en español primero)
        rag_result = rag_module.search_and_generate(
            request.query,
            context_type=f"chat_{target_lang}"
        )
        
        # Respuesta original en español
        answer_original = rag_result['response']
        
        # Traducir si el idioma no es español
        if target_lang != 'es':
            answer_translated = translator.translate_text(answer_original, target_lang)
        else:
            answer_translated = answer_original
        
        # Extraer contexto y fuentes
        context = []
        personalized_tips = []
        
        if rag_result['sources']:
            for source in rag_result['sources']:
                source_text = f"[{source['source']}] {source['title']}"
                content_text = source['content'][:200] + "..."
                
                # Traducir contexto si es necesario
                if target_lang != 'es':
                    source_text = translator.translate_text(source_text, target_lang)
                    content_text = translator.translate_text(content_text, target_lang)
                
                context.append(source_text)
                personalized_tips.append(content_text)
        
        # Crear respuesta con traducciones opcionales
        response = ChatResponse(
            query=request.query,
            answer=answer_translated,
            answer_original=answer_original,
            translations={target_lang: answer_translated} if target_lang != 'es' else None,
            context=context,
            personalized_tips=personalized_tips if personalized_tips else [
                "Consulte los documentos oficiales para más información" if target_lang == 'es' else 
                translator.translate_text("Consulte los documentos oficiales para más información", target_lang)
            ],
            language=target_lang,
            available_languages=list(translator.get_supported_languages().keys())
        )
        return response
    except Exception as e:
        return ChatResponse(
            query=request.query,
            answer=f"Error al procesar la búsqueda: {str(e)}",
            answer_original=f"Error al procesar la búsqueda: {str(e)}",
            context=["Error"],
            personalized_tips=["Por favor, intente nuevamente"],
            language=request.language,
            available_languages=list(translator.get_supported_languages().keys())
        )

# Endpoint de idiomas disponibles
@app.get("/api/languages")
async def get_languages():
    """Obtener lista de idiomas disponibles"""
    return {
        "supported_languages": translator.get_supported_languages(),
        "default_language": "es",
        "total_languages": len(translator.get_supported_languages())
    }

# Endpoint de traducción
@app.post("/api/translate")
async def translate(request: TranslationRequest):
    """Traducir texto entre idiomas"""
    try:
        translated_text = translator.translate_text(
            request.text,
            request.target_language,
            request.source_language
        )
        return {
            "original_text": request.text,
            "translated_text": translated_text,
            "source_language": request.source_language,
            "target_language": request.target_language,
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }

# Información del proyecto
@app.get("/api/info")
async def get_project_info():
    return {
        "name": "Asistente Inteligente de Integración Cultural",
        "institution": "Kubán State University (KubGU)",
        "version": "0.1.0 MVP",
        "features": [
            "Base de 200+ frases contextualizadas",
            "Búsqueda RAG en documentos oficiales",
            "Personalización por perfil de usuario",
            "Soporte TTS/STT",
            "Interfaz web + Telegram bot"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
