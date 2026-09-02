# Comparacion diagnostica de keyword y dense para consultas SPbU

**Fecha de ejecucion:** 2026-09-02  
**Rama:** `feature/real-source-testing`  
**Commit evaluado:** `2fbdff0`  
**Estado del corpus:** `artifacts/real-source-tests/spbu-20260901/state`  
**Naturaleza del analisis:** diagnostico exploratorio, no benchmark oficial

## Objetivo y alcance

Este informe compara los rankings producidos por `keyword` y `dense` para tres
consultas dirigidas a Saint Petersburg State University (SPbU) e investiga por
que `dense` antepone una seccion de КубГУ a la fuente SPbU en la consulta rusa.

Se utilizaron las tres consultas predefinidas:

1. `¿Que programas ofrece SPbU?`
2. `What programs does SPbU offer?`
3. `программы образование СПБГУ курсы`

La ejecucion `keyword` uso `venv311/Scripts/python.exe`. La ejecucion `dense`
uso Python 3.13.9, PyTorch 2.12.0+cu126, Transformers 5.3.0 y
sentence-transformers 5.3.0. El modelo fue
`paraphrase-multilingual-MiniLM-L12-v2`, cargado desde el entorno local con
`HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`. La biblioteca produjo 45 chunks.

El campo `score` de las fuentes renderizadas fue `None` en ambos modos. Las
puntuaciones que aparecen a continuacion proceden de `relevance`. En `keyword`
son puntuaciones del buscador heredado; en `dense` son puntuaciones RRF. Estas
escalas no son directamente comparables.

## Comparacion de rankings

La siguiente tabla corresponde a la repeticion solicitada con
`language='es'`, `allow_external=False` y los tres primeros resultados. Un guion
indica que el pipeline devolvio menos de tres fuentes.

| Consulta | Modo | Rango 1 | Rango 2 | Rango 3 | Fuentes devueltas |
|---|---|---|---|---|---:|
| ES | keyword | SPbU (0.900000) | FAQ (0.300000) | - | 2 |
| ES | dense | SPbU (0.032787) | Стипендии (0.032258) | Мобильная связь (0.031746) | 5 |
| EN | keyword | SPbU (0.900000) | - | - | 1 |
| EN | dense | SPbU (0.032787) | Мобильная связь (0.032002) | Стипендии (0.032002) | 5 |
| RU | keyword | SPbU (0.400000) | - | - | 1 |
| RU | dense | КубГУ (0.016393) | Стипендии (0.016129) | SPbU (0.015873) | 5 |

Para la consulta rusa repetida con `language='ru'`, el ranking final mantuvo el
mismo top 3, pero el filtrado posterior del pipeline devolvio tres fuentes:

| Rango | Fuente | Titulo | Relevance RRF |
|---:|---|---|---:|
| 1 | КубГУ | Академическая информация | 0.0163934426 |
| 2 | Стипендии | Виды стипендий / Tipos de becas | 0.0161290323 |
| 3 | Saint Petersburg State University | Saint Petersburg State University | 0.0158730159 |

## Analisis del ranking ruso

### 1. El orden se origina en el coseno, no en RRF

La consulta rusa no activa expansion lexica: `query_expanded` es identica a
`query_original`. Por tanto, `dense` genera un solo ranking y RRF se limita a
transformar cada rango mediante `1 / (60 + rango)`; no altera el orden.

Los cosenos anteriores a RRF fueron:

| Rango | Fuente y titulo | Coseno |
|---:|---|---:|
| 1 | КубГУ - Академическая информация | 0.563097060 |
| 2 | Стипендии - Виды стипендий / Tipos de becas | 0.540232122 |
| 3 | SPbU - Saint Petersburg State University | 0.520817578 |
| 4 | Русский язык - Сертификат ТРКИ / Certificado TRKI | 0.487956166 |
| 5 | Русский язык - Examenes de idiomas internacionales | 0.474181056 |

La diferencia observada entre КубГУ y SPbU fue `0.042279482` de coseno.

### 2. El chunk SPbU se trunca de forma sustancial

`Chunk.text` concatena aliases, titulo y contenido. La construccion actual crea
un chunk por cada seccion aplanada, sin subdivision por longitud. El modelo
declaro `max_seq_length=128`.

| Chunk | Caracteres | Tokens del tokenizer | Tokens codificados | Truncado |
|---|---:|---:|---:|---|
| КубГУ - Академическая информация | 529 | 126 | 126 | No |
| SPbU - Saint Petersburg State University | 5,210 | 1,333 | 128 | Si |

El chunk КубГУ entra completo y concentra vocabulario academico relacionado con
estructura de cursos, grados, lengua de ensenanza y examenes. En SPbU solo se
codifica el inicio de una pagina principal extensa. La ventana conserva una
mencion temprana a `СПбГУ`, pero deja fuera el pasaje posterior
`Дополнительное образование и онлайн-курсы ... программы`, que combina la
entidad solicitada con los conceptos tematicos de la consulta.

### 3. Ablaciones de representacion

