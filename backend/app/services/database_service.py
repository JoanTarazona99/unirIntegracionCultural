"""
Database service for persistent conversation history and user profiles.

Supports multiple backends: SQLite (default), PostgreSQL (optional).
Automatically falls back to in-memory storage if database unavailable.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
import json
from pathlib import Path

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class DatabaseService:
    """
    Database service with backend swapping (SQLite/PostgreSQL/Memory).
    
    Supports:
    - SQLite (default, stdlib, no dependencies)
    - PostgreSQL (optional, with asyncpg)
    - Memory fallback (dict-based)
    
    Tables:
    - conversations: id, session_id, role, content, language, timestamp
    - user_profiles: user_id, country, visa_type, academic_level, russian_level, updated_at
    """
    
    def __init__(self, database_url: str = "sqlite:///./data/assistant.db", db_path: str = "./data/assistant.db"):
        """
        Initialize database service.
        
        Args:
            database_url: Database URL (sqlite:/// or postgresql://)
            db_path: Path for SQLite database file
        """
        self.database_url = database_url
        self.db_path = db_path
        self.backend_type = "memory"  # Default fallback
        self.db_client = None
        self.connection = None
        
        # In-memory storage fallback
        self.memory_conversations = {}  # session_id -> [messages]
        self.memory_profiles = {}  # user_id -> profile_data
        
        logger.info(
            "database_service_initialized",
            database_url=database_url,
            backend_type="memory_fallback"
        )
    
    async def initialize(self) -> bool:
        """
        Initialize database connection.
        
        Tries: SQLite → PostgreSQL → Memory fallback
        
        Returns:
            True if initialized
        """
        logger.info("database_initialize_start", database_url=self.database_url)
        
        try:
            # Try SQLite first (stdlib, always available)
            if "sqlite" in self.database_url:
                return await self._init_sqlite()
            
            # Try PostgreSQL
            elif "postgresql" in self.database_url or "postgres" in self.database_url:
                return await self._init_postgresql()
            
            # Fallback to memory
            logger.warning("database_unknown_url_using_memory", url=self.database_url)
            self.backend_type = "memory"
            return True
            
        except Exception as e:
            logger.error("database_initialize_failed", error=str(e))
            self.backend_type = "memory"
            return True  # Memory fallback always works
    
    async def _init_sqlite(self) -> bool:
        """Initialize SQLite connection."""
        try:
            import aiosqlite
            
            # Create data directory if needed
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            self.connection = await aiosqlite.connect(str(db_file))
            self.backend_type = "sqlite"
            
            # Create tables
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    language TEXT DEFAULT 'es',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    country TEXT,
                    visa_type TEXT,
                    academic_level TEXT,
                    russian_level TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self.connection.commit()
            logger.info("database_sqlite_initialized", db_path=self.db_path)
            return True
            
        except ImportError:
            logger.warning("aiosqlite_not_installed_using_memory")
            self.backend_type = "memory"
            return True
        except Exception as e:
            logger.error("database_sqlite_init_failed", error=str(e))
            self.backend_type = "memory"
            return True
    
    async def _init_postgresql(self) -> bool:
        """Initialize PostgreSQL connection."""
        try:
            import asyncpg
            
            # Parse connection string (simplified)
            # Format: postgresql://user:password@localhost:5432/dbname
            try:
                connection = await asyncpg.connect(self.database_url)
                self.connection = connection
                self.backend_type = "postgresql"
                
                # Create tables
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        language TEXT DEFAULT 'es',
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await connection.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id TEXT PRIMARY KEY,
                        country TEXT,
                        visa_type TEXT,
                        academic_level TEXT,
                        russian_level TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                logger.info("database_postgresql_initialized")
                return True
                
            except asyncpg.PostgresError as e:
                logger.error("database_postgresql_connection_failed", error=str(e))
                self.backend_type = "memory"
                return True
                
        except ImportError:
            logger.warning("asyncpg_not_installed_using_memory")
            self.backend_type = "memory"
            return True
        except Exception as e:
            logger.error("database_postgresql_init_failed", error=str(e))
            self.backend_type = "memory"
            return True
    
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        language: str = "es"
    ) -> Dict[str, Any]:
        """
        Save conversation message.
        
        Args:
            session_id: Conversation session ID
            role: Message role (user/assistant)
            content: Message content
            language: Language code (default: es)
            
        Returns:
            Dict with saved message info
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("session_id must be non-empty string", field="session_id")
        if not role or role not in ["user", "assistant"]:
            raise ValidationError("role must be 'user' or 'assistant'", field="role")
        if not content or not isinstance(content, str):
            raise ValidationError("content must be non-empty string", field="content")
        
        logger.info(
            "message_save_start",
            session_id=session_id,
            role=role,
            content_length=len(content)
        )
        
        try:
            if self.backend_type == "sqlite" and self.connection:
                cursor = await self.connection.execute(
                    "INSERT INTO conversations (session_id, role, content, language) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, language)
                )
                await self.connection.commit()
                message_id = cursor.lastrowid
                logger.info("message_save_success", session_id=session_id, id=message_id, backend="sqlite")
                return {
                    "id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            elif self.backend_type == "postgresql" and self.connection:
                result = await self.connection.fetchval(
                    "INSERT INTO conversations (session_id, role, content, language) VALUES ($1, $2, $3, $4) RETURNING id",
                    session_id, role, content, language
                )
                message_id = result
                logger.info("message_save_success", session_id=session_id, id=message_id, backend="postgresql")
                return {
                    "id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                # Memory fallback
                if session_id not in self.memory_conversations:
                    self.memory_conversations[session_id] = []
                
                message_id = len(self.memory_conversations[session_id]) + 1
                msg = {
                    "id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.memory_conversations[session_id].append(msg)
                logger.info("message_save_success", session_id=session_id, id=message_id, backend="memory")
                return msg
                
        except Exception as e:
            logger.error("message_save_failed", session_id=session_id, error=str(e))
            raise AppError(f"Failed to save message: {str(e)}", context={"session_id": session_id})
    
    async def get_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            session_id: Conversation session ID
            limit: Max messages to return (default: 50)
            
        Returns:
            List of messages ordered by timestamp
        """
        if not session_id or not isinstance(session_id, str):
            raise ValidationError("session_id must be non-empty string", field="session_id")
        if limit <= 0:
            raise ValidationError("limit must be positive", field="limit")
        
        logger.info("history_get_start", session_id=session_id, limit=limit)
        
        try:
            if self.backend_type == "sqlite" and self.connection:
                cursor = await self.connection.execute(
                    "SELECT id, session_id, role, content, language, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, limit)
                )
                rows = await cursor.fetchall()
                messages = [
                    {
                        "id": r[0],
                        "session_id": r[1],
                        "role": r[2],
                        "content": r[3],
                        "language": r[4],
                        "timestamp": r[5]
                    }
                    for r in rows
                ]
                logger.info("history_get_success", session_id=session_id, count=len(messages), backend="sqlite")
                return list(reversed(messages))  # Reverse to get chronological order
            
            elif self.backend_type == "postgresql" and self.connection:
                rows = await self.connection.fetch(
                    "SELECT id, session_id, role, content, language, timestamp FROM conversations WHERE session_id = $1 ORDER BY timestamp DESC LIMIT $2",
                    session_id, limit
                )
                messages = [
                    {
                        "id": r["id"],
                        "session_id": r["session_id"],
                        "role": r["role"],
                        "content": r["content"],
                        "language": r["language"],
                        "timestamp": r["timestamp"]
                    }
                    for r in rows
                ]
                logger.info("history_get_success", session_id=session_id, count=len(messages), backend="postgresql")
                return list(reversed(messages))
            
            else:
                # Memory fallback
                messages = self.memory_conversations.get(session_id, [])
                messages = sorted(messages, key=lambda m: m["timestamp"], reverse=True)[:limit]
                logger.info("history_get_success", session_id=session_id, count=len(messages), backend="memory")
                return list(reversed(messages))
                
        except Exception as e:
            logger.error("history_get_failed", session_id=session_id, error=str(e))
            raise AppError(f"Failed to get history: {str(e)}", context={"session_id": session_id})
    
    async def save_profile(
        self,
        user_id: str,
        profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save user profile.
        
        Args:
            user_id: User ID
            profile_data: Profile data (country, visa_type, academic_level, russian_level)
            
        Returns:
            Dict with saved profile info
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("user_id must be non-empty string", field="user_id")
        
        logger.info("profile_save_start", user_id=user_id, fields=len(profile_data))
        
        try:
            country = profile_data.get("country")
            visa_type = profile_data.get("visa_type")
            academic_level = profile_data.get("academic_level")
            russian_level = profile_data.get("russian_level")
            
            if self.backend_type == "sqlite" and self.connection:
                await self.connection.execute(
                    """INSERT OR REPLACE INTO user_profiles 
                       (user_id, country, visa_type, academic_level, russian_level, updated_at)
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (user_id, country, visa_type, academic_level, russian_level)
                )
                await self.connection.commit()
                logger.info("profile_save_success", user_id=user_id, backend="sqlite")
                return {
                    "user_id": user_id,
                    "country": country,
                    "visa_type": visa_type,
                    "academic_level": academic_level,
                    "russian_level": russian_level,
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            elif self.backend_type == "postgresql" and self.connection:
                await self.connection.execute(
                    """INSERT INTO user_profiles 
                       (user_id, country, visa_type, academic_level, russian_level)
                       VALUES ($1, $2, $3, $4, $5)
                       ON CONFLICT(user_id) DO UPDATE SET
                       country=$2, visa_type=$3, academic_level=$4, russian_level=$5, updated_at=CURRENT_TIMESTAMP""",
                    user_id, country, visa_type, academic_level, russian_level
                )
                logger.info("profile_save_success", user_id=user_id, backend="postgresql")
                return {
                    "user_id": user_id,
                    "country": country,
                    "visa_type": visa_type,
                    "academic_level": academic_level,
                    "russian_level": russian_level,
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            else:
                # Memory fallback
                self.memory_profiles[user_id] = {
                    "user_id": user_id,
                    "country": country,
                    "visa_type": visa_type,
                    "academic_level": academic_level,
                    "russian_level": russian_level,
                    "updated_at": datetime.utcnow().isoformat()
                }
                logger.info("profile_save_success", user_id=user_id, backend="memory")
                return self.memory_profiles[user_id]
                
        except Exception as e:
            logger.error("profile_save_failed", user_id=user_id, error=str(e))
            raise AppError(f"Failed to save profile: {str(e)}", context={"user_id": user_id})
    
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile.
        
        Args:
            user_id: User ID
            
        Returns:
            Profile data or None if not found
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationError("user_id must be non-empty string", field="user_id")
        
        logger.info("profile_get_start", user_id=user_id)
        
        try:
            if self.backend_type == "sqlite" and self.connection:
                cursor = await self.connection.execute(
                    "SELECT user_id, country, visa_type, academic_level, russian_level, updated_at FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    profile = {
                        "user_id": row[0],
                        "country": row[1],
                        "visa_type": row[2],
                        "academic_level": row[3],
                        "russian_level": row[4],
                        "updated_at": row[5]
                    }
                    logger.info("profile_get_success", user_id=user_id, found=True, backend="sqlite")
                    return profile
                else:
                    logger.info("profile_get_success", user_id=user_id, found=False, backend="sqlite")
                    return None
            
            elif self.backend_type == "postgresql" and self.connection:
                row = await self.connection.fetchrow(
                    "SELECT user_id, country, visa_type, academic_level, russian_level, updated_at FROM user_profiles WHERE user_id = $1",
                    user_id
                )
                if row:
                    profile = dict(row)
                    logger.info("profile_get_success", user_id=user_id, found=True, backend="postgresql")
                    return profile
                else:
                    logger.info("profile_get_success", user_id=user_id, found=False, backend="postgresql")
                    return None
            
            else:
                # Memory fallback
                profile = self.memory_profiles.get(user_id)
                logger.info("profile_get_success", user_id=user_id, found=profile is not None, backend="memory")
                return profile
                
        except Exception as e:
            logger.error("profile_get_failed", user_id=user_id, error=str(e))
            raise AppError(f"Failed to get profile: {str(e)}", context={"user_id": user_id})
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get database service status.
        
        Returns:
            Dict with backend info and statistics
        """
        logger.info("database_status_check")
        
        try:
            status = {
                "backend_type": self.backend_type,
                "connected": self.connection is not None,
                "database_url": self.database_url,
            }
            
            if self.backend_type == "sqlite" and self.connection:
                cursor = await self.connection.execute("SELECT COUNT(*) FROM conversations")
                conv_count = (await cursor.fetchone())[0]
                cursor = await self.connection.execute("SELECT COUNT(*) FROM user_profiles")
                prof_count = (await cursor.fetchone())[0]
                status.update({
                    "conversations_count": conv_count,
                    "profiles_count": prof_count,
                })
            
            elif self.backend_type == "postgresql" and self.connection:
                conv_count = await self.connection.fetchval("SELECT COUNT(*) FROM conversations")
                prof_count = await self.connection.fetchval("SELECT COUNT(*) FROM user_profiles")
                status.update({
                    "conversations_count": conv_count,
                    "profiles_count": prof_count,
                })
            
            else:
                status.update({
                    "conversations_count": len(self.memory_conversations),
                    "profiles_count": len(self.memory_profiles),
                })
            
            logger.info("database_status_retrieved", backend=self.backend_type)
            return status
            
        except Exception as e:
            logger.error("database_status_failed", error=str(e))
            raise AppError(f"Failed to get database status: {str(e)}")
