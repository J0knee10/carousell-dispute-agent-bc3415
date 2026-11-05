# Model comparison

## What we compared, and why

The professor asked us to try different models and explain what we concluded.
We kept everything else fixed (the 50 held-out test cases, the prompts, the
decision guide, the code, temperature 0 where the model allows it) and changed
only the model that does claim matching and judgement:

- `gemini-flash-lite-latest`: Google's small cloud model, free tier (our default).
- `llama3.1:8b` (Meta) and `qwen3:8b` (Alibaba, thinking mode off): two widely used open models with 8 billion parameters, run on our own PC through Ollama, so no case data leaves the machine.

So the question is a free cloud model against open models that keep the data
on our own machine. OpenAI is not part of the comparison: the app uses
`gpt-5.4-mini` only as a fallback when a Gemini call fails, and our OpenAI key
is on the free usage tier (unpaid, about 50 requests a day per model), far
short of the roughly 500 requests one test run with its ablations needs.

Each model ran the full agent and the single-prompt baseline. We then varied
the retrieval design and the decision guide on the local models (free to run)
and probed them on Gemini (10 or 25 cases, to save the free quota).

Accuracy is measured against the team's hand labels (`final_outcome` in
`data/labels/labels.csv`): B1 labelled 25 test cases and B2 the other 25, on
4 Nov, after these runs. No case was labelled by both, so we cannot report
agreement between the labellers. The hand labels differ from the outcomes the
cases were written for on two cases: G134 (decline instead of a partial refund)
and G147 (a partial refund instead of a decline). Every run is a
single run on 50 cases, so one case is 2 points.

## Results

| Judge model | Agent | Baseline | Agent gain | Paired test (cases only the agent / only the baseline got right) | Seconds per case (agent) |
|---|---|---|---|---|---|
| Gemini Flash-Lite (cloud) | 90% | 88% | +2 pts | 5 vs 4, p = 1.00 | 9 (includes free-tier pacing) |
| Llama 3.1 8B (local) | 54% | 34% | +20 pts | 17 vs 7, p = 0.06 | 15 |
| Qwen 3 8B (local) | 52% | 44% | +8 pts | 6 vs 2, p = 0.29 | 19 |

**Gemini is far better at the judgement.** The two local models get about half
the cases right. Their problem is one-sided: of the 21 eligible test cases that
should be declined, Gemini's agent refunded 1, Llama's 19 and Qwen's 20,
including change-of-mind and damage-after-delivery claims. They do not apply the
policy's exclusions ("not covered: the buyer changed their mind", "wear on an
item listed as used"), and their claim matching labels ordinary complaints as
defects or "condition worse than listed". Qwen's single prompt refunded all 21.

**The agent is ahead of the single prompt with every model, but no gap is
statistically significant on 50 cases.** With Gemini the two are tied on
judgement (90% against 88%; 5 cases only the agent got right, 4 only the single
prompt; exact McNemar p = 1.00): equal on borderline cases (80%), the single
prompt slightly ahead on clear ones (97% against 93%), the agent ahead on the
5 ineligible ones (100% against 60%). The largest gap is Llama's (+20 points;
17 cases against 7, p = 0.06). Part of every gain is the eligibility rules in
code: the agent is 100% right on eligibility with every model, while the single
prompt gets 68% (Gemini), 86% (Llama) and 90% (Qwen). That 100% shows the rules
are implemented correctly; on our data it is guaranteed, because the cases'
order facts were generated from the same rules. Neither local model is usable
either way.

**Citations.** With every model, the agent's final answers cite no clause the
judge was not shown, because code removes them. Before that check, Qwen cited
BPR-05, a real clause it had not been given, in 10 of 45 judged cases, and those
10 were escalated. Llama's single prompt copied the clause heading into every
citation ("[BPR-02] The item is significantly not as described"); that is a real
clause in the wrong format, counted separately.

**Escalation.** Gemini's agent escalates 6% of cases (asking for more evidence,
or low confidence), and 2 of its 5 mistakes are among them; on the cases it does
not escalate it is right 94% of the time (that includes the 5 ineligible cases,
decided by the rules and right by construction). The baseline has no review
step: it counts as escalated only when its confidence is below 0.7 (1 of its 6
mistakes), so the two escalation figures measure different mechanisms. Qwen's 22% is almost entirely the
BPR-05 citations (10 of 11), not low confidence; Llama escalates 2%. The local
models never reported low confidence on their mistakes, so with them escalation
protects only against bad citations.

