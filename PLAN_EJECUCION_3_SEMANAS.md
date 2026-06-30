# PLAN DE ACCIÓN: DE MVP A MAESTRÍA
## KubGU Assistant - Roadmap Ejecutivo (3 Semanas)

**Fecha de inicio:** 2026-06-30  
**Objetivo:** Proyecto defendible en defensa de maestría  
**Esfuerzo total:** 60-80 horas

---

## 🎯 PRIORIDADES CRÍTICAS (SIN COMPROMETER)

### ✅ NO NEGOCIABLE - Deben hacerse
- [ ] Refactorizar arquitectura (capas limpias, DI)
- [ ] Tipado estricto con mypy
- [ ] Logging estructurado
- [ ] Tests unitarios
- [ ] Evaluación RAG con métricas
- [ ] Documentación académica (ARCHITECTURE.md, DECISIONS.md, REFERENCES.md)

### ⚠️ NICE TO HAVE - Si hay tiempo
- [ ] Base de datos PostgreSQL real
- [ ] CI/CD completo
- [ ] Frontend con Vite/TypeScript
- [ ] Evaluación de traducción (BLEU/TER)

### ❌ OPTIONAL - Posponer
- [ ] Telegram bot refactorizado
- [ ] Evaluación con usuarios reales
- [ ] Performance tuning avanzado

---

## 📅 SPRINTS DETALLADOS

### SPRINT 1: FUNDACIONES (Semana 1 - 20 horas)

**Objetivo:** Proyecto reproducible y tipado

#### Día 1 (Lunes) - Estructura y Configuración

**9:00-12:00 - SETUP (3h)**
```bash
# Crear estructura de directorios
mkdir -p backend/app/{config,api/routes,services,domain,data,utils,middleware,schemas}
mkdir -p backend/app/data/repositories
mkdir -p backend/tests/{unit,integration,e2e}
mkdir -p backend/scripts

# Crear archivos base
touch backend/app/__init__.py
touch backend/app/config/__init__.py
touch backend/app/config/settings.py
touch backend/app/config/logging_config.py
touch backend/app/config/constants.py
touch backend/app/domain/__init__.py
touch backend/app/domain/exceptions.py
touch backend/app/domain/models.py
```

**12:00-13:00 - Lunch**

**13:00-17:00 - Pydantic Settings (4h)**

Crear `backend/app/config/settings.py`:
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    app_name: str = "KubGU Assistant"
    app_version: str = "1.0.0"
    environment: str = "development"
    
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/kubgu"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # RAG
    rag_top_k: int = 10
    rag_min_score: float = 0.3
    semantic_search_enabled: bool = False
    
    # Security
    cors_allowed_origins: List[str] = ["http://localhost:3000"]
    rate_limit_requests: int = 30
    rate_limit_window: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

Actualizar `requirements.txt` con pin de versiones:
```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
structlog==24.1.0
```

Crear `.env.example`:
```bash
ENVIRONMENT=development
APP_VERSION=1.0.0
DATABASE_URL=postgresql://kubgu_user:password@localhost:5432/kubgu_assistant
RAG_TOP_K=10
RAG_MIN_SCORE=0.3
SEMANTIC_SEARCH_ENABLED=false
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Día 2 (Martes) - Typeo y Excepciones

**9:00-12:00 - Excepciones Custom (3h)**

Crear `backend/app/domain/exceptions.py`:
```python
class AppError(Exception):
    """Base para excepciones de negocio"""
    code: str = "UNKNOWN_ERROR"
    http_status: int = 500
    user_message: str = "Error desconocido"

class RAGError(AppError):
    code = "RAG_ERROR"
    http_status = 503
    user_message = "Búsqueda no disponible"

class TranslationError(AppError):
    code = "TRANSLATION_ERROR"
    http_status = 400
    user_message = "Traducción no disponible"

class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422
    user_message = "Datos inválidos"
```

Crear `backend/app/domain/models.py` con Pydantic:
```python
from pydantic import BaseModel, field_validator

