#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generación de diagramas de arquitectura profesionales para la tesis.
Figuras 1-3: Arquitectura general, RAG, Pipeline de voz
"""
import os
import subprocess
import tempfile
from pathlib import Path

OUT_DIR = Path(__file__).parent

# ============================================================================
# FIGURA 1: ARQUITECTURA GENERAL DEL SISTEMA
# ============================================================================
DIAGRAM_1 = """
graph TB
    subgraph "🎯 Interfaz de Usuario"
        WEB["🌐 Web Frontend<br/>Vue.js + HTML5"]
        TG["🤖 Telegram Bot<br/>python-telegram-bot"]
    end
    
    subgraph "⚙️ Backend API FastAPI"
        API["REST API<br/>(puerto 8000)"]
        AUTH["Autenticación<br/>& Gestión de Sesiones"]
        CONV["Módulo de Conversación"]
    end
    
    subgraph "🧠 Módulos de IA"
        LLM["LLM: Qwen2.5<br/>7B-Instruct-Q4_K_M<br/>(Ollama local)"]
        RAG["RAG Híbrido<br/>BM25 + Embeddings"]
        PERS["Personalización<br/>(perfil del usuario)"]
    end
    
    subgraph "🔊 Módulos Multimedia"
        STT["STT: Whisper<br/>(reconocimiento)"]
        TTS["TTS: Web Speech API<br/>+ Backend"]
        TRANS["Traductor<br/>(ES↔RU↔EN↔)"]
    end
    
    subgraph "📚 Datos"
        KB["Knowledge Base<br/>официales<br/>КубГУ, МВД, МФЦ"]
        CACHE["Redis Cache<br/>(respuestas)"]
    end
    
    WEB --> API
    TG --> API
    API --> AUTH
    API --> CONV
    CONV --> LLM
    CONV --> RAG
    CONV --> PERS
    RAG --> KB
    RAG --> CACHE
    CONV --> STT
    CONV --> TTS
    CONV --> TRANS
    LLM -.->|Ollama REST| CACHE
    
    style API fill:#e8f4f8,stroke:#0066cc,stroke-width:2px
    style LLM fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style RAG fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style KB fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
"""

# ============================================================================
# FIGURA 2: ESQUEMA DEL MÓDULO RAG (RECUPERACIÓN Y GENERACIÓN)
# ============================================================================
DIAGRAM_2 = """
graph LR
    Q["🔍 Consulta del Usuario"]
    
    subgraph "📊 Recuperación"
        PREPROC["Preprocesamiento<br/>Normalización"]
        EXPAND["Expansión de Consulta<br/>Sinónimos RU/ES/EN"]
        
        subgraph "🔎 Búsqueda Paralela"
            BM25["BM25<br/>(léxico)"]
            DENSE["Dense Search<br/>paraphrase-multilingual-<br/>MiniLM-L12-v2<br/>(384-dim)"]
        end
        
        RRF["RRF Fusion<br/>(rank combination)"]
        RERANK["Cross-Encoder<br/>Reranking<br/>(precisión)"]
    end
    
    subgraph "🎯 Generación"
        CONTEXT["Preparar Contexto<br/>+ Perfil Usuario"]
        PROMPT["Construcción de Prompt<br/>(inyección perfil)"]
        GEN["Generación LLM<br/>Qwen2.5"]
        FAITH["Control Faithfulness<br/>(umbral: 0.35)"]
    end
    
    subgraph "📋 Salida"
        RESPONSE["Respuesta en RU"]
        TRANS_OUT["Traducción<br/>a idioma usuario"]
        FINAL["Respuesta + Fuentes<br/>+ Confianza"]
    end
    
    Q --> PREPROC
    PREPROC --> EXPAND
    EXPAND --> BM25
    EXPAND --> DENSE
    BM25 --> RRF
    DENSE --> RRF
    RRF --> RERANK
    RERANK --> CONTEXT
    CONTEXT --> PROMPT
    PROMPT --> GEN
    GEN --> FAITH
    FAITH -->|Si confianza > 0.35| RESPONSE
    FAITH -->|Si confianza ≤ 0.35| FINAL
    RESPONSE --> TRANS_OUT
    TRANS_OUT --> FINAL
    
    style RAG fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style RERANK fill:#ffe0b2,stroke:#ff9800,stroke-width:2px
    style FAITH fill:#ffebee,stroke:#f44336,stroke-width:2px
