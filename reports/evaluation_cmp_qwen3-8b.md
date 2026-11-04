# Evaluation report: cmp_qwen3-8b

- Cases: test split, 50 cases
- Models: ollama/qwen3:8b
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | 50 |
| Failed (no valid answer; counted as wrong) | 0 | 0 |
| Decision accuracy (4 outcomes) | 50% | 40% |
|   clear cases | 57% (n=30) | 57% (n=30) |
|   borderline cases | 20% (n=15) | 20% (n=15) |
|   ineligible cases | 100% (n=5) | 0% (n=5) |
| Direction accuracy (refund vs decline) | 56% | 44% |
| Buyer-win cases right | 86% (n=22) | 91% (n=22) |
| Seller-win cases right | 21% (n=28) | 0% (n=28) |
| Eligibility accuracy | 100% | 90% |
| Ineligible cases flagged | 100% | 0% |
| Judged cases citing a clause | 100% | 100% |
| Cases with invented clause IDs (final answer) | 0% | 0% |
| Cases citing a real clause in the wrong format (final answer) | 0% | 0% |
| Judged cases where the model cited a clause it was not shown | 22% | 0% |
| Judged cases where the judge called search_policy | 0% | 0% |
| Escalated | 22% | 0% |
| Wrong decisions that were escalated | 28% | 0% |
| Right decisions that were escalated | 16% | 0% |
| Accuracy on cases not escalated | 54% | 40% |
| Seconds per case (median) | 18.91 | 4.63 |
| LLM calls per case | 1.8 | 1 |
| Tokens per case (in / out) | 3524 / 628 | 6707 / 147 |

**Gain over baseline:** +10.0 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 3 | 0 | 3 | 0 |
| Decline | 17 | 0 | 5 | 6 |

Wrong cases (agent): G006 (decline -> partial_refund), G008 (partial_refund -> full_refund_with_return), G013 (decline -> full_refund_with_return), G019 (decline -> full_refund_with_return, escalated), G041 (decline -> full_refund_with_return), G042 (decline -> full_refund_with_return), G043 (partial_refund -> full_refund_with_return), G054 (decline -> full_refund_with_return, escalated), G061 (decline -> full_refund_with_return), G070 (decline -> full_refund_with_return, escalated), G076 (decline -> full_refund_with_return), G084 (decline -> full_refund_with_return), G111 (decline -> partial_refund), G116 (decline -> full_refund_with_return, escalated), G124 (partial_refund -> full_refund_with_return, escalated), G125 (decline -> full_refund_with_return), G126 (decline -> full_refund_with_return), G129 (decline -> full_refund_with_return), G146 (decline -> partial_refund), G147 (decline -> partial_refund, escalated), G148 (decline -> full_refund_with_return), G155 (decline -> full_refund_with_return), G158 (decline -> full_refund_with_return, escalated), G163 (decline -> partial_refund), S08 (decline -> full_refund_with_return)

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 2 | 0 | 4 | 0 |
| Decline | 11 | 1 | 16 | 0 |

Wrong cases (baseline): G006 (decline -> partial_refund), G008 (partial_refund -> full_refund_with_return), G013 (decline -> full_refund_with_return), G019 (decline -> full_refund_with_return), G041 (decline -> partial_refund), G042 (decline -> full_refund_with_return), G043 (partial_refund -> full_refund_with_return), G054 (decline -> partial_refund), G061 (decline -> partial_refund), G070 (decline -> full_refund_with_return), G076 (decline -> partial_refund), G084 (decline -> full_refund_with_return), G111 (decline -> partial_refund), G116 (decline -> partial_refund), G125 (decline -> full_refund_with_return), G126 (decline -> partial_refund), G129 (decline -> partial_refund), G134 (decline -> partial_refund), G146 (decline -> partial_refund), G147 (decline -> partial_refund), G148 (decline -> partial_refund), G155 (decline -> full_refund_with_return), G158 (decline -> full_refund_with_return), G163 (decline -> partial_refund), G165 (decline -> full_refund_with_return), G173 (decline -> full_refund_with_return), G176 (decline -> full_refund_without_return), S08 (decline -> full_refund_with_return), S17 (decline -> partial_refund), S18 (decline -> partial_refund)

## Citation check by hand

`citation_check_cmp_qwen3-8b.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

