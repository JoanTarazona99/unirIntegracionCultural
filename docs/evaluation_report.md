# Informe técnico de evaluación de recuperación documental

## 1. Identificación de la ejecución

- Fecha y hora final: 2026-08-28 00:35:56 UTC.
- Commit de partida: `0c75e897a0611b02b2d7fb52b4d6a3bce0ae3a02`.
- Sistema usado: Windows, Python 3.11.5.
- Semilla: 42.
- Modo: offline (`ENABLE_SEMANTIC_SEARCH=0`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`).
- Resultado completo: `data/eval/results/retrieval_eval_20260828_offline.json`.
- Resumen tabular: `data/eval/results/retrieval_eval_20260828_offline_summary.csv`.
- Trazas por consulta: `data/eval/results/retrieval_eval_20260828_offline_queries.csv`.

Este documento es un informe técnico independiente. No se modificaron archivos de tesis, DOCX, anexos ni documentación académica.

## 2. Auditoría del repositorio

El backend usa FastAPI y Pydantic. La recuperación utiliza NumPy, `rank-bm25` y, opcionalmente, `sentence-transformers`/PyTorch. El repositorio también contiene integraciones con Redis, PostgreSQL, Telegram, traducción, Ollama, TTS y STT, pero no son necesarias para la evaluación de retrieval.

No se encontró ningún archivo con nombre `README*`. La documentación inicial disponible está distribuida en `agents.md`, `INICIO_AQUI.md`, `QUICK_START.md` y numerosos informes históricos; sus afirmaciones no se usaron como sustituto de ejecuciones o conteos directos.

La base efectiva de evaluación es el corpus construido en memoria por `OfficialDocumentLibrary` en `backend/enhanced_rag.py`. La llamada a `load_from_json()` está comentada. El corpus activo tiene 18 fuentes o documentos de nivel superior y 44 secciones recuperables. Los IDs de fragmento siguen el formato estable `source::index`.

Existen además `data/rag_database.json` (4 fuentes y 14 secciones) y `backend/data/rag_database.json` (8 fuentes y 39 secciones), pero ninguna de esas copias se carga automáticamente en la ruta evaluada. La primera tampoco contiene todos los IDs anotados del benchmark. Esta divergencia impide tratar los JSON como representación canónica del corpus activo.

Los métodos implementados son:

- palabras clave: adaptador de `OfficialDocumentLibrary._keyword_search`;
- BM25: `BM25Okapi` con expansión multilingüe de términos de dominio;
- dense: `paraphrase-multilingual-MiniLM-L12-v2`;
- híbrido: BM25+dense mediante Reciprocal Rank Fusion, `rrf_k=60`;
- híbrido con reranking: RRF seguido de cross-encoder multilingüe.

Ya existían `backend/eval/benchmark.py`, `metrics.py` y `run_eval.py`, seis tests de métricas/benchmark y scripts históricos de fases 4/5. El harness anterior evaluaba un solo valor de k, guardaba solo JSON, desglosaba únicamente nDCG y permitía degradación silenciosa de híbrido a BM25. No existía workflow de GitHub Actions.

## 3. Benchmark

El benchmark original se conservó intacto en `data/eval/benchmark.jsonl`. Su SHA-256 antes y después de la implementación fue:

`b69b4916f94411621cae4336e235e8221f3d0e677b86e3c5a1fd53fca7c7215d`

Se añadió `data/eval/benchmark.manifest.json`, versión `kubgu-retrieval-v1`, para fijar hash, esquema y conteos sin duplicar ni sobrescribir las consultas.

| Dimensión | Conteo |
|---|---:|
| Consultas | 36 |
| Etiquetas binarias fragmento-consulta | 50 |
| Consultas con 1 fragmento relevante | 22 |
| Consultas con 2 fragmentos relevantes | 14 |
| Español | 23 |
| Inglés | 9 |
| Ruso | 4 |

| Categoría | Consultas |
|---|---:|
| academic | 6 |
| admin | 7 |
| health | 3 |
| housing | 4 |
| language | 4 |
| migration | 7 |
| visa | 5 |

Las 50 etiquetas apuntan a IDs presentes en los 44 fragmentos activos. La relevancia es binaria; por ello nDCG se calculó con ganancia binaria. El repositorio no documenta quién realizó la anotación, si hubo expertos, el protocolo de juicio ni acuerdo entre anotadores. El campo `notes` describe la respuesta esperada, pero no acredita procedencia.

No se generaron consultas candidatas. Por tanto no existe `candidate_queries_for_manual_review.jsonl` y ninguna consulta sintética entró en los resultados oficiales. La fixture `backend/tests/fixtures/evaluation_synthetic.jsonl` contiene tres casos artificiales usados exclusivamente por pytest.

## 4. Implementación realizada

- `backend/eval/benchmark.py`: validación de campos y tipos, IDs duplicados, etiquetas duplicadas, consultas sin etiqueta, filtros, resumen y SHA-256.
- `backend/eval/metrics.py`: `Precision@k` usa el denominador estándar k, incluso si se devuelven menos resultados.
- `backend/eval/evaluator.py`: evaluación inyectable, k múltiples, trazas, grupos, errores, exclusiones y salida JSON/CSV.
- `backend/eval/statistics.py`: bootstrap pareado reproducible e infraestructura de comparación BM25-híbrido.
- `backend/eval/retrieval_evaluation.py`: CLI offline, metadata, verificación del manifiesto, validación de IDs y detección de fallbacks.
- `data/eval/benchmark.manifest.json`: versión y huella del benchmark original.
- `backend/tests/test_evaluator_unit.py` y `test_evaluator_integration.py`: pruebas puras y con retriever simulado.
- `backend/tests/conftest.py`: bloqueo autouse de sockets y `urlopen` durante pytest.
- `backend/pytest.ini`, `backend/.coveragerc` y `backend/requirements-eval.txt`: configuración y dependencias mínimas.
- `.github/workflows/tests.yml`: workflow offline sin instalación de modelos neuronales y sin umbral de cobertura.

No se modificó la lógica de retrieval de producción. La corrección de `Precision@k` afecta únicamente las métricas de evaluación.

## 5. Comandos de reproducción

Desde la raíz del repositorio, para crear un entorno mínimo en Windows:

```powershell
py -3.11 -m venv .venv-eval
.venv-eval\Scripts\python -m pip install -r backend\requirements-eval.txt
```

Pruebas offline de evaluación y retrieval:

```powershell
cd backend
$env:ENABLE_SEMANTIC_SEARCH="0"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
$env:HF_HUB_DISABLE_TELEMETRY="1"
..\.venv-eval\Scripts\python -m pytest tests/test_eval_metrics.py tests/test_evaluator_unit.py tests/test_evaluator_integration.py tests/test_retrieval.py tests/test_retrieval_phase3.py
```

Evaluación completa y generación de JSON/CSV:

```powershell
cd backend
..\.venv-eval\Scripts\python -m eval.retrieval_evaluation --benchmark ../data/eval/benchmark.jsonl --manifest ../data/eval/benchmark.manifest.json --method keyword bm25 dense hybrid hybrid_rerank --k 1 3 5 --seed 42 --bootstrap-samples 10000 --run-id retrieval_eval_reproduced --output-dir ../data/eval/results
```

Filtro de ejemplo:

```powershell
..\.venv-eval\Scripts\python -m eval.retrieval_evaluation --method keyword bm25 --k 1 3 5 --language ru --category housing --seed 42 --skip-bootstrap --no-save
```

El comando completo intenta el bootstrap automáticamente. En el entorno auditado devuelve `not_computed` porque ningún híbrido genuino pudo ejecutarse.

Cobertura, una vez instalado `pytest-cov` mediante `requirements-eval.txt`:

```powershell
..\.venv-eval\Scripts\python -m pytest tests/test_eval_metrics.py tests/test_evaluator_unit.py tests/test_evaluator_integration.py tests/test_retrieval.py tests/test_retrieval_phase3.py --cov=eval --cov=retrieval --cov-report=term-missing --cov-report=xml
```

## 6. Tests ejecutados

Suite focalizada offline final:

| Total | Aprobados | Fallidos | Omitidos | Errores | Tiempo |
|---:|---:|---:|---:|---:|---:|
| 38 | 38 | 0 | 0 | 0 | 3.57 s |

Incluye métricas, rankings vacíos, consultas sin relevantes, orden estable ante puntuaciones empatadas del retriever simulado, validación/lectura, filtros, JSON/CSV, bootstrap con semilla fija, keyword, BM25, RRF y utilidades de reranking sin cargar modelos.

Suite backend completa exploratoria:

| Total | Aprobados | Fallidos | Omitidos | Errores | Tiempo |
|---:|---:|---:|---:|---:|---:|
| 136 | 128 | 3 | 0 | 5 | 11.44 s |

Los cinco errores proceden de `TestClient`: Starlette 0.27.0 pasa `app=` a httpx 0.28.1, cuyo constructor ya no acepta ese argumento. Dos fallos de `test_integration_phase4.py` esperan resultados híbridos para consultas RU/EN, pero dense no está disponible y BM25 devuelve vacío sobre sus fixtures. El tercer fallo, en `test_unit_rag.py`, espera una cadena de abstención distinta de la devuelta actualmente.

Durante esa primera ejecución completa, antes de añadir la barrera autouse, el último test activó un intento preexistente a DuckDuckGo y recibió una respuesta sin resultado. No se usaron credenciales. Después se añadió el bloqueo de red; la repetición focalizada mostró `External network access is disabled during pytest` antes de abrir la conexión. El fallo funcional de la cadena de abstención permanece y no se modificó por estar fuera del alcance de retrieval.

Cobertura local: **No ejecutada**. El entorno `venv311` no tiene instalados `pytest-cov` ni `coverage`; pytest rechazó las opciones `--cov`. El workflow sí instala `backend/requirements-eval.txt`, pero GitHub Actions no fue ejecutado desde esta sesión.

## 7. Resultados globales

| Método | Métrica | @1 | @3 | @5 |
|---|---|---:|---:|---:|
| Keyword | Hit | 0.277778 | 0.305556 | 0.361111 |
| Keyword | Recall | 0.180556 | 0.222222 | 0.263889 |
| Keyword | Precision | 0.277778 | 0.120370 | 0.083333 |
| Keyword | MRR | 0.277778 | 0.291667 | 0.304167 |
| Keyword | nDCG | 0.277778 | 0.232564 | 0.251116 |
| BM25 | Hit | 0.361111 | 0.444444 | 0.500000 |
| BM25 | Recall | 0.222222 | 0.361111 | 0.430556 |
| BM25 | Precision | 0.361111 | 0.203704 | 0.144444 |
| BM25 | MRR | 0.361111 | 0.393519 | 0.406019 |
| BM25 | nDCG | 0.361111 | 0.352685 | 0.384415 |

Keyword produjo cuatro rankings vacíos; BM25 no produjo rankings vacíos. Ninguno de los dos registró excepciones de retrieval.

Dense: **No ejecutado**. `sentence-transformers 5.6.0` no importa correctamente con `torch 2.0.1+cpu`; falla por ausencia de `torch.compiler`, aunque los pesos estén en caché.

Híbrido RRF y híbrido con reranking: **No ejecutados**. La etapa dense no se activó. El evaluador impidió etiquetar el fallback BM25 como resultado híbrido.

## 8. Desglose descriptivo @5

| Idioma | N | Keyword Hit | Keyword Recall | Keyword MRR | Keyword nDCG | BM25 Hit | BM25 Recall | BM25 MRR | BM25 nDCG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| en | 9 | 0.222222 | 0.166667 | 0.222222 | 0.179239 | 0.555556 | 0.500000 | 0.555556 | 0.495944 |
| es | 23 | 0.347826 | 0.282609 | 0.258696 | 0.242939 | 0.391304 | 0.304348 | 0.244203 | 0.240222 |
| ru | 4 | 0.750000 | 0.375000 | 0.750000 | 0.459860 | 1.000000 | 1.000000 | 1.000000 | 0.962586 |

| Categoría | N | Keyword Hit | Keyword Recall | Keyword MRR | Keyword nDCG | BM25 Hit | BM25 Recall | BM25 MRR | BM25 nDCG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| academic | 6 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.166667 | 0.166667 | 0.083333 | 0.105155 |
| admin | 7 | 0.571429 | 0.571429 | 0.464286 | 0.478628 | 0.571429 | 0.500000 | 0.369048 | 0.391036 |
| health | 3 | 0.333333 | 0.166667 | 0.066667 | 0.079066 | 1.000000 | 0.666667 | 0.777778 | 0.639907 |
| housing | 4 | 0.500000 | 0.250000 | 0.375000 | 0.250000 | 0.750000 | 0.750000 | 0.750000 | 0.750000 |
| language | 4 | 0.750000 | 0.500000 | 0.750000 | 0.556574 | 0.750000 | 0.625000 | 0.750000 | 0.653287 |
| migration | 7 | 0.142857 | 0.142857 | 0.142857 | 0.142857 | 0.285714 | 0.214286 | 0.171429 | 0.176743 |
| visa | 5 | 0.400000 | 0.200000 | 0.400000 | 0.245259 | 0.400000 | 0.400000 | 0.400000 | 0.340138 |

Estos desgloses son descriptivos. En particular, ruso, health, housing y language tienen entre 3 y 4 consultas y no permiten inferencias sólidas.

## 9. Bootstrap y comparación

**No ejecutado estadísticamente**: no hubo un método híbrido genuino completado para formar pares BM25-híbrido. La infraestructura implementada calcula diferencias pareadas, intervalos percentiles del 95 % y p-valores bilaterales con semilla fija. Su reproducibilidad fue verificada con datos sintéticos, pero esos resultados no se trasladaron al benchmark oficial.

Incluso con los 36 pares disponibles, el tamaño del benchmark ofrece capacidad estadística limitada, especialmente en desgloses por idioma o categoría. No se presentan intervalos, p-valores ni afirmaciones de superioridad para BM25 frente a keyword porque la comparación solicitada era BM25 frente al mejor híbrido.

## 10. Limitaciones y siguientes pasos

1. Alinear las versiones neuronales en un entorno separado y offline. El entorno ejecutado mezcla `sentence-transformers 5.6.0` con `torch 2.0.1+cpu`; no debe cambiarse solo una dependencia sin validar compatibilidad completa.
2. Establecer un corpus canónico versionado. Actualmente el corpus hardcoded y los dos JSON divergen.
3. Someter las 36 consultas y sus etiquetas a revisión humana documentada, idealmente con dos anotadores, criterios explícitos y medición de acuerdo.
4. Ampliar el benchmark con consultas revisadas, en especial ruso y categorías con 3-5 casos. Las candidatas deben permanecer separadas hasta su anotación.
5. Reejecutar dense, híbrido y reranking únicamente cuando sus etapas reales estén activas; después ejecutar el bootstrap pareado BM25-híbrido.
6. Corregir por separado la incompatibilidad Starlette/httpx y los tres fallos preexistentes de la suite completa.
7. Ejecutar el workflow de GitHub Actions para verificar instalación limpia y generar el XML de cobertura.
