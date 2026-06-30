"""
Conversation Service: wrapper around ConversationMemory.

Manages conversation history per session with structured logging.
Does not modify the underlying ConversationMemory implementation.
"""

from typing import Dict, List, Optional

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class ConversationService:
    """Service for conversation history management.
    
    Wraps ConversationMemory without modifying it.
    Provides clean interface for routers with structured logging.
    Handles session-based conversation tracking.
    """
    
    def __init__(self, conversation_memory):
        """Initialize with ConversationMemory instance.
        
        Args:
            conversation_memory: ConversationMemory instance from main.py
            
        Raises:
            ValidationError: If memory is not initialized
        """
        if conversation_memory is None:
            raise ValidationError(
                "Conversation memory not initialized",
                field="conversation_memory",
                context={"reason": "memory is None"}
            )
        
        self.memory = conversation_memory
        logger.info(
            "conversation_service_initialized",
            module_type=type(conversation_memory).__name__
        )
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Add message to conversation history.
        
        Args:
            session_id: Unique session identifier
            role: 'user', 'assistant', or 'system'
            content: Message content
            metadata: Optional metadata (language, model, etc.)
            
        Returns:
            Dict with {success: bool, message_count: int, session_id: str}
            
        Raises:
            ValidationError: If inputs are invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError(
                "Invalid session_id",
                field="session_id",
                context={"received": session_id}
            )
        
        if not role or role not in ['user', 'assistant', 'system']:
            raise ValidationError(
                "Invalid role",
                field="role",
                context={"received": role, "allowed": ['user', 'assistant', 'system']}
            )
        
        if not content or not isinstance(content, str):
            raise ValidationError(
                "Invalid content",
                field="content",
                context={"received": content}
            )
        
        try:
            logger.info(
                "add_message_start",
                session_id=session_id,
                role=role,
                content_length=len(content),
                has_metadata=metadata is not None
            )
            
            self.memory.add_message(
                session_id=session_id,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            message_count = self.memory.get_message_count(session_id)
            
            logger.info(
                "add_message_success",
                session_id=session_id,
                role=role,
                message_count=message_count
            )
            
            return {
                "success": True,
                "message_count": message_count,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(
                "add_message_failed",
                session_id=session_id,
                role=role,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Failed to add message: {str(e)}",
                context={"session_id": session_id, "role": role},
                original_exception=e
            )
    
    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dicts with {role, content, timestamp}
            
        Raises:
            ValidationError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError(
                "Invalid session_id",
                field="session_id",
                context={"received": session_id}
            )
        
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise ValidationError(
                "Invalid limit",
                field="limit",
                context={"received": limit, "must_be": "positive int"}
            )
        
        try:
            logger.info(
                "get_history_start",
                session_id=session_id,
                limit=limit
            )
            
            history = self.memory.get_history(session_id)
            
            # Apply limit if specified
            if limit and len(history) > limit:
                history = history[-limit:]
            
            logger.info(
                "get_history_success",
                session_id=session_id,
                message_count=len(history),
                limit_applied=limit is not None
            )
            
            return history
            
        except Exception as e:
            logger.error(
                "get_history_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Failed to get history: {str(e)}",
                context={"session_id": session_id},
                original_exception=e
            )
    
    def clear_session(self, session_id: str) -> Dict:
        """Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with {success: bool, session_id: str}
            
        Raises:
            ValidationError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError(
                "Invalid session_id",
                field="session_id",
                context={"received": session_id}
            )
        
        try:
            logger.info(
                "clear_session_start",
                session_id=session_id
            )
            
            self.memory.clear_session(session_id)
            
            logger.info(
                "clear_session_success",
                session_id=session_id
            )
            
            return {
                "success": True,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(
                "clear_session_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Failed to clear session: {str(e)}",
                context={"session_id": session_id},
                original_exception=e
            )
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get summary of a session's conversation.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with message_count, session_id, last_message_time
            
        Raises:
            ValidationError: If session_id is invalid
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError(
                "Invalid session_id",
                field="session_id",
                context={"received": session_id}
            )
        
        try:
            logger.info(
                "get_session_summary_start",
                session_id=session_id
            )
            
            history = self.memory.get_history(session_id)
            message_count = len(history)
            last_message_time = None
            
            if history:
                last_message_time = history[-1].get('timestamp')
            
            logger.info(
                "get_session_summary_success",
                session_id=session_id,
                message_count=message_count
            )
            
            return {
                "session_id": session_id,
                "message_count": message_count,
                "last_message_time": last_message_time
            }
            
        except Exception as e:
            logger.error(
                "get_session_summary_failed",
                session_id=session_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Failed to get session summary: {str(e)}",
                context={"session_id": session_id},
                original_exception=e
            )
    
    def get_status(self) -> Dict:
        """Get service status.
        
        Returns:
            Dict with {available: bool, active_sessions: int, total_messages: int}
        """
        try:
            logger.info("conversation_status_check")
            
            active_sessions = self.memory.get_session_count()
            total_messages = self.memory.get_message_count()
            
            logger.info(
                "conversation_status_retrieved",
                active_sessions=active_sessions,
                total_messages=total_messages
            )
            
            return {
                "available": True,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "max_history": self.memory.max_history
            }
            
        except Exception as e:
            logger.error(
                "conversation_status_failed",
                error=str(e)
            )
            return {
                "available": False,
                "error": str(e)
            }
