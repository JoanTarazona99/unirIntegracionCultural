# Contexto del Proyecto de Software

**Repositorio analizado:** `C:\xampp\htdocs\proyectos\unirIntegracionCultural`  
**Rama verificada:** `main`  
**Fecha de corte:** 2026-09-23  
**Ventana de cambios:** 2026-08-26 a 2026-09-23  
**Actualización de implementación:** 2026-09-27, rama `feature/procedural-recommendations`  
**Fuentes de evidencia:** código, tests, historial Git, documentación versionada, resultados de evaluación y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\курсовая_090403_Тарасона.docx`.

> El archivo de tesis encontrado no tiene exactamente el nombre indicado en la solicitud (`kursovaia_090403_Tarasona-comments.docx`). El documento disponible es `C:\xampp\htdocs\proyectos\unirIntegracionCultural\курсовая_090403_Тарасона.docx`. Se consultó su contenido de texto sin modificarlo. Las prioridades de los requisitos se marcan como no especificadas porque ni el código ni la tesis definen una escala de prioridad verificable.

## 1. Visión General

KubGU Assistant es un prototipo de asistencia para estudiantes extranjeros de la Universidad Estatal de Kubán. Recibe consultas en lenguaje natural desde una interfaz web, un bot de Telegram o la API REST; recupera fragmentos de una base de conocimiento orientada a fuentes oficiales; genera una respuesta mediante Ollama cuando está habilitado o mediante plantillas; evalúa la suficiencia de la evidencia y el grounding; y se abstiene cuando la evidencia no permite sostener la respuesta.

El ensamblaje ejecutable está en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\main.py`. No existe `backend/app/main.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app` contiene configuración, modelos, servicios, middleware y routers incluidos desde el punto de entrada principal.

La configuración predeterminada en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\config\settings.py` usa retrieval `keyword`, mantiene activados el citation guard, la evaluación de evidencia y el scheduler de la base de conocimiento, pero deja desactivados por defecto el LLM, la búsqueda semántica, Redis, la persistencia de base de datos y la adquisición pública de fuentes. Por tanto, su presencia en el código representa capacidad disponible, no necesariamente un servicio activo en una ejecución concreta.

El contrato procedural reconoce 13 idiomas: español, inglés, ruso, francés, alemán, chino simplificado, árabe, vietnamita, armenio, kazajo, portugués, italiano y turco. La evidencia documental sigue concentrada en ES/EN/RU; los demás idiomas se enrutan mediante traducción verificada y producen abstención si se pierde información crítica. La lista de códigos disponible contiene 13 elementos, aunque documentación solicitada anteriormente la denominara de 14 idiomas.

### 1.1 Estructura principal verificada

| Ruta completa | Contenido y responsabilidad |
|---|---|
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend` | FastAPI, RAG, retrieval, grounding, adquisición, refresh, evaluación, persistencia, audio, traducción y tests. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app` | Configuración tipada, modelos API, dependencias, middleware, servicios y routers. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval` | Contrato de retriever, chunking y estrategias keyword, BM25, dense, híbrida RRF y reranking. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\trust` | Evaluación de suficiencia, grounding, citas, faithfulness y abstención. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\procedural` | Clasificación, generación estructurada y evaluación fail-closed de procedimientos personalizados. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\eval` | Benchmark, métricas, evaluación reproducible, bootstrap, validación y publicación transaccional. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests` | Suite pytest. No existe `C:\xampp\htdocs\proyectos\unirIntegracionCultural\tests` en la raíz. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\frontend` | Interfaces Vue 3 autocontenidas: `index.html`, `fuentes.html`, `dashboard.html`, `demo.html` y `refresh_probe.html`. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\telegram_bot` | Bot real (`bot.py`) y demostración (`bot_demo.py`). |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data` | Base RAG, registro y versiones de fuentes, colas y logs, frases, audio, SQLite y datos de evaluación. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts` | Diagnósticos y experimentos de adquisición y retrieval multilingüe. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs` | Informes de evaluación, protocolos, auditoría de tesis y persistencia transaccional. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.github` | Agentes especializados y workflow de tests offline. |

## 2. Procesos Principales

### 2.1 Adquisición de Fuentes

La adquisición reactiva se activa desde el flujo RAG cuando la evaluación previa considera insuficiente la evidencia o cuando el guard de grounding se abstiene. La política central está en `should_activate_external_search()` y `external_search_activation_reason()` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\source_acquisition_orchestrator.py`.

`KnowledgeAcquisitionAgent` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\knowledge_acquisition.py`:

1. Clasifica la carencia mediante `detect_missing_info()` en temas como visado/registro, cursos, tasas, vivienda o general.
2. Busca candidatos con `search_official_sources()`. El código contempla Google Gemini, Google Custom Search, DuckDuckGo y referencias a dominios conocidos.
3. Obtiene y limpia contenido HTML mediante `_fetch_content_from_url()`, `_fetch_wikipedia_content()` o `_fetch_html_content()`.
4. Registra los intentos sin incluir la consulta en claro salvo configuración explícita de desarrollo.
5. Entrega el candidato al flujo transaccional de `KnowledgeBaseRefresher.acquire_refresh_and_index_candidate()` para que el contenido sea validado, versionado e indexado antes de reutilizarlo.

La política endurecida de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\kb_refresh.py` exige HTTPS, host y puerto permitidos, límites de tamaño y MIME, control explícito de redirecciones, contenido mínimo, confianza mínima, tema admisible y ausencia de patrones de prompt injection. La adquisición pública está desactivada por defecto y, cuando se activa, requiere URL y host explícitamente permitidos, además de límites de peticiones por ejecución.

### 2.2 Indexación de Documentos

`OfficialDocumentLibrary` y `SemanticSearchEngine`, definidos en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\enhanced_rag.py`, controlan el corpus operativo:

