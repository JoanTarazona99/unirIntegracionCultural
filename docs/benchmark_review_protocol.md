# Protocolo de revisión humana del benchmark sintético

## Propósito

Este protocolo define una capa de revisión humana separada para los 132 candidatos de `data/eval/benchmark_extended.jsonl`. Los candidatos generados no son anotaciones humanas, juicios expertos ni evaluaciones de relevancia validadas. La revisión nunca sobrescribe el benchmark sintético fuente.

La plantilla inicial contiene 132 registros con estado `pending` y 0 registros aptos para métricas oficiales. Este workflow documenta decisiones humanas, pero por sí solo no convierte los datos en un benchmark oficial.

## Candidato sintético y juicio humano

Cada consulta sintética se generó a partir del fragmento marcado inicialmente como relevante. Esta procedencia puede introducir sesgo de plantilla, fuga de vocabulario (`query leakage`) y una asociación de relevancia favorable al fragmento generador. La relación sintética inicial sirve como propuesta para revisión, no como juicio humano.

El revisor debe evaluar de forma independiente:

- calidad lingüística y naturalidad de la consulta;
- validez semántica como necesidad de información;
- categoría;
- relevancia de uno o más fragmentos activos;
- ambigüedad y problemas de calidad.

Idealmente, el revisor debe ser independiente de la persona autora del generador. Cuando sea viable, se recomiendan dos revisores y el cálculo de acuerdo interanotador sobre estados, categorías y relevancia.

## Esquema y trazabilidad

Cada registro conserva sin modificaciones:

- `query_id`;
- `synthetic_query_text`, copiado literalmente de `query_text`;
- `language`;
- `synthetic_category`, copiado literalmente de `category`;
- `synthetic_relevant_fragments`, copiado literalmente de `relevant_fragments`;
- `annotation_status: synthetic_needs_human_review`;
- `used_for_official_metrics: false`.

El workflow añade:

- `reviewed_query_text`;
- `reviewed_category`;
- `reviewed_relevant_fragments`;
- `review_status`;
- `semantic_validity`;
- `relevance_validity`;
- `language_quality`;
- `ambiguity`;
- `notes`;
- `reviewer_id`;
- `reviewed_at`.

Las correcciones humanas se registran exclusivamente en campos `reviewed_*`. Nunca deben copiarse a campos `synthetic_*`. `reviewer_id` debe identificar al revisor de forma estable y `reviewed_at` debe usar formato ISO-8601 UTC, por ejemplo `2026-08-29T12:00:00Z`.

## Estados de revisión

### `pending`

Registro aún no revisado. Todos los campos de decisión humana permanecen en `null`.

### `accepted`

La consulta puede conservar su formulación, pero la decisión humana debe quedar explícita. Requiere texto revisado no vacío, categoría válida, al menos un fragmento relevante activo, identificador del revisor y timestamp UTC. Además exige:

- `semantic_validity: valid`;
- `relevance_validity: valid` o `multi_fragment`;
- `language_quality: fluent` o `acceptable`;
- `ambiguity: low` o `medium`.

### `revised`

El revisor corrigió la consulta, categoría o fragmentos relevantes. Debe cumplir exactamente los mismos requisitos de completitud y calidad que `accepted`. El valor corregido se guarda en el campo `reviewed_*` correspondiente.

### `rejected`

La consulta no debe formar parte de una futura exportación revisada. Requiere una explicación no vacía en `notes`; los demás campos humanos pueden permanecer en `null`. Deben rechazarse, entre otros casos, necesidades incoherentes, semánticamente inválidas o imposibles de fundamentar en el corpus activo.

## Relevancia multi-fragmento

Use `relevance_validity: multi_fragment` cuando una consulta válida necesite más de un fragmento para quedar respondida correctamente. En ese caso, `reviewed_relevant_fragments` debe enumerar todos y solo los fragmentos relevantes, sin limitarse al fragmento que originó la consulta. Cada identificador debe usar el formato `source::index` y existir en el inventario activo cubierto por el benchmark fuente.

No use `multi_fragment` para añadir contexto meramente relacionado. Si la relevancia no puede decidirse con seguridad, use `unclear`; ese registro no será candidato para una futura exportación evaluable.

## Revisión por idioma

Para ES, EN y RU, el revisor debe dominar el idioma evaluado o contar con apoyo lingüístico competente. Debe comprobar gramática, fluidez, terminología institucional, naturalidad y correspondencia entre la consulta y su intención. No debe aprobar una traducción solo porque comparte palabras con el fragmento fuente.

En ruso deben revisarse especialmente declinación, régimen preposicional y naturalidad de las formulaciones que presentan el tema entre comillas. En español e inglés deben evitarse calcos y construcciones artificiales derivadas de las plantillas. Una corrección lingüística requiere estado `revised` y texto completo en `reviewed_query_text`.

## Elegibilidad y métricas

Todos los registros de esta plantilla, incluidos `accepted` y `revised`, deben mantener `used_for_official_metrics: false`. El manifest y los diagnostics deben mantener `official_evaluation_eligible: false`.

Los registros `pending`, `rejected` o con decisiones `unclear` se excluyen de cualquier métrica oficial. Los registros completos `accepted` y `revised` solo son candidatos para una futura exportación separada; no se convierten automáticamente en oficiales. Una versión posterior necesitaría generación separada, validación, versionado y aprobación explícita antes de poder habilitar métricas oficiales.

El tamaño final evaluable debe calcularse y reportarse únicamente después de terminar la revisión. No debe presentarse 132 como tamaño humano validado.

## Limitaciones

- El conjunto tiene solo 132 candidatos y 44 fragmentos activos.
- Las consultas proceden de plantillas deterministas y no representan necesariamente preguntas reales.
- La generación desde el fragmento relevante introduce sesgo y `query leakage`.
- La relevancia inicial es sintética y binaria, no un juicio humano.
- Las 17 categorías tienen tamaños desiguales y no constituyen una taxonomía experta validada.
- La cobertura equilibrada de ES, EN y RU no garantiza igual dificultad lingüística o de recuperación.

Estas limitaciones deben acompañar cualquier informe posterior sobre el conjunto revisado.