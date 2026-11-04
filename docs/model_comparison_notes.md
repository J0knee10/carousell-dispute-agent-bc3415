## What we compared, and why

The professor asked us to try different models and explain what we concluded.
We kept everything else fixed (the 50 held-out test cases, the prompts, the
decision guide, the code, temperature 0) and changed only the model that does
claim matching and judgement:

- `gemini-flash-lite-latest`: Google's small cloud model, free tier (our default since 28 Oct).
- `llama3.1:8b` (Meta) and `qwen3:8b` (Alibaba, thinking mode off): two widely used open models with 8 billion parameters, run on our own PC through Ollama, so no case data leaves the machine.

Each model ran the full agent and the single-prompt baseline. We then varied
the retrieval design and the decision guide on the local models (free to run)
and probed one design on Gemini (10 cases, to save the free quota).

Accuracy means agreement with the provisional labels: the outcome each
synthetic dispute was written for (two team members have not finished labelling
by hand). Every run is a single run on 50 cases, so one case is 2 points.

## Results

| Judge model | Agent | Baseline | Agent gain | Paired test (cases only the agent / only the baseline got right) | Seconds per case (agent) |
|---|---|---|---|---|---|
| Gemini Flash-Lite (cloud) | 90% | 88% | +2 pts | 5 vs 4, p = 1.00 | 9 (includes free-tier pacing) |
| Llama 3.1 8B (local) | 52% | 34% | +18 pts | 17 vs 8, p = 0.11 | 15 |
| Qwen 3 8B (local) | 48% | 44% | +4 pts | 5 vs 3, p = 0.73 | 19 |

**Gemini is far better at the judgement.** The two local models get about half
the cases right. Their problem is one-sided: of the 21 test cases that should be
declined and reach the LLM, Gemini refunded 1, Llama 19 and Qwen all 21,
including change-of-mind and damage-after-delivery claims. They do not apply the
policy's exclusions ("not covered: the buyer changed their mind", "wear on an
item listed as used"), and their claim matching labels ordinary complaints as
defects or "condition worse than listed". With Qwen, the single prompt never
declined a single case (0% of seller wins right).

**The agent beats the single prompt with every model, but no gap is
statistically significant on 50 cases.** The largest is Llama's (+18 points;
17 cases only the agent got right against 8, exact McNemar p = 0.11). Part of it
is the eligibility rules in code: the agent is 100% right on eligibility with
every model, while the single prompt gets 68% (Gemini), 86% (Llama) and 90%
(Qwen) and misses most of the 5 ineligible cases with the local models. That
100% shows the rules are implemented correctly; it is guaranteed on our data,
because the cases' order facts were generated from the same rules. On clear
cases Llama goes from 37% (single prompt) to 60% (agent). Neither local model
is usable: the agent's lead does not change that.

