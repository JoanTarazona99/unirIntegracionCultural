#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests End-to-End del Asistente de Integración Cultural
Simula usuarios reales interactuando con todos los componentes
"""

import sys
import json
from pathlib import Path

if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Añadir backend al path
sys.path.insert(0, str(Path(__file__).parent))

from phrase_manager import PhraseManager, UserPreferences
from personalization import PersonalizationEngine, ContextAwareResponseFormatter
from enhanced_rag import EnhancedRAGModule


class E2ETestRunner:
    """Ejecutor de pruebas end-to-end"""
    
    def __init__(self):
        self.test_results = []
        self.phrase_manager = PhraseManager(
            Path(__file__).parent.parent / "data" / "phrases" / "complete_phrases.json"
        )
        self.user_prefs = UserPreferences()
        self.personalization = PersonalizationEngine()
        self.rag_module = EnhancedRAGModule()
        self.formatter = ContextAwareResponseFormatter()
        
        self.test_count = 0
        self.passed = 0
        self.failed = 0
    
    def log(self, msg, level="INFO"):
        prefix = "[OK]" if level == "OK" else "[FAIL]" if level == "FAIL" else "[TEST]"
        print(f"{prefix} {msg}")
    
    def test(self, name, condition, expected=None, actual=None):
        """Registrar resultado de test"""
        self.test_count += 1
        if condition:
            self.passed += 1
            self.log(f"[{self.test_count}] {name}... PASS", "OK")
        else:
            self.failed += 1
            msg = f"[{self.test_count}] {name}... FAIL"
            if expected and actual:
                msg += f" (Expected: {expected}, Got: {actual})"
            self.log( msg, "FAIL")
    
    def test_user_profile_creation(self):
        """Test 1: Crear perfil de usuario"""
        print("\n" + "="*70)
        print("[TEST SUITE 1] CREACION DE PERFIL DE USUARIO")
        print("="*70)
        
        user_data = {
            'country': 'Vietnam',
            'visa_type': 'student',
            'academic_level': 'bachelor',
            'housing_type': 'dorm',
            'russian_level': 'A1'
        }
        
        profile = self.user_prefs.create_user('user_001', user_data)
        self.test("Perfil cread", profile is not None)
        self.test("Pais guardado", profile['country'] == 'Vietnam')
        self.test("Visa guardada", profile['visa_type'] == 'student')
        self.test("Nivel ruso guardado", profile['russian_level'] == 'A1')
    
    def test_phrase_retrieval(self):
        """Test 2: Obtener frases contextualizadas"""
        print("\n" + "="*70)
        print("[TEST SUITE 2] OBTENCION DE FRASES CONTEXTUALIZADAS")
        print("="*70)
        
        # Obtener frases por categoría
        med_phrases = self.phrase_manager.get_phrases_by_category("Медицина")
        self.test("Frases medicas disponibles", len(med_phrases) > 0)
        
        # Obtain frases por contexto
        admin_phrases = self.phrase_manager.get_phrases_by_context("admin")
        self.test("Frases administrativas disponibles", len(admin_phrases) > 0)
        
        # Verificar estructura
        if med_phrases:
            sample = med_phrases[0]
            self.test("Frase tiene id", 'id' in sample)
            self.test("Frase tiene ruso", 'russian' in sample)
            self.test("Frase tiene transliteracion", 'transliteration' in sample)
            self.test("Frase tiene ingles", 'english' in sample)
    
    def test_personalization(self):
        """Test 3: Personalización de recomendaciones"""
        print("\n" + "="*70)
        print("[TEST SUITE 3] PERSONALIZACION DE RECOMENDACIONES")
        print("="*70)
        
        user_profile = {
            'country': 'Vietnam',
            'visa_type': 'student',
            'academic_level': 'bachelor',
            'russian_level': 'A1'
        }
        
        personalization = self.personalization.create_profile('user_001', user_profile)
        self.test("Perfil personalizado creado", personalization is not None)
        self.test("Contextos prioritarios asignados", len(personalization['priority_contexts']) > 0)
        self.test("Adaptacion de texto configurada", personalization['text_adaptation'] is not None)
        
        # Obtener recomendaciones
        recommendations = self.personalization.get_personalized_recommendations('user_001')
        self.test("Recomendaciones generadas", len(recommendations) > 0)
        
        # Generar checklist
        checklist = self.personalization.generate_checklist('user_001')
        self.test("Checklist generado", len(checklist) > 0)
    
    def test_response_formatting(self):
        """Test 4: Formatteo de respuestas por nivel de ruso"""
        print("\n" + "="*70)
        print("[TEST SUITE 4] FORMATTEO DE RESPUESTAS POR NIVEL")
        print("="*70)
        
        base_response = "Este es un texto de prueba en ruso"
        
        # Test diferentes niveles
        levels = ['A1', 'A2', 'B1', 'B2', 'C1']
        for level in levels:
            formatted = self.formatter.format_response(base_response, level)
            self.test(f"Respuesta formattada para {level}", formatted is not None)
    
    def test_rag_search(self):
        """Test 5: Búsqueda RAG en documentos"""
        print("\n" + "="*70)
        print("[TEST SUITE 5] BUSQUEDA RAG EN DOCUMENTOS")
        print("="*70)
        
        queries = [
            "registro",
            "visa",
            "seguro",
            "dormitorio"
        ]
        
        for query in queries:
            result = self.rag_module.search_and_generate(query)
            self.test(f"Busqueda '{query}' retorna respuesta", result['response'] is not None)
    
    def test_user_flow(self):
        """Test 6: Flujo completo de usuario"""
        print("\n" + "="*70)
        print("[TEST SUITE 6] FLUJO COMPLETO DE USUARIO")
        print("="*70)
        
        # 1. Usuario crea perfil
        user_id = 'user_test_006'
        user_data = {
            'name': 'Juan',
            'country': 'Vietnam',
            'visa_type': 'student',
            'academic_level': 'bachelor',
            'housing_type': 'dorm',
            'russian_level': 'A1'
        }
        
        profile = self.user_prefs.create_user(user_id, user_data)
        self.test("1. Perfil de usuario creado", profile is not None)
        
        # 2. Sistema personaliza
        personalization = self.personalization.create_profile(user_id, user_data)
        self.test("2. Sistema personaliza perfil", personalization is not None)
        
        # 3. Usuario busca información
        query = "Como registrarse en MFC"
        rag_result = self.rag_module.search_and_generate(query)
        self.test("3. Busqueda RAG exitosa", rag_result['response'] is not None)
        
        # 4. Obtener frases útiles
        recommended_phrases = self.phrase_manager.get_phrases_by_context("admin")
        self.test("4. Frases recomendadas obtenidas", len(recommended_phrases) > 0)
        
        # 5. Formatear respuesta según nivel
        if rag_result['response']:
            formatted = self.formatter.format_response(
                rag_result['response'][:200],
                user_data['russian_level']
            )
            self.test("5. Respuesta formattada segun nivel", formatted is not None)
    
    def run_all(self):
        """Ejecutar todas las pruebas"""
        print("\n" + "="*70)
        print("E2E TEST RUNNER - ASISTENTE KUBGU")
        print("="*70)
        
        self.test_user_profile_creation()
        self.test_phrase_retrieval()
        self.test_personalization()
        self.test_response_formatting()
        self.test_rag_search()
        self.test_user_flow()
        
        self.print_summary()
    
    def print_summary(self):
        """Imprimir resumen de pruebas"""
        print("\n" + "="*70)
        print("RESUMEN DE PRUEBAS END-TO-END")
        print("="*70)
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print(f"Total de pruebas: {total}")
        print(f"Exitosas: {self.passed} ({percentage:.1f}%)")
        print(f"Fallidas: {self.failed}")
        
        if self.failed == 0:
            print("\n[OK] TODOS LOS TESTS EXITOSOS!")
            print("[OK] SISTEMA END-TO-END OPERACIONAL")
        else:
            print(f"\n[ALERT] {self.failed} test(s) fallido(s)")
        
        print("\n" + "="*70)


def main():
    runner = E2ETestRunner()
    runner.run_all()


if __name__ == "__main__":
    main()
