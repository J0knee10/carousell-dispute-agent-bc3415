"""Generate synthetic disputes on top of real Mercari listings.

Each case gets a scenario (e.g. "missing accessory") with an intended outcome.
Code fixes the order facts (payment, dates) so eligibility is exact; the
generator model writes the people's words (complaint, seller reply, chat). The
intended outcome becomes the case's provisional label until people label it.

Runs resume: cases already in generated_cases.jsonl are skipped.
"""

from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from ..config import load_config, path
from ..llm import LLMClient, LLMError, RateLimitError
from ..schemas import CaseMeta, Dispute, DisputeCase, GeneratedDispute, Listing, Order
from .cases import load_generated_cases, load_seed_cases
from .mercari import load_sample

ACCESSORY = re.compile(r"comes with|come with|includ|\bpieces\b|\bpcs\b|with (the )?(original )?(box|charger|case|cable|strap|cord|manual|remote|stand|padding)", re.I)
VARIANT = re.compile(r"\bsize\b|colou?r|\b\d+ ?gb\b|model|version|\b(xs|xl|xxl|small|medium|large)\b|\b(black|white|blue|red|pink|green|grey|gray|navy|purple|yellow|brown|beige)\b", re.I)
COLOUR = re.compile(r"\b(black|white|blue|red|pink|green|grey|gray|navy|purple|yellow|brown|beige|teal|maroon|burgundy|coral|mint|lavender|olive|cream|tan|gold|silver)\b", re.I)
FLAW = re.compile(r"flaw|stain|scratch|pill|piling|tear|wear|worn|defect|hole|fad|mark|crack|chip|broken|dent|yellow", re.I)
NO_FLAW = re.compile(r"no (flaws|stains|scratches|holes|rips|defects|imperfections)|perfect|mint|flawless", re.I)


@dataclass(frozen=True)
class Scenario:
    name: str
    difficulty: str
    target_outcome: str
    reason: str
    instruction: str
    needs_quote: bool = False
    fits: Callable[[Listing], bool] = lambda listing: True
    order_kind: str = "normal"
    target_eligible: bool = True


