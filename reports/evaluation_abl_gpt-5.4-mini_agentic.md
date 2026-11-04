# Evaluation report: abl_gpt-5.4-mini_agentic

- Cases: test split, 50 cases
- Models: openai/gpt-5.4-mini
- Confidence threshold for escalation: 0.7
- Labels used: final: 5. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 5 | n/a |
| Failed (no valid answer; counted as wrong) | 0 | n/a |
| Decision accuracy (4 outcomes) | 80% | n/a |
|   clear cases | 80% (n=5) | n/a |
|   borderline cases | n/a (n=0) | n/a |
|   ineligible cases | n/a (n=0) | n/a |
| Direction accuracy (refund vs decline) | 100% | n/a |
| Buyer-win cases right | 50% (n=2) | n/a |
| Seller-win cases right | 100% (n=3) | n/a |
| Eligibility accuracy | 100% | n/a |
| Ineligible cases flagged | n/a | n/a |
| Judged cases citing a clause | 100% | n/a |
| Cases with invented clause IDs (final answer) | 0% | n/a |
| Cases citing a real clause in the wrong format (final answer) | 0% | n/a |
| Judged cases where the model cited a clause it was not shown | 0% | n/a |
| Judged cases where the judge called search_policy | 0% | n/a |
| Escalated | 0% | n/a |
| Wrong decisions that were escalated | 0% | n/a |
| Right decisions that were escalated | 0% | n/a |
| Accuracy on cases not escalated | 80% | n/a |
| Seconds per case (median) | 22.28 | n/a |
| LLM calls per case | 3 | n/a |
| Tokens per case (in / out) | 4188 / 1027 | n/a |

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 1 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 1 | 0 | 0 | 0 |
| Decline | 0 | 0 | 0 | 3 |

Wrong cases (agent): G008 (partial_refund -> full_refund_with_return)

## Citation check by hand

`citation_check_abl_gpt-5.4-mini_agentic.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

