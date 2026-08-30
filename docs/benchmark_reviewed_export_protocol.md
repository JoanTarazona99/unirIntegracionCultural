# Protocolo de exportación del benchmark sintético revisado por IA

## Alcance

`data/eval/benchmark_extended_reviewed_114.jsonl` es una exportación exploratoria separada de `data/eval/benchmark_extended_review_template.jsonl`. Conserva el origen sintético de las consultas y de los qrels y no modifica ni sustituye la plantilla de revisión.

La plantilla fuente contiene 132 registros. La exportación incluye 114 registros completos: 15 con `review_status: accepted` y 99 con `review_status: revised`. Los 18 registros `pending` quedan fuera, al igual que cualquier registro `rejected`; en esta versión no había registros rechazados.

## Criterios de inclusión

Solo se exportan registros `accepted` o `revised` que cumplan todas estas condiciones:

- texto, categoría y fragmentos revisados completos;
- `semantic_validity: valid`;
- `relevance_validity: valid` o `multi_fragment`;
- `language_quality: fluent` o `acceptable`;
- `ambiguity: low` o `medium`;
- `reviewer_id` y `reviewed_at` presentes;
- todos los fragmentos revisados pertenecen al inventario activo de la fuente;
- campos sintéticos idénticos a los del benchmark candidato;
- `used_for_official_metrics: false`.

Un registro que tenga estado incluido pero incumpla una condición se excluye y se documenta en los diagnostics sin convertirlo automáticamente en `rejected`.

## Naturaleza de la revisión

La revisión fue asistida por IA. El identificador de revisor preservado en los registros identifica al sistema que realizó esa revisión y no atribuye la decisión a una persona. Por ello, todos los registros y artefactos mantienen:

```json
{
  "export_status": "synthetic_ai_reviewed_exploratory",
  "human_review_completed": false,
  "used_for_official_metrics": false,
  "official_evaluation_eligible": false
}
```

Este workflow no completa una revisión humana, no convierte qrels sintéticos en juicios humanos y no hace oficial el conjunto. El archivo no debe llamarse benchmark oficial, benchmark validado por humanos ni anotación humana.

## Trazabilidad

El manifest registra el hash SHA-256 del JSONL exportado, los hashes de la plantilla y del benchmark sintético fuente, las distribuciones por idioma y categoría revisada, el número de casos `multi_fragment`, la fecha de generación y la versión `v1` del protocolo.

Los diagnostics registran todos los motivos de exclusión, sus conteos y los `query_id` afectados. En esta exportación los 18 registros excluidos lo fueron por estado `pending`; ningún registro `accepted` o `revised` incumplió las reglas de calidad.

La exportación es determinista respecto al contenido de la plantilla. Una regeneración con la misma entrada produce el mismo JSONL; solo la fecha de generación de los metadatos puede variar.

## Uso y limitaciones

Toda evaluación posterior debe conservar y comunicar el origen sintético de las consultas y los qrels, la asistencia de IA durante la revisión y los flags de no elegibilidad. Los registros `pending` permanecen fuera de cualquier análisis basado en esta exportación.

El conjunto es exploratorio. Sus resultados no deben generalizarse a estudiantes, usuarios reales ni tráfico de producción. La procedencia desde fragmentos conocidos puede introducir fuga de vocabulario, sesgo favorable a los qrels generadores y una dificultad distinta de la observada en consultas reales.

Una evaluación oficial requeriría un proceso posterior, separado y explícitamente aprobado, con revisión humana documentada y un artefacto diferente. Este protocolo no concede esa aprobación.