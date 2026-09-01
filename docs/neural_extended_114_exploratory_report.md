# Informe técnico de la evaluación neuronal exploratoria de 114 consultas

Fecha del resultado publicado: 2026-08-30
Run: `retrieval_eval_neural_extended_114_20260830_v2`
Directorio publicado: `data/eval/results/neural_extended_114_20260830_v2/`

> **Condición de uso:** este resultado procede de un benchmark sintético revisado con asistencia de IA. Es exclusivamente exploratorio: no constituye un benchmark oficial, un gold standard ni una anotación humana independiente, y no es elegible para métricas oficiales.

## 1. Alcance

La evaluación usa 114 consultas del conjunto B3 exploratorio, con una distribución equilibrada por idioma y una distribución desigual por categoría.

| Propiedad | Valor |
| --- | ---: |
| Consultas | 114 |
| Español (ES) | 38 |
| Inglés (EN) | 38 |
| Ruso (RU) | 38 |
| Registros `accepted` | 15 |
| Registros `revised` | 99 |
| Registros `pending` excluidos | 18 |
| Registros con qrels multifragmento | 44 |

El adaptador B3 preservó una relación uno a uno con la exportación revisada, el orden fuente y los qrels multifragmento. El SHA-256 del benchmark evaluado es:

```text
8e2584735a7d62b249c7c2c2acdfd029a4f46fd55d5112805491f6712fc2bec5
```

Los metadatos mantienen explícitamente:

```text
evaluation_dataset_type=synthetic_ai_reviewed_exploratory
used_for_official_metrics=false
official_evaluation_eligible=false
human_review_completed=false
```

## 2. Reproducibilidad

La ejecución publicada declara modo offline, semilla 42 y el intérprete dedicado `C:\venvs\unirIntegracionCultural\venv-rag-eval-probe\Scripts\python.exe`.

### Versiones de ejecución

| Componente | Versión |
| --- | --- |
| Python | 3.11.5 |
| PyTorch | 2.4.1+cpu |
| sentence-transformers | 5.6.0 |
| transformers | 4.57.6 |
| huggingface-hub | 0.36.2 |
| rank-bm25 | 0.2.2 |

### Snapshots locales

