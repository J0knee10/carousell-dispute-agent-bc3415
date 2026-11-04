# How the full report is built

`Carousell_Dispute_Agent_Full_Report.docx` (repo root) is generated, not edited
by hand, so its numbers always match `reports/`.

| File | What it is |
|---|---|
| `report_orig.docx` | The first version of the report (3 Nov). Every build starts from it, so no edit is applied twice and the styles stay the same. |
| `findings_text.json` | The written findings, conclusions and table notes. Edit this to change wording. |
| `findings_build.py` | Reads `reports/evaluation_*.json` and builds the result tables (runs that are not finished show "pending"). |
| `update_report.py` | Applies every change to the original: updated sections, new sections 8.5–8.6, the redrawn figure, and the removal of internal notes. |
| `docx_helpers.py` | Small python-docx helpers that keep the report's own styles. |
| `build_report.py` | Runs the two steps above and writes the report to the repo root. |
| `render_docx.ps1` | Windows only: opens the report in Word, updates the contents page, saves, and exports a PDF to check. |

Rebuild after new results (for example the GPT-5.4 mini runs):

```bash
uv run dispute-agent compare cmp_gemini-flash-lite cmp_gpt-5.4-mini cmp_llama3.1-8b cmp_qwen3-8b ...   # refresh reports/
uv run --no-project --with python-docx --with pillow python docs/report_build/build_report.py
```

Then update the contents page: in Word, References → Update Table, or on
Windows `powershell -File docs/report_build/render_docx.ps1 -Docx <full path to the .docx> -Pdf <full path to a .pdf> -UpdateAndSave`.
The workflow figure comes from `docs/figures/agent_workflow.png` (drawn by
`docs/figures/agent_workflow.py`).
