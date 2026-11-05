# Retrieval evaluation

Retrieval accuracy on 25 test queries (`data/eval/retrieval_queries.jsonl`). Hit@k: the clause that answers the query is in the top k results. MRR: mean of 1 / rank of that clause within the top 3 (0 if missing). The agent takes the top 3 per query.

| Mode | Hit@1 | Hit@3 | Hit@5 | MRR (top 3) |
|---|---|---|---|---|
| dense | 52% | 84% | 84% | 0.67 |
| lexical | 52% | 92% | 92% | 0.71 |
| hybrid | 76% | 88% | 96% | 0.81 |

Misses at k=3 (hybrid):
- colour shade is slightly different from the photos: expected ['BPR-03'], got ['BPR-02', 'RRR-03', 'WBP-05']
- item not received and it was sent by untracked mail: expected ['WBP-04'], got ['DPO-08', 'BPR-07', 'BPR-03']
- buyer already got a refund from the seller outside Carousell: expected ['BPR-03'], got ['DPO-11', 'DPO-03', 'DPO-06']

## Why hybrid search finds fewer answers in the top 3 than keyword search

Hybrid search misses 3 of 25 queries in the top 3, keyword search alone 2 and embeddings alone 4. Hybrid search merges the two rankings by reciprocal rank fusion, which favours clauses that both methods rank fairly high, so a clause that only one method ranks high can be pushed down. That happened on these queries, where one method alone had the answer in its top 3:

- colour shade is slightly different from the photos: the answer (BPR-03) is ranked below 8 by keyword search, 1 by embeddings and 7 by hybrid search.
- item not received and it was sent by untracked mail: the answer (WBP-04) is ranked 3 by keyword search, 6 by embeddings and 4 by hybrid search.

The trade is worth it for the agent: hybrid search puts the right clause first far more often (Hit@1 76% against 52% and 52%) and has the best MRR (0.81), so the clause the judge reads first is usually the right one.
