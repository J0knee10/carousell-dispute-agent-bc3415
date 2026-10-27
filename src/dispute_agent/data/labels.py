"""The labelling sheet: provisional labels from the case author, plus two human labellers.

data/labels/labels.csv has one row per case. B1 and B2 fill their columns
separately; `final_*` settles disagreements. Evaluation uses, in order: the
final label, else the label both labellers agree on, else the provisional label.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from ..config import path
from ..schemas import OUTCOMES
from .cases import load_all_cases, load_splits

COLUMNS = [
    "case_id", "split", "difficulty", "scenario", "listing_title",
    "provisional_outcome", "provisional_eligible",
    "b1_outcome", "b1_eligible", "b2_outcome", "b2_eligible",
    "final_outcome", "final_eligible", "notes",
]
HUMAN_COLUMNS = ["b1_outcome", "b1_eligible", "b2_outcome", "b2_eligible", "final_outcome", "final_eligible", "notes"]


def _bool(text: str) -> bool | None:
    t = (text or "").strip().lower()
    if t in ("true", "yes", "y", "1"):
        return True
    if t in ("false", "no", "n", "0"):
        return False
    return None


def _outcome(text: str) -> str | None:
    t = (text or "").strip().lower().replace(" ", "_")
    return t if t in OUTCOMES else None


def read_sheet(file: Path | None = None) -> dict[str, dict]:
    file = file or path("data.labels")
    if not file.exists():
        return {}
    with open(file, encoding="utf-8", newline="") as f:
        return {row["case_id"]: row for row in csv.DictReader(f)}


def export_sheet(file: Path | None = None) -> tuple[Path, int]:
    """Write or refresh the sheet. Human-entered columns are never overwritten."""
    file = file or path("data.labels")
    existing = read_sheet(file)
    splits = load_splits()
    split_of = {cid: name for name, ids in splits.items() for cid in ids}
    rows = []
    for case in load_all_cases():
        row = {
            "case_id": case.case_id,
            "split": split_of.get(case.case_id, ""),
            "difficulty": case.meta.difficulty,
            "scenario": case.meta.scenario,
            "listing_title": case.listing.title[:60],
            "provisional_outcome": case.meta.target_outcome or "",
            "provisional_eligible": str(case.meta.target_eligible),
        }
        old = existing.get(case.case_id, {})
        for col in HUMAN_COLUMNS:
            row[col] = old.get(col, "")
        rows.append(row)
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return file, len(rows)


def resolved_labels() -> dict[str, dict]:
    """case_id -> {outcome, eligible, source} using final > agreed > provisional."""
    sheet = read_sheet()
    out = {}
    for case in load_all_cases():
        row = sheet.get(case.case_id, {})
        final_o, final_e = _outcome(row.get("final_outcome", "")), _bool(row.get("final_eligible", ""))
        b1_o, b2_o = _outcome(row.get("b1_outcome", "")), _outcome(row.get("b2_outcome", ""))
        b1_e, b2_e = _bool(row.get("b1_eligible", "")), _bool(row.get("b2_eligible", ""))
        if final_o:
            label = {"outcome": final_o, "eligible": final_e if final_e is not None else case.meta.target_eligible, "source": "final"}
        elif b1_o and b1_o == b2_o:
            eligible = b1_e if b1_e is not None and b1_e == b2_e else case.meta.target_eligible
            label = {"outcome": b1_o, "eligible": eligible, "source": "agreed"}
        else:
            label = {"outcome": case.meta.target_outcome, "eligible": case.meta.target_eligible, "source": "provisional"}
        out[case.case_id] = label
    return out


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


def agreement_report() -> dict:
    sheet = read_sheet()
    pairs = [(cid, _outcome(r.get("b1_outcome", "")), _outcome(r.get("b2_outcome", ""))) for cid, r in sheet.items()]
    both = [(cid, x, y) for cid, x, y in pairs if x and y]
    if not both:
        return {"labelled_by_both": 0, "message": "No case has both B1 and B2 outcome labels yet."}
    a = [x for _, x, _ in both]
    b = [y for _, _, y in both]
    diff = sheet
    by_difficulty: dict[str, list[bool]] = {}
    for cid, x, y in both:
        by_difficulty.setdefault(diff[cid]["difficulty"], []).append(x == y)
    kappa = cohen_kappa(a, b)
    return {
        "labelled_by_both": len(both),
        "agreement": round(sum(x == y for x, y in zip(a, b)) / len(both), 3),
        "cohen_kappa": round(kappa, 3) if kappa is not None else None,
        "agreement_by_difficulty": {k: round(sum(v) / len(v), 3) for k, v in by_difficulty.items()},
        "disagreements": [{"case_id": cid, "b1": x, "b2": y} for cid, x, y in both if x != y],
    }