class ChatRequest(BaseModel):
    session_id: str
    query: str
    language: str
    
    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Query debe tener 3+ caracteres")
        if len(v) > 1000:
            raise ValueError("Query <= 1000 caracteres")
        return v.strip()

class ChatResponse(BaseModel):
    success: bool
    data: dict
```

**12:00-13:00 - Lunch**

**13:00-17:00 - mypy + Typado (4h)**

Crear `mypy.ini`:
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
strict_optional = True
no_implicit_optional = True
```

Crear `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

Instalar dev tools:
```bash
pip install -r backend/requirements-dev.txt
# Con: pytest, mypy, black, isort, pylint
```

#### Día 3 (Miércoles) - Logging y Middleware

**9:00-12:00 - Structlog (3h)**

Crear `backend/app/config/logging_config.py`:
```python
import structlog
import sys
from structlog.processors import JSONRenderer

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)
```

Crear `backend/app/middleware/logging_middleware.py`:
```python
from fastapi import Request
import uuid
import time
import structlog

logger = structlog.get_logger(__name__)

async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration * 1000
    )
    
    return response
```

**12:00-13:00 - Lunch**

**13:00-17:00 - Reemplazar prints (4h)**

- Buscar todos los `print()` en backend/
- Reemplazar con `logger.info()` / `logger.warning()` / `logger.error()`
- Verificar: no hay prints en código production

#### Día 4 (Jueves) - Documentación Inicial

**9:00-12:00 - ARCHITECTURE.md (3h)**

Crear `ARCHITECTURE.md`:
```markdown
# Arquitectura de KubGU Assistant

## Capas del Sistema

```
┌─────────────────────────────┐
│   Presentación (Frontend)   │  Vue.js 3
├─────────────────────────────┤
│   API Routes (FastAPI)      │  /api/chat, /api/phrases, etc
├─────────────────────────────┤
│   Services (Lógica)         │  RAG, Translation, Personalization
├─────────────────────────────┤
│   Domain (Modelos)          │  Entities, Value Objects, Exceptions
├─────────────────────────────┤
│   Data (Persistencia)       │  Repositories, Database
├─────────────────────────────┤
│   Config (Configuración)    │  Settings, Logging, Constants
└─────────────────────────────┘
```

## Módulos Clave

### RAGService
- Input: `query: str, language: str`
- Process: Search documentos + score relevancia
- Output: `List[RAGResult]`
- Fallback: Si embedding falla, usar keyword search

### TranslationService
- Input: `text: str, target_lang: str`
- Process: Traducción con google-trans
- Output: `translated_text: str`
- Fallback: Si google-trans falla, usar diccionario estático

### PersonalizationService
- Input: `user_profile: UserProfile`
- Process: Recomendaciones según país/visa/nivel
- Output: `List[Phrase]`

## Flujo Principal

1. User hace pregunta en frontend
2. API recibe en /api/chat con session_id, query, language
3. RAGService busca documentos relevantes
4. TranslationService adapta respuesta al idioma
5. PersonalizationService añade frases contextuales
6. API devuelve respuesta + metadata
7. Frontend renderiza + TTS si disponible
```

**12:00-13:00 - Lunch**

**13:00-17:00 - DECISIONS.md (4h)**

Crear `DECISIONS.md` con 3-4 ADRs:

```markdown
# Architectural Decision Records (ADRs)

## ADR-001: FastAPI como Framework Web

**Contexto:** Necesitamos API REST rápida con documentación automática

**Decisión:** Usar FastAPI en lugar de Flask/Django

**Justificación:**
- Automatic OpenAPI/Swagger docs
- Async/await por defecto
- Validación Pydantic incluida
- Performance comparable a Go/Rust

**Consecuencias:**
- Require Python 3.10+
- Learning curve para async
- Plus: mejor performance, menos boilerplate

---

## ADR-002: Pydantic para Validación y Configuración

**Contexto:** Validación de input, configuración por entorno

