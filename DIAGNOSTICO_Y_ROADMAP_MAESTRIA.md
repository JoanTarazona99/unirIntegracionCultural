# DIAGNÓSTICO Y EVOLUCIÓN A NIVEL MAESTRÍA
## KubGU Assistant - Asistente de Integración Cultural

**Análisis Técnico Integral | Arquitecto de Software | Nivel Maestría**  
**Fecha:** 2026-06-30 | **Versión Actual:** 0.5.0 (MVP)

---

## PARTE A: DIAGNÓSTICO TÉCNICO DETALLADO

### A.1 ESTADO ACTUAL DEL PROYECTO

#### A.1.1 Fortalezas Identificadas ✅

| Dimensión | Fortaleza | Evidencia | Potencial |
|-----------|-----------|----------|----------|
| **Modularidad básica** | Módulos separados por responsabilidad | `enhanced_rag.py`, `translator.py`, `personalization.py`, `phrase_manager.py` | Alto - bien ubicados pero sin inversión de dependencias |
| **Testing E2E** | 29 tests end-to-end con cobertura funcional | `test_e2e.py` documentado y estructurado | Medio - sin unitarios ni integración |
| **Frontend moderno** | Vue.js 3 Composition API, responsive, multiidioma | `index.html` con CSS moderno, detección de idioma | Alto - arquitectura clara |
| **Multiidioma por diseño** | 15 idiomas configurados, traductor + fallback | `translator.py` con diccionario estático + google-trans fallback | Alto - bien implementado |
| **Rate limiting** | Implementación en memoria per-IP | `main.py` RateLimiter class | Medio - funcional pero sin persistencia |
| **Conversation memory** | Gestión de sesiones con historial configurable | `personalization.py` ConversationMemory | Medio - bien estructurado |
| **Docker-ready** | compose.yml con PostgreSQL + backend + frontend | Infraestructura presente | Alto - pero sin usar BD |
| **API REST documentada** | Swagger UI automático de FastAPI | FastAPI con decoradores `/docs` | Alto - profesional |

#### A.1.2 Debilidades Críticas ❌

| Área | Debilidad | Impacto en Maestría | Severidad |
|------|-----------|-------------------|-----------|
| **Tipado de datos** | Pydantic parcialmente usado; tipos Python débiles en módulos auxiliares | Reduce confiabilidad en refactoring; imposible verificar contratos en tiempo de compilación | 🔴 CRÍTICA |
| **Manejo de errores** | No hay excepciones custom; fallbacks ad-hoc; sin logging de errores | Debugging difícil; imposible auditar decisiones; comportamiento impredecible | 🔴 CRÍTICA |
| **Logging** | Solo `print()` sin estructura; sin niveles; sin persistencia | No hay trazabilidad de producción; impossible auditoría; evaluación sin evidencia | 🔴 CRÍTICA |
| **Configuración** | Hardcoded: rutas, límites de rate-limit, TTL de caché, parámetros RAG | No reproducible en entornos; variables mágicas sin documentación | 🔴 CRÍTICA |
| **Deuda técnica residual** | `main_minimal.py`, `debug_startup.py`, `demo_rag.py`, `rag_module.py` sin uso | Confunde propósito del proyecto; aumenta superficie de ataque; mantenimiento múltiple | 🔴 CRÍTICA |
| **Tests unitarios** | Inexistentes; solo E2E | Sin aislamiento de componentes; regresiones silenciosas; imposible evaluar partes en maestría | 🔴 CRÍTICA |
| **Documentación técnica** | Sin ADRs; sin especificaciones de contratos; sin decisiones justificadas | Imposible defender en académica; conocimiento tácito; impossible reproducir racional | 🔴 CRÍTICA |
| **Seguridad: CORS** | ALLOW_ORIGINS + `["*"]` crea vulnerabilidad de lógica | Expone backend a CSRF; contra estándares OWASP | 🔴 CRÍTICA |
| **RAG: Evaluación** | Sin métricas de relevancia, precisión, grounding; sin ground-truth; sin benchmark | Afirmaciones sobre "búsqueda inteligente" sin evidencia | 🟠 ALTA |
| **Caché: Persistencia** | En memoria solamente; se pierde al restart; sin Redis | No escalable; evaluación de hit-rate imposible; no reproducible | 🟠 ALTA |
| **Base de datos** | PostgreSQL en compose pero **NO USADO** en código | Sólo conversation memory en RAM; usuarios/sesiones se pierden | 🟠 ALTA |
| **Traducción: Evaluación** | Sin métricas de fluidez/adecuación; google-trans como fallback no documentado | Sin comparativa con alternativas; traducción no auditada | 🟠 ALTA |
| **TTS/STT: Evaluación** | Sin métricas de latencia, inteligibilidad, error-rate | Afirmaciones sobre "síntesis de voz" sin datos; fallback silencioso | 🟠 ALTA |
| **Requerimientos** | `requirements.txt` sin pinning de versiones; torch con `+cpu` no reproducible | Instalación impredecible entre máquinas; incompatibilidades silenciosas | 🟠 ALTA |
| **Versionado semántico** | Versión hardcodeada "0.5.0" sin CHANGELOG; sin tags git | Imposible rastrear qué cambió; releases no auditables | 🟠 ALTA |
| **CI/CD** | No existe; sin tests automáticos; sin build reproducible | Riesgo de regresiones; imposible desplegar con confianza | 🟠 ALTA |
| **Arquitectura: Acoplamientos** | `main.py` importa directamente todos los módulos; sin inyección de dependencias | Dificil testear; dificil mockear; acoplamiento tight | 🟡 MEDIA |
| **API: Contratos** | Sin OpenAPI schemas explícitos; sin validación exhaustiva de input | Integración frágil; sin auto-documentación de requerimientos | 🟡 MEDIA |
| **Frontend: Tipado** | HTML/JS sin TypeScript; sin validación de respuestas del backend | Errores runtime; debugging en producción | 🟡 MEDIA |
| **Frases: Escalabilidad** | Búsqueda en JSON con `.lower()` loops; sin índices | Performance lineal; O(n) en cada búsqueda; no escalable a 10k+ frases | 🟡 MEDIA |
| **Documentación: Academia** | Sin referencias bibliográficas; sin justificación de decisiones NLP | Indefendible en defensa de tesis; parece cargo-cult | 🟡 MEDIA |

---

### A.1.3 Puntos de Fricción para Defensa de Maestría

#### 🚨 "¿Cómo defiendes la calidad de las búsquedas RAG sin métricas?"
**Respuesta actual:** "Los tests E2E pasan"  
**Respuesta de maestría esperada:** Matriz de evaluación con: precision@k, recall@k, MRR, NDCG, con ground-truth labeled y cobertura de casos  

#### 🚨 "¿Cómo sabes que el traductor es adecuado?"
**Respuesta actual:** "Usamos google-trans con fallback a diccionario"  
**Respuesta de maestría esperada:** Comparative evaluation con BLEU, TER, human evaluation; análisis de error typology  

#### 🚨 "¿Por qué la arquitectura es monolítica?"
**Respuesta actual:** "Es MVP, es simple"  
**Respuesta de maestría esperada:** Capas con inversión de dependencias; testeable; escalable; con justificación de trade-offs  

#### 🚨 "¿Cómo reproduces el project en otra máquina?"
**Respuesta actual:** "Clona y `python main.py`"  
**Respuesta de maestría esperada:** Dockerfile con versiones pinned; Makefile con targets; scripts de setup; testing post-setup  

#### 🚨 "¿Qué pasa cuando falla TTS o traducción?"
**Respuesta actual:** Fallback silencioso; user nunca sabe qué sucedió  
**Respuesta de maestría esperada:** Logging estructurado; métricas de fallback; trazabilidad en debug  

---

### A.1.4 Análisis de Archivos Residuales

```
Archivos RESIDUALES (deuda técnica):
├── backend/main_minimal.py      ← Duplica main.py, versión "mínima" abandonada
├── backend/debug_startup.py     ← Script de debug; debe ser test o ser eliminado
├── backend/demo_rag.py          ← Demostración ad-hoc; no es parte del sistema
├── backend/rag_module.py        ← ¿Alternativa a enhanced_rag.py? Deprecada?
├── backend/audio_module.py      ← Importado en main.py pero ¿realmente usado?
└── telegram_bot/bot_demo.py     ← Demo vs bot.py real; confuso

DECISIÓN: Eliminar todos excepto versión canónica.
```

---

### A.1.5 Estado de Infraestructura

#### Docker Compose
- ✅ PostgreSQL definido
- ✅ Backend container
- ✅ Frontend nginx
- ❌ **PERO:** Código NO usa PostgreSQL; conversation_memory es RAM solamente
- ❌ PERO: Volúmenes montados para desarrollo; no es build para producción

#### Base de Datos
- ✅ Schema: PostgreSQL 15 definido
- ❌ **PERO:** Nunca inicializado; sin migrations
- ❌ PERO: Sin ORM (SQLAlchemy importado pero no usado)
- ❌ PERO: Sin pool de conexiones; sin retry logic

---

### A.1.6 Matriz de Responsabilidades Actual (Confusa)

```
main.py:
├── FastAPI app + CORS + rate limiting ← DEMASIADAS RESPONSABILIDADES
├── Enrutamiento de requests
├── Orquestación de módulos RAG/Translator/Personalization
├── Manejo de sesiones
├── Sirving de archivos estáticos
└── Manejo de audio/TTS

enhanced_rag.py:
├── Carga de documentos JSON
├── Búsqueda semántica (si disponible) vs keyword fallback
├── LLM call (si disponible) con template fallback
└── Traducción de contenido (delegada a translator.py cuando disponible)

translator.py:
├── Traducción con google-trans (si disponible)
├── Diccionario estático de fallback
├── Manejo de 15 idiomas
└── Gestión de errores de traducción

personalization.py:
├── Conversation memory (sesiones)
├── Perfiles de personalización
├── Formateador de respuestas contextual
└── Funciones que PARECEN utilidades pero no son reutilizables

phrase_manager.py:
├── Carga de 200 frases desde JSON
├── Búsqueda por categoría/contexto (O(n))
├── Personalization de frases
└── Almacenamiento en UserPreferences (no persistido)

PROBLEMA: Cada módulo tiene lógica de manejo de errores distinta.
         Sin inversión de dependencias → acoplamiento implícito.
         Sin interfaces claras → imposible mockear en tests.
```

---

### A.1.7 Evaluación de MVP vs Maestría

