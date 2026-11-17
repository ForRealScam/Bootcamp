# Local Document Q&A Service (Day 11 Capstone)

A local Retrieval-Augmented Generation (RAG) pipeline built for regulated environments where proprietary documents cannot leave on-premise infrastructure. The pipeline ingests internal company PDFs into a local ChromaDB vector store using `nomic-embed-text` (`768`-dim cosine similarity) and answers questions via `qwen3.5:4b-q4_K_M` served locally by Ollama (`http://localhost:11434/v1`).

**AI Coding Assistant Used:** Antigravity (Gemini 4 Argon) used for coding assistance; all pipeline models (`qwen3.5:4b-q4_K_M`, `qwen3.5:2b-q4_K_M`, `nomic-embed-text`) run locally via Ollama.

---

## Project Structure

```text
local-rag/
├── config.py                # Central configuration & Day 12 local-to-cloud swap layer
├── ingest.py                # PDF layout extraction, chunking, embedding, and ChromaDB indexing
├── retrieve.py              # Vector similarity search with cosine scores and metadata logging
├── generate.py              # Grounded LLM generation with context transparency and empty-answer guard
├── pipeline.py              # End-to-end RAG runner with atomic per-question checkpointing & resume
├── benchmark.py             # Exercise 1 benchmark comparing qwen3.5:4b-q4_K_M vs qwen3.5:2b-q4_K_M
├── test_api.py              # Exercise 0 connectivity & reasoning_effort="none" verification
├── test_questions.json      # 18 evaluation Q&A pairs across all 5 documents (easy, medium, hard, unanswerable)
├── benchmark_results.json   # Exercise 1 measured outputs and quality ratings (1-5)
├── pipeline_outputs.json    # Exercise 2 full pipeline evaluation outputs and pass/fail ratings
├── decision_log.md          # Engineering decision log and empirical analysis
├── AGENTS.md                # Ground rules and execution commands for coding assistants
├── README.md                # Setup and execution guide
├── documents/               # Source PDFs (5 NovaTech internal documents)
└── chroma_db/               # Local ChromaDB storage (gitignored; rebuilt via ingest.py)
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

uv run python pipeline.py --reset
```
Embeddings remain local (`nomic-embed-text`), so the existing `chroma_db/` vector store serves both local and cloud runs directly.