1. `OfficialDocumentLibrary.__init__()` carga el corpus base, rehidrata versiones activas desde `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\source_registry.json` y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\kb_versions`, y aplana las secciones recuperables.
2. `build_chunks_from_library()` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval\chunks.py` adapta esas secciones al contrato común `Chunk`.
3. `build_retriever()` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval\factory.py` crea e indexa la estrategia seleccionada: `keyword`, `bm25`, `dense`, `hybrid` o `hybrid_rerank`.
4. `SemanticSearchEngine.build_index()` genera embeddings con `paraphrase-multilingual-MiniLM-L12-v2` cuando la búsqueda semántica está habilitada.
5. `EnhancedRAGModule.apply_refreshed_source()` sustituye la sección activa por una nueva versión, invalida el retriever y actualiza el índice semántico si está activo. `reindex_sources_incremental()` reconstruye solo cuando existe una lista no vacía de fuentes modificadas.

El informe `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\evaluation_report.md` advierte que el corpus efectivo se construye en memoria y que las copias `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\rag_database.json` y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\data\rag_database.json` no deben asumirse como representación canónica de la ruta evaluada.

### 2.3 Procesamiento de Consultas

El endpoint `POST /api/search` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\api\routes\chat.py` delega en `RAGService.search()`, ubicado en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\services\rag_service.py`. Este adaptador invoca `EnhancedRAGModule.search_and_generate()`.

Dentro de `EnhancedRAGModule`:

1. `_retrieve()` selecciona la estrategia configurada.
2. Los modos avanzados se construyen perezosamente con `build_retriever()`; si no están disponibles o fallan, se usa la búsqueda keyword de `OfficialDocumentLibrary`.
3. BM25 usa `rank-bm25`; dense usa `sentence-transformers`; hybrid fusiona rankings mediante Reciprocal Rank Fusion; `hybrid_rerank` añade un cross-encoder.
4. La expansión léxica multilingüe está implementada en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval\expansion.py` y se integra en los retrievers dense e híbrido.
5. `assess_evidence_sufficiency()` del paquete `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\trust` evalúa relevancia, cobertura de términos, entidades y slots antes de permitir generación.

`POST /api/chat` añade caché, rate limiting, memoria de conversación, persistencia opcional y métricas de transparencia. La clave de caché se deriva de consulta e idioma; el TTL utilizado por la ruta es 3600 segundos.

### 2.4 Generación de Respuestas

`EnhancedRAGModule.search_and_generate()` genera únicamente si la evidencia es suficiente:

1. Si Ollama está habilitado y disponible, `LLMModule.generate_response()` recibe consulta, fragmentos recuperados, idioma y sesión.
2. Si el LLM no está disponible, `_generate_template_response()` construye una respuesta basada en los fragmentos.
3. `enforce_grounding_improved()` comprueba grounding y faithfulness; los temas sensibles como visado, tasas, registro, documentos o policía usan modo estricto.
4. Si la evidencia o el grounding son insuficientes, la respuesta pasa a `abstained`; el flujo puede intentar una única adquisición externa autorizada y repetir la recuperación con el contenido ya indexado.
5. La salida incluye fuentes, modo de retrieval, modo de respuesta, puntuación de grounding, estado de abstención, idioma, correlación y métricas de latencia.

`RAGService` registra por defecto hashes y longitudes, no consultas, respuestas ni chunks en claro. Los payloads completos solo se habilitan con flags explícitos en entorno de desarrollo.

### 2.5 Actualización de Base de Conocimientos

`KnowledgeRefreshScheduler` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\kb_scheduler.py` se inicia y detiene mediante el lifespan de FastAPI en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\main.py`.

`KnowledgeBaseRefresher.run_refresh()` y `process_candidate_sources()` realizan el ciclo:

1. Seleccionan fuentes vencidas según categoría: crítica cada 6 horas, FAQ/admisión cada 24 horas y estable cada 168 horas por defecto; las candidatas se procesan cada 4 horas.
2. Validan y descargan contenido con transporte sin proxies de entorno (`requests.Session.trust_env = False`).
3. Limpian HTML, validan tamaño/tipo/contenido y calculan fingerprint SHA-256.
4. Si no cambió, registran `unchanged`; si cambió, escriben una versión en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\kb_versions`, actualizan el registro y aplican la versión al RAG.
5. Después de fallos consecutivos, la fuente puede quedar `stale` sin borrar la última versión válida.
6. Las escrituras JSON usan `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\atomic_json.py`; la adquisición reactiva toma snapshots y revierte archivos y estado RAG si alguna etapa transaccional falla.
7. Los eventos quedan en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\refresh_log.json`, `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\integration_log.json` y, cuando corresponde, manifiestos de adquisición pública.

El scheduler usa lock local y admite elección de líder con Redis para despliegues con varias instancias; esta última opción está desactivada por defecto.

## 3. Requisitos Funcionales

Los IDs siguientes normalizan capacidades verificadas; no son identificadores originales de la tesis. La tesis formula requisitos y funciones en prosa, no una matriz RF priorizada.

| ID | Descripción verificable | Prioridad |
|---|---|---|
| RF-001 | Permitir consultas en lenguaje natural mediante `POST /api/chat` y `POST /api/search`. | No especificada |
| RF-002 | Recuperar documentos con estrategias intercambiables keyword, BM25, dense, hybrid RRF y hybrid con reranking. | No especificada |
| RF-003 | Generar respuestas con Ollama cuando esté habilitado y usar plantillas cuando no esté disponible. | No especificada |
| RF-004 | Evaluar suficiencia de evidencia y grounding, citar fuentes y abstenerse ante evidencia insuficiente. | No especificada |
| RF-005 | Activar adquisición externa una sola vez ante evidencia insuficiente o abstención, conforme a la política central. | No especificada |
| RF-006 | Validar, versionar, deduplicar e indexar una fuente adquirida como una transacción reversible. | No especificada |
| RF-007 | Actualizar periódicamente fuentes oficiales por categoría y reindexar solo fuentes modificadas. | No especificada |
| RF-008 | Mantener trazabilidad mediante IDs de correlación, fingerprints, versiones y logs estructurados. | No especificada |
| RF-009 | Detectar y responder consultas procedimentales en 13 idiomas (`es`, `en`, `ru`, `fr`, `de`, `zh`, `ar`, `vi`, `hy`, `kk`, `pt`, `it`, `tr`); usar evidencia prioritaria ES/EN/RU y abstenerse si la traducción pierde información crítica. Ofrecer además traducción general mediante `POST /api/translate` y `GET /api/languages`. | No especificada |
| RF-010 | Crear, consultar y actualizar perfiles con país, tipo de visado, nivel de ruso y otros datos de personalización. | No especificada |
| RF-011 | Consultar frases útiles por categoría o identificador mediante `GET /api/phrases` y `GET /api/phrases/{phrase_id}`. | No especificada |
| RF-012 | Sintetizar voz, procesar audio y exponer disponibilidad mediante las rutas de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\api\routes\audio.py`. | No especificada |
| RF-013 | Mantener historial por sesión, listar sesiones y permitir borrar una conversación. | No especificada |
| RF-014 | Cachear respuestas de chat y degradar de Redis a caché LRU cuando Redis no esté habilitado o disponible. | No especificada |
| RF-015 | Persistir opcionalmente perfiles y conversaciones en SQLite/PostgreSQL con fallback a memoria. | No especificada |
| RF-016 | Ofrecer acceso por web responsiva y bot de Telegram conectado a la API REST. | No especificada |
| RF-017 | Listar fuentes, consultar su contenido y solicitar traducción desde la interfaz de fuentes. | No especificada |
| RF-018 | Exponer salud, estado y métricas del sistema mediante `/health`, `/api/status` y `/api/metrics/system`. | No especificada |
| RF-019 | Ejecutar evaluaciones de retrieval y consultar el último resultado mediante `/api/eval/run` y `/api/eval/results`. | No especificada |
| RF-020 | Aplicar rate limiting por IP, whitelist CORS y política HTTPS/allowlist a la adquisición de fuentes. | No especificada |
| RF-021 | Generar recomendaciones procedimentales personalizadas y trazables, solicitar aclaraciones ante datos de perfil insuficientes y abstenerse si faltan documentos, plazos, organismo o evidencia oficial. | No especificada |

