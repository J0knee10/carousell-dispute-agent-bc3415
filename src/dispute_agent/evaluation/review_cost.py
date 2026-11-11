"""Cost-based escalation threshold: which recommendations deserve a careful review?

Run with ``uv run dispute-agent review-cost``. It writes reports/review_cost.md
and reports/review_cost.csv.

A person checks every recommendation, because the agent never acts alone. A
confident recommendation gets a standard review, which the agent makes faster.
An escalated one gets a careful review, in which staff decide the dispute from
scratch. Escalating more costs staff time. Escalating less lets more wrong
recommendations through a standard review. The confidence threshold sets the
balance, and this module prices it.

The rule is a cost-sensitive reject option (Chow, 1970). An answer should get a
careful review when the expected cost of letting it stand is more than the
extra cost of the careful review. The judge's confidence is not a probability:
Gemini gives 0.9 or 0.95 to most of its mistakes. So the chance of a mistake is
not read off the model. It is measured on labelled cases, and the threshold is
the one with the lowest total cost per dispute on them.

Cost of one dispute at threshold t, in S$:

    staff       careful review if escalated, else standard review
                careful  = staff cost per hour x careful review minutes / 60
                standard = careful x (1 - time saved by the agent)
    AI usage    measured tokens x paid-tier price (the same at every threshold)
    mistake     only for a wrong recommendation that is not escalated:
                rework (one careful review when the wronged side appeals)
                + |refund share given - refund share due| x order value

The inputs and their low, base and high values are in config.yaml
(review_cost). The threshold is chosen on dev cases, labelled with the outcome
each case was written for. It is then checked on the test set (hand labels),
which plays no part in the choice.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from ..config import load_config, path
from .harness import load_records
from .metrics import failed_cases, latest_by_case

LEVELS = ("low", "base", "high")
FULL_REFUNDS = {"full_refund_with_return", "full_refund_without_return"}
EPS = 1e-9


@dataclass(frozen=True)
class Costs:
    """Unit costs in S$ at one level of the inputs."""

    careful: float
    standard: float
    order_value: float
    partial_share: float
    llm_in: float  # S$ per input token
    llm_out: float  # S$ per output token

    @property
    def extra(self) -> float:
        """What escalating one recommendation adds: a careful review instead of a standard one."""
        return self.careful - self.standard

    def mistake(self, money_share: float) -> float:
        """A wrong recommendation let through: rework plus the money moved wrongly."""
        return self.careful + money_share * self.order_value


def unit_costs(level: str = "base", cfg: dict | None = None) -> Costs:
    cfg = cfg or load_config()
    rc = cfg["review_cost"]
    careful = rc["staff_cost_per_hour"][level] * rc["careful_review_minutes"][level] / 60
    price = rc["llm_price_per_million"]
    rate = cfg["data"]["usd_to_sgd"]
    return Costs(
        careful=careful,
        standard=careful * (1 - rc["time_saved_by_agent"][level]),
        order_value=rc["order_value"][level],
        partial_share=rc["partial_refund_share"],
        llm_in=price["input"] * rate / 1e6,
        llm_out=price["output"] * rate / 1e6,
    )


def refund_share(outcome: str, percent: float | None, partial_share: float) -> float:
    """Share of the order refunded: 1 for a full refund, 0 for a decline."""
    if outcome in FULL_REFUNDS:
        return 1.0
    if outcome == "partial_refund":
        return percent / 100 if percent else partial_share
    return 0.0


@dataclass(frozen=True)
class Case:
    case_id: str
    run: str
    label: str
    pred: str | None  # None: the model never gave a valid answer
    pred_percent: float | None
    confidence: float | None
    judged: bool  # decided by the LLM, so the threshold applies (not by the eligibility rules)
    other_reasons: bool  # escalated by the review gate for a reason other than confidence
    tokens_in: float = 0.0
    tokens_out: float = 0.0

    @property
    def wrong(self) -> bool:
        return self.pred != self.label

    def escalated(self, threshold: float) -> bool:
        if self.pred is None or self.other_reasons:
            return True
        return self.judged and self.confidence is not None and self.confidence < threshold - EPS

    def money_share(self, partial_share: float) -> float:
        """Share of the order moved wrongly if this recommendation stands."""
        if not self.wrong or self.pred is None:
            return 0.0
        given = refund_share(self.pred, self.pred_percent, partial_share)
        return abs(given - refund_share(self.label, None, partial_share))


def _mean_tokens(runs: list[str]) -> tuple[float, float]:
    """Mean tokens per LLM-judged case over the runs that recorded them."""
    tin, tout = [], []
    for run in runs:
        for r in latest_by_case(load_records(run, "agent")).values():
            if r.get("llm_calls") and r.get("tokens_in") is not None:
                tin.append(r["tokens_in"])
                tout.append(r.get("tokens_out") or 0)
    return (sum(tin) / len(tin), sum(tout) / len(tout)) if tin else (0.0, 0.0)


def load_cases(runs: list[str], split: str, mean_tokens: tuple[float, float] = (0.0, 0.0)) -> list[Case]:
    """The agent's answers in these runs, for the cases of one split that have a label."""
    from ..data.cases import load_splits
    from ..data.labels import resolved_labels

    labels = resolved_labels()
    in_split = set(load_splits().get(split, []))
    cases = []
    for run in runs:
        records = load_records(run, "agent")
        if not records:
            raise FileNotFoundError(f"No agent predictions in outputs/runs/{run}")
        preds, failed = latest_by_case(records), failed_cases(records)
        for cid in sorted(set(preds) | set(failed)):
            label = labels.get(cid, {}).get("outcome")
            if cid not in in_split or not label:
                continue
            p = preds.get(cid)
            if p is None:  # never answered: handed to a person
                cases.append(Case(cid, run, label, None, None, None, True, True, *mean_tokens))
                continue
            judged = p.get("decided_by") == "llm"
            calls = p.get("llm_calls") or 0
            if p.get("tokens_in") is not None:
                tokens = (p["tokens_in"], p.get("tokens_out") or 0)
            else:
                tokens = mean_tokens if calls else (0.0, 0.0)
            other = any(not r.startswith("Confidence ") for r in p.get("escalation_reasons") or [])
            cases.append(Case(
                case_id=cid, run=run, label=label, pred=p["predicted_outcome"],
                pred_percent=p.get("partial_refund_percent"), confidence=p.get("confidence"),
                judged=judged, other_reasons=other or (p.get("escalate", False) and not p.get("escalation_reasons")),
                tokens_in=tokens[0], tokens_out=tokens[1],
            ))
    return cases


