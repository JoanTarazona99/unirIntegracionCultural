# ⚡ QUICK START CHECKLIST
## KubGU Assistant - 3 Semanas a Maestría

**Imprime esto o guárdalo en tu escritorio**

---

## 📌 HOY (30 de junio)

- [ ] Leer `INICIO_AQUI.md` (10 min)
- [ ] Ejecutar `make setup-dirs` (crear estructura)
- [ ] Ejecutar `make setup` (instalar deps)
- [ ] Ejecutar `make info` (verificar setup)
- [ ] Commit: `git commit -m "init: master-level refactoring setup"`

**Salida esperada:** Directorios creados, deps instaladas, `.env` local

---

## 🗓️ SPRINT 1: FUNDACIONES (Semana 1)

### Día 1 (Lunes)
- [ ] Crear `backend/app/config/settings.py` (Pydantic)
- [ ] Actualizar `requirements.txt` con versiones exactas
- [ ] Crear `.env` desde `.env.example`
- [ ] Test: `python -c "from app.config.settings import settings; print(settings)"`
- [ ] Commit: `"feat: Pydantic settings configuration"`

### Día 2 (Martes)
- [ ] Crear `backend/app/domain/exceptions.py` (excepciones custom)
- [ ] Crear `backend/app/domain/models.py` (Pydantic models)
- [ ] Test: `python -m mypy backend/app/domain/ --strict`
- [ ] Crear `mypy.ini` con strict mode
- [ ] Commit: `"feat: custom exceptions and Pydantic models"`

### Día 3 (Miércoles)
- [ ] Instalar structlog: `pip install structlog`
- [ ] Crear `backend/app/config/logging_config.py`
- [ ] Crear `backend/app/middleware/logging_middleware.py`
- [ ] Reemplazar print() con logger en 1-2 módulos clave
- [ ] Test: `python -m pytest tests/` (crear test básico)
- [ ] Commit: `"feat: structured logging with structlog"`

### Día 4 (Jueves)
- [ ] Crear `ARCHITECTURE.md` (diagrama ASCII de capas)
- [ ] Crear `DECISIONS.md` (primeras 2-3 ADRs)
- [ ] Documentar: FastAPI vs alternatives, Pydantic vs alternatives
- [ ] Commit: `"docs: architecture and decision records"`

### Día 5 (Viernes) - REVIEW
- [ ] Ejecutar `make type-check` (mypy strict debe pasar 100%)
- [ ] Ejecutar `make lint` (revisar warnings)
- [ ] Ejecutar `make test` (tests deben pasar)
- [ ] Verificar: 0 print() statements en backend/
- [ ] Commit: `"feat: Sprint 1 complete - foundations ready"`
- [ ] **Sprint 1 Salida:** ✅ Reproducible, tipado, loggeable

---

## 🗓️ SPRINT 2: MODULARIDAD (Semana 2)

### Día 6 (Lunes)
- [ ] Crear `backend/app/api/routes/` (chat.py, phrases.py, profile.py, health.py)
- [ ] Crear `backend/app/api/dependencies.py` (inyección de dependencias)
- [ ] Refactorizar rutas principales de main.py
- [ ] Test: `make run` y verificar que FastAPI docs funciona
- [ ] Commit: `"refactor: separate API routes and dependencies"`

### Día 7 (Martes)
- [ ] Migrar `enhanced_rag.py` → `backend/app/services/rag_service.py`
- [ ] Añadir type hints completos
- [ ] Test: Crear `tests/unit/test_rag_service.py` (mínimo 3 tests)
- [ ] Commit: `"refactor: migrate RAG service"`

### Día 8 (Miércoles)
- [ ] Migrar `translator.py` → `backend/app/services/translation_service.py`
- [ ] Migrar `phrase_manager.py` → `backend/app/services/phrase_service.py`
- [ ] Migrar `personalization.py` → `backend/app/services/personalization_service.py`
- [ ] Test: unit tests para cada servicio
- [ ] Commit: `"refactor: migrate remaining services"`

