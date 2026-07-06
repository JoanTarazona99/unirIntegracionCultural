#!/bin/bash
# Script de instalación para Git Bash (Windows)
# Asistente de Integración Cultural - KubGU

echo "========================================"
echo "Instalando Asistente de Integración Cultural"
echo "========================================"
echo

# Crear ambiente virtual
echo "[1/3] Creando ambiente virtual..."
python -m venv venv

# Activar ambiente virtual
echo "[2/3] Activando ambiente virtual..."
source venv/Scripts/activate

# Instalar dependencias
echo "[3/3] Instalando dependencias..."
pip install --upgrade pip --quiet
if [ -f requirements.txt ]; then
    pip install -r requirements.txt --quiet
else
    echo "⚠️  requirements.txt no encontrado; instalando dependencias mínimas."
    pip install fastapi uvicorn pydantic python-dotenv --quiet
fi

echo
echo "========================================"
echo "✅ Instalación completada!"
echo "========================================"
echo
echo "Para activar el ambiente en el futuro usa:"
echo "  source venv/Scripts/activate"
echo
echo "Próximos pasos:"
echo "1. Generar frases: python data/phrases/generate_phrases.py"
echo "2. Iniciar backend: python backend/main.py"
echo "3. Abrir frontend: start frontend/index.html"
echo
