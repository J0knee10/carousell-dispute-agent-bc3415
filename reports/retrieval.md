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