SCENARIOS: list[Scenario] = [
    # ---- clear
    Scenario("missing_accessory", "clear", "partial_refund", "incomplete",
             "The listing says the item comes with something extra (an accessory, part or bundled piece). That extra is missing from the parcel. The main item is fine. The buyer has a photo of what arrived. The seller is unsure or says they packed it.",
             needs_quote=True, fits=lambda l: bool(ACCESSORY.search(l.description))),
    Scenario("wrong_variation", "clear", "full_refund_with_return", "snad",
             "The buyer received a different size, colour, model or version from the one the listing states. The buyer has a clear photo (tag, label, settings screen). The seller admits a mix-up or did not check.",
             needs_quote=True, fits=lambda l: bool(VARIANT.search(l.title + " " + l.description))),
    Scenario("undisclosed_functional_defect", "clear", "full_refund_with_return", "snad",
             "The item has a defect that stops it working or being used properly (broken zip, dead battery, won't power on, torn seam that makes it unwearable), which the listing did not mention. The buyer has a photo or video. The seller says it was fine when sent."),
    Scenario("condition_misrepresented", "clear", "full_refund_with_return", "snad",
             "The listing states a near-new condition, but the item is clearly well used with obvious damage the listing never mentions (large stains, broken parts, heavy wear). The buyer has photos.",
             fits=lambda l: l.condition_grade <= 2),
    Scenario("change_of_mind", "clear", "decline", "snad",
             "The item matches the listing exactly. The buyer simply no longer wants it (doesn't suit them, found it cheaper, not as nice as hoped) but words it as a complaint. The seller points out it is as described."),
    Scenario("not_in_listing", "clear", "decline", "incomplete",
             "The buyer complains about something the listing never promised (an accessory, feature, original box, a size they assumed). The listing is clear and silent on it. The seller points to the listing.",
             needs_quote=False),
    Scenario("post_delivery_damage", "clear", "decline", "snad",
             "The item arrived as described, but was damaged after delivery by the buyer (dropped, washed wrongly, pet chewed it). The buyer's own chat messages reveal this, while the complaint blames the seller."),
    # ---- borderline
    Scenario("minor_shade", "borderline", "decline", "snad",
             "The colour in person is a slightly different shade from what the buyer expected from the listing (e.g. lighter, warmer, more teal), but it is the same colour as stated. The seller says it's lighting.",
             needs_quote=True, fits=lambda l: bool(COLOUR.search(l.title + " " + l.description))),
    Scenario("subjective_condition", "borderline", "decline", "snad",
             "The buyer feels the item is more worn than the stated condition suggests ('listed lightly used but feels like 6/10'), but describes only ordinary wear for that condition, with no specific undisclosed defect.",
             fits=lambda l: l.condition_grade >= 2),
    Scenario("wear_disclosed", "borderline", "decline", "snad",
             "The buyer complains about a flaw that the listing itself disclosed. Quote the disclosure as grounding_quote. The buyer feels it is worse than expected.",
             needs_quote=True, fits=lambda l: bool(FLAW.search(l.description))),
    Scenario("cosmetic_undisclosed_minor", "borderline", "partial_refund", "snad",
             "The listing explicitly says the item has no flaws (or is new/like new). The buyer finds one small cosmetic flaw (a small stain, a scratch, a loose thread) that does not affect use. The buyer has a photo. Otherwise the item is fine.",
             fits=lambda l: l.condition_grade <= 2 or bool(NO_FLAW.search(l.description))),
    Scenario("conflicting_accounts", "borderline", "decline", "incomplete",
             "The buyer says a part promised in the listing was missing, but has no photo. The seller has a photo of the open parcel before sealing that shows the part.",
             needs_quote=True, fits=lambda l: bool(ACCESSORY.search(l.description))),
    # ---- ineligible: a genuine-sounding complaint, but order facts make it not covered
    Scenario("off_platform_payment", "ineligible", "decline", "snad",
             "The item is significantly not as described (wrong variation or an undisclosed defect). In the chat the buyer mentions paying by bank transfer or PayNow directly to the seller's number instead of using the Buy button.",
             order_kind="off_platform", target_eligible=False),
    Scenario("late_dispute", "ineligible", "decline", "incomplete",
             "Something the listing promised is missing. The buyer only opened the parcel several days after it was delivered, and the chat shows the delay.",
             order_kind="late", target_eligible=False),
    Scenario("order_completed", "ineligible", "decline", "snad",
             "The item has an undisclosed defect. The buyer had already tapped 'Order received' to complete the order before noticing, and says so in the chat.",
             order_kind="completed", target_eligible=False),
    Scenario("untracked_not_received", "ineligible", "decline", "not_received",
             "The item never arrived. The seller posted it by normal untracked mail. Both are frustrated.",
             order_kind="untracked", target_eligible=False),
]
SCENARIOS_BY_NAME = {s.name: s for s in SCENARIOS}

SUPPORTED = ["PayNow", "PayNow", "DBS PayLah!", "Visa/Mastercard", "Visa/Mastercard", "Atome", "PayLater by Grab"]

GENERATOR_SYSTEM = """\
You write realistic test cases for training Carousell Singapore's support team on buyer disputes about second-hand items.
Write the way real Singapore users write on Carousell: short, casual, sometimes terse, occasionally a little Singlish (use sparingly). Buyers and sellers each believe they are right.
Stay consistent with the listing and the scenario. Do not mention Carousell's policy, Buyer Protection, refund rules or what the outcome should be. Photo descriptions describe what a photo shows, in one line each.
Keep the complaint under 70 words and the chat to 2 to 6 short messages."""


def _rng(case_id: str) -> random.Random:
    return random.Random(int(hashlib.sha256(case_id.encode()).hexdigest()[:12], 16))


def build_order(case_id: str, listing: Listing, scenario: Scenario) -> tuple[Order, datetime, dict]:
    """Order facts and dispute timing, set by code so eligibility is exact."""
    rng = _rng(case_id)
    confirmed = datetime(2026, 9, 1, 9) + timedelta(days=rng.randint(0, 49), hours=rng.randint(0, 12), minutes=rng.choice([0, 15, 30, 45]))
    kind = scenario.order_kind
    method = "meetup" if kind == "normal" and rng.random() < 0.15 else "tracked_mail"
    if kind == "untracked":
        method = "untracked_mail"
    extra: dict = {}
    order = dict(
        programme="buyer_protection",
        paid_via_buy_button=True,
        payment_method=rng.choice(SUPPORTED),
        delivery_method=method,
        order_confirmed_at=confirmed,
        amount_paid_sgd=listing.price_sgd,
    )
    if method == "tracked_mail":
        delivered = confirmed + timedelta(days=rng.randint(2, 4), hours=rng.randint(0, 8))
        order["delivered_at"] = delivered
        raised = delivered + timedelta(hours=rng.randint(2, 40))
    elif method == "meetup":
        met = confirmed + timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 8))
        order["meetup_confirmed_at"] = met
        raised = met + timedelta(days=rng.randint(0, 5), hours=rng.randint(2, 20))
        extra["meetup"] = True
    else:
        expected = confirmed + timedelta(days=rng.randint(3, 5))
        order["expected_delivery_at"] = expected
        raised = expected + timedelta(days=rng.randint(1, 4), hours=rng.randint(0, 10))

    if kind == "off_platform":
        order["paid_via_buy_button"] = False
        order["payment_method"] = rng.choice(["Bank transfer", "PayNow to seller's phone number"])
    elif kind == "late":
        raised = order["delivered_at"] + timedelta(days=rng.randint(3, 7), hours=rng.randint(0, 10))
    elif kind == "completed":
        order["completed_at"] = order["delivered_at"] + timedelta(hours=rng.randint(1, 6))
        raised = order["completed_at"] + timedelta(hours=rng.randint(4, 30))
    return Order(**order), raised, extra


