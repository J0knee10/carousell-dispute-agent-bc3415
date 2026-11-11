"""Build findings.json for update_report.py from the evaluation JSONs plus written text."""
import csv
import json
import sys
from pathlib import Path

R = Path("reports")
OUT = Path(sys.argv[1])


def load(run):
    return json.loads((R / f"evaluation_{run}.json").read_text(encoding="utf-8"))


def pct(x):
    return "n/a" if x is None else f"{x:.0%}"


g = load("cmp_gemini-flash-lite")
ll = load("cmp_llama3.1-8b")
qw = load("cmp_qwen3-8b")
ln = load("abl_llama3.1-8b_norag")["agent"]
qn = load("abl_qwen3-8b_norag")["agent"]
la = load("abl_llama3.1-8b_agentic")["agent"]
qa = load("abl_qwen3-8b_agentic")["agent"]
ga, gb = g["agent"], g["baseline"]


def d(m, k):
    return pct(m["accuracy_by_difficulty"][k]["accuracy"])


headline = [
    ["Decision accuracy (4 outcomes)", pct(ga["decision_accuracy"]), pct(gb["decision_accuracy"])],
    ["   clear cases (n = 30)", d(ga, "clear"), d(gb, "clear")],
    ["   borderline cases (n = 15)", d(ga, "borderline"), d(gb, "borderline")],
    ["   ineligible cases (n = 5)", d(ga, "ineligible"), d(gb, "ineligible")],
    ["Direction accuracy (refund vs decline)", pct(ga["direction_accuracy"]), pct(gb["direction_accuracy"])],
    ["Eligibility accuracy", pct(ga["eligibility_accuracy"]), pct(gb["eligibility_accuracy"])],
    ["Cases with invented clause IDs", pct(ga["invented_citation_rate"]), pct(gb["invented_citation_rate"])],
    [f"Buyer-win cases right (n = {ga['buyer_win_accuracy']['n']})", pct(ga["buyer_win_accuracy"]["accuracy"]), pct(gb["buyer_win_accuracy"]["accuracy"])],
    [f"Seller-win cases right (n = {ga['seller_win_accuracy']['n']})", pct(ga["seller_win_accuracy"]["accuracy"]), pct(gb["seller_win_accuracy"]["accuracy"])],
    ["Escalated to a person", pct(ga["escalation"]["escalated_share"]), pct(gb["escalation"]["escalated_share"])],
    ["Wrong decisions that were escalated", pct(ga["escalation"]["wrong_decisions_escalated"]), pct(gb["escalation"]["wrong_decisions_escalated"])],
    ["Accuracy on cases not escalated", pct(ga["escalation"]["accuracy_when_not_escalated"]), pct(gb["escalation"]["accuracy_when_not_escalated"])],
    ["Seconds per case (median)", f"{ga['seconds_per_case']['median']:.1f}", f"{gb['seconds_per_case']['median']:.1f}"],
    ["LLM calls per case", str(ga["llm_calls_per_case"]), "1"],
]
assert len(headline) == 14

F = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))  # the written text
F["gemini"] = {
    "headline_rows": headline,
    "wrong": [
        ["G008", "Partial refund", "Full refund with return", "Not escalated; the missing knobs could be judged either way"],
        ["G059", "Full refund with return", "Decline", "Escalated; judgement call (the AI reviewer also said decline)"],
        ["G125", "Decline", "Partial refund", "Escalated; the baseline made the same mistake"],
        ["G129", "Partial refund", "Decline", "Judgement call (scratch on the container only); the baseline got it right"],
        ["G147", "Partial refund", "Decline", "Judgement call (‘6/10’ complaint on a ‘like new’ case); the baseline got it right"],
    ],
}
F["comparison_table"] = [
    ["Judge model (where it runs)", "Agent: all / clear / borderline", "Single prompt: all / clear / borderline", "Notes"],
    ["Gemini Flash-Lite (Google cloud, free tier)", f"{pct(ga['decision_accuracy'])} / {d(ga,'clear')} / {d(ga,'borderline')}",
     f"{pct(gb['decision_accuracy'])} / {d(gb,'clear')} / {d(gb,'borderline')}", "9 s a case; refunded 1 of 21 cases that should be declined"],
    ["Llama 3.1 8B (our PC, Ollama)", f"{pct(ll['agent']['decision_accuracy'])} / {d(ll['agent'],'clear')} / {d(ll['agent'],'borderline')}",
     f"{pct(ll['baseline']['decision_accuracy'])} / {d(ll['baseline'],'clear')} / {d(ll['baseline'],'borderline')}", "15 s a case; refunded 19 of 21 that should be declined"],
    ["Qwen 3 8B (our PC, Ollama)", f"{pct(qw['agent']['decision_accuracy'])} / {d(qw['agent'],'clear')} / {d(qw['agent'],'borderline')}",
     f"{pct(qw['baseline']['decision_accuracy'])} / {d(qw['baseline'],'clear')} / {d(qw['baseline'],'borderline')}", "19 s a case; refunded 20 of 21; the single prompt refunded all 21"],
]
F["retrieval_table"] = [
    ["Retrieval design", "Llama 3.1 8B", "Qwen 3 8B", "What happens"],
    ["Per gap (default)", pct(ll["agent"]["decision_accuracy"]), pct(qw["agent"]["decision_accuracy"]),
     "One search per gap before the judgement; search_policy as a fallback"],
    ["Agent-driven (plan, search, judge)", pct(la["decision_accuracy"]), pct(qa["decision_accuracy"]),
     f"General clauses only; a planning step calls search_policy (Llama in {pct(la['tool_use']['cases_using_search'])} of cases, Qwen {pct(qa['tool_use']['cases_using_search'])}); one more LLM call"],
    ["None (ablation)", pct(ln["decision_accuracy"]), pct(qn["decision_accuracy"]),
     "No policy clauses: nothing can be cited, so the check escalates every judged case"],
]
lr = load("abl_llama3.1-8b_rubric")["agent"]
lrn = load("abl_llama3.1-8b_rubric_norag")["agent"]
qr = load("abl_qwen3-8b_rubric")["agent"]
qrn = load("abl_qwen3-8b_rubric_norag")["agent"]
gr = load("probe_gemini_rubric")["agent"]
grn = load("probe_gemini_rubric_norag")["agent"]
F["rubric_table"] = [
    ["Decision guide, retrieval", "Llama 3.1 8B", "Qwen 3 8B", "Gemini (first 25, all clear)"],
    ["Full guide, per gap (default)", pct(ll["agent"]["decision_accuracy"]), pct(qw["agent"]["decision_accuracy"]), "92% (23 of 25)"],
    ["Full guide, no retrieval", pct(ln["decision_accuracy"]), pct(qn["decision_accuracy"]), "not run"],
    ["Rubric only, per gap", pct(lr["decision_accuracy"]), pct(qr["decision_accuracy"]), pct(gr["decision_accuracy"])],
    ["Rubric only, no retrieval", pct(lrn["decision_accuracy"]), pct(qrn["decision_accuracy"]), pct(grn["decision_accuracy"])],
]