| Dimensión | MVP (Actual) | Nivel Maestría |
|-----------|--------------|----------------|
| **Funcionalidad** | Chat RAG + Frases + Traducción | ✅ Mismo + Evaluación rigurosa |
| **Confiabilidad** | Works when libraries available | ✅ Tested isoladamente; error handling explícito |
| **Observabilidad** | `print()` statements | ✅ Structured logging; métricas; tracing |
| **Escalabilidad** | RAM; O(n) búsquedas | ✅ BD; índices; caché con persistencia |
| **Mantenibilidad** | Modular; legible | ✅ Tipado; contratos; documentación; tests |
| **Seguridad** | Básica (rate limit) | ✅ Input validation; CORS restrictivo; audit logs |
| **Reproducibilidad** | "Clona y corre" | ✅ Docker reproducible; versions pinned; setup automático |
| **Evaluación** | "Funciona" | ✅ Métricas formales; ground-truth; benchmarks |
| **Documentación** | README + agents.md | ✅ ADRs; decisiones justificadas; referencias académicas |

---

## PARTE B: PROPUESTA DE EVOLUCIÓN A NIVEL MAESTRÍA

### B.1 ROADMAP PRIORIZADO (3 Fases)

#### **FASE 1: FUNDACIONES (Semanas 1-3)** 🏗️
*Objetivo: Hacer el proyecto reproducible, evaluable y defensible*

**P1.1 - Refactorización Estructural** [ALTA PRIORIDAD]
- [ ] Eliminar archivos residuales
- [ ] Inyección de dependencias en main.py
- [ ] Separar responsabilidades: main.py → api_routes.py, config.py, services/
- [ ] Estimado: 15-20 horas

**P1.2 - Configuración y Reproducibilidad** [ALTA PRIORIDAD]
- [ ] Config management: pydantic-settings con validación
- [ ] requirements.txt con pinning de versiones exactas
- [ ] Dockerfile reproducible con build multi-stage
- [ ] Makefile con targets para setup/test/run
- [ ] .env.example completamente documentado
- [ ] Estimado: 12-15 horas

**P1.3 - Tipado Completo** [ALTA PRIORIDAD]
- [ ] mypy strict mode en all backend modules
- [ ] Pydantic v2 schemas para todos los modelos de dominio
- [ ] Type hints en todas las funciones
- [ ] Estimado: 10-12 horas

**P1.4 - Logging Estructurado** [ALTA PRIORIDAD]
- [ ] Reemplazar print() con structlog + JSON output
- [ ] Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL
- [ ] Contexto de request (request_id, session_id, user_id)
- [ ] Rotación de logs; persistencia a disco
- [ ] Estimado: 8-10 horas

**P1.5 - Testing Framework** [ALTA PRIORIDAD]
- [ ] pytest + fixtures para fixtures comunes
- [ ] pytest-asyncio para tests de endpoints
- [ ] Mocking de dependencies (rag_module, translator)
- [ ] Fixture factories para test data
- [ ] Estimado: 12-15 horas

---

#### **FASE 2: EVALUACIÓN Y MÉTRICAS (Semanas 4-6)** 📊
*Objetivo: Hacer el sistema evaluable en términos académicos*

**P2.1 - Evaluación de RAG** [ALTA PRIORIDAD]
- [ ] Dataset ground-truth con 50-100 queries etiquetadas
- [ ] Métricas: precision@k, recall@k, MRR, NDCG
- [ ] Evaluación baseline vs mejorado
- [ ] Análisis de errores por tipo (hallucination, off-topic, etc)
- [ ] Estimado: 20-25 horas

**P2.2 - Evaluación de Traducción** [ALTA PRIORIDAD]
- [ ] Dataset de frases con traducciones de referencia
- [ ] BLEU, TER, BERTScore
- [ ] Análisis de terminología especializada (visa, housing, etc)
- [ ] Tabla de errores por idioma
- [ ] Estimado: 15-20 horas

**P2.3 - Evaluación de TTS/STT** [MEDIA PRIORIDAD]
- [ ] Métricas: latencia (p50, p95, p99)
- [ ] Inteligibilidad (MOS - Mean Opinion Score con testers)
- [ ] Error rate de STT por acento/idioma
- [ ] Estimado: 12-15 horas

**P2.4 - Benchmarking** [MEDIA PRIORIDAD]
- [ ] Performance profile: CPU/Memory/Latency por endpoint
- [ ] Load testing con locust
- [ ] Throughput máximo sostenible
- [ ] Estimado: 10-12 horas

---

#### **FASE 3: CALIDAD PROFESIONAL (Semanas 7-8)** ✨
*Objetivo: Nivel de producción*

**P3.1 - Seguridad** [ALTA PRIORIDAD]
- [ ] Input validation exhaustivo con pydantic validators
- [ ] SQL injection prevention (ORM en queries BD)
- [ ] CORS restrictivo (whitelist no wildcards)
- [ ] API key management (si aplicable)
- [ ] Security headers (CSP, HSTS, etc)
- [ ] Estimado: 10-12 horas

**P3.2 - Base de Datos** [MEDIA PRIORIDAD]
- [ ] Schema migration con Alembic
- [ ] ORM queries con SQLAlchemy
- [ ] Connection pooling
- [ ] Persistence de: usuarios, sesiones, queries RAG, métricas
- [ ] Estimado: 15-18 horas

**P3.3 - CI/CD** [MEDIA PRIORIDAD]
- [ ] GitHub Actions workflow para: test, lint, build
- [ ] SonarQube o Codecov para cobertura
- [ ] Automated release con semantic versioning
- [ ] Estimado: 12-15 horas

**P3.4 - Documentación Académica** [ALTA PRIORIDAD]
- [ ] ADRs (Architecture Decision Records) para 5-7 decisiones clave
- [ ] Sistema de contratos API (OpenAPI explicit schemas)
- [ ] Guía de evaluación del sistema
- [ ] Referencias bibliográficas: LLMs, RAG, traducción, etc
- [ ] Justificación de trade-offs
- [ ] Estimado: 15-20 horas

---

### B.2 DIMENSIONES DE MEJORA

```
ARQUITECTURA DE SOFTWARE
├── Capas explícitas: Presentation / API / Services / Domain / Data / Config
├── Dependency Injection: Inyección explícita; sin imports circulares
├── Clean Boundaries: Contratos claros entre módulos
└── Escalabilidad: De RAM a BD; de O(n) a indexed

CALIDAD DE CÓDIGO
├── Tipado: mypy strict; sin Any implícito
├── Linting: pylint, flake8 con configuración estricta
├── Code review checklist: 10+ items
├── Cobertura: mínimo 70% unitarios; 90% críticos
└── Refactoring: Reducir cyclomatic complexity < 5 por función

EXPERIENCIA DE USUARIO (UX)
├── Feedback visual: Loading states, error toasts, success confirmations
├── Accesibilidad: WCAG 2.1 AA (contrast, keyboard nav, screen reader)
├── Performance: Latency < 200ms en 95% de requests
├── Mobile-first: Responsive; testeado en mobile
└── Internacionalización: i18n framework en frontend; plurals handling

INTERNACIONALIZACIÓN (i18n)
├── Backend: Respuestas en idioma de user sin hardcoding
├── Frontend: Archivos de traducción separados por idioma
├── Fallbacks: Cadena clara: user_lang → app_lang → English
├── Plurals: Manejo correcto de plurales en idiomas complejos
└── Timezone: Timestamps normalizados a UTC

EVALUACIÓN DE MÓDULOS RAG / TRADUCCIÓN / TTS
├── RAG: Precision, Recall, MRR, NDCG, grounding check
├── Traducción: BLEU, TER, BERTScore, human eval
├── TTS/STT: Latency, MOS, WER, accent robustness
├── Dataset: Ground-truth labeled; reproducible
└── Reportes: Tablas, gráficos, análisis de errores

SEGURIDAD Y PRIVACIDAD
├── Input validation: Toda entrada validada con Pydantic
├── Rate limiting: Per-IP, per-user; configuración flexible
├── CORS: Whitelist explícito; sin wildcards
├── Logging: Sin PII sensible; compliant con GDPR
├── Auditoría: Todas las mutaciones logged con timestamp/user
└── Secrets: Variables sensibles en .env; nunca en código

REPRODUCIBILIDAD Y DESPLIEGUE
├── Docker: Reproducible; multi-stage; pequeño
├── Versionado: Semántico (MAJOR.MINOR.PATCH); auto release
├── Documentación: Setup scripts; Makefile; deployment guide
├── Tests: Reproducibles en CI/CD; seed fijo en randomness
└── Monitoreo: Health checks; uptime alerts; error tracking
```

---

## PARTE C: REFACTORIZACIÓN ESTRUCTURAL PROPUESTA

### C.1 NUEVA ESTRUCTURA DE DIRECTORIOS

