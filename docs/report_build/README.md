# How the full report is built

`Carousell_Dispute_Agent_Full_Report.docx` (repo root) is generated, not edited
by hand, so its numbers always match `reports/`.

| File | What it is |
|---|---|
| `report_orig.docx` | The first version of the report (3 Nov). Every build starts from it, so no edit is applied twice and the styles stay the same. |
| `findings_text.json` | The written findings, conclusions and table notes. Edit this to change wording. |
| `findings_build.py` | Reads `reports/evaluation_*.json` and builds the result tables. |
| `update_report.py` | Applies every change to the original: updated sections, new sections 8.5–8.6, the redrawn figure, and the removal of internal notes. |
| `docx_helpers.py` | Small python-docx helpers that keep the report's own styles. |
| `build_report.py` | Runs the two steps above and writes the report to the repo root. |
| `render_docx.ps1` | Windows only: opens the report in Word, updates the contents page, saves, and exports a PDF to check. |

Rebuild after new results (for example full-length Gemini ablations):

```bash
# refresh reports/ (same runs and hardware line as now; without --hardware the hardware line drops out of the report)
uv run dispute-agent compare cmp_gemini-flash-lite cmp_llama3.1-8b cmp_qwen3-8b abl_llama3.1-8b_agentic abl_qwen3-8b_agentic probe_gemini_agentic abl_llama3.1-8b_norag abl_qwen3-8b_norag abl_llama3.1-8b_rubric abl_qwen3-8b_rubric probe_gemini_rubric abl_llama3.1-8b_rubric_norag abl_qwen3-8b_rubric_norag probe_gemini_rubric_norag --notes docs/model_comparison_notes.md --hardware "Intel Core i5-13400F, 32 GB RAM, NVIDIA RTX 4060 Ti 8 GB, Windows 11; Ollama, 4-bit models, 10,240-token context"
uv run --no-project --with python-docx --with pillow python docs/report_build/build_report.py
```

On Windows, `compare` rewrites every `reports/evaluation_*` file with CRLF endings: restore the ones whose content did not change with `git checkout -- <file>`.

Section 9.7 (the escalation threshold) takes its tables from `reports/review_cost.md` and `reports/review_cost.csv`. After new runs or a change to `review_cost` in `config.yaml`, refresh them with `uv run dispute-agent review-cost` (no LLM calls) before rebuilding, and update the numbers in the `threshold_*` text in `findings_text.json`.

Then update the contents page: in Word, References → Update Table, or on
Windows `powershell -File docs/report_build/render_docx.ps1 -Docx <full path to the .docx> -Pdf <full path to a .pdf> -UpdateAndSave`.
The workflow figure comes from `docs/figures/agent_workflow.png` (drawn by
`docs/figures/agent_workflow.py`).
