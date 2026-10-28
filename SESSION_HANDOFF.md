# Session handoff (working notes, delete before submission)

Last updated: 28 Oct 2026 (3 PM). Planning docs (briefs, assignment) live in
`D:\Jon\Uni\BC3415\Project\Group\`; this repo holds the code.

## Ground rules agreed with Jonathan

- Claude edits only inside this repo; research agents never edit.
- Claude never reads `.env` (blocked in `.claude/settings.local.json` for sessions opened here).
- Commit locally in small commits; **do not push** until Jonathan has reviewed.
- No fabricated listings: listings are real Mercari rows. Disputes on top of them are synthetic, as the brief planned.
- Free tools only: Gemini free tier, no paid APIs.
- If the Gemini quota runs out mid-job, start `uv run dispute-agent wait-for-quota --model <model>` in the background as a watchdog, then resume the job when it exits.

## Decisions made

- uv-managed venv in `.venv` (Python 3.12 pinned), lock in `uv.lock`; `requirements.txt` exported for Streamlit Cloud.
- Judge model `gemini-flash-lite-latest` (Jonathan set `GEMINI_MODEL` in `.env`). Generator `gemini-3-flash-preview`, falling back to `gemma-4-26b-a4b-it`. `gemini-flash-latest` was overloaded (503), `gemini-3.5-flash` had a tiny daily quota, and Gemma is slow with a response schema, so for Gemma the schema goes in the prompt.
- Outcomes follow Carousell's own four: full refund with return, full refund without return, partial refund, decline. The partial-vs-return rubric is ours (`DECISION_GUIDE`).
- Eligibility is plain code (payment, window, tracked non-delivery, one dispute per order, seller 24h deadline).
- Retrieval is hybrid (Chroma + BM25, RRF): 76% hit@1 and 96% hit@5 on 25 queries, vs 52% hit@1 for either method alone.
- Provisional labels = generator's target outcome; B1/B2 columns in `data/labels/labels.csv`.

- Decision guide clarified after the first test run (small specific flaw on a new/like-new item = partial refund); validated on dev only. README "Results so far" explains it.

## State

All 200 cases generated, split (50 test / 150 dev) and evaluated. Latest test run `gemini_test_v2`: agent 88%, baseline 86%. The free daily quota for `gemini-flash-lite-latest` covers roughly one full test run (agent + baseline); it resets at midnight Pacific (3 PM Singapore while US daylight saving lasts, 4 PM after 1 Nov).

## Next steps

1. Jonathan reviews, then pushes to GitHub.
2. B1/B2 label `data/labels/labels.csv` (guide: `docs/labelling_guide.md`), then re-run `uv run dispute-agent evaluate --split test --run gemini_test_v3`. G008 is mislabelled (its listing says the knobs are missing); G129/G134 are judgement calls.
3. Someone fills `reports/citation_check_gemini_test_v2.csv` (citation accuracy).
4. Deploy to Streamlit Community Cloud (README has the steps).
5. Check the Mercari competition rules before making the repo public.