**Speed.** Gemini's 9 seconds a case include the free tier's pacing (at least
4.5 s between calls, so part of that time is waiting); the local models are not
paced. Local models cost nothing per call.

## Retrieval design: per gap, agent-driven, or none

We tested whether retrieval changes the decisions or only the citations, with
three designs of the agent on both local models, and a 10-case probe on Gemini:

| Retrieval design | Llama 3.1 8B | Qwen 3 8B | What happens |
|---|---|---|---|
| Per gap (default) | 54% | 52% | One search per gap before the judgement; the judge may call `search_policy` as a fallback |
| Agent-driven | 54% | 52% | Only general clauses up front; a planning step lists which gaps they cover and calls `search_policy` for the rest; then the judge decides (2.7 LLM calls a case instead of 1.8) |
| None (ablation) | 64% | 56% | No policy clauses at all |

- **With our full decision guide, retrieval hardly moves the local models'
  accuracy**, and removing it even looks better (5 and 2 cases out of 50; the
  seller wins the 8B models get right rise from 27% to 38% for Llama). The reason is in the prompt: the decision guide restates
  the policy's covered and not-covered lists, so the judge has the rules without
  retrieval. The next section removes them.
- **Without retrieval the citations are made up.** Both models still cited a
  clause in every case, almost always "BPR-02", the example ID in the prompt
  (40 of 48 citations for Llama, 45 of 46 for Qwen). The check removes them and
  escalates the case, so staff would get no usable policy reference.
- **How the tool gets used.** In the default design no model called
  `search_policy` on the test set: the per-gap searches already supplied the
  clauses. The tool is a structured-output tool call: the model returns the
  tool's arguments as JSON and code runs the search, which works the same with
  every provider. We first offered it in the agent-driven design as
  an optional field inside the judgement, and no model used it (0 of 40 judged
  Llama cases, 0 of 10 Gemini cases; [details](../reports/tool_field_experiment.md)): a
  model that must give an outcome in the same answer does not stop to search.
  With a separate planning step the tool is used: Llama searched in every case,
  Qwen in 9%, and Gemini in 3 of 10, each time for a gap the general clauses
  missed (for example "item not in listing description", which found the
  exclusion in BPR-04). On those 10 cases Gemini scored the same with either
  design (9 right; [probe report](../reports/evaluation_probe_gemini_agentic.md)).
- **Choice:** per-gap retrieval stays the default. It is as accurate as letting
  the model drive the search, needs one LLM call less per case, and its
  behaviour is predictable. The tool stays as a fallback for gaps the per-gap
  searches miss.

## Decision guide: does retrieval matter when the prompt does not restate the policy?

Our decision guide restates the policy's covered and not-covered lists, so the
judge has the rules even without retrieval. To test whether retrieval can carry
the policy on its own, we ran a **rubric-only** guide (`--guide rubric`): the
judge keeps only our outcome rubric (when to refund, partially refund or
decline) and is told that what is covered must come from the clauses it is given.

| Decision guide, retrieval | Llama 3.1 8B (50 cases) | Qwen 3 8B (50 cases) | Gemini Flash-Lite (first 25 cases, all clear ones) | Where the coverage rules come from |
|---|---|---|---|---|
| Full guide, per gap (default) | 54% | 52% | 92% (23 of 25) | The prompt and the retrieved clauses |
| Full guide, no retrieval | 64% | 56% | not run | The prompt only |
| Rubric only, per gap | 58% | 54% | 92% (23 of 25) | The retrieved clauses only |
| Rubric only, no retrieval | 60% | 58% | 88% (22 of 25) | Nowhere: only the outcome rubric and the model's own knowledge |

- **The local models cannot tell us.** Every 8B variant lands at 52–64% (a
  spread of 6 cases) and gets only 23–38% of seller wins right: they refund
  almost everything whatever the prompt holds, so neither the guide nor
  retrieval measurably changes their decisions.
- **For Gemini, retrieval can replace the restated policy** (rubric only with
  retrieval matched the full guide: 23 of 25). Without retrieval it dropped one
  case: it declined two missing-accessory claims (G008, G043) that the policy
  covers as incomplete items. On these cases the effect on accuracy is small,
  because the policy is short and its rules are close to common sense.
- **Without retrieval nothing can be cited.** Gemini then cited no clause at all
  (all 25 cases were escalated for having no valid citation), while the 8B
  models made citations up.
