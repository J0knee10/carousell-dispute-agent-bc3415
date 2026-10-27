# Evaluation report: dev_borderline_v1

- Cases: dev (cosmetic_undisclosed_minor, wear_disclosed, subjective_condition, minor_shade) split, 36 cases
- Models: gemini/gemini-flash-lite-latest
- Confidence threshold for escalation: 0.7
- Labels used: provisional: 36. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 36 | 36 |
| Decision accuracy (4 outcomes) | 81% | 78% |
|   clear cases | n/a (n=0) | n/a (n=0) |
|   borderline cases | 81% (n=36) | 78% (n=36) |
|   ineligible cases | n/a (n=0) | n/a (n=0) |
| Direction accuracy (refund vs decline) | 81% | 78% |
| Buyer-win cases right | 14% (n=7) | 14% (n=7) |
| Seller-win cases right | 97% (n=29) | 93% (n=29) |
| Eligibility accuracy | 100% | 83% |
| Ineligible cases flagged | n/a | n/a |
| Judged cases citing a clause | 100% | 100% |
| Cases with invented clause IDs | 0% | 0% |
| Escalated | 0% | 0% |
| Wrong decisions that were escalated | 0% | 0% |
| Right decisions that were escalated | 0% | 0% |
| Accuracy on cases not escalated | 81% | 78% |
| Seconds per case (median) | 8.95 | 4.7 |
| LLM calls per case | 2 | 1 |

**Gain over baseline:** +2.8 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 0 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 1 | 6 |
| Decline | 1 | 0 | 0 | 28 |

Wrong cases (agent): G113 (decline -> full_refund_with_return), G114 (partial_refund -> decline), G119 (partial_refund -> decline), G149 (partial_refund -> decline), G154 (partial_refund -> decline), G159 (partial_refund -> decline), G164 (partial_refund -> decline)

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 0 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 1 | 6 |
| Decline | 1 | 0 | 1 | 27 |

Wrong cases (baseline): G113 (decline -> full_refund_with_return), G114 (partial_refund -> decline), G119 (partial_refund -> decline), G143 (decline -> partial_refund), G149 (partial_refund -> decline), G154 (partial_refund -> decline), G159 (partial_refund -> decline), G164 (partial_refund -> decline)

## Citation check by hand

`citation_check_dev_borderline_v1.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