**Decisión:** Usar Pydantic v2 + pydantic-settings

**Justificación:**
- Type hints + validación automática
- Errores claros
- Compatible con FastAPI

**Consecuencias:**
- Extra dependency
- Plus: input safety, configuration management

---

## ADR-003: Arquitectura Modular en Capas

**Contexto:** Código en monolith main.py; imposible testear

**Decisión:** Separar en capas: API / Services / Domain / Data

**Justificación:**
- Separación de responsabilidades
- Testeable (mockear dependencies)
- Escalable

**Consecuencias:**
- Más archivos, más estructura
- Plus: código limpio, mantenible

---

## ADR-004: Structlog para Logging

**Contexto:** print() statements sin estructura

**Decisión:** Usar structlog con JSON output

**Justificación:**
- Parseable por tools (ELK, Datadog)
- Contexto por request
- Production-grade

**Consecuencias:**
- Output JSON en lugar de texto
- Plus: debugging en producción, auditability
```

#### Día 5 (Viernes) - Testing y Review

**9:00-13:00 - Testing Framework (4h)**

Crear `backend/tests/conftest.py`:
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def rag_service():
    service = Mock()
    service.search.return_value = []
    return service

@pytest.fixture
def translator_service():
    service = Mock()
    service.translate.return_value = "translated text"
    return service
```

Crear test básico `backend/tests/unit/test_rag_service.py`:
```python
import pytest

def test_rag_search_returns_results(rag_service):
    """Test: búsqueda exitosa devuelve resultados"""
    result = rag_service.search("test")
    assert result == []
```

**13:00-17:00 - Review y Setup (4h)**

- [ ] Verificar: `mypy backend/app/` pasa 100%
- [ ] Verificar: `pytest backend/tests/` pasa
- [ ] Verificar: `black --check backend/app/` OK
- [ ] Crear `.env` local desde `.env.example`
- [ ] Test: `python -c "from app.config.settings import settings; print(settings)"`
- [ ] Commit: "feat: foundations - config, logging, typing"

**Salida Sprint 1:** Proyecto reproducible, tipado, loggeable ✅

---

### SPRINT 2: MODULARIDAD (Semana 2 - 20 horas)

#### Día 6 (Lunes) - Refactorización de main.py

**Objetivo:** Separar rutas de lógica

**9:00-12:00 - Crear estructura de rutas (3h)**

```bash
touch backend/app/api/routes/{__init__.py,chat.py,phrases.py,profile.py,health.py}
```

Crear `backend/app/api/routes/chat.py`:
```python
from fastapi import APIRouter, Depends
from app.services.rag_service import RAGService
from app.domain.models import ChatRequest, ChatResponse
from app.api.dependencies import get_rag_service

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """Chat endpoint"""
    try:
        results = rag_service.search(request.query)
        return ChatResponse(success=True, data={"response": results})
    except Exception as e:
        return ChatResponse(success=False, data={"error": str(e)})
```

**12:00-13:00 - Lunch**

**13:00-17:00 - Dependency Injection (4h)**

Crear `backend/app/api/dependencies.py`:
```python
from fastapi import Depends
from app.services.rag_service import RAGService
from app.services.translation_service import TranslationService
from app.config.settings import settings

_rag_service: RAGService = None
_translator_service: TranslationService = None

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService(
            top_k=settings.rag_top_k,
            min_score=settings.rag_min_score
        )
    return _rag_service

def get_translator_service() -> TranslationService:
    global _translator_service
    if _translator_service is None:
        _translator_service = TranslationService()
    return _translator_service
```

#### Días 7-9 (Martes-Jueves) - Migrar Servicios

**Tarea por día:** Migrar un servicio + mejorar interfaces

**Día 7: RAG**
- Copiar `enhanced_rag.py` → `app/services/rag_service.py`
- Añadir type hints
- Crear excepciones custom

**Día 8: Translation**
- Copiar `translator.py` → `app/services/translation_service.py`
- Añadir type hints
- Logging estructurado

