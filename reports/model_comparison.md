# Model comparison

## What we compared, and why

The professor asked us to try different models and explain what we concluded.
We kept everything else fixed (the 50 held-out test cases, the prompts, the
decision guide, the code, temperature 0) and changed only the model that does
claim matching and judgement:

- `gemini-flash-lite-latest`: Google's small cloud model, free tier (our default since 28 Oct).
- `llama3.1:8b` (Meta) and `qwen3:8b` (Alibaba, thinking mode off): two widely used open models with 8 billion parameters, run on our own PC through Ollama, so no case data leaves the machine.

Each model ran the full agent and the single-prompt baseline. We then varied
the retrieval design on the local models (free to run) and probed it on Gemini
(10 cases, to save the free quota).

## Results

| Judge model | Agent | Baseline | Agent gain | Seconds per case (agent) |
|---|---|---|---|---|
| Gemini Flash-Lite (cloud) | 90% | 88% | +2 pts | 9 |
| Llama 3.1 8B (local) | 52% | 34% | +18 pts | 15 |
| Qwen 3 8B (local) | 48% | 44% | +4 pts | 19 |

**Gemini is far better at the judgement.** The two local models get about half
the cases right. Their problem is one-sided: of the 21 test cases that should be
declined and reach the LLM, Gemini refunded 1, Llama 19 and Qwen all 21,
including change-of-mind and damage-after-delivery claims. They do not apply the
policy's exclusions ("not covered: the buyer changed their mind", "wear on an
item listed as used"), and their claim matching labels ordinary complaints as
defects or "condition worse than listed". With Qwen, the single prompt never
declined a single case (0% of seller wins right).

**The agent's structure matters most for weak models.** The gain over the single
prompt is +2 points with Gemini but +18 with Llama and +4 with Qwen. Part of it
is the eligibility rules in code: the agent is 100% right on eligibility with
every model, while the single prompt gets 68% (Gemini), 86% (Llama) and 90%
(Qwen), and misses most of the 5 ineligible cases with the local models. The
rest is the step-by-step structure (claim matching, then judgement on each gap):
on clear cases Llama goes from 37% (single prompt) to 60% (agent).

