# Informe técnico de evaluación neuronal de retrieval

## Identificación

- Ejecución: `retrieval_eval_neural_20260829_v1`.
- Fecha: 2026-08-29 03:53:44 UTC.
- Rama: `feature/neural-retrieval-evaluation`.
- Commit: `c5da076212af6859d15b775185776ec69f308eea`.
- Entorno: `C:\venvs\unirIntegracionCultural\venv-rag-eval-probe`.
- Python: 3.11.5.
- Plataforma de cómputo: CPU.

Este documento registra una ejecución técnica independiente. No modifica ni contiene texto destinado a la tesis, anexos o archivos DOCX.

## Configuración evaluada

Se evaluaron, sin cambiar algoritmos ni hiperparámetros:

- keyword: `OfficialDocumentLibrary._keyword_search`;
- BM25: `BM25Okapi` con expansión de consulta habilitada;
- dense: `paraphrase-multilingual-MiniLM-L12-v2`;
- hybrid: BM25+dense con Reciprocal Rank Fusion, `rrf_k=60` y multiplicador de candidatos 4;
- hybrid rerank: hybrid seguido de cross-encoder con selección por idioma.

Los cinco métodos usaron `k=1,3,5`, semilla 42 y el mismo corpus y benchmark. El bootstrap pareado utilizó 10 000 muestras y semilla 42.

## Entorno y modelos

| Dependencia | Versión |
|---|---:|
| torch | 2.4.1+cpu |
| torchvision | 0.19.1+cpu |
| sentence-transformers | 5.6.0 |
| transformers | 4.57.6 |
| huggingface-hub | 0.36.2 |
| rank-bm25 | 0.2.2 |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| scikit-learn | 1.9.0 |
| tokenizers | 0.22.2 |
| safetensors | 0.8.0 |

Snapshots usados:

| Rol | Modelo | Commit de snapshot |
|---|---|---|
| Dense | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` |
| Reranker ES/RU | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | `1427fd652930e4ba29e8149678df786c240d8825` |
| Reranker EN | `cross-encoder/ms-marco-MiniLM-L-12-v2` | `7b0235231ca2674cb8ca8f022859a6eba2b1c968` |

El preflight produjo embeddings con forma `(2, 384)` y predicciones con formas `(1,)` para cada cross-encoder. Todos los valores fueron finitos y terminó con `OFFLINE_NEURAL_PROBE_OK`.

## Evidencia offline

Antes de iniciar Python se establecieron:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
ENABLE_SEMANTIC_SEARCH=1
```

Se eliminaron proxies y variables de credenciales del proceso. Durante preflight y evaluación se bloquearon localmente `socket.socket.connect`, `socket.create_connection` y `urllib.request.urlopen`. El contador final fue:

```text
network_attempts=0
```

No se ejecutó Ollama. El mensaje de importación indicó que su paquete no estaba disponible en el entorno aislado.

## Benchmark y corpus

El benchmark fue `data/eval/benchmark.jsonl`, versión `kubgu-retrieval-v1`, con SHA-256 verificado:

```text
b69b4916f94411621cae4336e235e8221f3d0e677b86e3c5a1fd53fca7c7215d
```

Contiene 36 consultas y 50 etiquetas binarias de relevancia:

| Idioma | Consultas |
|---|---:|
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

El corpus efectivo fue el construido en memoria por `OfficialDocumentLibrary`: 18 fuentes y 44 fragmentos activos. El repositorio no documenta la identidad, número o acuerdo de los anotadores. Por ello no se atribuyen las etiquetas a varios expertos.

## Activación efectiva

| Solicitado | Efectivo | Estado | Dense activo | Reranker activo | Consultas | Errores |
|---|---|---|---:|---:|---:|---:|
| keyword | keyword | completed | No | No | 36 | 0 |
| bm25 | bm25 | completed | No | No | 36 | 0 |
| dense | dense | completed | Sí | No | 36 | 0 |
| hybrid | hybrid | completed | Sí | No | 36 | 0 |
| hybrid_rerank | hybrid_rerank | completed | Sí | Sí | 36 | 0 |

El reranker cargó y usó ambos cross-encoders y registró 720 predicciones. No se aceptó ningún fallback BM25 como método neuronal.