**Citations.** With every model, the agent's final answers cite no clause the
judge was not shown, because code removes them. Before that check, Qwen cited
BPR-05, a real clause it had not been given, in 10 of 45 judged cases, and those 10 were escalated. Llama's single
prompt copied the clause heading into every citation ("[BPR-02] The item is
significantly not as described"); that is a real clause in the wrong format,
counted separately.

**Escalation.** Gemini's agent escalates 6% of cases, mostly because it asks
for more evidence, and 2 of its 5 mistakes are among them. Qwen's 22% is almost
entirely the citation check catching BPR-05 (10 of 11 escalations), not low
confidence; Llama escalates 2%. Neither local model ever reported low
confidence on its mistakes, so with them the escalation rule protects only
against bad citations.

**Speed.** Gemini's 9 seconds a case include the free tier's pacing (at least
4.5 s between calls, so part of that time is waiting); the local models are
not paced. Local models cost nothing per call.

## Retrieval design: per gap, agent-driven, or none

We tested whether retrieval changes the decisions or only the citations, with
three designs of the agent on both local models, and a 10-case probe on Gemini:

| Retrieval design | Llama 3.1 8B | Qwen 3 8B | What happens |
|---|---|---|---|
| Per gap (default) | 52% | 48% | One search per gap before the judgement; the judge may call `search_policy` as a fallback |
| Agent-driven | 54% | 48% | Only general clauses up front; a planning step lists which gaps they cover and calls `search_policy` for the rest; then the judge decides (2.7 LLM calls a case instead of 1.8) |
| None (ablation) | 60% | 52% | No policy clauses at all |

- **With our full decision guide, retrieval hardly moves the local models'
  accuracy**, and removing it even looks slightly better (4 and 2 cases out of
  50, within noise). The reason is in the prompt: the decision guide restates
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
  Gemini, Ollama and OpenAI. We first offered it in the agent-driven design as
  an optional field inside the judgement, and no model used it (0 of 40 judged
  Llama cases, 0 of 10 Gemini cases; [details](tool_field_experiment.md)): a
  model that must give an outcome in the same answer does not stop to search.
  With a separate planning step the tool is used: Llama searched in every case,
  Qwen in 9%, and Gemini in 3 of 10, each time for a gap the general clauses
  missed (for example "item not in listing description", which found the
  exclusion in BPR-04). On those 10 cases Gemini scored the same with either
  design (9 right; [probe report](evaluation_probe_gemini_agentic.md)).
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
| Full guide, per gap (default) | 52% | 48% | 92% (23 of 25) | The prompt and the retrieved clauses |
| Full guide, no retrieval | 60% | 52% | not run | The prompt only |
| Rubric only, per gap | 58% | 50% | 92% (23 of 25) | The retrieved clauses only |
| Rubric only, no retrieval | 56% | 54% | 88% (22 of 25) | Nowhere: only the outcome rubric and the model's own knowledge |

- **The local models cannot tell us.** Every 8B variant lands at 48–60% (within
  3 cases) and gets only 23–35% of seller wins right: they refund almost
  everything whatever the prompt holds, so neither the guide nor retrieval
  measurably changes their decisions.
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
  would make retrieval matter more. The Gemini probe covers only the first 25 test cases, which are all clear cases; the borderline ones, where policy detail matters most, are not in it.

## Our choice, and why

1. **Gemini Flash-Lite stays the default judge.** It is the only model accurate enough (90%, 94% on cases it does not escalate) to be worth a staff member's time. On the free tier it costs nothing; a deployment would use the paid tier (no training on prompts) after removing personal details.
2. **Llama 3.1 8B is the default local model.** It beat Qwen 3 8B (52% vs 48%, within noise), fits fully on our 8 GB GPU (Qwen spilled 11% onto the CPU) and is faster. It is a fallback for when data must stay on the machine or the cloud is down, not a replacement: with it, nearly every dispute would be refunded, which hurts honest sellers.
3. **Per-gap retrieval stays the default retrieval design,** with the `search_policy` tool as a fallback: agent-driven retrieval was no more accurate on any model and costs one more LLM call per case.

## Hardware and other limits

- Local runs used one desktop: Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti with 8 GB of GPU memory, Windows 11, Ollama with 4-bit models.
- 8 GB of GPU memory limits us to about 8 billion parameters. With a 10,240-token context window Llama takes 6.1 GB and runs fully on the GPU; Qwen takes 6.9 GB and ran 11% on the CPU. A 16k window pushed even Llama 13% onto the CPU, so we used 10,240 tokens, which fits the largest prompt (6,800 tokens).
- "Cloud vs local" here is also "a strong small cloud model vs 8B models at 4-bit": the comparison cannot separate the two. 14B-and-larger open models, which might close the gap, would run largely on the CPU, several times slower, and all runs had to finish in one night.
- Windows ran short of committed memory once while a model was loaded and a test suite ran next to it; that run resumed from where it stopped (the harness saves after every case).
- The free Gemini quota allows about one full test run a day, so the Gemini rubric-only runs cover the first 25 test cases and the agent-driven run 10; the full-guide no-retrieval run and full-length versions are left for another day.
- Single runs on 50 cases, no repeat runs, provisional labels. The test set has now been used three times and the local default was chosen on it, so the local numbers are slightly optimistic.

## What we would try next

- The Gemini ablations on all 50 cases when the free quota allows: `uv run dispute-agent evaluate --provider gemini --system agent --guide rubric --run abl_gemini_rubric` (and with `--no-retrieval`).
- The paid OpenAI key (the client is ready): `uv run dispute-agent evaluate --provider openai --run cmp_openai`, then `compare`.
- Repeat runs to measure run-to-run variation, and the human labels.
- A larger local model on a bigger GPU, or a few worked examples of declines in the prompt for the small models.