Evidencia principal: routers en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\api\routes`, modelos en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\api\models.py`, tests en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests` y descripción funcional de interfaces, voz, retrieval y base oficial en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\курсовая_090403_Тарасона.docx`.

## 4. Casos de Uso

### CU-001: Consultar al asistente con respuesta fundamentada

- **Actor**: estudiante extranjero o cliente API.
- **Precondiciones**: backend iniciado; consulta válida; cliente dentro del límite de peticiones; corpus RAG inicializado.
- **Flujo principal**: el actor envía `POST /api/chat`; la ruta busca en caché; `RAGService.search()` ejecuta retrieval y evaluación de evidencia; el módulo genera por LLM o plantilla; el guard valida grounding; se guarda el intercambio en memoria, se agenda persistencia opcional y se cachea la respuesta.
- **Postcondiciones**: el actor recibe respuesta, contexto, idioma, sesión, correlación y métricas de IA; si no hay evidencia suficiente recibe abstención en vez de una respuesta no sustentada.

### CU-002: Ampliar conocimiento ante evidencia insuficiente

- **Actor**: sistema RAG.
- **Precondiciones**: evaluación de evidencia insuficiente o grounding abstained; búsqueda externa habilitada; candidato compatible con las políticas de adquisición.
- **Flujo principal**: el sistema identifica términos faltantes; busca una fuente; valida URL, dominio, confianza, tema, transporte y contenido; calcula fingerprint; versiona; actualiza el registro; aplica la fuente al RAG; reindexa; repite la consulta una sola vez.
- **Postcondiciones**: la nueva evidencia queda recuperable y trazada, o toda la transacción se revierte y se conserva la abstención.

### CU-003: Buscar documentos sin flujo conversacional

- **Actor**: usuario web, bot o consumidor API.
- **Precondiciones**: backend y corpus disponibles.
- **Flujo principal**: el actor envía `POST /api/search`; `RAGService` llama a `search_and_generate()` con el idioma y contexto; el retriever devuelve los fragmentos mejor puntuados y sus metadatos.
- **Postcondiciones**: el actor obtiene respuesta, fuentes y modo de búsqueda sin modificar el historial de chat de la ruta conversacional.

### CU-004: Gestionar perfil personalizado

- **Actor**: estudiante extranjero.
- **Precondiciones**: identificador de usuario y datos válidos según los modelos Pydantic.
- **Flujo principal**: el actor crea o actualiza el perfil con `POST /api/users/profile` o `PUT /api/users/profile/{user_id}`; el servicio de perfiles conserva el estado; la persistencia opcional se ejecuta en segundo plano; el actor puede consultar perfil y recomendaciones.
- **Postcondiciones**: perfil y consejos quedan disponibles mediante la API, con fallback en memoria si la base de datos no está activa.

### CU-005: Consultar y escuchar una frase útil

- **Actor**: estudiante desde la web o Telegram.
- **Precondiciones**: frases cargadas desde `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\phrases`; TTS del navegador o backend disponible para audio.
- **Flujo principal**: el actor solicita frases por categoría o límite; selecciona una frase; la web intenta `window.speechSynthesis`; si no dispone de voz adecuada, envía `POST /api/tts` y reproduce el audio devuelto.
- **Postcondiciones**: frase mostrada y, si algún proveedor está disponible, reproducida en audio.

### CU-006: Usar el asistente desde Telegram

- **Actor**: usuario de Telegram.
- **Precondiciones**: token configurado, bot en ejecución y `BACKEND_URL` accesible.
- **Flujo principal**: `/setup` configura país, visado y nivel de ruso; `/ask` o un mensaje libre llama a `/api/chat`; `/search`, `/phrases`, `/voice`, `/status`, `/lang` y `/profile` usan las funciones correspondientes del bot.
- **Postcondiciones**: el usuario recibe respuesta y fuentes; `UserSession` conserva perfil, identificador de sesión e historial de los últimos diez mensajes en memoria del proceso del bot.

