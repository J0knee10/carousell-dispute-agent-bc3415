"""Prompts for each LLM step, plus the case and clause formatting they share."""

from __future__ import annotations

from ..schemas import DisputeCase, RetrievedClause

# The team's rubric for choosing an outcome. Carousell's policy says what is
# covered; it does not say when to pick a partial refund over a return, so this
# part is our own assumption. docs/labelling_guide.md gives labellers the same text.
SIGNIFICANCE_GUIDE = """\
Deciding whether a gap is significant (from Carousell's policy):
- Significant (covered): a different variation (size, colour, model, version, storage); missing parts or accessories that the listing said were included; damage or defects the listing did not disclose, especially ones affecting function; condition clearly worse than the condition stated; a specific undisclosed flaw (a stain, scratch, mark or tear) on an item listed as brand new, like new or flawless, even if it works fine, because it contradicts what the listing claimed; an item that deviates extensively from the listing.
- Not significant (not covered): wear that matches a correctly stated used condition or flaws the listing disclosed; subjective or minor variations (a slightly different shade, approximate sizes, "8/10 vs 6/10" style condition opinions that describe only ordinary wear and no specific flaw); the buyer changing their mind or ordering the wrong thing; claims about things the listing never promised; damage after delivery; surface wear that does not affect function on an item whose stated used condition allows for it."""

OUTCOME_RUBRIC = """\
Choosing the outcome (team rubric):
- full_refund_with_return: a significant gap that makes the item substantially not what was bought (wrong variation, defect affecting function, major undisclosed damage). The buyer returns it.
- partial_refund: a significant gap, but the item is still usable and mostly as described (a missing minor accessory; a small specific flaw on an item listed as brand new, like new or flawless). Suggest a percentage of the item price.
- full_refund_without_return: a significant gap where a return makes no sense, e.g. the item is worthless or unsafe to send back. Rare.
- decline: no significant gap.

Confidence: lower it when the buyer and seller give conflicting accounts and neither has clear evidence, when significance is a judgement call, or when key evidence (photos, serial numbers, packing proof) is missing. Ask for that evidence in follow-up questions."""

DECISION_GUIDE = f"{SIGNIFICANCE_GUIDE}\n\n{OUTCOME_RUBRIC}"


def render_case(case: DisputeCase) -> str:
    li, o, d = case.listing, case.order, case.dispute
    lines = [
        "LISTING",
        f"Title: {li.title}",
        f"Condition: {li.condition}",
        f"Category: {li.category}" + (f" | Brand: {li.brand}" if li.brand else ""),
        f"Price: S${li.price_sgd:.2f}",
        f"Description: {li.description}",
        "",
        "ORDER",
        f"Paid with: {o.payment_method}" + (" via the 'Buy' button" if o.paid_via_buy_button else " (outside the 'Buy' button)"),
        f"Delivery: {o.delivery_method.replace('_', ' ')}",
        f"Amount paid: S${o.amount_paid_sgd:.2f}",
        "",
        "DISPUTE",
        f"Reason selected by buyer: {d.reason}",
        f"Buyer complaint: {d.buyer_complaint}",
        f"Buyer proposes: {d.buyer_proposed_resolution.replace('_', ' ')}"
        + (f" (S${d.buyer_requested_refund_sgd:.2f})" if d.buyer_requested_refund_sgd else ""),
    ]
    if d.buyer_photo_descriptions:
        lines.append("Buyer photos: " + " | ".join(d.buyer_photo_descriptions))
    lines.append(f"Seller response: {d.seller_response or '(none)'}")
    if d.seller_counter_proposal:
        lines.append(f"Seller counter-proposal: {d.seller_counter_proposal}")
    if d.seller_evidence:
        lines.append("Seller evidence: " + " | ".join(d.seller_evidence))
    if case.chat:
        lines += ["", "CHAT"] + [f"{t.sender}: {t.text}" for t in case.chat]
    return "\n".join(lines)


