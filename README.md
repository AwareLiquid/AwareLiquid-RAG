# AwareLiquid

**A memory-compression adapter for Qwen.** AwareLiquid wraps a frozen Qwen model
with an external long-term memory layer so it can answer questions over documents
far longer than its context window — while spending as few generation tokens as
possible.

The adapter is **non-invasive**: it never modifies the base model's weights and
reaches generation only through the official Qwen API. Everything that makes it
work — chunking, embedding-based retrieval, and dynamic context compression —
runs locally, *around* the model rather than inside it.

```
          ┌─────────────────────── AwareLiquid adapter (local) ──────────────────────┐
document → │  chunker → sentence encoder → vector store → retrieve → compressor      │ → compact prompt ─┐
          └──────────────────────────────────────────────────────────────────────────┘                  │
question ─────────────────────────────────────────────────────────────────────────────────────────────► │
                                                                                                          ▼
                                                                                            frozen Qwen model (API)
                                                                                                          │
                                                                                       answer + token usage ◄┘
```

## Why

A long report rarely fits in a context window, and even when it does, feeding the
whole thing to the model for every question is wasteful — most of the document is
irrelevant to any one question, and tokens cost money and latency. AwareLiquid
keeps the document in a local vector store, pulls in only the passages a question
needs, compresses those to their load-bearing sentences, and sends the model a
prompt that is a small fraction of the source. The base model does what it is good
at — reading a short, relevant context and answering — and nothing else.

## How it works

| Stage | Module | What it does |
|-------|--------|--------------|
| **Chunk** | `adapter/chunker.py` | Split documents on sentence/paragraph boundaries into overlapping passages (language-agnostic, handles Chinese). |
| **Embed** | `memory/encoder.py` | Lazy, L2-normalised multilingual sentence embedder (`intfloat/multilingual-e5-small` by default; `bge` selectable). |
| **Store** | `memory/lexical_store.py` | SQLite-backed FTS5/BM25 lexical index with deterministic source metadata and strict document filters. The legacy vector store remains research-only. |
| **Retrieve** | `adapter/qa_agent.py` + `adapter/evidence_index.py` | Competition-safe retrieval: structural source nodes, BM25, exact numeric/clause anchors, bounded neighbor expansion, and source-linked evidence deduplication. |
| **Compress** | `adapter/compressor.py` | Extractive, **LLM-free** sentence selection under a character budget — keeps sentences by question overlap plus a salience bonus for numbers, %, currency and dates. Compression itself costs **zero** generation tokens. |
| **Answer** | `adapter/qwen_client.py` | OpenAI-compatible Qwen chat call with exact per-call token accounting. |

Retrieval and compression run entirely locally, so the only generation tokens
spent are the compact prompt and the short answer.

## Install

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Quick start

```python
from awareliquid import MemoryQAAgent

agent = MemoryQAAgent()                     # local store + local embedder
agent.ingest_document("report-1", long_text)

res = agent.answer_question(
    qid="q1",
    question="公司 2023 年营业收入是多少？",
    options=["10.2 亿元", "12.4 亿元", "15.1 亿元", "20.0 亿元"],
    qtype="mcq",                            # "mcq" | "tf" | "multi"
    doc_ids=["report-1"],                   # restrict retrieval to these docs
)
print(res.answer, res.usage.total_tokens)   # e.g. "B" 812
```

Run the bundled demo (works offline with the mock backend):

```bash
python examples/run_qa.py
```

## Configuration

Generation is configured entirely through environment variables — nothing is
hard-coded, and the client falls back to a deterministic offline mock when no key
is present:

| Variable | Default | Meaning |
|----------|---------|---------|
| `AWARELIQUID_LLM_BACKEND` | `qwen` | `qwen` or `mock` (offline). |
| `AWARELIQUID_LLM_API_KEY` | — | API key (falls back to `DASHSCOPE_API_KEY`). |
| `AWARELIQUID_LLM_BASE_URL` | DashScope compatible-mode | OpenAI-compatible base URL. |
| `AWARELIQUID_LLM_MODEL` | `qwen-plus` | Model id. |

```bash
export AWARELIQUID_LLM_API_KEY="sk-..."
export AWARELIQUID_LLM_MODEL="qwen-plus"
python examples/run_qa.py
```

