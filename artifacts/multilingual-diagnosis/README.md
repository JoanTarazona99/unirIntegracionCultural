# Diagnóstico multilingüe de retrieval sobre SPbU

Fecha: 2026-09-01

## Alcance y estatus

Este es un diagnóstico exploratorio, corpus-specific y protocol-specific sobre
cuatro consultas y una página real adquirida de `https://spbu.ru`. No es un
benchmark, no contiene juicios de relevancia independientes y no permite estimar
efectividad general.

El preflight confirmó el repositorio esperado, la rama
`feature/real-source-testing`, un working tree limpio, `HEAD 64ca908` y
`git diff --check` sin incidencias.

## Configuración observada

- Estado rehidratado: 45 chunks, incluido un chunk SPbU.
- Contenido SPbU persistido: ruso, 5.108 caracteres en un solo chunk.
- Modo predeterminado: `keyword`.
- Modelo dense configurado: `paraphrase-multilingual-MiniLM-L12-v2`.
- Snapshot dense local: presente; se forzó carga offline.
- No hubo adquisición externa durante las consultas.

## Resultados por idioma

### Retrieval keyword end-to-end

| Consulta | Fuente efectiva | Modo | Respuesta | Grounding |
|---|---|---|---|---|
| Español: `¿Qué programas ofrece SPbU?` | FAQ KubSU | keyword | abstained | low, 0.25 |
| Inglés: `What programs does SPbU offer?` | fallback KubSU | fallback | abstained | low, 0.25 |
| Ruso: `Какие программы предлагает СПБГУ?` | fallback KubSU | fallback | abstained | low, 0.25 |
| Ruso técnico: `программы дополнительное образование онлайн курсы` | SPbU | keyword | template | high, 0.94 |

`sources_found=1` no equivale a un hit de SPbU: en las tres primeras consultas,
la fuente fue KubSU. Los campos top-level `confidence`, `grounding_level` y
`source_urls` devolvieron `None` o una lista vacía; la evidencia efectiva está en
`sources` y `grounding`.

### Rankings crudos por método

| Método solicitado | Español | Inglés | Ruso | Ruso técnico |
|---|---:|---:|---:|---:|
| keyword | SPbU ausente | SPbU ausente | SPbU ausente | SPbU rango 1, 0.5 |
| BM25 | SPbU ausente | SPbU ausente | SPbU rango 1, 1.0 | SPbU rango 1, 1.0 |
| dense | no ejecutado | no ejecutado | no ejecutado | no ejecutado |

Los scores BM25 están normalizados dentro de cada ranking y no deben compararse
directamente con el score keyword. No se calcularon métricas agregadas.

## Análisis de tokenización

El tokenizer Unicode avanzado produjo correctamente:

- español: `qué`, `programas`, `ofrece`, `spbu`;
- inglés: `what`, `programs`, `does`, `spbu`, `offer`;
- ruso: `какие`, `программы`, `предлагает`, `спбгу`.

Por tanto, no se observó un problema de segmentación entre alfabetos en BM25.
Sin embargo, su tabla de expansión no contiene equivalencias para
`programas/programs`, `ofrece/offer` ni `spbu/спбгу`.

El keyword legacy usa `query.lower().split()`, por lo que conserva puntuación:
`¿qué`, `spbu?`, `offer?` y `спбгу?`. Además, asigna 0.1 por coincidencia en
contenido y descarta scores que no superan 0.3. La consulta rusa natural solo
aporta suficientes coincidencias tras reformularla con cinco términos presentes
literalmente en la página.

## Estado de dense

Dense no pudo compararse con keyword. El objeto `DenseRetriever` se construyó,
pero `is_available()` devolvió `false`, no cargó embeddings y `_retrieve()` cayó
a keyword.

Versiones observadas:

- `torch 2.0.1+cpu`;
- `torchvision 0.15.2+cpu`;
- `sentence-transformers 5.6.0`;
- `transformers 4.57.6`;
- `numpy 1.24.3`.

