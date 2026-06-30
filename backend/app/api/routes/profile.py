"""
User Profile routes.

Handles user profile management, preferences, and personalization recommendations.

Persistence Strategy:
- ProfileService: Primary storage (always available, no dependencies)
- DatabaseService: Optional complementary persistence (background tasks, graceful fallback)
  - Enabled via settings.enable_database and settings.database_url
  - Uses FastAPI BackgroundTasks for non-blocking persistence (safe shutdown guarantee)
  - Falls back to memory if database unavailable or not configured
  - No impact on HTTP response contract or latency
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
import asyncio

from app.api.models import ProfileUpdateRequest, ProfileResponse, UserProfile
from app.api.dependencies import get_profile_service, get_database_service
from app.domain.exceptions import ValidationError, AppError
from app.config.settings import settings
from app.config.logging_config import get_logger

logger = get_logger(__name__)


# ================== BACKGROUND TASK HELPERS ==================

def _persist_user_profile(db_service, user_id: str, profile_data: dict):
    """Background task: Persist user profile to database.
    
    Runs in background, guaranteed to complete before server shutdown.
    Failures are logged but don't affect the HTTP response.
    """
    if not settings.enable_database:
        return
    
    try:
        # Create new event loop for this background task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(
            db_service.save_profile(
                user_id=user_id,
                profile_data=profile_data
            )
        )
        
        logger.info("user_profile_persisted_to_database", user_id=user_id)
    except Exception as e:
        logger.warning("database_profile_save_failed", error=str(e), user_id=user_id)
    finally:
        loop.close()

router = APIRouter()


@router.post("/api/users/profile")
async def create_user_profile(profile: UserProfile):
    """Crear perfil de usuario personalizado (legacy endpoint)."""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")


@router.get("/api/users/profile/{user_id}")
async def get_profile(
    user_id: str,
    profile_service = Depends(get_profile_service),
    database_service = Depends(get_database_service)
) -> ProfileResponse:
    """Get user profile and personalization data.
    
    Tries: DatabaseService → ProfileService (fallback)
    """
    try:
        result = None
        
        # Try database first if enabled
        if settings.enable_database:
            try:
                result = await database_service.get_profile(user_id)
                if result:
                    logger.info("profile_retrieved_from_database", user_id=user_id)
            except Exception as e:
                logger.warning("database_profile_lookup_failed", error=str(e), user_id=user_id)
                # Fall through to profile_service
        
        # Fallback to profile service if DB didn't return anything
        if result is None:
            result = profile_service.get_profile(user_id)
            logger.info("profile_retrieved_from_memory", user_id=user_id)
        
        return ProfileResponse(**result)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting profile: {str(e)}")


@router.put("/api/users/profile/{user_id}")
async def update_profile(
    user_id: str,
    data: ProfileUpdateRequest,
    background_tasks: BackgroundTasks,
    profile_service = Depends(get_profile_service),
    database_service = Depends(get_database_service)
) -> dict:
    """Update user profile with preferences.
    
    Persistence:
    - ProfileService: Primary (updated immediately, synchronous)
    - DatabaseService: Background persistence (if enabled, non-blocking)
    """
    try:
        # Update profile in memory (primary store)
        result = profile_service.update_profile(user_id, data.model_dump())
        
        # Queue background task for async database persistence (non-blocking)
        if settings.enable_database:
            background_tasks.add_task(
                _persist_user_profile,
                database_service,
                user_id,
                data.model_dump()
            )
            logger.info("profile_persistence_queued_for_background", user_id=user_id)
        
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


@router.get("/api/users/profile/{user_id}/tips")
async def get_personalization_tips(
    user_id: str,
    context: str = None,
    profile_service = Depends(get_profile_service)
) -> dict:
    """Get personalized tips and recommendations."""
    try:
        tips = profile_service.get_personalization_tips(user_id, context)
        return {
            "user_id": user_id,
            "context": context,
            "tips": tips,
            "tips_count": len(tips)
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting tips: {str(e)}")