- **Conclusion:** on this test set, retrieval is not what makes the decisions
  accurate; Gemini mostly knows the rules. Its value is that every
  recommendation is grounded in a clause staff can check, that coverage the
  model would miss (incomplete items) is in front of it, and that a policy
  change only needs the policy text re-indexed (and can be tested first with
  the what-if page). A larger corpus (more help-centre pages, category rules)
  would make retrieval matter more. The Gemini probe covers only the first 25
  test cases, which are all clear cases; the borderline ones, where policy
  detail matters most, are not in it.

## Our choice, and why

1. **Gemini Flash-Lite is the judge.** It is by far the most accurate of the models we tested (90% against 54% and 52%, and 94% on the cases it does not escalate), and on the free tier it costs nothing. A deployment would use the paid tier (no training on prompts) after removing personal details.
2. **The local models are not good enough to judge.** Llama 3.1 8B is the default local model: level with Qwen 3 8B (54% vs 52%), faster, and it fits fully on our 8 GB GPU (Qwen spilled 11% onto the CPU). It is an option only when case data must stay on the machine, not a replacement: with it, nearly every dispute would be refunded, which hurts honest sellers.
3. **Per-gap retrieval stays the default retrieval design,** with the `search_policy` tool as a fallback: agent-driven retrieval was no more accurate on any model and costs one more LLM call per case.
4. **OpenAI keeps the cloud app available, nothing more.** When a Gemini call fails (free quota used up, or the service overloaded), the app makes that call with `gpt-5.4-mini` on the key's free usage tier (about 50 requests a day, so roughly 15 to 25 cases). Its judgements were not tested on our test set, so the app labels them "(fallback)" and staff should treat them with extra care.

## Hardware and other limits

- Local runs used one desktop: Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti with 8 GB of GPU memory, Windows 11, Ollama with 4-bit models.
- 8 GB of GPU memory limits us to about 8 billion parameters. With a 10,240-token context window Llama takes 6.1 GB and runs fully on the GPU; Qwen takes 6.9 GB and ran 11% on the CPU. A 16k window pushed even Llama 13% onto the CPU, so we used 10,240 tokens, which fits the largest prompt (6,800 tokens).
- "Cloud vs local" here is also "a strong small cloud model vs 8B models at 4-bit": the comparison cannot separate the two. 14B-and-larger open models, which might close the gap, would run largely on the CPU, several times slower, and all runs had to finish in one night.
- Windows ran short of committed memory once while a model was loaded and a test suite ran next to it; that run resumed from where it stopped (the harness saves after every case).
- The free Gemini quota allows about one full test run a day, so the Gemini rubric-only runs cover the first 25 test cases and the agent-driven run 10; the full-guide no-retrieval run and full-length versions are left for another day.
- Single runs on 50 cases, no repeat runs. The test set has now been used three times and the local default was chosen on it, so the local numbers are slightly optimistic. The hand labels were made after the runs, one person per case.

## What we would try next

- The Gemini ablations on all 50 cases when the free quota allows: `uv run dispute-agent evaluate --provider gemini --system agent --guide rubric --run abl_gemini_rubric` (and with `--no-retrieval`).
- Double-label some cases (both B1 and B2) to measure agreement, and repeat runs to measure run-to-run variation.
- A larger local model on a bigger GPU, or a few worked examples of declines in the prompt for the small models.

## The numbers

- Local hardware: Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti 8 GB, Windows 11; Ollama, 4-bit models, 10,240-token context
- Runs: [cmp_gemini-flash-lite](evaluation_cmp_gemini-flash-lite.md), [cmp_llama3.1-8b](evaluation_cmp_llama3.1-8b.md), [cmp_qwen3-8b](evaluation_cmp_qwen3-8b.md), [abl_llama3.1-8b_agentic](evaluation_abl_llama3.1-8b_agentic.md), [abl_qwen3-8b_agentic](evaluation_abl_qwen3-8b_agentic.md), [probe_gemini_agentic](evaluation_probe_gemini_agentic.md), [abl_llama3.1-8b_norag](evaluation_abl_llama3.1-8b_norag.md), [abl_qwen3-8b_norag](evaluation_abl_qwen3-8b_norag.md), [abl_llama3.1-8b_rubric](evaluation_abl_llama3.1-8b_rubric.md), [abl_qwen3-8b_rubric](evaluation_abl_qwen3-8b_rubric.md), [probe_gemini_rubric](evaluation_probe_gemini_rubric.md), [abl_llama3.1-8b_rubric_norag](evaluation_abl_llama3.1-8b_rubric_norag.md), [abl_qwen3-8b_rubric_norag](evaluation_abl_qwen3-8b_rubric_norag.md), [probe_gemini_rubric_norag](evaluation_probe_gemini_rubric_norag.md)
- Same held-out test cases and prompts for every model, temperature 0. Only the judge model changes.
- A case with no valid answer (for example invalid JSON twice) counts as wrong.
- Paired test: cases only the agent got right vs cases only the baseline got right, with an exact McNemar test (p below 0.05 means the difference is unlikely to be chance on these 50 cases).
- Gemini's seconds per case include the free-tier pacing (at least 4.5 s between calls); local models are not paced.

