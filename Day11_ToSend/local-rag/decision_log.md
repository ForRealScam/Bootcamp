# Decision Log: Local RAG Pipeline

## Machine

- **Hardware:** Personal laptop with an Intel Core i7-11800H, 16 GB RAM, and an NVIDIA RTX 3060 GPU (native Windows Ollama).
- **`ollama ps` with my main model loaded:**
  ```text
  NAME                       ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
  qwen3.5:4b-q4_K_M          d8b0f5e9760c    3.3 GB    100% GPU     8192       llamacpp    4 minutes from now    
  nomic-embed-text:latest    0a109f422b47    335 MB    100% GPU     2048       llamacpp    4 minutes from now    
  ```

## Model Selection

- **Chosen model:** `qwen3.5:4b-q4_K_M`
- **Thinking:** I turned thinking off using `reasoning_effort="none"`. Qwen 3.5 has thinking enabled by default, which uses part of the token limit and can cause empty responses.
- **Why I chose it:** I tested the 4B and 2B models across 6 prompts in `benchmark_results.json`. The 4B model scored `5/5` on 5 of the 6 prompts (and `4/5` on `instruction_following`), while the 2B model dropped to `4/5` on `factual` and `code_generation` and `3/5` on `instruction_following`. I rejected the 2B model because even though it was slightly faster, the 4B model gave more accurate answers.

## Embedding Model

- **Chosen:** `nomic-embed-text` (768 dimensions).

## PDF Parsing

- **Tool:** I used `pypdf` with `page.extract_text(extraction_mode="layout")`, which kept table rows aligned on single lines, and stripped extra spaces so tables stayed compact.

## Chunking Strategy

- **Chunk size:** 1000 characters.
- **Overlap:** 150 characters.
- **Why:** The default 512-character chunks were too small and split tables across multiple chunks.

## Retrieval Configuration

- **Top-K:** 7
- **Context window:** 8192 tokens (for example, `q01` in `pipeline_outputs.json` used 1391 `prompt_tokens`).
- **Why:** Increasing Top-K from 5 to 7 helped retrieve information when answers spanned two documents, such as `q13`.

## Results and Observations

- **What worked well:** 14 out of 18 questions passed in pipeline_outputs.json.
  - **Reading tables:** Questions `q03`, `q04`, `q08`, and `q15` worked good because keeping tables together helped the model read the right rows.
  - **Using information from two documents:** Questions `q01` and `q13` worked well comparing older handbook rules with newer meeting notes.
  - **Handling missing information:** For `q17` and `q18`, the model correctly said it couldn't find information instead of making it up.

- **What failed:** 4 out of 18 questions failed in `pipeline_outputs.json`: `q07`, `q12`, `q14`, and `q16`.
  - **q07 – Support tiers:** Retrieved bottom of SLA table but missed the top rows.
  - **q12 – Copilot budget:** Found the total budget of EUR 1.2M but missed the chunk with exact breakdown.
  - **q14 – Pricing differences:** Found the section heading but missed the pricing table in next chunk.
  - **q16 – Lisbon office:** Found the budget amounts but missed the meeting notes.

## Problems I Ran Into

1. **Laptop overheating:** Running all 18 questions at once pushed my GPU too hard and caused my laptop to shut down.
