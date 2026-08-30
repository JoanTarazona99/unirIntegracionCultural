# Adaptador del benchmark revisado al contrato B3

## Motivo y alcance

El loader B3 consume los campos `id`, `question`, `lang`, `category` y
`relevant_chunk_ids`. La exportación exploratoria revisada conserva esos valores con
nombres orientados al proceso de revisión. El adaptador traduce los nombres sin
filtrar, reordenar, duplicar ni alterar contenido.

La fuente contiene 114 registros exportables: 15 `accepted` y 99 `revised`, con 38
consultas en español, 38 en inglés y 38 en ruso. Los 18 IDs `pending` ya excluidos de
la exportación fuente no se reincorporan; no existen registros `rejected` excluidos en
esta versión.

## Entradas y salidas

El adaptador lee:

- `data/eval/benchmark_extended_reviewed_114.jsonl`;
- `data/eval/benchmark_extended_reviewed_114.manifest.json`;
- `data/eval/benchmark_extended_reviewed_114_diagnostics.json`;
- `data/eval/benchmark_extended.jsonl`, solo como vocabulario de 17 categorías e
  inventario de fragmentos activos.

Genera, por separado de todos los benchmarks fuente:

- `data/eval/benchmark_extended_reviewed_114_b3.jsonl`;
- `data/eval/benchmark_extended_reviewed_114_b3.manifest.json`;
- `data/eval/benchmark_extended_reviewed_114_b3_diagnostics.json`.

Se ejecuta con:

```bash
python backend/eval/adapt_reviewed_benchmark_for_b3.py
```

## Esquemas y mapeo

Cada entrada contiene la consulta y los qrels sintéticos originales, los campos
revisados, el estado de revisión, los controles de calidad y los metadatos de
elegibilidad y procedencia. El adaptador conserva todos esos campos sin modificación.

El contrato B3 añadido es:

```json
{
  "id": "q001",
  "question": "texto revisado",
  "lang": "es",
  "category": "education",
  "relevant_chunk_ids": ["КубГУ::0"]
}
```

El mapeo exacto es:

| Campo B3 | Campo fuente revisado |
| --- | --- |
| `id` | `query_id` |
| `question` | `reviewed_query_text` |
| `lang` | `language` |
| `category` | `reviewed_category` |
| `relevant_chunk_ids` | `reviewed_relevant_fragments` |

Los qrels multifragmento se copian completos y en el mismo orden. Además, cada salida
incluye:

```json
{
  "evaluation_dataset_type": "synthetic_ai_reviewed_exploratory",
  "used_for_official_metrics": false,
  "official_evaluation_eligible": false,
  "human_review_completed": false,
  "b3_adapter_version": "v1"
}
```

## Invariantes

Antes de escribir, el adaptador exige:

- exactamente 114 entradas y un `id` único por entrada;
- relación uno a uno y conservación del orden fuente;
- estados `accepted` o `revised` y todos los controles de calidad elegibles;
- texto, categoría, qrels, `reviewer_id` y `reviewed_at` no vacíos;
- idiomas `es`, `en` o `ru`, con distribución 38/38/38;
- categorías pertenecientes al vocabulario activo de 17 categorías;
- qrels no vacíos y presentes en el inventario activo;
- ausencia de los 18 IDs `pending` registrados por los diagnostics fuente;
- igualdad exacta entre cada campo revisado y su alias B3;
- preservación de todos los campos fuente y de los qrels multifragmento;
- los tres flags de elegibilidad en `false` en fuente y salida;
- coincidencia de hashes fuente con sus metadatos y SHA-256 del JSONL generado;
- regeneración determinista de los bytes JSONL para las mismas entradas.

El manifest registra distribuciones, multifragmento, hashes o referencias de todas las
entradas, fecha de creación, versión, mapeo y advertencia metodológica. Los diagnostics
registran errores, conteos, IDs únicos, comparaciones con la fuente, exclusiones, flags
e invariantes.

## Limitaciones metodológicas

Las consultas y los qrels tienen origen sintético y fueron revisados con asistencia de
IA. `human_review_completed`, `official_evaluation_eligible` y
`used_for_official_metrics` permanecen en `false`; la adaptación no convierte el
conjunto en anotación humana ni en benchmark oficial.

El adaptador no ejecuta retrieval, modelos neuronales, reranking, métricas, bootstrap
ni llamadas de red, y no modifica algoritmos, hiperparámetros o configuración de
retrieval. Cualquier evaluación posterior es exclusivamente exploratoria y sus
resultados deben persistirse en un directorio separado, nunca sobre estos artefactos o
los benchmarks fuente.