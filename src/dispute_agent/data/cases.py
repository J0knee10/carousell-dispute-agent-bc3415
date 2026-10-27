"""Load dispute cases (hand-written seeds plus generated ones) and the test/dev split."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

import yaml

from ..config import load_config, path
from ..schemas import DisputeCase
from .mercari import listings_by_id


def load_seed_cases(seed_file: Path | None = None) -> list[DisputeCase]:
    seed_file = seed_file or path("data.seed_cases")
    with open(seed_file, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []
    listings = listings_by_id()
    cases = []
    for item in raw:
        listing = listings[item["listing_id"]]
        order = dict(item["order"])
        order.setdefault("amount_paid_sgd", listing.price_sgd)
        meta = dict(item.get("meta", {}))
        meta.setdefault("source", "seed")
        cases.append(
            DisputeCase(
                case_id=item["case_id"],
                listing=listing,
                order=order,
                dispute=item["dispute"],
                chat=item.get("chat", []),
                meta=meta,
            )
        )
    return cases


def load_generated_cases(file: Path | None = None) -> list[DisputeCase]:
    file = file or path("data.generated_cases")
    if not file.exists():
        return []
    with open(file, encoding="utf-8") as f:
        return [DisputeCase.model_validate_json(line) for line in f if line.strip()]


def load_all_cases() -> list[DisputeCase]:
    return load_seed_cases() + load_generated_cases()


def cases_by_id() -> dict[str, DisputeCase]:
    return {c.case_id: c for c in load_all_cases()}


def make_splits(cases: list[DisputeCase], test_size: int | None = None, seed: int | None = None) -> dict[str, list[str]]:
    """Stratified hold-out split. Demo cases always stay in dev, since we look at them while tuning."""
    cfg = load_config()
    test_size = test_size if test_size is not None else cfg["data"]["test_size"]
    seed = seed if seed is not None else cfg["data"]["seed"]
    rng = random.Random(seed)
    pool = [c for c in cases if not c.meta.demo]
    by_diff: dict[str, list[str]] = defaultdict(list)
    for c in pool:
        by_diff[c.meta.difficulty].append(c.case_id)

    test: list[str] = []
    total = len(pool)
    for diff, ids in sorted(by_diff.items()):
        ids = sorted(ids)
        rng.shuffle(ids)
        share = round(test_size * len(ids) / total) if total else 0
        test.extend(ids[:share])
    # Rounding can leave us one off; top up or trim from the largest group.
    leftovers = [cid for ids in by_diff.values() for cid in ids if cid not in test]
    rng.shuffle(leftovers)
    while len(test) < min(test_size, len(pool)) and leftovers:
        test.append(leftovers.pop())
    test = sorted(test[:test_size])
    dev = sorted(c.case_id for c in cases if c.case_id not in set(test))
    return {"test": test, "dev": dev}


def write_splits(splits: dict[str, list[str]]) -> Path:
    out = path("data.splits")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(splits, indent=2) + "\n", encoding="utf-8")
    return out


def load_splits() -> dict[str, list[str]]:
    file = path("data.splits")
    if not file.exists():
        return {"test": [], "dev": [c.case_id for c in load_all_cases()]}
    return json.loads(file.read_text(encoding="utf-8"))


def case_ids_for(split: str) -> list[str]:
    if split == "all":
        return sorted(cases_by_id())
    if split == "demo":
        return [c.case_id for c in load_all_cases() if c.meta.demo]
    if split == "seed":
        return [c.case_id for c in load_seed_cases()]
    return load_splits()[split]
