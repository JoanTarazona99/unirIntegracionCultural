# Guía para agentes — KubGU Assistant

## Propósito

Proyecto de asistencia a estudiantes extranjeros de la Universidad Estatal
de Kubán, con API FastAPI, interfaz web, bot de Telegram y componentes de
recuperación de información, personalización, traducción y audio.

## Reglas generales

Consulta [.github/copilot-instructions.md](.github/copilot-instructions.md)
antes de trabajar. Allí se mantienen las reglas generales del repositorio;
esta guía solo aporta orientación sobre su estructura.

## Mapa del repositorio

- [backend/main.py](backend/main.py): entrada FastAPI y montaje del frontend.
- [backend/app/](backend/app/): rutas API, modelos, dependencias, servicios
  y configuración.
- [backend/enhanced_rag.py](backend/enhanced_rag.py),
  [backend/retrieval/](backend/retrieval/) y
  [backend/trust/](backend/trust/): recuperación y fundamentación.
- [backend/procedural/](backend/procedural/) y
  [backend/eval/](backend/eval/): lógica procedimental y evaluación.
- [frontend/](frontend/): interfaz web y páginas auxiliares.
- [telegram_bot/](telegram_bot/): implementación y demostración del bot.
- [data/](data/): frases, documentos, registros y datos de evaluación.
- [docs/](docs/): protocolos y documentación técnica especializada.

## Localizar configuración y pruebas

- Contrasta [.env.example](.env.example) con
  [backend/app/config/settings.py](backend/app/config/settings.py)
  y con el código que consume cada variable.
- Consulta [requirements.txt](requirements.txt) y los manifiestos
  `requirements-*.txt` de [backend/](backend/) según la tarea.
- Localiza los tests en [backend/tests/](backend/tests/), su configuración
  en [backend/pytest.ini](backend/pytest.ini) y las fixtures compartidas
  en [backend/tests/conftest.py](backend/tests/conftest.py).
- Hay ejecutores adicionales, como
  [backend/test_e2e.py](backend/test_e2e.py), fuera del directorio de
  descubrimiento configurado para pytest.
- Consulta [.github/workflows/tests.yml](.github/workflows/tests.yml)
  para conocer la selección y el entorno declarados en CI; no representa
  necesariamente toda la suite.

## Verificación durante cada tarea

Los estados de servicios, resultados de tests, cantidades de fuentes o
endpoints, idiomas funcionales y compatibilidad deben verificarse durante
cada tarea antes de afirmarlos. Distingue lo inspeccionado de lo ejecutado
y registra el alcance y las limitaciones de la comprobación.

Las cifras de demostraciones y documentos históricos no acreditan el
estado actual. La existencia de una ruta, dependencia o configuración
no demuestra disponibilidad ni preparación para producción.
