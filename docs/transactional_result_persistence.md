# Persistencia transaccional de resultados

## Causa del fallo reparado

La evaluación exploratoria completó el cálculo, pero su publicación se abortó
con `OSError: [Errno 9] Bad file descriptor`. Una validación auxiliar abrió un
artefacto en modo lectura e intentó ejecutar `os.fsync()` sobre ese descriptor.
Ese uso no es válido en Windows.

El módulo `backend/eval/transactional_result_persistence.py` separa la
durabilidad de escritura de la validación de contenido. No recupera ni publica
el staging diagnóstico de la ejecución fallida.

## Escritura y validación

Las escrituras JSON y CSV siguen este protocolo:

1. Crear un archivo temporal en el mismo directorio de staging que el destino.
2. Serializar el contenido con el archivo abierto en modo escritura.
3. Ejecutar `flush()` y después `os.fsync()` mientras el descriptor de escritura
   continúa abierto.
4. Cerrar el archivo.
5. Reemplazar el nombre de destino mediante `os.replace()`.

Si la serialización, `flush`, `fsync` o el reemplazo falla, el temporal se
elimina y el error se propaga. No se presenta un artefacto parcial como válido.

La validación abre artefactos existentes exclusivamente en modo lectura y los
parsea mediante `json.load()` o `csv.reader(strict=True)`. No llama a `flush()`
ni a `os.fsync()`. `validate_artifact_windows_safe()` hace explícito este
contrato y evita repetir el fallo `Bad file descriptor` observado en Windows.

## Protocolo de publicación

`publish_staging()` requiere que:

- el directorio de staging exista;
- el destino final no exista;
- el contrato declare exactamente seis nombres de artefacto únicos;
- staging contenga exactamente esos seis archivos, sin archivos adicionales ni
  subdirectorios;
- cada archivo tenga extensión JSON o CSV y pueda parsearse correctamente.

Solo después de superar todas las validaciones se ejecuta
`os.replace(staging, final)`. La función no borra directorios, no sobrescribe un
destino final preexistente y vuelve a comprobar su ausencia inmediatamente antes
de publicar. Ante cualquier error, propaga una excepción clara, conserva staging
y deja ausente el destino final.

Los seis artefactos corresponden al resultado JSON completo, resumen global
CSV, trazas por consulta CSV, desglose por idioma CSV, desglose por categoría CSV
y bootstrap JSON. Sus nombres concretos se proporcionan al publicar para que el
contrato sea reutilizable entre ejecuciones.

## Atomicidad en Windows

Los archivos temporales se cierran antes de `os.replace()`, requisito necesario
para evitar bloqueos de handles en Windows. El reemplazo de staging es atómico
dentro del mismo volumen según las garantías ofrecidas por el sistema de
archivos y Python. La comprobación de que el destino no existe protege el flujo
normal, pero no constituye un bloqueo entre procesos: un proceso externo podría
crear el destino entre la comprobación final y la llamada al sistema.

Este componente persiste y valida sintaxis de artefactos. No ejecuta retrieval,
modelos, reranking, métricas o bootstrap, y no interpreta resultados ni métricas.