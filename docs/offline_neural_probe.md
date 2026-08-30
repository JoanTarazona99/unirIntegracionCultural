# Offline neural probe

## Purpose

`backend/eval/offline_neural_probe.py` verifies that the three neural components
required by retrieval evaluation can load and perform minimal finite inference
from local snapshots. It does not load a benchmark or corpus, run retrieval,
compute metrics, or persist evaluation artifacts.

## Process isolation

The parent starts one clean Python subprocess for each component: `dense`,
`rerank_multilingual`, and `rerank_english`. Loading all three models in one
Windows process previously produced native instability. Isolation also lets the
parent retain evidence when one child exits with a segmentation fault,
`WinError 1114`, invalid JSON, or a timeout.

Run the probe only with the dedicated interpreter:

```text
C:\venvs\unirIntegracionCultural\venv-rag-eval-probe\Scripts\python.exe backend/eval/offline_neural_probe.py
```

The optional `--timeout SECONDS` argument controls the limit for each child.

## Offline controls

The parent and children force these values before importing neural libraries:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
TOKENIZERS_PARALLELISM=false
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
```

Every child blocks and counts `socket.socket.connect`,
`socket.socket.connect_ex`, `socket.create_connection`, and
`urllib.request.urlopen`. `network_attempts=0` means none of those guarded entry
points was called. Any attempt fails the child and the complete probe.

## Required snapshots

| Component | Commit |
| --- | --- |
| Dense multilingual | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` |
| Reranker Spanish/Russian | `1427fd652930e4ba29e8149678df786c240d8825` |
| Reranker English | `7b0235231ca2674cb8ca8f022859a6eba2b1c968` |

Models are loaded from these snapshot directories with
`local_files_only=True`. Missing snapshots never trigger a download.

## Result interpretation

The parent prints one JSON summary. `offline_probe_ok=true` requires all three
children to return zero, emit valid one-line JSON, produce the expected finite
shape, and report zero network attempts. A missing snapshot, invalid output,
network attempt, timeout, segmentation fault, or `WinError 1114` makes the
summary fail and appears in `failures`.

A segmentation fault indicates native process failure, commonly while loading
PyTorch or a model dependency. `WinError 1114` indicates DLL initialization
failure. Neither condition is retried or converted into a successful result;
resolve the environment issue and run a new probe.

The probe confirms individual component availability only. It does not replace
a complete retrieval evaluation or prove that a multi-model evaluation run will
finish successfully.

## Fallback telemetry

Evaluation results expose `fallback_count`. It increments once when evaluation
observes `hybrid` or `hybrid_rerank` indexed with `_dense_active=False`, meaning
the retriever entered its sparse-only activation path. Strict evaluation then
reports that method as `not_executed` instead of completed. Lexical methods,
standalone dense failures, strict reranker failures, and successful neural runs
record zero because no BM25 activation fallback was observed for those methods.