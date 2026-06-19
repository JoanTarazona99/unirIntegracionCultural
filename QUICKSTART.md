# Guía de Inicio - Asistente de Integración Cultural KubGU

## Requisitos Previos

- Python 3.11+
- pip
- (Opcional) Token de Telegram Bot

---

## Instalación Rápida

### Paso 1: Entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows
```

### Paso 2: Instalar dependencias core

```bash
pip install -r requirements.txt
```

Esto instala:
- fastapi, uvicorn, pydantic (API)
- numpy (procesamiento)
- python-telegram-bot, aiohttp, requests (bot)

### Paso 3: Configurar variables de entorno

```bash
cp .env.example .env  # si existe
# o crear .env con:
echo "TELEGRAM_BOT_TOKEN=tu_token_aqui" > .env
echo "API_PORT=8000" >> .env
```

---

## Ejecutar el Backend

```bash
# Desde la raíz del proyecto
python -m uvicorn backend.main:app --reload --port 8000
```

El backend estará disponible en:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: http://localhost:8000/frontend/

---

## Ejecutar el Telegram Bot

```bash
# En otra terminal
python telegram_bot/bot.py
```

---

## Dependencias Opcionales

### Para traducción automática

```bash
pip install google-trans-new
```

### Para búsqueda semántica

```bash
pip install sentence-transformers torch
```

Nota: Requiere PyTorch (~2GB). El sistema funciona con keyword search si no se instala.

### Para text-to-speech

```bash
pip install gTTS
```

### Para LLM local (Ollama)

```bash
pip install ollama httpx

# Instalar Ollama server
# Descargar de: https://ollama.ai

# Descargar modelo
ollama pull llama3
```

---

## Verificar que Funciona

### Test 1: Health check

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "message": "Asistente de Integración Cultural activo",
  "features": {
    "semantic_search": "keyword_fallback",
    "tts": "available",
    "stt": "unavailable"
  }
}
```

### Test 2: Búsqueda RAG

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "registro migración", "user_id": "test", "language": "es"}'
```

### Test 3: Chat

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Dónde está el MFC?", "user_id": "test", "language": "es"}'
```

---

## Estructura de Archivos

```
project/
├── backend/
│   ├── main.py              # API FastAPI
│   ├── enhanced_rag.py      # RAG con keyword/semantic
│   ├── personalization.py   # Memoria de conversación
│   ├── cache_module.py      # Cache LRU
│   └── translator.py        # Traductor
├── frontend/
│   ├── index.html           # Interfaz Vue.js
│   └── demo.html            # Dashboard
├── telegram_bot/
│   └── bot.py               # Bot Telegram
├── data/
│   └── phrases/             # Frases JSON
├── requirements.txt         # Dependencias core
└── .env                     # Configuración
```

---

## Datos del Sistema

**Los documentos RAG están hardcodeados** en `enhanced_rag.py`:
- КубГУ - información universitaria
- МВД РФ - migración y visas
- МФЦ - servicios públicos
- Госуслуги - portal electrónico
- FAQ - preguntas frecuentes

**No se cargan de archivos externos ni base de datos.**

---

## Comandos Telegram Bot

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar bot |
| `/ask <pregunta>` | Consultar asistente |
| `/status` | Estado del sistema |
| `/lang <ru\|es\|en>` | Cambiar idioma |
| `/phrases` | Ver frases útiles |
| `/profile` | Ver perfil |
| `/setup` | Configurar perfil |

---

## Solución de Problemas

### "ModuleNotFoundError: No module named 'xxx'"

Dependencias opcionales no instaladas. Solución:
```bash
pip install -r requirements.txt  # reinstalar core
# o instalar la específica que falta
```

### "semantic_search": "keyword_fallback"

Normal - indica que sentence-transformers no está instalado. El sistema usa búsqueda por palabras clave.

### TTS no disponible

```bash
pip install gTTS
```

### Ollama no conecta

1. Verificar que Ollama server está corriendo: `ollama serve`
2. Verificar que hay un modelo: `ollama list`
3. Si no hay modelo: `ollama pull llama3`

---

## Docker (Alternativa)

```bash
docker-compose up -d
```

Servicios:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

---

**Proyecto:** Asistente de Integración Cultural KubGU  
**Universidad:** Kubán State University  
**Año:** 2026
