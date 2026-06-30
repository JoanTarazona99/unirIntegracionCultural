"""
Profile Service: wrapper around PersonalizationEngine.

Manages user profiles, preferences, and personalization recommendations.
Does not modify the underlying PersonalizationEngine implementation.
"""

from typing import Any, Dict, Optional, List

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class ProfileService:
    """Service for user profile and personalization operations.
    
    Wraps PersonalizationEngine without modifying it.
    Provides clean interface for routers with structured logging.
    Handles user preference management and recommendations.
    """
    
    def __init__(self, personalization_engine):
        """Initialize with PersonalizationEngine instance.
        
        Args:
            personalization_engine: PersonalizationEngine instance from main.py
            
        Raises:
            ValidationError: If personalization_engine is not initialized
        """
        if personalization_engine is None:
            raise ValidationError(
                "PersonalizationEngine not initialized",
                field="personalization_engine",
                context={"reason": "personalization_engine is None"}
            )
        
        self.engine = personalization_engine
        logger.info(
            "profile_service_initialized",
            module_type=type(personalization_engine).__name__
        )
    
    def get_profile(self, user_id: str) -> Dict:
        """Get user profile and personalization data.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dict with user profile, preferences, and personalization
            
        Raises:
            ValidationError: If user_id is invalid
            AppError: If operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationError(
                "Invalid user_id",
                field="user_id",
                context={"received": user_id}
            )
        
        try:
            logger.info(
                "profile_get_start",
                user_id=user_id,
                user_id_length=len(user_id)
            )
            
            # Get from engine's user_profiles dictionary
            profile = self.engine.user_profiles.get(user_id)
            
            if profile is None:
                logger.warning(
                    "profile_not_found",
                    user_id=user_id
                )
                return {
                    "user_id": user_id,
                    "exists": False,
                    "message": "Profile not found - please create profile first"
                }
            
            logger.info(
                "profile_get_success",
                user_id=user_id,
                has_profile=True
            )
            
            return {
                "user_id": user_id,
                "exists": True,
                "profile": profile
            }
            
        except Exception as e:
            logger.error(
                "profile_get_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Profile retrieval failed: {str(e)}",
                context={"user_id": user_id},
                original_exception=e
            )
    
    def update_profile(self, user_id: str, data: Dict) -> Dict:
        """Update user profile with new preferences.
        
        Args:
            user_id: Unique user identifier
            data: Dict with profile data (country, visa_type, russian_level, etc.)
            
        Returns:
            Dict with {success: bool, user_id: str, updated_fields: list}
            
        Raises:
            ValidationError: If user_id or data is invalid
            AppError: If operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationError(
                "Invalid user_id",
                field="user_id",
                context={"received": user_id}
            )
        
        if not data or not isinstance(data, dict):
            raise ValidationError(
                "Invalid profile data",
                field="data",
                context={"received": type(data).__name__, "must_be": "dict"}
            )
        
        try:
            logger.info(
                "profile_update_start",
                user_id=user_id,
                fields_count=len(data)
            )
            
            # Create or update profile using engine
            profile = self.engine.create_profile(user_id, data)
            
            updated_fields = list(data.keys())
            
            logger.info(
                "profile_update_success",
                user_id=user_id,
                fields_updated=len(updated_fields)
            )
            
            return {
                "success": True,
                "user_id": user_id,
                "updated_fields": updated_fields,
                "profile": profile
            }
            
        except Exception as e:
            logger.error(
                "profile_update_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Profile update failed: {str(e)}",
                context={"user_id": user_id},
                original_exception=e
            )
    
    def get_personalization_tips(self, user_id: str, context: Optional[str] = None) -> List[str]:
        """Get personalized tips and recommendations for user.
        
        Args:
            user_id: Unique user identifier
            context: Optional context filter (e.g., 'administrative', 'housing')
            
        Returns:
            List of personalized tip strings
            
        Raises:
            ValidationError: If user_id is invalid
            AppError: If operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValidationError(
                "Invalid user_id",
                field="user_id",
                context={"received": user_id}
            )
        
        try:
            logger.info(
                "tips_get_start",
                user_id=user_id,
                context=context
            )
            
            # Get recommendations from engine
            recommendations = self.engine.get_personalized_recommendations(user_id)
            
            # Filter by context if provided
            tips = []
            for rec in recommendations:
                rec_type = rec.get("type", "")
                content = rec.get("content", "")
                
                if context is None or rec_type.startswith(context):
                    tips.append(content)
            
            logger.info(
                "tips_get_success",
                user_id=user_id,
                tips_count=len(tips)
            )
            
            return tips
            
        except Exception as e:
            logger.error(
                "tips_get_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Tips retrieval failed: {str(e)}",
                context={"user_id": user_id},
                original_exception=e
            )
    
    def get_status(self) -> Dict:
        """Get profile service status and statistics.
        
        Returns:
            Dict with {available: bool, profiles_count: int, engine_type: str}
        """
        try:
            logger.info("profile_status_check")
            
            profiles_count = len(self.engine.user_profiles) if hasattr(self.engine, 'user_profiles') else 0
            
            return {
                "available": True,
                "profiles_count": profiles_count,
                "engine_type": type(self.engine).__name__
            }
            
        except Exception as e:
            logger.error(
                "profile_status_failed",
                error=str(e)
            )
            return {
                "available": False,
                "error": str(e)
            }