## Decision accuracy

| Model | Runs on | Agent | Baseline | Agent minus baseline | Paired test | Agent clear / borderline / ineligible | Baseline clear / borderline / ineligible |
|---|---|---|---|---|---|---|---|
| `gemini-flash-lite-latest` | Google cloud API (free tier) | 90% | 88% | +2 pts | 5 vs 4 cases, p = 1.00 | 93% / 80% / 100% | 97% / 80% / 60% |
| `llama3.1:8b` | This computer (local, via Ollama) | 54% | 34% | +20 pts | 17 vs 7 cases, p = 0.06 | 60% / 27% / 100% | 37% / 33% / 20% |
| `qwen3:8b` | This computer (local, via Ollama) | 52% | 44% | +8 pts | 6 vs 2 cases, p = 0.29 | 57% / 27% / 100% | 57% / 33% / 0% |
| `llama3.1:8b` (agent-driven retrieval) | This computer (local, via Ollama) | 54% | n/a | n/a | n/a | 60% / 27% / 100% | n/a |
| `qwen3:8b` (agent-driven retrieval) | This computer (local, via Ollama) | 52% | n/a | n/a | n/a | 57% / 27% / 100% | n/a |
| `gemini-flash-lite-latest` (agent-driven retrieval, first 10 cases only) | Google cloud API (free tier) | 90% | n/a | n/a | n/a | 90% / n/a / n/a | n/a |
| `llama3.1:8b` (no retrieval) | This computer (local, via Ollama) | 64% | n/a | n/a | n/a | 63% / 53% / 100% | n/a |
| `qwen3:8b` (no retrieval) | This computer (local, via Ollama) | 56% | n/a | n/a | n/a | 63% / 27% / 100% | n/a |
| `llama3.1:8b` (rubric-only guide) | This computer (local, via Ollama) | 58% | n/a | n/a | n/a | 63% / 33% / 100% | n/a |
| `qwen3:8b` (rubric-only guide) | This computer (local, via Ollama) | 54% | n/a | n/a | n/a | 60% / 27% / 100% | n/a |
| `gemini-flash-lite-latest` (rubric-only guide, first 25 cases only) | Google cloud API (free tier) | 92% | n/a | n/a | n/a | 92% / n/a / n/a | n/a |
| `llama3.1:8b` (rubric-only guide, no retrieval) | This computer (local, via Ollama) | 60% | n/a | n/a | n/a | 67% / 33% / 100% | n/a |
| `qwen3:8b` (rubric-only guide, no retrieval) | This computer (local, via Ollama) | 58% | n/a | n/a | n/a | 67% / 27% / 100% | n/a |
| `gemini-flash-lite-latest` (rubric-only guide, no retrieval, first 25 cases only) | Google cloud API (free tier) | 88% | n/a | n/a | n/a | 88% / n/a / n/a | n/a |

## Reliability

Unseen clause: the model cited a clause ID that does not exist or that it was never shown. For the agent this is counted before the citation check removes it; for the baseline (which has no check) it stays in the answer. Format errors (a real ID with the heading text pasted after it) are counted separately.

