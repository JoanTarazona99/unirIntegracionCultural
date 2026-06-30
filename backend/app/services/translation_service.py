"""
Translation Service: wrapper around MultiLanguageTranslator.

Encapsulates translation logic with clean interface and structured error handling.
Does not modify the underlying module.
"""

from typing import Dict

from app.config.logging_config import get_logger
from app.domain.exceptions import TranslationError

logger = get_logger(__name__)


class TranslationService:
    """Service for translation operations.
    
    Wraps MultiLanguageTranslator without modifying it.
    Handles errors with TranslationError exceptions.
    Provides clean interface for routers.
    """
    
    def __init__(self, translator):
        """Initialize with a MultiLanguageTranslator instance.
        
        Args:
            translator: MultiLanguageTranslator instance from main.py
            
        Raises:
            TranslationError: If translator is not initialized
        """
        if translator is None:
            raise TranslationError(
                "Translator not initialized",
                context={"reason": "translator is None"}
            )
        self.translator = translator
        logger.info("translation_service_initialized", module_type=type(translator).__name__)
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "es"
    ) -> str:
        """Translate text to target language.
        
        Args:
            text: Text to translate
            target_language: Target language code (ru, en, fr, etc.)
            source_language: Source language code (default: es)
            
        Returns:
            Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        try:
            if not text or not text.strip():
                logger.warning("translate_empty_text")
                return text
            
            logger.info(
                "translate_start",
                text_length=len(text),
                source_lang=source_language,
                target_lang=target_language
            )
            
            translated = self.translator.translate_text(
                text=text,
                target_language=target_language,
                source_language=source_language
            )
            
            logger.info("translate_success", output_length=len(translated))
            
            return translated
            
        except TranslationError:
            raise
        except Exception as e:
            logger.error(
                "translate_failed",
                error=str(e),
                text_sample=text[:50],
                target_language=target_language
            )
            raise TranslationError(
                f"Translation failed: {str(e)}",
                context={
                    "text_sample": text[:100],
                    "target_language": target_language,
                    "source_language": source_language
                }
            )
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages.
        
        Returns:
            Dict mapping language codes to language names
            
        Raises:
            TranslationError: If retrieval fails
        """
        try:
            logger.info("get_supported_languages")
            
            languages = self.translator.get_supported_languages()
            
            logger.info("get_supported_languages_success", count=len(languages))
            
            return languages
            
        except Exception as e:
            logger.error("get_supported_languages_failed", error=str(e))
            raise TranslationError(
                f"Failed to get supported languages: {str(e)}",
                context={"reason": "languages_retrieval"}
            )
    
    def get_status(self) -> Dict:
        """Get translation service status.
        
        Returns:
            Dict with service status and capabilities
        """
        try:
            languages = self.get_supported_languages()
            return {
                "available": True,
                "languages_count": len(languages),
                "language_codes": list(languages.keys())
            }
        except Exception as e:
            logger.error("translation_status_failed", error=str(e))
            return {
                "available": False,
                "error": str(e)
            }
