"""
Fase 5: Model Warming & Lazy Loading

Pre-carga modelos en startup para evitar latencia inicial
Lazy loading con fallback elegante si no está disponible

Uso:
    warmer = ModelWarmer()
    warmer.warm_models()  # En thread de background
    
    if warmer.is_model_ready('dense'):
        # Dense model está disponible
        dense = DenseRetriever()
"""

import threading
import time
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ModelWarmer:
    """
    Calienta (pre-carga) modelos en background thread.
    Permite que búsquedas iniciales no sufran spike de latencia.
    """
    
    def __init__(self, timeout: float = 60.0):
        """
        Initialize model warmer.
        
        Args:
            timeout: Máximo tiempo en segundos para calentar un modelo
        """
        self.timeout = timeout
        self._models_loaded = {}
        self._loading_started = {}
        self._lock = threading.Lock()
    
    def warm_models(self):
        """
        Pre-carga todos los modelos de Hybrid retriever.
        Debe ejecutarse en thread separado para no bloquear startup.
        
        Models que se cargan:
        1. Dense Embedder (paraphrase-multilingual-MiniLM-L12-v2)
        2. Reranker ES/RU (cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)
        3. Reranker EN (cross-encoder/ms-marco-MiniLM-L-12-v2)
        """
        
        print("[ModelWarmer] Starting model warm-up...")
        start_time = time.time()
        
        # Model 1: Dense Embedder
        print("[ModelWarmer] Loading Dense Embedder...")
        self._warm_dense()
        
        # Model 2: Reranker (Spanish/Russian)
        print("[ModelWarmer] Loading Reranker (ES/RU)...")
        self._warm_reranker_es_ru()
        
        # Model 3: Reranker (English)
        print("[ModelWarmer] Loading Reranker (EN)...")
        self._warm_reranker_en()
        
        elapsed = time.time() - start_time
        print(f"[ModelWarmer] Warm-up completed in {elapsed:.1f}s")
        
        # Log status
        status = {
            model: self._models_loaded.get(model, False)
            for model in ['dense', 'reranker_es_ru', 'reranker_en']
        }
        print(f"[ModelWarmer] Status: {status}")
    
    def _warm_dense(self):
        """Warm dense embedder model"""
        with self._lock:
            if 'dense' in self._models_loaded:
                return  # Already loaded
            
            self._loading_started['dense'] = time.time()
        
        try:
            from retrieval.dense import DenseRetriever
            
            start = time.time()
            embedder = DenseRetriever()
            elapsed = time.time() - start
            
            with self._lock:
                self._models_loaded['dense'] = True
            
            logger.info(f"Dense model loaded in {elapsed:.2f}s")
            print(f"  [+] Dense Embedder: {elapsed:.2f}s")
        
        except Exception as e:
            logger.warning(f"Failed to warm dense model: {e}")
            print(f"  [-] Dense Embedder failed: {e}")
            with self._lock:
                self._models_loaded['dense'] = False
    
    def _warm_reranker_es_ru(self):
        """Warm Spanish/Russian reranker model"""
        with self._lock:
            if 'reranker_es_ru' in self._models_loaded:
                return
            
            self._loading_started['reranker_es_ru'] = time.time()
        
        try:
            from retrieval.rerank import CrossEncoderReranker
            
            start = time.time()
            # Load with language-specific model
            reranker = CrossEncoderReranker(language='es')
            elapsed = time.time() - start
            
            with self._lock:
                self._models_loaded['reranker_es_ru'] = True
            
            logger.info(f"Reranker (ES/RU) loaded in {elapsed:.2f}s")
            print(f"  [+] Reranker (ES/RU): {elapsed:.2f}s")
        
        except Exception as e:
            logger.warning(f"Failed to warm reranker (ES/RU): {e}")
            print(f"  [-] Reranker (ES/RU) failed: {e}")
            with self._lock:
                self._models_loaded['reranker_es_ru'] = False
    
    def _warm_reranker_en(self):
        """Warm English reranker model"""
        with self._lock:
            if 'reranker_en' in self._models_loaded:
                return
            
            self._loading_started['reranker_en'] = time.time()
        
        try:
            from retrieval.rerank import CrossEncoderReranker
            
            start = time.time()
            reranker = CrossEncoderReranker(language='en')
            elapsed = time.time() - start
            
            with self._lock:
                self._models_loaded['reranker_en'] = True
            
            logger.info(f"Reranker (EN) loaded in {elapsed:.2f}s")
            print(f"  [+] Reranker (EN): {elapsed:.2f}s")
        
        except Exception as e:
            logger.warning(f"Failed to warm reranker (EN): {e}")
            print(f"  [-] Reranker (EN) failed: {e}")
            with self._lock:
                self._models_loaded['reranker_en'] = False
    
    def is_model_ready(self, model_name: str) -> bool:
        """
        Check if model is loaded and ready for use.
        
        Args:
            model_name: 'dense', 'reranker_es_ru', or 'reranker_en'
        
        Returns:
            True if model is loaded, False otherwise
        """
        with self._lock:
            return self._models_loaded.get(model_name, False)
    
    def wait_for_model(self, model_name: str, timeout: float = None) -> bool:
        """
        Wait for model to be loaded (blocking).
        
        Args:
            model_name: Model to wait for
            timeout: Max time to wait (seconds). If None, uses default.
        
        Returns:
            True if model loaded within timeout, False otherwise
        """
        timeout = timeout or self.timeout
        start = time.time()
        
        while time.time() - start < timeout:
            if self.is_model_ready(model_name):
                return True
            time.sleep(0.1)  # Poll every 100ms
        
        logger.warning(f"Timeout waiting for model {model_name}")
        return False
    
    def get_stats(self) -> Dict:
        """Get warming statistics"""
        with self._lock:
            stats = {
                'models_loaded': dict(self._models_loaded),
                'loading_times': {},
            }
            
            for model, start_time in self._loading_started.items():
                if model in self._models_loaded:
                    stats['loading_times'][model] = {
                        'started_at': start_time,
                        'duration_estimate': '?'  # Would need end time
                    }
            
            return stats


def warm_models_background():
    """
    Convenience function: Start warming models in background thread.
    
    Uso:
        warm_models_background()  # Al startup de la aplicación
    """
    warmer = ModelWarmer()
    thread = threading.Thread(
        target=warmer.warm_models,
        daemon=True,
        name='ModelWarmerThread'
    )
    thread.start()
    return warmer


if __name__ == "__main__":
    # Test script
    import sys
    logging.basicConfig(level=logging.INFO)
    
    print("="*80)
    print("MODEL WARMER TEST")
    print("="*80)
    
    warmer = ModelWarmer()
    warmer.warm_models()
    
    print("\n" + "="*80)
    print("STATS:")
    print("="*80)
    print(warmer.get_stats())
