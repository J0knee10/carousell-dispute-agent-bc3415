# Session handoff (working notes, delete before submission)

Last updated: 6 Nov 2026. For continuing the work on another device (or in a
new Claude Code session). The team's task list is in [NEXT_STEPS.md](NEXT_STEPS.md);
this file is the context behind it.

## Where things stand

- **Story of the project:** Gemini Flash-Lite is the judge (agent 90%, single-prompt baseline 88% on the 50 held-out cases, hand labels). The model comparison is Gemini against two local 8B models through Ollama (Llama 3.1 54%, Qwen 3 52%); they refund nearly everything, so Gemini stays. Per-gap retrieval stays the default. Full write-up: README, `reports/model_comparison.md`, the full report.
- **OpenAI:** only the cloud app's automatic fallback when a Gemini call fails (`gpt-5.4-mini`). The key is **unpaid** (OpenAI free usage tier, about 50 requests a day), so there is no spend cap any more, and OpenAI is not in the comparison and not selectable as a judge in the app's sidebar. The CLI still takes `--provider openai` (`check-llm --provider openai` tests the key). The partial GPT-5.4 mini runs were deleted on 5 Nov.
- **Gemini model:** `gemini-flash-lite-latest` pointed to `gemini-3.5-flash-lite` when checked through the API on 5 Nov. Google's paid price for it: US$0.30 in / US$2.50 out per million tokens (about US$0.002 a case); the free tier costs nothing.
- **Team:** C1 Ronak, C2 Akshaya, C3 Evelyn, C4 Jonathan, B1 Dan Yu, B2 Drue. Names are in the README table and report section 12.2. The "Main contributions" and "Evidence" columns are still the role defaults: each member should correct their row.
- **Video:** not recorded yet. `presentation/VIDEO_SCRIPT.md` gives all six members a part (B1 problem, C1 workflow, C2 policy search, C4 demo, C3 evaluation, B2 risks, B1 recommendation), about 4:55 in total, and asks for every speaker on camera. The slide deck was deleted on 6 Nov: the video records the app's own pages, with text cards added in editing.
- **Deployment:** live since 6 Nov at https://bc3415-carousell-dispute-agent.streamlit.app/; every push to `main` redeploys it. Secrets (set in Streamlit, not in the repo): `GEMINI_API_KEY` and `OPENAI_API_KEY`. Everyone using the link shares the free Gemini quota.
- **App UI (6 Nov):** Review and What-if are a guided chat (bottom bar with a case picker or settings, plus a chat box); Evaluation results is a summary for non-technical readers that reads its numbers from `reports/`; How it works uses `docs/figures/agent_workflow.png`.
- **Tests:** 69, all passing, offline.

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
- If a number changes, it has to change in the README, the comparison notes, `findings_text.json` / `update_report.py` (then rebuild the report) and `VIDEO_SCRIPT.md`. The app's Evaluation results page reads `reports/` itself.

## Ground rules with Jonathan

- Commit only when asked; branch-free, straight onto `main` is fine for this repo. Push only when asked.
- No fabricated data, contributions or meeting notes: per-member evidence must come from the team.
- Free tools only (Gemini free tier; the OpenAI key stays unpaid).