"""

# ============================================================================
# FIGURA 3: PIPELINE DE INTERACCIÓN POR VOZ (STT → LLM → TTS)
# ============================================================================
DIAGRAM_3 = """
graph TB
    subgraph "🎤 Entrada de Voz"
        USER["Usuario dice:<br/>¿Dónde está...?"]
        MIC["Captura de Audio<br/>(micrófono)"]
    end
    
    subgraph "🔊 STT (Speech-to-Text)"
        WHISPER["Whisper<br/>(OpenAI)<br/>Soporte multilingüe"]
        NORM["Normalización de Texto"]
    end
    
    subgraph "🧠 Procesamiento (RAG)"
        SEARCH["Búsqueda RAG Híbrida<br/>(ver Figura 2)"]
        CONTEXT["Contexto del usuario"]
        LLM["Generación LLM<br/>Qwen2.5"]
    end
    
    subgraph "🌐 Traducción"
        RUSO["Respuesta en RU"]
        DETECT["Detectar idioma usuario"]
        TRADUCIR["Traducción<br/>(Google Translate API)"]
    end
    
    subgraph "🔊 TTS (Text-to-Speech)"
        PRIMARY["Nivel 1:<br/>Web Speech API<br/>(browser nativo)"]
        FALLBACK["Nivel 2 Fallback:<br/>gTTS Backend<br/>(si falla API)"]
        AUDIO["Síntesis de Audio"]
    end
    
    subgraph "🎵 Salida de Voz"
        PLAY["Reproducción:<br/>altavoces del dispositivo"]
        TEXT["Transcripción visible<br/>en pantalla"]
    end
    
    USER --> MIC
    MIC --> WHISPER
    WHISPER --> NORM
    NORM --> SEARCH
    CONTEXT --> SEARCH
    SEARCH --> LLM
    LLM --> RUSO
    RUSO --> DETECT
    DETECT -->|Idioma ≠ RU| TRADUCIR
    DETECT -->|Idioma = RU| PRIMARY
    TRADUCIR --> PRIMARY
    PRIMARY -->|Funciona| AUDIO
    PRIMARY -->|Falla| FALLBACK
    FALLBACK --> AUDIO
    AUDIO --> PLAY
    PLAY --> TEXT
    
    style WHISPER fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style LLM fill:#e8f4f8,stroke:#0066cc,stroke-width:2px
    style PRIMARY fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style FALLBACK fill:#ffebee,stroke:#f44336,stroke-width:2px
"""

def diagram_to_mermaid_file(diagram_code, filename):
    """Guardar código Mermaid en archivo."""
    filepath = OUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(diagram_code)
    print(f"✓ Guardado: {filename}")
    return filepath

def mermaid_to_png(mermaid_code, output_png):
    """Convertir Mermaid a PNG usando mermaid-cli (requiere instalación)."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False, encoding='utf-8') as f:
            f.write(mermaid_code)
            mmd_file = f.name
        
        # Intentar usar mmdc (mermaid-cli)
        subprocess.run(
            ['mmdc', '-i', mmd_file, '-o', output_png],
            check=True, capture_output=True
        )
        os.unlink(mmd_file)
        print(f"✓ PNG generado: {output_png}")
        return True
    except FileNotFoundError:
        print(f"⚠️  mmdc no encontrado. Instalalo con: npm install -g @mermaid-js/mermaid-cli")
        print(f"    Alternativa: usar https://mermaid.live para convertir a PNG manualmente")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generando PNG: {e}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("Generando diagramas de arquitectura para tesis (Figuras 1-3)")
    print("=" * 70)
    
    # Guardar archivos Mermaid
    diagram_to_mermaid_file(DIAGRAM_1, "figura_1_arquitectura.mmd")
    diagram_to_mermaid_file(DIAGRAM_2, "figura_2_rag.mmd")
    diagram_to_mermaid_file(DIAGRAM_3, "figura_3_voz.mmd")
    
    print("\n" + "=" * 70)
    print("SIGUIENTES PASOS para convertir a PNG:")
    print("=" * 70)
    print("\nOpción A (automática - si tienes mmdc instalado):")
    print("  $ mmdc -i figura_1_arquitectura.mmd -o fig_arquitectura.png")
    print("  $ mmdc -i figura_2_rag.mmd -o fig_rag_detalle.png")
    print("  $ mmdc -i figura_3_voz.mmd -o fig_voz.png")
    
    print("\nOpción B (manual - usando mermaid.live):")
    print("  1. Ir a https://mermaid.live")
    print("  2. Copiar contenido de .mmd files")
    print("  3. Exportar a PNG (botón download)")
    print("  4. Guardar como fig_arquitectura.png, fig_rag_detalle.png, fig_voz.png")
    
    print("\nOpción C (conversión en línea):")
    print("  $ pip install mermaid (if available)")
    print("  $ python -c 'from mermaid import mermaid; mermaid.render(...)'")
    
    print("\n✓ Archivos Mermaid listos en:", OUT_DIR)
