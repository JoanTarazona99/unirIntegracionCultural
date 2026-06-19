# Asistente de Integración Cultural - KubGU

Sistema de soporte para estudiantes extranjeros en la Universidad Estatal de Kubán

---

## Inicio Rápido

```bash
# 1. Clonar y entrar al directorio
cd /path/to/project

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# 3. Instalar dependencias core
pip install -r requirements.txt

# 4. Iniciar backend
python -m uvicorn backend.main:app --reload --port 8000

# 5. Abrir en navegador
http://localhost:8000/frontend/
```

---

## Interfaces Disponibles

| Interfaz | URL | Descripción |
|----------|-----|-------------|
| Web Principal | http://localhost:8000/frontend/ | Chat, búsqueda, perfil |
| Dashboard | http://localhost:8000/frontend/demo.html | Métricas y estado |
| API Docs | http://localhost:8000/docs | Swagger UI interactiva |
| Health Check | http://localhost:8000/health | Estado del servidor |

---

## Características

- **Búsqueda RAG** con keyword fallback (no requiere ML)
- **200+ frases rusas** contextualizadas para estudiantes
- **Personalización** por país, tipo de visa, nivel de ruso
- **Chat multicanal:** Web + Telegram Bot
- **Traducción multiidioma** (opcional)
- **TTS/STT** (opcional)

---

## Estructura del Proyecto

```
project/
├── backend/
│   ├── main.py              ← API FastAPI
│   ├── enhanced_rag.py      ← Módulo RAG (keyword + semantic opcional)
│   ├── personalization.py   ← Memoria de conversación
│   ├── cache_module.py      ← Cache LRU con TTL
│   ├── translator.py        ← Traductor multiidioma
│   └── llm_module.py        ← Integración Ollama (opcional)
├── frontend/
│   ├── index.html           ← Web principal (Vue.js)
│   └── demo.html            ← Dashboard
├── telegram_bot/
│   └── bot.py               ← Bot de Telegram
├── data/
│   └── phrases/
│       └── base_phrases.json
├── requirements.txt
└── .env
```

---

## Datos

**Los documentos RAG son estáticos**, codificados en `enhanced_rag.py`:
- КубГУ (universidad)
- МВД РФ (migración)
- МФЦ (servicios públicos)
- Госуслуги (portal electrónico)
- FAQ (preguntas frecuentes)

---

## Dependencias

### Core (requeridas)
```
fastapi, uvicorn, pydantic, python-dotenv
numpy, python-telegram-bot, aiohttp, requests
```

### Opcionales (instalar según necesidad)

```bash
# Para traducción automática
pip install google-trans-new

# Para búsqueda semántica (mejor calidad)
pip install sentence-transformers torch

# Para text-to-speech
pip install gTTS

# Para speech-to-text
pip install SpeechRecognition

# Para LLM local (Ollama)
pip install ollama httpx
# Requiere: ollama server corriendo con modelo descargado
```

---

## API Endpoints

```
GET  /health                    Estado del servidor
GET  /api/status                 Estado de todos los módulos
GET  /api/phrases               Listado de frases
POST /api/search                Búsqueda RAG
POST /api/chat                  Chat personalizado
POST /api/tts                   Text-to-speech (requiere gTTS)
GET  /api/languages             Idiomas disponibles
```

---

## Configuración

Archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
API_PORT=8000
BACKEND_URL=http://localhost:8000
```

---

## Deployment

### Con Docker

```bash
docker-compose up
```

### Manual

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## Telegram Bot

```bash
# Configurar token en .env
export TELEGRAM_BOT_TOKEN="tu_token"

# Iniciar bot
python telegram_bot/bot.py
```

Comandos disponibles:
- `/start` - Iniciar
- `/ask <pregunta>` - Consultar al asistente
- `/status` - Estado del sistema
- `/lang <ru|es|en>` - Cambiar idioma
- `/phrases` - Ver frases útiles

---

## Licencia

Proyecto académico - Universidad UNIR | 2026
