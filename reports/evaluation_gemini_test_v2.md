# Evaluation report: gemini_test_v2

- Cases: test split, 50 cases
- Models: gemini/gemini-flash-lite-latest
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | 50 |
| Failed (no valid answer; counted as wrong) | 0 | 0 |
| Decision accuracy (4 outcomes) | 88% | 90% |
|   clear cases | 93% (n=30) | 97% (n=30) |
|   borderline cases | 73% (n=15) | 87% (n=15) |
|   ineligible cases | 100% (n=5) | 60% (n=5) |
| Direction accuracy (refund vs decline) | 90% | 90% |
| Buyer-win cases right | 83% (n=24) | 96% (n=24) |
| Seller-win cases right | 92% (n=26) | 85% (n=26) |
| Eligibility accuracy | 100% | 74% |
| Ineligible cases flagged | 100% | 60% |
| Judged cases citing a clause | 98% | 100% |
| Cases with invented clause IDs (final answer) | 0% | 4% |
| Cases citing a real clause in the wrong format (final answer) | 0% | 0% |
| Judged cases where the model cited a clause it was not shown | 0% | 4% |
| Judged cases where the judge called search_policy | 0% | 0% |
| Escalated | 6% | 4% |
| Wrong decisions that were escalated | 33% | 20% |
| Right decisions that were escalated | 2% | 2% |
| Accuracy on cases not escalated | 92% | 92% |
| Seconds per case (median) | 8.94 | 4.52 |
| LLM calls per case | 1.8 | 1 |
| Tokens per case (in / out) | n/a / n/a | n/a / n/a |

**Gain over baseline:** -2.0 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 15 | 0 | 0 | 1 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 1 | 0 | 5 | 2 |
| Decline | 1 | 0 | 1 | 24 |

Wrong cases (agent): G008 (partial_refund -> full_refund_with_return), G059 (full_refund_with_return -> decline, escalated), G125 (decline -> partial_refund), G129 (partial_refund -> decline), G147 (partial_refund -> decline), G155 (decline -> full_refund_with_return, escalated)

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 15 | 0 | 0 | 1 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 8 | 0 |
| Decline | 0 | 0 | 4 | 22 |

Wrong cases (baseline): G025 (full_refund_with_return -> decline), G125 (decline -> partial_refund, escalated), G155 (decline -> partial_refund), S17 (decline -> partial_refund), S18 (decline -> partial_refund)

## Citation check by hand

`citation_check_gemini_test_v2.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

- Checked by Claude (an AI reviewer, not a person): 70 of 70 citations, 91% support the decision.

