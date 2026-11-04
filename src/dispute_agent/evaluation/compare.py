"""Compare several evaluation runs (one per judge model or variant) in one report."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import path
from .harness import load_records, run_dir
from .report import _pct, build_report

WHERE = {
    "gemini": "Google cloud API (free tier)",
    "openai": "OpenAI cloud API (paid)",
    "ollama": "This computer (local, via Ollama)",
    "mock": "Offline keyword rules (not a model)",
}


def _cell(r: dict, system: str, fn) -> str:
    m = r.get(system)
    return fn(m) if m and m.get("n") else "n/a"


def _by_difficulty(m: dict) -> str:
    d = m["accuracy_by_difficulty"]
    return " / ".join(_pct(d.get(k, {}).get("accuracy")) for k in ("clear", "borderline", "ineligible"))


def _tokens(m: dict) -> str:
    t = m.get("tokens_per_case", {})
    return f"{t.get('input') or 'n/a'} / {t.get('output') or 'n/a'}"


def _name(r: dict) -> str:
    return f"`{r['model']}`" + (f" ({r['variant']})" if r["variant"] else "")


def load_run(run: str) -> dict:
    _, results = build_report(run)
    records = load_records(run, "agent") or load_records(run, "baseline")
    info_file = run_dir(run) / "run_info.json"
    info = json.loads(info_file.read_text(encoding="utf-8")) if info_file.exists() else {}
    return {
        "run": run,
        "provider": next((r.get("provider") for r in records if r.get("provider")), "?"),
        "model": next((r.get("model") for r in records if r.get("model")), "?"),
        "variant": info.get("variant", ""),
        **results,
    }


def build_comparison(runs: list[str], out_name: str = "model_comparison", hardware: str = "") -> Path:
    rows = [load_run(run) for run in runs]
    lines = ["# Model comparison", ""]
    if hardware:
        lines.append(f"- Local hardware: {hardware}")
    lines += [
        "- Runs: " + ", ".join(f"[{r['run']}](evaluation_{r['run']}.md)" for r in rows),
        "- Same held-out test cases and prompts for every model, temperature 0. Only the judge model changes.",
        "- A case with no valid answer (for example invalid JSON twice) counts as wrong.",
        "",
        "## Decision accuracy",
        "",
        "| Model | Runs on | Agent | Baseline | Agent minus baseline | Agent clear / borderline / ineligible | Baseline clear / borderline / ineligible |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gain = "n/a"
        if r.get("agent", {}).get("n") and r.get("baseline", {}).get("n"):
            gain = f"{(r['agent']['decision_accuracy'] - r['baseline']['decision_accuracy']) * 100:+.0f} pts"
        lines.append(
            f"| {_name(r)} | {WHERE.get(r['provider'], r['provider'])} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['decision_accuracy']))} "
            f"| {_cell(r, 'baseline', lambda m: _pct(m['decision_accuracy']))} | {gain} "
            f"| {_cell(r, 'agent', _by_difficulty)} | {_cell(r, 'baseline', _by_difficulty)} |"
        )
    lines += [
        "",
        "## Reliability",
        "",
        "Unseen clause: the model cited a clause ID it was never shown. For the agent this is counted "
        "before the citation check removes it; for the baseline (which has no check) it stays in the answer.",
        "",
        "| Model | Failed answers (agent / baseline) | Eligibility right (agent / baseline) | Unseen clause cited (agent judge / baseline) "
        "| Agent escalated | Wrong agent decisions escalated | Agent accuracy when not escalated | Judge called search_policy |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {_name(r)} "
            f"| {_cell(r, 'agent', lambda m: str(m['failed']['n']))} / {_cell(r, 'baseline', lambda m: str(m['failed']['n']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['eligibility_accuracy']))} / {_cell(r, 'baseline', lambda m: _pct(m['eligibility_accuracy']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['raw_invented_citation_rate']))} / {_cell(r, 'baseline', lambda m: _pct(m['invented_citation_rate']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['escalated_share']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['wrong_decisions_escalated']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['accuracy_when_not_escalated']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['tool_use']['cases_using_search']))} |"
        )
    lines += [
        "",
        "## Speed and cost",
        "",
        "| Model | Seconds per case, median (agent / baseline) | LLM calls per case (agent / baseline) "
        "| Tokens per case in / out (agent) | Tokens per case in / out (baseline) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {_name(r)} "
            f"| {_cell(r, 'agent', lambda m: str(m['seconds_per_case']['median']))} / {_cell(r, 'baseline', lambda m: str(m['seconds_per_case']['median']))} "
            f"| {_cell(r, 'agent', lambda m: str(m['llm_calls_per_case']))} / {_cell(r, 'baseline', lambda m: str(m['llm_calls_per_case']))} "
            f"| {_cell(r, 'agent', _tokens)} | {_cell(r, 'baseline', _tokens)} |"
        )
    reports = path("outputs.reports_dir")
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"{out_name}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (reports / f"{out_name}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return out
