# Evaluation report: cmp_llama3.1-8b

- Cases: test split, 50 cases
- Models: ollama/llama3.1:8b
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | 50 |
| Failed (no valid answer; counted as wrong) | 0 | 0 |
| Decision accuracy (4 outcomes) | 52% | 30% |
|   clear cases | 60% (n=30) | 37% (n=30) |
|   borderline cases | 20% (n=15) | 20% (n=15) |
|   ineligible cases | 100% (n=5) | 20% (n=5) |
| Direction accuracy (refund vs decline) | 58% | 52% |
| Buyer-win cases right | 86% (n=22) | 50% (n=22) |
| Seller-win cases right | 25% (n=28) | 14% (n=28) |
| Eligibility accuracy | 100% | 86% |
| Ineligible cases flagged | 100% | 20% |
| Judged cases citing a clause | 100% | 0% |
| Cases with invented clause IDs (final answer) | 0% | 0% |
| Cases citing a real clause in the wrong format (final answer) | 0% | 100% |
| Judged cases where the model cited a clause it was not shown | 2% | 0% |
| Judged cases where the judge called search_policy | 0% | 0% |
| Escalated | 2% | 0% |
| Wrong decisions that were escalated | 4% | 0% |
| Right decisions that were escalated | 0% | 0% |
| Accuracy on cases not escalated | 53% | 30% |
| Seconds per case (median) | 14.98 | 3.66 |
| LLM calls per case | 1.8 | 1 |
| Tokens per case (in / out) | 3554 / 641 | 6595 / 155 |

**Gain over baseline:** +22.0 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 3 | 0 | 3 | 0 |
| Decline | 16 | 0 | 5 | 7 |

Wrong cases (agent): G006 (decline -> full_refund_with_return), G008 (partial_refund -> full_refund_with_return, escalated), G013 (decline -> full_refund_with_return), G019 (decline -> full_refund_with_return), G042 (decline -> full_refund_with_return), G043 (partial_refund -> full_refund_with_return), G054 (decline -> full_refund_with_return), G061 (decline -> partial_refund), G070 (decline -> full_refund_with_return), G076 (decline -> full_refund_with_return), G084 (decline -> full_refund_with_return), G111 (decline -> partial_refund), G116 (decline -> full_refund_with_return), G124 (partial_refund -> full_refund_with_return), G125 (decline -> full_refund_with_return), G126 (decline -> full_refund_with_return), G129 (decline -> full_refund_with_return), G134 (decline -> full_refund_with_return), G147 (decline -> partial_refund), G148 (decline -> partial_refund), G155 (decline -> full_refund_with_return), G158 (decline -> full_refund_with_return), G163 (decline -> partial_refund), S08 (decline -> full_refund_with_return)

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 5 | 0 | 11 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 6 | 0 |
| Decline | 0 | 0 | 24 | 4 |

Wrong cases (baseline): G013 (decline -> partial_refund), G018 (full_refund_with_return -> partial_refund), G019 (decline -> partial_refund), G025 (full_refund_with_return -> partial_refund), G031 (full_refund_with_return -> partial_refund), G041 (decline -> partial_refund), G042 (decline -> partial_refund), G046 (full_refund_with_return -> partial_refund), G051 (full_refund_with_return -> partial_refund), G054 (decline -> partial_refund), G061 (decline -> partial_refund), G065 (full_refund_with_return -> partial_refund), G070 (decline -> partial_refund), G081 (full_refund_with_return -> partial_refund), G084 (decline -> partial_refund), G088 (full_refund_with_return -> partial_refund), G102 (full_refund_with_return -> partial_refund), G107 (full_refund_with_return -> partial_refund), G109 (full_refund_with_return -> partial_refund), G111 (decline -> partial_refund), G116 (decline -> partial_refund), G125 (decline -> partial_refund), G126 (decline -> partial_refund), G129 (decline -> partial_refund), G134 (decline -> partial_refund), G146 (decline -> partial_refund), G147 (decline -> partial_refund), G148 (decline -> partial_refund), G155 (decline -> partial_refund), G158 (decline -> partial_refund), G163 (decline -> partial_refund), G165 (decline -> partial_refund), G173 (decline -> partial_refund), S17 (decline -> partial_refund), S18 (decline -> partial_refund)

## Citation check by hand

`citation_check_cmp_llama3.1-8b.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