```
proyectos/unirIntegracionCultural/
│
├── 📦 BACKEND
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     ← SOLO FastAPI app + middleware + mount
│   │   │
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py             ← Pydantic Settings (DB, API keys, etc)
│   │   │   ├── logging_config.py       ← Structlog configuration
│   │   │   └── constants.py            ← Constantes immutables
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py             ← POST /api/chat
│   │   │   │   ├── phrases.py          ← GET /api/phrases/*
│   │   │   │   ├── profile.py          ← POST /api/profile/*
│   │   │   │   ├── health.py           ← GET /health
│   │   │   │   └── metrics.py          ← GET /api/metrics
│   │   │   │
│   │   │   └── dependencies.py         ← Inyección de dependencias (get_db, get_rag, etc)
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rag_service.py          ← Orquestación RAG (legacy: enhanced_rag.py)
│   │   │   ├── translation_service.py  ← Traducción (legacy: translator.py)
│   │   │   ├── phrase_service.py       ← Frases (legacy: phrase_manager.py)
│   │   │   ├── personalization_service.py ← Personalización
│   │   │   ├── tts_service.py          ← Text-to-Speech
│   │   │   └── cache_service.py        ← Caché (legacy: cache_module.py)
│   │   │
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py               ← Pydantic models: UserProfile, Query, Response, etc
│   │   │   ├── entities.py             ← Entidades de negocio: Phrase, Document, etc
│   │   │   ├── value_objects.py        ← Value objects: Language, LanguageLevel, etc
│   │   │   └── exceptions.py           ← Custom exceptions (RAGError, TranslationError, etc)
│   │   │
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── database.py             ← SQLAlchemy session/engine
│   │   │   ├── repositories/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user_repository.py
│   │   │   │   ├── session_repository.py
│   │   │   │   ├── phrase_repository.py
│   │   │   │   └── metrics_repository.py
│   │   │   │
│   │   │   └── migrations/
│   │   │       └── versions/          ← Alembic migrations
│   │   │
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── logger.py              ← Structlog helpers
│   │   │   ├── validators.py          ← Custom Pydantic validators
│   │   │   ├── helpers.py             ← Funciones auxiliares
│   │   │   └── decorators.py          ← @retry, @cache_result, @track_metric
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── cors_middleware.py
│   │   │   ├── rate_limit_middleware.py
│   │   │   ├── logging_middleware.py   ← Request/response logging
│   │   │   └── error_handler.py        ← Exception handlers
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── request_schemas.py      ← Entrada de API
│   │       └── response_schemas.py     ← Salida de API
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 ← pytest fixtures globales
│   │   │
│   │   ├── unit/
│   │   │   ├── test_rag_service.py     ← Unit tests para RAG
│   │   │   ├── test_translation_service.py
│   │   │   ├── test_phrase_service.py
│   │   │   └── test_personalization.py
│   │   │
│   │   ├── integration/
│   │   │   ├── test_chat_endpoint.py
│   │   │   ├── test_phrase_endpoint.py
│   │   │   └── test_profile_endpoint.py
│   │   │
│   │   └── e2e/
│   │       ├── test_user_workflow.py   ← Legacy test_e2e.py, mejorado
│   │       └── test_multilingual_flow.py
│   │
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── generate_ground_truth.py    ← Para evaluación RAG
│   │   ├── evaluate_rag.py             ← Calcular métricas RAG
│   │   ├── evaluate_translation.py     ← BLEU, TER
│   │   ├── benchmark.py                ← Load testing
│   │   └── seed_database.py            ← Inicializar BD
│   │
│   ├── requirements.txt                ← Versionado exacto
│   ├── requirements-dev.txt            ← Dev: pytest, mypy, etc
│   ├── Dockerfile                      ← Multi-stage; reproducible
│   ├── .dockerignore
│   ├── pyproject.toml                  ← Black, isort, pylint config
│   └── mypy.ini                        ← mypy strict
│
├── 📱 FRONTEND
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   │
│   │   ├── components/
│   │   │   ├── ChatBox.vue
│   │   │   ├── PhraseSearch.vue
│   │   │   ├── ProfileForm.vue
│   │   │   └── LanguageSelector.vue
│   │   │
│   │   ├── services/
│   │   │   ├── api.js                  ← API client (type-safe calls)
│   │   │   ├── translation.js          ← i18n
│   │   │   └── storage.js              ← LocalStorage abstraction
│   │   │
│   │   ├── types/
│   │   │   └── api.d.ts                ← TypeScript interfaces (generadas de OpenAPI)
│   │   │
│   │   ├── i18n/
│   │   │   ├── en.json
│   │   │   ├── es.json
│   │   │   ├── ru.json
│   │   │   ├── fr.json
│   │   │   └── index.js
│   │   │
│   │   └── assets/
│   │       └── styles/
│   │           └── main.css
│   │
│   ├── vite.config.js                  ← Build tool (better than plain HTML)
│   ├── package.json
│   ├── tsconfig.json                   ← TypeScript config
│   └── index.html
│
├── 📚 TELEGRAM_BOT
│   ├── bot.py                          ← Bot real
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py
│   │   ├── setup.py
│   │   ├── search.py
│   │   └── phrases.py
│   │
│   └── utils/
│       └── api_client.py               ← HTTP calls al backend
│
├── 📊 DATA
│   ├── phrases/
│   │   ├── complete_phrases.json       ← 200 frases
│   │   ├── ground_truth_queries.json   ← Para evaluación RAG (NUEVO)
│   │   └── generate_phrases.py         ← Mantenido para regen
│   │
│   ├── rag_database.json
│   ├── ground_truth_translation.json   ← Para evaluar traducción (NUEVO)
│   └── audio/
│
├── 📋 DOCUMENTACIÓN
│   ├── ARCHITECTURE.md                 ← Visión general (NUEVO)
│   ├── DECISIONS.md                    ← ADRs (NUEVO)
│   ├── EVALUATION.md                   ← Protocolo de evaluación (NUEVO)
│   ├── API_CONTRACTS.md                ← Contratos explícitos (NUEVO)
│   ├── SETUP.md                        ← Guía de setup
│   ├── EVALUATION_RESULTS.md           ← Métricas y resultados (NUEVO)
│   └── REFERENCES.md                   ← Bibliografía académica (NUEVO)
│
├── ⚙️ CONFIGURACIÓN
│   ├── Makefile                        ← Tasks: setup, test, run, lint
│   ├── docker-compose.yml              ← Actualizado con definiciones correctas
│   ├── docker-compose.prod.yml         ← Production-ready
│   ├── .env.example                    ← Documentado completamente
│   ├── .github/workflows/
│   │   ├── test.yml                    ← Run tests on push
│   │   ├── lint.yml                    ← Code quality checks
│   │   └── release.yml                 ← Auto semantic versioning
│   │
│   ├── .gitignore                      ← Actualizado
│   ├── .editorconfig
│   ├── renovate.json                   ← Automated dependency updates
│   └── CHANGELOG.md                    ← Generado automáticamente
│
└── 🧪 TESTING / BENCHMARKING
    ├── locustfile.py                   ← Load testing (NUEVO)
    └── benchmark_results/
        ├── latency.csv
        ├── throughput.csv
        └── results.html
```

---

### C.2 MAPEO DE MIGRACIÓN (Qué Pasa con los Archivos Existentes)

| Archivo Actual | Destino | Acción | Justificación |
|---|---|---|---|
| `enhanced_rag.py` | `app/services/rag_service.py` | Migrar + refactor | Mantiene lógica core; separar config y error handling |
| `translator.py` | `app/services/translation_service.py` | Migrar + refactor | Ídem |
| `personalization.py` | `app/services/personalization_service.py` | Migrar + split | `ConversationMemory` → `app/data/repositories/session_repository.py` |
| `phrase_manager.py` | `app/services/phrase_service.py` | Migrar + refactor | Usar BD en lugar de JSON searches |
| `cache_module.py` | `app/services/cache_service.py` | Migrar + refactor | Integrar con Redis/BD |
| `main.py` | `app/main.py` + `app/api/routes/` | Refactor masivo | Separar responsabilidades; invertir dependencias |
| `test_e2e.py` | `tests/e2e/test_user_workflow.py` | Mantener + mejorar | Añadir más casos; integrar con pytest |
| `audio_module.py` | `app/services/tts_service.py` | Revisar si existe | Consolidar con TTS logic |
| `llm_module.py` | `app/services/llm_service.py` | Mantener | Subyace en RAG; separar explícitamente |
| **ELIMINAR:** `main_minimal.py` | 🗑️ | Borrar | Redundante |
| **ELIMINAR:** `debug_startup.py` | 🗑️ | Borrar | Debug script; convertir en pytest si necesario |
| **ELIMINAR:** `demo_rag.py` | 🗑️ | Borrar | Demo ad-hoc; documentar en README |
| **ELIMINAR:** `rag_module.py` | 🗑️ | Borrar | Duplicado de enhanced_rag.py |
| **ELIMINAR:** `telegram_bot/bot_demo.py` | 🗑️ | Borrar | Keep bot.py, bot_demo para desarrolladores |
| `requirements.txt` | `backend/requirements.txt` | Actualizar | Pin versiones exactas |
| ← → `backend/requirements-dev.txt` | Crear | Dev dependencies: pytest, mypy, etc |
| `docker-compose.yml` | Actualizar | Mantener con correcciones | Usar BD correctamente; multi-file compose |
| `agents.md` | Documentación/ | Refactor | Convertir a ARCHITECTURE.md + DECISIONS.md |

---

## PARTE D: ESTÁNDARES DE MAESTRÍA

### D.1 TIPADO Y VALIDACIÓN

#### Estándar de Tipado
```python
# ❌ ACTUAL (incorrecto)
def search_rag(query: str, language: str):
    ...
    results = rag_module.search(query)  # Qué devuelve? Dict? List?
    return results

# ✅ MAESTRÍA
from typing import List
from pydantic import BaseModel

class RAGResult(BaseModel):
    id: str
    document_id: str
    content: str
    relevance_score: float  # 0.0-1.0
    source: str
    language: str

def search_rag(query: str, language: str, top_k: int = 10) -> List[RAGResult]:
    """
    Busca documentos relevantes en base de datos RAG.
    
    Args:
        query: Texto de búsqueda (validado, no vacío)
        language: Código ISO de idioma (validado en enum)
        top_k: Número máximo de resultados (1-100)
    
    Returns:
        Lista ordenada por relevancia (descendente)
    
    Raises:
        RAGServiceError: Si búsqueda falla
        ValidationError: Si parámetros inválidos
    """
    ...
```

**Reglas concretas:**
- ✅ Todos los parámetros de función tienen type hints
- ✅ Todos los return values tienen type hints (no `-> None`, ser explícito)
- ✅ Sin `Any` implícito; si es necesario usar `Any`, debe justificarse con # type: ignore
- ✅ Pydantic models para TODA entrada/salida de API
- ✅ Custom validators en Pydantic para lógica de negocio
- ✅ mypy strict mode pasa 100%

---

### D.2 MANEJO DE ERRORES

#### Excepciones Custom
```python
# app/domain/exceptions.py

class AppError(Exception):
    """Base para todas las excepciones de negocio"""
    code: str
    http_status: int = 500
    user_message: str

class RAGError(AppError):
    code = "RAG_ERROR"
    http_status = 503
    user_message = "Búsqueda no disponible; intenta más tarde"

class TranslationError(AppError):
    code = "TRANSLATION_ERROR"
    http_status = 400
    user_message = "Traducción no disponible para este idioma"

class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422
    user_message = "Datos inválidos"
```

#### Implementación en Endpoints
```python
@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, rag_service: RAGService = Depends(get_rag_service)) -> ChatResponse:
    """Chat endpoint con manejo estructurado de errores"""
    try:
        # Lógica principal
        results = rag_service.search(request.query)
        response = rag_service.format_response(results)
        return ChatResponse(success=True, data=response)
    
    except RAGError as e:
        logger.warning(f"RAG error: {e.code}", extra={"query": request.query})
        raise HTTPException(status_code=e.http_status, detail={"code": e.code})
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})
```

**Reglas concretas:**
- ✅ Excepciones custom heredan de `AppError`
- ✅ Cada excepción define `code`, `http_status`, `user_message`
- ✅ Nunca `except Exception: pass` (mask errors)
- ✅ Todos los `except` tienen logging estructurado
- ✅ Fallbacks documentados y explícitos (no silenciosos)

---

### D.3 LOGGING ESTRUCTURADO

```python
# app/utils/logger.py

import structlog
import sys
from structlog.processors import KeyValueRenderer, JSONRenderer

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        JSONRenderer(),  # Salida JSON estructurada
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# USO
logger.info("rag_search_completed", 
    query=request.query,
    result_count=len(results),
    latency_ms=elapsed_time * 1000,
    relevance_scores=[r.score for r in results]
)

logger.error("translation_failed",
    error_code="GOOGLE_TRANS_TIMEOUT",
    language=language,
    retry_count=3
)
```

**Reglas concretas:**
- ✅ Logging JSON en producción (parseable por tools)
- ✅ Contexto por request: `request_id`, `session_id`, `user_id`, `timestamp`
- ✅ Niveles: DEBUG (dev), INFO (normal flow), WARNING (degradation), ERROR (failures), CRITICAL (alert required)
- ✅ Sin PII sensible; sin passwords ni tokens
- ✅ Métricas clave logged: latency, result count, error rates

