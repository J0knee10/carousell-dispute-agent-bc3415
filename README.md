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
2. **Claim matching (LLM).** Lists what the listing promised and what the buyer reports, and pairs them up as gaps ("listing says it comes with an 8GB SD card; buyer says no card").
3. **Policy retrieval (RAG).** Each gap becomes a search query over the policy clauses. Search is hybrid: ChromaDB embeddings plus BM25 keyword scores, combined by rank fusion.
4. **Policy judgement (LLM).** Decides whether each gap is significant and recommends one of Carousell's four outcomes: full refund with return, full refund without return, partial refund, or decline. It must cite clause IDs.
5. **Confidence and citation check (code).** Drops citations to clauses that were not retrieved, and escalates low-confidence, unclear or self-contradicting judgements, with follow-up questions to ask for evidence.
6. **Staff decision.** The LangGraph workflow pauses until a person approves or overrides. Every decision is logged.
7. **Message drafts (LLM).** Drafts the decision messages to the buyer and the seller.

Also included:
- **What-if policy test:** re-judges past disputes under a proposed rule change and reports how many outcomes flip.
- **Evaluation harness:** the agent against a single-prompt baseline on a held-out test set.
- **Photo checking:** an interface only (`src/dispute_agent/agent/photo.py`). Cases carry text descriptions of photos for now.

```
intake -> eligibility --covered--> claim matching -> retrieval -> judgement -> check -> STAFF DECIDES -> messages
                      \--not covered / procedural--> rule-based recommendation ------^
```

## Tech stack

| Part | Tool |
|---|---|
| Agent workflow, pause for human approval | LangGraph (`interrupt`) |
| LLM calls with structured JSON output | Google Gemini API (free tier) via `google-genai`; an offline mock for tests |
| Policy retrieval | ChromaDB (local all-MiniLM-L6-v2 embeddings) + BM25, reciprocal rank fusion |
| Interface | Streamlit |
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

## Run the app

```bash
uv run streamlit run app/streamlit_app.py
```

Pages: review a dispute (run the agent, approve or override, see message drafts),
what-if policy test, evaluation results, policy library (search the clauses), and
how it works.

Docker alternative (no Python needed): `docker compose up --build`, then open
http://localhost:8501. The Docker files are included but were not tested on
our machines.

## Command line

All commands run as `uv run dispute-agent <command>`; add `--provider mock` to
avoid API calls.

| Command | What it does |
|---|---|
| `check-llm` | Checks the Gemini key and models respond |
| `run-case S01 [--approve]` | Runs the agent on one case and prints each step |
| `evaluate --split test` | Agent and baseline on the 50 held-out cases, then writes `reports/evaluation_<run>.md` |
| `eval-retrieval` | Retrieval hit rates for dense, keyword and hybrid search |
| `whatif "proposed rule..." --limit 20` | Re-judges past cases under a proposed rule |
| `export-labels` / `agreement` | Labelling sheet and agreement between the two labellers |
| `sample-listings`, `generate`, `split` | Rebuild the dataset (see below) |
| `wait-for-quota --model <m>` | Waits until the Gemini free-tier quota is back |

Long jobs (`generate`, `evaluate`, `whatif`) save after every case. If the free
tier quota runs out they stop with exit code 75; run the same command again
later and they continue where they stopped.

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
the judge (`gemini-flash-lite-latest`), so no model grades its own writing.

To rebuild from scratch: download `train.tsv.7z` from Kaggle into `data/raw/`,
then run `sample-listings`, `generate`, `split` and `export-labels`.

## Evaluation

See `reports/` for the latest numbers. Details on labels are in
[docs/labelling_guide.md](docs/labelling_guide.md).

- **Decision accuracy** on the 50-case held-out test set, overall and for clear, borderline and ineligible cases separately, compared with a single-prompt baseline (the whole policy pasted into one prompt, no rules, no retrieval, no agent steps).
- **Eligibility accuracy**, **escalation quality** (how many wrong answers were flagged), **buyer-win vs seller-win accuracy** (a bias check), **time per case** and **LLM calls per case**.
- **Citation accuracy** needs a person: fill in `reports/citation_check_<run>.csv`.
- **Retrieval accuracy:** `reports/retrieval.md`.

Until B1 and B2 finish labelling, accuracy is measured against the provisional
labels. The report says how many labels of each kind it used.

## Limitations

- Disputes are synthetic and may be easier than real ones; the generator sees the scenario and the target outcome it should support.
- Policy text comes from four help-centre pages copied on 28 Oct 2026; Carousell may change them.
- Listings are from a US marketplace (Mercari), not Carousell.
- When to give a partial refund rather than a return is our own rubric (see `DECISION_GUIDE` in `src/dispute_agent/agent/prompts.py`); Carousell's policy does not spell it out.
- Free-tier Gemini may use prompts to improve Google's products; all data here is made up or public. A real deployment would remove personal details and use a paid tier.
- LLM answers can vary between runs even at temperature 0.

## Project layout

```
app/streamlit_app.py          staff interface
src/dispute_agent/
  agent/                      LangGraph graph, eligibility rules, prompts, runner
  rag/                        clause chunker, ChromaDB + BM25 store
  llm/                        Gemini client, mock, fallback
  data/                       Mercari sampler, case loading, generator, labels
  evaluation/                 harness, metrics, report, retrieval eval, what-if
  cli.py                      command line
data/                         policy text, listings, cases, labels, eval queries
docs/labelling_guide.md       how to label cases
reports/                      evaluation reports
tests/                        pytest suite (runs offline with the mock)
```

Run the tests with `uv run pytest`.

## Deploying to Streamlit Community Cloud

1. Push the repo to GitHub.
2. At https://share.streamlit.io, create an app from the repo with main file `app/streamlit_app.py` and Python 3.12 (in Advanced settings).
3. Under Secrets, add `GEMINI_API_KEY = "..."`.

Everyone who opens the link shares that key's free quota. Streamlit Cloud
installs from `requirements.txt`; after changing dependencies, regenerate it with
`uv export --no-hashes --no-dev --no-emit-project -o requirements.txt`.

## Before submission

- [ ] Delete `SESSION_HANDOFF.md` (working notes, not part of the submission).
- [ ] Check the Mercari competition rules allow sharing the 300 sampled listings before making the repo public.
- [ ] Re-run `uv run dispute-agent evaluate` once the labels are final.