## Resultados globales

| Método | Métrica | @1 | @3 | @5 |
|---|---|---:|---:|---:|
| keyword | Hit | 0.277778 | 0.305556 | 0.361111 |
| keyword | Recall | 0.180556 | 0.222222 | 0.263889 |
| keyword | Precision | 0.277778 | 0.120370 | 0.083333 |
| keyword | MRR | 0.277778 | 0.291667 | 0.304167 |
| keyword | nDCG | 0.277778 | 0.232564 | 0.251116 |
| bm25 | Hit | 0.361111 | 0.444444 | 0.500000 |
| bm25 | Recall | 0.222222 | 0.361111 | 0.430556 |
| bm25 | Precision | 0.361111 | 0.203704 | 0.144444 |
| bm25 | MRR | 0.361111 | 0.393519 | 0.406019 |
| bm25 | nDCG | 0.361111 | 0.352685 | 0.384415 |
| dense | Hit | 0.583333 | 0.805556 | 0.805556 |
| dense | Recall | 0.444444 | 0.722222 | 0.777778 |
| dense | Precision | 0.583333 | 0.342593 | 0.227778 |
| dense | MRR | 0.583333 | 0.689815 | 0.689815 |
| dense | nDCG | 0.583333 | 0.668239 | 0.696087 |
| hybrid | Hit | 0.361111 | 0.611111 | 0.694444 |
| hybrid | Recall | 0.236111 | 0.513889 | 0.666667 |
| hybrid | Precision | 0.361111 | 0.259259 | 0.200000 |
| hybrid | MRR | 0.361111 | 0.467593 | 0.487037 |
| hybrid | nDCG | 0.361111 | 0.444115 | 0.513971 |
| hybrid_rerank | Hit | 0.527778 | 0.722222 | 0.777778 |
| hybrid_rerank | Recall | 0.375000 | 0.680556 | 0.736111 |
| hybrid_rerank | Precision | 0.527778 | 0.314815 | 0.205556 |
| hybrid_rerank | MRR | 0.527778 | 0.620370 | 0.632870 |
| hybrid_rerank | nDCG | 0.527778 | 0.614584 | 0.640471 |

Dense obtuvo los mayores valores globales de Hit@5, MRR@5 y nDCG@5. Hybrid rerank superó a BM25 y a hybrid simple en MRR@5 y nDCG@5, pero no superó a dense en Hit@5, MRR@5 ni nDCG@5.

## Resultados por idioma

Los resultados siguientes son descriptivos. Inglés tiene 9 consultas y ruso solo 4; no deben interpretarse como evidencia de comportamiento general por idioma.

| Método | Idioma | N | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
|---|---|---:|---:|---:|---:|---:|---:|
| keyword | en | 9 | 0.222222 | 0.166667 | 0.044444 | 0.222222 | 0.179239 |
| keyword | es | 23 | 0.347826 | 0.282609 | 0.086957 | 0.258696 | 0.242939 |
| keyword | ru | 4 | 0.750000 | 0.375000 | 0.150000 | 0.750000 | 0.459860 |
| bm25 | en | 9 | 0.555556 | 0.500000 | 0.177778 | 0.555556 | 0.495944 |
| bm25 | es | 23 | 0.391304 | 0.304348 | 0.095652 | 0.244203 | 0.240222 |
| bm25 | ru | 4 | 1.000000 | 1.000000 | 0.350000 | 1.000000 | 0.962586 |
| dense | en | 9 | 0.666667 | 0.666667 | 0.222222 | 0.537037 | 0.581911 |
| dense | es | 23 | 0.826087 | 0.782609 | 0.208696 | 0.739130 | 0.716416 |
| dense | ru | 4 | 1.000000 | 1.000000 | 0.350000 | 0.750000 | 0.836087 |
| hybrid | en | 9 | 0.777778 | 0.722222 | 0.222222 | 0.509259 | 0.536186 |
| hybrid | es | 23 | 0.608696 | 0.586957 | 0.165217 | 0.410870 | 0.435929 |
| hybrid | ru | 4 | 1.000000 | 1.000000 | 0.350000 | 0.875000 | 0.912730 |
| hybrid_rerank | en | 9 | 0.444444 | 0.333333 | 0.111111 | 0.355556 | 0.316705 |
| hybrid_rerank | es | 23 | 0.869565 | 0.847826 | 0.217391 | 0.677536 | 0.704636 |
| hybrid_rerank | ru | 4 | 1.000000 | 1.000000 | 0.350000 | 1.000000 | 1.000000 |

