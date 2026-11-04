"""Compare several evaluation runs (one per judge model or variant) in one report."""

from __future__ import annotations

import json
from math import comb
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


def _reasons(m: dict) -> str:
    top = sorted(m.get("escalation_reasons", {}).items(), key=lambda kv: -kv[1])[:2]
    return "; ".join(f"{k} ({v})" for k, v in top) or "none"


def _name(r: dict) -> str:
    n = (r.get("agent") or r.get("baseline") or {}).get("n", 0)
    extra = [r["variant"]] if r["variant"] else []
    if n and n < 50:
        extra.append(f"first {n} cases only")
    return f"`{r['model']}`" + (f" ({', '.join(extra)})" if extra else "")


def mcnemar(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value: b = cases only the agent got right, c = only the baseline."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired(run: str) -> dict | None:
    """Agent vs baseline on the same cases (a failed answer counts as wrong)."""
    from ..data.labels import resolved_labels
    from .metrics import latest_by_case

    labels = resolved_labels()
    agent = latest_by_case(load_records(run, "agent"))
    base = latest_by_case(load_records(run, "baseline"))
    ids = {r["case_id"] for r in load_records(run, "agent")} & {r["case_id"] for r in load_records(run, "baseline")}
    ids = [i for i in ids if labels.get(i, {}).get("outcome")]
    if not ids:
        return None
    right = lambda preds, i: i in preds and preds[i]["predicted_outcome"] == labels[i]["outcome"]  # noqa: E731
    b = sum(right(agent, i) and not right(base, i) for i in ids)
    c = sum(right(base, i) and not right(agent, i) for i in ids)
    return {"agent_only": b, "baseline_only": c, "p": round(mcnemar(b, c), 3)}


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
        "paired": paired(run),
        **results,
    }


def build_comparison(runs: list[str], out_name: str = "model_comparison", hardware: str = "", notes: Path | None = None) -> Path:
    """notes: a Markdown file with the written conclusions, placed after the title."""
    rows = [load_run(run) for run in runs]
    lines = ["# Model comparison", ""]
    if notes:
        lines += [Path(notes).read_text(encoding="utf-8").strip(), "", "## The numbers", ""]
    if hardware:
        lines.append(f"- Local hardware: {hardware}")
    lines += [
        "- Runs: " + ", ".join(f"[{r['run']}](evaluation_{r['run']}.md)" for r in rows),
        "- Same held-out test cases and prompts for every model, temperature 0. Only the judge model changes.",
        "- A case with no valid answer (for example invalid JSON twice) counts as wrong.",
        "- Paired test: cases only the agent got right vs cases only the baseline got right, with an exact McNemar test "
        "(p below 0.05 means the difference is unlikely to be chance on these 50 cases).",
        "- Gemini's seconds per case include the free-tier pacing (at least 4.5 s between calls); local models are not paced.",
        "",
        "## Decision accuracy",
        "",
        "| Model | Runs on | Agent | Baseline | Agent minus baseline | Paired test | Agent clear / borderline / ineligible | Baseline clear / borderline / ineligible |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gain = "n/a"
        if r.get("agent", {}).get("n") and r.get("baseline", {}).get("n"):
            gain = f"{(r['agent']['decision_accuracy'] - r['baseline']['decision_accuracy']) * 100:+.0f} pts"
        pt = r.get("paired")
        test = f"{pt['agent_only']} vs {pt['baseline_only']} cases, p = {pt['p']:.2f}" if pt else "n/a"
        lines.append(
            f"| {_name(r)} | {WHERE.get(r['provider'], r['provider'])} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['decision_accuracy']))} "
            f"| {_cell(r, 'baseline', lambda m: _pct(m['decision_accuracy']))} | {gain} | {test} "
            f"| {_cell(r, 'agent', _by_difficulty)} | {_cell(r, 'baseline', _by_difficulty)} |"
        )
    lines += [
        "",
        "## Reliability",
        "",
        "Unseen clause: the model cited a clause ID that does not exist or that it was never shown. For the agent "
        "this is counted before the citation check removes it; for the baseline (which has no check) it stays in "
        "the answer. Format errors (a real ID with the heading text pasted after it) are counted separately.",
        "",
        "| Model | Failed answers (agent / baseline) | Eligibility right (agent / baseline) | Unseen clause cited (agent judge / baseline) "
        "| Citation format errors (baseline) | Agent escalated | Wrong agent decisions escalated | Agent accuracy when not escalated "
        "| Judge called search_policy | Main escalation reasons (agent) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {_name(r)} "
            f"| {_cell(r, 'agent', lambda m: str(m['failed']['n']))} / {_cell(r, 'baseline', lambda m: str(m['failed']['n']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['eligibility_accuracy']))} / {_cell(r, 'baseline', lambda m: _pct(m['eligibility_accuracy']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['raw_invented_citation_rate']))} / {_cell(r, 'baseline', lambda m: _pct(m['invented_citation_rate']))} "
            f"| {_cell(r, 'baseline', lambda m: _pct(m['citation_format_error_rate']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['escalated_share']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['wrong_decisions_escalated']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['escalation']['accuracy_when_not_escalated']))} "
            f"| {_cell(r, 'agent', lambda m: _pct(m['tool_use']['cases_using_search']))} "
            f"| {_cell(r, 'agent', _reasons)} |"
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
