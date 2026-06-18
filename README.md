# 🎓 Asistente Inteligente de Integración Cultural - KubGU

**Sistema de IA para soporte a estudiantes extranjeros en la Universidad Estatal de Kubán**

---

## ⚡ Inicio Rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Iniciar backend
python backend/main.py

# 3. Abrir en navegador
http://localhost:8000/frontend/
```

---

## 🌐 Interfaces Disponibles

| Interfaz | URL | Descripción |
|----------|-----|-------------|
| **Web Principal** | http://localhost:8000/frontend/ | Chat, búsqueda, perfil |
| **Dashboard** | http://localhost:8000/frontend/demo.html | Métricas y estado |
| **API Docs** | http://localhost:8000/docs | Swagger UI interactiva |
| **Health Check** | http://localhost:8000/health | Estado del servidor |

---

## 🚀 Características

- ✅ **200 frases rusas** contextualizadas para estudiantes
- ✅ **RAG inteligente** con búsqueda en 4 fuentes oficiales
- ✅ **Personalización** por país, tipo de visa, nivel de ruso
- ✅ **Chat multicanal:** Web + Telegram Bot
- ✅ **100% operacional** (29/29 tests end-to-end PASS)

---

## 📁 Estructura del Proyecto

```
proyectos/unir/
├── backend/
│   ├── main.py              ← API FastAPI (7 endpoints)
│   ├── enhanced_rag.py      ← Módulo RAG 
│   ├── personalization.py   ← Motor de personalización
│   └── phrase_manager.py    ← Gestor de frases
├── frontend/
│   ├── index.html           ← Web principal
│   └── demo.html            ← Dashboard demo
├── telegram_bot/
│   ├── bot.py               ← Bot real
│   └── bot_demo.py          ← Bot simulado
├── data/
│   ├── phrases/
│   │   └── complete_phrases.json    (200 frases)
│   └── rag_database.json    (Documentos oficiales)
│
├── requirements.txt
├── .env                     (Configuración)
├── docker-compose.yml       (Deployment)
└── Documentación
    ├── README.md     ← Estás aquí
    ├── QUICKSTART.md        (Guía paso a paso)
    └── INFORME_FINAL.md     (Reporte técnico)
```

---

## 🔧 Tecnologías

- **Backend:** FastAPI 0.104.1
- **Frontend:** Vue.js 3 (CDN)
- **Bot:** python-telegram-bot 20.3
- **Validación:** Pydantic 2.5.0
- **Server:** Uvicorn
- **Deployment:** Docker

---

## 📖 Documentación

- **[QUICKSTART.md](QUICKSTART.md)** - Guía de inicio paso a paso
- **[INFORME_FINAL.md](INFORME_FINAL.md)** - Documento técnico completo con arquitectura y resultados

---

## ✅ Estado del Sistema

```
Backend API:        ✅ Operacional (Puerto 8000)
Frontend Web:       ✅ Accesible
Dashboard:          ✅ Disponible
Bot Telegram:       ✅ Conectado
Tests E2E:          ✅ 29/29 PASS (100%)
Documentación:      ✅ Completa
```

---

## 🎯 Cómo Usar

### 1. Ver Dashboard (Rápido)
```
http://localhost:8000/frontend/demo.html
```

### 2. Usar Chat Web
```
http://localhost:8000/frontend/
- Crear perfil (país, visa, nivel ruso)
- Hacer preguntas
- Ver respuestas personalizadas
```

### 3. Explorar API
```
http://localhost:8000/docs
- Documentación Swagger
- Probar endpoints interactivamente
```

### 4. Bot Telegram (Real)
```bash
# Ya está corriendo en background
# Busca el bot con el token en .env
# Usa comandos: /start, /setup, /search, /phrases
```

---

## 📊 Métricas del Proyecto

| Métrica | Valor |
|---------|-------|
| Funcionalidades | 100% completadas |
| Tests E2E | 29/29 PASS |
| Frases | 200+ contextualizadas |
| Fuentes RAG | 4 (КубГУ, МВД, МФЦ, Госуслуги) |
| Endpoints API | 7 |
| Errores críticos | 0 |

---

## 🔌 API Endpoints

```
GET  /health                    Estado del servidor
GET  /api/phrases              Listado de 200 frases
POST /api/search               Búsqueda RAG
POST /api/chat                 Chat personalizado
POST /api/users/profile        Gestión de perfil
GET  /api/info                 Información del sistema
GET  /api/search/sources       Fuentes RAG disponibles
```

---

## 📞 Configuración

El archivo `.env` contiene:

```
TELEGRAM_BOT_TOKEN=<token_aqui>
API_PORT=8000
API_DEBUG=True
```

---

## 🚀 Deployment

### Con Docker
```bash
docker-compose up
```

### Manual
```bash
python backend/main.py
```

---

## 📝 Licencia

Proyecto académico - Universidad UNIR | 2026

---

**Estado:** ✅ Listo para Producción | **Versión:** 1.0 | **Última actualización:** Marzo 2026
