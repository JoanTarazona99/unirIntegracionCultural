"""
Chat and RAG search routes.
"""

import uuid
import hashlib
import json
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import AsyncGenerator

from app.api.models import QueryRequest, StreamRequest, ChatResponse
from app.api.dependencies import (
    get_rag_module,
    get_rag_service,
    get_translator,
    get_conversation_memory,
    get_conversation_service,
    get_cache,
    get_cache_service,
    check_rate_limit,
)
from app.domain.exceptions import RAGError, ValidationError, AppError
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
    rag_service = Depends(get_rag_service),
    conversation_service = Depends(get_conversation_service),
    cache_service = Depends(get_cache_service),
    _: str = Depends(check_rate_limit)
):
    """Chat principal con soporte multiidioma, RAG, historial y caché integrados.
    
    Flujo:
    1. Generar cache key (hash de query + language)
    2. Intentar obtener del cache
    3. Si no está en cache: usar RAG para buscar
    4. Guardar query + response en memoria de conversación
    5. Guardar resultado en cache (TTL 1 hora)
    6. Retornar respuesta con metadata
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        target_lang = request.language
        
        # ============ CACHE LOOKUP ============
        # Generate deterministic cache key
        cache_key = hashlib.md5(
            json.dumps({"query": request.query, "language": target_lang}, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"rag_chat_{cache_key}_{target_lang}"
        
        # Try to get from cache
        cached_result = cache_service.get(cache_key)
        if cached_result:
            cached_result['cached'] = True
            cached_result['cache_key'] = cache_key
            return cached_result
        
        # ============ RAG SEARCH ============
        # If not cached, perform RAG search
        rag_result = rag_service.search(
            query=request.query,
            language=target_lang,
            context_type=f"chat_{target_lang}"
        )
        
        answer_translated = rag_result['response']
        answer_original = rag_result['response']
        
        # ============ CONVERSATION MEMORY ============
        # Store in conversation memory
        conversation_service.add_message(session_id, 'user', request.query)
        conversation_service.add_message(session_id, 'assistant', answer_translated)
        
        # ============ CONTEXT & TIPS ============
        # Extract context and personalized tips from RAG sources
        context = []
        personalized_tips = []
        
        if rag_result.get('sources_found', 0) > 0:
            for source in rag_result.get('sources', [])[:3]:  # Limit to 3 sources
                source_text = f"[{source.get('source', 'Unknown')}] {source.get('title', '')}"
                content_text = source.get('content', '')[:200] + "..." if len(source.get('content', '')) > 200 else source.get('content', '')
                
                context.append(source_text)
                personalized_tips.append(content_text)
        
        # Default tips if none found
        if not personalized_tips:
            personalized_tips = [
                "Consulte los documentos oficiales para más información"
            ]
        
        # ============ BUILD RESPONSE ============
        response = ChatResponse(
            query=request.query,
            answer=answer_translated,
            answer_original=answer_original,
            translations={target_lang: answer_translated} if target_lang != 'es' else None,
            context=context,
            personalized_tips=personalized_tips,
            language=target_lang,
            available_languages=['es', 'en', 'ru', 'fr'],
            search_mode=rag_result.get('search_mode', 'keyword'),
            session_id=session_id,
            cached=False,
            cache_key=cache_key
        )
        
        # ============ CACHE UPDATE ============
        # Cache the response for 1 hour (3600 seconds)
        response_dict = response.model_dump()
        cache_service.set(cache_key, response_dict, ttl=3600)
        
        return response
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=f"Service error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing chat: {str(e)}"
        )



@router.post("/api/chat/stream")
async def chat_stream(
    request: StreamRequest,
    conversation_service = Depends(get_conversation_service)
):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Returns tokens as they are generated from the LLM with conversation memory tracking.
    
    Flujo:
    1. Generar session_id si no existe
    2. Guardar query en conversación
    3. Stream tokens desde RAG
    4. Guardar respuesta completa en conversación al terminar
    """
    rag_module = get_rag_module()
    
    session_id = request.session_id or str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from LLM stream."""
        full_response = ""

        try:
            # Add user message to conversation memory
            conversation_service.add_message(session_id, 'user', request.query)

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

            # Add assistant response to conversation memory
            conversation_service.add_message(session_id, 'assistant', full_response)

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
async def get_chat_history(session_id: str, conversation_service = Depends(get_conversation_service)):
    """Get conversation history for a session using ConversationService."""
    try:
        history = conversation_service.get_history(session_id)
        summary = conversation_service.get_session_summary(session_id)
        return {
            "session_id": session_id,
            "history": history,
            "summary": summary
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


@router.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str, conversation_service = Depends(get_conversation_service)):
    """Clear conversation history for a session using ConversationService."""
    try:
        result = conversation_service.clear_session(session_id)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")


@router.get("/api/chat/sessions")
async def list_chat_sessions(conversation_service = Depends(get_conversation_service)):
    """List all active chat sessions with status."""
    try:
        status = conversation_service.get_status()
        return {
            "active_sessions": status["active_sessions"],
            "total_messages": status["total_messages"],
            "max_history_per_session": status["max_history"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")