### CU-007: Actualizar automáticamente la base de conocimiento

- **Actor**: `KnowledgeRefreshScheduler`.
- **Precondiciones**: scheduler habilitado; instancia líder cuando se usa lock distribuido; registro de fuentes legible.
- **Flujo principal**: el scheduler determina la categoría vencida; `run_refresh()` descarga y valida cada fuente; compara fingerprints; persiste una versión nueva cuando hay cambios; actualiza RAG y logs; procesa por separado candidatas de revisión manual.
- **Postcondiciones**: fuentes sin cambios quedan registradas como comprobadas; fuentes modificadas tienen nueva versión activa; fuentes con fallos repetidos pueden quedar stale sin perder la versión previa.

### CU-008: Ejecutar una evaluación reproducible de retrieval

- **Actor**: investigador o mantenedor.
- **Precondiciones**: benchmark y manifiesto válidos; dependencias del modo solicitado disponibles; entorno offline configurado cuando corresponda.
- **Flujo principal**: el actor ejecuta la CLI de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\eval\retrieval_evaluation.py` o `POST /api/eval/run`; se validan hash y qrels; se ejecutan métodos; se calculan métricas y bootstrap aplicable; se publican JSON/CSV transaccionalmente.
- **Postcondiciones**: resultados reproducibles y trazables quedan en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results`, o la publicación se aborta sin sobrescribir resultados anteriores.

### CU-009: Obtener una recomendación procedimental personalizada

- **Actor**: estudiante extranjero o consumidor API.
- **Precondiciones**: backend iniciado; consulta válida; perfil persistido o inline cuando el trámite requiere país, visa, nivel académico o vivienda.
- **Flujo principal**: el actor envía `POST /api/procedural`; el sistema recupera evidencia sin generación ni adquisición externa; clasifica el trámite; solicita aclaraciones si faltan datos; extrae pasos, documentos, plazos y organismo; asocia URL, título, chunk y versión; evalúa completitud y evidencia.
- **Postcondiciones**: devuelve `complete` con pasos trazables, `needs_clarification` sin acciones o `abstained` sin pasos cuando la evidencia no supera la política fail-closed.

## 5. Componentes del Sistema

### 5.1 Módulos Principales

- **API y composición**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\main.py`; crea FastAPI, middleware, dependencias globales, scheduler y routers.
- **RAG**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\enhanced_rag.py`; contiene `SemanticSearchEngine`, `OfficialDocumentLibrary` y `EnhancedRAGModule`.
- **Retrieval**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval`; implementa `BaseRetriever`, `KeywordBaselineRetriever`, `BM25Retriever`, `DenseRetriever`, `HybridRetriever`, `CrossEncoderReranker`, expansión y RRF.
- **Grounding y confianza**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\trust`; evalúa evidencia, citas, faithfulness, niveles de grounding y abstención.
- **Adquisición reactiva**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\knowledge_acquisition.py` y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\source_acquisition_orchestrator.py`.
- **Refresh y ciclo de vida de fuentes**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\kb_refresh.py` y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\kb_scheduler.py`.
- **Servicios de aplicación**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\services`; adaptadores de RAG, perfiles, frases, conversación, audio, traducción, caché y base de datos.
- **Personalización**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\personalization.py`.
- **Voz**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\audio_module.py` y router de audio.
- **Evaluación**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\eval`; métricas Hit, Recall, Precision, MRR y nDCG, desgloses, bootstrap y publicación.
- **Recomendaciones procedimentales**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\procedural` y `backend\app\services\procedural_service.py`; clasificación, extracción, trazabilidad y evaluación de suficiencia.

### 5.2 Servicios Externos

- **Ollama**: LLM local opcional en `http://localhost:11434`; modelo predeterminado `qwen2.5:7b-instruct-q4_K_M`.
- **Google Gemini / Google Custom Search**: proveedores opcionales contemplados por `KnowledgeAcquisitionAgent`; requieren credenciales de entorno.
- **DuckDuckGo**: búsqueda de respuesta instantánea como fallback del agente de adquisición.
- **Sitios oficiales**: KubSU, МВД, МФЦ y Госуслуги, limitados por allowlist en el flujo endurecido.
- **Telegram Bot API**: canal de mensajería implementado con `python-telegram-bot` y `aiohttp`.
- **gTTS y Google Speech Recognition**: TTS y STT opcionales del backend.
- **Servicios de traducción**: `google-trans-new` y `deep-translator` aparecen en las dependencias y módulos de traducción.
- **Hugging Face / modelos locales**: `sentence-transformers` y cross-encoders para dense y reranking; las evaluaciones reproducibles usan snapshots locales y modo offline.

### 5.3 Bases de Datos

- **JSON versionado**: registro, candidatas, versiones y logs bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data`.
- **SQLite**: URL predeterminada `sqlite:///./data/assistant.db`; archivo presente en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\assistant.db`; persistencia desactivada por defecto.
- **PostgreSQL**: backend opcional mediante SQLAlchemy, `asyncpg` y `psycopg2-binary`.
- **Redis**: caché distribuida y lock de líder opcionales; fallback a LRU en proceso.
- **Memoria de proceso**: almacenamiento primario disponible para conversaciones y perfiles cuando no se activa persistencia externa.

### 5.4 Interfaces