No se afirma que un método sea mejor para todos los idiomas. Por ejemplo, hybrid rerank presenta valores descriptivos inferiores a dense en inglés, mientras el grupo ruso es demasiado pequeño para generalizar.

## Resultados por categoría

Todos los grupos tienen entre 3 y 7 consultas. La tabla @5 es exclusivamente descriptiva.

| Método | Categoría | N | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
|---|---|---:|---:|---:|---:|---:|---:|
| keyword | academic | 6 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| keyword | admin | 7 | 0.571429 | 0.571429 | 0.142857 | 0.464286 | 0.478628 |
| keyword | health | 3 | 0.333333 | 0.166667 | 0.066667 | 0.066667 | 0.079066 |
| keyword | housing | 4 | 0.500000 | 0.250000 | 0.100000 | 0.375000 | 0.250000 |
| keyword | language | 4 | 0.750000 | 0.500000 | 0.150000 | 0.750000 | 0.556574 |
| keyword | migration | 7 | 0.142857 | 0.142857 | 0.057143 | 0.142857 | 0.142857 |
| keyword | visa | 5 | 0.400000 | 0.200000 | 0.080000 | 0.400000 | 0.245259 |
| bm25 | academic | 6 | 0.166667 | 0.166667 | 0.033333 | 0.083333 | 0.105155 |
| bm25 | admin | 7 | 0.571429 | 0.500000 | 0.114286 | 0.369048 | 0.391036 |
| bm25 | health | 3 | 1.000000 | 0.666667 | 0.266667 | 0.777778 | 0.639907 |
| bm25 | housing | 4 | 0.750000 | 0.750000 | 0.300000 | 0.750000 | 0.750000 |
| bm25 | language | 4 | 0.750000 | 0.625000 | 0.250000 | 0.750000 | 0.653287 |
| bm25 | migration | 7 | 0.285714 | 0.214286 | 0.057143 | 0.171429 | 0.176743 |
| bm25 | visa | 5 | 0.400000 | 0.400000 | 0.160000 | 0.400000 | 0.340138 |
| dense | academic | 6 | 0.833333 | 0.833333 | 0.166667 | 0.666667 | 0.710310 |
| dense | admin | 7 | 0.571429 | 0.500000 | 0.114286 | 0.571429 | 0.516164 |
| dense | health | 3 | 1.000000 | 1.000000 | 0.400000 | 1.000000 | 0.959072 |
| dense | housing | 4 | 1.000000 | 1.000000 | 0.400000 | 1.000000 | 1.000000 |
| dense | language | 4 | 1.000000 | 0.875000 | 0.300000 | 0.625000 | 0.657732 |
| dense | migration | 7 | 0.714286 | 0.714286 | 0.171429 | 0.714286 | 0.692906 |
| dense | visa | 5 | 0.800000 | 0.800000 | 0.240000 | 0.466667 | 0.565124 |
| hybrid | academic | 6 | 0.166667 | 0.166667 | 0.033333 | 0.166667 | 0.166667 |
| hybrid | admin | 7 | 0.857143 | 0.785714 | 0.171429 | 0.564286 | 0.580229 |
| hybrid | health | 3 | 1.000000 | 1.000000 | 0.400000 | 0.833333 | 0.833755 |
| hybrid | housing | 4 | 0.750000 | 0.750000 | 0.300000 | 0.750000 | 0.750000 |
| hybrid | language | 4 | 1.000000 | 0.875000 | 0.300000 | 0.812500 | 0.740886 |
| hybrid | migration | 7 | 0.571429 | 0.571429 | 0.142857 | 0.309524 | 0.382100 |
| hybrid | visa | 5 | 0.800000 | 0.800000 | 0.240000 | 0.333333 | 0.460368 |
| hybrid_rerank | academic | 6 | 0.500000 | 0.500000 | 0.100000 | 0.416667 | 0.438488 |
| hybrid_rerank | admin | 7 | 1.000000 | 0.928571 | 0.200000 | 0.857143 | 0.839287 |
| hybrid_rerank | health | 3 | 0.666667 | 0.500000 | 0.200000 | 0.400000 | 0.412399 |
| hybrid_rerank | housing | 4 | 1.000000 | 1.000000 | 0.400000 | 1.000000 | 1.000000 |
| hybrid_rerank | language | 4 | 0.750000 | 0.750000 | 0.250000 | 0.625000 | 0.657732 |
| hybrid_rerank | migration | 7 | 0.571429 | 0.571429 | 0.142857 | 0.464286 | 0.472556 |
| hybrid_rerank | visa | 5 | 1.000000 | 0.900000 | 0.240000 | 0.666667 | 0.675001 |