def render_clauses(clauses: list[RetrievedClause]) -> str:
    return "\n\n".join(f"[{c.clause_id}] {c.doc_title} > {c.section}\n{c.text}" for c in clauses)


CLAIMS_SYSTEM = """\
You are a case analyst on Carousell Singapore's support team. You prepare 'not as described' disputes on second-hand items so a colleague can judge them.

Read the listing, the dispute and the chat. Then:
1. List what the seller promised: concrete statements in the title, description, stated condition or chat (accessories included, size, colour, model, 'no stains', 'works perfectly', disclosed flaws). Quote or closely paraphrase.
2. List each problem the buyer reports, with any evidence offered.
3. Match each problem to the promise it concerns as a gap. If the listing promised nothing about it, leave promised_claim_id empty and use gap_type not_in_listing. If the listing disclosed the flaw or the item was listed as used and the complaint is ordinary wear, use wear_consistent_with_listing.
4. For each gap, write a short retrieval_query in plain policy language (e.g. "missing parts incomplete item", "non-significant colour variation", "signs of wear item listed as used").

Do not decide the outcome. Be factual and brief."""


def claims_prompt(case: DisputeCase) -> str:
    return f"{render_case(case)}\n\nExtract the promises, the reported problems and the gaps."


JUDGE_SYSTEM = f"""\
You assist Carousell Singapore's support team in deciding 'significantly not as described' and incomplete-item disputes under the Buyer Protection and Certified Refund Policy. A staff member makes the final decision; you recommend.

Rules:
- Base every judgement only on the policy clauses provided. Cite clause IDs exactly as given (e.g. "BPR-02"). Never invent clause IDs.
- Eligibility (payment method, dispute window) has already been checked and passed. Judge only the substance.
- Assess each gap, then recommend one outcome.

{DECISION_GUIDE}"""

# Ablation (--guide rubric): the judge gets only the team's outcome rubric, so what is
# and is not covered has to come from the policy clauses it is given.
JUDGE_SYSTEM_RUBRIC_ONLY = f"""\
You assist Carousell Singapore's support team in deciding 'significantly not as described' and incomplete-item disputes under the Buyer Protection and Certified Refund Policy. A staff member makes the final decision; you recommend.

Rules:
- Base every judgement only on the policy clauses provided: they say what counts as significantly not as described and what is not covered. Cite clause IDs exactly as given (e.g. "BPR-02"). Never invent clause IDs.
- Eligibility (payment method, dispute window) has already been checked and passed. Judge only the substance.
- Assess each gap as significant (covered), not significant (not covered) or unclear, then recommend one outcome.

{OUTCOME_RUBRIC}"""


SEARCH_TOOL_AVAILABLE = """\
TOOL: search_policy (available)
The clauses above were found by searching for each gap. If deciding a gap needs a policy rule that none of them covers, write up to {n} short search queries in search_policy (e.g. "seller sends the missing part", "damage during delivery"). The tool searches the full policy, the clauses it finds are added, and you will be asked again. If the clauses above are enough, which is the usual case, leave search_policy empty and decide now."""

SEARCH_TOOL_USED = """\
TOOL: search_policy (already used; not available again)
Clauses found by your searches are included above. Leave search_policy empty and decide with the clauses you have."""


def judge_prompt(
    case: DisputeCase,
    claims_json: str,
    clauses: list[RetrievedClause],
    proposed_rule: str | None = None,
    tool: str = "none",
    max_searches: int = 2,
) -> str:
    """tool: 'available' (the judge may call search_policy), 'used' (it already did) or 'none'."""
    parts = [
        render_case(case),
        "",
        "GAPS FOUND BY THE CASE ANALYST",
        claims_json,
        "",
        "POLICY CLAUSES",
        render_clauses(clauses),
    ]
    if proposed_rule:
        parts += [
            "",
            "PROPOSED POLICY CHANGE [PROPOSED-1]",
            "Carousell is testing this change. Treat it as in force; where it conflicts with the clauses above, it wins. Cite it as PROPOSED-1 when it applies.",
            proposed_rule,
        ]
    if tool == "available":
        parts += ["", SEARCH_TOOL_AVAILABLE.format(n=max_searches)]
    elif tool == "used":
        parts += ["", SEARCH_TOOL_USED]
    else:
        parts += ["", "No tools are available: leave search_policy empty."]
    parts += ["", "Assess each gap and recommend an outcome."]
    return "\n".join(parts)