---

### D.4 CONFIGURACIÓN POR ENTORNO

```python
# app/config/settings.py

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    app_name: str = "KubGU Assistant"
    app_version: str = "1.0.0"
    environment: str = "development"  # dev, staging, prod
    
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/kubgu"
    database_echo: bool = False  # SQL logging
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # RAG
    rag_top_k: int = 10
    rag_min_score: float = 0.3
    semantic_search_enabled: bool = False  # Flag explícito
    
    # Translation
    translation_provider: str = "google_trans"  # fallback: static_dict
    translation_timeout: float = 10.0
    
    # TTS
    tts_provider: str = "gtts"  # Explícito
    tts_cache_enabled: bool = True
    
    # Security
    cors_allowed_origins: List[str] = ["http://localhost:3000"]
    rate_limit_requests: int = 30
    rate_limit_window: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # o "text"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**.env.example documentado:**
```bash
# Environment
ENVIRONMENT=development  # development, staging, production
APP_VERSION=1.0.0

# Database
DATABASE_URL=postgresql://kubgu_user:password@localhost:5432/kubgu_assistant
DATABASE_ECHO=false

# RAG
RAG_TOP_K=10
RAG_MIN_SCORE=0.3
SEMANTIC_SEARCH_ENABLED=false  # Set to 'true' to enable (computationally expensive)

# Translation
TRANSLATION_PROVIDER=google_trans  # Options: google_trans, static_dict
TRANSLATION_TIMEOUT=10.0

# TTS
TTS_PROVIDER=gtts  # Options: gtts, web_speech_fallback
TTS_CACHE_ENABLED=true

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json  # json or text
```

**Reglas concretas:**
- ✅ Pydantic Settings para validación automática
- ✅ TODAS las variables de configuración en .env
- ✅ Valores por defecto seguros (dev settings)
- ✅ Documentación en línea en .env.example
- ✅ Diferentes archivos .env por entorno: .env.dev, .env.test, .env.prod

---

### D.5 VALIDACIÓN DE DATOS

```python
# app/domain/models.py

from pydantic import BaseModel, field_validator, model_validator
from typing import List

class ChatRequest(BaseModel):
    session_id: str
    query: str
    language: str
    
    @field_validator('query')
    @classmethod
    def query_not_empty(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Query debe tener al menos 3 caracteres")
        if len(v) > 1000:
            raise ValueError("Query no puede exceder 1000 caracteres")
        return v.strip()
    
    @field_validator('language')
    @classmethod
    def language_valid(cls, v):
        VALID_LANGUAGES = {"es", "en", "ru", "fr", "pt", "de"}
        if v not in VALID_LANGUAGES:
            raise ValueError(f"Language {v} no soportado. Válidos: {VALID_LANGUAGES}")
        return v
    
    @model_validator(mode='after')
    def validate_model(self):
        # Validación a nivel de modelo (múltiples campos)
        if len(self.session_id) < 8:
            raise ValueError("session_id inválido")
        return self
```

**Reglas concretas:**
- ✅ Field validators para lógica por campo
- ✅ Model validators para lógica entre campos
- ✅ Mensajes de error claros y específicos
- ✅ Mensajes NO exponen detalles de implementación
- ✅ Validar rangos, longitudes, formatos

---

### D.6 CONTRATOS DE API

```markdown
# API CONTRACTS

## Endpoint: POST /api/chat

### Contrato
- **Path**: /api/chat
- **Method**: POST
- **Auth**: Optional (session_id tracking)
- **Rate Limit**: 30 requests/min per IP

### Request

```json
{
  "session_id": "uuid",      // Required, length 36
  "query": "¿Dónde está MFC?", // Required, 3-1000 chars
  "language": "es"           // Required, one of: es, en, ru, fr, pt, de
}
```

### Response 200 OK
```json
{
  "success": true,
  "data": {
    "response": "MFC está en...",
    "sources": [
      {
        "id": "doc_123",
        "title": "МФЦ Адреса",
        "relevance": 0.95
      }
    ],
    "execution_time_ms": 245
  },
  "metadata": {
    "request_id": "req_xyz",
    "timestamp": "2024-06-30T10:30:00Z"
  }
}
```

### Response 400 Bad Request
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Query must be 3-1000 characters",
  "request_id": "req_xyz"
}
```

### Response 503 Service Unavailable
```json
{
  "error_code": "RAG_ERROR",
  "message": "Search service temporarily unavailable",
  "request_id": "req_xyz",
  "retry_after_seconds": 30
}
```

### Guarantees
- ✅ Response time: p95 < 200ms (normal), p95 < 1s (degraded)
- ✅ Uptime SLA: 99% (subject to deployment infrastructure)
- ✅ Request idempotency: Same (session_id, query) within 60s → cached response
- ✅ Data consistency: Queries logged; answers traceable to source documents

### Changelog
- 1.0.0: Initial release
- Future: Support for follow-up questions (context-aware chat)
```

**Reglas concretas:**
- ✅ Contrato explícito para cada endpoint
- ✅ Request/Response schemas con ejemplos
- ✅ Status codes con significado claro
- ✅ Garantías de performance y SLA
- ✅ Changelog de versiones

---

### D.7 PRUEBAS

#### Estándar de Cobertura
- **Unitarias**: ≥70% de funciones
- **Integración**: ≥50% de endpoints
- **E2E**: ≥3 happy paths + 3 error paths
- **Críticas**: ≥90% (RAG, traducción, personalization)

#### Estructura de Tests
```python
# tests/unit/test_rag_service.py

import pytest
from unittest.mock import Mock, patch
from app.services.rag_service import RAGService
from app.domain.exceptions import RAGError

class TestRAGService:
    """Tests para RAGService"""
    
    @pytest.fixture
    def rag_service(self):
        """Fixture para instancia de RAGService"""
        service = RAGService(
            db=Mock(),
            translator=Mock(),
            embedding_model=Mock()
        )
        return service
    
    def test_search_returns_results(self, rag_service):
        """Test: búsqueda exitosa devuelve resultados ordenados"""
        # Arrange
        query = "¿Dónde está MFC?"
        expected_results = [
            {"id": "1", "score": 0.95},
            {"id": "2", "score": 0.85}
        ]
        rag_service.db.search.return_value = expected_results
        
        # Act
        results = rag_service.search(query)
        
        # Assert
        assert len(results) == 2
        assert results[0].score >= results[1].score
        rag_service.db.search.assert_called_once_with(query)
    
    def test_search_with_low_score_filters_results(self, rag_service):
        """Test: resultados bajo threshold se filtran"""
        query = "query"
        rag_service.db.search.return_value = [
            {"id": "1", "score": 0.5},  # < 0.6 threshold
            {"id": "2", "score": 0.8}
        ]
        
        results = rag_service.search(query, min_score=0.6)
        
        assert len(results) == 1
        assert results[0].id == "2"
    
    @pytest.mark.asyncio
    async def test_search_db_error_raises_rag_error(self, rag_service):
        """Test: error de BD genera RAGError"""
        rag_service.db.search.side_effect = ConnectionError("DB unavailable")
        
        with pytest.raises(RAGError) as exc_info:
            rag_service.search("query")
        
        assert exc_info.value.code == "RAG_ERROR"
```

**Reglas concretas:**
- ✅ Nombre de test describe lo que prueba
- ✅ Arrange-Act-Assert structure
- ✅ Fixtures para reutilizar setup
- ✅ Mocks de dependencias externas (DB, API, LLM)
- ✅ Al menos 1 happy path + 1 error path por función
- ✅ Tests son independientes (sin state compartido)

---

### D.8 MÉTRICAS Y BENCHMARKING

#### Métricas a Recolectar
```python
# app/utils/metrics.py

from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Metric:
    name: str
    value: float
    timestamp: datetime
    tags: dict  # e.g., {"endpoint": "/api/chat", "language": "es"}

class MetricsCollector:
    """Recolecta y persiste métricas del sistema"""
    
    def record_query_latency(self, endpoint: str, duration_ms: float, language: str):
        """Latencia de queries (ms)"""
        metric = Metric(
            name="query_latency_ms",
            value=duration_ms,
            timestamp=datetime.now(),
            tags={"endpoint": endpoint, "language": language}
        )
        self.persist(metric)
    
    def record_rag_quality(self, mrr: float, precision_at_10: float, query_count: int):
        """Calidad de búsqueda RAG"""
        metrics = [
            Metric("rag_mrr", mrr, datetime.now(), {}),
            Metric("rag_precision@10", precision_at_10, datetime.now(), {}),
            Metric("rag_query_count", query_count, datetime.now(), {})
        ]
        for m in metrics:
            self.persist(m)
    
    def record_translation_quality(self, bleu: float, ter: float, language_pair: str):
        """Calidad de traducción (BLEU, TER)"""
        metrics = [
            Metric("translation_bleu", bleu, datetime.now(), {"pair": language_pair}),
            Metric("translation_ter", ter, datetime.now(), {"pair": language_pair})
        ]
        for m in metrics:
            self.persist(m)
```

**Métricas Clave por Módulo:**

| Módulo | Métrica | Umbral | Objetivo |
|--------|---------|--------|----------|
| **RAG** | MRR (Mean Reciprocal Rank) | ≥0.7 | Documentos relevantes en top 3 |
| | Precision@10 | ≥0.8 | 8/10 results relevantes |
| | Recall@10 | ≥0.6 | Encuentra 60% de docs relevantes |
| | NDCG | ≥0.75 | Ranking quality (normado) |
| **Traducción** | BLEU score | ≥0.4 | Adequacy (4-grams) |
| | TER (Translation Edit Rate) | ≤0.4 | 40% edits necesarios |
| | Consistencia terminológica | ≥0.9 | Mismos términos siempre igual |
| **TTS** | Latencia p95 | ≤500ms | Síntesis rápida |
| | Latencia p99 | ≤1s | Worst case aceptable |
| | Error rate | ≤1% | Síntesis fallida |
| **API** | Latencia p95 | ≤200ms | Response rápido |
| | Latencia p99 | ≤1s | Worst case aceptable |
| | Availability | ≥99% | 99% uptime |
| | Error rate | ≤0.1% | Errores < 0.1% |

---

### D.9 VERSIONADO SEMÁNTICO

**Formato:** MAJOR.MINOR.PATCH

- **MAJOR** (0→1): Cambios incompatibles en API
- **MINOR** (0→1): Features nuevos; compatible hacia atrás
- **PATCH** (0→1): Bug fixes solamente

**Ejemplo de Changelog:**