Retrieval and compression are tunable via `RetrievalConfig` (chunk size, overlap,
`top_k`, compression budget, answer-token cap, structural evidence settings, and
optional multi-query retrieval). The formal `submit.py` entry point is lexical/BM25
only; the legacy dense/hybrid path is not part of the competition workflow.

## Batch answering

Answer a whole question set and write a CSV (`qid,answer,prompt_tokens,
completion_tokens,total_tokens`, with a leading `summary` totals row):

```bash
python submit.py --questions examples/sample_questions.jsonl \
                 --docs examples/sample_docs.json --out submission.csv
```

Batch runs are atomic and ordered by default: after each completed question,
`<out>.checkpoint.json` is replaced atomically. Re-running the command resumes
from the first uncommitted question and validates the question/document
fingerprints before continuing. Use `--checkpoint PATH` to choose the file,
`--fresh` to intentionally restart, or `--no-checkpoint` for an ephemeral run.

Questions are JSONL/JSON (`qid`, `question`, `options` as a `{letter: text}` dict
or a list, `answer_format`, `doc_ids`); docs are a `{doc_id: text}` JSON or a
directory of `<doc_id>.txt` files. To score a labelled set end-to-end (accuracy +
tokens), use `examples/eval_accuracy.py`.

## Token accounting

Every chat call reports exact `prompt_tokens` / `completion_tokens` /
`total_tokens`. `AnswerResult.usage` carries per-question usage and
`summarize_usage(results)` aggregates a batch, so total generation cost across a
run is always known.

## Tests

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
./scripts/test.sh
```

The suite runs offline with the deterministic local mock backend and in-memory
stores; it does not require a Qwen API key or a GPU. The `lexical` retrieval
backend uses SQLite/FTS5 and is the only backend accepted by formal submission.
The original `hybrid` backend remains available for isolated research tests only.

## Validation

`benchmarks/bench_adapter.py` measures the adapter's own contribution — retrieval
and compression — on an adversarial financial QA set where a few answer-bearing
sentences are buried in thousands of tokens of boilerplate:

```bash
python benchmarks/bench_adapter.py          # real multilingual embedder
python benchmarks/bench_adapter.py --fake   # lexical stand-in, no model download
```

On the bundled set (3 financial documents inflated with boilerplate to ≈22.7k
full-document tokens, 8 questions):

| Metric | Lexical stand-in (8-q set, deterministic) |
|--------|:----------------:|
| Retrieval recall@1, dense → hybrid RRF | 6/8 → 6/8 |
| Retrieval recall@4 (answer chunk retrieved) | 7/8 → 8/8 |
| Answer-sentence retention after compression | 7/8 → 8/8 |
| End-to-end valid rows (formal format) | 8/8 |
| Prompt context tokens vs. full-document | 1254 vs 22668 (−94%) |

These are **single-run screening counts, not conclusions**: they prove the
pipeline works and the gate conditions hold, not that retrieval beats any
baseline. Citing them externally requires multi-seed expansion through the
`publishable()` gate in `benchmarks/experiment_protocol.py`. Numbers are
reconciled in `docs/RESULTS.md` (single source of truth); pre-registration
rules live in `docs/PREREGISTRATION.md`. The `--fake` run is byte-identical
across processes (three-run proof: `benchmarks/results/bench_adapter_fake_20260906_r1.log`
and its `r2`/`r3` siblings; pinned by `tests/test_bench_determinism.py`).

A historical single-run e5 result (6-question set) is archived in
`docs/RESULTS.md` (SUPERSEDED section): it showed the multilingual embedder
recovering a paraphrased question ("归母净利润同比增长" vs. the document's
"归属于母公司股东的净利润…较上年同期增长") that pure lexical overlap misses —
which is why the multilingual model, not a keyword index, drives retrieval.
Re-run it through the `publishable()` gate before citing it anywhere.

**Scope:** this benchmark validates retrieval, compression and token efficiency,
which are the adapter's job. The final letter is chosen by the frozen model, so
end-to-end answer *accuracy* requires a live Qwen key and is not measured offline.

## License

MIT — see [LICENSE](LICENSE).
