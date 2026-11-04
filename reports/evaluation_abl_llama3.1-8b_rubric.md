# Evaluation report: abl_llama3.1-8b_rubric

- Cases: test split, 50 cases
- Models: ollama/llama3.1:8b
- Confidence threshold for escalation: 0.7
- Labels used: final: 50. 'provisional' means the outcome the case was written for, not yet checked by the labellers.

## Headline numbers

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Cases scored | 50 | n/a |
| Failed (no valid answer; counted as wrong) | 0 | n/a |
| Decision accuracy (4 outcomes) | 58% | n/a |
|   clear cases | 63% (n=30) | n/a |
|   borderline cases | 33% (n=15) | n/a |
|   ineligible cases | 100% (n=5) | n/a |
| Direction accuracy (refund vs decline) | 62% | n/a |
| Buyer-win cases right | 92% (n=24) | n/a |
| Seller-win cases right | 27% (n=26) | n/a |
| Eligibility accuracy | 100% | n/a |
| Ineligible cases flagged | 100% | n/a |
| Judged cases citing a clause | 100% | n/a |
| Cases with invented clause IDs (final answer) | 0% | n/a |
| Cases citing a real clause in the wrong format (final answer) | 0% | n/a |
| Judged cases where the model cited a clause it was not shown | 0% | n/a |
| Judged cases where the judge called search_policy | 0% | n/a |
| Escalated | 4% | n/a |
| Wrong decisions that were escalated | 0% | n/a |
| Right decisions that were escalated | 7% | n/a |
| Accuracy on cases not escalated | 56% | n/a |
| Seconds per case (median) | 14.73 | n/a |
| LLM calls per case | 1.8 | n/a |
| Tokens per case (in / out) | 3384 / 642 | n/a |

## Confusion matrix: agent

Rows are the label, columns the prediction.

| Label \ Predicted | Full refund with return | Full refund without return | Partial refund | Decline |
|---|---|---|---|---|
| Full refund with return | 16 | 0 | 0 | 0 |
| Full refund without return | 0 | 0 | 0 | 0 |
| Partial refund | 2 | 0 | 6 | 0 |
| Decline | 9 | 0 | 10 | 7 |

Wrong cases (agent): G006 (decline -> partial_refund), G008 (partial_refund -> full_refund_with_return), G013 (decline -> partial_refund), G019 (decline -> full_refund_with_return), G042 (decline -> full_refund_with_return), G043 (partial_refund -> full_refund_with_return), G054 (decline -> full_refund_with_return), G070 (decline -> full_refund_with_return), G076 (decline -> partial_refund), G084 (decline -> full_refund_with_return), G111 (decline -> partial_refund), G116 (decline -> full_refund_with_return), G125 (decline -> partial_refund), G126 (decline -> full_refund_with_return), G134 (decline -> partial_refund), G146 (decline -> partial_refund), G148 (decline -> partial_refund), G155 (decline -> full_refund_with_return), G158 (decline -> partial_refund), G163 (decline -> partial_refund), S08 (decline -> full_refund_with_return)

## Citation check by hand

`citation_check_abl_llama3.1-8b_rubric.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.

