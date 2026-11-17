import argparse
import json
import os
import time
from pathlib import Path

from retrieve import retrieve_chunks
from generate import generate_answer


def answer_question(query: str) -> dict:
    retrieval_result = retrieve_chunks(query)
    generation_result = generate_answer(
        query=query,
        chunks=retrieval_result["retrieved_chunks"],
    )
    return {
        **generation_result,
        "retrieval": retrieval_result,
    }


def _save_outputs_atomic(output_file: str, outputs: list[dict]) -> None:
    """Save outputs atomically and flush to disk so a power loss or thermal shutdown cannot corrupt the file."""
    tmp_file = f"{output_file}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_file, output_file)


def run_test_suite(
    questions_file: str = "test_questions.json",
    output_file: str = "pipeline_outputs.json",
    limit: int | None = None,
    cooldown_seconds: float = 2.5,
    reset: bool = False,
) -> list[dict]:
    with open(questions_file, "r", encoding="utf-8") as f:
        test_questions = json.load(f)

    existing_by_id: dict[str, dict] = {}
    output_path = Path(output_file)
    if not reset and output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_rows = json.load(f)
            for row in existing_rows:
                if row.get("id") and row.get("actual_answer"):
                    existing_by_id[row["id"]] = row
            if existing_by_id:
                print(f"Resuming: found {len(existing_by_id)} already-completed questions in {output_file}.")
        except Exception as exc:
            print(f"Warning: could not read existing {output_file} ({exc}); starting fresh.")

    outputs: list[dict] = []
    # Preserve completed rows in order
    for item in test_questions:
        qid = item["id"]
        if qid in existing_by_id:
            outputs.append(existing_by_id[qid])

    total = len(test_questions)
    completed_this_run = 0
    print(f"Running RAG pipeline on test questions (total={total}, already_done={len(existing_by_id)})...")

    for idx, item in enumerate(test_questions, start=1):
        qid = item["id"]
        question = item["question"]
        expected = item["expected_answer"]

        if qid in existing_by_id:
            print(f"[{idx}/{total}] {qid}: already completed, skipping.")
            continue

        if limit is not None and completed_this_run >= limit:
            print(f"Reached batch limit of {limit} questions for this run. Stopping cleanly.")
            break

        if completed_this_run > 0 and cooldown_seconds > 0:
            time.sleep(cooldown_seconds)

        print(f"[{idx}/{total}] {qid}: {question}")
        result = answer_question(question)
        retrieval = result["retrieval"]
        chunks = retrieval["retrieved_chunks"]

        row = {
            "id": qid,
            "question": question,
            "expected_answer": expected,
            "actual_answer": result["answer"],
            "retrieved_context": [c["content"] for c in chunks],
            "context_sources": [
                {
                    "source": c["source"],
                    "page": c["page"],
                    "score": c["relevance_score"],
                }
                for c in chunks
            ],
            "model": result["model"],
            "thinking": result["thinking"],
            "finish_reason": result["finish_reason"],
            "embedding_model": retrieval["embedding_model"],
            "prompt_tokens": result["prompt_tokens"],
            "tokens_generated": result["tokens_generated"],
            "retrieval_time_ms": retrieval["retrieval_time_ms"],
            "generation_time_ms": result["generation_time_ms"],
            "passed": None,
            "rating_note": "",
        }
        print(
            f"  -> {result['generation_time_ms']}ms | "
            f"prompt_tokens={result['prompt_tokens']} | "
            f"tokens_generated={result['tokens_generated']} | "
            f"finish_reason={result['finish_reason']}"
        )
        outputs.append(row)
        existing_by_id[qid] = row
        completed_this_run += 1

        # Save checkpoint immediately after each question so progress is never lost
        ordered_outputs = [existing_by_id[q["id"]] for q in test_questions if q["id"] in existing_by_id]
        _save_outputs_atomic(output_file, ordered_outputs)

    ordered_outputs = [existing_by_id[q["id"]] for q in test_questions if q["id"] in existing_by_id]
    _save_outputs_atomic(output_file, ordered_outputs)
    print(f"\nSaved {len(ordered_outputs)}/{total} pipeline outputs to {output_file}")
    return ordered_outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the local RAG pipeline over test_questions.json")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of unanswered questions to run in this batch")
    parser.add_argument("--cooldown", type=float, default=2.5, help="Seconds to pause between questions for GPU cooling")
    parser.add_argument("--reset", action="store_true", help="Ignore existing pipeline_outputs.json and re-run all questions")
    args = parser.parse_args()

    run_test_suite(
        limit=args.limit,
        cooldown_seconds=args.cooldown,
        reset=args.reset,
    )