# Section 9.7: the escalation threshold, from `uv run dispute-agent review-cost`
def md_table(path, header):
    """Rows of the Markdown table whose header row starts with `header`, bold marks removed."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"| {header} |"))
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        cells = [c.strip().replace("**", "") for c in line.strip().strip("|").split("|")]
        if not set("".join(cells)) <= set("-: "):  # skip the |---| line
            rows.append(cells)
    return rows


events = md_table(R / "review_cost.md", "Event")
events[0][0] = "What it costs"
F["threshold_costs_table"] = events
rc = [r for r in csv.DictReader((R / "review_cost.csv").open(encoding="utf-8")) if r["level"] == "base"]


def rc_cell(s, t):
    r = next(r for r in rc if r["set"] == s and float(r["threshold"]) == t)
    n, esc = int(r["disputes"]), int(r["escalated"])
    cheapest = float(r["cost_per_dispute_sgd"]) == min(float(x["cost_per_dispute_sgd"]) for x in rc if x["set"] == s)
    return [f"{esc} ({esc / n:.0%}); {r['mistakes_caught']} of {r['mistakes']}",
            f"S${float(r['cost_per_dispute_sgd']):.2f}" + (" (cheapest)" if cheapest else "")]


n_dev = next(int(r["disputes"]) for r in rc if r["set"] == "dev")
n_test = next(int(r["disputes"]) for r in rc if r["set"] == "test")
F["threshold_table"] = [["Escalate below", f"Dev ({n_dev} cases): escalated; mistakes caught", "Dev: cost per dispute",
                         f"Test ({n_test} cases): escalated; mistakes caught", "Test: cost per dispute"]]
for t in (0.7, 0.8, 0.85, 0.9, 0.95, 1.0):
    F["threshold_table"].append([f"{t:.2f}" + (" (now)" if t == 0.7 else "")] + rc_cell("dev", t) + rc_cell("test", t))

nums = {
    "lr": pct(lr["decision_accuracy"]), "lrn": pct(lrn["decision_accuracy"]),
    "qr": pct(qr["decision_accuracy"]), "qrn": pct(qrn["decision_accuracy"]),
    "lr_sw": pct(lr["seller_win_accuracy"]["accuracy"]), "lrn_sw": pct(lrn["seller_win_accuracy"]["accuracy"]),
    "qr_sw": pct(qr["seller_win_accuracy"]["accuracy"]), "qrn_sw": pct(qrn["seller_win_accuracy"]["accuracy"]),
    "la": pct(la["decision_accuracy"]), "qa": pct(qa["decision_accuracy"]),
    "ls": pct(la["tool_use"]["cases_using_search"]), "qs": pct(qa["tool_use"]["cases_using_search"]),
    "la_calls": la["llm_calls_per_case"], "qa_calls": qa["llm_calls_per_case"],
    "la_sec": la["seconds_per_case"]["median"], "qa_sec": qa["seconds_per_case"]["median"],
}
for k, v in list(F.items()):
    if isinstance(v, str):
        F[k] = v.format(**nums)
    elif isinstance(v, list) and all(isinstance(x, str) for x in v):
        F[k] = [x.format(**nums) for x in v]
OUT.write_text(json.dumps(F, indent=1, ensure_ascii=False), encoding="utf-8")
print("ok", nums)
