# Instrucciones de Copilot para este repositorio

- Consulta la estructura, configuración, documentación y tests reales antes de asumir rutas, contratos o resultados.
- Antes de trabajar, registra la raíz, rama, `git status --short` y resultado de `git diff --check`. Preserva los cambios locales preexistentes. No uses `reset`, `restore`, `clean`, `stash`, `checkout` ni cambies de rama para resolver conflictos o limpiar el árbol.
- Selecciona y verifica el intérprete según la tarea y la configuración vigente. No asumas compatibilidad neuronal por la mera existencia del entorno. Para evaluaciones neuronales protegidas, sigue las restricciones del agente y protocolo específicos; no cambies sus entornos sin autorización.
- Ejecuta primero los tests focalizados y después la regresión pertinente. Un test con mocks, stubs o respuestas prefabricadas no demuestra inferencia real ni disponibilidad de servicios externos.
- No presentes consultas sintéticas ni revisadas con asistencia de IA como anotación humana, benchmark oficial o evidencia confirmatoria.
- Mantén separado B3 del conjunto exploratorio de 114 consultas. Conserva los indicadores de elegibilidad y procedencia; no conviertas resultados exploratorios en evaluación oficial.
- No describas un microbenchmark ni una medición warm como latencia end-to-end, cold start o rendimiento de traducción externa. Identifica método, entorno, estado de caché y límites de medición.
- Sustenta las afirmaciones procedimentales con fuentes y fragmentos trazables; no inventes hechos. Pide aclaración o abstente cuando la evidencia sea insuficiente o contradictoria.
- Trata como protegidos `data/eval/benchmark.jsonl`, `data/eval/benchmark.manifest.json`, `data/eval/benchmark*.jsonl`, `data/eval/*manifest*.json`, `data/eval/*diagnostics*.json` y todo `data/eval/results/`. Identifica las rutas concretas antes de cualquier operación y no las modifiques sin autorización explícita.
- No registres consultas, perfiles, respuestas, comentarios de usuarios ni secretos en claro salvo configuración y justificación explícitas. Usa datos sintéticos o anonimizados en fixtures y ejemplos versionados.
- Que un servicio sea local no lo convierte en una operación sin red. No realices llamadas a proveedores externos ni a servicios locales de inferencia sin que estén permitidas por la tarea y el flujo. En evaluación offline protegida, respeta las prohibiciones específicas.
- No hagas `stage`, commit ni push sin autorización explícita para esa operación. No afirmes que ejecutaste comandos, pruebas, modelos o mediciones si no ocurrió.
