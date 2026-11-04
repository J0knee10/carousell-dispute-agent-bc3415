"""Offline stand-in for the LLM, built from keyword rules.

Used by the tests and for working without an API key. Its answers have the
right shape but are not real judgements, so never report its accuracy as a
result.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from ..schemas import (
    Adjudication,
    BaselineJudgement,
    ChatTurn,
    ClaimGap,
    ClaimMatchResult,
    FollowUpQuestion,
    GapAssessment,
    GapCoverage,
    GeneratedDispute,
    MessageDrafts,
    PromisedClaim,
    ReportedIssue,
    ResearchPlan,
)
from .base import CallStats, LLMError, T

# Ordered: the first matching pattern decides the gap type.
GAP_PATTERNS: list[tuple[str, str]] = [
    ("change_of_mind", r"changed? my mind|not (really )?my style|not as fun|don'?t (need|want|like) it|useless to me"),
    ("post_delivery_damage", r"dropped it|after (it )?(was )?delivered.*(broke|damage)|my (kid|dog|son|daughter) (broke|chewed)"),
    ("not_in_listing", r"normally comes with|usually comes with|should have come with|expected it to (include|come)|need king|doesn'?t fit my"),
    ("different_variation", r"wrong (size|colou?r|model|version|item)|size \d+ not|says size|\b\d+ ?gb\b.*(not|capacity)|different (model|version)|not the same model"),
    ("missing_part", r"missing|no (sd card|charger|booklet|strap|cable|band|dongle)|wasn'?t (in|with)|were not in|not in the (box|package|bag)|there is no|didn'?t come with"),
    ("undisclosed_defect", r"won'?t (play|turn on|charge|work)|doesn'?t work|not working|switches off|keeps turning off|broken|crack|empty setting|stain|tear|hole"),
    ("minor_variation", r"shade|looks? (more|different)|lighting|teal|not what i expected from the photos"),
    ("wear_consistent_with_listing", r"pilling|piling|worn|signs of wear|creas|yellow|scratch|not \d+/10|\d+/10 at best"),
]

SIGNIFICANCE = {
    "missing_part": "significant",
    "different_variation": "significant",
    "undisclosed_defect": "significant",
    "condition_worse_than_listed": "significant",
    "deviates_from_listing": "significant",
    "minor_variation": "not_significant",
    "wear_consistent_with_listing": "not_significant",
    "not_in_listing": "not_significant",
    "change_of_mind": "not_significant",
    "post_delivery_damage": "not_significant",
    "other": "unclear",
}


def classify(text: str) -> str:
    low = text.lower()
    for gap_type, pattern in GAP_PATTERNS:
        if re.search(pattern, low):
            return gap_type
    return "other"


class MockLLM:
    def __init__(self) -> None:
        self.name = "mock"
        self.model = "mock-keyword-rules"
        self.stats = CallStats()

    def generate(
        self,
        *,
        task: str,
        system: str,
        prompt: str,
        schema: type[T],
        hints: dict[str, Any] | None = None,
        temperature: float | None = None,
    ) -> T:
        hints = hints or {}
        handler = getattr(self, f"_{task}", None)
        if handler is None:
            raise LLMError(f"MockLLM has no handler for task '{task}'")
        result: BaseModel = handler(hints)
        self.stats.record(task, 0.0)
        if not isinstance(result, schema):
            raise LLMError(f"MockLLM task '{task}' returned {type(result).__name__}, expected {schema.__name__}")
        return result  # type: ignore[return-value]

    # ------------------------------------------------------------- tasks

    def _claim_matching(self, hints: dict) -> ClaimMatchResult:
        case = hints["case"]
        complaint = case["dispute"]["buyer_complaint"]
        listing = case["listing"]
        gap_type = classify(complaint)
        if gap_type == "undisclosed_defect" and re.search(r"stain", complaint, re.I) and listing["condition_grade"] >= 3:
            gap_type = "wear_consistent_with_listing"
        promised = [
            PromisedClaim(claim_id="P1", text=listing["title"], source="title"),
            PromisedClaim(claim_id="P2", text=f"Condition: {listing['condition']}", source="condition"),
        ]
        reported = [ReportedIssue(issue_id="R1", text=complaint[:200], evidence="; ".join(case["dispute"]["buyer_photo_descriptions"]))]
        gaps = [
            ClaimGap(
                gap_id="G1",
                issue_id="R1",
                promised_claim_id="P1",
                gap_type=gap_type,  # type: ignore[arg-type]
                description=f"Buyer reports: {complaint[:120]}",
                retrieval_query=gap_type.replace("_", " ") + " " + complaint[:60],
            )
        ]
        return ClaimMatchResult(promised=promised, reported=reported, gaps=gaps, summary=f"[MOCK] {complaint[:150]}")

    def _adjudication(self, hints: dict) -> Adjudication:
        gaps = hints.get("gaps", [])
        clause_ids = [c["clause_id"] for c in hints.get("clauses", [])]
        cite = clause_ids[:1]
        assessments = []
        for g in gaps:
            assessments.append(
                GapAssessment(gap_id=g["gap_id"], significance=SIGNIFICANCE[g["gap_type"]], reasoning="[MOCK] keyword rule", clause_ids=cite)  # type: ignore[arg-type]
            )
        types = {g["gap_type"] for g in gaps}
        if types & {"different_variation", "undisclosed_defect", "condition_worse_than_listed", "deviates_from_listing"}:
            outcome, pct, conf = "full_refund_with_return", 0, 0.85
        elif "missing_part" in types:
            outcome, pct, conf = "partial_refund", 20, 0.8
        elif types and types <= {"other"}:
            outcome, pct, conf = "decline", 0, 0.4
        else:
            outcome, pct, conf = "decline", 0, 0.75
        # Unclear gaps make the mock call the search_policy tool once, so tests cover the loop.
        searches = [f"policy on {g['description'][:60]}" for g in gaps if g["gap_type"] == "other"]
        if hints.get("tool") != "available":
            searches = []
        proposed = hints.get("proposed_rule")
        if proposed and outcome == "decline" and "wear" in proposed.lower() and "wear_consistent_with_listing" in types:
            outcome, pct, conf = "partial_refund", 15, 0.6
        return Adjudication(
            gap_assessments=assessments,
            outcome=outcome,  # type: ignore[arg-type]
            partial_refund_percent=pct,
            confidence=conf,
            reasons=[f"[MOCK] Gap types: {', '.join(sorted(types)) or 'none'}"],
            citations=cite,
            search_policy=searches[:2],
            needs_more_evidence=conf < 0.5,
            follow_up_questions=[FollowUpQuestion(to="buyer", question="[MOCK] Please send a clear photo of the issue.")] if conf < 0.5 else [],
            summary_for_staff=f"[MOCK] Recommend {outcome.replace('_', ' ')}.",
        )

    def _research_plan(self, hints: dict) -> ResearchPlan:
        """Searches for every gap, so tests cover the plan -> search -> judge path."""
        gaps = hints.get("gaps", [])
        return ResearchPlan(
            coverage=[GapCoverage(gap_id=g["gap_id"], clause_ids=[]) for g in gaps],
            search_policy=[g["retrieval_query"] for g in gaps],
        )

    def _whatif_adjudication(self, hints: dict) -> Adjudication:
        return self._adjudication(hints)

    def _baseline(self, hints: dict) -> BaselineJudgement:
        case = hints["case"]
        claim = self._claim_matching(hints)
        adj = self._adjudication({"gaps": [g.model_dump() for g in claim.gaps], "clauses": []})
        eligible = case["order"]["paid_via_buy_button"]
        return BaselineJudgement(
            eligible=eligible,
            outcome=adj.outcome if eligible else "decline",
            confidence=adj.confidence,
            reasons=adj.reasons,
            citations=[],
        )

    def _message_drafts(self, hints: dict) -> MessageDrafts:
        outcome = hints.get("outcome", "decline").replace("_", " ")
        return MessageDrafts(
            buyer_message=f"[MOCK] Hi, we have reviewed your dispute. Outcome: {outcome}.",
            seller_message=f"[MOCK] Hi, we have reviewed the dispute on your order. Outcome: {outcome}.",
        )

    def _dispute_generation(self, hints: dict) -> GeneratedDispute:
        listing = hints["listing"]
        scenario = hints["scenario"]
        quote = listing["title"]
        complaint = {
            "missing_accessory": f"The listing for '{quote}' mentions extras that are missing from the package.",
            "wrong_variation": f"I received the wrong size, not the one in the listing for '{quote}'.",
            "undisclosed_functional_defect": "It doesn't work properly and this wasn't mentioned in the listing.",
            "change_of_mind": "It's fine, but I changed my mind and don't need it anymore.",
        }.get(scenario["name"], f"The item isn't what I expected from '{quote}'.")
        return GeneratedDispute(
            grounding_quote=quote,
            buyer_complaint=complaint,
            buyer_photo_descriptions=["[MOCK] Photo of the item as received"],
            seller_response="[MOCK] It was as described when I sent it.",
            seller_evidence=[],
            chat=[ChatTurn(sender="buyer", text="[MOCK] Hi, there's a problem with the item"), ChatTurn(sender="seller", text="[MOCK] What's wrong?")],
        )
