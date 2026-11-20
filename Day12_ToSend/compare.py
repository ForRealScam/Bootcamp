"""Compare local and cloud RAG evaluation results and pipeline outputs.

Reads DeepEval results and pipeline output JSON files for both runs and prints:
1. Per-metric paired comparison (mean ± 2*SE, cloud - local diff, verdict).
2. Run summary table (median/slowest generation time, avg completion tokens,
   and empty/failed answer count).
3. Per-question score difference table (cloud - local).

Uses the Python standard library only.

Usage:
    python compare.py
    python compare.py eval_local.json eval_cloud.json pipe_local.json pipe_cloud.json --out compare_output.md
"""

import argparse
import json
import statistics

DEFAULT_METRICS = [
    "Faithfulness",
    "Answer Relevancy",
    "Contextual Relevancy",
    "Contextual Recall",
    "Contextual Precision",
]


def load_json(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mean_2se(values: list[float]) -> tuple[float | None, float | None]:
    """Return (mean, 2 * sample_std / sqrt(n)); error is None when n < 2."""
    if not values:
        return None, None
    if len(values) < 2:
        return values[0], None
    mean = statistics.mean(values)
    err = 2 * statistics.stdev(values) / (len(values) ** 0.5)
    return mean, err


def fmt_mean_se(mean: float | None, err: float | None, signed: bool = False) -> str:
    if mean is None:
        return "n/a"
    fmt = "+.2f" if signed else ".2f"
    err_str = f"{err:.2f}" if err is not None else "n/a"
    return f"{mean:{fmt}} ± {err_str}"


def ordered_metrics(local_by_id: dict, cloud_by_id: dict) -> list[str]:
    found = {m for row in local_by_id.values() for m in row} | {
        m for row in cloud_by_id.values() for m in row
    }
    return [m for m in DEFAULT_METRICS if m in found] + sorted(
        found - set(DEFAULT_METRICS)
    )


def summarize_pipeline(label: str, rows: list[dict]) -> dict[str, str]:
    times = [r["generation_time_ms"] for r in rows if r.get("generation_time_ms") is not None]
    median_ms = f"{statistics.median(times):.0f}" if times else "n/a"
    slowest_ms = f"{max(times):.0f}" if times else "n/a"

    token_totals = []
    for r in rows:
        gen = r.get("tokens_generated")
        reasoning = r.get("reasoning_tokens")
        if gen is not None or reasoning is not None:
            token_totals.append((gen or 0) + (reasoning or 0))
    avg_tokens = f"{statistics.mean(token_totals):.1f}" if token_totals else "n/a"

    empty_or_failed = sum(
        1
        for r in rows
        if not (r.get("actual_answer") or "").strip() or r.get("finish_reason") != "stop"
    )
    return {
        "label": label,
        "count": str(len(rows)),
        "median_ms": median_ms,
        "slowest_ms": slowest_ms,
        "avg_tokens": avg_tokens,
        "failed": f"{empty_or_failed} / {len(rows)}",
    }


def build_report(
    eval_local_rows: list[dict],
    eval_cloud_rows: list[dict],
    pipe_local_rows: list[dict],
    pipe_cloud_rows: list[dict],
) -> str:
    local_by_id = {r["id"]: r.get("metrics", {}) for r in eval_local_rows}
    cloud_by_id = {r["id"]: r.get("metrics", {}) for r in eval_cloud_rows}
    metrics = ordered_metrics(local_by_id, cloud_by_id)

    lines: list[str] = []
    lines.append("## Metric Comparison (Local vs Cloud)\n")
    lines.append("| Metric | n | Local (mean ± 2×SE) | Cloud (mean ± 2×SE) | Diff (cloud − local) | Verdict |")
    lines.append("|---|---:|---:|---:|---:|---|")

    for metric in metrics:
        paired_ids = [
            qid
            for qid in local_by_id
            if qid in cloud_by_id
            and local_by_id[qid].get(metric, {}).get("score") is not None
            and cloud_by_id[qid].get(metric, {}).get("score") is not None
        ]
        local_scores = [local_by_id[qid][metric]["score"] for qid in paired_ids]
        cloud_scores = [cloud_by_id[qid][metric]["score"] for qid in paired_ids]
        diffs = [c - l for l, c in zip(local_scores, cloud_scores)]

        m_local, e_local = mean_2se(local_scores)
        m_cloud, e_cloud = mean_2se(cloud_scores)
        m_diff, e_diff = mean_2se(diffs)

        if m_diff is None or e_diff is None:
            verdict = "insufficient data (n<2)"
        elif m_diff - e_diff <= 0 <= m_diff + e_diff:
            verdict = "no clear difference"
        elif m_diff > 0:
            verdict = "cloud higher"
        else:
            verdict = "local higher"

        lines.append(
            f"| {metric} | {len(paired_ids)} | "
            f"{fmt_mean_se(m_local, e_local)} | "
            f"{fmt_mean_se(m_cloud, e_cloud)} | "
            f"{fmt_mean_se(m_diff, e_diff, signed=True)} | "
            f"{verdict} |"
        )

    lines.append("\n## Runtime and Reliability\n")
    lines.append("| Run | Questions | Median gen time (ms) | Slowest gen time (ms) | Avg completion tokens | Empty / failed answers |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for summary in (
        summarize_pipeline("local", pipe_local_rows),
        summarize_pipeline("cloud", pipe_cloud_rows),
    ):
        lines.append(
            f"| {summary['label']} | {summary['count']} | "
            f"{summary['median_ms']} | {summary['slowest_ms']} | "
            f"{summary['avg_tokens']} | {summary['failed']} |"
        )

    all_ids = list(local_by_id.keys()) + [
        qid for qid in cloud_by_id if qid not in local_by_id
    ]
    lines.append("\n## Per-Question Score Differences (cloud − local)\n")
    lines.append("| id | " + " | ".join(metrics) + " |")
    lines.append("|---|" + "|".join(["---:"] * len(metrics)) + "|")
    for qid in all_ids:
        cells = []
        for metric in metrics:
            l_score = local_by_id.get(qid, {}).get(metric, {}).get("score")
            c_score = cloud_by_id.get(qid, {}).get(metric, {}).get("score")
            if l_score is not None and c_score is not None:
                cells.append(f"{c_score - l_score:+.2f}")
            else:
                cells.append("n/a")
        lines.append(f"| {qid} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare local and cloud RAG evaluation and pipeline output files."
    )
    parser.add_argument(
        "eval_local",
        nargs="?",
        default="eval_results_local.json",
        help="Path to local eval results JSON (default: eval_results_local.json)",
    )
    parser.add_argument(
        "eval_cloud",
        nargs="?",
        default="eval_results_cloud.json",
        help="Path to cloud eval results JSON (default: eval_results_cloud.json)",
    )
    parser.add_argument(
        "pipeline_local",
        nargs="?",
        default="pipeline_outputs_local.json",
        help="Path to local pipeline outputs JSON (default: pipeline_outputs_local.json)",
    )
    parser.add_argument(
        "pipeline_cloud",
        nargs="?",
        default="pipeline_outputs_cloud.json",
        help="Path to cloud pipeline outputs JSON (default: pipeline_outputs_cloud.json)",
    )
    parser.add_argument(
        "--out",
        help="Optional output markdown file path (e.g. compare_output.md)",
    )
    args = parser.parse_args()

    report = build_report(
        load_json(args.eval_local),
        load_json(args.eval_cloud),
        load_json(args.pipeline_local),
        load_json(args.pipeline_cloud),
    )
    print(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\nSaved comparison to {args.out}")


if __name__ == "__main__":
    main()