### Día 9 (Jueves)
- [ ] Eliminar: `main_minimal.py`, `debug_startup.py`, `demo_rag.py`, `rag_module.py`
- [ ] Verificar: `grep -r "from main_minimal import" .` → debe estar vacío
- [ ] Crear `tests/integration/test_chat_endpoint.py`
- [ ] Commit: `"cleanup: remove technical debt"`

### Día 10 (Viernes) - REVIEW
- [ ] Ejecutar `make test` (target >= 70%)
- [ ] Ejecutar `make lint` (mypy, pylint, black)
- [ ] Verificar: main.py es pequeño y limpio
- [ ] Commit: `"feat: Sprint 2 complete - modular architecture ready"`
- [ ] **Sprint 2 Salida:** ✅ Código modular, testeable, sin deuda técnica

---

## 🗓️ SPRINT 3: EVALUACIÓN (Semana 3)

### Día 11 (Lunes)
- [ ] Crear `data/ground_truth_queries.json` (50+ queries anotadas)
  - Incluir: id, query_text, language, intent, relevant_documents, highly_relevant
  - Mínimo 50 queries; ideal 100
- [ ] Ejemplo: q_001 "¿Dónde está МФЦ?" → relevant_documents: ["doc_042", "doc_043"]
- [ ] Commit: `"data: ground-truth dataset for RAG evaluation"`

### Día 12 (Martes)
- [ ] Crear `backend/scripts/evaluate_rag.py` (calcular métricas)
  - Implementar: precision@10, recall@10, MRR, NDCG
- [ ] Ejecutar: `python backend/scripts/evaluate_rag.py`
- [ ] Documentar resultados en `EVALUATION_RESULTS.md`
  - Tabla: mean_precision@10, mean_recall@10, mean_mrr, mean_ndcg
- [ ] Commit: `"feat: RAG evaluation with formal metrics"`

### Día 13 (Miércoles)
- [ ] Crear `locustfile.py` (load testing)
- [ ] Ejecutar: `locust -f locustfile.py --host=http://localhost:8000`
- [ ] Medir: latencia p50/p95/p99, throughput
- [ ] Documentar en `PERFORMANCE_REPORT.md`
- [ ] Commit: `"perf: benchmarking and load testing"`

### Día 14 (Jueves)
- [ ] Completar `DECISIONS.md` (5-7 ADRs total)
- [ ] Crear `REFERENCES.md` (citas académicas)
  - RAG: Lewis et al. 2020
  - Traducción: Vaswani et al. 2017
  - Evaluación: Papineni et al. 2002
  - Arquitectura: Martin 2017, Fowler & Lewis 2014
- [ ] Crear `API_CONTRACTS.md` (contratos explícitos para 4-5 endpoints)
- [ ] Commit: `"docs: academic documentation and references"`

### Día 15 (Viernes) - REVIEW Y CIERRE
- [ ] Ejecutar `make test` (verificar 70%+ coverage)
- [ ] Ejecutar `make evaluate-rag` (métricas visibles)
- [ ] Ejecutar `make benchmark` (latency data collected)
- [ ] Verificar todos los documentos: ARCHITECTURE.md, DECISIONS.md, EVALUATION.md, REFERENCES.md, API_CONTRACTS.md
- [ ] Commit: `"feat: Sprint 3 complete - master-level ready"`
- [ ] **Sprint 3 Salida:** ✅ Evaluable, documentado, defendible

---

## ✅ FINAL CHECKLIST

### Código
- [ ] mypy strict: 100% passing
- [ ] pytest: >= 70% coverage
- [ ] pylint: >= 8.0 score
- [ ] black: formatting applied
- [ ] No archivos residuales (main_minimal.py, demo_rag.py, etc)

