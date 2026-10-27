# Retrieval evaluation

Retrieval accuracy on 25 test queries (data/eval/retrieval_queries.jsonl)

| Mode | Hit@1 | Hit@1 | MRR |
|---|---|---|---|
| dense | 52% | 52% | 0.52 |
| lexical | 52% | 52% | 0.52 |
| hybrid | 76% | 76% | 0.76 |

Retrieval accuracy on 25 test queries (data/eval/retrieval_queries.jsonl)

| Mode | Hit@1 | Hit@3 | MRR |
|---|---|---|---|
| dense | 52% | 84% | 0.67 |
| lexical | 52% | 92% | 0.71 |
| hybrid | 76% | 88% | 0.81 |

Retrieval accuracy on 25 test queries (data/eval/retrieval_queries.jsonl)

| Mode | Hit@1 | Hit@5 | MRR |
|---|---|---|---|
| dense | 52% | 84% | 0.67 |
| lexical | 52% | 92% | 0.71 |
| hybrid | 76% | 96% | 0.83 |

Misses at k=3 (hybrid):
- colour shade is slightly different from the photos: expected ['BPR-03'], got ['BPR-02', 'RRR-03', 'WBP-05']
- item not received and it was sent by untracked mail: expected ['WBP-04'], got ['DPO-08', 'BPR-07', 'BPR-03']
- buyer already got a refund from the seller outside Carousell: expected ['BPR-03'], got ['DPO-11', 'DPO-03', 'DPO-06']