- **Web principal**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\frontend\index.html`; chat, perfil, selector de idioma, frases y TTS con fallback.
- **Fuentes**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\frontend\fuentes.html`; consulta `/api/sources` y traducción por fuente.
- **Dashboard**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\frontend\dashboard.html`; métricas del sistema y ejecución/consulta de evaluaciones.
- **Diagnóstico de refresh**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\frontend\refresh_probe.html`.
- **Telegram**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\telegram_bot\bot.py`.
- **REST/OpenAPI**: FastAPI expone documentación automática en `/docs` y registra once routers, incluido `POST /api/procedural`.

## 6. Estructura del Código

La organización combina un núcleo histórico de módulos Python en la raíz de `backend` con una capa de aplicación más reciente bajo `backend/app`. `backend/main.py` actúa como composition root: crea instancias y las expone a los routers mediante `backend/app/api/dependencies.py`. Los routers contienen adaptación HTTP; los servicios encapsulan acceso a RAG, caché, conversación, perfiles, traducción, audio y persistencia.

Patrones observados:

- **Strategy + Factory**: las implementaciones de `BaseRetriever` se seleccionan mediante `build_retriever()` sin cambiar el flujo RAG.
- **Adapter/Service layer**: `RAGService` y los demás servicios presentan interfaces estables sobre módulos heredados.
- **Dependency Injection**: los routers FastAPI obtienen servicios mediante `Depends` y funciones de `backend/app/api/dependencies.py`.
- **Lifecycle management**: el lifespan de FastAPI inicia calentamiento de modelos y scheduler, y detiene el scheduler al cerrar.
- **Fallback/degradación controlada**: keyword sustituye retrieval avanzado; plantilla sustituye LLM; LRU sustituye Redis; memoria sustituye base de datos; gTTS sustituye Web Speech API en la web.
- **Transacción compensatoria**: adquisición e indexación capturan snapshots de archivos y RAG y restauran el estado ante fallos.
- **Escritura atómica**: JSON y resultados de evaluación se escriben en temporal, sincronizan y reemplazan.
- **Estado versionado**: cada actualización aceptada conserva fingerprint, `version_id`, versión activa y versión archivada.

Dependencias principales verificadas en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\requirements.txt`: FastAPI, Uvicorn, Pydantic/Pydantic Settings, structlog, NumPy, pandas, SQLAlchemy, SQLite/asyncpg/PostgreSQL, Redis, python-telegram-bot, aiohttp, requests, rank-bm25, sentence-transformers, PyTorch CPU, gTTS, SpeechRecognition, httpx, python-multipart y librerías de traducción. Las dependencias específicas de evaluación neuronal están separadas en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\requirements-neural-eval.txt` y su lock.

## 7. Avance de Cambios (Últimas 4 Semanas)

El comando `git log --oneline --since="4 weeks ago"` devuelve 28 commits entre el 28 de agosto y el 2 de septiembre de 2026. No hay commits posteriores dentro de la ventana hasta la fecha de corte.

### Commit: e4438ad - docs(analysis): dense vs keyword comparison for SPbU queries

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\dense-vs-keyword-comparison.md`.
- **Funcionalidad**: documenta un diagnóstico de tres consultas SPbU y atribuye el error ruso observado al chunk monolítico, truncamiento a 128 tokens y falta de control explícito de entidad; no es un benchmark oficial.

### Commit: 2fbdff0 - feat(dense): add lexical expansion and RRF fusion

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval\dense.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests\test_dense_multilingual.py`.
- **Funcionalidad**: añade expansión léxica al dense y fusiona ranking original/expandido mediante RRF; incorpora pruebas multilingües focalizadas.

### Commit: 6804ad1 - feat(multilingual): add lexical expansion and RRF fusion

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\enhanced_rag.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\kb_refresh.py`; módulos `base.py`, `chunks.py`, `expansion.py`, `factory.py`, `hybrid.py`, `rerank.py` y `sparse.py` de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\retrieval`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests\test_multilingual_expansion.py`.
- **Funcionalidad**: integra expansión multilingüe, aliases estables de fuente y trazas/fusión RRF en la tubería general de retrieval.

### Commit: d38a5a9 - style(agents): formatting updates to methodology-lead

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.github\agents\methodology-lead.agent.md`.
- **Funcionalidad**: cambio de formato del agente metodológico; sin cambio de runtime.

### Commit: 5930acb - solutions(multilingual): cross-lingual retrieval improvements

- **Archivos**: `README.md`, `experiments.log`, `preflight.log`, `results.json` y `run_experiments.py` bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-solutions`.
- **Funcionalidad**: registra y ejecuta experimentos de mejora de retrieval cross-lingual, con preflight y resultados reproducibles.

### Commit: 0dda598 - diagnosis(multilingual): retrieval cross-lingual analysis

- **Archivos**: `README.md`, `diagnosis.log`, `end-to-end-keyword.log`, `preflight.log`, `results.json` y `run_diagnosis.py` bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-diagnosis`.
- **Funcionalidad**: incorpora diagnóstico reproducible del comportamiento cross-lingual y evidencia de la ruta keyword end-to-end.

### Commit: 64ca908 - chore(agents): enable feature/real-source-testing branch for methodology-lead

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.github\agents\methodology-lead.agent.md`.
- **Funcionalidad**: ajusta permisos/configuración del agente para la rama de pruebas con fuentes reales; sin cambio de runtime.

### Commit: 57b7e65 - chore(agents): add GitHub Copilot agent configurations

- **Archivos**: `benchmark-generator.agent.md`, `eval-runner.agent.md`, `methodology-lead.agent.md` y `review-validator.agent.md` bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.github\agents`.
- **Funcionalidad**: añade roles especializados para generación, ejecución, metodología y validación humana de benchmarks.

### Commit: 4c3ea3f - Merge feature/neural-retrieval-evaluation into main

- **Archivos**: commit de merge sin lista propia en la salida de `git log --name-only`.
- **Funcionalidad**: integra en `main` la rama de evaluación neuronal cuyos commits individuales se detallan a continuación.

### Commit: 824ea9b - chore(repo): stop tracking scheduler runtime lock

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\kb_scheduler.leader.lock`.
- **Funcionalidad**: deja de versionar un lock efímero del scheduler; no cambia lógica de ejecución.

### Commit: 3283533 - test(acquisition): enforce offline transport and traceability

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests\conftest.py`, `test_acquisition_security_traceability.py`, `test_kb_refresh_scheduler.py`, `test_source_acquisition_orchestrator.py` y `test_unit_rag.py` bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests`.
- **Funcionalidad**: endurece pruebas de transporte offline, política de adquisición, correlación y trazabilidad end-to-end.