def make_plan(listings: list[Listing], used: set[str], seeds: list[DisputeCase], target_total: int, mix: dict, seed: int) -> list[tuple[str, str, str]]:
    """Deterministic list of (case_id, listing_id, scenario) to generate."""
    rng = random.Random(seed)
    have = {d: sum(1 for c in seeds if c.meta.difficulty == d) for d in mix}
    need = {d: max(0, round(target_total * share) - have[d]) for d, share in mix.items()}
    pool = [listing for listing in listings if listing.listing_id not in used]
    rng.shuffle(pool)
    plan: list[tuple[str, str, str]] = []
    taken: set[str] = set()
    for diff in ("clear", "borderline", "ineligible"):
        group = [s for s in SCENARIOS if s.difficulty == diff]
        for i in range(need[diff]):
            # Rotate scenarios; if no listing fits this one, try the next scenario.
            for shift in range(len(group)):
                scen = group[(i + shift) % len(group)]
                listing = next((x for x in pool if x.listing_id not in taken and scen.fits(x)), None)
                if listing:
                    taken.add(listing.listing_id)
                    plan.append((f"G{len(plan) + 1:03d}", listing.listing_id, scen.name))
                    break
    return plan


def generator_prompt(listing: Listing, scenario: Scenario, order: Order, raised: datetime, extra: dict) -> str:
    when = {
        "tracked_mail": f"Delivered by tracked mail on {order.delivered_at:%d %b %Y}" if order.delivered_at else "",
        "untracked_mail": f"Posted by normal untracked mail, expected around {order.expected_delivery_at:%d %b %Y}" if order.expected_delivery_at else "",
        "meetup": f"Handed over at a meet-up on {order.meetup_confirmed_at:%d %b %Y}" if order.meetup_confirmed_at else "",
    }[order.delivery_method]
    quote_rule = (
        "grounding_quote: copy, word for word, the part of the listing title or description this dispute is about."
        if scenario.needs_quote
        else "grounding_quote: the listing words most relevant to the dispute, copied word for word, or an empty string."
    )
    return "\n".join(
        [
            "LISTING",
            f"Title: {listing.title}",
            f"Condition: {listing.condition}",
            f"Category: {listing.category}",
            f"Price: S${listing.price_sgd:.2f}",
            f"Description: {listing.description}",
            "",
            "ORDER",
            when,
            f"Dispute raised on {raised:%d %b %Y}",
            "",
            "SCENARIO",
            scenario.instruction,
            "",
            quote_rule,
            "Write the buyer complaint, buyer photo descriptions (0 to 3), the seller's response, seller evidence (0 to 2 items), and the chat before the dispute.",
        ]
    )


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_ok(listing: Listing, quote: str) -> bool:
    q = _norm(quote).strip("\"'.… ")
    return len(q) >= 3 and q in _norm(listing.title + " " + listing.description)


def proposed_resolution(scenario: Scenario, listing: Listing, rng: random.Random) -> tuple[str, float | None]:
    if scenario.reason == "not_received":
        return "full_refund", None
    if scenario.target_outcome == "partial_refund" or scenario.name in ("subjective_condition", "wear_disclosed", "minor_shade"):
        if rng.random() < 0.6:
            return "partial_refund", round(listing.price_sgd * rng.choice([0.15, 0.2, 0.25, 0.3, 0.4]), 2)
    return "return_and_refund", None


