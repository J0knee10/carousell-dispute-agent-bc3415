# Evaluation report: abl_llama3.1-8b_norag

- Cases: test split, 50 cases
- Models: ollama/llama3.1:8b
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | n/a |
| Failed (no valid answer; counted as wrong) | 0 | n/a |
| Decision accuracy (4 outcomes) | 64% | n/a |
|   clear cases | 63% (n=30) | n/a |
|   borderline cases | 53% (n=15) | n/a |
|   ineligible cases | 100% (n=5) | n/a |
| Direction accuracy (refund vs decline) | 66% | n/a |
| Buyer-win cases right | 92% (n=24) | n/a |
| Seller-win cases right | 38% (n=26) | n/a |
| Eligibility accuracy | 100% | n/a |
| Ineligible cases flagged | 100% | n/a |
| Judged cases citing a clause | 0% | n/a |
| Cases with invented clause IDs (final answer) | 0% | n/a |
| Cases citing a real clause in the wrong format (final answer) | 0% | n/a |
| Judged cases where the model cited a clause it was not shown | 100% | n/a |
| Judged cases where the judge called search_policy | 0% | n/a |
| Escalated | 90% | n/a |
| Wrong decisions that were escalated | 100% | n/a |
| Right decisions that were escalated | 84% | n/a |
| Accuracy on cases not escalated | 100% | n/a |
| Seconds per case (median) | 13.54 | n/a |
| LLM calls per case | 1.8 | n/a |
| Tokens per case (in / out) | 2724 / 628 | n/a |

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 1 | 0 | 6 | 1 |
| Decline | 8 | 0 | 8 | 10 |

Wrong cases (agent): G008 (partial_refund -> full_refund_with_return, escalated), G013 (decline -> partial_refund, escalated), G019 (decline -> full_refund_with_return, escalated), G041 (decline -> partial_refund, escalated), G042 (decline -> full_refund_with_return, escalated), G054 (decline -> partial_refund, escalated), G061 (decline -> partial_refund, escalated), G070 (decline -> full_refund_with_return, escalated), G076 (decline -> partial_refund, escalated), G084 (decline -> full_refund_with_return, escalated), G116 (decline -> partial_refund, escalated), G125 (decline -> full_refund_with_return, escalated), G139 (partial_refund -> decline, escalated), G148 (decline -> partial_refund, escalated), G155 (decline -> full_refund_with_return, escalated), G158 (decline -> full_refund_with_return, escalated), G163 (decline -> partial_refund, escalated), S08 (decline -> full_refund_with_return, escalated)

## Citation check by hand

`citation_check_abl_llama3.1-8b_norag.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