La importación de `sentence_transformers` falló con
`AttributeError: module 'torch' has no attribute 'compiler'`. El archivo general
`requirements.txt` fija Torch 2.0.1, mientras
`backend/requirements-neural-eval.lock` fija el conjunto compatible con
`torch 2.4.1+cpu` y `torchvision 0.19.1+cpu`.

No se puede afirmar que dense funciona mejor que keyword en esta prueba porque
dense no produjo ningún ranking. El snapshot local existente no resuelve una
incompatibilidad del runtime.

## Causa raíz

1. **Desajuste léxico cross-lingual confirmado.** La fuente está en ruso; las
   consultas ES/EN no comparten términos de contenido ni aliases institucionales.
2. **Normalización insuficiente en keyword.** `split()` conserva puntuación y el
   umbral exige varias coincidencias literales.
3. **Expansión BM25 incompleta.** La tokenización Unicode funciona, pero faltan
   términos académicos y aliases `SPbU`/`СПбГУ`.
4. **Dense inoperativo en el entorno actual.** Hay una combinación incompatible
   de Torch con sentence-transformers/transformers y fallback silencioso.
5. **Granularidad de indexación como riesgo secundario.** Toda la página SPbU se
   indexó como un chunk. Esto puede diluir señales y causar truncación en modelos,
   pero no se probó como causa porque dense no llegó a ejecutarse.

## Soluciones propuestas

### Prioridad 0: hacer observable y restaurar dense

- Crear o usar un entorno neural separado con el lock completo, sin actualizar
  dependencias individualmente.
- Cargar el snapshot por ruta local con modo offline y verificar que se generan
  45 embeddings antes de aceptar el modo `dense`.
- Exponer `requested_mode`, `effective_mode` y `fallback_reason`; en diagnóstico,
  fallar explícitamente si dense no está disponible en vez de etiquetar el
  resultado fallback como una comparación dense.

### Prioridad 1: normalización y aliases

- Reutilizar el tokenizer Unicode de `retrieval/chunks.py` en keyword legacy.
- Mantener aliases de entidad en metadata: `SPbU`, `СПбГУ`,
  `Санкт-Петербургский государственный университет` y su nombre inglés.
- Añadir expansión retrieval-scoped para `programas/programs -> программы,
  образовательные программы` y `ofrece/offer -> предлагает`.
- Cubrir puntuación, mayúsculas, alfabeto y aliases con pruebas unitarias.

La expansión manual es una mitigación acotada, no una solución universal.

### Prioridad 2: recuperación cross-lingual

- Tras restaurar el runtime, probar embeddings multilingües sobre estas mismas
  consultas y registrar rankings crudos antes del grounding.
- Evaluar un modo híbrido que combine dense con BM25 y aliases, sin asumir que
  será superior hasta medirlo en un conjunto separado y revisado.
- Como fallback controlado, traducir o expandir la consulta hacia el idioma de la
  fuente, conservando consulta original, traducción y trazabilidad.

### Prioridad 3: indexación y validación

- Dividir páginas adquiridas por secciones semánticas y conservar idioma,
  encabezado, URL y aliases por chunk.
- Construir un pequeño conjunto de diagnóstico independiente con consultas
  equivalentes ES/EN/RU y juicios explícitos de fuente/chunk esperado.
- Separar ese conjunto de B3 y del benchmark exploratorio de 114 consultas.
- Comparar cobertura y calidad de ranking; no inferir superioridad estadística a
  partir de estas cuatro consultas.

## Artefactos

- `run_diagnosis.py`: ejecución reproducible, offline para modelos.
- `results.json`: tokens, entorno y rankings estructurados.
- `diagnosis.log`: traza completa de keyword, BM25 y dense solicitado.
- `end-to-end-keyword.log`: resultados de `search_and_generate` por idioma.
- `preflight.log`: controles Git iniciales.

No se ejecutaron B3, el conjunto de 114 consultas, bootstrap, reranking ni
adquisición de red durante este diagnóstico.