```markdown
# CHANGELOG

## [1.0.0] - 2024-07-15 (Production Ready)

### Added
- RAG evaluation framework with precision/recall metrics
- Translation quality evaluation (BLEU, TER)
- Database persistence for users, sessions, queries
- Structured logging with JSON output
- API contracts and OpenAPI schemas
- Comprehensive test suite (70% coverage)

### Changed
- Refactored monolithic main.py into modular services
- Configuration moved to Pydantic Settings
- All modules now have strict typing (mypy passed)

### Fixed
- CORS vulnerability (whitelist instead of wildcard)
- Silent fallback for TTS/translation now logged explicitly
- Rate limiter now uses Redis for distributed systems

### Security
- Input validation for all API endpoints
- Password encryption for database credentials
- Audit logging of all user queries

## [0.5.0] - 2024-06-01 (MVP)
- Initial release with basic RAG, translation, TTS, phrases
```

**Reglas concretas:**
- ✅ CHANGELOG.md mantenido manualmente y generado automáticamente
- ✅ Git tags: `v1.0.0`, `v1.0.1`, `v1.1.0`
- ✅ Auto-release con GitHub Actions
- ✅ Cada PATCH incrementa build metadata

---

## PARTE E: EVALUACIÓN EXPERIMENTAL SERIA

### E.1 FRAMEWORK DE EVALUACIÓN

#### Objetivo General
*Evaluar si el sistema cumple con su propósito: asistir efectivamente a estudiantes extranjeros en integración cultural a través de búsqueda informada, traducción multiidioma y síntesis de voz.*

---

### E.2 EVALUACIÓN DE RAG (BÚSQUEDA INTELIGENTE)

#### Preguntas de Investigación
1. **¿Qué tan precisos son los documentos recuperados?**
2. **¿Recupera todos los documentos relevantes?**
3. **¿Son los documentos de alto rango los más útiles?**
4. **¿Cómo afecta el idioma a la calidad de búsqueda?**

#### Dataset de Evaluación (Ground Truth)

**Construcción:** 50-100 queries anotadas manualmente

```json
{
  "queries": [
    {
      "id": "q_001",
      "query_text": "¿Dónde está la oficina de МФЦ más cercana?",
      "query_language": "es",
      "intent": "location_query",
      "relevant_documents": ["doc_042", "doc_043", "doc_051"],
      "highly_relevant": ["doc_042"],  // Most helpful
      "not_relevant": ["doc_099"]
    },
    {
      "id": "q_002",
      "query_text": "Какие документы нужны для студенческой визы?",
      "query_language": "ru",
      "intent": "procedural_query",
      "relevant_documents": ["doc_015", "doc_016"],
      "highly_relevant": ["doc_015"],
      "not_relevant": ["doc_030", "doc_031"]
    }
  ]
}
```

#### Métricas de Evaluación

| Métrica | Fórmula | Interpretación | Umbral |
|---------|---------|-----------------|--------|
| **Precision@k** | `relevant_in_top_k / k` | Fracción de top-k que es relevante | ≥0.8 |
| **Recall@k** | `relevant_in_top_k / total_relevant` | Fracción de relevantes encontrados en top-k | ≥0.7 |
| **MRR** (Mean Reciprocal Rank) | `1 / average_rank_of_first_relevant` | Posición promedio del primer doc relevante | ≥0.7 |
| **NDCG@k** (Normalized DCG) | Normalized Discounted Cumulative Gain | Ranking quality (penaliza malos docs alto) | ≥0.75 |
| **F1@k** | `2 * (Precision * Recall) / (Precision + Recall)` | Media armónica de precision/recall | ≥0.7 |

#### Protocolo de Evaluación

```python
# scripts/evaluate_rag.py

import json
from pathlib import Path
from app.services.rag_service import RAGService
from app.domain.models import RAGResult

class RAGEvaluator:
    """Evaluador de calidad RAG"""
    
    def __init__(self, ground_truth_file: str, rag_service: RAGService):
        self.ground_truth = json.load(open(ground_truth_file))
        self.rag_service = rag_service
        self.results = {}
    
    def evaluate_query(self, query_id: str, query_text: str, language: str, 
                      relevant_docs: list, k: int = 10):
        """Evaluar una query individual"""
        
        # 1. Retrieve top-k
        retrieved = self.rag_service.search(query_text, language, top_k=k)
        retrieved_ids = [r.document_id for r in retrieved]
        
        # 2. Calculate Precision@k
        relevant_in_k = len(set(retrieved_ids[:k]) & set(relevant_docs))
        precision_k = relevant_in_k / k
        
        # 3. Calculate Recall@k
        recall_k = relevant_in_k / len(relevant_docs)
        
        # 4. Calculate MRR
        mrr = 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in relevant_docs:
                mrr = 1.0 / (i + 1)
                break
        
        # 5. Calculate NDCG@k
        dcg = self._calculate_dcg(retrieved_ids, relevant_docs)
        idcg = self._calculate_idcg(relevant_docs, k)
        ndcg = dcg / idcg if idcg > 0 else 0.0
        
        # Store results
        self.results[query_id] = {
            "precision@k": precision_k,
            "recall@k": recall_k,
            "mrr": mrr,
            "ndcg@k": ndcg,
            "f1@k": 2 * (precision_k * recall_k) / (precision_k + recall_k + 1e-10)
        }
    
    def evaluate_all(self) -> dict:
        """Evaluar todas las queries"""
        for query in self.ground_truth["queries"]:
            self.evaluate_query(
                query_id=query["id"],
                query_text=query["query_text"],
                language=query["query_language"],
                relevant_docs=query["relevant_documents"]
            )
        
        return self._aggregate_results()
    
    def _aggregate_results(self) -> dict:
        """Agregar resultados y calcular promedios"""
        metrics = {
            "precision@10": [],
            "recall@10": [],
            "mrr": [],
            "ndcg@10": []
        }
        
        for query_id, result in self.results.items():
            metrics["precision@10"].append(result["precision@k"])
            metrics["recall@10"].append(result["recall@k"])
            metrics["mrr"].append(result["mrr"])
            metrics["ndcg@10"].append(result["ndcg@k"])
        
        return {
            "mean_precision@10": np.mean(metrics["precision@10"]),
            "mean_recall@10": np.mean(metrics["recall@10"]),
            "mean_mrr": np.mean(metrics["mrr"]),
            "mean_ndcg@10": np.mean(metrics["ndcg@10"]),
            "all_results": self.results
        }

# Uso
if __name__ == "__main__":
    evaluator = RAGEvaluator("data/ground_truth_queries.json", rag_service)
    results = evaluator.evaluate_all()
    print(json.dumps(results, indent=2))
```

#### Análisis de Errores

**Tipología de errores:**

1. **False Negatives** (doc relevante no recuperado)
   - Causa: Query muy diferente del documento
   - Solución: Mejorar query expansion o embeddings

2. **False Positives** (doc irrelevante recuperado)
   - Causa: Palabra clave coincide pero contexto diferente
   - Solución: Añadir filtros semánticos

3. **Ranking Error** (doc relevante pero bajo)
   - Causa: Scoring débil
   - Solución: Mejorar weighting en BM25 o embeddings

---

### E.3 EVALUACIÓN DE TRADUCCIÓN

#### Preguntas de Investigación
1. **¿Qué tan adecuada es la traducción (fidelidad)?**
2. **¿Qué tan fluida es la traducción (naturalidad)?**
3. **¿Cómo maneja terminología especializada (visa, МФЦ)?**
4. **¿Cuál es el acuerdo entre traductores?**

#### Dataset de Evaluación

```json
{
  "translations": [
    {
      "id": "t_001",
      "source_text": "Общежитие находится на улице Октябрьская",
      "source_language": "ru",
      "target_language": "es",
      "reference_translations": [
        "El dormitorio se encuentra en la calle Oktyabrskaya",
        "La residencia estudiantil está en la calle Oktyabrskaya"
      ],
      "domain": "housing",
      "difficulty": "medium"
    }
  ]
}
```

#### Métricas de Evaluación

| Métrica | Fórmula | Rango | Interpretación |
|---------|---------|-------|-----------------|
| **BLEU** | Precision de n-gramas (1-4) | 0-1 | Adequacy (higher = better) |
| **TER** | Translation Edit Rate | 0-∞ | Edits needed to match ref (lower = better) |
| **BERTScore** | Cosine similarity de BERT embeddings | 0-1 | Semantic similarity |
| **chrF3** | F3-score de character n-gramas | 0-1 | Character-level similarity |

#### Protocolo de Evaluación

```python
# scripts/evaluate_translation.py

import nltk.translate.bleu_score as bleu
from bert_score import score as bert_score

class TranslationEvaluator:
    def evaluate_translation(self, hypothesis: str, references: list) -> dict:
        """Evaluar traducción contra referencias"""
        
        # BLEU (corpus level)
        bleu_score = bleu.sentence_bleu(
            [ref.split() for ref in references],
            hypothesis.split(),
            weights=(0.25, 0.25, 0.25, 0.25)
        )
        
        # BERTScore (semantic)
        P, R, F1 = bert_score([hypothesis], [references[0]], lang="es")
        bert_f1 = F1[0].item()
        
        # Manual Evaluation Criteria
        evaluation = {
            "bleu": bleu_score,
            "bert_f1": bert_f1,
            "terminology_preserved": self._check_terminology(hypothesis, references),
            "no_hallucinations": self._check_hallucinations(hypothesis),
            "natural_flow": None  # Anotación manual
        }
        
        return evaluation
    
    def _check_terminology(self, hyp: str, refs: list) -> bool:
        """¿Se preservan términos especializados?"""
        SPECIALIZED_TERMS = {"МФЦ": "MFC", "общежитие": "dormitory"}
        for term, translation in SPECIALIZED_TERMS.items():
            if any(term in ref for ref in refs) and translation not in hyp:
                return False
        return True
```

#### Evaluación Manual

**Escala de 1-5 para evaluadores humanos:**

- **Fidelidad (Adequacy):** 1=Completa distorsión, 5=Equivalencia completa
- **Fluidez (Fluency):** 1=Incomprensible, 5=Nativa
- **Terminología:** 1=Todos mal, 5=Todos correctos

---

### E.4 EVALUACIÓN DE TTS/STT

#### Preguntas de Investigación
1. **¿Cuánto tarda la síntesis de voz?**
2. **¿Qué tan inteligible es el audio?**
3. **¿Qué languages tienen mejor calidad?**

#### Métricas

| Métrica | Objetivo | Método |
|---------|----------|--------|
| **Latencia p50, p95, p99** | p95 < 500ms | Medir tiempo end-to-end |
| **MOS (Mean Opinion Score)** | ≥3.5 | Evaluadores humanos (1-5 scale) |
| **Error Rate** | <1% | Contar síntesis fallidas |
| **Acento/Pronunciación** | Acceptable | Subjective por nativo hablante |

#### Protocolo