**Citations.** With every model, the agent's final answers cite no invented
clause IDs, because code removes any clause the judge was not shown. Llama's
single prompt copied the clause heading into every citation ("[BPR-02] The item
is significantly not as described"); that is a real clause in the wrong format,
which we count separately from invention.

**Escalation.** Gemini's agent escalates 6% of cases and catches 2 of its 5
mistakes. Qwen escalates 22% but catches only 27% of its mistakes; Llama
escalates 2%. A small model's confidence score is not a reliable signal, so the
escalation rule protects much less with a local model.

## Retrieval design: per gap, agent-driven, or none

We tested whether retrieval changes the decisions or only the citations, with
three designs of the agent on both local models (free to run), and a 10-case
probe on Gemini:

| Retrieval design | Llama 3.1 8B | Qwen 3 8B | What happens |
|---|---|---|---|
| Per gap (default) | 52% | 48% | One search per gap before the judgement; the judge may call `search_policy` as a fallback |
| Agent-driven | 54% | 48% | Only general clauses up front; a planning step lists which gaps they cover and calls `search_policy` for the rest; then the judge decides (2.7 LLM calls a case instead of 1.8) |
| None (ablation) | 60% | 52% | No policy clauses at all |

- **Retrieval hardly moves accuracy for the 8B models**, and removing it even
  looks slightly better (4 and 2 cases out of 50, within noise). The decision
  guide in the prompt carries most of the judgement, and the retrieved clauses
  mostly list what *is* covered, which pushes small models further towards
  refunds (seller wins right: Llama 35% without clauses, 27% with).
- **Retrieval's value is grounding.** Without clauses the judge cannot cite
  anything, so the check escalates 90% of cases, and staff could not check the
  reasoning against the policy. With retrieval, every judged case cites a real
  clause and 90% of Gemini's citations support the decision.
- **How the tool gets used.** In the default design no model called
  `search_policy` on the test set: the per-gap searches already supplied the
  clauses. We first offered the tool in the agent-driven design as an optional
  field inside the judgement, and no model used it (0 of 28 Llama cases, 0 of
  10 Gemini cases), even with only general clauses: a model that must give an
  outcome in the same answer does not stop to search. With a separate planning
  step the tool is used: Llama searched in every case, Qwen in 9%, and Gemini
  in 3 of 10, each time for a gap the general clauses missed (for example "item
  not in listing description", which found the exclusion BPR-04). On those 10
  cases Gemini scored the same with either design (9 right).
- **Choice:** per-gap retrieval stays the default. It is as accurate as letting
  the model drive the search, needs one LLM call less per case, and its
  behaviour is predictable. The tool stays as a fallback for gaps the per-gap
  searches miss.

## Our choice, and why

1. **Gemini Flash-Lite stays the default judge.** It is the only model accurate enough (90%, 94% on cases it does not escalate) to be worth a staff member's time, and it is the fastest of the three. On the free tier it costs nothing; a deployment would use the paid tier (no training on prompts) after removing personal details.
2. **Llama 3.1 8B is the default local model.** It beat Qwen 3 8B (52% vs 48%), fits fully on our 8 GB GPU (Qwen spilled 11% onto the CPU) and is faster. It is a fallback for when data must stay on the machine or the cloud is down, not a replacement: with it, nearly every dispute would be refunded, which hurts honest sellers.
3. **Per-gap retrieval stays the default retrieval design,** with the `search_policy` tool as a fallback. Agent-driven retrieval was no more accurate on any model and costs one more LLM call per case (section above).

## Hardware and other limits

- Local runs used one desktop: Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti with 8 GB of GPU memory, Windows 11, Ollama with 4-bit models.
- 8 GB of GPU memory limits us to about 8 billion parameters. With a 10,240-token context window Llama takes 6.1 GB and runs fully on the GPU; Qwen takes 6.9 GB and ran 11% on the CPU. A 16k window pushed even Llama 13% onto the CPU, so we used 10,240 tokens, which fits the largest prompt (6,800 tokens).
- 14B-and-larger open models, which might close the gap with Gemini, would run largely on the CPU, several times slower; all runs had to finish in one night.
- Windows ran short of committed memory once while a model was loaded and a test suite ran next to it; that run resumed from where it stopped (the harness saves after every case).
- The free Gemini quota allows about one full test run a day, so the Gemini no-retrieval run and a full Gemini agent-driven run are left for another day.
- 50 cases is small (one case = 2 points) and the labels are still provisional. The test set has now been used three times and the local default was chosen on it, so the local numbers are slightly optimistic.

## What we would try next

- The paid OpenAI key (the client is ready): `uv run dispute-agent evaluate --provider openai --run cmp_openai`, then `compare`.
- A larger local model on a bigger GPU, or a few worked examples of declines in the prompt for the small models.
- The Gemini no-retrieval and full agent-driven runs when the free quota allows.

## The numbers

- Local hardware: Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti 8 GB, Windows 11; Ollama, 4-bit models, 10,240-token context
- Runs: [cmp_gemini-flash-lite](evaluation_cmp_gemini-flash-lite.md), [cmp_llama3.1-8b](evaluation_cmp_llama3.1-8b.md), [cmp_qwen3-8b](evaluation_cmp_qwen3-8b.md), [abl_llama3.1-8b_agentic](evaluation_abl_llama3.1-8b_agentic.md), [abl_qwen3-8b_agentic](evaluation_abl_qwen3-8b_agentic.md), [abl_llama3.1-8b_norag](evaluation_abl_llama3.1-8b_norag.md), [abl_qwen3-8b_norag](evaluation_abl_qwen3-8b_norag.md)
- Same held-out test cases and prompts for every model, temperature 0. Only the judge model changes.
- A case with no valid answer (for example invalid JSON twice) counts as wrong.

## Decision accuracy

| Model | Runs on | Agent | Baseline | Agent minus baseline | Agent clear / borderline / ineligible | Baseline clear / borderline / ineligible |
|---|---|---|---|---|---|---|
| `gemini-flash-lite-latest` | Google cloud API (free tier) | 90% | 88% | +2 pts | 93% / 80% / 100% | 97% / 80% / 60% |
| `llama3.1:8b` | This computer (local, via Ollama) | 52% | 34% | +18 pts | 60% / 20% / 100% | 37% / 33% / 20% |
| `qwen3:8b` | This computer (local, via Ollama) | 48% | 44% | +4 pts | 57% / 13% / 100% | 57% / 33% / 0% |
| `llama3.1:8b` (agent-driven retrieval) | This computer (local, via Ollama) | 54% | n/a | n/a | 60% / 27% / 100% | n/a |
| `qwen3:8b` (agent-driven retrieval) | This computer (local, via Ollama) | 48% | n/a | n/a | 57% / 13% / 100% | n/a |
| `llama3.1:8b` (no retrieval) | This computer (local, via Ollama) | 60% | n/a | n/a | 63% / 40% / 100% | n/a |
| `qwen3:8b` (no retrieval) | This computer (local, via Ollama) | 52% | n/a | n/a | 63% / 13% / 100% | n/a |

## Reliability

Unseen clause: the model cited a clause ID that does not exist or that it was never shown. For the agent this is counted before the citation check removes it; for the baseline (which has no check) it stays in the answer. Format errors (a real ID with the heading text pasted after it) are counted separately.

| Model | Failed answers (agent / baseline) | Eligibility right (agent / baseline) | Unseen clause cited (agent judge / baseline) | Citation format errors (baseline) | Agent escalated | Wrong agent decisions escalated | Agent accuracy when not escalated | Judge called search_policy |
|---|---|---|---|---|---|---|---|---|
| `gemini-flash-lite-latest` | 0 / 0 | 100% / 68% | 0% / 0% | 0% | 6% | 40% | 94% | 0% |
| `llama3.1:8b` | 0 / 0 | 100% / 86% | 2% / 0% | 100% | 2% | 4% | 53% | 0% |
| `qwen3:8b` | 0 / 0 | 100% / 90% | 0% / 0% | 0% | 22% | 27% | 51% | 0% |
| `llama3.1:8b` (agent-driven retrieval) | 0 / n/a | 100% / n/a | 4% / n/a | n/a | 10% | 9% | 53% | 100% |
| `qwen3:8b` (agent-driven retrieval) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 2% | 4% | 49% | 9% |
| `llama3.1:8b` (no retrieval) | 0 / n/a | 100% / n/a | 4% / n/a | n/a | 90% | 100% | 100% | 0% |
| `qwen3:8b` (no retrieval) | 0 / n/a | 100% / n/a | 0% / n/a | n/a | 90% | 100% | 100% | 0% |

## Speed and cost

| Model | Seconds per case, median (agent / baseline) | LLM calls per case (agent / baseline) | Tokens per case in / out (agent) | Tokens per case in / out (baseline) |
|---|---|---|---|---|
| `gemini-flash-lite-latest` | 9.12 / 4.47 | 1.8 / 1 | 2249 / 590 | 6691 / 153 |
| `llama3.1:8b` | 14.98 / 3.66 | 1.8 / 1 | 3554 / 641 | 6595 / 155 |
| `qwen3:8b` | 18.91 / 4.63 | 1.8 / 1 | 3524 / 628 | 6707 / 147 |
| `llama3.1:8b` (agent-driven retrieval) | 16.75 / n/a | 2.7 / n/a | 4590 / 721 | n/a |
| `qwen3:8b` (agent-driven retrieval) | 19.53 / n/a | 2.7 / n/a | 4216 / 664 | n/a |
| `llama3.1:8b` (no retrieval) | 13.54 / n/a | 1.8 / n/a | 2724 / 628 | n/a |
| `qwen3:8b` (no retrieval) | 16.93 / n/a | 1.8 / n/a | 2729 / 611 | n/a |
