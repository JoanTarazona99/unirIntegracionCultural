from typing import List, Dict
import numpy as np
try:
    import faiss
except ImportError:
    faiss = None

class RAGModule:
    """Módulo Retrieval-Augmented Generation"""
    
    def __init__(self, documents: List[str] = None, use_faiss: bool = True):
        self.documents = documents or []
        self.use_faiss = use_faiss and faiss is not None
        self.embeddings = []
        self.index = None
        
        if self.use_faiss:
            self._initialize_faiss()
    
    def _initialize_faiss(self):
        """Inicializar índice FAISS"""
        try:
            # Crear embeddings dummy (en producción usar Sentence-BERT)
            embedding_dim = 384
            self.embeddings = np.random.randn(len(self.documents), embedding_dim).astype(np.float32)
            
            # Crear índice FAISS
            self.index = faiss.IndexFlatL2(embedding_dim)
            self.index.add(self.embeddings)
        except Exception as e:
            print(f"Error inicializando FAISS: {e}")
            self.use_faiss = False
    
    def search_documents(self, query: str, k: int = 5) -> List[Dict]:
        """Buscar documentos relevantes"""
        if not self.use_faiss or self.index is None:
            # Búsqueda simple por keyword
            return self._keyword_search(query, k)
        
        try:
            # En producción usar embeddings reales
            query_embedding = np.random.randn(1, 384).astype(np.float32)
            distances, indices = self.index.search(query_embedding, k)
            
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.documents):
                    results.append({
                        "document": self.documents[idx],
                        "relevance": 1 / (1 + distance),
                        "source": f"documento_{idx}"
                    })
            return results
        except Exception as e:
            print(f"Error en búsqueda FAISS: {e}")
            return self._keyword_search(query, k)
    
    def _keyword_search(self, query: str, k: int = 5) -> List[Dict]:
        """Búsqueda simple por palabra clave"""
        query_lower = query.lower()
        scored = []
        
        for idx, doc in enumerate(self.documents):
            doc_lower = doc.lower()
            if query_lower in doc_lower:
                # Calcular score según posición y frecuencia
                score = doc_lower.count(query_lower)
                scored.append({
                    "document": doc,
                    "relevance": min(score / 5.0, 1.0),
                    "source": f"documento_{idx}"
                })
        
        # Ordenar por relevancia
        scored.sort(key=lambda x: x["relevance"], reverse=True)
        return scored[:k]
    
    def add_documents(self, new_documents: List[str]):
        """Añadir nuevos documentos al índice"""
        self.documents.extend(new_documents)
        if self.use_faiss:
            self._initialize_faiss()
    
    def generate_response(self, query: str, context: List[str]) -> str:
        """Generar respuesta basada en contexto"""
        # En producción, integrar con modelo de generación (LLM)
        response = f"Respuesta para: {query}\n\n"
        response += "Basado en las siguientes fuentes:\n"
        for i, ctx in enumerate(context, 1):
            response += f"{i}. {ctx[:100]}...\n"
        return response

class DocumentLoader:
    """Cargador de documentos oficiales"""
    
    OFFICIAL_SOURCES = {
        "kubsu": "Sitio oficial de KubSU",
        "mvd": "Ministerio de Interior (MВД РФ)",
        "mfc": "Centro Multifuncional (МФЦ)",
        "gosuslugi": "Portal de Servicios del Estado (Gosuslugi)"
    }
    
    def __init__(self):
        self.documents = {}
        self._load_default_documents()
    
    def _load_default_documents(self):
        """Cargar documentos por defecto"""
        self.documents = {
            "kubsu": [
                "Página del Departamento de Servicios Internacionales",
                "Reglamento de admisión para estudiantes internacionales",
                "Información sobre alojamiento universitario",
                "Programa académico y calendario"
            ],
            "mvd": [
                "Procedimientos de registro migratorio",
                "Requisitos para visa de estudiante",
                "Información sobre estatuto migratorio"
            ],
            "mfc": [
                "Servicios disponibles en MFC",
                "Horario de atención",
                "Documentos necesarios para cada servicio"
            ],
            "gosuslugi": [
                "Información sobre servicios digitales",
                "Trámites administrativos en línea"
            ]
        }
    
    def get_documents(self, source: str = None) -> List[str]:
        """Obtener documentos de una fuente específica"""
        if source and source in self.documents:
            return self.documents[source]
        
        # Retornar todos los documentos
        all_docs = []
        for docs in self.documents.values():
            all_docs.extend(docs)
        return all_docs
    
    def add_document(self, source: str, content: str):
        """Añadir un nuevo documento"""
        if source not in self.documents:
            self.documents[source] = []
        self.documents[source].append(content)
