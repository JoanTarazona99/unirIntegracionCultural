# Soluciones para retrieval léxico multilingüe

Fecha: 2026-09-01

## Alcance

Investigación exploratoria sobre el estado SPbU previamente adquirido: 45 chunks,
un chunk SPbU en ruso y ejecución sin red. Se evaluaron consultas y
transformaciones controladas; no se modificó código operativo.

No es un benchmark y no contiene qrels ni juicios independientes. Los resultados
son corpus-specific y protocol-specific, y no establecen superioridad general.

## Preflight

- Repositorio: `C:/xampp/htdocs/proyectos/unirIntegracionCultural`.
- Rama: `feature/real-source-testing`.
- Working tree inicial: limpio.
- HEAD inicial: `0dda598`.
- `git diff --check`: limpio.

## Causas confirmadas en código

### Aliases

No existe un registro de aliases para SPbU, СПбГУ, UNAM o UBA. Solo hay lógica
especial hardcoded para KubGU en el keyword legacy. `Chunk.metadata` existe,
pero `Chunk.text` indexa únicamente título y contenido, por lo que aliases en
metadata no serían recuperables sin integrarlos explícitamente al texto de
índice o al procesamiento de consultas.

### Expansión cross-lingual

BM25 dispone de una tabla ES/EN→RU para términos migratorios y administrativos.
No incluye `programas/programs`, `ofrece/offer`, `educación/education`,
`cursos/courses` ni aliases `SpbU/СПбГУ`.

### Tokenización

El tokenizer avanzado usa `\w+` Unicode y separa correctamente puntuación y
alfabetos. El keyword legacy usa `query.lower().split()`, conserva `¿qué` y
`spbu?`, asigna 0.1 por coincidencia en contenido y exige `match_score > 0.3`.

### Dense

El modelo configurado es multilingüe, pero dense no está disponible en el
entorno actual: `torch 2.0.1+cpu` es incompatible con
`sentence-transformers 5.6.0`/`transformers 4.57.6`. Dense no produjo rankings y
no puede compararse con las soluciones léxicas en este experimento.

El híbrido degrada a sparse cuando dense no está activo. Esa degradación es útil
en producción, pero debe exponer el modo efectivo para no interpretar sparse
como evidencia de un híbrido real.

## Experimento 1: aliases explícitos en consultas

Modo: keyword end-to-end, sin modificar índice.

| Consulta | SPbU recuperado | Resultado |
|---|---:|---|
| `¿Qué programas ofrece SpbU?` | no | FAQ KubSU; abstained |
| `¿Qué programas ofrece СПБГУ?` | no | FAQ KubSU; abstained |
| `What programs does SpbU offer?` | no | fallback KubSU; abstained |
| `SpbU programs admission` | no | fallback KubSU; abstained |

Escribir un alias en la consulta no basta cuando dicho alias no está indexado y
la puntuación permanece adherida al token.

## Experimento 2: expansión manual de consulta

Modo: keyword end-to-end.

| Consulta | SPbU recuperado | Relevancia | Resultado |
|---|---:|---:|---|
| `программы образование СПБГУ курсы` | sí | 0.4 | template; grounding high, 0.932 |
| `programas educación SpbU cursos` | no | 0.3 fallback | abstained |
| `programs education SpbU courses` | no | 0.3 fallback | abstained |

La expansión temática solo funcionó cuando los términos se expresaron en el
idioma del contenido. Añadir más términos ES/EN sin traducción no resolvió el
desajuste.

## Componentes controlados con BM25

Consulta original: `¿Qué programas ofrece SpbU?`.

| Condición | Rango SPbU | Score normalizado | Interpretación |
|---|---:|---:|---|
| BM25 actual | ausente | n/a | sin cobertura cross-lingual |
| Solo aliases añadidos al título in-memory | 5 | 0.0 | señal insuficiente |
| Expansión ES→RU de la consulta | 1 | 1.0 | recuperación exitosa |
| Aliases + expansión ES→RU | 1 | 1.0 | sin mejora observable sobre expansión |
| Solo normalización en keyword | ausente | n/a | necesaria, no suficiente |