### Commit: a109aee - feat(acquisition): make source ingestion transactional and policy gated

- **Archivos**: modelos, chat, settings y RAG service bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\atomic_json.py`; `enhanced_rag.py`; `kb_refresh.py`; `knowledge_acquisition.py`; `knowledge_integrator.py`; `source_acquisition_orchestrator.py`.
- **Funcionalidad**: convierte la adquisición reactiva en una transacción validada por política, con escritura atómica, rollback, trazabilidad y reindexación antes del reintento.

### Commit: 8fd8a0d - feat(trust): fail closed on insufficient retrieval evidence

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\config\settings.py`; `enhanced_rag.py`; tests de grounding y RAG; `citation.py`, `hallucination.py` e `__init__.py` bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\trust`.
- **Funcionalidad**: añade evaluación previa de suficiencia y política fail-closed para abstenerse cuando retrieval no sostiene la respuesta.

### Commit: 2fd4751 - fix(logging): redact raw RAG payloads by default

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\services\rag_service.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\enhanced_rag.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests\test_unit_rag.py`.
- **Funcionalidad**: sustituye payloads RAG en claro por hashes, longitudes y metadatos sanitizados salvo opt-in de desarrollo.

### Commit: 0e23e83 - chore(repo): ignore artifacts and scheduler runtime lock

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.gitignore`.
- **Funcionalidad**: configura exclusiones de artefactos y locks de runtime; sin cambio funcional del producto.

### Commit: 73ee328 - Ignore agents and staging directory

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.gitignore`.
- **Funcionalidad**: excluye configuraciones/agentes y staging temporal según la política de ese momento; sin cambio de runtime.

### Commit: 6d0ada9 - Draft Russian thesis update for retrieval evaluation

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\thesis_neural_evaluation_update_ru.md`.
- **Funcionalidad**: prepara texto ruso para actualizar la tesis con resultados y limitaciones de evaluación reproducibles.

### Commit: 16c8677 - Audit thesis evaluation claims

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\thesis_evaluation_claims_audit.md`.
- **Funcionalidad**: audita 37 afirmaciones de la tesis y clasifica cuáles están soportadas, desactualizadas, exageradas o no sustentadas.

### Commit: 32efa83 - Document exploratory 114-query neural evaluation

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\neural_extended_114_exploratory_report.md`.
- **Funcionalidad**: documenta metodología, resultados, integridad y límites de la evaluación neuronal exploratoria de 114 consultas.

### Commit: 89d1eac - Add exploratory neural evaluation results for 114 queries

- **Archivos**: seis artefactos JSON/CSV bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2`.
- **Funcionalidad**: publica resultados globales, trazas, desgloses por idioma/categoría y bootstrap de cinco métodos sobre 114 consultas sintéticas revisadas con IA.

### Commit: c1841d8 - Fix transactional result persistence

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\eval\transactional_result_persistence.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests\test_transactional_result_persistence.py`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\transactional_result_persistence.md`.
- **Funcionalidad**: corrige publicación atómica de resultados, validación previa y conservación de resultados históricos.

### Commit: d5a03b3 - Add B3 adapter for reviewed exploratory benchmark

- **Archivos**: adaptador y test en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend`; benchmark, manifiesto y diagnóstico B3 en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval`; protocolo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_reviewed_b3_adapter.md`.
- **Funcionalidad**: transforma de forma validada el benchmark revisado al formato consumido por la evaluación B3 y conserva trazabilidad uno a uno.

### Commit: 5bdf087 - Add reviewed exploratory benchmark export

- **Archivos**: test de exportación; plantilla, JSONL revisado, manifiesto y diagnóstico bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_reviewed_export_protocol.md`.
- **Funcionalidad**: exporta registros `accepted`/`revised`, excluye pendientes y declara de forma explícita que el conjunto no es apto para métricas oficiales.

### Commit: b559c15 - Stabilize offline neural probe and fallback telemetry

- **Archivos**: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\eval\offline_neural_probe.py`; `retrieval_evaluation.py`; tests neuronales/offline; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\offline_neural_probe.md`.
- **Funcionalidad**: valida modelos locales antes de evaluar, bloquea degradaciones silenciosas y registra uso real/fallback de dense y reranker.

### Commit: 9059525 - Add human review validation workflow

- **Archivos**: validador y test bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend`; plantilla, manifiesto y diagnóstico de revisión bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_review_protocol.md`.
- **Funcionalidad**: incorpora un flujo auditable de revisión humana y validación de estados, qrels y exclusiones.

### Commit: 8af10b2 - Add synthetic benchmark generation workflow

- **Archivos**: generador, configuración y test bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend`; benchmark extendido, manifiesto y diagnóstico bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_generation.md`.
- **Funcionalidad**: añade generación determinista de candidatos sintéticos multilingües sin modificar el benchmark oficial.

### Commit: 3971f6b - Add reproducible neural retrieval evaluation