| Model | Failed answers (agent / baseline) | Eligibility right (agent / baseline) | Unseen clause cited (agent judge / baseline) | Citation format errors (baseline) | Agent escalated | Wrong agent decisions escalated | Agent accuracy when not escalated | Judge called search_policy | Main escalation reasons (agent) |
|---|---|---|---|---|---|---|---|---|---|
| `gemini-flash-lite-latest` | 0 / 0 | 100% / 68% | 0% / 0% | 0% | 6% | 40% | 94% | 0% | More evidence needed (3); Low confidence (2) |
| `llama3.1:8b` | 0 / 0 | 100% / 86% | 2% / 0% | 100% | 2% | 4% | 55% | 0% | Cited clauses that were not retrieved (1) |
| `qwen3:8b` | 0 / 0 | 100% / 90% | 22% / 0% | 0% | 22% | 25% | 54% | 0% | Cited clauses that were not retrieved (10); More evidence needed (1) |
| `llama3.1:8b` (agent-driven retrieval) | 0 / n/a | 100% / n/a | 11% / n/a | n/a | 10% | 9% | 53% | 100% | Cited clauses that were not retrieved (5) |
| `qwen3:8b` (agent-driven retrieval) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 2% | 4% | 53% | 9% | More evidence needed (1) |
| `gemini-flash-lite-latest` (agent-driven retrieval, first 10 cases only) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 10% | 0% | 89% | 30% | No valid policy citation supports the outcome (1) |
| `llama3.1:8b` (no retrieval) | 0 / n/a | 100% / n/a | 100% / n/a | n/a | 90% | 100% | 100% | 0% | Cited clauses that were not retrieved (45); No valid policy citation supports the outcome (45) |
| `qwen3:8b` (no retrieval) | 0 / n/a | 100% / n/a | 100% / n/a | n/a | 90% | 100% | 100% | 0% | Cited clauses that were not retrieved (45); No valid policy citation supports the outcome (45) |
| `llama3.1:8b` (rubric-only guide) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 4% | 0% | 56% | 0% | Declines although a gap was judged significant (1); Refunds although no gap was judged significant (1) |
| `qwen3:8b` (rubric-only guide) | 0 / n/a | 100% / n/a | 20% / n/a | n/a | 20% | 17% | 52% | 0% | Cited clauses that were not retrieved (9); More evidence needed (1) |
| `gemini-flash-lite-latest` (rubric-only guide, first 25 cases only) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 12% | 50% | 96% | 0% | Refunds although no gap was judged significant (1); Low confidence (1) |
| `llama3.1:8b` (rubric-only guide, no retrieval) | 0 / n/a | 100% / n/a | 100% / n/a | n/a | 90% | 100% | 100% | 0% | Cited clauses that were not retrieved (45); No valid policy citation supports the outcome (45) |
| `qwen3:8b` (rubric-only guide, no retrieval) | 0 / n/a | 100% / n/a | 100% / n/a | n/a | 90% | 100% | 100% | 0% | Cited clauses that were not retrieved (45); No valid policy citation supports the outcome (45) |
| `gemini-flash-lite-latest` (rubric-only guide, no retrieval, first 25 cases only) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 100% | 100% | n/a | 0% | No valid policy citation supports the outcome (25); Low confidence (3) |

## Speed and cost

| Model | Seconds per case, median (agent / baseline) | LLM calls per case (agent / baseline) | Tokens per case in / out (agent) | Tokens per case in / out (baseline) |
|---|---|---|---|---|
| `gemini-flash-lite-latest` | 9.12 / 4.47 | 1.8 / 1 | 2249 / 590 | 6691 / 153 |
| `llama3.1:8b` | 14.98 / 3.66 | 1.8 / 1 | 3554 / 641 | 6595 / 155 |
| `qwen3:8b` | 18.91 / 4.63 | 1.8 / 1 | 3524 / 628 | 6707 / 147 |
| `llama3.1:8b` (agent-driven retrieval) | 16.75 / n/a | 2.7 / n/a | 4590 / 721 | n/a |
| `qwen3:8b` (agent-driven retrieval) | 19.53 / n/a | 2.7 / n/a | 4216 / 664 | n/a |
| `gemini-flash-lite-latest` (agent-driven retrieval, first 10 cases only) | 14.04 / n/a | 3 / n/a | 3135 / 756 | n/a |
| `llama3.1:8b` (no retrieval) | 13.54 / n/a | 1.8 / n/a | 2724 / 628 | n/a |
| `qwen3:8b` (no retrieval) | 16.93 / n/a | 1.8 / n/a | 2729 / 611 | n/a |
| `llama3.1:8b` (rubric-only guide) | 14.73 / n/a | 1.8 / n/a | 3384 / 642 | n/a |
| `qwen3:8b` (rubric-only guide) | 17.98 / n/a | 1.8 / n/a | 3352 / 622 | n/a |
| `gemini-flash-lite-latest` (rubric-only guide, first 25 cases only) | 8.92 / n/a | 2 / n/a | 2329 / 663 | n/a |
| `llama3.1:8b` (rubric-only guide, no retrieval) | 13.57 / n/a | 1.8 / n/a | 2554 / 630 | n/a |
| `qwen3:8b` (rubric-only guide, no retrieval) | 17.61 / n/a | 1.8 / n/a | 2557 / 613 | n/a |
| `gemini-flash-lite-latest` (rubric-only guide, no retrieval, first 25 cases only) | 9.55 / n/a | 2 / n/a | 1434 / 631 | n/a |
