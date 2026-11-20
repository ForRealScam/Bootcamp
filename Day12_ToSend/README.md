# Local Document Q&A Service — Day 12 Evaluation Capstone

A local Retrieval-Augmented Generation (RAG) pipeline and evaluation suite built for regulated environments where proprietary documents cannot leave on-premise infrastructure. This folder evaluates our own Day 11 RAG pipeline (`retrieve.py`, `generate.py`, `pipeline.py`), which ingests internal company PDFs into a local ChromaDB vector store using `nomic-embed-text` (`768`-dim cosine similarity) and answers questions via `qwen3.5:4b-q4_K_M` served locally by Ollama (`http://localhost:11434/v1`), compared against `gpt-5.6-luna` on Azure OpenAI and judged by `gpt-5.4-mini` via DeepEval (`4.3.4`).

**Pipeline Evaluated:** Own Day 11 RAG pipeline (`config.py`, `ingest.py`, `retrieve.py`, `generate.py`, `pipeline.py`).
**AI Coding Assistant Used:** Day 11 code was written with Antigravity (Gemini 4 Argon); Day 12 code was written with Antigravity (Gemini 4 Hydrogen workers, reviewed by Claude Opus 5.5). All local models (`qwen3.5:4b-q4_K_M`, `nomic-embed-text`) run locally via Ollama.

---

## Project Structure

```text
Day12_ToSend/
├── config.py                   # Central configuration & Day 12 local-to-cloud swap layer
├── ingest.py                   # PDF layout extraction, chunking, embedding, and ChromaDB indexing
├── retrieve.py                 # Vector similarity search with cosine scores and metadata logging
├── generate.py                 # Grounded LLM generation with context transparency and empty-answer guard
├── pipeline.py                 # End-to-end RAG runner with atomic checkpointing, resume, and --test-set
├── eval_pipeline.py            # Day 12 DeepEval runner (5 metrics) -> eval_results_<label>.json
├── security_probe.py           # Day 12 security probes (7 given + 5 custom attacks) -> security_results_<label>.json
├── compare.py                  # Day 12 local vs cloud comparison table (--out compare_output.md)
├── retrieval_metrics.py        # Day 12 deterministic Hit@5, Hit@7, and MRR retrieval metrics
├── analyze_eval.py             # Day 12 per-run summary, low-score reasons, refusal & judge-vs-human check
├── test_questions.json         # 18 evaluation Q&A pairs across all 5 documents (easy, medium, hard, unanswerable)
├── pipeline_outputs_local.json # Local model (qwen3.5:4b-q4_K_M) answers and manual ratings over test_questions.json
├── pipeline_outputs_cloud.json # Cloud model (gpt-5.6-luna) answers over test_questions.json
├── eval_results_local.json     # DeepEval 5-metric scores and reasons for the local model
├── eval_results_cloud.json     # DeepEval 5-metric scores and reasons for the cloud model
├── security_results_local.json # Local security probe outputs, verdicts, and notes
├── security_results_cloud.json # Cloud security probe outputs, verdicts, and notes
├── compare_output.md           # Output table from compare.py (local vs cloud metrics & speed)
├── evaluation_report.md        # Day 12 evaluation report
├── README.md                   # Setup and execution guide
├── documents/                  # Source PDFs (5 NovaTech internal documents)
└── chroma_db/                  # Local ChromaDB storage (gitignored; rebuilt via ingest.py)
```

---

## Prerequisites & Setup

