from typing import List, Dict, Optional
from datetime import datetime

class PersonalizationEngine:
    """Motor de personalización de recomendaciones"""
    
    COUNTRY_PROFILES = {
        "Vietnam": {"priority_contexts": ["admin", "housing", "daily"], "language_support": "high"},
        "China": {"priority_contexts": ["academic", "housing"], "language_support": "high"},
        "Kazakhstan": {"priority_contexts": ["migration", "healthcare"], "language_support": "medium"},
        "Armenia": {"priority_contexts": ["academic", "communication"], "language_support": "low"},
        "Syria": {"priority_contexts": ["healthcare", "housing", "daily"], "language_support": "high"},
        "Egypt": {"priority_contexts": ["academic", "daily"], "language_support": "medium"},
        "Morocco": {"priority_contexts": ["migration", "daily"], "language_support": "high"},
        "Nigeria": {"priority_contexts": ["academic", "healthcare"], "language_support": "high"},
    }
    
    VISA_REQUIREMENTS = {
        "student": ["migration_registration", "health_insurance", "housing"],
        "study_visit": ["migration_registration", "temporary_registration"],
        "exchange": ["academic_schedule", "housing", "travel_documents"]
    }
    
    ACADEMIC_LEVEL_CONTEXTS = {
        "bachelor": ["academic_schedule", "exams", "coursework", "housing"],
        "master": ["research", "academic_advising", "departmental_procedures"],
        "phd": ["research", "library_access", "academic_freedom"]
    }
    
    RUSSIAN_LEVEL_ADAPTATIONS = {
        "A1": {"text_format": "transliterated", "simplification": "high"},
        "A2": {"text_format": "bilingual", "simplification": "medium"},
        "B1": {"text_format": "russian_main", "simplification": "low"},
        "B2": {"text_format": "russian_only", "simplification": "none"},
        "C1": {"text_format": "russian_only", "simplification": "none"}
    }
    
    def __init__(self):
        self.user_profiles = {}
    
    def create_profile(self, user_id: str, profile: Dict) -> Dict:
        """Crear perfil personalizado de usuario"""
        country = profile.get("country", "")
        visa_type = profile.get("visa_type", "student")
        academic_level = profile.get("academic_level", "bachelor")
        russian_level = profile.get("russian_level", "A1")
        
        personalization = {
            "user_id": user_id,
            "profile": profile,
            "priority_contexts": self._get_priority_contexts(
                country, visa_type, academic_level
            ),
            "text_adaptation": self.RUSSIAN_LEVEL_ADAPTATIONS.get(russian_level, {}),
            "recommended_phrases": 50,
            "checklist_templates": self._get_checklists(visa_type, country),
            "created_at": datetime.now().isoformat()
        }
        
        self.user_profiles[user_id] = personalization
        return personalization
    
    def _get_priority_contexts(self, country: str, visa_type: str, academic_level: str) -> List[str]:
        """Obtener contextos prioritarios según perfil"""
        contexts = []
        
        # Añadir contextos por país
        if country in self.COUNTRY_PROFILES:
            contexts.extend(self.COUNTRY_PROFILES[country]["priority_contexts"])
        
        # Añadir contextos por visa
        if visa_type in self.VISA_REQUIREMENTS:
            contexts.extend([c.replace("_", "") for c in self.VISA_REQUIREMENTS[visa_type]])
        
        # Añadir contextos por nivel académico
        if academic_level in self.ACADEMIC_LEVEL_CONTEXTS:
            contexts.extend(self.ACADEMIC_LEVEL_CONTEXTS[academic_level])
        
        return list(set(contexts))  # Eliminar duplicados
    
    def _get_checklists(self, visa_type: str, country: str) -> Dict:
        """Obtener plantillas de checklist personalizadas"""
        checklists = {
            "first_days": [
                "Registrarse en МФЦ",
                "Obtener tarjeta de seguro médico",
                "Recoger llaves del dormitorio",
                "Registrarse en decanato"
            ],
            "administrative": [
                "Renovar registro migratorio",
                "Registrar cambio de domicilio",
                "Actualizar datos en universidad"
            ]
        }
        
        # Adaptar según tipo de visa
        if visa_type == "study_visit":
            checklists["first_days"].append("Verificar duración de estadía")
        
        return checklists
    
    def get_personalized_recommendations(self, user_id: str) -> List[Dict]:
        """Obtener recomendaciones personalizadas para usuario"""
        if user_id not in self.user_profiles:
            return []
        
        profile_data = self.user_profiles[user_id]
        recommendations = []
        
        # Tips culturales
        country = profile_data["profile"].get("country")
        if country == "Vietnam":
            recommendations.append({
                "type": "cultural_tip",
                "content": "En Rusia, el horario es muy importante. Llega a tiempo a los eventos académicos."
            })
        elif country == "China":
            recommendations.append({
                "type": "cultural_tip",
                "content": "Establece relaciones formales primero. La camaradería viene después."
            })
        
        # Tips de logística
        russian_level = profile_data["profile"].get("russian_level", "A1")
        if russian_level in ["A1", "A2"]:
            recommendations.append({
                "type": "practical_tip",
                "content": "Descarga la app Yandex.Translate o Google Translate para comunicaciones rápidas."
            })
        
        # Recordatorios temporales
        recommendations.append({
            "type": "reminder",
            "content": "Próxima tarea: Inscribirse en las clases del semestre",
            "deadline": "2026-03-10"
        })
        
        return recommendations
    
    def generate_checklist(self, user_id: str, checklist_type: str = "first_days") -> List[Dict]:
        """Generar checklist personalizado"""
        if user_id not in self.user_profiles:
            return []
        
        profile_data = self.user_profiles[user_id]
        checklists = profile_data.get("checklist_templates", {})
        
        items = checklists.get(checklist_type, [])
        return [
            {
                "id": i,
                "task": item,
                "completed": False,
                "priority": "high" if i <= 3 else "medium"
            }
            for i, item in enumerate(items, 1)
        ]

class ContextAwareResponseFormatter:
    """Formateador de respuestas sensibles al contexto"""
    
    def __init__(self):
        self.formats = {
            "A1": "simple",      # Texto muy simple
            "A2": "bilingual",   # Ruso + inglés
            "B1": "standard",    # Ruso estándar
            "B2": "detailed",    # Ruso con detalles
            "C1": "academic"     # Ruso académico
        }
    
    def format_response(self, base_response: str, russian_level: str, 
                       include_transliteration: bool = False) -> str:
        """Formatear respuesta según nivel de ruso"""
        
        format_type = self.formats.get(russian_level, "standard")
        
        if format_type == "simple":
            return self._simplify_text(base_response)
        elif format_type == "bilingual":
            return self._add_english_translation(base_response)
        elif format_type == "standard":
            return base_response
        elif format_type == "detailed":
            return self._add_details(base_response)
        elif format_type == "academic":
            return self._academicize_text(base_response)
        
        return base_response
    
    def _simplify_text(self, text: str) -> str:
        # Simplificar vocabulario complejo
        replacements = {
            "документ": "бумага",
            "процедура": "шаги",
            "учреждение": "место"
        }
        for complex_word, simple_word in replacements.items():
            text = text.replace(complex_word, simple_word)
        return text
    
    def _add_english_translation(self, text: str) -> str:
        # En producción, usar API de traducción
        return f"{text}\n[Translation needed]"
    
    def _add_details(self, text: str) -> str:
        return f"{text}\n\nДругие детали...\n"
    
    def _academicize_text(self, text: str) -> str:
        return f"Уважаемый студент,\n\n{text}"
