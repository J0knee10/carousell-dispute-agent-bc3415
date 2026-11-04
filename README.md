# Carousell Dispute Agent

An AI agent that helps Carousell Singapore's support team settle "significantly
not as described" disputes on second-hand items sold between individuals. It
reads the listing, the buyer's complaint, the seller's reply and the chat,
checks them against Carousell's Buyer Protection policy with retrieval-augmented
generation (RAG), and recommends an outcome with reasons and policy citations.
A staff member always makes the final decision.

BC3415 group project, Option A (working prototype + demo video).

## What it does

1. **Eligibility rules (plain code).** Paid with the 'Buy' button? Raised within the dispute window? Tracked delivery for non-receipt? Seller missed the 24-hour reply deadline? These are exact rules, so no LLM is involved, and each check cites the clause it comes from.
2. **Claim matching (LLM).** Lists what the listing promised and what the buyer reports, and pairs them up as gaps ("listing says it comes with an 8GB SD card; buyer says no card"). It writes a policy search query for each gap.
3. **Policy retrieval (RAG).** Each gap's query is run over the policy clauses. Search is hybrid: ChromaDB embeddings plus BM25 keyword scores, combined by rank fusion.
4. **Policy judgement (LLM, with a tool).** Decides whether each gap is significant and recommends one of Carousell's four outcomes: full refund with return, full refund without return, partial refund, or decline. It must cite clause IDs. If the clauses it was given do not cover a gap, it can call the **`search_policy` tool**: code runs the search, adds the new clauses, and the graph loops back to the judge.
5. **Confidence and citation check (code).** Drops citations to clauses that were not retrieved, and escalates low-confidence, unclear, uncited or self-contradicting judgements, with follow-up questions to ask for evidence.
6. **Staff decision.** The LangGraph workflow pauses until a person approves or overrides. Every decision is logged.
7. **Message drafts (LLM).** Drafts the decision messages to the buyer and the seller.

