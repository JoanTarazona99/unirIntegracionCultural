"""
Fase 4: HybridRAGEngine - Integración de HybridRetriever en RAG Pipeline

Este módulo integra BM25 + Dense + Rerank retrieval en el sistema RAG existente.

Uso:
    from hybrid_rag import HybridRAGEngine
    
    engine = HybridRAGEngine()
    results = engine.search("¿Cuánto cuesta el curso?")
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from retrieval.sparse import BM25Retriever
from retrieval.dense import DenseRetriever
from retrieval.hybrid import HybridRetriever
from retrieval.rerank import CrossEncoderReranker, QueryLanguageDetector
from retrieval.chunks import Chunk


class HybridRAGEngine:
    """
    Integración de HybridRetriever en el sistema RAG.
    
    Combina:
    - BM25 (sparse, recall-focused)
    - Dense embeddings (semantic, relevance-focused)
    - Cross-encoder reranking (fine-grained scoring)
    """
    
    def __init__(
        self,
        enable_dense: bool = True,
        enable_reranking: bool = True,
        top_k: int = 5,
        candidate_multiplier: int = 4,
    ):
        """
        Initialize HybridRAGEngine.
        
        Args:
            enable_dense: Enable dense retriever (semantic search)
            enable_reranking: Enable cross-encoder reranking
            top_k: Number of final results to return
            candidate_multiplier: Rerank top K*multiplier results
        """
        self.enable_dense = enable_dense
        self.enable_reranking = enable_reranking
        self.top_k = top_k
        self.candidate_multiplier = candidate_multiplier
        
        self.detector = QueryLanguageDetector()
        self._initialize_retrievers()
    
    def _initialize_retrievers(self):
        """Initialize retriever components"""
        self.sparse = BM25Retriever()
        
        self.dense = None
        if self.enable_dense:
            try:
                self.dense = DenseRetriever()
            except Exception as e:
                print(f"[HybridRAG] Failed to initialize dense retriever: {e}")
                self.dense = None
        
        self.reranker = None
        if self.enable_reranking:
            try:
                self.reranker = CrossEncoderReranker()
            except Exception as e:
                print(f"[HybridRAG] Failed to initialize reranker: {e}")
                self.reranker = None
        
        self.hybrid = HybridRetriever(
            sparse=self.sparse,
            dense=self.dense,
            reranker=self.reranker,
            candidate_multiplier=self.candidate_multiplier,
        )
    
    def index(self, chunks: List[Chunk]) -> None:
        """Index chunks for retrieval"""
        self.hybrid.index(chunks)
    
    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Search for relevant chunks.
        
        Args:
            query: User query (ES/EN/RU)
            top_k: Number of results (uses default if None)
        
        Returns:
            List of result dicts with metadata
        """
        top_k = top_k or self.top_k
        
        # Detect language
        lang = self.detector.detect(query)
        
        # Search using hybrid retriever
        results = self.hybrid.search(query, top_k=top_k)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'id': result.chunk.id,
                'source': result.chunk.source,
                'title': result.chunk.title,
                'content': result.chunk.content,
                'score': float(result.score),
                'language_detected': lang,
                'retrieval_method': 'hybrid',
            })
        
        return formatted_results
    
    def get_stats(self) -> Dict:
        """Get retrieval engine statistics"""
        return {
            'dense_enabled': self.enable_dense and self.dense is not None,
            'reranking_enabled': self.enable_reranking and self.reranker is not None,
            'top_k': self.top_k,
            'candidate_multiplier': self.candidate_multiplier,
        }


class HybridRAGConfig:
    """Configuration for HybridRAGEngine"""
    
    # Retrieval settings
    ENABLE_DENSE = True
    ENABLE_RERANKING = True
    TOP_K = 5
    CANDIDATE_MULTIPLIER = 4
    
    # Reranker models by language
    RERANKER_MODELS = {
        'en': 'cross-encoder/ms-marco-MiniLM-L-12-v2',
        'es': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
        'ru': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
    }
    
    # Score fusion weights
    # (w_bm25, w_dense, w_rerank)
    FUSION_WEIGHTS_NORMAL = (0.3, 0.4, 0.3)  # Balanced
    FUSION_WEIGHTS_BM25_HEAVY = (0.5, 0.3, 0.2)  # Favor keyword match
    FUSION_WEIGHTS_DENSE_HEAVY = (0.2, 0.5, 0.3)  # Favor semantic
    
    @classmethod
    def get_weights_for_query_type(cls, query_type: str = 'normal') -> Tuple[float, float, float]:
        """Get fusion weights based on query type"""
        if query_type == 'bm25_heavy':
            return cls.FUSION_WEIGHTS_BM25_HEAVY
        elif query_type == 'dense_heavy':
            return cls.FUSION_WEIGHTS_DENSE_HEAVY
        else:
            return cls.FUSION_WEIGHTS_NORMAL


def create_hybrid_rag_engine(
    enable_dense: bool = True,
    enable_reranking: bool = True,
) -> HybridRAGEngine:
    """Factory function to create HybridRAGEngine"""
    return HybridRAGEngine(
        enable_dense=enable_dense,
        enable_reranking=enable_reranking,
        top_k=HybridRAGConfig.TOP_K,
        candidate_multiplier=HybridRAGConfig.CANDIDATE_MULTIPLIER,
    )