**Día 9: Phrases**
- Copiar `phrase_manager.py` → `app/services/phrase_service.py`
- Refactor para usar BD (future)

#### Día 10 (Viernes) - Limpieza y Testing

**9:00-12:00 - Eliminar deuda técnica**

```bash
rm backend/main_minimal.py
rm backend/debug_startup.py
rm backend/demo_rag.py
rm backend/rag_module.py
# Verificar imports no rotos
grep -r "from main_minimal import" . || echo "OK"
```

**12:00-17:00 - Crear tests integración**

Crear `backend/tests/integration/test_chat_endpoint.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    response = client.post(
        "/api/chat",
        json={
            "session_id": "test_session",
            "query": "¿Dónde está МФЦ?",
            "language": "es"
        }
    )
    assert response.status_code == 200
```

Verificar cobertura: `pytest --cov=app` (objetivo: >70%)

**Salida Sprint 2:** Código modular, testeable, sin deuda técnica ✅

---

### SPRINT 3: EVALUACIÓN (Semana 3 - 15-20 horas)

#### Día 11 (Lunes) - Dataset Ground Truth

**9:00-17:00 - Crear dataset RAG (8h)**

Crear `data/ground_truth_queries.json`:
```json
{
  "queries": [
    {
      "id": "q_001",
      "query_text": "¿Dónde está la oficina de МФЦ?",
      "language": "es",
      "intent": "location",
      "relevant_documents": ["doc_042", "doc_043"],
      "highly_relevant": ["doc_042"]
    },
    {
      "id": "q_002",
      "query_text": "Какие документы нужны для студенческой визы?",
      "language": "ru",
      "intent": "procedural",
      "relevant_documents": ["doc_015"],
      "highly_relevant": ["doc_015"]
    }
    // + 48 más queries
  ]
}
```

Crear al menos 50-100 queries anotadas (pedirle a usuarios reales o anotadores)

#### Día 12 (Martes) - Evaluación RAG

**9:00-17:00 - Implementar script de evaluación (8h)**

Crear `backend/scripts/evaluate_rag.py`:
```python
import json
import numpy as np
from app.services.rag_service import RAGService

class RAGEvaluator:
    def __init__(self, ground_truth_file: str):
        with open(ground_truth_file) as f:
            self.ground_truth = json.load(f)
        self.rag_service = RAGService()
    
    def evaluate_all(self):
        metrics = {
            "precision@10": [],
            "recall@10": [],
            "mrr": [],
            "ndcg@10": []
        }
        
        for query in self.ground_truth["queries"]:
            results = self.rag_service.search(query["query_text"])
            result_ids = [r.id for r in results[:10]]
            relevant = query["relevant_documents"]
            
            # Precision@10
            precision = len(set(result_ids) & set(relevant)) / 10
            metrics["precision@10"].append(precision)
            
            # Recall@10
            recall = len(set(result_ids) & set(relevant)) / len(relevant)
            metrics["recall@10"].append(recall)
            
            # MRR
            mrr = 0.0
            for i, doc_id in enumerate(result_ids):
                if doc_id in relevant:
                    mrr = 1.0 / (i + 1)
                    break
            metrics["mrr"].append(mrr)
        
        return {
            "mean_precision@10": np.mean(metrics["precision@10"]),
            "mean_recall@10": np.mean(metrics["recall@10"]),
            "mean_mrr": np.mean(metrics["mrr"])
        }

# Uso
if __name__ == "__main__":
    evaluator = RAGEvaluator("data/ground_truth_queries.json")
    results = evaluator.evaluate_all()
    print(json.dumps(results, indent=2))
    # Guardar en EVALUATION_RESULTS.md
```

Ejecutar:
```bash
python backend/scripts/evaluate_rag.py > EVALUATION_RESULTS.md
```

#### Día 13 (Miércoles) - Benchmarking

**9:00-17:00 - Load testing (8h)**