```python
# scripts/evaluate_tts.py

import time
from app.services.tts_service import TTSService

class TTSEvaluator:
    def __init__(self, tts_service: TTSService):
        self.tts_service = tts_service
    
    def benchmark_latency(self, texts: list, language: str, iterations: int = 10) -> dict:
        """Benchmarkeo de latencia"""
        latencies = []
        
        for text in texts:
            for _ in range(iterations):
                start = time.time()
                audio = self.tts_service.synthesize(text, language)
                latency_ms = (time.time() - start) * 1000
                latencies.append(latency_ms)
        
        return {
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99),
            "mean": np.mean(latencies)
        }
```

---

### E.5 EVALUACIÓN CON USUARIOS

#### Protocolo de Prueba con Usuarios Objetivo

**Participantes:** 10-15 estudiantes extranjeros de KubGU (países objetivo: Vietnam, China, Syria, Nigeria)

**Tarea:**
```
Eres un estudiante extranjero recién llegado a KubGU.
Tienes 5 preguntas realistas que necesitas responder:
1. ¿Dónde está la oficina МФЦ?
2. ¿Cuál es el costo del dormitorio?
3. ¿Qué documentos necesito para una visa de estudiante?
4. ¿Hay acceso a internet en el dormitorio?
5. ¿Cómo puedo registrarme en la clínica universitaria?

Usa el asistente KubGU para encontrar respuestas.
Marca tu satisfacción en escala 1-5 para cada aspuesta.
```

**Métricas de UX:**

```json
{
  "satisfaction": {
    "response_helpfulness": "1-5",
    "response_clarity": "1-5",
    "search_relevance": "1-5",
    "translation_quality": "1-5",
    "voice_clarity": "1-5"
  },
  "system_usability": {
    "ease_to_find_answer": "1-5",
    "interface_intuitiveness": "1-5",
    "time_to_answer_seconds": "number"
  },
  "qualitative_feedback": "free text"
}
```

---

### E.6 HIPÓTESIS Y AMENAZAS A LA VALIDEZ

#### Hipótesis Principales

| Hipótesis | Predicción | Métrica | Resultado Esperado |
|-----------|-----------|---------|-------------------|
| **H1: RAG es efectivo** | Búsqueda recupera docs relevantes | MRR ≥ 0.7 | ✅ Documentos útiles en top 3 |
| **H2: Traducción es comprensible** | Traducciones son adecuadas | BLEU ≥ 0.4 | ✅ Adequacy aceptable |
| **H3: TTS es usable** | Síntesis < 500ms en p95 | Latencia | ✅ Respuesta rápida |
| **H4: Terminología especializada** | Términos visa/housing correctos | % Accuracy | ≥ 90% |

#### Amenazas a la Validez

| Amenaza | Riesgo | Mitigación |
|---------|--------|-----------|
| **Sesgo del dataset** | Ground truth puede ser incompleto | Multiple annotators; Cohen's kappa |
| **Cambio de dominio** | Queries nuevas no vistas en training | Test set separado; cross-validation |
| **Dependencia de librerías** | google-trans puede cambiar formato | Pin versiones exactas; fall back a static dict |
| **Variabilidad de LLM** | Respuestas stochastic | Temperature=0 en evaluaciones |
| **Sesgo del evaluador** | Manual evaluation subjetivo | Kappa agreement ≥ 0.6 entre annotators |
| **Tamaño de muestra** | 50 queries puede ser pequeño | Power analysis; 100+ queries idealmente |

---

## PARTE F: ENTREGABLES CONCRETOS

### F.1 LISTA EXACTA DE ARCHIVOS A CREAR

```bash
# CONFIGURACIÓN Y BUILD
├── Makefile                          [NEW - Build automation]
├── pyproject.toml                    [NEW - Project metadata, Black/isort config]
├── mypy.ini                          [NEW - mypy strict configuration]
├── .dockerignore                     [NEW - Docker optimization]
├── backend/requirements-dev.txt      [NEW - Development dependencies]
├── docker-compose.prod.yml           [NEW - Production compose]
├── .github/workflows/test.yml        [NEW - Run tests on push]
├── .github/workflows/lint.yml        [NEW - Code quality on push]
├── .github/workflows/release.yml     [NEW - Auto semantic versioning]

# CÓDIGO BACKEND (REFACTORIZADO)
├── backend/app/__init__.py           [NEW - Package marker]
├── backend/app/main.py               [REFACTORED FROM main.py - FastAPI app only]
├── backend/app/config/__init__.py    [NEW]
├── backend/app/config/settings.py    [NEW - Pydantic settings]
├── backend/app/config/logging_config.py [NEW - Structlog setup]
├── backend/app/config/constants.py   [NEW - App constants]
├── backend/app/api/__init__.py       [NEW]
├── backend/app/api/dependencies.py   [NEW - Dependency injection]
├── backend/app/api/routes/__init__.py [NEW]
├── backend/app/api/routes/chat.py    [NEW - Chat endpoints]
├── backend/app/api/routes/phrases.py [NEW - Phrase endpoints]
├── backend/app/api/routes/profile.py [NEW - Profile endpoints]
├── backend/app/api/routes/health.py  [NEW - Health check]
├── backend/app/api/routes/metrics.py [NEW - Metrics endpoints]
├── backend/app/services/__init__.py  [NEW]
├── backend/app/services/rag_service.py [NEW - FROM enhanced_rag.py]
├── backend/app/services/translation_service.py [NEW - FROM translator.py]
├── backend/app/services/phrase_service.py [NEW - FROM phrase_manager.py]
├── backend/app/services/personalization_service.py [NEW - FROM personalization.py]
├── backend/app/services/tts_service.py [NEW - Text-to-speech]
├── backend/app/services/cache_service.py [NEW - FROM cache_module.py]
├── backend/app/domain/__init__.py    [NEW]
├── backend/app/domain/models.py      [NEW - Pydantic request/response models]
├── backend/app/domain/entities.py    [NEW - Business entities]
├── backend/app/domain/value_objects.py [NEW - Enum, Language, LanguageLevel, etc]
├── backend/app/domain/exceptions.py  [NEW - Custom exceptions]
├── backend/app/data/__init__.py      [NEW]
├── backend/app/data/database.py      [NEW - SQLAlchemy session/engine]
├── backend/app/data/repositories/__init__.py [NEW]
├── backend/app/data/repositories/user_repository.py [NEW]
├── backend/app/data/repositories/session_repository.py [NEW]
├── backend/app/data/repositories/phrase_repository.py [NEW]
├── backend/app/data/repositories/metrics_repository.py [NEW]
├── backend/app/data/migrations/__init__.py [NEW - Alembic]
├── backend/app/middleware/__init__.py [NEW]
├── backend/app/middleware/cors_middleware.py [NEW - CORS handling]
├── backend/app/middleware/rate_limit_middleware.py [NEW - Rate limiting]
├── backend/app/middleware/logging_middleware.py [NEW - Request logging]
├── backend/app/middleware/error_handler.py [NEW - Exception handlers]
├── backend/app/utils/__init__.py     [NEW]
├── backend/app/utils/logger.py       [NEW - Structlog helpers]
├── backend/app/utils/validators.py   [NEW - Custom validators]
├── backend/app/utils/helpers.py      [NEW - Utility functions]
├── backend/app/utils/decorators.py   [NEW - Retry, cache, metrics]
├── backend/app/schemas/__init__.py   [NEW]
├── backend/app/schemas/request_schemas.py [NEW - OpenAPI schemas]
├── backend/app/schemas/response_schemas.py [NEW - OpenAPI schemas]

# TESTS
├── backend/tests/__init__.py         [NEW]
├── backend/tests/conftest.py         [NEW - pytest fixtures]
├── backend/tests/unit/test_rag_service.py [NEW]
├── backend/tests/unit/test_translation_service.py [NEW]
├── backend/tests/unit/test_phrase_service.py [NEW]
├── backend/tests/integration/test_chat_endpoint.py [NEW]
├── backend/tests/integration/test_phrase_endpoint.py [NEW]
├── backend/tests/e2e/test_user_workflow.py [NEW - improved test_e2e.py]

# SCRIPTS Y BENCHMARKING
├── backend/scripts/__init__.py       [NEW]
├── backend/scripts/generate_ground_truth.py [NEW - For RAG evaluation]
├── backend/scripts/evaluate_rag.py   [NEW - RAG metrics]
├── backend/scripts/evaluate_translation.py [NEW - BLEU, TER]
├── backend/scripts/benchmark.py      [NEW - Load testing with locust]
├── backend/scripts/seed_database.py  [NEW - Initialize BD]
├── locustfile.py                     [NEW - At project root for load tests]

# FRONTEND (MEJORADO)
├── frontend/src/main.js              [NEW - Entry point]
├── frontend/src/App.vue              [NEW - Main component]
├── frontend/src/components/ChatBox.vue [NEW]
├── frontend/src/components/PhraseSearch.vue [NEW]
├── frontend/src/components/ProfileForm.vue [NEW]
├── frontend/src/services/api.js      [NEW - Type-safe API client]
├── frontend/src/services/translation.js [NEW - i18n]
├── frontend/src/types/api.d.ts       [NEW - TypeScript types]
├── frontend/src/i18n/en.json         [NEW]
├── frontend/src/i18n/es.json         [NEW]
├── frontend/src/i18n/ru.json         [NEW]
├── frontend/vite.config.js           [NEW - Build tool]
├── frontend/tsconfig.json            [NEW - TypeScript config]
├── frontend/package.json             [NEW - Dependencies]

# DOCUMENTACIÓN TÉCNICA Y ACADÉMICA
├── ARCHITECTURE.md                   [NEW - System design]
├── DECISIONS.md                      [NEW - Architecture Decision Records (5-7 ADRs)]
├── EVALUATION.md                     [NEW - Evaluation protocol and results]
├── API_CONTRACTS.md                  [NEW - Explicit API contracts per endpoint]
├── SETUP.md                          [UPDATED - Comprehensive setup guide]
├── DEPLOYMENT.md                     [NEW - Deployment procedures]
├── TESTING.md                        [NEW - Testing strategy and coverage]
├── REFERENCES.md                     [NEW - Academic citations]
├── CHANGELOG.md                      [NEW - Version history]
└── PERFORMANCE_REPORT.md             [NEW - Benchmarking results]

# EVALUACIÓN Y DATOS
├── data/ground_truth_queries.json    [NEW - 50+ labeled queries for RAG eval]
├── data/ground_truth_translation.json [NEW - Translation references]
├── benchmark_results/latency.csv     [NEW - Performance data]
├── benchmark_results/throughput.csv  [NEW - Throughput data]
└── benchmark_results/results.html    [NEW - Visual report]
```

---

### F.2 ARCHIVOS A MODIFICAR

