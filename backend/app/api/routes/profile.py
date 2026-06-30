"""
User profile routes.
"""

from fastapi import APIRouter, HTTPException

from app.api.models import UserProfile

router = APIRouter()


@router.post("/api/users/profile")
async def create_user_profile(profile: UserProfile):
    """Crear perfil de usuario personalizado."""
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