No se afirma superioridad para todas las categorías; existen categorías donde dense presenta valores mayores y los tamaños por grupo son reducidos.

## Bootstrap pareado

La comparación solicitada fue BM25 frente al mejor método híbrido por nDCG@5, que en esta ejecución fue hybrid rerank.

| Métrica | Diferencia hybrid rerank - BM25 | IC 95 % | p bilateral |
|---|---:|---|---:|
| MRR@5 | 0.226852 | [0.077766, 0.377789] | 0.0042 |
| nDCG@5 | 0.256056 | [0.116496, 0.398848] | 0.0010 |

Se usaron 36 pares, 10 000 remuestras y semilla 42. Esta comparación no evalúa ni prueba superioridad de hybrid rerank frente a dense. El benchmark pequeño limita la potencia y estabilidad de los intervalos y p-valores.

## Reproducción de B2

Los 75 agregados globales de B3 coincidieron con B2 con tolerancia absoluta `1e-12`. No se observaron diferencias en métricas, estados, número de consultas, activación de componentes o predicciones registradas.

## Tests focalizados

Comando ejecutado desde `backend`, usando `venv311` con semantic search desactivado para no cargar modelos reales desde ese entorno:

```bash
ENABLE_SEMANTIC_SEARCH=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 ../venv311/Scripts/python.exe -m pytest tests/test_eval_metrics.py tests/test_evaluator_unit.py tests/test_evaluator_integration.py tests/test_retrieval.py tests/test_retrieval_phase3.py tests/test_neural_evaluation_strict.py -q
```

Resultado: 51 aprobados, 0 fallidos, 0 omitidos y 0 errores. Se observaron dos advertencias preexistentes de torchvision sobre APIs beta.

## Artefactos

Directorio: `data/eval/results/neural_20260829_v1/`.

- `retrieval_eval_neural_20260829_v1.json`: configuración, entorno, snapshots, evidencia offline, resultados y 180 trazas.
- `retrieval_eval_neural_20260829_v1_summary.csv`: cinco resultados globales y metadata de activación.
- `retrieval_eval_neural_20260829_v1_queries.csv`: 36 consultas por cada uno de los cinco métodos.
- `retrieval_eval_neural_20260829_v1_by_language.csv`: 15 filas método-idioma.
- `retrieval_eval_neural_20260829_v1_by_category.csv`: 35 filas método-categoría.
- `retrieval_eval_neural_20260829_v1_bootstrap.json`: comparación pareada BM25-hybrid rerank.

## Limitaciones y conclusiones técnicas

- Los resultados corresponden a 36 consultas y no permiten una generalización amplia.
- La relevancia es binaria y la procedencia de la anotación no está documentada.
- Los desgloses de ruso y de todas las categorías tienen muestras pequeñas.
- Solo se verificó un entorno Windows CPU y los snapshots indicados.
- El corpus efectivo se construye en memoria desde código de producción; otras copias JSON del corpus no representan necesariamente esa ejecución.
- Dense fue el mejor método global en Hit@5, MRR@5 y nDCG@5.
- Hybrid rerank mejoró respecto de BM25 y hybrid simple en MRR@5 y nDCG@5, pero quedó por debajo de dense en Hit@5, MRR@5 y nDCG@5.
- El bootstrap solo sustenta la comparación pareada BM25-hybrid rerank bajo este benchmark. No compara hybrid rerank con dense.
- No se concluye una superioridad general del enfoque híbrido ni se considera confirmada una hipótesis global de superioridad.
