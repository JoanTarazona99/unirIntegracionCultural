@echo off
REM Setup Fase 2: Python 3.11 Environment with Transformers
REM Windows batch script

echo.
echo 🚀 Configurando Fase 2: Python 3.11 + Transformers...
echo.

REM 1. Check if venv311 exists
if not exist "venv311" (
    echo 📦 Creando venv Python 3.11...
    py -3.11 -m venv venv311
    echo ✅ venv311 creado
) else (
    echo ✅ venv311 ya existe
)

echo.
echo 📥 Instalando dependencias...

REM 2. Update pip
echo    Actualizando pip...
call venv311\Scripts\python.exe -m pip install -q --upgrade pip setuptools wheel

REM 3. Install main packages
echo    Instalando PyTorch + Transformers + SentenceTransformers...
call venv311\Scripts\python.exe -m pip install -q torch transformers sentence-transformers

REM 4. Install backend dependencies
echo    Instalando dependencias FastAPI + pytest...
call venv311\Scripts\python.exe -m pip install -q pytest pydantic requests fastapi uvicorn gtts

echo ✅ Dependencias instaladas
echo.

REM 5. Verify installation
echo 🔍 Verificando instalación...
call venv311\Scripts\python.exe -c "import torch; print(f'✅ torch: {torch.__version__}'); import transformers; print(f'✅ transformers: {transformers.__version__}'); from sentence_transformers import SentenceTransformer; print('✅ sentence-transformers: OK')" 2>&1

echo.
echo ✅ Fase 2 configurada correctamente
echo.
echo Próximos pasos:
echo 1. Ejecutar tests simple (Python 3.13):
echo    python backend/tests/test_grounding_simple.py
echo.
echo 2. Ejecutar tests mejorados (Python 3.11):
echo    venv311\Scripts\python.exe -m pytest backend/tests/test_grounding_improved.py -v
echo.
echo 3. Ver estado completo:
echo    python backend/tests/test_grounding_simple.py ^&^& venv311\Scripts\python.exe -m pytest backend/tests/test_grounding_improved.py -v
echo.