| Componente | Modelo | Commit del snapshot |
| --- | --- | --- |
| Dense multilingüe | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` |
| Reranker ES/RU | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | `1427fd652930e4ba29e8149678df786c240d8825` |
| Reranker EN | `cross-encoder/ms-marco-MiniLM-L-12-v2` | `7b0235231ca2674cb8ca8f022859a6eba2b1c968` |

Los tres snapshots locales constaban como disponibles. La evidencia incorporada al resultado registra `offline_probe_ok=true`, `probe_network_attempts=0` y `evaluation_network_attempts=0`. El probe verificó inferencia finita mínima de los tres componentes con archivos locales; no sustituyó la evaluación integral.

Los cinco métodos terminaron sin fallback (`fallback_count=0`) ni errores de retrieval. Dense estuvo activo en `dense`, `hybrid` y `hybrid_rerank`; el reranker estuvo activo en `hybrid_rerank`, con manejo estricto y 2.280 predicciones registradas. La telemetría `reranker_used` confirma que ambos cross-encoders, el modelo multilingüe para ES/RU y el modelo específico para EN, fueron cargados y utilizados.

La publicación siguió persistencia transaccional: cada JSON/CSV se serializó en un temporal del mismo directorio, se sincronizó y se reemplazó de forma atómica; después se validaron exactamente seis artefactos en staging. El directorio completo se publicó mediante reemplazo atómico solo tras superar el contrato y sin sobrescribir un destino existente.

## 3. Métricas globales

Todas las métricas de esta sección se presentan en corte 5 y proceden del resumen publicado.

| Método | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `keyword` | 0.5263 | 0.4415 | 0.1211 | 0.4336 | 0.4064 |
| `bm25` | 0.6842 | 0.5892 | 0.1596 | 0.5048 | 0.4930 |
| `dense` | **0.8684** | **0.7807** | 0.2053 | 0.6743 | 0.6577 |
| `hybrid` | 0.8070 | 0.7398 | 0.2018 | 0.6452 | 0.6418 |
| `hybrid_rerank` | 0.8246 | 0.7529 | **0.2070** | **0.7020** | **0.6841** |

## 4. Desglose por idioma

Cada celda de idioma resume 38 consultas. Este desglose es descriptivo, no inferencial: no se ejecutaron contrastes por idioma.

| Método | Idioma | n | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `keyword` | EN | 38 | 0.2368 | 0.1974 | 0.0526 | 0.2061 | 0.1853 |
| `keyword` | ES | 38 | 0.6316 | 0.5482 | 0.1421 | 0.4719 | 0.4721 |
| `keyword` | RU | 38 | 0.7105 | 0.5789 | 0.1684 | 0.6228 | 0.5618 |
| `bm25` | EN | 38 | 0.5000 | 0.4167 | 0.1211 | 0.2825 | 0.2873 |
| `bm25` | ES | 38 | 0.6316 | 0.5351 | 0.1316 | 0.4798 | 0.4713 |
| `bm25` | RU | 38 | 0.9211 | 0.8158 | 0.2263 | 0.7522 | 0.7205 |
| `dense` | EN | 38 | 0.8684 | 0.8114 | 0.2211 | 0.6689 | 0.6714 |
| `dense` | ES | 38 | 0.8158 | 0.7281 | 0.1842 | 0.6018 | 0.5965 |
| `dense` | RU | 38 | 0.9211 | 0.8026 | 0.2105 | 0.7522 | 0.7054 |
| `hybrid` | EN | 38 | 0.7368 | 0.7061 | 0.1947 | 0.5268 | 0.5487 |
| `hybrid` | ES | 38 | 0.7632 | 0.6579 | 0.1737 | 0.5732 | 0.5728 |
| `hybrid` | RU | 38 | 0.9211 | 0.8553 | 0.2368 | 0.8355 | 0.8037 |
| `hybrid_rerank` | EN | 38 | 0.5789 | 0.5000 | 0.1263 | 0.4000 | 0.3980 |
| `hybrid_rerank` | ES | 38 | 0.8947 | 0.8026 | 0.2211 | 0.7697 | 0.7387 |
| `hybrid_rerank` | RU | 38 | 1.0000 | 0.9561 | 0.2737 | 0.9364 | 0.9156 |

## 5. Desglose por categoría

Las categorías tienen tamaños pequeños y desiguales, entre 3 y 15 consultas. Estas cifras son descriptivas; diferencias grandes pueden depender de muy pocos casos y no deben interpretarse como evidencia inferencial por categoría.

| Método | Categoría | n | Hit@5 | Recall@5 | Precision@5 | MRR@5 | nDCG@5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `keyword` | admin | 12 | 0.5000 | 0.5000 | 0.1000 | 0.5000 | 0.5000 |
| `keyword` | communication | 6 | 0.8333 | 0.8333 | 0.1667 | 0.7500 | 0.7718 |
| `keyword` | cultural_adaptation | 6 | 0.8333 | 0.8333 | 0.1667 | 0.7500 | 0.7718 |
| `keyword` | documents | 15 | 0.4667 | 0.4000 | 0.1467 | 0.3333 | 0.3311 |
| `keyword` | education | 9 | 0.2222 | 0.1667 | 0.0444 | 0.1111 | 0.1131 |
| `keyword` | finance | 6 | 0.5000 | 0.5000 | 0.1000 | 0.5000 | 0.5000 |
| `keyword` | food | 3 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `keyword` | health | 6 | 0.5000 | 0.5000 | 0.1000 | 0.4167 | 0.4385 |
| `keyword` | housing | 9 | 0.4444 | 0.3889 | 0.1111 | 0.4444 | 0.4015 |
| `keyword` | language | 6 | 0.8333 | 0.5833 | 0.1667 | 0.7000 | 0.5772 |
| `keyword` | legal_rights | 3 | 0.3333 | 0.3333 | 0.0667 | 0.1667 | 0.2103 |
| `keyword` | migration | 12 | 0.6667 | 0.3611 | 0.1833 | 0.4083 | 0.3093 |
| `keyword` | safety | 6 | 0.3333 | 0.2500 | 0.0667 | 0.2500 | 0.2311 |
| `keyword` | scholarships | 3 | 0.6667 | 0.6667 | 0.1333 | 0.6667 | 0.6667 |
| `keyword` | transport | 6 | 0.3333 | 0.3333 | 0.0667 | 0.2222 | 0.2500 |
| `keyword` | visa | 6 | 0.8333 | 0.5000 | 0.2000 | 0.7500 | 0.5243 |
| `bm25` | admin | 12 | 0.4167 | 0.4167 | 0.0833 | 0.3333 | 0.3552 |
| `bm25` | communication | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8333 | 0.8770 |
| `bm25` | cultural_adaptation | 6 | 0.6667 | 0.6667 | 0.1333 | 0.4722 | 0.5218 |
| `bm25` | documents | 15 | 0.6000 | 0.4000 | 0.1467 | 0.3389 | 0.2887 |
| `bm25` | education | 9 | 0.2222 | 0.2222 | 0.0444 | 0.2222 | 0.2222 |
| `bm25` | finance | 6 | 0.8333 | 0.8333 | 0.1667 | 0.7222 | 0.7500 |
| `bm25` | food | 3 | 0.3333 | 0.3333 | 0.0667 | 0.1111 | 0.1667 |
| `bm25` | health | 6 | 1.0000 | 1.0000 | 0.2000 | 0.7639 | 0.8218 |
| `bm25` | housing | 9 | 0.7778 | 0.7778 | 0.2444 | 0.6148 | 0.6590 |
| `bm25` | language | 6 | 1.0000 | 0.8333 | 0.2333 | 0.8056 | 0.7057 |
| `bm25` | legal_rights | 3 | 0.3333 | 0.3333 | 0.0667 | 0.3333 | 0.3333 |
| `bm25` | migration | 12 | 0.8333 | 0.4722 | 0.2333 | 0.5125 | 0.4082 |
| `bm25` | safety | 6 | 0.6667 | 0.5833 | 0.1667 | 0.4222 | 0.4562 |
| `bm25` | scholarships | 3 | 0.6667 | 0.6667 | 0.1333 | 0.6667 | 0.6667 |
| `bm25` | transport | 6 | 0.8333 | 0.8333 | 0.1667 | 0.5000 | 0.5820 |
| `bm25` | visa | 6 | 0.8333 | 0.5000 | 0.2000 | 0.7222 | 0.4994 |
| `dense` | admin | 12 | 0.7500 | 0.7500 | 0.1500 | 0.6111 | 0.6468 |
| `dense` | communication | 6 | 1.0000 | 1.0000 | 0.2000 | 0.5833 | 0.6872 |
| `dense` | cultural_adaptation | 6 | 1.0000 | 1.0000 | 0.2000 | 0.6389 | 0.7321 |
| `dense` | documents | 15 | 0.3333 | 0.1889 | 0.0667 | 0.2800 | 0.1797 |
| `dense` | education | 9 | 1.0000 | 0.8333 | 0.2000 | 0.7778 | 0.7387 |
| `dense` | finance | 6 | 1.0000 | 1.0000 | 0.2000 | 0.9167 | 0.9385 |
| `dense` | food | 3 | 1.0000 | 1.0000 | 0.2000 | 0.8333 | 0.8770 |
| `dense` | health | 6 | 1.0000 | 1.0000 | 0.2000 | 0.5556 | 0.6706 |
| `dense` | housing | 9 | 0.8889 | 0.8333 | 0.2667 | 0.8148 | 0.7697 |
| `dense` | language | 6 | 1.0000 | 0.8333 | 0.2333 | 0.5556 | 0.5602 |
| `dense` | legal_rights | 3 | 1.0000 | 1.0000 | 0.2000 | 1.0000 | 1.0000 |
| `dense` | migration | 12 | 1.0000 | 0.7222 | 0.3333 | 0.8264 | 0.6727 |
| `dense` | safety | 6 | 0.8333 | 0.8333 | 0.2333 | 0.7500 | 0.7380 |
| `dense` | scholarships | 3 | 1.0000 | 1.0000 | 0.2000 | 0.3611 | 0.5205 |
| `dense` | transport | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8333 | 0.8770 |
| `dense` | visa | 6 | 1.0000 | 0.7500 | 0.3000 | 0.9167 | 0.7439 |
| `hybrid` | admin | 12 | 0.5000 | 0.5000 | 0.1000 | 0.4333 | 0.4489 |
| `hybrid` | communication | 6 | 1.0000 | 1.0000 | 0.2000 | 1.0000 | 1.0000 |
| `hybrid` | cultural_adaptation | 6 | 1.0000 | 1.0000 | 0.2000 | 0.7917 | 0.8436 |
| `hybrid` | documents | 15 | 0.5333 | 0.4444 | 0.1467 | 0.3056 | 0.3178 |
| `hybrid` | education | 9 | 0.5556 | 0.5000 | 0.1111 | 0.3556 | 0.3783 |
| `hybrid` | finance | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8667 | 0.8978 |
| `hybrid` | food | 3 | 0.3333 | 0.3333 | 0.0667 | 0.3333 | 0.3333 |
| `hybrid` | health | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8889 | 0.9167 |
| `hybrid` | housing | 9 | 0.7778 | 0.7778 | 0.2444 | 0.7778 | 0.7778 |
| `hybrid` | language | 6 | 1.0000 | 0.9167 | 0.2667 | 0.8333 | 0.7920 |
| `hybrid` | legal_rights | 3 | 0.6667 | 0.6667 | 0.1333 | 0.4167 | 0.4769 |
| `hybrid` | migration | 12 | 1.0000 | 0.7639 | 0.3667 | 0.7639 | 0.6656 |
| `hybrid` | safety | 6 | 1.0000 | 0.9167 | 0.2667 | 0.6389 | 0.7064 |
| `hybrid` | scholarships | 3 | 1.0000 | 1.0000 | 0.2000 | 0.7778 | 0.8333 |
| `hybrid` | transport | 6 | 1.0000 | 1.0000 | 0.2000 | 0.7833 | 0.8363 |
| `hybrid` | visa | 6 | 1.0000 | 0.6667 | 0.2667 | 0.8333 | 0.6213 |
| `hybrid_rerank` | admin | 12 | 0.5833 | 0.5833 | 0.1167 | 0.5208 | 0.5359 |
| `hybrid_rerank` | communication | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8333 | 0.8770 |
| `hybrid_rerank` | cultural_adaptation | 6 | 0.8333 | 0.8333 | 0.1667 | 0.8333 | 0.8333 |
| `hybrid_rerank` | documents | 15 | 0.6667 | 0.6333 | 0.2400 | 0.6222 | 0.5869 |
| `hybrid_rerank` | education | 9 | 0.6667 | 0.5556 | 0.1333 | 0.5833 | 0.5419 |
| `hybrid_rerank` | finance | 6 | 1.0000 | 1.0000 | 0.2000 | 1.0000 | 1.0000 |
| `hybrid_rerank` | food | 3 | 1.0000 | 1.0000 | 0.2000 | 0.6111 | 0.7103 |
| `hybrid_rerank` | health | 6 | 0.8333 | 0.8333 | 0.1667 | 0.6667 | 0.7103 |
| `hybrid_rerank` | housing | 9 | 1.0000 | 0.8889 | 0.2889 | 0.7130 | 0.7213 |
| `hybrid_rerank` | language | 6 | 1.0000 | 0.8333 | 0.2333 | 1.0000 | 0.8506 |
| `hybrid_rerank` | legal_rights | 3 | 0.6667 | 0.6667 | 0.1333 | 0.6667 | 0.6667 |
| `hybrid_rerank` | migration | 12 | 0.7500 | 0.5278 | 0.2500 | 0.5792 | 0.4873 |
| `hybrid_rerank` | safety | 6 | 1.0000 | 0.8333 | 0.2333 | 0.6389 | 0.6669 |
| `hybrid_rerank` | scholarships | 3 | 0.6667 | 0.6667 | 0.1333 | 0.6667 | 0.6667 |
| `hybrid_rerank` | transport | 6 | 1.0000 | 1.0000 | 0.2000 | 0.8056 | 0.8552 |
| `hybrid_rerank` | visa | 6 | 1.0000 | 0.8333 | 0.3333 | 0.8889 | 0.7745 |

## 6. Bootstrap pareado

El artefacto bootstrap compara exclusivamente `bm25` (baseline) con `hybrid_rerank` (candidate) sobre las mismas 114 consultas, con 10.000 remuestreos, semilla 42, intervalos de confianza del 95 % y valor p bilateral.

| Métrica | Diferencia observada (`hybrid_rerank - bm25`) | IC 95 % | p bilateral |
| --- | ---: | --- | ---: |
| MRR@5 | 0.1972 | [0.1186, 0.2769] | 0.0000 |
| nDCG@5 | 0.1911 | [0.1201, 0.2644] | 0.0000 |

El valor p se reproduce tal como fue publicado (`0.0`). Ambos intervalos quedan por encima de cero, por lo que el bootstrap publicado respalda una mejora de `hybrid_rerank` frente a BM25 en MRR@5 y nDCG@5 dentro de este conjunto. No se realizó comparación bootstrap con `dense` (`dense_comparison_performed=false`).

## 7. Interpretación

- `dense` obtiene los mejores valores globales de Hit@5 (0.8684) y Recall@5 (0.7807).
- `hybrid_rerank` obtiene los mejores valores globales de Precision@5 (0.2070), MRR@5 (0.7020) y nDCG@5 (0.6841).
- El bootstrap publicado respalda la mejora de `hybrid_rerank` frente a BM25 para MRR@5 y nDCG@5 en estas 114 consultas.
- No existe evidencia inferencial publicada para afirmar superioridad estadística de `hybrid_rerank` frente a `dense`.
- Las diferencias por idioma y categoría son descriptivas y no prueban comportamiento equivalente en usuarios reales, tráfico de producción u otros corpus.

## 8. Limitaciones

- Las consultas y los qrels tienen origen sintético.
- La revisión fue asistida por IA y no constituye revisión humana independiente completa.
- Se excluyeron 18 registros `pending`; los resultados no caracterizan esos casos.
- La procedencia desde fragmentos conocidos puede introducir fuga léxica y favorecer términos presentes en el corpus.
- Los qrels fueron generados y revisados a partir del corpus activo, lo que puede sesgar la dificultad y favorecer los fragmentos generadores.
- La distribución de categorías es desigual y abarca solo 3 a 15 consultas por categoría.
- Los tamaños pequeños por categoría producen estimaciones inestables; no se ejecutó inferencia por categoría.
- Las trazas contienen 9 estados `empty_results` y 561 `evaluated`. Un `empty_results` indica ausencia de resultados para esa consulta y método, pero no implica por sí mismo un error técnico; el conteo publicado de errores de retrieval es cero.
- Todo resultado e interpretación de este informe es exploratorio y no debe generalizarse a estudiantes, usuarios reales, otros corpus ni otros entornos de ejecución.

## 9. Integridad de la publicación

- La publicación contiene exactamente seis artefactos: resultado JSON completo, resumen global CSV, trazas CSV, desglose por idioma CSV, desglose por categoría CSV y bootstrap JSON.
- Se registran 570 trazas, equivalentes a 114 consultas por cada uno de los cinco métodos.
- Los cinco métodos constan como `completed`, con `retrieval_error_count=0` y `fallback_count=0`.
- `hybrid_rerank` registra 2.280 predicciones reales del reranker y activación efectiva tanto de dense como del reranker.
- La validación de publicación confirmó que los hashes de resultados históricos permanecieron intactos.
- El staging abortado `data/eval/results/.neural_extended_114_20260830_v1.staging/` no se recuperó, no se publicó y no se utilizó para generar los artefactos `v2`.
- El resultado final se publicó en `data/eval/results/neural_extended_114_20260830_v2/` mediante el protocolo transaccional descrito, sin sobrescribir resultados anteriores.

## 10. Fuentes

Este informe se generó exclusivamente a partir de los seis artefactos publicados de `v2`, el manifest y los diagnostics del benchmark B3, y la documentación versionada de exportación, adaptación, probe offline y persistencia transaccional. No se ejecutaron retrieval, modelos, reranking, métricas, bootstrap ni probes para producir este documento.