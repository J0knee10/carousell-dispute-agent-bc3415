"""Eligibility rules from Carousell SG's Buyer Protection policy, written as plain code.

These are fixed rules (payment method, dispute window, dispute reason), so they
are checked without the LLM. Each check cites the clause it comes from.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..rag.chunker import find_clause_id
from ..schemas import DisputeCase, EligibilityCheck, EligibilityResult

SUPPORTED_PAYMENT_METHODS = {"PayNow", "DBS PayLah!", "Visa/Mastercard", "Atome", "PayLater by Grab"}

# Days after the anchor date (delivery, expected delivery or meet-up) before the
# order autocompletes and the dispute window closes.
AUTOCOMPLETE_DAYS = {
    ("buyer_protection", "tracked_mail"): 2,
    ("buyer_protection", "untracked_mail"): 6,
    ("buyer_protection", "meetup"): 13,
    ("certified", "tracked_mail"): 7,
    ("certified", "untracked_mail"): 11,
    ("certified", "meetup"): 13,
}


def _cite(doc: str, phrase: str) -> list[str]:
    cid = find_clause_id(doc, phrase)
    return [cid] if cid else []


def window_close(case: DisputeCase) -> tuple[datetime | None, str]:
    """When the dispute window closes, and a description of why."""
    o = case.order
    anchor = {
        "tracked_mail": o.delivered_at,
        "untracked_mail": o.expected_delivery_at,
        "meetup": o.meetup_confirmed_at,
    }[o.delivery_method]
    days = AUTOCOMPLETE_DAYS[(o.programme, o.delivery_method)]
    auto = anchor + timedelta(days=days) if anchor else None
    label = {"tracked_mail": "delivery", "untracked_mail": "expected delivery", "meetup": "confirmed meet-up"}[o.delivery_method]
    if o.completed_at and (auto is None or o.completed_at < auto):
        return o.completed_at, f"buyer marked the order completed on {o.completed_at:%d %b %Y %H:%M}"
    if auto:
        return auto, f"autocompletes {days} days after {label} ({anchor:%d %b %Y %H:%M})"
    return None, f"no {label} date yet, so the window is still open"


def check_eligibility(case: DisputeCase) -> EligibilityResult:
    o, d = case.order, case.dispute
    checks: list[EligibilityCheck] = []

    paid_ok = o.paid_via_buy_button and o.payment_method in SUPPORTED_PAYMENT_METHODS
    checks.append(
        EligibilityCheck(
            name="Paid with the 'Buy' button",
            passed=paid_ok,
            detail=(
                f"Paid via 'Buy' button with {o.payment_method}"
                if paid_ok
                else f"Paid by {o.payment_method}"
                + ("" if o.paid_via_buy_button else " outside the 'Buy' button")
                + "; Buyer Protection only covers 'Buy' button orders with supported payment methods"
            ),
            clause_ids=_cite("what_is_buyer_protection", "paid through the 'Buy' button")
            + _cite("what_is_buyer_protection", "PayNow, DBS PayLah"),
        )
    )

    close, why = window_close(case)
    in_window = d.raised_at >= o.order_confirmed_at and (close is None or d.raised_at <= close)
    checks.append(
        EligibilityCheck(
            name="Raised within the dispute window",
            passed=in_window,
            detail=(
                f"Raised {d.raised_at:%d %b %Y %H:%M}; window "
                + (f"closed {close:%d %b %Y %H:%M} ({why})" if close else f"open ({why})")
            ),
            clause_ids=_cite("buyer_protection_refund_policy", "whichever occurs first"),
        )
    )

    checks.append(
        EligibilityCheck(
            name="First dispute on this order",
            passed=not d.previously_disputed,
            detail="A dispute can only be raised once per order" if d.previously_disputed else "No earlier dispute",
            clause_ids=_cite("dispute_process_overview", "raised once"),
        )
    )

    checks.append(
        EligibilityCheck(
            name="No refund through another channel",
            passed=not d.refund_received_elsewhere,
            detail=(
                "Buyer already received a refund outside Carousell's process"
                if d.refund_received_elsewhere
                else "No refund outside Carousell reported"
            ),
            clause_ids=_cite("buyer_protection_refund_policy", "separate resolution process"),
        )
    )

    if d.reason == "not_received":
        tracked = o.delivery_method == "tracked_mail"
        checks.append(
            EligibilityCheck(
                name="Non-delivery covered",
                passed=tracked,
                detail="Tracked mail: non-delivery is covered" if tracked else "Untracked mail: non-delivery is not covered",
                clause_ids=_cite("what_is_buyer_protection", "Item Not Received: Covered only"),
            )
        )

    failed = [c for c in checks if not c.passed]
    if failed:
        return EligibilityResult(
            status="not_covered", checks=checks, note="Not covered. " + " ".join(c.detail.rstrip(".") + "." for c in failed)
        )

    if d.reason == "not_received":
        return EligibilityResult(
            status="out_of_scope",
            checks=checks,
            note="Tracked non-delivery: check the courier record. This agent only judges 'not as described' and incomplete items.",
        )

    if not d.seller_responded:
        checks.append(
            EligibilityCheck(
                name="Seller responded within 24 hours",
                passed=False,
                detail="Seller did not respond within 24 hours, so the buyer's proposed resolution is deemed accepted",
                clause_ids=_cite("dispute_process_overview", "fail to respond within the 24-hour"),
            )
        )
        return EligibilityResult(
            status="procedural", checks=checks, note="Seller missed the 24-hour deadline: buyer's proposal applies"
        )

    return EligibilityResult(status="eligible", checks=checks, note="Covered by Buyer Protection; judge the claim")
