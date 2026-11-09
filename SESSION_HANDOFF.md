# Session handoff (working notes, delete before submission)

Last updated: 9 Nov 2026. For continuing the work on another device (or in a
new Claude Code session). The team's task list is in [NEXT_STEPS.md](NEXT_STEPS.md);
this file is the context behind it.

## Where things stand

- **Story of the project:** Gemini Flash-Lite is the judge (agent 90%, single-prompt baseline 88% on the 50 held-out cases, hand labels). The model comparison is Gemini against two local 8B models through Ollama (Llama 3.1 54%, Qwen 3 52%); they refund nearly everything, so Gemini stays. Per-gap retrieval stays the default. Full write-up: README, `reports/model_comparison.md`, the full report.
- **OpenAI:** only the cloud app's automatic fallback when a Gemini call fails (`gpt-5.4-mini`). The key is **unpaid** (OpenAI free usage tier, about 50 requests a day), so there is no spend cap any more, and OpenAI is not in the comparison and not selectable as a judge in the app's sidebar. The CLI still takes `--provider openai` (`check-llm --provider openai` tests the key). The partial GPT-5.4 mini runs were deleted on 5 Nov.
- **Gemini model:** `gemini-flash-lite-latest` pointed to `gemini-3.5-flash-lite` when checked through the API on 5 Nov. Google's paid price for it: US$0.30 in / US$2.50 out per million tokens (about US$0.002 a case); the free tier costs nothing.
- **Team:** C1 Ronak, C2 Akshaya, C3 Evelyn, C4 Jonathan, B1 Dan Yu, B2 Drue. Names are in the README table and report section 12.2. The "Main contributions" and "Evidence" columns are still the role defaults: each member should correct their row.
- **Video:** not recorded yet. `presentation/VIDEO_SCRIPT.md` gives all six members a part (B1 problem, C1 workflow, C2 policy search, C4 demo, C3 evaluation, B2 risks, B1 recommendation), about 4:55 in total, and asks for every speaker on camera. The old video slide deck (.pptx) was deleted on 6 Nov: the video records the app's own pages, with text cards added in editing. The professor will not run the app himself (no API keys are submitted), so the video and the live demo are where the app is seen working.
- **Live presentation:** separate from the video. The team presents live (15 to 17 min plus about 5 min Q&A) to a mock Carousell CTO and CFO, using a 26-slide Canva pitch deck ("Carousell_Dispute_Agent_Canva_Pitch", Group 4). The deck is kept outside the repo; its edit link is with the team and must not go in the repo.
  - **Speakers and script:** the script is in the deck's speaker notes. Each note Claude wrote starts with the speaker, a length and an "on time if done by" mark.
    - Work split: Drue 1–5, Evelyn 6–9, Ronak 10–13, Jonathan 14–18 (live demo on 18), Akshaya 19–22, Dan Yu 23–26.
    - Dan Yu is writing his own notes: slides 23 and 24 are his, and he trimmed 25. Don't overwrite notes that don't start with "[Name ·".
  - **Timing:** about 14:50 at 150 words a minute, including about 75 s of app waits in the demo; about 13:15 at 170 wpm. Handovers add about 25 s, and Dan Yu's own notes add about 20 s. If rehearsal runs long, cut slides 11 and 12 to the sentences their notes mark.
  - **Demo and Q&A:**
    - Slide 18's notes hold the demo steps (S01, S16, G155; backups S02 and S10).
    - Slide 26's notes hold a Q&A bank of CFO, CTO and evidence questions, each with an answer and who gives it.
    - Slide 16's notes hold Jonathan's extra CTO Q&A prep: prompt injection, photos, model version, fallback, PDPA.
  - **QR code:** `qr-code.jpg` (in the repo folder, not committed) opens the live app. It is on slides 18 and 26. Ask the panel to scan it after the demo, because everyone on the link shares the free Gemini quota with the demo.
- **Deployment:** live since 6 Nov at https://bc3415-carousell-dispute-agent.streamlit.app/; every push to `main` redeploys it. Secrets (set in Streamlit, not in the repo): `GEMINI_API_KEY` and `OPENAI_API_KEY`. Everyone using the link shares the free Gemini quota.
- **App UI (6 Nov):** Review and What-if are a guided chat (bottom bar with a case picker or settings, plus a chat box); Evaluation results is a summary for non-technical readers that reads its numbers from `reports/`; How it works uses `docs/figures/agent_workflow.png`.
- **Tests:** 69, all passing, offline.

## What changed on 9 Nov

A review compared the repo with the Canva pitch deck, then fixed both.

**Canva pitch deck** (slide numbers are Canva's page numbers; the deck's own "(01)" labels are one lower):