Se codificaron representaciones alternativas con el mismo modelo y la misma
consulta. Son pruebas diagnosticas, no resultados de produccion:

| Representacion | Coseno |
|---|---:|
| КубГУ, chunk completo | 0.563097060 |
| SPbU, chunk completo actual | 0.520817578 |
| SPbU, titulo solamente | 0.539589167 |
| SPbU, alias cirilico solamente | 0.518201649 |
| SPbU, extracto breve con entidad y contenido academico | 0.640285909 |
| `СПбГУ` antepuesto al chunk completo | 0.501192510 |

El extracto breve y tematicamente coherente supera a КубГУ en esta consulta.
Anteponer solo el alias no mejora el chunk completo, por lo que la evidencia no
respalda explicar el problema unicamente por ausencia de alias.

### 4. La senal de entidad es debil frente a la afinidad tematica

El registro de la fuente SPbU no contiene un campo `aliases`. Los aliases
derivados e indexados son `Saint Petersburg State University`,
`candidate_spbu-home-20260901` y `spbu`; no incluyen `СПбГУ` ni el nombre ruso
completo. Aun asi, el contenido truncado si contiene una mencion a `СПбГУ`.

Las consultas de ablacion mostraron:

| Consulta | Mejor КубГУ | Mejor SPbU |
|---|---:|---:|
| `СПбГУ` | rango 1, 0.535879374 | rango 10, 0.356127292 |
| `программы образование курсы` | rango 1, 0.504421949 | rango 6, 0.443027854 |
| `СПбГУ программы` | rango 5, 0.455016047 | rango 3, 0.455271184 |

Estos datos son compatibles con un retriever que prioriza similitud semantica
global y no impone una restriccion explicita de identidad institucional. No
demuestran por si solos una limitacion universal del modelo.

## Interpretacion

La explicacion mejor respaldada para `КубГУ > SPbU` es la combinacion de:

1. representacion monolitica de la pagina SPbU;
2. truncamiento de 1,333 a 128 tokens;
3. exclusion del pasaje SPbU academicamente mas relevante de la ventana;
4. alta densidad tematica del chunk corto de КубГУ;
5. ausencia de una restriccion lexical de entidad en dense puro.

La ausencia de aliases cirilicos es una debilidad adicional, pero las ablaciones
indican que agregar el alias sin corregir la segmentacion no basta.

## Recomendaciones de uso e implementacion

1. **Segmentar fuentes adquiridas antes del embedding.** Dividir paginas largas
   en fragmentos semanticamente coherentes que entren completos en el limite de
   128 tokens, preservando titulo, fuente y aliases en cada fragmento.
2. **Registrar aliases multilingues explicitos.** Para SPbU, incluir al menos
   `SPbU`, `СПбГУ`, `Saint Petersburg State University` y
   `Санкт-Петербургский государственный университет` en el registro fuente.
3. **Usar control lexical para consultas con entidad explicita.** En este corpus
   y estas tres consultas, keyword mantuvo SPbU en rango 1. Una estrategia
   hybrid o un boost verificable por alias puede reducir confusiones entre
   universidades; debe validarse antes de adoptarse.
4. **Exponer cosenos en la traza dense.** La traza actual conserva rangos y RRF,
   pero no los cosenos originales. Registrar `score_original` y
   `score_expanded` facilitaria diagnosticos sin ejecutar rutas internas.
5. **Crear una evaluacion focal separada.** Definir previamente qrels para un
   conjunto de consultas institucionales conflictivas (por ejemplo, SPbU frente
   a КубГУ) y medir Hit@k, MRR y nDCG por idioma antes de afirmar una mejora.

Como recomendacion operativa provisional, keyword es mas fiable para la consulta
rusa institucional exacta observada. Dense fue adecuado en posicion 1 para las
consultas ES y EN observadas. Esto no establece que keyword o dense sea el mejor
metodo en general.

## Limitaciones metodologicas

- Solo se analizaron tres consultas seleccionadas y un snapshot de corpus.
- No se realizaron juicios de relevancia independientes ni anotacion humana.
- No se ejecutaron comparaciones estadisticas ni paired bootstrap.
- Las puntuaciones keyword, coseno y RRF tienen significados y escalas distintas.
- Las ablaciones son evidencia exploratoria sobre este modelo, corpus y protocolo.
- El numero de fuentes finales depende tambien del filtrado posterior del pipeline
  y del parametro `language`; no equivale necesariamente al top-k bruto.
- Los resultados no deben generalizarse a usuarios reales, otros corpus u otros
  modelos.
- No se ejecutaron los benchmarks B3 ni 114 para este informe.

## Conclusion

La repeticion confirma que keyword situa SPbU primero en las tres consultas y
dense lo hace en ES y EN, pero no en RU. En la consulta rusa, КубГУ supera a
SPbU antes de RRF. La evidencia diagnostica atribuye principalmente esta
inversion a la segmentacion y al truncamiento del contenido SPbU, combinados con
la falta de control explicito de entidad en dense puro. La correccion prioritaria
es mejorar el chunking y despues validar aliases y fusion lexical mediante una
evaluacion focal con qrels predefinidos.