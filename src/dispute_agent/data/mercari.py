"""Sample real second-hand listings from the Mercari Price Suggestion dataset.

The raw file (train.tsv, about 1.48M listings) comes from Kaggle and is not
committed. This module extracts it, filters for usable English descriptions and
writes a stratified sample to data/listings/listings_sample.jsonl.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from ..config import load_config, path
from ..schemas import CONDITION_BY_GRADE, Listing

# Mercari main categories that also exist on Carousell, mapped to its names.
CATEGORY_MAP = {
    "Electronics": "Electronics",
    "Women": "Women's Fashion",
    "Men": "Men's Fashion",
    "Home": "Home & Living",
    "Kids": "Babies & Kids",
    "Vintage & Collectibles": "Hobbies & Toys",
    "Sports & Outdoors": "Sports Equipment",
    "Beauty": "Health & Nutrition",
    "Handmade": "Hobbies & Toys",
    "Other": "Everything Else",
}

# Target share of each Mercari condition grade in the sample.
CONDITION_SHARE = {1: 0.25, 2: 0.25, 3: 0.33, 4: 0.13, 5: 0.04}


def ensure_tsv() -> Path:
    tsv = path("data.mercari_tsv")
    if tsv.exists():
        return tsv
    archive = path("data.mercari_archive")
    if not archive.exists():
        raise FileNotFoundError(
            f"Neither {tsv} nor {archive} exists. Download train.tsv.7z from "
            "https://www.kaggle.com/competitions/mercari-price-suggestion-challenge/data "
            "and put it in data/raw/."
        )
    import py7zr

    with py7zr.SevenZipFile(archive, "r") as z:
        z.extractall(path=archive.parent)
    if not tsv.exists():
        raise FileNotFoundError(f"Extracted {archive} but {tsv} is still missing")
    return tsv


def _is_usable(desc: str) -> bool:
    if not isinstance(desc, str):
        return False
    d = desc.strip()
    if d.lower() == "no description yet" or "[rm]" in d:
        return False
    if not 120 <= len(d) <= 900:
        return False
    ascii_share = sum(c.isascii() for c in d) / len(d)
    return ascii_share > 0.97 and len(re.findall(r"[A-Za-z]+", d)) >= 20


def load_candidates(tsv: Path) -> pd.DataFrame:
    df = pd.read_csv(tsv, sep="\t", dtype={"brand_name": "string"})
    df = df[df["price"] >= 5]
    df = df[df["item_description"].map(_is_usable)]
    df = df[df["category_name"].notna()]
    df["main_category"] = df["category_name"].str.split("/").str[0]
    return df[df["main_category"].isin(CATEGORY_MAP)]


def sample_listings(n: int | None = None, seed: int | None = None) -> list[Listing]:
    cfg = load_config()
    n = n or cfg["data"]["sample_size"]
    seed = seed if seed is not None else cfg["data"]["seed"]
    rate = cfg["data"]["usd_to_sgd"]
    df = load_candidates(ensure_tsv())

    # Equal share per main category. Within a category, rows are weighted so
    # used items are not swamped: Mercari is about 45% brand new, and disputes
    # about condition matter most for used goods.
    per_cat = -(-n // df["main_category"].nunique())
    parts = []
    for _, group in df.groupby("main_category"):
        counts = group["item_condition_id"].value_counts()
        weights = group["item_condition_id"].map(lambda g: CONDITION_SHARE[g] / counts[g])
        parts.append(group.sample(min(per_cat, len(group)), weights=weights, random_state=seed))
    picked = pd.concat(parts).sample(frac=1, random_state=seed).head(n)

    listings = []
    for i, row in enumerate(picked.itertuples(index=False), start=1):
        grade = int(row.item_condition_id)
        brand = row.brand_name if isinstance(row.brand_name, str) else ""
        listings.append(
            Listing(
                listing_id=f"L{i:04d}",
                title=str(row.name).strip(),
                description=str(row.item_description).strip(),
                condition=CONDITION_BY_GRADE[grade],
                condition_grade=grade,
                category=f"{CATEGORY_MAP[row.main_category]} / {row.category_name.split('/')[-1]}",
                brand=brand,
                price_sgd=round(float(row.price) * rate, 2),
                source=f"mercari_train:{row.train_id}",
            )
        )
    return listings


def write_sample(listings: list[Listing]) -> Path:
    out = path("data.listings_sample")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for listing in listings:
            f.write(listing.model_dump_json() + "\n")
    return out


def load_sample() -> list[Listing]:
    with open(path("data.listings_sample"), encoding="utf-8") as f:
        return [Listing.model_validate_json(line) for line in f if line.strip()]


def listings_by_id() -> dict[str, Listing]:
    return {listing.listing_id: listing for listing in load_sample()}


def summary(listings: list[Listing]) -> str:
    from collections import Counter

    cats = Counter(listing.category.split(" / ")[0] for listing in listings)
    conds = Counter(listing.condition for listing in listings)
    return json.dumps({"count": len(listings), "categories": cats, "conditions": conds}, indent=2)