### Documentación
- [ ] ARCHITECTURE.md (3 KB min)
- [ ] DECISIONS.md (5-7 ADRs, 10 KB min)
- [ ] EVALUATION.md (protocolo + resultados)
- [ ] REFERENCES.md (10+ referencias académicas)
- [ ] API_CONTRACTS.md (4+ endpoints documentados)

### Evaluación
- [ ] ground_truth_queries.json (50+ queries)
- [ ] RAG evaluation: precision@10, recall@10, MRR, NDCG
- [ ] Benchmarking: latency p50/p95/p99, throughput
- [ ] Performance report HTML (locust)

### Preparación para Defensa
- [ ] Demo funciona: `make run` + pregunta → respuesta
- [ ] Tests pasan: `make test` → 70%+ coverage
- [ ] Logs visibles: Estructurados en JSON
- [ ] Arquitectura explicable: Diagrama en ARCHITECTURE.md
- [ ] Decisiones defendibles: ADRs con contexto + consecuencias

---

## 🎯 COMANDOS DIARIOS

**Cada día:**
```bash
make help                 # Ver targets
make setup              # Setup si aún no hecho
make format             # Formatear código
make test               # Ejecutar tests
make lint               # Verificar calidad
```

**Al terminar Sprint:**
```bash
make clean              # Limpiar cachés
git add -A
git commit -m "feat: Sprint X complete"
git push
```

**Semana 3 (Evaluación):**
```bash
make evaluate-rag       # Ejecutar evaluación RAG
make benchmark          # Load testing
```

---

## 📊 TRACKING DE PROGRESO

```
Sprint 1: Fundaciones        [████████████████░░] 80% → Target: 100% viernes
Sprint 2: Modularidad        [████████░░░░░░░░░░] 40% → Target: 100% viernes
Sprint 3: Evaluación         [░░░░░░░░░░░░░░░░░░]  0% → Target: 100% viernes

Total:                        [████████░░░░░░░░░░] 33% → Target: 100% en 3 semanas
```

**Actualizar cada viernes**

---

## 🆘 SI TE ATASCAS

### Error: "No module named 'app'"
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -m pytest tests/
```

### Error: "mypy not found"
```bash
pip install mypy==1.7.1
```

### Error: "Import still using old module"
```bash
grep -r "from main_minimal import" backend/
grep -r "from demo_rag import" backend/
grep -r "from debug_startup import" backend/
# Reemplazar con nuevo import
```

### Error: Tests no ejecutan
```bash
cd backend
pip install pytest pytest-asyncio pytest-cov
python -m pytest tests/ -v
```

---

## 📞 RECURSOS

| Recurso | Link |
|---------|------|
| Documentación completa | `DIAGNOSTICO_Y_ROADMAP_MAESTRIA.md` |
| Plan día a día | `PLAN_EJECUCION_3_SEMANAS.md` |
| Índice | `INICIO_AQUI.md` |
| Este checklist | `QUICK_START.md` |
| Automatización | `Makefile` |
| Config | `.env.example` |

---

## ⏱️ GESTIÓN DE TIEMPO

**Total:** 60-80 horas en 3 semanas = ~20 horas/semana = ~4 horas/día

**Recomendado:**
- Lun-Mié: 4h implementación
- Jueves: 3h implementación + 1h documentación
- Viernes: 2h review + testing + 1h commit + 1h planning

---

## ✨ AL TERMINAR LOS 3 SPRINTS

Tendrás:
1. ✅ Código producción-ready (tipado, testeable, limpio)
2. ✅ Documentación académica (ARCHITECTURE, DECISIONS, REFERENCES)
3. ✅ Métricas formales (RAG evaluation, benchmarks)
4. ✅ Demo funcional en vivo
5. ✅ Preparado para defensa de maestría

**¡Éxito!** 🚀

---

*KubGU Assistant - Quick Start*  
*v1.0.0 | 2026-06-30*  
*Imprime esto o guárdalo en favoritos*