- **Archivos**: evaluador, CLI, factory y reranker bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend`; requirements neuronales; tests; seis resultados bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_20260829_v1`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\neural_evaluation_report.md`.
- **Funcionalidad**: añade evaluación offline reproducible de keyword, BM25, dense, hybrid e hybrid_rerank, con snapshots de modelos, telemetría, desgloses y bootstrap.

### Commit: c5da076 - Add offline RAG retrieval evaluation and tests

- **Archivos**: workflow `C:\xampp\htdocs\proyectos\unirIntegracionCultural\.github\workflows\tests.yml`; configuración, benchmark, métricas, evaluador, estadísticas y tests bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend`; manifiesto y tres resultados bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval`; `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\evaluation_report.md`.
- **Funcionalidad**: establece el harness offline, métricas en varios cortes, trazas por consulta, filtros, bootstrap reproducible, salidas JSON/CSV y CI sin red.

## 8. Informes de Auditoría

La fecha procede del commit que añadió el archivo o de la fecha declarada dentro del propio informe. Se listan los informes y resultados principales generados dentro de la ventana; scripts y fixtures no se consideran informes. Los artefactos bajo `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\public_acquisition`, `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\real-source-tests` y `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\source_lifecycle` están ignorados por Git; sus fechas y ramas proceden de sus propios manifiestos o README y no prueban integración en `main`.

| Ruta completa | Fecha | Tipo | Descripción |
|---|---|---|---|
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\evaluation_report.md` | 2026-08-28 | Evaluación offline | Auditoría del corpus y evaluación inicial de 36 consultas; documenta incompatibilidad neuronal y límites del benchmark. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\retrieval_eval_20260828_offline.json` | 2026-08-28 | Resultado de evaluación | Resultado completo machine-readable de la evaluación offline inicial. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\retrieval_eval_20260828_offline_summary.csv` | 2026-08-28 | Resumen de métricas | Métricas globales por método y corte. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\retrieval_eval_20260828_offline_queries.csv` | 2026-08-28 | Trazas de evaluación | Resultado por consulta para auditoría de rankings. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\neural_evaluation_report.md` | 2026-08-29 | Evaluación neuronal | Informe reproducible de cinco métodos en el benchmark primario B3. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_20260829_v1\retrieval_eval_neural_20260829_v1.json` | 2026-08-29 | Resultado neuronal | Resultado completo de la evaluación B3 con métodos neuronales activos. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_20260829_v1\retrieval_eval_neural_20260829_v1_summary.csv` | 2026-08-29 | Resumen de métricas | Resumen global del resultado B3. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_20260829_v1\retrieval_eval_neural_20260829_v1_bootstrap.json` | 2026-08-29 | Inferencia estadística | Bootstrap pareado BM25 frente a hybrid_rerank. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_generation.md` | 2026-08-29 | Protocolo de benchmark | Generación determinista de candidatos sintéticos y separación del benchmark oficial. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\benchmark_extended_diagnostics.json` | 2026-08-29 | Diagnóstico de dataset | Conteos y validaciones del benchmark sintético extendido. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_review_protocol.md` | 2026-08-29 | Protocolo de auditoría humana | Define estados y validaciones para revisión independiente del benchmark. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\benchmark_extended_review_diagnostics.json` | 2026-08-29 | Diagnóstico de revisión | Registra preparación y validación del lote para revisión humana. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\offline_neural_probe.md` | 2026-08-30 | Validación de entorno | Protocolo de preflight offline para dense y cross-encoders y detección de fallback. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_reviewed_export_protocol.md` | 2026-08-30 | Protocolo de exportación | Define exportación trazable de registros revisados y exclusión de pendientes. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\benchmark_extended_reviewed_114_diagnostics.json` | 2026-08-30 | Diagnóstico de benchmark | Documenta 114 registros exportados y el estado no oficial del conjunto. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\benchmark_reviewed_b3_adapter.md` | 2026-08-30 | Protocolo de adaptación | Describe la conversión del export revisado al esquema B3. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\benchmark_extended_reviewed_114_b3_diagnostics.json` | 2026-08-30 | Diagnóstico de adaptación | Verifica correspondencia, qrels y exclusiones del adaptador B3. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\transactional_result_persistence.md` | 2026-08-30 | Auditoría de persistencia | Especifica publicación atómica, validación y rollback de resultados. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\neural_extended_114_exploratory_report.md` | 2026-08-30 | Evaluación exploratoria | Informe de cinco métodos sobre 114 consultas sintéticas revisadas con IA; no elegible como benchmark oficial. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2\retrieval_eval_neural_extended_114_20260830_v2.json` | 2026-08-30 | Resultado exploratorio | Resultado completo de 570 trazas, cinco métodos y 114 consultas. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2\retrieval_eval_neural_extended_114_20260830_v2_summary.csv` | 2026-08-30 | Resumen de métricas | Métricas globales del conjunto exploratorio. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2\retrieval_eval_neural_extended_114_20260830_v2_by_language.csv` | 2026-08-30 | Evaluación multilingüe | Desglose descriptivo ES/EN/RU. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2\retrieval_eval_neural_extended_114_20260830_v2_by_category.csv` | 2026-08-30 | Evaluación temática | Desglose descriptivo por categoría. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\data\eval\results\neural_extended_114_20260830_v2\retrieval_eval_neural_extended_114_20260830_v2_bootstrap.json` | 2026-08-30 | Inferencia estadística exploratoria | Bootstrap pareado BM25 frente a hybrid_rerank; no compara contra dense. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\thesis_evaluation_claims_audit.md` | 2026-08-30 | Auditoría metodológica | Audita 37 afirmaciones de la tesis y propone correcciones sustentadas. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\thesis_neural_evaluation_update_ru.md` | 2026-08-30 | Borrador académico | Propone actualización rusa de metodología, resultados y limitaciones para la tesis. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-diagnosis\README.md` | 2026-09-01 | Diagnóstico cross-lingual | Resume el análisis reproducible de fallos multilingües. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-diagnosis\results.json` | 2026-09-01 | Resultado diagnóstico | Datos estructurados del diagnóstico cross-lingual. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-solutions\README.md` | 2026-09-01 | Informe experimental | Describe soluciones candidatas para mejorar recuperación multilingüe. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\multilingual-solutions\results.json` | 2026-09-01 | Resultado experimental | Resultados estructurados de los experimentos de solución. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\dense-vs-keyword-comparison.md` | 2026-09-02 | Diagnóstico de retrieval | Compara keyword/dense para SPbU y documenta truncamiento y confusión de entidad. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\public_acquisition\PUB-AQ-20260831T201721Z\run_manifest.json` | 2026-08-31 | Prueba de adquisición pública | Ejecución aislada sobre Sechenov: una petición, rechazo por certificado TLS no confiable y estado del proyecto sin cambios. Artefacto local no versionado. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\public_acquisition\PUB-AQ-20260831T203632Z\run_manifest.json` | 2026-08-31 | Prueba de adquisición pública | Ejecución aislada sobre SPbU: adquisición, versionado, indexación y rehidratación exitosos; el grounding posterior de esa ejecución no fue suficiente. Artefacto local no versionado. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\public_acquisition\PUB-AQ-20260831T203632Z-offline-revalidation\run_manifest.json` | 2026-08-31 | Revalidación offline | Reutiliza el sandbox histórico sin red; las aserciones confirman fuente rehidratada, SPbU en rango 1, evidencia/grounding suficientes, cita exacta y ninguna nueva escritura. Artefacto local no versionado. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\source_lifecycle\FNT-E2E-001\run_manifest.json` | 2026-08-31 | Auditoría E2E del ciclo de fuente | Prueba simulada y aislada de detección, adquisición, versionado, indexación, retrieval e idempotencia; resultado global `fallo funcional` por detección inicial y rehidratación tras reinicio. Artefacto local no versionado. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\real-source-tests\spbu-20260901\README.md` | 2026-09-01 | Prueba controlada de fuente real | Adquisición SPbU exitosa, pero la consulta natural española no seleccionó la fuente; resultado parcial y sin commit. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\real-source-tests\unam-20260901\README.md` | 2026-09-01 | Prueba controlada de fuente real | UNAM/UBA en español: transacciones válidas, pero solo una de seis consultas fue sustantivamente pertinente; identifica falsos positivos de grounding. Artefacto local no versionado. |
| `C:\xampp\htdocs\proyectos\unirIntegracionCultural\artifacts\real-source-tests\uba-20260901\README.md` | 2026-09-01 | Control alternativo de fuente real | Resumen del control UBA; remite al informe UNAM para interpretación comparada. Artefacto local no versionado. |

