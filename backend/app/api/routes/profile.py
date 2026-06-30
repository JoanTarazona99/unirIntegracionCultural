"""
User Profile routes.

Handles user profile management, preferences, and personalization recommendations.
Integrates with ProfileService for all operations.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.api.models import ProfileUpdateRequest, ProfileResponse, UserProfile
from app.api.dependencies import get_profile_service
from app.domain.exceptions import ValidationError, AppError

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
    profile_service = Depends(get_profile_service)
) -> ProfileResponse:
    """Get user profile and personalization data."""
    try:
        result = profile_service.get_profile(user_id)
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
    profile_service = Depends(get_profile_service)
) -> dict:
    """Update user profile with preferences."""
    try:
        result = profile_service.update_profile(user_id, data.model_dump())
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