```bash
# BACKEND
backend/main.py                        → REFACTORED: Move logic to app/
backend/enhanced_rag.py                → REFACTORED: Migrate to app/services/rag_service.py
backend/translator.py                  → REFACTORED: Migrate to app/services/translation_service.py
backend/personalization.py             → REFACTORED: Split into service + repositories
backend/phrase_manager.py              → REFACTORED: Migrate to app/services/phrase_service.py
backend/cache_module.py                → REFACTORED: Migrate to app/services/cache_service.py
backend/test_e2e.py                    → REFACTORED: Migrate to tests/e2e/

backend/requirements.txt               → ADD: Pin all versions; add dev dependencies
backend/Dockerfile                     → UPDATE: Multi-stage build; clean cache
docker-compose.yml                     → UPDATE: Correct service config; use BD
.env.example                           → EXPANDED: Document all config options

# FRONTEND (OPCIONAL - If using Vite)
frontend/index.html                    → Keep but integrate with Vite build system
frontend/demo.html                     → Archive or remove

# GIT
.gitignore                             → ADD: __pycache__, .pytest_cache, .mypy_cache, etc
CHANGELOG.md                           → CREATE: Document all releases

# RAÍZ
start.sh / start.bat                   → UPDATE: Point to new Makefile targets
agents.md                              → ARCHIVE: Content moved to ARCHITECTURE.md
```

---

### F.3 ARCHIVOS A ELIMINAR

```bash
# DEUDA TÉCNICA
backend/main_minimal.py                ❌ Duplicate of main.py
backend/debug_startup.py               ❌ Debug script; not part of system
backend/demo_rag.py                    ❌ Ad-hoc demo; document in README if needed
backend/rag_module.py                  ❌ Deprecated; use enhanced_rag.py
telegram_bot/bot_demo.py               ❌ Keep bot.py; bot_demo confuses purpose
```

---

### F.4 ESTÁNDARES DE CÓDIGO A IMPLEMENTAR

```bash
# LINTING Y FORMATTING
pyproject.toml:
  [tool.black]
  line-length = 100
  target-version = ['py311']
  
  [tool.isort]
  profile = "black"
  line_length = 100
  
  [tool.pylint]
  max-line-length = 100
  disable = ["C0111"]  # Missing docstring (allow some)

# TYPING
mypy.ini:
  [mypy]
  python_version = 3.11
  warn_return_any = True
  warn_unused_configs = True
  disallow_untyped_defs = True
  disallow_incomplete_defs = True
  check_untyped_defs = True
  strict_optional = True
  no_implicit_optional = True

# TESTING
pytest.ini or pyproject.toml:
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "--cov=app --cov-report=html --cov-fail-under=70"
  asyncio_mode = "auto"
```

---

## PARTE G: CAMBIOS EJECUTABLES Y PRIORITARIOS

### G.1 MATRIZ DE PRIORIDAD

```
┌─────────────────────────────────────────────────────────────────┐
│ MAPEO: Impacto Académico vs Effort Requerido                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ALTO IMPACTO, BAJO EFFORT (Hacer primero):                     │
│  ✅ P1.2: Configuración + reproducibilidad (12h)               │
│  ✅ P1.4: Logging estructurado (8h)                             │
│  ✅ P3.4: Documentación académica (15h)                         │
│                                                                  │
│  ALTO IMPACTO, MEDIO EFFORT (Segundo):                          │
│  ✅ P1.3: Tipado completo (10h)                                 │
│  ✅ P1.1: Refactorización modular (15h)                         │
│  ✅ P2.1: Evaluación RAG (20h)                                  │
│                                                                  │
│  MEDIO IMPACTO, BAJO EFFORT (Bonus):                            │
│  ✅ P1.5: Testing framework (12h)                               │
│  ✅ P3.1: Seguridad (10h)                                       │
│                                                                  │
│  BAJO IMPACTO, ALTO EFFORT (Opcional):                          │
│  ⚠️ P3.2: Base de datos full (15h) - Usar si tiempo disponible │
│  ⚠️ P3.3: CI/CD (12h) - Nice to have                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### G.2 SPRINT RECOMENDADO

#### **Sprint 1: Fundaciones (Semana 1)**
**Objetivo:** Proyecto reproducible y evaluable

- [ ] **Tarea 1.1** (3h): Crear estructura de directorios; mover archivos
  ```bash
  mkdir -p backend/app/{config,api,services,domain,data,utils,middleware,schemas,tests}
  mkdir -p backend/app/api/routes
  mkdir -p backend/app/data/repositories
  ```

- [ ] **Tarea 1.2** (4h): Pydantic Settings + .env
  - Crear `backend/app/config/settings.py`
  - Actualizar `requirements.txt` con versiones exactas
  - Crear `.env.example` documentado
  - Test: `python -c "from app.config.settings import settings; print(settings)"`

- [ ] **Tarea 1.3** (3h): Structlog + logging middleware
  - Crear `backend/app/config/logging_config.py`
  - Reemplazar todos los `print()` con `logger.info/warning/error`
  - Crear `backend/app/middleware/logging_middleware.py`

- [ ] **Tarea 1.4** (4h): Tipado + mypy
  - Añadir type hints a todos los módulos
  - Crear `mypy.ini`
  - Run: `mypy backend/app/` (debe pasar)

- [ ] **Tarea 1.5** (2h): Documentación arquitectónica inicial
  - Crear `ARCHITECTURE.md` (diagrama ASCII de capas)
  - Crear `DECISIONS.md` (primeras 2 ADRs)

**Salida del Sprint 1:** Proyecto es reproducible, tipado, loggeable

---

#### **Sprint 2: Modularidad y Testing (Semana 2)**
**Objetivo:** Código limpio, testeable, con buena cobertura

- [ ] **Tarea 2.1** (6h): Refactorizar main.py
  - Separar rutas en `backend/app/api/routes/`
  - Inyectar dependencias en `backend/app/api/dependencies.py`
  - main.py queda limpio: solo FastAPI + middleware + mount

- [ ] **Tarea 2.2** (6h): Migrar servicios
  - `enhanced_rag.py` → `backend/app/services/rag_service.py` (con type hints)
  - `translator.py` → `backend/app/services/translation_service.py`
  - `phrase_manager.py` → `backend/app/services/phrase_service.py`
  - Mantener misma lógica; solo mejorar interfaces

- [ ] **Tarea 2.3** (6h): Testing framework
  - Crear `backend/tests/conftest.py` (fixtures)
  - Escribir 5-10 unit tests para RAG service
  - Crear GitHub Actions workflow para auto-run tests

- [ ] **Tarea 2.4** (3h): Eliminar deuda técnica
  - Borrar: `main_minimal.py`, `debug_startup.py`, `demo_rag.py`, `rag_module.py`
  - Verificar que no hay imports rotos

**Salida del Sprint 2:** Proyecto modular, testeable, sin deuda técnica

---

#### **Sprint 3: Evaluación (Semana 3)**
**Objetivo:** Métricas formales; sistema evaluable académicamente

- [ ] **Tarea 3.1** (8h): Dataset ground-truth RAG
  - Crear `data/ground_truth_queries.json` con 50+ queries anotadas
  - Script: `scripts/generate_ground_truth.py`

- [ ] **Tarea 3.2** (8h): Evaluación RAG
  - Crear `scripts/evaluate_rag.py` (precision@k, recall@k, MRR, NDCG)
  - Ejecutar evaluación; documentar resultados en `EVALUATION_RESULTS.md`

- [ ] **Tarea 3.3** (6h): Benchmarking
  - Crear `locustfile.py` con carga simulada
  - Medir: latencia (p50, p95, p99), throughput
  - Documentar en `PERFORMANCE_REPORT.md`

- [ ] **Tarea 3.4** (4h): Documentación académica final
  - Actualizar `DECISIONS.md` con 5-7 ADRs
  - Crear `REFERENCES.md` (citas académicas sobre RAG, LLM, traducción)
  - Crear `API_CONTRACTS.md` (contratos explícitos)

**Salida del Sprint 3:** Sistema evaluable; resultados documentados; defensa posible

---

### G.3 SCRIPTS DE AUTOMATIZACIÓN

#### Makefile (Ejemplo)
```makefile
.PHONY: help setup test lint run clean docker-build docker-run

help:
	@echo "KubGU Assistant - Available targets"
	@echo "  make setup           Install dependencies & setup environment"
	@echo "  make test            Run all tests (unit + integration + e2e)"
	@echo "  make lint            Run linters (mypy, pylint, black)"
	@echo "  make format          Format code with black & isort"
	@echo "  make run             Run development server"
	@echo "  make docker-build    Build Docker image"
	@echo "  make docker-run      Run in Docker container"
	@echo "  make evaluate-rag    Run RAG evaluation"
	@echo "  make benchmark       Run load testing"

setup:
	pip install -r backend/requirements.txt
	pip install -r backend/requirements-dev.txt
	cd frontend && npm install
	python backend/scripts/seed_database.py

test:
	pytest backend/tests/ -v --cov=app --cov-report=html

lint:
	mypy backend/app/ --strict
	pylint backend/app/
	black --check backend/app/
	isort --check backend/app/

format:
	black backend/app/
	isort backend/app/

run:
	cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker-compose build

docker-run:
	docker-compose up

evaluate-rag:
	python backend/scripts/evaluate_rag.py

benchmark:
	locust -f locustfile.py --host=http://localhost:8000 -u 100 -r 10

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	rm -rf htmlcov/
```

---

## PARTE H: SALIDA FINAL - CHECKLISTS

### H.1 CHECKLIST DE IMPLEMENTACIÓN

```markdown
# CHECKLIST DE IMPLEMENTACIÓN A MAESTRÍA

## ✅ FASE 1: FUNDACIONES (Semana 1)

### Estructura y Configuración
- [ ] Crear estructura de directorios modular (`app/`, `tests/`, `scripts/`)
- [ ] Crear Pydantic Settings (`config/settings.py`)
- [ ] Crear `.env.example` completamente documentado
- [ ] Pin todas las versiones en `requirements.txt`
- [ ] Crear `requirements-dev.txt` con pytest, mypy, black
- [ ] Crear `pyproject.toml` con Black/isort/pylint config
- [ ] Crear `mypy.ini` en modo strict

### Tipado y Calidad
- [ ] Añadir type hints a TODAS las funciones
- [ ] Crear `app/domain/exceptions.py` con excepciones custom
- [ ] Crear `app/domain/models.py` con Pydantic models
- [ ] Ejecutar `mypy app/` y verificar 100% passing
- [ ] Crear `pyproject.toml` con Black formatting

### Logging
- [ ] Crear `app/config/logging_config.py` con structlog
- [ ] Reemplazar TODOS los `print()` con `logger.info/warning/error`
- [ ] Crear `app/middleware/logging_middleware.py` para request logging
- [ ] Testar: output deve ser JSON parseable