## 9. Estado Actual

El sistema dispone de API FastAPI modular, web Vue 3, bot Telegram, retrieval con cinco estrategias, guard de evidencia/grounding, adquisición transaccional, refresh versionado, evaluación reproducible y persistencia opcional. La ruta segura predeterminada es conservadora: keyword, sin LLM, sin semantic search, sin adquisición pública y con abstención habilitada.

La evidencia de evaluación más sólida publicada en la ventana es B3, con 36 consultas y cinco métodos. La auditoría de tesis indica que dense obtuvo las mejores métricas globales en B3 y que el bootstrap solo sustenta una mejora de `hybrid_rerank` frente a BM25 en MRR@5 y nDCG@5; no demuestra superioridad frente a dense. El conjunto de 114 consultas es exploratorio, sintético y revisado con asistencia de IA (`official_evaluation_eligible=false`, `human_review_completed=false`).

El diagnóstico del 2 de septiembre muestra una limitación actual: fuentes largas se convierten en chunks monolíticos y el modelo dense puede truncarlos a 128 tokens. La consulta rusa de SPbU quedó por debajo de КубГУ; la recomendación verificada es mejorar chunking y validar aliases/control léxico con un benchmark focal.

Las pruebas locales de fuentes reales refuerzan que una adquisición técnicamente correcta no garantiza relevancia ni grounding. Los controles del 31 de agosto y 1 de septiembre incluyen resultados fallidos o parciales, y están ignorados por Git; deben tratarse como evidencia diagnóstica local, no como validación de producción ni como avance integrado en `main`.

El árbol de trabajo no estaba limpio al momento del análisis: `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\app\config\settings.py` tenía modificaciones locales y había cuatro tests no versionados (`test_configuration.py`, `test_edge_cases.py`, `test_multilingual_universities.py` y `test_performance.py` en `C:\xampp\htdocs\proyectos\unirIntegracionCultural\backend\tests`). Este documento no modifica ni interpreta esos cambios como parte del historial de `main`.

No se afirma que todos los tests actuales pasen. El informe del 28 de agosto registró 38/38 en su suite focalizada, pero también 128 aprobados, 3 fallidos y 5 errores en una ejecución exploratoria completa, con incompatibilidad Starlette/httpx y fallos preexistentes. Las cifras promocionales antiguas de otros documentos no sustituyen una ejecución actual.

En la rama `feature/procedural-recommendations` se implementó el primer módulo de recomendaciones procedimentales: contratos Pydantic, detección y clasificación en 13 idiomas, routing de evidencia hacia ES/EN/RU, traducción verificada fail-closed, retrieval-only, extracción estructurada, evaluación, endpoint API, cuatro agentes especializados y tres ejemplos JSON escritos atómicamente. Los artefactos SPbU/UNAM/UBA se conservan como pruebas negativas de abstención, no como procedimientos completos.

## 10. Próximos Pasos

Los siguientes pasos están respaldados por los informes y diagnósticos versionados:

1. Dividir páginas adquiridas extensas en chunks semánticos que respeten la ventana del modelo y conserven título, fuente y aliases.
2. Incorporar aliases institucionales multilingües y validar su efecto con qrels focalizados, especialmente para entidades como SPbU frente a КубГУ.
3. Establecer un corpus canónico versionado y eliminar la ambigüedad entre corpus en memoria y archivos `rag_database.json` heredados.
4. Construir un benchmark con consultas reales, revisión humana independiente, protocolo documentado y acuerdo entre anotadores; mantener separado el conjunto sintético de 114 consultas.
5. Ejecutar una comparación estadística planificada entre dense e hybrid_rerank antes de afirmar superioridad general del enfoque híbrido.
6. Actualizar la tesis con las correcciones de `C:\xampp\htdocs\proyectos\unirIntegracionCultural\docs\thesis_evaluation_claims_audit.md`, separando resultados primarios y exploratorios y retirando afirmaciones de impacto no medido.
7. Resolver y volver a ejecutar la suite completa en un entorno de dependencias compatible, incluyendo el conflicto Starlette/httpx documentado y cobertura reproducible.
8. Validar en entorno de despliegue los componentes desactivados por defecto (Ollama, semantic search, Redis, base de datos y adquisición pública) antes de declarar disponibilidad operacional de esas capacidades.