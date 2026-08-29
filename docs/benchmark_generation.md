# Generación del benchmark sintético extendido

## Propósito

`backend/eval/generate_extended_benchmark.py` genera offline 132 consultas de recuperación a partir de los 44 fragmentos activos de `OfficialDocumentLibrary`. No modifica el benchmark original.

El resultado es enteramente sintético: no es una anotación humana ni experta. Cada consulta y su relación binaria con un fragmento se derivan de una configuración de temas y plantillas, no de un juicio humano. Todos los registros tienen `annotation_status: synthetic_needs_human_review` y `used_for_official_metrics: false`. El manifest y diagnostics repiten esos valores y establecen `official_evaluation_eligible: false`. Estas consultas no son aptas para métricas oficiales.

## Diseño

La configuración está en `backend/eval/benchmark_generation_config.py` y contiene:

- versión del generador `template-grounded-v2`;
- semilla predeterminada 42;
- idiomas ES, EN y RU;
- 44 temas vinculados uno a uno con IDs reales `source::index`;
- categoría y descripción localizada de cada tema;
- plantillas interrogativas generales por idioma, incluidas formulaciones rusas que presentan el tema como etiqueta para evitar problemas de declinación;
- objetivos por idioma y categoría.

El generador crea una pregunta por cada par idioma-fragmento: 44 consultas en cada idioma y 132 en total. La selección de plantilla usa `random.Random(seed)`. No usa LLM, embeddings, APIs, red ni modelos externos.

## Ejecución

Desde `backend/`:

```bash
ENABLE_SEMANTIC_SEARCH=0 \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
HF_HUB_DISABLE_TELEMETRY=1 \
../venv311/Scripts/python.exe -m eval.generate_extended_benchmark \
  --seed 42 \
  --output ../data/eval/benchmark_extended.jsonl \
  --manifest ../data/eval/benchmark_extended.manifest.json \
  --diagnostics ../data/eval/benchmark_extended_diagnostics.json
```

El script carga el corpus efectivo de producción con semantic search desactivado, compara exactamente sus IDs con la configuración y falla ante fragmentos ausentes o inesperados.

## Esquema

Cada línea incluye los campos solicitados:

```json
{
  "query_id": "q001",
  "query_text": "...",
  "language": "es",
  "category": "education",
  "relevant_fragments": ["КубГУ::0"],
  "annotation_notes": "...",
  "annotation_status": "synthetic_needs_human_review",
  "used_for_official_metrics": false
}
```

También incluye:

- `annotation_type: synthetic_binary`;
- `status: needs_human_review` como alias legado conservado únicamente para compatibilidad con el loader existente; no sustituye a `annotation_status`;
- versión, método, semilla, plantilla y fragmento en `generation_metadata`;
- aliases `id`, `question`, `lang`, `relevant_chunk_ids`, `notes` y `metadata` para compatibilidad con el loader de evaluación existente.

La relevancia es binaria y contiene un fragmento por consulta. No se implementó relevancia gradual porque no existe un juicio humano que sustente grados.

## Validación

El generador comprueba antes de escribir:

- `query_id` único y no vacío;
- consulta única, no vacía y de longitud mínima;
- forma lingüística básica para ES, EN y RU;
- idioma perteneciente a `{es, en, ru}`;
- categoría no vacía;
- al menos un fragmento relevante;
- existencia de cada ID en el corpus activo;
- `annotation_status: synthetic_needs_human_review` presente y exacto en cada registro;
- `used_for_official_metrics: false` presente y exacto en cada registro;
- alias legado `status: needs_human_review` y tipo de anotación sintética explícitos;
- coherencia de aliases;
- cumplimiento exacto de objetivos por idioma y categoría.

El manifest y diagnostics deben contener de forma coherente `annotation_status: synthetic_needs_human_review`, `used_for_official_metrics: false` y `official_evaluation_eligible: false`.

Pruebas:

```bash
cd backend
ENABLE_SEMANTIC_SEARCH=0 \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
HF_HUB_DISABLE_TELEMETRY=1 \
../venv311/Scripts/python.exe -m pytest tests/test_benchmark_generation.py -q
```

## Archivos generados

- `data/eval/benchmark_extended.jsonl`: 132 consultas sintéticas.
- `data/eval/benchmark_extended.manifest.json`: hash, versión, esquema, conteos, corpus y procedencia.
- `data/eval/benchmark_extended_diagnostics.json`: validación, cobertura, objetivos y estado de revisión.

## Limitaciones

- Cada pregunta se crea a partir del tema y del fragmento que después se marca como relevante. Este procedimiento introduce sesgo de construcción y fuga de vocabulario: las consultas comparten términos explícitos con su referencia y pueden favorecer recuperadores léxicos o semánticos.
- La cobertura de 44 fragmentos no demuestra representatividad de necesidades reales de estudiantes.
- Las preguntas no incluyen errores, ambigüedad o variación conversacional observada en usuarios reales.
- Las categorías son una taxonomía técnica del generador, no una taxonomía validada por expertos.
- La coherencia lingüística se valida con reglas estructurales, no mediante evaluación humana de naturalidad.
- La evaluación sobre este archivo debe presentarse separada de los resultados del benchmark humano original.

## Revisión humana requerida

La siguiente iteración debe someter las 132 consultas a revisión humana, corregir formulación y categoría, verificar uno o más fragmentos relevantes y registrar anotador y protocolo. Solo una versión revisada por personas, validada y versionada por separado puede utilizarse en una evaluación oficial.