PLAN_SYSTEM = """\
You prepare the policy research for a colleague on Carousell Singapore's support team who will judge a 'not as described' dispute. You do not judge the dispute.

You have one tool, search_policy, which searches Carousell's full Buyer Protection policy. The clauses you are given come only from a general search on the dispute reason.
1. For each gap, list the IDs of the clauses given that say how that kind of problem is treated (covered or not covered). Leave the list empty if none do.
2. For each gap with no such clause, write one short search query in search_policy, in plain policy language (e.g. "missing parts incomplete item", "non-significant colour variation", "damage after delivery", "buyer changed their mind"). Write at most {n} queries.
3. If every gap is covered, leave search_policy empty."""


def plan_prompt(claims_json: str, clauses: list[RetrievedClause]) -> str:
    return "\n".join(["GAPS FOUND BY THE CASE ANALYST", claims_json, "", "POLICY CLAUSES", render_clauses(clauses), "",
                      "List the clauses that cover each gap, and the searches needed for the rest."])


BASELINE_SYSTEM = f"""\
You assist Carousell Singapore's support team in deciding buyer disputes. Below is Carousell's full Buyer Protection policy, split into clauses with IDs. Decide whether the dispute is covered at all (eligible) and what the outcome should be. Cite clause IDs exactly as given.

{DECISION_GUIDE}

If the dispute is not eligible, the outcome is decline."""


def baseline_prompt(case: DisputeCase, all_clauses: list[RetrievedClause]) -> str:
    o, d = case.order, case.dispute
    timing = [
        f"Order confirmed: {o.order_confirmed_at:%Y-%m-%d %H:%M}",
        f"Delivered (tracked): {o.delivered_at:%Y-%m-%d %H:%M}" if o.delivered_at else "",
        f"Expected delivery (untracked): {o.expected_delivery_at:%Y-%m-%d %H:%M}" if o.expected_delivery_at else "",
        f"Meet-up confirmed: {o.meetup_confirmed_at:%Y-%m-%d %H:%M}" if o.meetup_confirmed_at else "",
        f"Order marked completed: {o.completed_at:%Y-%m-%d %H:%M}" if o.completed_at else "",
        f"Dispute raised: {d.raised_at:%Y-%m-%d %H:%M}",
        f"Programme: {o.programme.replace('_', ' ')}",
        f"Seller responded within 24 hours: {'yes' if d.seller_responded else 'no'}",
        f"Previously disputed: {'yes' if d.previously_disputed else 'no'}",
    ]
    return "\n".join(
        ["POLICY", render_clauses(all_clauses), "", "CASE", render_case(case), "", "TIMELINE", *[t for t in timing if t], "", "Decide eligibility and the outcome."]
    )


MESSAGES_SYSTEM = """\
You write messages from Carousell Singapore's support team to a buyer and a seller after a dispute decision. Be polite, plain and brief (under 120 words each). State the outcome, the main reason in one or two sentences, and the next steps from the policy excerpts provided. Do not promise anything the excerpts do not say. Do not use the parties' names."""


def messages_prompt(case: DisputeCase, outcome: str, reasons: list[str], refund_note: str, next_steps: list[RetrievedClause]) -> str:
    return "\n".join(
        [
            render_case(case),
            "",
            f"FINAL DECISION: {outcome.replace('_', ' ')}{refund_note}",
            "Reasons: " + " ".join(reasons),
            "",
            "POLICY EXCERPTS ON NEXT STEPS",
            render_clauses(next_steps),
        ]
    )