@dataclass(frozen=True)
class Result:
    threshold: float
    disputes: int
    escalated: int
    mistakes: int
    caught: int
    staff: float
    ai: float
    mistake_cost: float

    @property
    def total(self) -> float:
        return self.staff + self.ai + self.mistake_cost

    @property
    def per_dispute(self) -> float:
        return self.total / self.disputes if self.disputes else 0.0


def evaluate(cases: list[Case], threshold: float, costs: Costs) -> Result:
    staff = ai = mistake_cost = 0.0
    escalated = mistakes = caught = 0
    for c in cases:
        esc = c.escalated(threshold)
        escalated += esc
        staff += costs.careful if esc else costs.standard
        ai += c.tokens_in * costs.llm_in + c.tokens_out * costs.llm_out
        if c.wrong:
            mistakes += 1
            if esc:
                caught += 1
            else:
                mistake_cost += costs.mistake(c.money_share(costs.partial_share))
    return Result(threshold, len(cases), escalated, mistakes, caught, staff, ai, mistake_cost)


def cheapest(results: list[Result], current: float) -> tuple[float, list[float]]:
    """The cheapest threshold, and every threshold tied with it.

    On a tie the current threshold stays if it is among the cheapest; otherwise
    the lowest tied threshold wins, as it escalates least.
    """
    best = min(r.total for r in results)
    tied = [r.threshold for r in results if r.total <= best + 1e-6]
    keep = [t for t in tied if abs(t - current) < EPS]
    return (keep[0] if keep else min(tied)), tied


