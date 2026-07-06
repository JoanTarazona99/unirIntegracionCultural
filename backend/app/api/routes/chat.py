"""
Chat and RAG search routes.

Persistence Strategy:
- ConversationService: Primary memory storage (always available, no dependencies)
- DatabaseService: Optional complementary persistence (background tasks, graceful fallback)
  - Enabled via settings.enable_database and settings.database_url
  - Uses FastAPI BackgroundTasks for non-blocking persistence (safe shutdown guarantee)
  - Falls back to memory if database unavailable or not configured
  - No impact on HTTP response contract or latency
"""

import uuid
import hashlib
import json
import time
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from typing import AsyncGenerator

from app.api.models import QueryRequest, StreamRequest, ChatResponse, AIMetrics
from app.api.dependencies import (
    get_rag_module,
    get_rag_service,
    get_translator,
    get_conversation_memory,
    get_conversation_service,
    get_cache,
    get_cache_service,
    check_rate_limit,
    get_database_service,
)
from app.domain.exceptions import RAGError, ValidationError, AppError
from fastapi.responses import StreamingResponse
from app.config.settings import settings
from app.config.logging_config import get_logger
import asyncio

logger = get_logger(__name__)


# ================== BACKGROUND TASK HELPERS ==================
# These functions are sync wrappers for async database operations
# They are executed in background tasks by FastAPI (guaranteed completion before shutdown)