### Documentación Inicial
- [ ] Crear `ARCHITECTURE.md` con diagrama de capas
- [ ] Crear `DECISIONS.md` con primeras 2 ADRs
- [ ] Crear `SETUP.md` con instrucciones claras
- [ ] Crear `API_CONTRACTS.md` para cada endpoint

---

## ✅ FASE 2: MODULARIDAD (Semana 2)

### Refactorización de Código
- [ ] Refactorizar `main.py` → separar en rutas/servicios/config
- [ ] Crear `app/api/routes/` con archivos por endpoint
- [ ] Crear `app/services/` con servicios inyectados
- [ ] Crear `app/api/dependencies.py` con inyección de dependencias
- [ ] Crear `app/middleware/` para CORS/rate-limit/error handling
- [ ] Todos los servicios usan Dependency Injection

### Migración de Módulos
- [ ] Migrar `enhanced_rag.py` → `app/services/rag_service.py`
- [ ] Migrar `translator.py` → `app/services/translation_service.py`
- [ ] Migrar `phrase_manager.py` → `app/services/phrase_service.py`
- [ ] Migrar `personalization.py` → `app/services/personalization_service.py`
- [ ] Migrar `cache_module.py` → `app/services/cache_service.py`

### Limpieza de Deuda Técnica
- [ ] Eliminar `main_minimal.py`
- [ ] Eliminar `debug_startup.py`
- [ ] Eliminar `demo_rag.py`
- [ ] Eliminar `rag_module.py`
- [ ] Eliminar `telegram_bot/bot_demo.py`
- [ ] Verificar que no hay imports rotos (`grep -r "from main_minimal import"`)

### Testing Framework
- [ ] Crear `tests/conftest.py` con fixtures
- [ ] Crear `tests/unit/test_*.py` para cada servicio (5+ tests)
- [ ] Crear `tests/integration/test_*.py` para endpoints
- [ ] Crear `tests/e2e/` mejorado a partir de `test_e2e.py`
- [ ] Verificar cobertura ≥70%: `pytest --cov`

---

## ✅ FASE 3: EVALUACIÓN Y PRODUCCIÓN (Semana 3)

### Evaluación de RAG
- [ ] Crear `data/ground_truth_queries.json` (50+ queries anotadas)
- [ ] Crear `scripts/generate_ground_truth.py`
- [ ] Crear `scripts/evaluate_rag.py` (precision@k, recall@k, MRR, NDCG)
- [ ] Ejecutar evaluación y documentar resultados
- [ ] Crear `EVALUATION_RESULTS.md` con tabla de métricas

### Evaluación de Traducción (Bonus)
- [ ] Crear `data/ground_truth_translation.json`
- [ ] Crear `scripts/evaluate_translation.py` (BLEU, TER)
- [ ] Ejecutar y documentar results

### Benchmarking
- [ ] Crear `locustfile.py` con carga simulada
- [ ] Ejecutar: `locust -f locustfile.py`
- [ ] Medir: latencia (p50, p95, p99), throughput
- [ ] Documentar en `PERFORMANCE_REPORT.md`

### Seguridad
- [ ] Revisión de CORS: whitelist específico (no wildcards)
- [ ] Validación exhaustiva en Pydantic
- [ ] Input sanitization para SQL injection
- [ ] Rate limiting funcional
- [ ] Logs sin PII sensible

### CI/CD
- [ ] Crear `.github/workflows/test.yml`
- [ ] Crear `.github/workflows/lint.yml`
- [ ] Crear `.github/workflows/release.yml` (auto semantic versioning)

### Docker y Despliegue
- [ ] Dockerfile multi-stage
- [ ] `docker-compose.yml` y `docker-compose.prod.yml`
- [ ] Crear `Makefile` con targets
- [ ] Crear `DEPLOYMENT.md`

### Documentación Final
- [ ] Completar `DECISIONS.md` con 5-7 ADRs
- [ ] Crear `REFERENCES.md` con bibliografía académica
- [ ] Crear `TESTING.md` con estrategia de testing
- [ ] Crear `CHANGELOG.md` con historia de versiones

---

## ✅ DEFENSA ACADÉMICA - PREP

### Pre-Defensa (1 semana antes)
- [ ] Documentación completa: ARCHITECTURE.md, DECISIONS.md, EVALUATION.md
- [ ] Todas las métricas calculadas y documentadas
- [ ] Tests ejecutando (29/29 PASS objetivo)
- [ ] Demo del sistema funcionando
- [ ] Slides con:
  - Problem statement
  - Arquitectura del sistema
  - Decisiones técnicas con justificación
  - Resultados de evaluación
  - Lecciones aprendidas
  - Trabajo futuro

### Durante Defensa
- [ ] Ejecutar `make test` en vivo (demostrar cobertura)
- [ ] Demostrar endpoint ejecutando en tiempo real
- [ ] Mostrar logs estructurados JSON
- [ ] Explicar cada decisión arquitectónica
- [ ] Defender trade-offs
```

---

### H.2 CHECKLIST DE DEFENSA ACADÉMICA

```markdown
# CHECKLIST DE DEFENSA ACADÉMICA

## 📋 PREPARACIÓN ACADÉMICA

### Sistema Defensible
- [ ] ¿Puedo explicar cada componente del sistema?
- [ ] ¿Cada decisión tiene justificación técnica documented?
- [ ] ¿Hay evidencia de evaluación rigurosa (métricas, benchmarks)?
- [ ] ¿El código es reproducible en otra máquina?
- [ ] ¿Hay referencias académicas para decisiones (RAG, LLM, traducción)?

### Métricas y Evidencia
- [ ] RAG evaluation: precision@k, recall@k, MRR, NDCG con resultados
- [ ] Traducción evaluation: BLEU, TER scores documentados
- [ ] TTS evaluation: latencia (p50, p95, p99) medida
- [ ] API performance: throughput y latencia bajo carga
- [ ] Test coverage: ≥70% de líneas de código
- [ ] Error handling: todas las excepciones loggadas

### Arquitectura
- [ ] ¿Puedo dibujar la arquitectura en una hoja?
- [ ] ¿Cada capa tiene responsabilidad clara?
- [ ] ¿Las dependencias fluyen hacia una dirección?
- [ ] ¿Sin ciclos de importación?
- [ ] ¿Separación clara: presentation / API / services / domain / data?

### Documentación
- [ ] ARCHITECTURE.md: Existe y es claro
- [ ] DECISIONS.md: 5-7 ADRs con contexto + decisión + consecuencias
- [ ] API_CONTRACTS.md: Contratos explícitos per endpoint
- [ ] EVALUATION.md: Protocolo y resultados
- [ ] REFERENCES.md: Citas académicas (10+ referencias)
- [ ] CHANGELOG.md: Historial de cambios

### Calidad de Código
- [ ] mypy: strict mode pasa 100%
- [ ] pylint: score ≥8.0
- [ ] black: formatting aplicado
- [ ] Todos los tipos explícitos (sin Any implícito)
- [ ] Excepciones custom por dominio
- [ ] Logging estructurado

### Testing
- [ ] Unit tests: ≥5 por módulo crítico (RAG, translation, personalization)
- [ ] Integration tests: ≥3 por endpoint
- [ ] E2E tests: ≥3 happy path + ≥3 error path
- [ ] Fixtures reusables
- [ ] CI/CD pipeline ejecutando

### Evaluación Seria
- [ ] Dataset ground-truth anotado (50+ queries)
- [ ] Métricas calculadas y comparadas
- [ ] Análisis de errores documentado
- [ ] Resultados vs baseline/SOTA
- [ ] Amenazas a validez discutidas
- [ ] Reproducibilidad del experimento garantizada

---

## 🎯 DURANTE DEFENSA

### Presentación (10-15 min)
- [ ] Problema claramente definido
- [ ] Solución propuesta con diagrama
- [ ] Componentes principales explicados
- [ ] Decisiones arquitectónicas clave
- [ ] Resultados de evaluación

### Demo (5 min)
- [ ] Usuario crea perfil
- [ ] Usuario hace pregunta
- [ ] Sistema devuelve respuesta + frases + traducción
- [ ] Mostrar logs estructurados
- [ ] Mostrar cobertura de tests

### Preguntas (15-20 min)
- [ ] "¿Por qué elegiste FastAPI?" → Justificación técnica
- [ ] "¿Cómo evaluaste RAG?" → Protocolo + métricas
- [ ] "¿Qué tan bien escala?" → Benchmarks + análisis
- [ ] "¿Cuáles son las limitaciones?" → Honestidad; amenazas a validez
- [ ] "¿Qué harías diferente?" → Reflexión y aprendizaje

### Respuestas Que Evitar
- ❌ "No sé"
- ❌ "Así lo encontré en internet"
- ❌ "Funciona pero no sé por qué"
- ❌ "Copié y pegué el código"
- ❌ "Las métricas se ven bien"

### Respuestas Que Impresionan
- ✅ "Elegí X por [decisión técnica justificada]"
- ✅ "Evaluamos con [métrica], resultando en [número]"
- ✅ "El trade-off fue [beneficio] vs [costo]"
- ✅ "Si tuviera más tiempo, haría [mejora específica] porque [razón]"
- ✅ "Las limitaciones incluyen [amenaza] que mitigamos con [estrategia]"
```

---

## RESUMEN EJECUTIVO

### Propuesta Concisa

El proyecto KubGU Assistant actualmente es un **MVP funcional pero académicamente débil** (sin metrícación, arquitectura monolítica, deuda técnica residual, configuración hardcodeada).

**Propuesta:** Evolucionar a **nivel maestría en 3-4 semanas** mediante:

1. **Fase 1 (Semana 1):** Fundaciones
   - Configuración reproducible (Pydantic Settings)
   - Tipado estricto (mypy)
   - Logging estructurado (structlog)
   - Documentación inicial (ARCHITECTURE.md, DECISIONS.md)

2. **Fase 2 (Semana 2):** Modularidad
   - Refactorizar main.py en capas
   - Migrar servicios con inyección de dependencias
   - Eliminar deuda técnica (4 archivos)
   - Testing framework (70%+ cobertura)

3. **Fase 3 (Semana 3):** Evaluación
   - Dataset ground-truth (50+ queries anotadas)
   - Métricas RAG (precision@k, recall@k, MRR, NDCG)
   - Benchmarking (latencia, throughput)
   - Documentación académica final (referencias, ADRs)

### Resultado Final

✅ **Proyecto defendible en maestría:**
- Arquitectura clara y documentada
- Código tipado, testeable, limpio
- Evaluación rigurosa con métricas
- Reproducible en cualquier máquina
- CI/CD automático
- Preparado para producción

---

**Entrega:** Este documento + checklist de implementación + scripts de automatización (Makefile, GitHub Actions)

**Tiempo estimado:** 60-80 horas (3-4 semanas a tiempo completo)

**ROI académico:** Transformación de MVP a sistema defendible, con evidencia cuantitativa, arquitectura justificada y conformidad con estándares de ingeniería de software.
