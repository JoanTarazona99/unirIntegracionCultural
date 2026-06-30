"""
Audio Service: wrapper around AudioManager (TTS/STT).

Manages text-to-speech and speech-to-text operations.
Handles optional dependencies gracefully.
"""

from typing import Any, Dict, Optional
import base64

from app.config.logging_config import get_logger
from app.domain.exceptions import ValidationError, AppError

logger = get_logger(__name__)


class AudioService:
    """Service for audio (TTS/STT) operations.
    
    Wraps AudioManager without modifying it.
    Provides clean interface for routers with structured logging.
    Handles optional TTS/STT availability gracefully.
    """
    
    def __init__(self, audio_manager):
        """Initialize with AudioManager instance.
        
        Args:
            audio_manager: AudioManager instance from main.py
            
        Raises:
            ValidationError: If audio_manager is not initialized
        """
        if audio_manager is None:
            raise ValidationError(
                "AudioManager not initialized",
                field="audio_manager",
                context={"reason": "audio_manager is None"}
            )
        
        self.manager = audio_manager
        logger.info(
            "audio_service_initialized",
            module_type=type(audio_manager).__name__
        )
    
    def text_to_speech(self, text: str, language: str = "ru") -> Dict:
        """Convert text to speech.
        
        Args:
            text: Text to synthesize
            language: Target language code (default: ru)
            
        Returns:
            Dict with {success: bool, audio_path: str, language: str}
            or error info if TTS not available
            
        Raises:
            ValidationError: If text is invalid
            AppError: If operation fails
        """
        if not text or not isinstance(text, str):
            raise ValidationError(
                "Invalid text for TTS",
                field="text",
                context={"received": type(text).__name__, "must_be": "non-empty string"}
            )
        
        if not language or not isinstance(language, str):
            raise ValidationError(
                "Invalid language",
                field="language",
                context={"received": language}
            )
        
        try:
            logger.info(
                "tts_start",
                text_length=len(text),
                language=language
            )
            
            # Check if TTS is available
            if not hasattr(self.manager, 'tts') or self.manager.tts is None:
                logger.warning(
                    "tts_not_available",
                    text_length=len(text),
                    language=language
                )
                return {
                    "success": False,
                    "available": False,
                    "message": "TTS not available",
                    "text": text,
                    "language": language
                }
            
            # Synthesize using manager's TTS
            # TTS synthesize typically returns audio_path or None
            audio_path = self.manager.tts.synthesize(text, phrase_id=hash(text) % 10000)
            
            if audio_path:
                logger.info(
                    "tts_success",
                    text_length=len(text),
                    language=language,
                    audio_path=audio_path
                )
                
                return {
                    "success": True,
                    "audio_path": audio_path,
                    "language": language,
                    "text": text
                }
            else:
                logger.warning(
                    "tts_failed_no_output",
                    text_length=len(text),
                    language=language
                )
                
                return {
                    "success": False,
                    "message": "TTS synthesis failed",
                    "text": text,
                    "language": language
                }
            
        except Exception as e:
            logger.error(
                "tts_failed",
                text_length=len(text),
                language=language,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Text-to-speech failed: {str(e)}",
                context={"text_length": len(text), "language": language},
                original_exception=e
            )
    
    def speech_to_text(self, audio_file_path: str) -> Dict:
        """Convert speech to text.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dict with {success: bool, transcription: str, confidence: float}
            or error info if STT not available
            
        Raises:
            ValidationError: If audio_file_path is invalid
            AppError: If operation fails
        """
        if not audio_file_path or not isinstance(audio_file_path, str):
            raise ValidationError(
                "Invalid audio file path",
                field="audio_file_path",
                context={"received": audio_file_path}
            )
        
        try:
            logger.info(
                "stt_start",
                audio_file_path=audio_file_path
            )
            
            # Check if STT is available
            if not hasattr(self.manager, 'stt') or self.manager.stt is None:
                logger.warning(
                    "stt_not_available",
                    audio_file_path=audio_file_path
                )
                return {
                    "success": False,
                    "available": False,
                    "message": "STT not available",
                    "audio_file_path": audio_file_path
                }
            
            # Recognize from file using manager's STT
            transcription = self.manager.stt.recognize(audio_file_path)
            
            if transcription:
                logger.info(
                    "stt_success",
                    audio_file_path=audio_file_path,
                    transcription_length=len(transcription)
                )
                
                return {
                    "success": True,
                    "transcription": transcription,
                    "confidence": 0.95,  # Placeholder confidence
                    "language": "ru"
                }
            else:
                logger.warning(
                    "stt_failed_no_output",
                    audio_file_path=audio_file_path
                )
                
                return {
                    "success": False,
                    "message": "STT recognition failed",
                    "audio_file_path": audio_file_path
                }
            
        except Exception as e:
            logger.error(
                "stt_failed",
                audio_file_path=audio_file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            raise AppError(
                f"Speech-to-text failed: {str(e)}",
                context={"audio_file_path": audio_file_path},
                original_exception=e
            )
    
    def get_status(self) -> Dict:
        """Get audio service status and capabilities.
        
        Returns:
            Dict with {available: bool, tts_available: bool, stt_available: bool}
        """
        try:
            logger.info("audio_status_check")
            
            tts_available = hasattr(self.manager, 'tts') and self.manager.tts is not None
            stt_available = hasattr(self.manager, 'stt') and self.manager.stt is not None
            
            return {
                "available": True,
                "tts_available": tts_available,
                "stt_available": stt_available,
                "manager_type": type(self.manager).__name__
            }
            
        except Exception as e:
            logger.error(
                "audio_status_failed",
                error=str(e)
            )
            return {
                "available": False,
                "error": str(e)
            }
