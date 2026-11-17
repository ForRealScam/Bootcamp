# AGENTS.md — Local Document Q&A Service (Day 11 Capstone)

## Ground Rules
- **Local models only:** The pipeline must use strictly local Ollama models (`qwen3.5:4b-q4_K_M`, `qwen3.5:2b-q4_K_M`, `nomic-embed-text`). No cloud-tagged models are allowed in the Day 11 pipeline.
- **Explicit reasoning control:** Every chat completion call must pass `reasoning_effort=config.REASONING_EFFORT` (`"none"` by default) so thinking tokens do not exhaust `max_tokens`.
- **Numbers come from files:** Never fabricate or hardcode benchmark metrics, latencies, or pass counts. Every figure reported in `README.md` or `decision_log.md` must come directly from `benchmark_results.json` or `pipeline_outputs.json`.
- **Manual evaluation:** `decision_log.md` and the quality ratings (`quality_rating`, `passed`, `rating_note`) are written/graded manually by the author after reviewing actual outputs.
- **Keep secrets out of git:** Never read, commit, or expose `.env` files or `chroma_db/`.

## How to Run Each Script
All commands are run from the `local-rag/` directory using `uv`:
- **Verify API connection:** `uv run python test_api.py`
- **Run model benchmarks (Exercise 1):** `uv run python benchmark.py` -> writes `benchmark_results.json`
- **Ingest PDFs into ChromaDB:** `uv run python ingest.py` -> rebuilds `chroma_db/`
- **Test retrieval standalone:** `uv run python retrieve.py`
- **Test generation standalone:** `uv run python generate.py`
- **Run full pipeline on test questions (Exercise 2):** `uv run python pipeline.py` -> writes `pipeline_outputs.json`

## Verification Checks
- Check `ollama ps` to confirm `CONTEXT` is `8192` and the model runs locally.
- Verify no empty `answer` strings or silent `"length"` finish reasons in `benchmark_results.json` and `pipeline_outputs.json`.
- Commit each step separately (`AGENTS.md`, setup, ingest, retrieve, generate, benchmark, pipeline).
