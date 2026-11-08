"""Turn a run's saved predictions into a Markdown report plus a citation check sheet."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ..config import load_config, path
from ..data.cases import cases_by_id
from ..data.labels import resolved_labels
from ..rag.chunker import clauses_by_id
from ..schemas import OUTCOME_LABELS, OUTCOMES
from .harness import load_records, run_dir
from .metrics import compute_metrics, latest_by_case


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def build_report(run: str) -> tuple[Path, dict]:
    cases = cases_by_id()
    labels = resolved_labels()
    info_file = run_dir(run) / "run_info.json"
    info = json.loads(info_file.read_text(encoding="utf-8")) if info_file.exists() else {}
    split_ids = set(info.get("case_ids", cases))
    meta = {cid: {"difficulty": c.meta.difficulty} for cid, c in cases.items()}

    results = {}
    for system in ("agent", "baseline"):
        recs = [r for r in load_records(run, system) if r["case_id"] in split_ids]
        if recs:
            results[system] = compute_metrics(recs, labels, meta)

    threshold = load_config()["agent"]["confidence_threshold"]
    providers = {r.get("provider") for s in results for r in load_records(run, s)}
    lines = [f"# Evaluation report: {run}", ""]
    if "mock" in providers:
        lines += ["> **Mock provider: these numbers come from keyword rules, not an LLM. They only show the pipeline works.**", ""]
    lines += [
        f"- Cases: {info.get('split', '?')} split, {len(split_ids)} cases",
        "- Models: " + ", ".join(sorted({f"{r.get('provider')}/{r.get('model')}" for s in results for r in load_records(run, s)})),
        f"- Confidence threshold for escalation: {threshold}",
    ]
    any_res = next(iter(results.values()), {})
    if any_res.get("label_sources"):
        src = ", ".join(f"{k}: {v}" for k, v in any_res["label_sources"].items())
        lines.append(f"- Labels used: {src}. 'provisional' means the outcome the case was written for, not yet checked by the labellers.")
    lines.append("")

    def row(name: str, key) -> str:
        cells = []
        for system in ("agent", "baseline"):
            m = results.get(system)
            cells.append(key(m) if m and m.get("n") else "n/a")
        return f"| {name} | " + " | ".join(cells) + " |"

    lines += [
        "## Headline numbers",
        "",
        "| Measure | Agent | Single-prompt baseline |",
        "|---|---|---|",
        row("Cases scored", lambda m: str(m["n"])),
        row("Failed (no valid answer; counted as wrong)", lambda m: f"{m.get('failed', {}).get('n', 0)}"),
        row("Decision accuracy (4 outcomes)", lambda m: _pct(m["decision_accuracy"])),
        *[
            row(f"  {d} cases", lambda m, d=d: f"{_pct(m['accuracy_by_difficulty'].get(d, {}).get('accuracy'))} (n={m['accuracy_by_difficulty'].get(d, {}).get('n', 0)})")
            for d in ("clear", "borderline", "ineligible")
        ],
        row("Direction accuracy (refund vs decline)", lambda m: _pct(m["direction_accuracy"])),
        row("Buyer-win cases right", lambda m: f"{_pct(m['buyer_win_accuracy']['accuracy'])} (n={m['buyer_win_accuracy']['n']})"),
        row("Seller-win cases right", lambda m: f"{_pct(m['seller_win_accuracy']['accuracy'])} (n={m['seller_win_accuracy']['n']})"),
        row("Eligibility accuracy", lambda m: _pct(m["eligibility_accuracy"])),
        row("Ineligible cases flagged", lambda m: _pct(m["ineligible_flagged"]["share"])),
        row("Judged cases citing a clause", lambda m: _pct(m["cited_at_least_one_clause"])),
        row("Cases with invented clause IDs (final answer)", lambda m: _pct(m["invented_citation_rate"])),
        row("Cases citing a real clause in the wrong format (final answer)", lambda m: _pct(m.get("citation_format_error_rate"))),
        row("Judged cases where the model cited a clause it was not shown", lambda m: _pct(m.get("raw_invented_citation_rate"))),
        row("Judged cases where the judge called search_policy", lambda m: _pct(m.get("tool_use", {}).get("cases_using_search"))),
        row("Escalated", lambda m: _pct(m["escalation"]["escalated_share"])),
        row("Wrong decisions that were escalated", lambda m: _pct(m["escalation"]["wrong_decisions_escalated"])),
        row("Right decisions that were escalated", lambda m: _pct(m["escalation"]["right_decisions_escalated"])),
        row("Accuracy on cases not escalated", lambda m: _pct(m["escalation"]["accuracy_when_not_escalated"])),
        row("Seconds per case (median)", lambda m: str(m["seconds_per_case"]["median"])),
        row("LLM calls per case", lambda m: str(m["llm_calls_per_case"])),
        row("Tokens per case (in / out)", lambda m: f"{m.get('tokens_per_case', {}).get('input') or 'n/a'} / {m.get('tokens_per_case', {}).get('output') or 'n/a'}"),
        "",
    ]
    if "agent" in results and "baseline" in results and results["agent"].get("n") and results["baseline"].get("n"):
        gain = results["agent"]["decision_accuracy"] - results["baseline"]["decision_accuracy"]
        lines += [f"**Gain over baseline:** {gain * 100:+.1f} percentage points in decision accuracy.", ""]

    for system, m in results.items():
        if not m.get("n"):
            continue
        lines += [f"## Confusion matrix: {system}", "", "Rows are the label, columns the prediction.", ""]
        short = {o: OUTCOME_LABELS[o] for o in OUTCOMES}
        lines.append("| Label \\ Predicted | " + " | ".join(short.values()) + " |")
        lines.append("|---" * (len(OUTCOMES) + 1) + "|")
        for lab in OUTCOMES:
            lines.append(f"| {short[lab]} | " + " | ".join(str(m["confusion"][lab][p]) for p in OUTCOMES) + " |")
        lines.append("")
        if m["wrong_cases"]:
            lines += [f"Wrong cases ({system}): " + ", ".join(f"{w['case_id']} ({w['label']} -> {w['pred'] or 'FAILED'}{', escalated' if w['escalated'] else ''})" for w in m["wrong_cases"]), ""]

    reports = path("outputs.reports_dir")
    reports.mkdir(parents=True, exist_ok=True)
    sheet = _citation_sheet(run, reports / f"citation_check_{run}.csv", split_ids)
    lines += [
        "## Citation check by hand",
        "",
        f"`citation_check_{run}.csv` lists every clause the agent cited with the decision it supports. Fill the `supports` column (Y/N); the share of Y is the citation accuracy in the brief.",
        "",
    ]
    for col, who in (("supports", "a person"), ("claude_supports", "Claude (an AI reviewer, not a person)")):
        filled = [r[col].strip().upper() for r in sheet if r[col].strip()]
        if filled:
            share = sum(v == "Y" for v in filled) / len(filled)
            lines += [f"- Checked by {who}: {len(filled)} of {len(sheet)} citations, {share:.0%} support the decision.", ""]
    out = reports / f"evaluation_{run}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (reports / f"evaluation_{run}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out, results


CITATION_COLUMNS = ["case_id", "predicted_outcome", "reasons", "clause_id", "clause_section", "clause_text",
                    "supports", "claude_supports", "claude_note"]
CITATION_FILLED = ["supports", "claude_supports", "claude_note"]


def _citation_sheet(run: str, out: Path, split_ids: set[str]) -> list[dict]:
    """Write the sheet, keeping any checks already filled in for the same case and clause."""
    old = {}
    if out.exists():
        with open(out, encoding="utf-8", newline="") as f:
            old = {(r["case_id"], r["clause_id"]): r for r in csv.DictReader(f)}
    by_id = clauses_by_id()
    preds = latest_by_case(load_records(run, "agent"))
    rows = []
    for cid, p in sorted(preds.items()):
        if cid not in split_ids or p.get("decided_by") != "llm":
            continue
        for c in p.get("citations", []):
            clause = by_id.get(c)
            row = {
                "case_id": cid,
                "predicted_outcome": p["predicted_outcome"],
                "reasons": " | ".join(p.get("reasons", [])),
                "clause_id": c,
                "clause_section": clause.section if clause else "",
                "clause_text": clause.text if clause else "",
            }
            kept = old.get((cid, c), {})
            row.update({col: kept.get(col, "") for col in CITATION_FILLED})
            rows.append(row)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CITATION_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return rows
