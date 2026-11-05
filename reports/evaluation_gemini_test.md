# Evaluation report: gemini_test

- Cases: test split, 50 cases
- Models: gemini/gemini-flash-lite-latest
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | 50 |
| Failed (no valid answer; counted as wrong) | 0 | 0 |
| Decision accuracy (4 outcomes) | 82% | 84% |
|   clear cases | 93% (n=30) | 97% (n=30) |
|   borderline cases | 53% (n=15) | 67% (n=15) |
|   ineligible cases | 100% (n=5) | 60% (n=5) |
| Direction accuracy (refund vs decline) | 84% | 84% |
| Buyer-win cases right | 71% (n=24) | 88% (n=24) |
| Seller-win cases right | 92% (n=26) | 81% (n=26) |
| Eligibility accuracy | 100% | 84% |
| Ineligible cases flagged | 100% | 60% |
| Judged cases citing a clause | 100% | 100% |
| Cases with invented clause IDs (final answer) | 0% | 0% |
| Cases citing a real clause in the wrong format (final answer) | 0% | 0% |
| Judged cases where the model cited a clause it was not shown | 0% | 0% |
| Judged cases where the judge called search_policy | 0% | 0% |
| Escalated | 6% | 6% |
| Wrong decisions that were escalated | 33% | 12% |
| Right decisions that were escalated | 0% | 5% |
| Accuracy on cases not escalated | 87% | 85% |
| Seconds per case (median) | 9.02 | 4.53 |
| LLM calls per case | 1.8 | 1 |
| Tokens per case (in / out) | n/a / n/a | n/a / n/a |

**Gain over baseline:** -2.0 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 15 | 0 | 0 | 1 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 1 | 0 | 2 | 5 |
| Decline | 0 | 0 | 2 | 24 |

Wrong cases (agent): G008 (partial_refund -> full_refund_with_return), G059 (full_refund_with_return -> decline, escalated), G124 (partial_refund -> decline), G125 (decline -> partial_refund, escalated), G129 (partial_refund -> decline), G139 (partial_refund -> decline), G144 (partial_refund -> decline), G147 (partial_refund -> decline), G155 (decline -> partial_refund, escalated)

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 5 | 3 |
| Decline | 0 | 0 | 5 | 21 |

Wrong cases (baseline): G041 (decline -> partial_refund), G124 (partial_refund -> decline), G125 (decline -> partial_refund), G129 (partial_refund -> decline), G147 (partial_refund -> decline), G155 (decline -> partial_refund, escalated), S17 (decline -> partial_refund), S18 (decline -> partial_refund)

## Citation check by hand

`citation_check_gemini_test.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

