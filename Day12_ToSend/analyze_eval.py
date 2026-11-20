"""Analyze DeepEval results and pipeline outputs for a single run label.

Reads eval_results_<label>.json and pipeline_outputs_<label>.json and prints:
(a) per-metric mean ± 2*SE and metric error count,
(b) every metric score < 0.7 with id, metric, score, and judge reason,
(c) unanswerable questions refusal string check,
(d) judge vs human agreement (all 5 metrics and Faithfulness + Answer Relevancy).

Uses the Python standard library only.

Usage:
    python analyze_eval.py local
    python analyze_eval.py cloud
"""

import argparse
import json
import os
import statistics

DEFAULT_METRICS = [
    "Faithfulness",
    "Answer Relevancy",
    "Contextual Relevancy",
    "Contextual Recall",
    "Contextual Precision",
]
REFUSAL_SUBSTRING = "cannot find this information"


def load_json(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mean_2se(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) < 2:
        return values[0], None
    mean = statistics.mean(values)
    err = 2 * statistics.stdev(values) / (len(values) ** 0.5)
    return mean, err


def fmt_mean_se(mean: float | None, err: float | None) -> str:
    if mean is None:
        return "n/a"
    err_str = f"{err:.2f}" if err is not None else "n/a"
    return f"{mean:.2f} ± {err_str}"


def ordered_metrics(eval_rows: list[dict]) -> list[str]:
    found = {m for row in eval_rows for m in row.get("metrics", {})}
    return [m for m in DEFAULT_METRICS if m in found] + sorted(
        found - set(DEFAULT_METRICS)
    )


def find_unanswerable_ids(
    outputs_rows: list[dict], outputs_path: str, questions_path: str | None
) -> set[str]:
    candidates = [questions_path] if questions_path else [
        "test_questions.json",
        os.path.join(os.path.dirname(os.path.abspath(outputs_path)), "test_questions.json"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            questions = load_json(path)
            return {
                q["id"]
                for q in questions
                if q.get("type") == "unanswerable"
                or q.get("source_document") in (None, "")
            }

    # Fallback if test_questions.json is unavailable
    return {
        row["id"]
        for row in outputs_rows
        if row.get("type") == "unanswerable"
        or "do not contain information" in (row.get("expected_answer") or "").lower()
    }


def judge_vs_human_summary(
    title: str,
    required_metrics: list[str],
    outputs_rows: list[dict],
    eval_by_id: dict[str, dict],
) -> None:
    buckets: dict[str, list[str]] = {
        "both pass": [],
        "both fail": [],
        "judge pass / human fail": [],
        "judge fail / human pass": [],
    }
    null_human: list[str] = []
    incomplete_judge: list[str] = []

    for row in outputs_rows:
        qid = row["id"]
        human_passed = row.get("passed")
        if human_passed is None:
            null_human.append(qid)
            continue

        metrics = eval_by_id.get(qid, {})
        if not required_metrics or any(
            m not in metrics or metrics[m].get("success") is None
            for m in required_metrics
        ):
            incomplete_judge.append(qid)
            continue

        judge_pass = all(metrics[m]["success"] is True for m in required_metrics)
        if judge_pass and human_passed:
            buckets["both pass"].append(qid)
        elif not judge_pass and not human_passed:
            buckets["both fail"].append(qid)
        elif judge_pass and not human_passed:
            buckets["judge pass / human fail"].append(qid)
        else:
            buckets["judge fail / human pass"].append(qid)

    print(f"\n### Judge vs Human ({title})")
    total_compared = sum(len(v) for v in buckets.values())
    if total_compared == 0:
        print("Skipped: no rows with both human `passed` rating and complete judge metrics.")
    else:
        print("| Case | Count | Question IDs |")
        print("|---|---:|---|")
        for case, ids in buckets.items():
            id_text = ", ".join(ids) if ids else "-"
            print(f"| {case} | {len(ids)} | {id_text} |")

    if null_human:
        print(f"Note: skipped {len(null_human)} row(s) with human `passed: null` ({', '.join(null_human)}).")
    if incomplete_judge:
        print(
            f"Note: skipped {len(incomplete_judge)} row(s) with missing/errored judge metrics ({', '.join(incomplete_judge)})."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze DeepEval scores, low-score reasons, refusals, and human agreement."
    )
    parser.add_argument(
        "label",
        nargs="?",
        default="local",
        help="Run label, e.g. 'local' or 'cloud' (default: local)",
    )
    parser.add_argument("--eval", dest="eval_path", help="Override eval_results_<label>.json path")
    parser.add_argument("--outputs", dest="outputs_path", help="Override pipeline_outputs_<label>.json path")
    parser.add_argument("--questions", dest="questions_path", help="Optional path to test_questions.json")
    args = parser.parse_args()

    eval_path = args.eval_path or f"eval_results_{args.label}.json"
    outputs_path = args.outputs_path or f"pipeline_outputs_{args.label}.json"

    eval_rows = load_json(eval_path)
    outputs_rows = load_json(outputs_path)
    metrics = ordered_metrics(eval_rows)
    eval_by_id = {r["id"]: r.get("metrics", {}) for r in eval_rows}

    # (a) Per-metric summary
    print(f"# Evaluation Analysis: {args.label}\n")
    print("## (a) Per-Metric Summary\n")
    print("| Metric | n | Mean ± 2×SE | Metric Errors |")
    print("|---|---:|---:|---:|")
    for metric in metrics:
        scores = [
            r["metrics"][metric]["score"]
            for r in eval_rows
            if metric in r.get("metrics", {}) and r["metrics"][metric].get("score") is not None
        ]
        errors = sum(
            1
            for r in eval_rows
            if metric in r.get("metrics", {}) and bool(r["metrics"][metric].get("error"))
        )
        m, e = mean_2se(scores)
        print(f"| {metric} | {len(scores)} | {fmt_mean_se(m, e)} | {errors} |")

    # (b) Scores < 0.7 with judge reason
    print("\n## (b) Metric Scores Below 0.7\n")
    low_items = []
    for row in eval_rows:
        qid = row["id"]
        row_metrics = row.get("metrics", {})
        for metric in metrics:
            data = row_metrics.get(metric)
            if not data:
                continue
            score = data.get("score")
            if score is not None and score < 0.7:
                low_items.append((qid, metric, score, data.get("reason") or "(no reason provided)"))

    if not low_items:
        print("None — all non-null metric scores are >= 0.7.")
    else:
        for qid, metric, score, reason in low_items:
            print(f"- **{qid}** | {metric}: **{score:.2f}**")
            print(f"  Reason: {reason}")

    # (c) Unanswerable questions refusal check
    print("\n## (c) Unanswerable Questions (Refusal Check)\n")
    unanswerable_ids = find_unanswerable_ids(outputs_rows, outputs_path, args.questions_path)
    unanswerable_rows = [r for r in outputs_rows if r["id"] in unanswerable_ids]
    if not unanswerable_rows:
        print("No unanswerable questions found.")
    else:
        passed_refusals = 0
        for row in unanswerable_rows:
            answer = (row.get("actual_answer") or "").strip()
            refused = REFUSAL_SUBSTRING in answer.lower()
            if refused:
                passed_refusals += 1
            status = "PASS" if refused else "FAIL"
            preview = answer.replace("\n", " ")
            if len(preview) > 140:
                preview = preview[:137] + "..."
            print(f"- **{row['id']}**: {status} — {preview or '(empty answer)'}")
        print(f"\nRefused correctly: {passed_refusals} of {len(unanswerable_rows)}")

    # (d) Judge vs human agreement
    print("\n## (d) Judge vs Human Agreement")
    judge_vs_human_summary("All 5 metrics", metrics, outputs_rows, eval_by_id)
    gen_metrics = [m for m in ("Faithfulness", "Answer Relevancy") if m in metrics]
    judge_vs_human_summary("Faithfulness + Answer Relevancy", gen_metrics, outputs_rows, eval_by_id)


if __name__ == "__main__":
    main()