def _persist_chat_messages(db_service, session_id: str, query: str, response: str, language: str):
    """Background task: Persist chat messages to database.
    
    Runs in background, guaranteed to complete before server shutdown.
    Failures are logged but don't affect the HTTP response.
    """
    if not settings.enable_database:
        return
    
    try:
        # Create new event loop for this background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Save user message
        loop.run_until_complete(
            db_service.save_message(
                session_id=session_id,
                role='user',
                content=query,
                language=language
            )
        )
        
        # Save assistant response
        loop.run_until_complete(
            db_service.save_message(
                session_id=session_id,
                role='assistant',
                content=response,
                language=language
            )
        )
        
        logger.info("chat_messages_persisted_to_database", session_id=session_id)
    except Exception as e:
        logger.warning("database_chat_persistence_failed", error=str(e), session_id=session_id)
    finally:
        loop.close()

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
    background_tasks: BackgroundTasks,
    rag_service = Depends(get_rag_service),
    conversation_service = Depends(get_conversation_service),
    cache_service = Depends(get_cache_service),
    database_service = Depends(get_database_service),
    knowledge_agent = Depends(lambda: None),  # Optional dependency
    _: str = Depends(check_rate_limit)
):
    """Chat principal con soporte multiidioma, RAG, historial, caché e integración web.
    
    Flujo:
    1. Generar cache key (hash de query + language)
    2. Intentar obtener del cache
    3. Si no está en cache: usar RAG para buscar
    4. Si grounding score < threshold: intentar adquirir conocimiento de web
    5. Guardar query + response en memoria de conversación
    6. Guardar resultado en cache (TTL 1 hora)
    7. Queue mensaje para persistencia en BD (background task)
    8. Retornar respuesta con metadata
    
    Persistencia:
    - ConversationService: Primary (always available)
    - DatabaseService: Optional background persistence
    
    Knowledge Acquisition:
    - Si grounding bajo: búsqueda en Wikipedia, Google AI, DuckDuckGo
    - Ingesta automática de documentos en RAG base
    - Re-búsqueda con conocimiento expandido
    """
    try:
        # Initialize knowledge agent for web search fallback
        if knowledge_agent is None:
            try:
                from knowledge_acquisition import KnowledgeAcquisitionAgent
                knowledge_agent = KnowledgeAcquisitionAgent()
                logger.info("knowledge_acquisition_agent_initialized")
            except Exception as e:
                logger.warning(f"knowledge_acquisition_agent_init_failed: {str(e)}")
                knowledge_agent = None
        
        session_id = request.session_id or str(uuid.uuid4())
        target_lang = request.language
        _t_request_start = time.perf_counter()
        
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
            if isinstance(cached_result.get('ai_metrics'), dict):
                total_ms = round((time.perf_counter() - _t_request_start) * 1000.0, 1)
                latency = cached_result['ai_metrics'].get('latency_ms') or {}
                latency['total'] = total_ms
                latency['cache_hit'] = True
                cached_result['ai_metrics']['latency_ms'] = latency
            return cached_result
        
        # ============ RAG SEARCH ============
        logger.info("chat_rag_search_start", query=request.query, language=target_lang)
        rag_result = rag_service.search(
            query=request.query,
            language=target_lang,
            context_type=f"chat_{target_lang}"
        )
        
        answer_translated = rag_result['response']
        answer_original = rag_result['response']
        grounding_score = rag_result.get('grounding_score', 0)
        
        # ============ KNOWLEDGE ACQUISITION (LOW GROUNDING) ============
        # If grounding is low and we have knowledge agent, try to acquire knowledge
        if knowledge_agent and grounding_score < 0.4:
            logger.info(
                "chat_low_grounding_detected",
                query=request.query,
                grounding_score=grounding_score,
                language=target_lang
            )
            
            try:
                print(f"\n[Chat] 🔍 Grounding score bajo ({grounding_score:.2f}), buscando en web...")
                
                # Attempt knowledge acquisition
                new_result = await knowledge_agent.handle_low_grounding(
                    query=request.query,
                    draft_answer=answer_translated,
                    retrieved_docs=rag_result.get('sources', []),
                    evaluation={'score': grounding_score, 'missing_entities': []},
                    rag_module=get_rag_service()  # Pass RAG module for retry
                )
                
                # If acquisition successful, use new result
                if new_result:
                    rag_result = new_result
                    answer_translated = new_result.get('response', answer_translated)
                    grounding_score = new_result.get('grounding_score', grounding_score)
                    
                    logger.info(
                        "chat_knowledge_acquisition_success",
                        query=request.query,
                        new_grounding_score=grounding_score,
                        language=target_lang
                    )
                    print(f"[Chat] ✅ Conocimiento adquirido exitosamente, grounding mejorado a {grounding_score:.2f}")
                else:
                    logger.warning(
                        "chat_knowledge_acquisition_failed",
                        query=request.query,
                        grounding_score=grounding_score,
                        language=target_lang
                    )
                    print(f"[Chat] ⚠️ No se pudo adquirir conocimiento adicional")
                    
            except Exception as e:
                logger.warning(
                    "chat_knowledge_acquisition_error",
                    query=request.query,
                    error=str(e),
                    language=target_lang
                )
                print(f"[Chat] ❌ Error en adquisición de conocimiento: {e}")
                # Continue with original result, don't block response
        
        # ============ CONVERSATION MEMORY (Primary) ============
        # Store in conversation memory immediately (synchronous, reliable)
        conversation_service.add_message(session_id, 'user', request.query)
        conversation_service.add_message(session_id, 'assistant', answer_translated)
        
        # ============ DATABASE PERSISTENCE (Background Task) ============
        # Queue background task for async database persistence (non-blocking)
        if settings.enable_database:
            background_tasks.add_task(
                _persist_chat_messages,
                database_service,
                session_id,
                request.query,
                answer_translated,
                target_lang
            )
            logger.info("chat_persistence_queued_for_background", session_id=session_id)
        
        # ============ CONTEXT & TIPS ============
        context = []
        personalized_tips = []
        
        if rag_result.get('sources_found', 0) > 0:
            for source in rag_result.get('sources', [])[:3]:
                source_text = f"[{source.get('source', 'Unknown')}] {source.get('title', '')}"
                content_text = source.get('content', '')[:200] + "..." if len(source.get('content', '')) > 200 else source.get('content', '')
                
                context.append(source_text)
                personalized_tips.append(content_text)
        
        if not personalized_tips:
            personalized_tips = [
                "Consulte los documentos oficiales para más información"
            ]
        
        # ============ AI TRANSPARENCY METRICS ============
        ai_metrics = None
        raw_metrics = rag_result.get('ai_metrics')
        if raw_metrics:
            total_ms = round((time.perf_counter() - _t_request_start) * 1000.0, 1)
            latency = dict(raw_metrics.get('latency_ms') or {})
            latency['total'] = total_ms
            latency['cache_hit'] = False
            try:
                ai_metrics = AIMetrics(
                    search_mode=raw_metrics.get('search_mode'),
                    response_mode=raw_metrics.get('response_mode'),
                    sources_found=raw_metrics.get('sources_found'),
                    retrieval_scores=raw_metrics.get('retrieval_scores', []),
                    faithfulness=raw_metrics.get('faithfulness'),
                    grounded=raw_metrics.get('grounded'),
                    abstained=raw_metrics.get('abstained'),
                    latency_ms=latency,
                    tokens=raw_metrics.get('tokens'),
                    models_active=raw_metrics.get('models_active'),
                    query_expansion=raw_metrics.get('query_expansion', []),
                )
            except Exception as e:
                logger.warning("ai_metrics_build_failed", error=str(e))
                ai_metrics = None

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
            cache_key=cache_key,
            ai_metrics=ai_metrics
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
    conversation_service = Depends(get_conversation_service),
    database_service = Depends(get_database_service)
):
    """Streaming chat endpoint using Server-Sent Events (SSE).

    Returns tokens as they are generated from the LLM with conversation memory tracking.
    
    Persistence Strategy:
    - ConversationService: Primary (stored immediately during streaming)
    - DatabaseService: Async persistence via asyncio.create_task() (inside async generator)
      - Explanation: asyncio.create_task() is appropriate here because we're in an async 
        context (event_generator is async), not an HTTP route (which uses BackgroundTasks)
      - asyncio.create_task() schedules the coroutine in the current event loop
      - The task runs concurrently with the SSE stream and completes before server shutdown
    
    Flujo:
    1. Generar session_id si no existe
    2. Guardar query en conversación (primary)
    3. Stream tokens desde RAG (SSE)
    4. Guardar respuesta completa en conversación (primary)
    5. Queue persistence task in background (asyncio.create_task, no wait)
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
            
            # Persist to database asynchronously if enabled
            if settings.enable_database:
                try:
                    asyncio.create_task(
                        database_service.save_message(
                            session_id=session_id,
                            role='user',
                            content=request.query,
                            language=request.language
                        )
                    )
                    asyncio.create_task(
                        database_service.save_message(
                            session_id=session_id,
                            role='assistant',
                            content=full_response,
                            language=request.language
                        )
                    )
                    logger.info("stream_messages_queued_for_persistence", session_id=session_id)
                except Exception as e:
                    logger.warning("database_stream_persistence_failed", error=str(e), session_id=session_id)

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
async def get_chat_history(
    session_id: str,
    conversation_service = Depends(get_conversation_service),
    database_service = Depends(get_database_service)
):
    """Get conversation history for a session.
    
    Tries: DatabaseService → ConversationService (fallback)
    """
    try:
        history = []
        source = "memory"  # Default fallback
        
        # Try database first if enabled
        if settings.enable_database:
            try:
                history = await database_service.get_history(session_id, limit=50)
                if history:
                    source = "database"
                    logger.info("history_retrieved_from_database", session_id=session_id, count=len(history))
            except Exception as e:
                logger.warning("database_history_lookup_failed", error=str(e), session_id=session_id)
                # Fall through to conversation_service
        
        # Fallback to conversation service if DB didn't return anything
        if not history:
            history = conversation_service.get_history(session_id)
            source = "memory"
            if history:
                logger.info("history_retrieved_from_memory", session_id=session_id, count=len(history))
        
        summary = conversation_service.get_session_summary(session_id)
        
        return {
            "session_id": session_id,
            "history": history,
            "summary": summary,
            "_source": source
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
