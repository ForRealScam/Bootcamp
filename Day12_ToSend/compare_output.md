## Metric Comparison (Local vs Cloud)

| Metric | n | Local (mean ± 2×SE) | Cloud (mean ± 2×SE) | Diff (cloud − local) | Verdict |
|---|---:|---:|---:|---:|---|
| Faithfulness | 18 | 0.76 ± 0.12 | 0.74 ± 0.17 | -0.02 ± 0.12 | no clear difference |
| Answer Relevancy | 18 | 0.98 ± 0.03 | 0.97 ± 0.04 | -0.01 ± 0.06 | no clear difference |
| Contextual Relevancy | 18 | 0.36 ± 0.12 | 0.35 ± 0.10 | -0.01 ± 0.04 | no clear difference |
| Contextual Recall | 18 | 0.66 ± 0.22 | 0.72 ± 0.20 | +0.06 ± 0.13 | no clear difference |
| Contextual Precision | 18 | 0.76 ± 0.14 | 0.76 ± 0.14 | -0.01 ± 0.04 | no clear difference |

## Runtime and Reliability

| Run | Questions | Median gen time (ms) | Slowest gen time (ms) | Avg completion tokens | Empty / failed answers |
|---|---:|---:|---:|---:|---:|
| local | 18 | 4935 | 24681 | 241.2 | 0 / 18 |
| cloud | 18 | 1470 | 2525 | 109.6 | 0 / 18 |

## Per-Question Score Differences (cloud − local)

| id | Faithfulness | Answer Relevancy | Contextual Relevancy | Contextual Recall | Contextual Precision |
|---|---:|---:|---:|---:|---:|
| q01 | +0.40 | -0.25 | -0.04 | +0.00 | +0.12 |
| q02 | +0.00 | +0.00 | +0.02 | +0.00 | +0.00 |
| q03 | +0.50 | +0.00 | +0.03 | +0.00 | +0.00 |
| q04 | +0.00 | +0.00 | +0.01 | -0.33 | +0.00 |
| q05 | +0.00 | +0.00 | +0.20 | +0.00 | +0.00 |
| q06 | -0.33 | +0.00 | -0.07 | +0.00 | +0.00 |
| q07 | +0.10 | +0.00 | -0.16 | +0.00 | +0.00 |
| q08 | -0.10 | +0.00 | -0.04 | +0.00 | +0.06 |
| q09 | +0.11 | +0.00 | +0.12 | +0.00 | +0.00 |
| q10 | -0.06 | +0.00 | +0.03 | +0.00 | +0.00 |
| q11 | +0.06 | +0.00 | -0.05 | +0.00 | +0.06 |
| q12 | +0.11 | -0.33 | -0.07 | +0.00 | -0.31 |
| q13 | -0.17 | +0.00 | -0.07 | +0.00 | -0.05 |
| q14 | -0.17 | +0.22 | -0.02 | +0.00 | +0.00 |
| q15 | +0.06 | +0.00 | -0.09 | +0.00 | +0.00 |
| q16 | -0.08 | +0.00 | +0.02 | +0.50 | +0.00 |
| q17 | -0.40 | +0.00 | -0.05 | +0.00 | +0.00 |
| q18 | -0.50 | +0.14 | +0.00 | +1.00 | +0.00 |