BM25 normaliza los scores dentro de cada ranking; el último resultado positivo
puede quedar en 0.0 tras min-max. Por ello, el valor 0.0 del alias no significa
ausencia de score BM25 bruto, sino que SPbU fue el candidato positivo más débil.

En esta única consulta, la expansión fue el componente decisivo. No puede
inferirse que siempre supere aliases o dense.

## Solución recomendada

### Prioridad 0: observabilidad y normalización

1. Reutilizar `retrieval.chunks.tokenize()` en todos los caminos sparse.
2. Registrar `requested_mode`, `effective_mode`, `fallback_reason` y si dense
   generó embeddings.
3. En pruebas, fallar explícitamente cuando se solicita dense y no está activo.

Esfuerzo orientativo: 0,5-1,5 días de desarrollo y pruebas.

### Prioridad 1: aliases institucionales versionados

1. Añadir a cada fuente `canonical_name`, `aliases` y `language`.
2. Propagar esos campos desde `source_registry` a `Chunk.metadata`.
3. Incorporar aliases al texto indexado de BM25/dense con menor peso o campo
   separado, evitando boosts hardcoded por universidad.
4. Canonicalizar aliases también en la cobertura de entidades del grounding.

Ejemplo SPbU: `SpbU`, `СПбГУ`, `Saint Petersburg State University` y
`Санкт-Петербургский государственный университет`.

Esfuerzo orientativo: 1,5-3 días, incluyendo migración compatible y pruebas.

### Prioridad 2: expansión léxica según idioma del corpus

1. Extender un diccionario versionado y retrieval-scoped con conceptos
   académicos y aliases institucionales.
2. Conservar consulta original, tokens añadidos, idioma destino y versión del
   diccionario en la traza.
3. Limitar expansión por dominio e idioma para reducir query drift.
4. Fusionar ranking original y expandido mediante RRF en vez de reemplazar la
   consulta del usuario.

Entradas mínimas sugeridas para el caso observado:

- `programas/programs` → `программы`, `образование`, `курсы`;
- `ofrece/offer` → `предлагает`;
- `SpbU` → `СПбГУ`, nombre ruso y nombre inglés.

Esfuerzo orientativo: 1-2 días para una tabla mínima con pruebas; 3-5 días para
detección de idioma, trazabilidad y fusión robusta.

### Prioridad 3: compuerta de evidencia

El detector de slots no contempla oferta académica. Debe exigir evidencia del
objeto solicitado (`programa`, `carrera`, `grado`, `posgrado`, etc.) y no aceptar
solo coincidencia institucional. Esto responde también a los falsos positivos
observados en la prueba UNAM.

Esfuerzo orientativo: 1-2 días más calibración en un conjunto de desarrollo
separado.

### Prioridad 4: restaurar dense y evaluar híbrido

1. Usar un entorno neural separado con el lock completo y snapshot local.
2. Confirmar carga offline y número esperado de embeddings.
3. Comparar query original, aliases, expansión, dense y fusión sobre un conjunto
   pequeño ES/EN/RU revisado manualmente.
4. No etiquetar sparse-only como `hybrid` cuando dense esté inactivo.

Esfuerzo orientativo: 1-2 días para restauración/observabilidad del entorno y
2-4 días para diseñar y revisar el conjunto diagnóstico. La estimación no incluye
un benchmark formal.

## Secuencia de implementación propuesta

1. Normalización compartida y telemetría de fallback.
2. Alias schema e indexación.
3. Expansión versionada con fusión original/expandida.
4. Cobertura académica en evidence assessment.
5. Dense offline y comparación controlada.

La primera entrega debe incluir pruebas de regresión con SPbU, UBA y UNAM:
recuperar SPbU desde ES/EN, conservar recuperación RU, recuperar UBA desde una
pregunta natural y abstenerse ante el contenido UNAM irrelevante.

## Artefactos

- `run_experiments.py`: protocolo reproducible.
- `results.json`: resultados estructurados.
- `experiments.log`: traza completa.
- `preflight.log`: controles iniciales.

Las estimaciones son orientativas y requieren validación del equipo. No se
ejecutaron B3, el conjunto de 114 consultas, reranking, métricas agregadas ni
bootstrap; tampoco hubo acceso de red durante los experimentos.