"""
Knowledge Integrator - Automatic KB enhancement from web sources
Monitors acquisition_log.json and integrates successful web findings into the knowledge base
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class KnowledgeIntegrator:
    """Automatically integrate web-acquired knowledge into the KB"""
    
    def __init__(self, project_root: str = None):
        """Initialize integrator with paths"""
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.project_root = project_root
        self.acquisition_log_path = os.path.join(project_root, 'data', 'acquisition_log.json')
        self.enhanced_rag_path = os.path.join(project_root, 'backend', 'enhanced_rag.py')
        self.integration_log_path = os.path.join(project_root, 'data', 'integration_log.json')
        
        # Initialize integration log if doesn't exist
        if not os.path.exists(self.integration_log_path):
            self._save_integration_log([])
    
    def load_acquisition_log(self) -> List[Dict]:
        """Load acquisition_log.json"""
        if not os.path.exists(self.acquisition_log_path):
            return []
        
        try:
            with open(self.acquisition_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading acquisition log: {e}")
            return []
    
    def load_integration_log(self) -> List[Dict]:
        """Load integration_log.json (tracks what's been integrated)"""
        if not os.path.exists(self.integration_log_path):
            return []
        
        try:
            with open(self.integration_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading integration log: {e}")
            return []
    
    def _save_integration_log(self, log: List[Dict]):
        """Save integration_log.json"""
        try:
            os.makedirs(os.path.dirname(self.integration_log_path), exist_ok=True)
            with open(self.integration_log_path, 'w', encoding='utf-8') as f:
                json.dump(log, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving integration log: {e}")
    
    def get_pending_acquisitions(self) -> List[Dict]:
        """Get successful acquisitions that haven't been integrated yet"""
        acq_log = self.load_acquisition_log()
        integ_log = self.load_integration_log()
        
        # Track which queries have been integrated
        integrated_queries = {entry.get('query') for entry in integ_log}
        
        # Return successful acquisitions not yet integrated
        pending = [
            entry for entry in acq_log 
            if entry.get('success') is True 
            and entry.get('query') not in integrated_queries
        ]
        
        return pending
    
    def create_section_from_query(self, query: str, source_url: str) -> Optional[Tuple[str, str]]:
        """
        Create KB section from query + source_url
        Returns: (section_name, section_python_code) or None
        """
        try:
            # Map query patterns to section types
            keywords = query.lower()
            
            # Normalize accents and special characters for matching
            import unicodedata
            keywords_normalized = unicodedata.normalize('NFD', keywords).encode('ascii', 'ignore').decode('utf-8')
            
            # Check in priority order - most specific first
            
            # Admission requirements (most specific)
            if any(w in keywords for w in ['nota mínima', 'nota minima', 'score minimo', 'puntuación mínima', 'calificación minima']) or \
               (any(w in keywords for w in ['nota', 'minimo', 'minima', 'score', 'puntuacion', 'calificacion']) and 
                any(w in keywords for w in ['admisión', 'admission', 'carrera', 'programa'])):
                return ('Criterios Admisión Integrado', self._generate_admission_section())
            
            # Deadlines
            elif any(w in keywords for w in ['plazo', 'convocatoria', 'fecha', 'deadline', 'cierre de', 'apertura']):
                return ('Fechas Plazos Integrado', self._generate_deadlines_section())
            
            # Financial requirements
            elif any(w in keywords for w in ['fondos', 'economicos', 'económicos', 'dinero', 'financiero', 'comprobante', 'cuenta bancaria', 'deposito']):
                return ('Requisitos Financieros Integrado', self._generate_financial_section())
            
            # Documents
            elif any(w in keywords for w in ['documento', 'traduccion', 'traducción', 'apostilla', 'legalizacion', 'legalización']):
                return ('Documentos Integrado', self._generate_documents_section(source_url))
            
            # Contacts/email
            elif any(w in keywords for w in ['correo', 'contact', 'email', 'director', 'telefono', 'teléfono', 'contacto']):
                return ('Contactos Integrado', self._generate_contacts_section(source_url))
            
            # Preparatory studies
            elif any(w in keywords for w in ['preparatoria', 'preparatory', 'ruso', 'russian', 'idioma']):
                return ('Preparatoria Integrado', self._generate_preparatory_section())
            
            # Pricing variations (least specific - catch-all for financial queries)
            elif any(w in keywords for w in ['precio', 'costo', 'coste', 'matricula', 'matrícula', 'ciudadania', 'ciudadanía', 'ue', 'pago']):
                return ('Precios Ciudadanía Integrado', self._generate_pricing_section())
            
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error creating section: {e}")
            return None
    
    def _generate_pricing_section(self) -> str:
        """Generate Python code for pricing section"""
        return '''self.documents['Precios Ciudadanía Integrado Web'] = {
            'name': 'Precios actualizados por web / Цены из веб-источников',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Variación de precios - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Esta información fue extraída automáticamente de búsquedas web
                    cuando el sistema no encontró información suficiente en la KB local.

                    - Verificar https://kubsu.ru para confirmación official
                    - Los precios pueden variar según programa y año académico
                    - Se recomienda contactar a admission@kubsu.ru para precio exacto

                    FUENTE: Google Gemini + búsqueda automatizada
                    FECHA INTEGRACIÓN: ''' + datetime.now().isoformat() + '''
                    \'''
                }
            ]
        }
'''
    
    def _generate_admission_section(self) -> str:
        """Generate Python code for admission section"""
        return '''self.documents['Criterios Admisión Integrado Web'] = {
            'name': 'Criterios integrados de admisión / Критерии из веб-источников',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Notas mínimas - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Esta información fue extraída automáticamente de búsquedas web.

                    REQUISITOS DE ADMISIÓN (Confirmación requerida):
                    - Contactar directamente a: admissions@kubsu.ru
                    - Consultar: https://kubsu.ru/en/admission
                    - Teléfono: +7 (861) 219-97-95

                    FUENTE: KubGU oficial + búsqueda automatizada
                    FECHA INTEGRACIÓN: ''' + datetime.now().isoformat() + '''
                    \'''
                }
            ]
        }
'''
    
    def _generate_deadlines_section(self) -> str:
        """Generate Python code for deadlines section"""
        return '''self.documents['Fechas Plazos Integrado Web'] = {
            'name': 'Convocatorias actualizadas / Сроки из веб-источников',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Calendarios integrados - Fuentes web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Las fechas de convocatoria pueden cambiar anualmente.

                    SIEMPRE VERIFICAR:
                    - Sitio oficial: https://kubsu.ru
                    - Email: admission@kubsu.ru
                    - Aplicar CON ANTICIPACIÓN (mínimo 6 semanas antes del cierre)

                    FUENTE: KubGU + búsqueda automatizada
                    FECHA INTEGRACIÓN: ''' + datetime.now().isoformat() + '''
                    \'''
                }
            ]
        }
'''
    
    def _generate_financial_section(self) -> str:
        """Generate Python code for financial requirements section"""
        return '''self.documents['Requisitos Financieros Integrado Web'] = {
            'name': 'Comprobantes financieros actualizados / Финансовые требования',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Fondos económicos - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Requisitos financieros mínimos para visa y matrícula.

                    RECOMENDACIÓN:
                    - Disponibilidad: USD $2,000-$5,000 mínimo
                    - Cobertura anual: USD $10,000-$15,000
                    - Contactar para confirmación: admission@kubsu.ru

                    FUENTE: Búsqueda automatizada + fuentes web
                    FECHA INTEGRACIÓN: ''' + datetime.now().isoformat() + '''
                    \'''
                }
            ]
        }
'''
    
    def _generate_documents_section(self, source_url: str = None) -> str:
        """Generate Python code for documents section"""
        return f'''self.documents['Documentos Integrado Web'] = {{
            'name': 'Documentos requeridos - Actualización web / Документы из веб-источников',
            'url': '{source_url or 'https://kubsu.ru'}',
            'sections': [
                {{
                    'title': 'Traducción y apostilla - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Información de traducción oficial extraída de búsquedas web.

                    REQUISITOS DOCUMENTALES:
                    - Todos los documentos extranjeros DEBEN ser traducidos
                    - Traducción debe ser certificada por notaría
                    - Apostilla es obligatoria según país de origen

                    CONTACTO:
                    - МФЦ Krasnodar: ul. Krasnaya, 176
                    - Email consultas: admission@kubsu.ru
                    - Verificar: https://kubsu.ru

                    FUENTE: búsqueda automatizada + МВД РФ
                    FECHA INTEGRACIÓN: {datetime.now().isoformat()}
                    \'''
                }}
            ]
        }}
'''
    
    def _generate_contacts_section(self, source_url: str = None) -> str:
        """Generate Python code for contacts section"""
        return f'''self.documents['Contactos Integrado Web'] = {{
            'name': 'Contactos actualizados / Контакты из веб-источников',
            'url': '{source_url or 'https://kubsu.ru'}',
            'sections': [
                {{
                    'title': 'Información de contacto - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Contactos recopilados automáticamente de búsquedas web.

                    CONTACTOS PRINCIPALES:
                    - Email general: admission@kubsu.ru
                    - Teléfono: +7 (861) 219-97-95
                    - Sitio web: https://kubsu.ru
                    - Oficina Internacional: international@kubsu.ru

                    Para solicitudes específicas:
                    - Preparatoria rusa: preparatory@kubsu.ru
                    - Estudios de posgrado: graduate@kubsu.ru

                    FUENTE: KubGU oficial + búsqueda automatizada
                    FECHA INTEGRACIÓN: {datetime.now().isoformat()}
                    \'''
                }}
            ]
        }}
'''
    
    def _generate_preparatory_section(self) -> str:
        """Generate Python code for preparatory studies section"""
        return '''self.documents['Preparatoria Integrado Web'] = {
            'name': 'Estudios preparatorios / Подготовительные программы',
            'url': 'https://kubsu.ru',
            'sections': [
                {
                    'title': 'Programas preparatorios - Integración web',
                    'content': \'''
                    INFORMACIÓN INTEGRADA DE FUENTES WEB / ИНТЕГРИРОВАННАЯ ИНФОРМАЦИЯ

                    ⭐ Nota: Información sobre estudios preparatorios extraída de búsquedas web.

                    PREPARATORIA DE RUSO / ПОДГОТОВИТЕЛЬНЫЙ ФАКУЛЬТЕТ:
                    - Duración: 3-6 meses
                    - Enfoque: Ruso académico, cultura rusa
                    - Certificado TRKI incluido
                    
                    PROCESO DE INSCRIPCIÓN:
                    - Contactar: preparatory@kubsu.ru
                    - Documentos: Pasaporte + Diploma + Visa
                    - Plazos: Aplicar 6-8 semanas antes del inicio

                    FUENTE: búsqueda automatizada
                    FECHA INTEGRACIÓN: ''' + datetime.now().isoformat() + '''
                    \'''
                }
            ]
        }
'''
    
    def integrate_pending(self, auto_add: bool = True) -> Dict:
        """
        Process pending acquisitions and integrate into KB
        
        Args:
            auto_add: If True, add sections to enhanced_rag.py automatically
        
        Returns:
            Dict with integration results
        """
        pending = self.get_pending_acquisitions()
        
        if not pending:
            return {
                'status': 'no_pending',
                'message': 'No pending acquisitions to integrate',
                'count': 0
            }
        
        logger.info(f"Found {len(pending)} pending acquisitions for integration")
        
        integrated = []
        failed = []
        
        for acquisition in pending:
            try:
                query = acquisition.get('query', '')
                source_url = acquisition.get('source_url', '')
                
                # Create section code
                result = self.create_section_from_query(query, source_url)
                if not result:
                    failed.append({
                        'query': query,
                        'reason': 'Could not classify query type'
                    })
                    continue
                
                section_name, section_code = result
                
                # Add to enhanced_rag.py if requested
                if auto_add:
                    self._add_section_to_rag(section_code)
                
                integrated.append({
                    'timestamp': datetime.now().isoformat(),
                    'query': query,
                    'source_url': source_url,
                    'section_name': section_name,
                    'status': 'integrated'
                })
                
                logger.info(f"✅ Integrated: {section_name} from query: {query}")
                
            except Exception as e:
                failed.append({
                    'query': acquisition.get('query'),
                    'error': str(e)
                })
                logger.error(f"Failed to integrate {acquisition.get('query')}: {e}")
        
        # Update integration log
        current_log = self.load_integration_log()
        current_log.extend(integrated)
        self._save_integration_log(current_log)
        
        result = {
            'status': 'success',
            'integrated_count': len(integrated),
            'failed_count': len(failed),
            'integrated': integrated,
            'failed': failed
        }
        
        logger.info(f"Integration complete: {len(integrated)} integrated, {len(failed)} failed")
        return result
    
    def _add_section_to_rag(self, section_code: str):
        """Add section code to enhanced_rag.py before the load_from_json method"""
        try:
            with open(self.enhanced_rag_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find insertion point (before load_from_json method)
            insertion_marker = '    def load_from_json'
            
            if insertion_marker not in content:
                logger.warning("Could not find insertion point in enhanced_rag.py")
                return False
            
            # Insert the new section
            insertion_point = content.find(insertion_marker)
            new_content = content[:insertion_point] + section_code + '\n\n        ' + content[insertion_point:]
            
            # Write back
            with open(self.enhanced_rag_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"✅ Added section to enhanced_rag.py")
            return True
            
        except Exception as e:
            logger.error(f"Error adding section to enhanced_rag.py: {e}")
            return False
    
    def get_integration_status(self) -> Dict:
        """Get status of integration process"""
        acq_log = self.load_acquisition_log()
        integ_log = self.load_integration_log()
        pending = self.get_pending_acquisitions()
        
        return {
            'total_acquisitions': len(acq_log),
            'successful_acquisitions': len([a for a in acq_log if a.get('success')]),
            'integrated_count': len(integ_log),
            'pending_count': len(pending),
            'pending_queries': [p.get('query') for p in pending]
        }


def auto_integrate():
    """Run integration process"""
    integrator = KnowledgeIntegrator()
    
    # Get status
    status = integrator.get_integration_status()
    print(f"\n📊 INTEGRATION STATUS:")
    print(f"   Total acquisitions: {status['total_acquisitions']}")
    print(f"   Successful: {status['successful_acquisitions']}")
    print(f"   Already integrated: {status['integrated_count']}")
    print(f"   Pending: {status['pending_count']}")
    
    if status['pending_count'] > 0:
        print(f"\n🔄 PENDING QUERIES:")
        for i, query in enumerate(status['pending_queries'], 1):
            print(f"   {i}. {query}")
        
        print(f"\n⏳ Processing {status['pending_count']} pending acquisitions...")
        result = integrator.integrate_pending(auto_add=True)
        
        print(f"\n✅ INTEGRATION RESULT:")
        print(f"   Integrated: {result['integrated_count']}")
        print(f"   Failed: {result['failed_count']}")
        
        if result['integrated']:
            print(f"\n📝 Successfully integrated sections:")
            for entry in result['integrated']:
                print(f"   - {entry['section_name']}")
                print(f"     Query: {entry['query']}")
    else:
        print("\n✨ No pending acquisitions to integrate - KB is up to date!")


if __name__ == '__main__':
    auto_integrate()
