# Evaluation report: gemini_seed

- Cases: seed split, 20 cases
- Models: gemini/gemini-flash-lite-latest
- Confidence threshold for escalation: 0.7
- Labels used: provisional: 20. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 20 | 20 |
| Decision accuracy (4 outcomes) | 100% | 80% |
|   clear cases | 100% (n=10) | 90% (n=10) |
|   borderline cases | 100% (n=6) | 83% (n=6) |
|   ineligible cases | 100% (n=4) | 50% (n=4) |
| Direction accuracy (refund vs decline) | 100% | 80% |
| Buyer-win cases right | 100% (n=8) | 100% (n=8) |
| Seller-win cases right | 100% (n=12) | 67% (n=12) |
| Eligibility accuracy | 100% | 85% |
| Ineligible cases flagged | 100% | 50% |
| Judged cases citing a clause | 100% | 100% |
| Cases with invented clause IDs | 0% | 0% |
| Escalated | 0% | 5% |
| Wrong decisions that were escalated | n/a | 25% |
| Right decisions that were escalated | 0% | 0% |
| Accuracy on cases not escalated | 100% | 84% |
| Seconds per case (median) | 8.88 | 4.5 |
| LLM calls per case | 1.5 | 1 |

**Gain over baseline:** +20.0 percentage points in decision accuracy.

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 4 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 4 | 0 |
| Decline | 0 | 0 | 0 | 12 |

## Confusion matrix: baseline

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 4 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 0 | 0 | 4 | 0 |
| Decline | 0 | 0 | 4 | 8 |

Wrong cases (baseline): S09 (decline -> partial_refund), S15 (decline -> partial_refund, escalated), S17 (decline -> partial_refund), S18 (decline -> partial_refund)

## Citation check by hand

`citation_check_gemini_seed.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