1. **Install Native Ollama (Windows `v0.40.16`):**
   Download and install `OllamaSetup.exe` from [https://ollama.com/download](https://ollama.com/download).

2. **Configure 8192 Context Window:**
   Set the `OLLAMA_CONTEXT_LENGTH` user environment variable to `8192` so RAG prompts are never silently truncated at the 4,096-token laptop default:
   ```powershell
   [Environment]::SetEnvironmentVariable("OLLAMA_CONTEXT_LENGTH", "8192", "User")
   ```
   Restart Ollama and verify with `ollama ps` while a model is loaded that `CONTEXT` reads `8192`.

3. **Pull Required Local Models:**
   ```powershell
   ollama pull qwen3.5:4b-q4_K_M
   ollama pull qwen3.5:2b-q4_K_M
   ollama pull nomic-embed-text
   ```

4. **Install Python Environment (`uv` with Python 3.12):**
   ```powershell
   cd local-rag
   uv sync
   ```

---

## How to Run

All scripts are executed from the `local-rag/` folder using `uv run`:

### 1. Rebuild the Vector Database (`chroma_db/`)
`chroma_db/` is gitignored. Rebuild it at any time with this single command:
```powershell
uv run python ingest.py
```
This extracts text from all 5 PDFs in `documents/` using `pypdf` layout mode, splits them into `206` chunks (`CHUNK_SIZE = 1000` characters, `CHUNK_OVERLAP = 150` characters), embeds them locally with `nomic-embed-text` (`search_document: ` prefix), and indexes them in `chroma_db/` under collection `bootcamp_docs` with cosine distance.

### 2. Verify API Connectivity (Exercise 0)
```powershell
uv run python test_api.py
```

### 3. Run Model Benchmark (Exercise 1)
```powershell
uv run python benchmark.py
```
Runs 6 capability prompts (`factual`, `reasoning`, `summarization`, `structured`, `code_generation`, `instruction_following`) across `qwen3.5:4b-q4_K_M` and `qwen3.5:2b-q4_K_M` (`reasoning_effort="none"`) and saves results to `benchmark_results.json`. *(Note: Re-running overwrites manual `quality_rating` and `rating_note` fields.)*

### 4. Test Retrieval or Generation Standalone
```powershell
uv run python retrieve.py
uv run python generate.py
```

### 5. Run Full RAG Pipeline Over `test_questions.json` (Exercise 2)
```powershell
uv run python pipeline.py
```
`pipeline.py` saves checkpoints atomically after every single question and automatically resumes from where it left off if interrupted. To run in smaller batches with a GPU cooling delay between questions:
```powershell
uv run python pipeline.py --limit 5 --cooldown 3.0
```
To force a fresh re-run from question 1:
```powershell
uv run python pipeline.py --reset
```

---

## Swapping to Cloud Provider (Day 12 Evaluation)

`config.py` isolates all provider settings so swapping the generation LLM from local Ollama (`max_tokens`) to Azure OpenAI (`max_completion_tokens`) requires **zero code changes**—only four environment variables in PowerShell:

```powershell
$env:LLM_BASE_URL = "https://<resource>.openai.azure.com/openai/v1/"
$env:LLM_API_KEY = $env:AZURE_OPENAI_API_KEY
$env:LLM_MODEL = "gpt-5.6-luna"
$env:TOKEN_LIMIT_PARAM = "max_completion_tokens"

uv run python pipeline.py --test-set pipeline_outputs_cloud.json
```

`pipeline.py` refuses to overwrite `pipeline_outputs.json` when `LLM_MODEL` is not `qwen3.5:4b-q4_K_M`. Always unset the four cloud variables after cloud runs before returning to local runs:

```powershell
Remove-Item Env:LLM_BASE_URL,Env:LLM_API_KEY,Env:LLM_MODEL,Env:TOKEN_LIMIT_PARAM
```

Embeddings remain local (`nomic-embed-text`), so the existing `chroma_db/` vector store serves both local and cloud runs directly.

---

## Day 12 Evaluation

This evaluation assesses our own Day 11 RAG pipeline (`retrieve.py`, `generate.py`, `pipeline.py`).

### Configure Judge Environment Variables (PowerShell)

```powershell
$env:AZURE_OPENAI_API_KEY = "<your-azure-openai-api-key>"
$env:JUDGE_BASE_URL = "https://<resource>.openai.azure.com/openai/v1/"
```

### Run Order

1. **Evaluate local outputs (`pipeline_outputs_local.json` -> `eval_results_local.json`):**
   ```powershell
   uv run python eval_pipeline.py local
   ```
2. **Run cloud pipeline (`pipeline_outputs_cloud.json`) and evaluate (`eval_results_cloud.json`):**
   ```powershell
   $env:LLM_BASE_URL = "https://<resource>.openai.azure.com/openai/v1/"
   $env:LLM_API_KEY = $env:AZURE_OPENAI_API_KEY
   $env:LLM_MODEL = "gpt-5.6-luna"
   $env:TOKEN_LIMIT_PARAM = "max_completion_tokens"

   uv run python pipeline.py --test-set pipeline_outputs_cloud.json
   uv run python eval_pipeline.py cloud
   ```
3. **Run security probes (with cloud vars unset for `local`, and set for `cloud`):**
   ```powershell
   Remove-Item Env:LLM_BASE_URL,Env:LLM_API_KEY,Env:LLM_MODEL,Env:TOKEN_LIMIT_PARAM -ErrorAction SilentlyContinue
   uv run python security_probe.py local

   # With the four cloud LLM_* variables set:
   uv run python security_probe.py cloud
   ```
4. **Analyze results and compare local vs cloud:**
   ```powershell
   uv run python analyze_eval.py local
   uv run python analyze_eval.py cloud
   uv run python retrieval_metrics.py
   uv run python compare.py --out compare_output.md
   ```