Crear `locustfile.py`:
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def chat(self):
        self.client.post("/api/chat", json={
            "session_id": "test",
            "query": "¿Dónde está МФЦ?",
            "language": "es"
        })
    
    @task
    def phrases(self):
        self.client.get("/api/phrases")
```

Ejecutar:
```bash
locust -f locustfile.py --host=http://localhost:8000
# Acceder a localhost:8089 y ejecutar prueba
# Recolectar: latencia p50/p95/p99, throughput
```

Documentar resultados en `PERFORMANCE_REPORT.md`

#### Día 14 (Jueves) - Documentación Académica

**9:00-12:00 - Completar DECISIONS.md (3h)**

Añadir 2-3 ADRs más:
- ADR-005: Caché en memoria vs Redis
- ADR-006: Traducción google-trans vs fallback estático
- ADR-007: Testing strategy (unit + integration + e2e)

**12:00-13:00 - Lunch**

**13:00-17:00 - REFERENCES.md (4h)**

Crear `REFERENCES.md`:
```markdown
# Referencias Académicas

## RAG (Retrieval-Augmented Generation)
- Lewis et al. (2020): "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- Gao et al. (2023): "Retrieval-Augmented Generation for Large Language Models: A Survey"

## Traducción Automática Neuronal
- Vaswani et al. (2017): "Attention Is All You Need"
- Papineni et al. (2002): "BLEU: a Method for Automatic Evaluation of Machine Translation"

## Evaluación de NLP
- Koehn & Monz (2006): "Manual and Automatic Metrics for Machine Translation Evaluation"
- Lin & Rey (2004): "ROUGE: A Package for Automatic Evaluation of Summaries"

## Arquitectura de Software
- Martin (2017): "Clean Architecture"
- Fowler & Lewis (2014): "Microservices"

## Síntesis de Voz
- Nishimura et al. (2016): "Parallel WaveNet"
- Wang et al. (2017): "Tacotron: Towards End-to-End Speech Synthesis"
```

#### Día 15 (Viernes) - Finalización

**9:00-12:00 - API_CONTRACTS.md (3h)**

Documentar 3-4 endpoints principales:

```markdown
# API Contracts

## POST /api/chat

**Request:**
```json
{
  "session_id": "uuid",
  "query": "¿Dónde está МФЦ?",
  "language": "es"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "response": "МФЦ está en...",
    "sources": [{"id": "doc_042", "relevance": 0.95}]
  }
}
```

**Garantías:**
- Latencia p95 < 200ms
- Presición@10 >= 0.8
- Reproducibility: same query → cached response 60s
```

**12:00-17:00 - Review y Cierre (5h)**

Checklist final:
- [ ] All tests passing (`pytest` → 70%+ coverage)
- [ ] mypy strict mode passing
- [ ] Documentación completa (ARCHITECTURE, DECISIONS, REFERENCES, API_CONTRACTS)
- [ ] Evaluación RAG documentada con métricas
- [ ] Benchmarking completado
- [ ] Commit: "feat: evaluation and documentation - master ready"

**Salida Sprint 3:** Sistema evaluable, documentado, defendible ✅

---

## 🚀 SCRIPTS DE AUTOMATIZACIÓN

### Makefile (crear en raíz)

```makefile
.PHONY: help setup test lint run clean evaluate benchmark

help:
	@echo "KubGU Assistant - Targets disponibles"
	@echo "  make setup           Instalar dependencias"
	@echo "  make test            Ejecutar tests (unit + integration + e2e)"
	@echo "  make lint            Ejecutar linters (mypy, pylint, black)"
	@echo "  make run             Correr servidor desarrollo"
	@echo "  make evaluate        Ejecutar evaluación RAG"
	@echo "  make benchmark       Correr load testing"
	@echo "  make clean           Limpiar cachés"

setup:
	pip install -r backend/requirements.txt
	pip install -r backend/requirements-dev.txt
	cp .env.example .env

test:
	cd backend && pytest tests/ -v --cov=app --cov-report=html