def generate_case(llm: LLMClient, case_id: str, listing: Listing, scenario: Scenario) -> DisputeCase:
    order, raised, extra = build_order(case_id, listing, scenario)
    prompt = generator_prompt(listing, scenario, order, raised, extra)
    hints = {"listing": listing.model_dump(), "scenario": {"name": scenario.name}}
    draft = llm.generate(task="dispute_generation", system=GENERATOR_SYSTEM, prompt=prompt, schema=GeneratedDispute, hints=hints)
    notes = ""
    if scenario.needs_quote and not quote_ok(listing, draft.grounding_quote):
        retry = prompt + f"\n\nYour grounding_quote '{draft.grounding_quote}' does not appear in the listing. Copy it exactly from the title or description."
        draft = llm.generate(task="dispute_generation", system=GENERATOR_SYSTEM, prompt=retry, schema=GeneratedDispute, hints=hints)
        if not quote_ok(listing, draft.grounding_quote):
            notes = f"grounding quote not found in listing: '{draft.grounding_quote}'"
    rng = _rng(case_id + "-resolution")
    resolution, amount = proposed_resolution(scenario, listing, rng)
    return DisputeCase(
        case_id=case_id,
        listing=listing,
        order=order,
        dispute=Dispute(
            reason=scenario.reason,  # type: ignore[arg-type]
            raised_at=raised,
            buyer_complaint=draft.buyer_complaint,
            buyer_proposed_resolution=resolution,  # type: ignore[arg-type]
            buyer_requested_refund_sgd=amount,
            buyer_photo_descriptions=draft.buyer_photo_descriptions,
            seller_response=draft.seller_response,
            seller_evidence=draft.seller_evidence,
        ),
        chat=draft.chat,
        meta=CaseMeta(
            source="generated",
            difficulty=scenario.difficulty,  # type: ignore[arg-type]
            scenario=scenario.name,
            target_outcome=scenario.target_outcome,  # type: ignore[arg-type]
            target_eligible=scenario.target_eligible,
            generator_model=llm.model,
            notes=notes or f"grounding: {draft.grounding_quote}",
        ),
    )


def generate_all(llm: LLMClient, limit: int | None = None, progress: Callable[[str], None] = print) -> int:
    """Generate every planned case not yet on disk. Returns how many were written."""
    cfg = load_config()
    seeds = load_seed_cases()
    used = {c.listing.listing_id for c in seeds}
    plan = make_plan(load_sample(), used, seeds, cfg["generation"]["target_total"], cfg["generation"]["mix"], cfg["data"]["seed"])
    done = {c.case_id for c in load_generated_cases()}
    listings = {listing.listing_id: listing for listing in load_sample()}
    out = path("data.generated_cases")
    out.parent.mkdir(parents=True, exist_ok=True)
    todo = [p for p in plan if p[0] not in done]
    if limit is not None:
        todo = todo[:limit]
    progress(f"Plan: {len(plan)} cases, {len(done)} already generated, {len(todo)} to do now")
    # Spare listings for when the generator cannot ground a scenario in the planned one.
    taken = used | {lid for _, lid, _ in plan} | {c.listing.listing_id for c in load_generated_cases()}
    spares = [x for x in load_sample() if x.listing_id not in taken]
    random.Random(cfg["data"]["seed"] + 1).shuffle(spares)
    written = failed = 0
    for case_id, listing_id, scen_name in todo:
        scenario = SCENARIOS_BY_NAME[scen_name]
        try:
            case = generate_case(llm, case_id, listings[listing_id], scenario)
            if scenario.needs_quote and case.meta.notes.startswith("grounding quote not found"):
                spare = next((x for x in spares if scenario.fits(x)), None)
                if spare:
                    spares.remove(spare)
                    progress(f"{case_id}: could not ground '{scen_name}' in {listing_id}; trying {spare.listing_id}")
                    retry = generate_case(llm, case_id, spare, scenario)
                    if not retry.meta.notes.startswith("grounding quote not found"):
                        case = retry
        except RateLimitError:
            raise
        except LLMError as e:
            failed += 1
            progress(f"{case_id} {scen_name}: FAILED ({str(e)[:120]}); will retry on the next run")
            continue
        with open(out, "a", encoding="utf-8") as f:
            f.write(case.model_dump_json() + "\n")
        written += 1
        flag = " (check grounding)" if case.meta.notes.startswith("grounding quote not found") else ""
        progress(f"{case_id} {scen_name} on {listing_id}: written{flag}")
    if failed:
        progress(f"{failed} case(s) failed and were skipped; run generate again to retry them")
    return written
