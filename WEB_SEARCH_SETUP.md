# Configuración para Web Search + Google AI Integration

## Variables de Entorno Recomendadas

### Opción 1: GRATIS - Sin API Keys (Funciona igual)
```bash
# Solo usa:
# - Wikipedia API (libre)
# - DuckDuckGo (libre)
# - Fuentes oficiales (КубГУ, МВД, МФЦ, Госуслуги)

# NO requiere configuración adicional
```

### Opción 2: RECOMENDADO - Google Gemini AI
```bash
# Obtener API key en: https://ai.google.dev/

GOOGLE_AI_API_KEY=tu_gemini_api_key_aqui

# Esto habilita:
# ✅ Búsqueda inteligente con IA
# ✅ Respuestas contextuales mejoradas
# ✅ Extracción automática de información relevante
```

### Opción 3: AVANZADO - Google Custom Search
```bash
# Obtener en: https://cse.google.com/

GOOGLE_CUSTOM_SEARCH_API_KEY=tu_api_key
GOOGLE_CUSTOM_SEARCH_CX=tu_cx_id

# Esto habilita:
# ✅ Búsqueda refinada en sitios específicos
# ✅ Ranking de resultados personalizado
```

---

## Archivo .env (Ejemplo)

```bash
# === APP CONFIG ===
APP_NAME=KubGU Assistant
APP_VERSION=0.5.0
DEBUG=false
ENVIRONMENT=production

# === WEB SEARCH (Opcional - elige uno o ninguno) ===

# Google Gemini AI (RECOMENDADO - más inteligente)
GOOGLE_AI_API_KEY=

# O Google Custom Search (más preciso)
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=

# === OTHER SETTINGS ===
DATABASE_URL=sqlite:///./data/kubgu.db
ENABLE_DATABASE=true
```

---

## Dónde Obtener API Keys

### 1. Google Gemini AI (Recomendado)
```
1. Ir a: https://ai.google.dev/
2. Hacer click en "Get API Key"
3. Crear nuevo proyecto (o usar existente)
4. Copiar la API key
5. Pegar en GOOGLE_AI_API_KEY=
```

**Ventajas:**
- ✅ Gratis para uso educativo
- ✅ Búsqueda muy inteligente
- ✅ Comprensión contextual
- ✅ Mejor en español/ruso

### 2. Google Custom Search (Alternativa)
```
1. Ir a: https://cse.google.com/
2. Crear nuevo motor de búsqueda
3. Ir a Configuración → Credenciales
4. Crear API key
5. Copiar values a .env
```

---

## Cómo Probar

### 1. Configurar (opcional)
```bash
# Editar .env
GOOGLE_AI_API_KEY=tu_key_aqui
```

### 2. Reiniciar backend
```bash
cd backend
python main.py
```

### 3. Ir a http://localhost:8000/frontend/

### 4. Hacer preguntas que causen bajo grounding
```
Ejemplos:
- "¿Cómo obtengo permiso de trabajo?"
- "¿Dónde registro mi vehículo?"
- "¿Cómo abro una cuenta bancaria?"
- "¿Qué documentos necesito para..."
```

### 5. Ver logs
```
[KnowledgeAcquisition] Detected low grounding: 0.25
[KnowledgeAcquisition] Searching with Google AI...
[KnowledgeAcquisition] ✅ Found Google AI result: ...
```

---

## Fallback Chain (Sin hacer nada)

Si NO configuras API keys, el sistema sigue funcionando:

```
Query → Bajo grounding?
    ↓
    ├─ Try Google Gemini (SI KEY) → ✅ Exitoso
    ├─ Try Wikipedia API → ✅ Exitoso (generalmente)
    ├─ Try DuckDuckGo → ✅ Exitoso (siempre)
    ├─ Try Official Sources (КубГУ, МВД) → ✅ Exitoso
    └─ Return original answer → Fallback
```

---

## Monitoring

### Ver intentos de Knowledge Acquisition
```bash
# Archivo de auditoría:
data/acquisition_log.json

# Contiene:
{
  "timestamp": "2026-07-06T...",
  "query": "¿Cómo me matriculo?",
  "info_type": "matriculation",
  "source_url": "https://...",
  "success": true/false
}
```

### Ver documentos ingiridos
```bash
# Archivo de base de datos RAG:
data/rag_database.json

# Sección nueva: "ingested_documents"
```

---

## Performance

- **Búsqueda local (cache hit):** ~2ms
- **Búsqueda RAG (sin web):** ~40ms
- **Búsqueda web (con ingesta):** ~2-5s (1x, luego cache)

---

## Limitaciones Conocidas

⚠️ Wikipedia bloqueado en algunos entornos → Fallback automático a DuckDuckGo

⚠️ Si no tienes API keys Google → Usa fallback a fuentes oficiales

⚠️ Ingesta lenta de documentos muy grandes → Se limita a 5000 caracteres

---

## Soporte

Si tienes preguntas:
1. Revisar `data/acquisition_log.json` para debugging
2. Verificar que .env está configurado correctamente
3. Revisar logs del backend: `python main.py`

---

**Setup Web Search** | Knowledge Acquisition Integration | v0.5.0
