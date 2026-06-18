# Guía de Inicio - Asistente de Integración Cultural KubGU

## 📋 Requisitos Previos

- Python 3.9+
- pip / conda
- Docker (opcional)
- Token de Telegram Bot (opcional)

## 🚀 Instalación Rápida

### Opción 1: Instalación local (Windows)

```bash
cd c:\xampp\htdocs\proyectos\unir
install.bat
```

### Opción 2: Instalación manual

```bash
# Crear ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
```

## 🎯 Ejecutar Componentes

### 1️⃣ Generar frases (200 ejemplos)

```bash
cd data/phrases
python generate_phrases.py
```

### 2️⃣ Iniciar Backend FastAPI

```bash
cd backend
uvicorn main:app --reload
```

Backend disponible en: `http://localhost:8000`
Documentación: `http://localhost:8000/docs`

### 3️⃣ Iniciar Interfaz Web

```bash
# Navegar a:
file:///c:/xampp/htdocs/proyectos/unir/frontend/index.html
```

O con un servidor HTTP:
```bash
python -m http.server 8080 --bind 127.0.0.1 --directory frontend
# Acceder a: http://localhost:8080
```

### 4️⃣ Iniciar Telegram Bot

```bash
# Primero configurar TELEGRAM_BOT_TOKEN en .env
cd telegram_bot
python bot.py
```

## 🐳 Opción Docker

```bash
docker-compose up -d
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432

## 📚 Estructura de Archivos

```
unir/
├── backend/
│   ├── main.py                 # API FastAPI principal
│   ├── phrase_manager.py       # Gestor de frases
│   ├── rag_module.py           # Módulo RAG/búsqueda
│   ├── audio_module.py         # TTS/STT
│   └── personalization.py      # Personalización
├── frontend/
│   └── index.html              # Interfaz Vue.js
├── telegram_bot/
│   └── bot.py                  # Bot de Telegram
├── data/
│   ├── phrases/
│   │   ├── base_phrases.json
│   │   ├── complete_phrases.json     # 200 frases completas
│   │   └── generate_phrases.py
│   ├── documents/               # Documentos oficiales
│   ├── vectors/                # Índices FAISS
│   └── audio/                  # Archivos de audio TTS
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🧪 Pruebas

### Test Backend

```bash
# Ver salud del API
curl http://localhost:8000/health

# Obtener frases
curl http://localhost:8000/api/phrases?category=Regristración%20y%20migración

# Crear perfil
curl -X POST http://localhost:8000/api/users/profile \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "name": "Juan",
    "country": "Vietnam",
    "visa_type": "student",
    "academic_level": "bachelor",
    "housing_type": "dorm",
    "russian_level": "A1"
  }'
```

### Test Frontend

1. Abre `frontend/index.html` en el navegador
2. Rellena tu perfil (país, visa, nivel de ruso)
3. Prueba buscar frases por categoría
4. Envía mensajes al chat

### Test Telegram Bot

1. Crea un bot en @BotFather (Telegram)
2. Copia el token a `.env`
3. Ejecuta `python telegram_bot/bot.py`
4. Busca tu bot en Telegram
5. Usa `/start`, `/help`, `/setup`, etc.

## 🔧 Configuración Avanzada

### Cambiar modelo TTS

En `audio_module.py`:
```python
# Cambiar de Coqui a pyttsx3 o viceversa
self.engine = "pyttsx3"
```

### Conectar base de datos real

En `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/kubgu
```

### Mejorar búsqueda RAG

En `rag_module.py`, reemplazar embeddings ficticios con Sentence-BERT:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
query_embedding = model.encode(query)
```

## 📊 Componentes Implementados

✅ **Estructura del proyecto** - Carpetas y archivos organizados
✅ **Base de frases** - 20-200 frases contextualizadas
✅ **Backend FastAPI** - API completo con rutas principales
✅ **Gestor de frases** - Búsqueda por categoría, contexto
✅ **Módulo RAG** - Integración FAISS y búsqueda de documentos
✅ **TTS/STT** - Síntesis y reconocimiento de voz
✅ **Personalización** - Perfil específico por usuario
✅ **Frontend Vue.js** - Interfaz interactiva
✅ **Telegram Bot** - Bot funcional con comandos
✅ **Docker** - Despliegue containerizado
✅ **Documentación** - Guías de instalación y uso

## 🎓 Próximos Pasos

1. **Expandir frases** - Generar 200 verdaleras
2. **Conectar LLM** - Integrar modelo de generación real
3. **Mejorar RAG** - Agregar más documentos oficiales
4. **Base de datos** - Conectar PostgreSQL real
5. **Testing** - Pruebas con estudiantes reales
6. **Deploy** - Publicar en servidor público

## 📞 Soporte

Para dudas o problemas:
- Revisa `README.md`
- Consulta las issues del proyecto
- Contacta al equipo de desarrollo

---

**Proyecto:** Asistente Inteligente de Integración Cultural
**Universidad:** Kúban State University (KubGU)
**Estudiante:** Tárásona Fernández Jóan Carlos
**Período:** 16.02.2026 - 02.03.2026