- Slides 2, 15, 16: "66 automated tests" became 69.
- Slides 15, 16: "not deployed yet" became "live on Streamlit Community Cloud (since 6 Nov)".
- Slide 5: the build cost row says "(amortised over 3 yrs)", so S$400K minus about S$100K a year gives the S$300K net value shown.
- Slide 9: escalation item (2) now also covers citing a clause the judge was not given, as `review_gate` in `graph.py` does.
- Slide 18: added the missing 17th scenario, "Seller didn't respond 1" (the Clear column now adds up to 120).
- Slide 20: the footnote explains G134 (a judgement call the agent got right).
- Slide 21: "THE AGENT BEAT A SINGLE PROMPT" became "WAS AHEAD OF", plus "none statistically significant", to agree with slide 19's "a tie on judgement".
- Slides 22–24: the source lines got their report section numbers back (8.2, 8.5 and 10; 8.8 and 8.7; 8.7).
- Slides 17 and 25: QR code to the live app, with a caption.
- Every slide: new speaker notes, as described above. The old notes still said "Group [number]", "66 tests", "we haven't deployed it yet" and described the old app layout.

**Repo:**

- `docs/report_build/update_report.py` now needs the output path as a third argument and refuses to save over `report_orig.docx`. Before, running it as its docstring said would overwrite the base file every build starts from.
- The report: Appendix B no longer says the Gemini pricing page is "to be checked", matching section 9.6. It was rebuilt with `build_report.py` and the contents page was refreshed in Word. The only text change is that line. Word's save also set the file's "last modified by" property.
- `README.md`: names the written report, has a complete project layout (`config.yaml`, `outputs/`, `docs/report_build/`, Docker files, the .docx), and lists the `build-index` and `report` commands.
- `docs/report_build/README.md`: the full `compare` command (it was cut short with "..." and no `--hardware`), plus the CRLF note, so it survives when this file is deleted.
- `Dockerfile`: copies `docs/figures/`, which the How it works page needs.
- Unused code removed: `mermaid_diagram` and `save_diagram` in `agent/graph.py`, and `format_retrieval` in `evaluation/retrieval.py`. `max_backup_calls` stays, because a test uses it and removing it would change the 69 test count.
- Small fixes:
  - the `config.yaml` comment on `target_total`, which includes the 20 seed cases;
  - two lint warnings, in `evaluation/report.py` and `data/cases.py`;
  - a `|` in the S13 title, which broke a table row in `reports/whatif_demo.md`.
- `NEXT_STEPS.md`: the Push item is ticked. The Mercari fallback is now "keep the repo private", because generated cases embed the listing text. The submission item now notes the README link to this file and the `docs/report_build/` decision.

**Later on 9 Nov (Jonathan's part, slides 14–18):**

- **New slide 16, "How it plugs in".**
  - It copies slide 7's layout, with its section tab set to FEASIBILITY.
  - It shows the path a case takes in 8 columns. Each column is tagged PILOT BUILD (case in, privacy, case out), RUNS TODAY, or DEMO TODAY (the staff app).
  - It also gives three real figures: S01 took 6.6 s and 2 AI calls (from `outputs/runs/gemini_seed/agent.jsonl`); its answer was a 15% refund of S$27.54; and the build is 6 months, S$150K, including the 14-week pilot.
  - The labels on old slides 16–25 moved up by one: (15)–(24) became (16)–(25).
- **Slide 14:** the "Dispute writer" row is now "Upgrades" (the Gemini version is pinned for the pilot). The rows also say:
  - the pilot uses Gemini's paid tier;
  - the local model is not good enough yet;
  - the OpenAI fallback is untested and only labelled "fallback".
- **Slide 14, later still:** the left-hand TECH STACK table became a workflow diagram, so the slide shows the branch, the tool loop and the pause for staff.
  - It's an image: a deck-coloured redraw of `docs/figures/agent_workflow.png`, sized 808 × 449.
  - The only red arrow is judge → search tool, the one point where the AI picks the next step. On the 50 test cases it never fired; the notes say so.
  - A caption keeps the stack names: "Built with LangGraph · ChromaDB + BM25 · Pydantic schemas · Streamlit".
  - The slide 14 script was rewritten to walk through the diagram (about 50 s).
  - The redraw script and the old table's text and positions, for a manual restore, are kept outside the repo (in Jonathan's Claude session scratchpad, not committed).
- **Slide 15:** the stack table repeated slide 14, so it became "What it takes to run" (speed on the free tier, volume, lock-in, data used today).
- **Slide 17:**
  - "Exit code 75" and mock mode are gone.
  - A new row covers both AI providers being down: staff handle the case as they do today.
  - The deployment box says "public demo, made-up data only".
- **Notes:**
  - All notes now use the work split above.
  - Slide 16's notes hold the CTO Q&A prep.
  - Slide 18's demo notes no longer promise G155's outcome; they say to look for the review box. They also name the video as a last-resort backup.
