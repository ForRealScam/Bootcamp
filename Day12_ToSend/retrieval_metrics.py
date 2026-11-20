"""Compute Hit@5, Hit@7, and MRR from test_questions.json and pipeline outputs.

Compares each question's labelled source_document against the retrieved
context_sources (TOP_K = 7). Unanswerable or multi-document questions are
skipped. Uses the Python standard library only.

Usage:
    python retrieval_metrics.py
    python retrieval_metrics.py test_questions.json pipeline_outputs_local.json
"""

import argparse
import json


def load_json(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def should_skip(question: dict | None, label: object) -> bool:
    if question and question.get("type") == "unanswerable":
        return True
    return label in (None, "", "multiple") or isinstance(label, list)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute Hit@5, Hit@7, and MRR from retrieved context sources."
    )
    parser.add_argument(
        "questions_path",
        nargs="?",
        default="test_questions.json",
        help="Path to test_questions.json (default: test_questions.json)",
    )
    parser.add_argument(
        "outputs_path",
        nargs="?",
        default="pipeline_outputs_local.json",
        help="Path to pipeline outputs JSON (default: pipeline_outputs_local.json)",
    )
    args = parser.parse_args()

    questions = load_json(args.questions_path)
    rows = load_json(args.outputs_path)
    questions_by_id = {q["id"]: q for q in questions}

    ranks: list[int | None] = []
    skipped_ids: list[str] = []

    print(f"Retrieval metrics ({args.outputs_path} vs {args.questions_path})\n")
    print("| id | labelled source | rank | Hit@5 | Hit@7 |")
    print("|---|---|---:|:---:|:---:|")

    for row in rows:
        qid = row["id"]
        q = questions_by_id.get(qid)
        label = q.get("source_document") if q else None
        if should_skip(q, label):
            skipped_ids.append(qid)
            continue

        sources = [c["source"] for c in row.get("context_sources", [])][:7]
        rank = sources.index(label) + 1 if label in sources else None
        ranks.append(rank)

        hit5 = "yes" if rank is not None and rank <= 5 else "no"
        hit7 = "yes" if rank is not None and rank <= 7 else "no"
        rank_text = str(rank) if rank is not None else "not in top 7"
        print(f"| {qid} | {label} | {rank_text} | {hit5} | {hit7} |")

    if not ranks:
        raise SystemExit("No answerable questions with a single labelled source_document.")

    hit_at_5 = sum(rk is not None and rk <= 5 for rk in ranks) / len(ranks)
    hit_at_7 = sum(rk is not None and rk <= 7 for rk in ranks) / len(ranks)
    mrr = sum(1 / rk for rk in ranks if rk is not None) / len(ranks)

    skipped_note = (
        f" (skipped {len(skipped_ids)}: {', '.join(skipped_ids)})"
        if skipped_ids
        else ""
    )
    print(f"\nQuestions scored: {len(ranks)}{skipped_note}")
    print(f"Hit@5: {hit_at_5:.2f}   Hit@7: {hit_at_7:.2f}   MRR: {mrr:.2f}")


if __name__ == "__main__":
    main()
