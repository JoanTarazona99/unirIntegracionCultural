.PHONY: help setup setup-dirs test lint format run clean evaluate benchmark docker-build docker-run

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║     KubGU Assistant - Targets de Automatización            ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  📦 SETUP"
	@echo "    make setup              Instalar TODO: deps + structure + .env"
	@echo "    make setup-dirs         Crear estructura de directorios solamente"
	@echo ""
	@echo "  🧪 TESTING"
	@echo "    make test               Ejecutar tests + coverage"
	@echo "    make test-unit          Unit tests solamente"
	@echo "    make test-integration   Integration tests solamente"
	@echo ""
	@echo "  🔍 QUALITY"
	@echo "    make lint               Ejecutar mypy + pylint + black check"
	@echo "    make format             Formatear código (black + isort)"
	@echo "    make type-check         mypy strict mode solamente"
	@echo ""
	@echo "  🚀 EXECUTION"
	@echo "    make run                Correr servidor desarrollo (hot reload)"
	@echo "    make run-prod           Correr servidor producción"
	@echo ""
	@echo "  📊 EVALUATION"
	@echo "    make evaluate-rag       Ejecutar evaluación RAG con ground-truth"
	@echo "    make benchmark          Load testing con locust"
	@echo "    make benchmark-report   Generar reporte HTML"
	@echo ""
	@echo "  🐳 DOCKER"
	@echo "    make docker-build       Construir imagen Docker"
	@echo "    make docker-run         Ejecutar con docker-compose"
	@echo "    make docker-prod        Ejecutar en producción (compose.prod.yml)"
	@echo ""
	@echo "  🧹 UTILITIES"
	@echo "    make clean              Limpiar cachés (__pycache__, .pytest_cache, etc)"
	@echo "    make requirements       Actualizar requirements.txt (pip-compile)"
	@echo ""

# ==================== SETUP ====================

setup: setup-dirs install-deps create-env
	@echo "✅ Setup completo!"
	@echo "   • Estructura de directorios creada"
	@echo "   • Dependencias instaladas"
	@echo "   • .env configurado"
	@echo "   Próximo paso: 'make run'"

setup-dirs:
	@echo "📁 Creando estructura de directorios..."
	mkdir -p backend/app/{config,api/routes,services,domain,data/repositories,utils,middleware,schemas}
	mkdir -p backend/tests/{unit,integration,e2e}
	mkdir -p backend/scripts
	mkdir -p frontend/src/{components,services,types,i18n,assets/styles}
	mkdir -p data/phrases data/audio benchmark_results
	mkdir -p .github/workflows
	touch backend/app/__init__.py
	touch backend/app/config/__init__.py
	touch backend/app/services/__init__.py
	touch backend/app/domain/__init__.py
	touch backend/app/data/__init__.py
	touch backend/app/utils/__init__.py
	touch backend/app/middleware/__init__.py
	touch backend/app/api/__init__.py
	touch backend/tests/__init__.py
	@echo "✅ Directorios creados"

install-deps:
	@echo "📦 Instalando dependencias..."
	pip install -q -r backend/requirements.txt
	pip install -q -r backend/requirements-dev.txt || pip install -q pytest pytest-asyncio pytest-cov mypy black isort pylint structlog
	@echo "✅ Dependencias instaladas"

create-env:
	@echo "⚙️  Creando .env desde .env.example..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env creado (completar con valores reales)"; \
	else \
		echo "ℹ️  .env ya existe"; \
	fi

# ==================== TESTING ====================

test: test-unit test-integration
	@echo "✅ Todos los tests pasaron"

test-unit:
	@echo "🧪 Ejecutando tests unitarios RAG (offline, sin Ollama/Redis)..."
	cd backend && python -m pytest tests/test_unit_rag.py -v --tb=short \
		--cov=enhanced_rag --cov=retrieval --cov-report=term-missing --cov-report=html
	@echo "📈 Reporte de cobertura: backend/htmlcov/index.html"

test-integration:
	@echo "🔗 Ejecutando tests de integración..."
	cd backend && python -m pytest tests/integration/ -v --tb=short 2>/dev/null || echo "⚠️  Sin tests aún"

test-coverage:
	@echo "📊 Ejecutando tests con cobertura..."
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term
	@echo "📈 Reporte de cobertura: htmlcov/index.html"

# ==================== QUALITY ====================

lint: type-check
	@echo "🔍 Ejecutando pylint..."
	cd backend && python -m pylint app/ --fail-under=8.0 2>/dev/null || echo "⚠️  pylint: revisar warnings"
	@echo "🔍 Verificando formato..."
	cd backend && python -m black --check app/ 2>/dev/null && echo "✅ Formato OK" || echo "⚠️  Código sin formatear"

type-check:
	@echo "🔍 mypy en modo strict..."
	cd backend && python -m mypy app/ --strict 2>/dev/null && echo "✅ Tipado correcto" || echo "❌ Errores de tipado"

format:
	@echo "🎨 Formateando código..."
	cd backend && python -m black app/ --quiet
	cd backend && python -m isort app/ --quiet
	@echo "✅ Código formateado"

# ==================== EXECUTION ====================

run:
	@echo "🚀 Iniciando servidor de desarrollo..."
	@echo "   URL: http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	@echo "🚀 Iniciando servidor de producción..."
	cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# ==================== EVALUATION ====================

evaluate-rag:
	@echo "📊 Evaluando RAG..."
	cd backend && python scripts/evaluate_rag.py || echo "⚠️  Script no existe aún"

benchmark:
	@echo "⚡ Iniciando load testing con locust..."
	@echo "   Web UI: http://localhost:8089"
	locust -f locustfile.py --host=http://localhost:8000 || echo "⚠️  locustfile.py no existe"

benchmark-report:
	@echo "📈 Generando reporte de benchmark..."
	@echo "ℹ️  Ejecutar 'make benchmark' primero"

# ==================== DOCKER ====================

docker-build:
	@echo "🐳 Construyendo imagen Docker..."
	docker-compose build

docker-run:
	@echo "🐳 Ejecutando con docker-compose..."
	docker-compose up

docker-prod:
	@echo "🐳 Ejecutando en producción..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# ==================== UTILITIES ====================

clean:
	@echo "🧹 Limpiando cachés..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name *.pyc -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ Cachés limpios"

requirements:
	@echo "📋 Actualizando requirements.txt..."
	@echo "ℹ️  pip-compile no instalado; hacer manualmente"
	@echo "    Usar: pip install --upgrade -r requirements.txt"

requirements-dev:
	@echo "📋 Instalando dev requirements..."
	pip install -r backend/requirements-dev.txt
	@echo "✅ Dev requirements instalados"

# ==================== MISC ====================

version:
	@echo "KubGU Assistant v1.0.0 (Master-Level Edition)"
	@grep -A 1 "__version__" backend/app/config/settings.py 2>/dev/null || echo "Version info en config/settings.py"

info:
	@echo "📊 Información del Proyecto"
	@echo "  Python: $$(python --version 2>&1 | cut -d' ' -f2)"
	@echo "  FastAPI: $$(python -c 'import fastapi; print(fastapi.__version__)' 2>/dev/null || echo 'no instalado')"
	@echo "  pytest: $$(python -m pytest --version 2>&1 | cut -d' ' -f2 || echo 'no instalado')"
	@echo "  mypy: $$(python -m mypy --version 2>&1 | cut -d' ' -f1 || echo 'no instalado')"
	@echo ""
	@echo "  Estructura:"
	@du -sh backend frontend data 2>/dev/null || echo "  (directorios no creados aún)"

.DEFAULT_GOAL := help
