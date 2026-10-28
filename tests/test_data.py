import csv

from dispute_agent.agent.eligibility import check_eligibility
from dispute_agent.config import load_config
from dispute_agent.data.cases import load_seed_cases, make_splits
from dispute_agent.data.generate import SCENARIOS, SCENARIOS_BY_NAME, generate_case, make_plan, quote_ok
from dispute_agent.data.labels import claude_agreement_report, cohen_kappa, export_sheet, read_sheet
from dispute_agent.data.mercari import load_sample


def test_sample_has_300_listings_with_text():
    listings = load_sample()
    assert len(listings) == 300
    assert all(len(x.description) >= 120 for x in listings)
    assert len({x.listing_id for x in listings}) == 300


def test_plan_follows_the_mix_and_uses_each_listing_once():
    cfg = load_config()
    seeds = load_seed_cases()
    plan = make_plan(load_sample(), {c.listing.listing_id for c in seeds}, seeds,
                     cfg["generation"]["target_total"], cfg["generation"]["mix"], cfg["data"]["seed"])
    assert len(plan) + len(seeds) == cfg["generation"]["target_total"]
    assert len({lid for _, lid, _ in plan}) == len(plan)
    by_diff = {}
    for _, _, s in plan:
        d = SCENARIOS_BY_NAME[s].difficulty
        by_diff[d] = by_diff.get(d, 0) + 1
    assert by_diff["clear"] > by_diff["borderline"] > by_diff["ineligible"]


def test_generated_order_facts_give_the_intended_eligibility(mock_llm):
    listing = load_sample()[10]
    for scenario in SCENARIOS:
        for i in range(5):
            case = generate_case(mock_llm, f"T{scenario.name}{i}", listing, scenario)
            assert check_eligibility(case).eligible == scenario.target_eligible, (scenario.name, i)


def test_quote_check():
    listing = load_sample()[0]
    assert quote_ok(listing, listing.description[:30])
    assert not quote_ok(listing, "words that are not in the listing at all")


def test_split_holds_out_test_cases_and_keeps_demos_in_dev():
    seeds = load_seed_cases()
    splits = make_splits(seeds, test_size=6, seed=1)
    assert len(splits["test"]) == 6
    assert not set(splits["test"]) & set(splits["dev"])
    demos = {c.case_id for c in seeds if c.meta.demo}
    assert demos <= set(splits["dev"])


def test_kappa():
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


def test_export_keeps_filled_columns_and_reports_claude_agreement(tmp_path):
    sheet = tmp_path / "labels.csv"
    export_sheet(sheet)
    rows = list(read_sheet(sheet).values())
    rows[0].update(claude_outcome=rows[0]["provisional_outcome"], claude_eligible="true", claude_note="checked")
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    export_sheet(sheet)
    kept = read_sheet(sheet)[rows[0]["case_id"]]
    assert (kept["claude_outcome"], kept["claude_note"]) == (rows[0]["provisional_outcome"], "checked")
    assert claude_agreement_report(read_sheet(sheet))["vs_provisional"]["agreement"] == 1.0