def break_even(cases: list[Case], threshold: float, current: float, costs: Costs) -> str:
    """How expensive a mistake must be for this threshold to beat the current one."""
    a, b = evaluate(cases, current, costs), evaluate(cases, threshold, costs)
    d_esc, d_caught = b.escalated - a.escalated, b.caught - a.caught
    if d_esc == 0 and d_caught == 0:
        return "same cases escalated"
    if threshold > current:
        if d_caught <= 0:
            return "never (escalates more, catches no more)"
        return f"if a mistake costs over S${d_esc * costs.extra / d_caught:,.0f}"
    if d_caught >= 0:
        return "always (escalates less, misses no more)"
    return f"if a mistake costs under S${-d_esc * costs.extra / -d_caught:,.0f}"


def bootstrap(cases: list[Case], thresholds: list[float], costs: Costs, current: float, n: int, seed: int) -> dict:
    """Resample the cases: how often each threshold is among the cheapest, and how
    often a higher or a lower threshold is strictly cheaper than the current one."""
    rng = random.Random(seed)
    among = {t: 0 for t in thresholds}
    higher = lower = 0
    for _ in range(n):
        sample = [rng.choice(cases) for _ in cases]
        results = [evaluate(sample, t, costs) for t in thresholds]
        _, tied = cheapest(results, current)
        for t in tied:
            among[t] += 1
        now = next(r.total for r in results if abs(r.threshold - current) < EPS)
        best_up = min((r.total for r in results if r.threshold > current + EPS), default=now)
        best_down = min((r.total for r in results if r.threshold < current - EPS), default=now)
        higher += best_up < now - 1e-6
        lower += best_down < now - 1e-6
    return {"n": n, "among_cheapest": {t: v / n for t, v in among.items()}, "higher_cheaper": higher / n, "lower_cheaper": lower / n}


def by_confidence(cases: list[Case], costs: Costs) -> list[dict]:
    """For each confidence the judge gave: how often it was wrong, and what letting it stand costs."""
    groups: dict[float, list[Case]] = {}
    for c in cases:
        if c.judged and c.pred is not None and c.confidence is not None:
            groups.setdefault(c.confidence, []).append(c)
    rows = []
    for conf in sorted(groups):
        g = groups[conf]
        cost = sum(costs.mistake(c.money_share(costs.partial_share)) for c in g if c.wrong)
        rows.append({
            "confidence": conf, "answers": len(g), "wrong": sum(c.wrong for c in g),
            "stand_cost": cost / len(g), "review_pays": cost / len(g) > costs.extra,
        })
    return rows


# --- Report -------------------------------------------------------------------

def _s(v: float, dp: int = 2) -> str:
    return f"S${v:,.{dp}f}"


def _pct(v: float) -> str:
    return f"{v:.0%}"


def _t(t: float) -> str:
    return f"{t:.2f}"


def _threshold_rows(cases: list[Case], thresholds: list[float], current: float, costs: dict[str, Costs]) -> tuple[list[str], float, list[float]]:
    base = [evaluate(cases, t, costs["base"]) for t in thresholds]
    choice, tied = cheapest(base, current)
    lines = [
        "| Escalate below | Escalated | Mistakes caught | Cost per dispute (low / **base** / high) | Beats the current threshold |",
        "|---|---|---|---|---|",
    ]
    for r in base:
        per = [evaluate(cases, r.threshold, costs[lvl]).per_dispute for lvl in LEVELS]
        name = _t(r.threshold) + (" (current)" if abs(r.threshold - current) < EPS else "")
        cost = f"{_s(per[0])} / **{_s(per[1])}** / {_s(per[2])}"
        if r.threshold in tied:
            name = f"**{name}**"
        vs = "" if abs(r.threshold - current) < EPS else break_even(cases, r.threshold, current, costs["base"])
        lines.append(f"| {name} | {r.escalated} of {r.disputes} ({_pct(r.escalated / r.disputes)}) | {r.caught} of {r.mistakes} | {cost} | {vs} |")
    return lines, choice, tied


