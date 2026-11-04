# Evaluation report: probe_gemini_rubric_norag

- Cases: test (first 25) split, 25 cases
- Models: gemini/gemini-flash-lite-latest
- Confidence threshold for escalation: 0.7
- Labels used: provisional: 25. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 25 | n/a |
| Failed (no valid answer; counted as wrong) | 0 | n/a |
| Decision accuracy (4 outcomes) | 88% | n/a |
|   clear cases | 88% (n=25) | n/a |
|   borderline cases | n/a (n=0) | n/a |
|   ineligible cases | n/a (n=0) | n/a |
| Direction accuracy (refund vs decline) | 88% | n/a |
| Buyer-win cases right | 80% (n=15) | n/a |
| Seller-win cases right | 100% (n=10) | n/a |
| Eligibility accuracy | 100% | n/a |
| Ineligible cases flagged | n/a | n/a |
| Judged cases citing a clause | 0% | n/a |
| Cases with invented clause IDs (final answer) | 0% | n/a |
| Cases citing a real clause in the wrong format (final answer) | 0% | n/a |
| Judged cases where the model cited a clause it was not shown | 0% | n/a |
| Judged cases where the judge called search_policy | 0% | n/a |
| Escalated | 100% | n/a |
| Wrong decisions that were escalated | 100% | n/a |
| Right decisions that were escalated | 100% | n/a |
| Accuracy on cases not escalated | n/a | n/a |
| Seconds per case (median) | 9.55 | n/a |
| LLM calls per case | 2 | n/a |
| Tokens per case (in / out) | 1434 / 631 | n/a |

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 11 | 0 | 0 | 1 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 1 | 2 |
| Decline | 0 | 0 | 0 | 10 |

Wrong cases (agent): G008 (partial_refund -> decline, escalated), G043 (partial_refund -> decline, escalated), G059 (full_refund_with_return -> decline, escalated)

## Citation check by hand

`citation_check_probe_gemini_rubric_norag.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

