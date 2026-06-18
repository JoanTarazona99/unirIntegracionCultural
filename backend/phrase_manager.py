import json
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

class PhraseManager:
    """Gestor de la base de frases"""
    
    def __init__(self, phrases_file: str):
        self.phrases_file = Path(phrases_file)
        self.phrases = self._load_phrases()
        self.categories = self._extract_categories()
    
    def _load_phrases(self) -> List[Dict]:
        if self.phrases_file.exists():
            with open(self.phrases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _extract_categories(self) -> set:
        return set(p.get("category") for p in self.phrases if "category" in p)
    
    def get_phrases_by_category(self, category: str) -> List[Dict]:
        return [p for p in self.phrases if p.get("category") == category]
    
    def get_phrases_by_context(self, context_tag: str) -> List[Dict]:
        return [p for p in self.phrases if context_tag in p.get("context", [])]
    
    def search_phrase(self, query: str) -> List[Dict]:
        """Búsqueda simple por keyword"""
        query_lower = query.lower()
        results = []
        for phrase in self.phrases:
            if (query_lower in phrase.get("russian", "").lower() or 
                query_lower in phrase.get("english", "").lower()):
                results.append(phrase)
        return results
    
    def get_personalized_phrases(self, 
                                 country: str, 
                                 visa_type: str,
                                 academic_level: str,
                                 context_tags: List[str]) -> List[Dict]:
        """Obtener frases personalizadas según perfil"""
        personalized = []
        
        # Frases prioritarias según contexto
        for tag in context_tags:
            personalized.extend(self.get_phrases_by_context(tag))
        
        # Eliminar duplicados preservando orden
        seen = set()
        unique = []
        for p in personalized:
            if p["id"] not in seen:
                seen.add(p["id"])
                unique.append(p)
        
        return unique[:50]  # Limitar a 50 frases personalizadas
    
    def get_suggested_phrases(self, academic_level: str) -> List[Dict]:
        """Obtener frases sugeridas según nivel académico"""
        if academic_level in ["bachelor", "master"]:
            return self.get_phrases_by_context("учёба")
        return self.get_phrases_by_context("админ")

class UserPreferences:
    """Gestión de preferencias de usuario"""
    
    def __init__(self):
        self.preferences = {}
    
    def create_user(self, user_id: str, profile: Dict):
        self.preferences[user_id] = {
            "country": profile.get("country"),
            "visa_type": profile.get("visa_type"),
            "academic_level": profile.get("academic_level"),
            "russian_level": profile.get("russian_level"),
            "housing_type": profile.get("housing_type"),
            "preferences": {
                "text_format": "standard",  # standard, transliterated, bilingual
                "audio_enabled": True,
                "tips_enabled": True
            }
        }
        return self.preferences[user_id]
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        return self.preferences.get(user_id)
    
    def update_preferences(self, user_id: str, prefs: Dict):
        if user_id in self.preferences:
            self.preferences[user_id]["preferences"].update(prefs)
            return self.preferences[user_id]
        return None