lint:
	cd backend && mypy app/ --strict
	cd backend && pylint app/
	cd backend && black --check app/

format:
	cd backend && black app/
	cd backend && isort app/

run:
	cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

evaluate:
	cd backend && python scripts/evaluate_rag.py

benchmark:
	locust -f locustfile.py --host=http://localhost:8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf htmlcov/
```

### GitHub Actions Workflow

Crear `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements-dev.txt
      - run: cd backend && mypy app/ --strict
      - run: cd backend && pytest tests/ -v --cov=app
```

---

## 🎯 ENTREGABLES FINALES

Al término del Sprint 3, deberás tener:

### Código
- [ ] `backend/app/` completamente refactorizado
- [ ] `backend/tests/` con 70%+ coverage
- [ ] `backend/scripts/evaluate_*.py` ejecutables
- [ ] `Makefile` con targets principales
- [ ] `pyproject.toml` + `mypy.ini`

### Documentación
- [ ] `ARCHITECTURE.md` (diagrama + explicación)
- [ ] `DECISIONS.md` (5-7 ADRs)
- [ ] `API_CONTRACTS.md` (contratos explícitos)
- [ ] `EVALUATION_RESULTS.md` (métricas RAG)
- [ ] `PERFORMANCE_REPORT.md` (benchmarks)
- [ ] `REFERENCES.md` (bibliografía académica)

### Evaluación
- [ ] `data/ground_truth_queries.json` (50+ queries anotadas)
- [ ] RAG evaluation: precision@10, recall@10, MRR
- [ ] Latencia benchmarks: p50, p95, p99
- [ ] Test coverage report

---

## 🛡️ DEFENSA DE MAESTRÍA - PREP

### Semana previa
- [ ] Ejecutar `make test` en vivo → verificar 70%+ coverage
- [ ] Ejecutar `make evaluate` → mostrar métricas
- [ ] Revisar documentación → todo debe ser claro
- [ ] Preparar slides con arquitectura + resultados

### Durante defensa
- [ ] Demo: usuario pregunta → sistema responde
- [ ] Mostrar logs JSON estructurados
- [ ] Explicar decisiones arquitectónicas (por qué FastAPI, por qué capas, etc)
- [ ] Defender trade-offs
- [ ] Responder: "¿Cómo evaluaste RAG?" → mostrar métricas

---

## ⏰ CRONOGRAMA RESUMIDO

```
Semana 1 (Lun-Vie): FUNDACIONES
├── Lun: Setup + Pydantic Settings
├── Mar: Excepciones + Typado
├── Mié: Logging + Middleware
├── Jue: Documentación
└── Vie: Testing + Review

Semana 2 (Lun-Vie): MODULARIDAD
├── Lun: Refactorizar main.py
├── Mar-Jue: Migrar servicios
└── Vie: Limpieza + Integración tests

Semana 3 (Lun-Vie): EVALUACIÓN
├── Lun: Dataset ground-truth
├── Mar: Evaluación RAG (métricas)
├── Mié: Benchmarking (latencia)
├── Jue: Documentación académica
└── Vie: Finalización y cierre

Post-Sprint: DEFENSA
└── Preparación, slides, demo
```

---

## ✅ PRÓXIMOS PASOS INMEDIATOS

**HOY (30 de junio):**
1. [ ] Crear Makefile en raíz
2. [ ] Crear estructura de directorios (`mkdir -p backend/app/...`)
3. [ ] Crear `requirements-dev.txt` y instalar: `pip install -r backend/requirements-dev.txt`
4. [ ] Commit inicial: "init: project restructuring for master-level"

**MAÑANA (01 de julio):**
1. [ ] Crear `backend/app/config/settings.py`
2. [ ] Crear `.env` local
3. [ ] Crear `mypy.ini`
4. [ ] Run: `mypy backend/app/` (debe pasar)

---

**¡A trabajar! Este es el path a un proyecto defendible en maestría.** 🚀