def _describe(cases: list[Case]) -> str:
    judged = sum(c.judged for c in cases)
    runs = sorted({c.run for c in cases})
    return f"{len(cases)} cases ({judged} judged by the LLM, {len(cases) - judged} decided by the eligibility rules) from {', '.join(f'`{r}`' for r in runs)}"


def build_review_cost(tune_runs: list[str] | None = None, check_runs: list[str] | None = None, out_name: str = "review_cost") -> Path:
    cfg = load_config()
    rc = cfg["review_cost"]
    tune_runs = tune_runs or rc["tune_runs"]
    check_runs = check_runs if check_runs is not None else rc["check_runs"]
    thresholds = sorted(rc["thresholds"])
    current = cfg["agent"]["confidence_threshold"]
    if not any(abs(t - current) < EPS for t in thresholds):
        thresholds = sorted([*thresholds, current])
    costs = {lvl: unit_costs(lvl, cfg) for lvl in LEVELS}
    base = costs["base"]

    tokens = _mean_tokens([*tune_runs, *check_runs])
    tune = load_cases(tune_runs, "dev", tokens)
    checks = {run: load_cases([run], "test", tokens) for run in check_runs}
    if not tune:
        raise ValueError("No labelled dev cases in the tuning runs")

    tune_lines, choice, tied = _threshold_rows(tune, thresholds, current, costs)
    choice_by_level = {lvl: cheapest([evaluate(tune, t, costs[lvl]) for t in thresholds], current)[0] for lvl in LEVELS}
    boot = bootstrap(tune, thresholds, base, current, rc["bootstrap"], cfg["data"]["seed"])
    at_current = evaluate(tune, current, base)
    at_choice = evaluate(tune, choice, base)
    ai_case = at_current.ai / max(1, sum(c.judged for c in tune))
    tied_text = (f"{_t(min(tied))} to {_t(max(tied))} cost the same" if len(tied) > 1 else "")

    L = [
        "# Cost-based escalation threshold",
        "",
        "_Generated by `uv run dispute-agent review-cost` (src/dispute_agent/evaluation/review_cost.py). "
        "Inputs: `review_cost` in config.yaml._",
        "",
        "A person checks every recommendation. A confident one gets a standard review, which the agent makes "
        "faster; an escalated one gets a careful review, in which staff decide the dispute from scratch. "
        "Escalating more costs staff time; escalating less lets more wrong recommendations through. "
        "This report prices both and finds the confidence threshold with the lowest cost per dispute.",
        "",
        "The rule is a cost-sensitive reject option (Chow, 1970): an answer deserves a careful review when the "
        "expected cost of letting it stand is more than the extra cost of the careful review. Gemini's "
        "confidence is not a probability, so the chance of a mistake at each confidence is measured on "
        "labelled cases, not read off the model.",
        "",
        "## Answer",
        "",
        f"- **Chosen on dev cases:** at base costs the cheapest threshold is **{_t(choice)}**"
        + (f" ({tied_text}, so the current {_t(current)} is kept)" if len(tied) > 1 and abs(choice - current) < EPS else
           f" ({tied_text})" if len(tied) > 1 else "")
        + f". At the current {_t(current)} a dispute costs {_s(at_current.per_dispute)}; "
        f"at {_t(choice)} it costs {_s(at_choice.per_dispute)}"
        + (f", {_s(at_current.per_dispute - at_choice.per_dispute)} less "
           f"({_pct((at_current.per_dispute - at_choice.per_dispute) / at_current.per_dispute)}), or about "
           f"{_s(round((at_current.per_dispute - at_choice.per_dispute) * rc['disputes_per_year']['base'], -2), 0)} a year at "
           f"{rc['disputes_per_year']['base']:,} disputes" if at_choice.per_dispute < at_current.per_dispute - 1e-9 else "")
        + ".",
        f"- **Low and high inputs:** the cheapest threshold is {_t(choice_by_level['low'])} with every input at its "
        f"low value and {_t(choice_by_level['high'])} with every input at its high value.",
        f"- **How sure:** in {boot['n']:,} resamples of the dev cases, a threshold above {_t(current)} is strictly "
        f"cheaper than {_t(current)} in {_pct(boot['higher_cheaper'])} of them and one below it in "
        f"{_pct(boot['lower_cheaper'])}.",
    ]
    for run, cases in checks.items():
        a, b = evaluate(cases, current, base), evaluate(cases, choice, base)
        test_choice = cheapest([evaluate(cases, t, base) for t in thresholds], current)[0]
        line = (f"- **Check on the test set (`{run}`, not used to choose):** {_t(current)} escalates "
                f"{a.escalated} of {a.disputes} and catches {a.caught} of {a.mistakes} mistakes, at "
                f"{_s(a.per_dispute)} a dispute")
        if abs(choice - current) > EPS:
            line += (f"; {_t(choice)} escalates {b.escalated}, catches {b.caught}, at {_s(b.per_dispute)}")
        line += f". The cheapest on the test set would be {_t(test_choice)}."
        L.append(line)
    L += [
        f"- **AI usage** is about {_s(ai_case, 4)} per judged case (measured tokens at the paid-tier price), "
        f"against {_s(base.extra)} of extra staff time for one escalation. It is the same at every threshold, "
        "so it does not move the choice.",
        "",
        "## Inputs",
        "",
        "| Input | Low | Base | High | Source |",
        "|---|---|---|---|---|",
    ]
    names = {
        "staff_cost_per_hour": "Staff cost per hour (S$)",
        "careful_review_minutes": "Careful review (minutes)",
        "time_saved_by_agent": "Time a confident recommendation saves",
        "order_value": "Average 'Buy' order (S$)",
        "disputes_per_year": "Disputes reaching staff a year",
    }
    for key, name in names.items():
        v = rc[key]
        fmt = _pct if key == "time_saved_by_agent" else (lambda x: f"{x:,}")
        L.append(f"| {name} | {fmt(v['low'])} | {fmt(v['base'])} | {fmt(v['high'])} | {v.get('source', '')} |")
    price = rc["llm_price_per_million"]
    L += [
        f"| Partial refund due, share of the order | | {_pct(rc['partial_refund_share'])} | | "
        "Labels give the outcome, not the amount; Gemini's partial refunds: median 15%, mean 23% |",
        f"| AI price (US$ per million tokens) | | {price['input']:g} in / {price['output']:g} out | | "
        f"Gemini paid tier for the judge model; tokens measured: {tokens[0]:,.0f} in and {tokens[1]:,.0f} out "
        "per judged case |",
        "",
        "## What each event costs",
        "",
        "| Event | Low | Base | High |",
        "|---|---|---|---|",
    ]

    def row(name: str, fn, dp: int = 2) -> str:
        return f"| {name} | " + " | ".join(_s(fn(costs[lvl]), dp) for lvl in LEVELS) + " |"

    L += [
        row("Standard review of a confident recommendation", lambda c: c.standard),
        row("Careful review of an escalated one", lambda c: c.careful),
        row("**Extra cost of escalating one recommendation**", lambda c: c.extra),
        row("AI usage per judged case", lambda c: tokens[0] * c.llm_in + tokens[1] * c.llm_out, 4),
        row("Mistake let through: partial refund vs decline", lambda c: c.mistake(c.partial_share)),
        row("Mistake let through: partial vs full refund", lambda c: c.mistake(1 - c.partial_share)),
        row("Mistake let through: full refund vs decline", lambda c: c.mistake(1)),
        "",
        "A mistake let through costs one careful review of rework (the wronged side appeals) plus the money "
        "moved wrongly: the gap between the refund given and the refund due, as a share of the order.",
        "",
        "**When escalating pays.** Escalating an answer costs the extra review for certain and saves the "
        "mistake cost only if the answer was wrong. So it pays when the chance of a mistake is above "
        "extra cost ÷ mistake cost:",
        "",
        "| Kind of mistake | Low | Base | High |",
        "|---|---|---|---|",
    ]
    for name, share in [("Partial refund vs decline", None), ("Partial vs full refund", "pf"), ("Full refund vs decline", 1.0)]:
        cells = []
        for lvl in LEVELS:
            c = costs[lvl]
            s = c.partial_share if share is None else (1 - c.partial_share if share == "pf" else share)
            cells.append(_pct(c.extra / c.mistake(s)))
        L.append(f"| {name} | " + " | ".join(cells) + " |")

    L += [
        "",
        f"## Mistakes by confidence (dev cases, base costs)",
        "",
        f"Data: {_describe(tune)}.",
        "",
        "| Confidence | Answers | Wrong | Expected mistake cost if it stands | Careful review pays? |",
        "|---|---|---|---|---|",
    ]
    for r in by_confidence(tune, base):
        pays = f"yes (above {_s(base.extra)})" if r["review_pays"] else f"no (below {_s(base.extra)})"
        L.append(f"| {r['confidence']:.2f} | {r['answers']} | {r['wrong']} | {_s(r['stand_cost'])} | {pays} |")
    L += [
        "",
        f"## Cost per dispute by threshold (dev cases, chosen here)",
        "",
        "Escalated counts every escalation reason, not only low confidence; the review gate's other reasons "
        "apply at every threshold. Bold: the cheapest at base costs.",
        "",
        *tune_lines,
        "",
        "Share of resamples in which each threshold is among the cheapest (base costs): "
        + ", ".join(f"{_t(t)} {_pct(v)}" for t, v in boot["among_cheapest"].items()) + ".",
    ]
    for run, cases in checks.items():
        lines, _, _ = _threshold_rows(cases, thresholds, current, costs)
        L += [
            "",
            f"## Check on the test set (`{run}`, not used to choose)",
            "",
            f"Data: {_describe(cases)}; hand labels.",
            "",
            *lines,
            "",
            "| Confidence | Answers | Wrong | Expected mistake cost if it stands | Careful review pays? |",
            "|---|---|---|---|---|",
        ]
        for r in by_confidence(cases, base):
            pays = "yes" if r["review_pays"] else "no"
            L.append(f"| {r['confidence']:.2f} | {r['answers']} | {r['wrong']} | {_s(r['stand_cost'])} | {pays} |")
    L += [
        "",
        "## Caveats",
        "",
        f"- **Few mistakes.** The dev cases hold {at_current.mistakes} mistakes, so one case more or less can "
        "move the answer. The resampling line above shows how much.",
        "- **Dev labels** are the outcomes the cases were written for, not hand labels. The dev runs are from "
        "28 Oct, before the `search_policy` tool was added; `gemini_seed` ran before the decision-guide fix. "
        "`dev_borderline_v2` holds only borderline cases, where mistakes are most common.",
        "- **Two simplifications favour escalating:** a careful review is assumed always to reach the right "
        "answer, and a standard review to miss every mistake. If staff catch some mistakes in a standard "
        "review, escalating is worth less than shown.",
        "- **The mistake cost** assumes every wrong decision is appealed and counts a full refund as lost even "
        "when the item goes back to the seller (both overstate it). It leaves out a user who stops using "
        "'Buy' after an unfair decision (understates it).",
        "- **The test set** has now been used for this check too; it played no part in choosing the threshold.",
    ]

    reports = path("outputs.reports_dir")
    reports.mkdir(parents=True, exist_ok=True)
    out = reports / f"{out_name}.md"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    with open(reports / f"{out_name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["set", "runs", "threshold", "level", "disputes", "escalated", "mistakes", "mistakes_caught",
                    "staff_sgd", "ai_sgd", "mistakes_sgd", "cost_per_dispute_sgd"])
        sets = [("dev", tune_runs, tune), *(("test", [run], cases) for run, cases in checks.items())]
        for name, runs, cases in sets:
            for t in thresholds:
                for lvl in LEVELS:
                    r = evaluate(cases, t, costs[lvl])
                    w.writerow([name, " ".join(runs), t, lvl, r.disputes, r.escalated, r.mistakes, r.caught,
                                round(r.staff, 2), round(r.ai, 4), round(r.mistake_cost, 2), round(r.per_dispute, 2)])
    return out
