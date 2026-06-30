"""
Chat and RAG search routes.
"""

import uuid
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import AsyncGenerator

from app.api.models import QueryRequest, StreamRequest, ChatResponse
from app.api.dependencies import (
    get_rag_module,
    get_rag_service,
    get_translator,
    get_conversation_memory,
    get_cache,
    check_rate_limit,
)
from app.domain.exceptions import RAGError
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.post("/api/search")
async def search_documents(
    query: QueryRequest,
    rag_service = Depends(get_rag_service)
):
    """Búsqueda en documentos oficiales usando RAG mejorado con semantic search."""
    try:
        result = rag_service.search(
            query=query.query,
            language=query.language,
            context_type=f"lang_{query.language}"
        )
        return result
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in RAG search: {str(e)}")


@router.get("/api/search/sources")
async def get_rag_sources(rag_service = Depends(get_rag_service)):
    """Obtener fuentes oficiales disponibles."""
    try:
        return rag_service.get_sources()
    except RAGError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")


@router.post("/api/chat")
async def chat(
    request: QueryRequest,
    http_request: Request,
    _: str = Depends(check_rate_limit)
):
    """Chat principal con soporte multiidioma, RAG y cache."""
    try:
        rag_module = get_rag_module()
        translator = get_translator()
        conversation_memory = get_conversation_memory()
        
        # Import cache functions
        from main import cache_rag_query, get_cached_rag_query
        
        # Generate or use existing session
        session_id = request.session_id or str(uuid.uuid4())
        target_lang = request.language

        # Try cache first
        cached_result = get_cached_rag_query(request.query, target_lang)
        if cached_result:
            cached_result['cached'] = True
            return cached_result

        # Buscar en el RAG
        rag_result = rag_module.search_and_generate(
            request.query,
            context_type=f"chat_{target_lang}",
            language=target_lang,
            session_id=session_id
        )

        # Respuesta
        answer_translated = rag_result['response']
        answer_original = rag_result['response']

        # Add to conversation memory
        conversation_memory.add_message(session_id, 'user', request.query)
        conversation_memory.add_message(session_id, 'assistant', answer_translated)

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
            available_languages=list(translator.get_supported_languages().keys()),
            search_mode=rag_result.get('search_mode', 'keyword')
        )

        # Cache the response
        response_dict = response.model_dump()
        cache_rag_query(request.query, target_lang, response_dict)

        return response
    except Exception as e:
        return ChatResponse(
            query=request.query,
            answer=f"Error al procesar la búsqueda: {str(e)}",
            answer_original=f"Error al procesar la búsqueda: {str(e)}",
            context=["Error"],
            personalized_tips=["Por favor, intente nuevamente"],
            language=request.language,
            available_languages=list(get_translator().get_supported_languages().keys()),
            search_mode="error"
        )


@router.post("/api/chat/stream")
async def chat_stream(request: StreamRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Returns tokens as they are generated from the LLM.
    """
    rag_module = get_rag_module()
    conversation_memory = get_conversation_memory()
    
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from LLM stream."""
        import json
        full_response = ""

        try:
            # Add user message to memory
            conversation_memory.add_message(session_id, 'user', request.query)

            # Send session ID first
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # Stream from RAG module
            async for token in rag_module.generate_stream_async(
                query=request.query,
                context_type='stream_chat',
                language=request.language,
                session_id=session_id
            ):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'full_length': len(full_response)})}\n\n"

            # Add assistant response to memory
            conversation_memory.add_message(session_id, 'assistant', full_response)

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get conversation history for a session."""
    try:
        conversation_memory = get_conversation_memory()
        history = conversation_memory.get_history(session_id)
        summary = conversation_memory.get_summary(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


@router.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    """Clear conversation history for a session."""
    try:
        conversation_memory = get_conversation_memory()
        conversation_memory.clear_session(session_id)
        return {
            "status": "cleared",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")


@router.get("/api/chat/sessions")
async def list_chat_sessions():
    """List all active chat sessions."""
    try:
        conversation_memory = get_conversation_memory()
        return {
            "active_sessions": conversation_memory.get_session_count(),
            "total_messages": conversation_memory.get_message_count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")
