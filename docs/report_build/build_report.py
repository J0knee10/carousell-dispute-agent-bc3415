"""Rebuild Carousell_Dispute_Agent_Full_Report.docx from the original and the current results.

Run from anywhere:
    uv run --no-project --with python-docx --with pillow python docs/report_build/build_report.py

It starts from report_orig.docx (the first version of the report, kept here so
edits are never applied twice), reads the numbers from reports/*.json and the
written text from findings_text.json, and writes the report to the repo root.
Then open it in Word and update the contents page (References -> Update Table),
or on Windows run render_docx.ps1 (see README.md in this folder).
"""

from __future__ import annotations

import os
import runpy
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main() -> None:
    os.chdir(REPO)
    findings = Path(tempfile.mkdtemp()) / "findings.json"
    sys.argv = ["findings_build.py", str(findings), str(HERE / "findings_text.json")]
    runpy.run_path(str(HERE / "findings_build.py"), run_name="__main__")
    out = REPO / "Carousell_Dispute_Agent_Full_Report.docx"
    sys.argv = ["update_report.py", str(HERE), str(findings), str(out)]
    runpy.run_path(str(HERE / "update_report.py"), run_name="__main__")


if __name__ == "__main__":
    main()
