#!/bin/bash
# Setup Fase 2: Python 3.11 Environment with Transformers

set -e

echo "🚀 Configurando Fase 2: Python 3.11 + Transformers..."
echo ""

# 1. Crear venv si no existe
if [ ! -d "venv311" ]; then
    echo "📦 Creando venv Python 3.11..."
    py -3.11 -m venv venv311
    echo "✅ venv311 creado"
else
    echo "✅ venv311 ya existe"
fi

echo ""
echo "📥 Instalando dependencias..."

# 2. Actualizar pip
./venv311/Scripts/python.exe -m pip install -q --upgrade pip setuptools wheel

# 3. Instalar paquetes principales
echo "   Instalando PyTorch + Transformers + SentenceTransformers..."
./venv311/Scripts/python.exe -m pip install -q torch transformers sentence-transformers

# 4. Instalar dependencias del backend
echo "   Instalando dependencias FastAPI + pytest..."
./venv311/Scripts/python.exe -m pip install -q pytest pydantic requests fastapi uvicorn gtts

echo "✅ Dependencias instaladas"
echo ""

# 5. Verificar instalación
echo "🔍 Verificando instalación..."
./venv311/Scripts/python.exe -c "
import torch; print(f'✅ torch: {torch.__version__}')
import transformers; print(f'✅ transformers: {transformers.__version__}')
from sentence_transformers import SentenceTransformer; print('✅ sentence-transformers: OK')
" 2>&1

echo ""
echo "✅ Fase 2 configurada correctamente"
echo ""
echo "Próximos pasos:"
echo "1. Ejecutar tests simple (Python 3.13):"
echo "   python backend/tests/test_grounding_simple.py"
echo ""
echo "2. Ejecutar tests mejorados (Python 3.11):"
echo "   ./venv311/Scripts/python.exe -m pytest backend/tests/test_grounding_improved.py -v"
echo ""
echo "3. Ver estado completo:"
echo "   python backend/tests/test_grounding_simple.py && ./venv311/Scripts/python.exe -m pytest backend/tests/test_grounding_improved.py -v"
echo ""
