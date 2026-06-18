from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

# ==================== Conversation Memory ====================

@dataclass
class ConversationMessage:
    """Single conversation message"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)


class ConversationMemory:
    """
    Manages conversation history per session

    Features:
    - Store conversations by session_id
    - Keep last N messages per session
    - Support for multiple sessions
    """

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._conversations: Dict[str, List[ConversationMessage]] = {}

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> None:
        """
        Add message to conversation history

        Args:
            session_id: Unique session identifier
            role: 'user', 'assistant', or 'system'
            content: Message content
            metadata: Optional metadata (e.g., language, model used)
        """
        if session_id not in self._conversations:
            self._conversations[session_id] = []

        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )

        self._conversations[session_id].append(message)

        # Trim to max history
        if len(self._conversations[session_id]) > self.max_history:
            self._conversations[session_id] = self._conversations[session_id][-self.max_history:]

    def get_history(self, session_id: str) -> List[Dict]:
        """
        Get conversation history as list of dicts

        Returns:
            List of messages: [{'role': ..., 'content': ...}, ...]
        """
        if session_id not in self._conversations:
            return []

        return [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in self._conversations[session_id]
        ]

    def get_messages(self, session_id: str) -> List[ConversationMessage]:
        """Get raw message objects"""
        return self._conversations.get(session_id, [])

    def clear_session(self, session_id: str) -> None:
        """Clear history for a session"""
        if session_id in self._conversations:
            del self._conversations[session_id]

    def clear_all(self) -> None:
        """Clear all conversation history"""
        self._conversations.clear()

    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self._conversations)

    def get_message_count(self, session_id: str = None) -> int:
        """Get total messages, optionally filtered by session"""
        if session_id:
            return len(self._conversations.get(session_id, []))
        return sum(len(msgs) for msgs in self._conversations.values())

    def get_summary(self, session_id: str) -> Dict:
        """Get summary of session conversation"""
        messages = self._conversations.get(session_id, [])
        if not messages:
            return {"exists": False, "message_count": 0}

        user_msgs = sum(1 for m in messages if m.role == 'user')
        assistant_msgs = sum(1 for m in messages if m.role == 'assistant')

        return {
            "exists": True,
            "message_count": len(messages),
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "first_message": messages[0].timestamp if messages else None,
            "last_message": messages[-1].timestamp if messages else None
        }


# Global conversation memory instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory(max_history: int = 10) -> ConversationMemory:
    """Get or create global conversation memory instance"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory(max_history=max_history)
    return _conversation_memory


# ==================== Personalization Engine ====================

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