- **Mock CTO and CFO review** (Claude agents, three rounds): Part 4 rose from 7/10 to 9/10 with both, and the decks scored 80/100 (CTO) and 74/100 (CFO). Both said "approve, with conditions". Their main points for other parts were passed to the team, not edited:
  - **Slide 26:** the ask names no amount and has no go/no-go pass marks. Its stages add up to 14 weeks.
  - **Slide 5:**
    - the inputs behind 6,000 disputes are not shown;
    - the low case (S$71K) is below the yearly cost;
    - break-even is +0.06 points only if the staff-time saving holds (+0.3 points without it);
    - payback starts at go-live.
  - **Slides 23 and 24:** add prompt injection and "photos are not analysed". The slide 23 notes skip the privacy row.
  - **Slide 25:** run 3 credits the search tool, which was never called; 88→90 is run-to-run noise.
  - **Slide 20:** 100% eligibility is expected, because the same rules generated the cases' dates.
  - **Slide 12:** the "23 of 25 with or without" wording reads as a contradiction.

**Still open from the review** (not changed on purpose):

- The deck repeats some content (slides 10 and 11 both show the retrieval figures; slide 15's repeated stack was fixed later the same day). It also has no team slide.
- `docs/report_build/report_orig.docx` still holds the draft's internal notes. Keep it while the report may need rebuilding, and decide before submission (see `NEXT_STEPS.md`).
- 17 of the 19 `reports/citation_check_*.csv` files are empty; only `cmp_gemini-flash-lite` matters, and its human `supports` column is still blank.

## Mock grade (5 Nov)

A Claude grader agent marked the repo against the Option A rubric: **74/100 (B+)** now, about **85–86** once the video features all six members, the app is deployed and each member has real evidence in the contribution table. Weakest criterion: collaboration (8/20), because every commit comes from one account and the evidence columns are generic. The rubric came from a photo of the assignment document; **do not add that photo or the rubric to the repo** (not sure it may be shared).

## Setting up on a new device

1. Clone, then `uv sync` (uv installs Python 3.12 itself). Windows: `winget install --id=astral-sh.uv -e`.
2. `.env` is not in git: copy `.env.example` to `.env` and put in `GEMINI_API_KEY` (and `OPENAI_API_KEY` for the fallback). Never show `.env` on screen.
3. `uv run pytest` should report 69 passed. The first run downloads the 80 MB embedding model and builds `.chroma/`.
4. Optional, only for rebuilding the report:
   - **Report:** Python with `python-docx` and `pillow`: `uv run --no-project --with python-docx --with pillow python docs/report_build/build_report.py`, then refresh the contents page in Word (or `docs/report_build/render_docx.ps1 ... -UpdateAndSave` on Windows).

## How the generated files are made (edit the source, not the output)

| Output | Source | Rebuild |
|---|---|---|
| `Carousell_Dispute_Agent_Full_Report.docx` | `docs/report_build/update_report.py`, `findings_text.json`, `findings_build.py` | see `docs/report_build/README.md` |
| `reports/model_comparison.md` | `docs/model_comparison_notes.md` (top part) + the run folders | command below |
| `reports/retrieval.md` | `src/dispute_agent/evaluation/retrieval.py` | `uv run dispute-agent eval-retrieval` |

Comparison report command (same runs and hardware line as now):

```bash
uv run dispute-agent compare cmp_gemini-flash-lite cmp_llama3.1-8b cmp_qwen3-8b abl_llama3.1-8b_agentic abl_qwen3-8b_agentic probe_gemini_agentic abl_llama3.1-8b_norag abl_qwen3-8b_norag abl_llama3.1-8b_rubric abl_qwen3-8b_rubric probe_gemini_rubric abl_llama3.1-8b_rubric_norag abl_qwen3-8b_rubric_norag probe_gemini_rubric_norag --notes docs/model_comparison_notes.md --hardware "Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti 8 GB, Windows 11; Ollama, 4-bit models, 10,240-token context"
```

## Gotchas

- **Line endings on Windows:** `compare` rewrites every `reports/evaluation_*` file with CRLF endings. The content is unchanged and git shows them as modified, so restore those with `git checkout -- <file>` and keep only the files whose content changed (`git diff --name-only` lists the real ones). The repo stores LF (`.gitattributes`).
- **Free Gemini quota:** about one full test run (agent and baseline on 50 cases) a day for `gemini-flash-lite-latest`; it resets at 4 PM Singapore. Long jobs stop with exit code 75 and resume when re-run.
- **The test set has been used three times;** don't tune anything on it.
- If a number changes, it has to change in the README, the comparison notes, `findings_text.json` / `update_report.py` (then rebuild the report), `VIDEO_SCRIPT.md`, and the Canva deck and its speaker notes. The app's Evaluation results page reads `reports/` itself.
- **Editing the Canva deck:**
  - Find and replace (File menu) keeps most formatting, but replaced text can pick up bold from the text just before it. Check the weight after each replacement.
  - Uploading images needs a signed-in Canva account; an anonymous edit link cannot upload.
  - A speaker note is saved only after you move to another slide; reloading straight after typing loses the edit.
  - Teammates edit the deck at the same time, so check a note's current text before replacing it.

## Ground rules with Jonathan

- Commit only when asked; branch-free, straight onto `main` is fine for this repo. Push only when asked.
- No fabricated data, contributions or meeting notes: per-member evidence must come from the team.
- Free tools only (Gemini free tier; the OpenAI key stays unpaid).
