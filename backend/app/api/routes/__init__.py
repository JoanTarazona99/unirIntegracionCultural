"""
Route routers for KubGU Assistant API.

Contains all endpoint handlers organized by domain.
"""

from .health import router as health_router
from .phrases import router as phrases_router
from .profile import router as profile_router
from .chat import router as chat_router
from .translation import router as translation_router
from .audio import router as audio_router
from .info import router as info_router

__all__ = [
    "health_router",
    "phrases_router",
    "profile_router",
    "chat_router",
    "translation_router",
    "audio_router",
    "info_router",
]