Also included:
- **A choice of judge model:** Gemini (Google cloud, free tier), a local model through [Ollama](https://ollama.com) (nothing leaves the machine), or OpenAI (paid). [reports/model_comparison.md](reports/model_comparison.md) compares them.
- **What-if policy test:** re-judges past disputes under a proposed rule change and reports how many outcomes flip.
- **Evaluation harness:** the agent against a single-prompt baseline on a held-out test set, for any judge model, plus retrieval ablations.
- **Photo checking:** an interface only (`src/dispute_agent/agent/photo.py`). Cases carry text descriptions of photos for now.

![Agent workflow](docs/figures/agent_workflow.png)

```
intake -> eligibility --covered--> claim matching -> retrieval -> judgement <-> search_policy tool
                     \                                               |
                      \                                              v
                       \                                           check -> STAFF DECIDES -> messages
                        \--not covered / procedural--> rule-based recommendation ---^
```

## Tech stack

| Part | Tool |
|---|---|
| Agent workflow, tool loop, pause for human approval | LangGraph (`StateGraph`, conditional edges, `interrupt`) |
| LLM calls with structured JSON output | Gemini API (`google-genai`), Ollama (local), OpenAI (`openai`); Pydantic schemas; an offline mock for tests |
| Policy retrieval | ChromaDB (local all-MiniLM-L6-v2 embeddings) + BM25, reciprocal rank fusion |
| Interface | Streamlit (runs locally or on Streamlit Community Cloud) |
| Environment | uv (Python 3.12 pinned, `uv.lock`), optional Docker |

## Setup

You need [uv](https://docs.astral.sh/uv/). It installs the right Python by itself.

| | Install uv |
|---|---|
| Windows | `winget install --id=astral-sh.uv -e` |
| macOS | `brew install uv` |

Then:

```bash
git clone https://github.com/J0knee10/carousell-dispute-agent-bc3415.git
cd carousell-dispute-agent-bc3415
uv sync                       # creates .venv with Python 3.12 and the locked packages
cp .env.example .env          # Windows: copy .env.example .env
```

Put a free Gemini API key (https://aistudio.google.com/apikey) in `.env` as
`GEMINI_API_KEY=...`. Without a key everything still runs in **mock mode**
(keyword rules instead of an LLM; its answers are not real judgements).

The first run downloads a small embedding model (about 80 MB) and builds the
policy index in `.chroma/`.

**Optional: a local model.** Install [Ollama](https://ollama.com/download), then
pull a model, e.g. `ollama pull qwen3:8b` (5.2 GB) or `ollama pull llama3.1:8b`
(4.9 GB). With Ollama running, the app lists it as a provider, and the CLI takes
`--provider ollama --model qwen3:8b`. An 8B model needs about 6 GB of GPU memory
to run at full speed (see [Model comparison](#model-comparison)).

**Optional: OpenAI.** Put `OPENAI_API_KEY=...` in `.env` and use
`--provider openai` (model in `config.yaml`, `OPENAI_MODEL` overrides it).

## Run the app

```bash
uv run streamlit run app/streamlit_app.py
```

Pages: review a dispute (run the agent, approve or override, see the tool calls
and message drafts), what-if policy test, evaluation results (including the
model comparison), policy library (search the clauses), and how it works. The
sidebar lists only the providers that can run on this machine.

Docker alternative (no Python needed): `docker compose up --build`, then open
http://localhost:8501. The Docker files are included but were not tested on
our machines.

## Command line

All commands run as `uv run dispute-agent <command>`. Add `--provider mock` to
avoid API calls, or `--provider ollama --model llama3.1:8b` to use a local model.

| Command | What it does |
|---|---|
| `check-llm` | Checks the provider and models respond |
| `run-case S01 [--approve]` | Runs the agent on one case and prints each step |
| `evaluate --split test` | Agent and baseline on the 50 held-out cases, then writes `reports/evaluation_<run>.md` |
| `evaluate ... --retrieval agentic` / `--no-retrieval` | Retrieval variants of the agent (see [Model comparison](#model-comparison)) |
| `compare RUN1 RUN2 ...` | One report across runs: `reports/model_comparison.md` |
| `eval-retrieval` | Retrieval hit rates for dense, keyword and hybrid search |
| `whatif "proposed rule..." --limit 20` | Re-judges past cases under a proposed rule |
| `export-labels` / `agreement` | Labelling sheet and agreement between the two labellers |
| `sample-listings`, `generate`, `split` | Rebuild the dataset (see below) |
| `wait-for-quota --model <m>` | Waits until the Gemini free-tier quota is back |

Long jobs (`generate`, `evaluate`, `whatif`) save after every case. If the
quota runs out they stop with exit code 75; run the same command again later
and they continue where they stopped.

## Data

| Data | Source | In the repo |
|---|---|---|
| Policy text | Four Carousell SG help-centre pages, copied by hand (the site blocks automated reading) | `data/policy/*.txt`, URL on line 1 |
| Listings | 300 real listings sampled from the [Mercari Price Suggestion](https://www.kaggle.com/competitions/mercari-price-suggestion-challenge/data) `train.tsv` (US marketplace; prices converted to SGD at 1.35; condition grade 1–5 mapped to Carousell's condition names) | `data/listings/listings_sample.jsonl` |
| Disputes | 20 written by hand (`data/cases/seed_cases.yaml`) and 180 generated (`data/cases/generated_cases.jsonl`) on top of real listings | yes |
| Labels | Provisional label = the outcome each case was written for; columns for two human labellers | `data/labels/labels.csv` |
| Retrieval test set | 25 queries with the clause text that answers each | `data/eval/retrieval_queries.jsonl` |

**How generated disputes are made.** Each case gets a scenario such as
"missing accessory" or "colour shade differs", following the brief's mix of
60% clear, 30% borderline and 10% ineligible cases. Code sets the order facts
(payment method, delivery and dispute dates), so eligibility labels are exact.
A generator model writes the complaint, the seller's reply and the chat, and
must quote the listing text the dispute is about. If the quote is not found in
the listing, it retries or switches to another listing. The generator models
(`gemini-3-flash-preview`, falling back to `gemma-4-26b-a4b-it`) differ from
every judge model compared below, so no model grades its own writing.

To rebuild from scratch: download `train.tsv.7z` from Kaggle into `data/raw/`,
then run `sample-listings`, `generate`, `split` and `export-labels`.

## Evaluation

Details on labels are in [docs/labelling_guide.md](docs/labelling_guide.md).

- **Decision accuracy** on the 50-case held-out test set, overall and for clear, borderline and ineligible cases separately, compared with a single-prompt baseline (the whole policy pasted into one prompt, no rules, no retrieval, no agent steps). A case where the model gives no valid answer counts as wrong.
- **Eligibility accuracy**, **escalation quality** (how many wrong answers were flagged), **buyer-win vs seller-win accuracy** (a bias check), **invented citations** (before and after the agent's check), **tool use**, **time, LLM calls and tokens per case**.
- **Citation accuracy** needs a person: fill in `reports/citation_check_<run>.csv`.
- **Retrieval accuracy:** `reports/retrieval.md`.

Until B1 and B2 finish labelling, accuracy is measured against the provisional
labels. The report says how many labels of each kind it used.

### Results (provisional labels, judge `gemini-flash-lite-latest`)

Test set, 50 held-out cases ([full report](reports/evaluation_cmp_gemini-flash-lite.md)):

| Measure | Agent | Single-prompt baseline |
|---|---|---|
| Decision accuracy | 90% | 88% |
| clear / borderline / ineligible | 93% / 80% / 100% | 97% / 80% / 60% |
| Eligibility accuracy | 100% | 68% |
| Cases with invented clause IDs | 0% | 0% |
| Buyer-win / seller-win cases right | 83% / 96% | 96% / 81% |
| Wrong decisions escalated to a person | 40% | 17% |
| Accuracy on cases not escalated | 94% | 90% |
| Seconds per case (median) | 9.1 | 4.5 |
| LLM calls per case | 1.8 | 1 |

With Gemini the two are close on overall accuracy: one case is 2 points, so a
2-point gap on 50 cases is not a reliable difference. The agent's clear gains
are on eligibility (the plain-code rules never miss a bank transfer, a late
dispute or a completed order; the baseline called 2 of the 5 ineligible cases
eligible and marked 14 eligible cases ineligible) and on escalation (it sends
2 of its 5 wrong answers to a person, the baseline 1 of 6). The baseline leans towards refunding; the agent
leans towards declining. The gap is much larger with weaker models (next
section).

**AI-assisted checks (not human).** Claude, an AI model separate from every
judge model here, did two checks. Its answers are in their own columns and
never replace the human ones:

- *Citation check:* 61 of the agent's 68 citations (90%) support the decision
  they are cited for (`claude_supports` in
  [the citation sheet](reports/citation_check_cmp_gemini-flash-lite.csv)). Most
  misses cite a procedural clause (how a return works), or a clause listing
  what *is* covered on a decline.
- *Labels:* Claude labelled the 50 test cases (`claude_*` in
  `data/labels/labels.csv`) and agreed with the provisional labels on 47 (94%,
  Cohen's kappa 0.90) and on all 50 eligibility calls. The three differences
  (G059, G129, G134) are judgement calls; all three are among the agent's 5
  wrong answers. Treat that with caution: Claude had already seen which cases
  the agent got wrong.

### Model comparison

The professor asked us to try different models. We compared the free cloud
model with two open models running locally, under the same prompts, cases and
code ([full tables](reports/model_comparison.md)):

| Judge model | Runs on | Agent | Single prompt | Agent gain | Seconds per case (agent) |
|---|---|---|---|---|---|
| `gemini-flash-lite-latest` | Google cloud, free tier | **90%** | 88% | +2 pts | 9 |
| `llama3.1:8b` | our PC, Ollama | 52% | 34% | +18 pts | 15 |
| `qwen3:8b` (thinking off) | our PC, Ollama | 48% | 44% | +4 pts | 19 |

**Hardware constraints.** The local models ran on one desktop: Intel Core
i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti with 8 GB of GPU memory, Windows 11.
8 GB of GPU memory limits us to models of about 8 billion parameters at 4-bit
quantisation (about 5 GB of weights). A 16k-token context window pushed 13% of
Llama onto the CPU, so we used 10,240 tokens, which fits the largest prompt
(6,800 tokens). Larger open models (14B and up) would have run partly on the
CPU, several times slower, and all runs had to finish in one night, so we
kept to two 8B models. Qwen took 6.9 GB at this window and ran 11% on the CPU. Each local run of 50 cases took about 15 to 30 minutes.

**What we found.**

- **Gemini is far better at the judgement.** The local 8B models get about half the cases right, and their failure is one-sided: of the 21 test cases that should be declined and reach the LLM, Gemini refunded 1, Llama 19 and Qwen all 21, including change-of-mind and damage-after-delivery claims. They do not apply the policy's exclusions.
- **The agent's structure matters most for weak models:** +2 points over the single prompt with Gemini, +18 with Llama, +4 with Qwen. The eligibility rules in code are 100% right with every model (the single prompt: 68%, 86%, 90%), and with every model the agent's final answers cite no invented clause IDs.
- **Escalation is only as good as the model's confidence:** Gemini's agent escalates 6% of cases and catches 2 of its 5 mistakes; Qwen escalates 22% but catches 27% of its mistakes; Llama escalates 2%.

**Our choice and why.** Gemini Flash-Lite stays the default judge: it is the
only model accurate enough to save a staff member time (90%, and 94% on the
cases it does not escalate), and it is the fastest. Llama 3.1 8B is the
default local model (better than Qwen, and it fits fully on our GPU), as a
fallback when case data must stay on the machine, not as a replacement: it
would refund nearly every dispute, which hurts honest sellers. The OpenAI
client is ready for when the paid key arrives.

### Retrieval design: per gap, agent-driven, or none

Does retrieval change the decisions, or only the citations? We ran three
designs of the agent on the local models and probed Gemini on 10 cases
([notes and tables](reports/model_comparison.md)):

| Retrieval design | Llama 3.1 8B | Qwen 3 8B |
|---|---|---|
| Per gap (default): one search per gap, `search_policy` as a fallback | 52% | 48% |
| Agent-driven: general clauses only; a planning step calls `search_policy` for the gaps they miss | 54% | 48% |
| None (ablation) | 60% | 52% |

- **Accuracy barely moves** (differences of 1 to 4 cases out of 50). The decision guide in the prompt carries most of the judgement, and the clauses mostly list what *is* covered, which pushes small models further towards refunds.
- **Retrieval's value is grounding.** Without clauses nothing can be cited, so the check escalates 90% of cases, and staff could not check the reasoning against the policy.
- **Tool use.** In the default design no model needed `search_policy` on the test set: the per-gap searches already found the clauses. Offered as an optional field inside the judgement, the tool was never used, even when the per-gap searches were removed (0 of 28 Llama cases, 0 of 10 Gemini cases). With a separate planning step it is: Llama searched in every case, Qwen in 9%, Gemini in 3 of 10 (each time for a gap the general clauses missed), and Gemini matched the per-gap design on those 10 cases.
- **Choice:** per-gap retrieval stays the default. It is as accurate, one LLM call cheaper per case, and predictable; the tool stays as a fallback.

### How we got here

**The decision-guide fix.** The first test run
([report](reports/evaluation_gemini_test.md)) gave agent 82%, baseline 84%.
Both declined every small undisclosed flaw on items listed as new or like new,
because two lines of the decision guide contradicted each other. We clarified
the rule and checked the change on dev cases only (agent 81% to 89%, baseline
78% to 81%; [before](reports/evaluation_dev_borderline_v1.md),
[after](reports/evaluation_dev_borderline_v2.md)), then re-ran the test set
([report](reports/evaluation_gemini_test_v2.md): agent 88%, baseline 86%).

**The tool and the model comparison.** We then added the `search_policy` tool
and ran the test set a third time, now once per judge model. Nothing was tuned
on the test set between these runs, but it has now been used three times, and
the default local model was chosen from these results, so its test numbers are
slightly optimistic.

## Limitations

- Disputes are synthetic and may be easier than real ones; the generator sees the scenario and the target outcome it should support.
- 50 test cases is small: one case moves accuracy by 2 points.
- Policy text comes from four help-centre pages copied on 28 Oct 2026; Carousell may change them.
- Listings are from a US marketplace (Mercari), not Carousell.
- When to give a partial refund rather than a return is our own rubric (see `DECISION_GUIDE` in `src/dispute_agent/agent/prompts.py`); Carousell's policy does not spell it out.
- Free-tier Gemini may use prompts to improve Google's products; all data here is made up or public. A real deployment would remove personal details and use a paid tier or a local model.
- LLM answers can vary between runs even at temperature 0.
- The local models were limited by an 8 GB GPU (see [Hardware constraints](#model-comparison)).

## Project layout

```
app/streamlit_app.py          staff interface
src/dispute_agent/
  agent/                      LangGraph graph (with the search_policy tool loop), eligibility rules, prompts, runner
  rag/                        clause chunker, ChromaDB + BM25 store
  llm/                        Gemini, Ollama and OpenAI clients, mock, fallback
  data/                       Mercari sampler, case loading, generator, labels
  evaluation/                 harness, metrics, report, model comparison, retrieval eval, what-if
  cli.py                      command line
data/                         policy text, listings, cases, labels, eval queries
docs/labelling_guide.md       how to label cases
docs/figures/                 workflow figure and the script that draws it
reports/                      evaluation reports and the model comparison
presentation/                 demo video slides (build_slides.js) and VIDEO_SCRIPT.md
tests/                        pytest suite (runs offline: mock LLM, faked HTTP)
```

Run the tests with `uv run pytest` (56 tests, no network or API key needed).

## Deploying to Streamlit Community Cloud

The app is ready for Community Cloud: it reads the key from Streamlit secrets,
installs from `requirements.txt` (checked in a clean Python 3.12 environment),
and hides the Ollama option when no local server is running. Steps:

1. Push the repo to GitHub (a private repo works; Streamlit asks for access to it).
2. Sign in at https://share.streamlit.io with GitHub and click **Create app** → **Deploy a public app from GitHub**.
3. Repository `J0knee10/carousell-dispute-agent-bc3415`, branch `main`, main file path `app/streamlit_app.py`.
4. Open **Advanced settings**: choose Python **3.12**, and under **Secrets** paste:
   ```toml
   GEMINI_API_KEY = "your-key"
   ```
5. Click **Deploy**. The first start takes a few minutes (it installs the packages and downloads the 80 MB embedding model).

On the cloud the app offers Gemini and mock only. Everyone who opens the link
shares that key's free quota (about one full test run a day for
`gemini-flash-lite-latest`; it resets at midnight Pacific time, 4 PM in
Singapore). Decisions logged on the cloud are lost when the app restarts.
After changing dependencies, regenerate `requirements.txt` with
`uv export --no-hashes --no-dev --no-emit-project -o requirements.txt`.

## Team and contributions

To be filled in by the team. Evidence can be commits, files, documents or
meeting notes; the commit history alone shows one author because the code was
pushed from one machine.

| Member | Role | Main contributions | Evidence | In the video |
|---|---|---|---|---|
| _Name 1_ | C1: Agent lead | LangGraph workflow, tool loop, confidence check, staff pause | `src/dispute_agent/agent/` | How it works (0:50–1:40) |
| _Name 2_ | C2: RAG and policy | Policy clauses, hybrid search, citations, retrieval evaluation | `src/dispute_agent/rag/`, `reports/retrieval.md` | |
| _Name 3_ | C3: Data and evaluation | Listings, dispute generator, labels, harness, baseline, model comparison | `src/dispute_agent/data/`, `src/dispute_agent/evaluation/`, `reports/` | Does it work? (3:00–3:55) |
| _Name 4_ | C4: App and deployment | Streamlit app, local models, cloud deployment, repo and README | `app/`, `src/dispute_agent/llm/`, `README.md` | Live demo (1:40–3:00) |
| _Name 5_ | B1: Business lead | Problem, evidence, competitors, business case, recommendation | Project Brief, Business Case | Problem; risks and recommendation |
| _Name 6_ | B2: Policy and story lead | Policy corpus, hard cases, labelling, risks and ethics, video editing | `data/policy/`, `data/labels/labels.csv`, `presentation/` | Edits the video |

## Before submission

- [ ] Fill in the team table above (and `TEAM` in `presentation/build_slides.js`).
- [ ] Check the Mercari competition rules allow sharing the 300 sampled listings before making the repo public.
- [ ] Re-run `uv run dispute-agent evaluate` once the labels are final.
