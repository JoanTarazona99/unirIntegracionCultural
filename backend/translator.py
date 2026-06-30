"""
Módulo de Traducción Multiidioma para Asistente RAG
Soporta traducción de respuestas a múltiples idiomas
"""

from typing import Dict, List, Optional
import os
import re

# Idiomas soportados con códigos ISO
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'pt': 'Português',
    'it': 'Italiano',
    'ru': 'Русский',
    'zh': '中文',
    'ja': '日本語',
    'ar': 'العربية',
    'ko': '한국어',
    'tr': 'Türkçe',
    'pl': 'Polski',
    'nl': 'Nederlands',
    'vi': 'Tiếng Việt'
}

class MultiLanguageTranslator:
    """Traductor multiidioma para respuestas RAG"""
    
    def __init__(self):
        self.language_map = SUPPORTED_LANGUAGES
        # Inicializar traduciones estáticas SIEMPRE
        self.static_translations = self._load_static_translations()
        self.try_import_translator()
    
    def try_import_translator(self):
        """Intentar importar googletrans para traducción"""
        try:
            from google_trans_new import google_translator
            self.translator = google_translator()
            self.has_translator = True
            print("[TRANSLATOR] google_trans_new loaded successfully")
        except (ImportError, Exception) as e:
            print(f"[TRANSLATOR] google_trans_new not available ({str(e)}). Using static translations.")
            self.has_translator = False
            self.translator = None
    
    def _load_static_translations(self) -> Dict:
        """Cargar diccionario estático de traducciones comunes"""
        return {
            'en': {
                # Frases oficiales
                'INFORMACIÓN OFICIAL SOBRE': 'OFFICIAL INFORMATION ABOUT',
                'Información oficial sobre': 'Official information about',
                'ОФИЦИАЛЬНАЯ ИНФОРМАЦИЯ О': 'OFFICIAL INFORMATION ABOUT',
                
                # Palabras clave comunes
                'Fuente': 'Source',
                'fuente': 'source',
                'Para mas información': 'For more information',
                'Para más información': 'For more information',
                'visite': 'visit',
                'contacte a': 'contact',
                'la administración': 'the administration',
                'el acministración': 'the administration',
                
                # MFC
                'МФЦ': 'MFC',
                'МФЦ находится': 'MFC is located',
                'Адреса МФЦ': 'MFC Addresses',
                'мfц': 'MFC',
                'Главный офис': 'Main Office',
                'Филиал': 'Branch',
                'Время работы': 'Working Hours',
                'ПН-ПТ': 'MON-FRI',
                'СБ': 'SAT',
                'Телефон': 'Phone',
                'ул.': 'str.',
                'д.': 'building',
                'корп.': 'building',
                'пр.': 'ave.',
                
                # Dormitorio
                'Dormitorio': 'Dormitory',
                'dormitorio': 'dormitory',
                'ОБЩЕЖИТИЕ': 'DORMITORY',
                'Общежитие': 'Dormitory',
                'Условия': 'Conditions',
                'условия': 'conditions',
                'человека на комнату': 'people per room',
                'Кровать': 'Bed',
                'Шкаф': 'Cabinet',
                'письменный стол': 'desk',
                'Стоимость': 'Cost',
                'стоимость': 'cost',
                'рублей': 'rubles',
                'руб': 'rub',
                'Комендантский час': 'Curfew',
                'Будни': 'Weekdays',
                'Выходные': 'Weekends',
                
                # Otros
                'Registración': 'Registration',
                'Póliza médica': 'Medical insurance',
                'Visa': 'Visa',
                'Documentos': 'Documents',
                'Процесс': 'Process',
                'Шаг': 'Step',
                'Требования': 'Requirements',
                'Минимум': 'Minimum',
                'Рекомендуется': 'Recommended',
                'Обязательно': 'Required',
                'Интенсив': 'Intensive',
                'Доступен': 'Available',
                'Для': 'For',
                'Студента': 'Student',
                'Студентов': 'Students',
                'Иностранных': 'Foreign',
                'Иностранцев': 'Foreigners',
                'Иностранного': 'Foreign',
                
                # Nivel de ruso
                'Nivel de ruso': 'Russian level',
                'Уровень': 'Level',
                'Языка': 'Language',
                'Русского': 'Russian',
                'ТРКИ': 'TRKI',
                'Бакалавриат': 'Bachelor',
                'Магистратура': 'Master',
                'Аспирантура': 'PhD',
                'Сертификат': 'Certificate',
                'Уровень B1': 'Level B1',
                'Уровень B2': 'Level B2',
                'Уровень C1': 'Level C1',
                
                # Palabras generales
                'и': 'and',
                'о': 'about',
                'в': 'in',
                'на': 'at',
                'с': 'from',
                'по': 'by',
                'от': 'from',
                'до': 'until',
                'между': 'between',
                'после': 'after',
                'перед': 'before',
            },
            'es': {},  # Español es el idioma original
            'fr': {
                'INFORMACIÓN OFICIAL SOBRE': 'INFORMATION OFFICIELLE SUR',
                'Fuente': 'Source',
                'Para mas información': 'Pour plus d\'informations',
                'visite': 'visite',
                'contacte a': 'contactez',
                'Registración': 'Enregistrement',
                'Dormitorio': 'Dortoir',
                'МФЦ': 'MFC',
                'Visa': 'Visa'
            },
            'de': {
                'INFORMACIÓN OFICIAL SOBRE': 'OFFIZIELLE INFORMATIONEN ÜBER',
                'Fuente': 'Quelle',
                'Para mas información': 'Für weitere Informationen',
                'visite': 'besuchen',
                'Registración': 'Registrierung',
                'Dormitorio': 'Wohnheim',
                'МФЦ': 'MFC',
                'Visa': 'Visum'
            },
            'pt': {
                'INFORMACIÓN OFICIAL SOBRE': 'INFORMAÇÃO OFICIAL SOBRE',
                'Fuente': 'Fonte',
                'Para mas información': 'Para mais informações',
                'visite': 'visite',
                'Registración': 'Registro',
                'Dormitorio': 'Dormitório',
                'МФЦ': 'MFC',
                'Visa': 'Visto'
            },
            'ru': {
                'INFORMACIÓN OFICIAL SOBRE': 'ОФИЦИАЛЬНАЯ ИНФОРМАЦИЯ О',
                'Fuente': 'Источник',
                'Para mas información': 'Для получения дополнительной информации',
                'visite': 'посетите',
                'Registración': 'Регистрация',
                'Dormitorio': 'Общежитие',
                'МФЦ': 'МФЦ',
                'Visa': 'Виза'
            }
        }
    
    def translate_text(self, text: str, target_language: str = 'en', source_language: str = 'es') -> str:
        """
        Traducir texto de un idioma a otro
        
        Args:
            text: Texto a traducir
            target_language: Idioma destino (código ISO)
            source_language: Idioma origen (default: español)
        
        Returns:
            Texto traducido
        """
        if target_language == source_language or target_language == 'es':
            return text
        
        if not self.has_translator:
            return self._translate_static(text, target_language)
        
        try:
            result = self.translator.translate(text, lang_src=source_language, lang_tgt=target_language)
            return result
        except Exception as e:
            print(f"Error en traducción: {e}")
            return self._translate_static(text, target_language)
    
    def _translate_static(self, text: str, target_language: str) -> str:
        """Traducción basada en diccionario estático - mejorada"""
        if target_language not in self.static_translations:
            return text
        
        translations = self.static_translations[target_language]
        result = text
        
        # Ordenar por longitud (palabras más largas primero) para evitar conflictos
        sorted_translations = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)
        
        for spanish, translated in sorted_translations:
            # Buscar y reemplazar (case-insensitive)
            pattern = r'\b' + re.escape(spanish) + r'\b'
            result = re.sub(pattern, translated, result, flags=re.IGNORECASE)
        
        return result
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Obtener lista de idiomas soportados"""
        return self.language_map
    
    def translate_response(self, response: str, target_language: str = 'en') -> Dict:
        """
        Traducir una respuesta completa a múltiples idiomas
        
        Args:
            response: Respuesta RAG
            target_language: Idioma principal adicional
        
        Returns:
            Dict con respuesta en español + traducciones
        """
        result = {
            'es': response,  # Original en español
            target_language: self.translate_text(response, target_language)
        }
        
        # Agregar inglés como idioma por defecto si no es el destino
        if target_language != 'en':
            result['en'] = self.translate_text(response, 'en')
        
        return result
    
    def translate_sources(self, sources: List[str], target_language: str = 'en') -> List[str]:
        """Traducir lista de fuentes"""
        return [self.translate_text(source, target_language) for source in sources]


def create_translator() -> MultiLanguageTranslator:
    """Factory para crear traductor"""
    return MultiLanguageTranslator()


if __name__ == "__main__":
    translator = create_translator()
    
    print("📚 Idiomas soportados:")
    for code, name in translator.get_supported_languages().items():
        print(f"  {code}: {name}")
    
    # Test de traducción
    test_text = "INFORMACIÓN OFICIAL SOBRE: Registración de estudiantes"
    print(f"\nTexto original (ES): {test_text}")
    
    for lang_code in ['en', 'fr', 'de', 'ru']:
        translated = translator.translate_text(test_text, lang_code)
        print(f"Traducción ({lang_code}): {translated}")
