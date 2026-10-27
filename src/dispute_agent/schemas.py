"""Data models for dispute cases and for the structured output the LLM returns.

LLM output models deliberately have no default values: the Gemini structured
output schema does not accept them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Outcome = Literal[
    "full_refund_with_return",
    "full_refund_without_return",
    "partial_refund",
    "decline",
]
OUTCOMES: tuple[str, ...] = Outcome.__args__  # type: ignore[attr-defined]

OUTCOME_LABELS = {
    "full_refund_with_return": "Full refund with return",
    "full_refund_without_return": "Full refund without return",
    "partial_refund": "Partial refund",
    "decline": "Decline",
}

Difficulty = Literal["clear", "borderline", "ineligible"]
DisputeReason = Literal["snad", "incomplete", "not_received"]
DeliveryMethod = Literal["tracked_mail", "untracked_mail", "meetup"]
Programme = Literal["buyer_protection", "certified"]

# Carousell's own condition names, matched to Mercari's 1 (new) to 5 (poor) grade.
CONDITION_BY_GRADE = {
    1: "Brand new",
    2: "Like new",
    3: "Lightly used",
    4: "Well used",
    5: "Heavily used",
}


# ---------------------------------------------------------------- case data

class Listing(BaseModel):
    listing_id: str
    title: str
    description: str
    condition: str
    condition_grade: int
    category: str
    brand: str = ""
    price_sgd: float
    source: str = ""


class Order(BaseModel):
    programme: Programme = "buyer_protection"
    paid_via_buy_button: bool = True
    payment_method: str = "PayNow"
    delivery_method: DeliveryMethod = "tracked_mail"
    order_confirmed_at: datetime
    delivered_at: datetime | None = None
    expected_delivery_at: datetime | None = None
    meetup_confirmed_at: datetime | None = None
    completed_at: datetime | None = None
    amount_paid_sgd: float


class Dispute(BaseModel):
    reason: DisputeReason = "snad"
    raised_at: datetime
    buyer_complaint: str
    buyer_proposed_resolution: Literal["return_and_refund", "partial_refund", "full_refund"] = "return_and_refund"
    buyer_requested_refund_sgd: float | None = None
    buyer_photo_descriptions: list[str] = Field(default_factory=list)
    seller_responded: bool = True
    seller_response: str = ""
    seller_counter_proposal: str = ""
    seller_evidence: list[str] = Field(default_factory=list)
    previously_disputed: bool = False
    refund_received_elsewhere: bool = False


class ChatTurn(BaseModel):
    sender: Literal["buyer", "seller"]
    text: str


class CaseMeta(BaseModel):
    source: Literal["seed", "generated"] = "seed"
    difficulty: Difficulty = "clear"
    scenario: str = ""
    target_outcome: Outcome | None = None
    target_eligible: bool = True
    demo: bool = False
    generator_model: str = ""
    notes: str = ""


class DisputeCase(BaseModel):
    case_id: str
    listing: Listing
    order: Order
    dispute: Dispute
    chat: list[ChatTurn] = Field(default_factory=list)
    meta: CaseMeta = Field(default_factory=CaseMeta)


# ------------------------------------------------------- LLM output: claims

GapType = Literal[
    "missing_part",
    "different_variation",
    "undisclosed_defect",
    "condition_worse_than_listed",
    "deviates_from_listing",
    "minor_variation",
    "wear_consistent_with_listing",
    "not_in_listing",
    "change_of_mind",
    "post_delivery_damage",
    "other",
]


class PromisedClaim(BaseModel):
    claim_id: str = Field(description="P1, P2, ...")
    text: str = Field(description="What the listing or chat promised, quoted or closely paraphrased")
    source: Literal["title", "description", "condition", "chat"]


class ReportedIssue(BaseModel):
    issue_id: str = Field(description="R1, R2, ...")
    text: str = Field(description="What the buyer says is wrong")
    evidence: str = Field(description="Evidence offered for it, e.g. photo descriptions; empty if none")


class ClaimGap(BaseModel):
    gap_id: str = Field(description="G1, G2, ...")
    issue_id: str
    promised_claim_id: str = Field(description="Matching promised claim ID, or empty string if the listing promised nothing about it")
    gap_type: GapType
    description: str = Field(description="One sentence: listing said X, buyer reports Y")
    retrieval_query: str = Field(description="Short search query to find the Carousell policy clause on this kind of problem")


class ClaimMatchResult(BaseModel):
    promised: list[PromisedClaim]
    reported: list[ReportedIssue]
    gaps: list[ClaimGap]
    summary: str = Field(description="Two sentences summarising the dispute for a support agent")


# ---------------------------------------------------- LLM output: judgement

class GapAssessment(BaseModel):
    gap_id: str
    significance: Literal["significant", "not_significant", "unclear"]
    reasoning: str
    clause_ids: list[str] = Field(description="IDs of the policy clauses this assessment relies on")


class FollowUpQuestion(BaseModel):
    to: Literal["buyer", "seller"]
    question: str


class Adjudication(BaseModel):
    gap_assessments: list[GapAssessment]
    outcome: Outcome
    partial_refund_percent: int = Field(description="Suggested refund as % of item price if outcome is partial_refund, else 0")
    confidence: float = Field(description="0 to 1: how sure you are the outcome is right")
    reasons: list[str] = Field(description="2 to 4 short reasons for the outcome")
    citations: list[str] = Field(description="Policy clause IDs that support the outcome")
    needs_more_evidence: bool
    follow_up_questions: list[FollowUpQuestion] = Field(description="Evidence to request if needed; empty list otherwise")
    summary_for_staff: str = Field(description="One or two sentences a support agent can read first")


class BaselineJudgement(BaseModel):
    eligible: bool = Field(description="Whether the dispute is covered by Buyer Protection at all")
    outcome: Outcome
    confidence: float
    reasons: list[str]
    citations: list[str]


class MessageDrafts(BaseModel):
    buyer_message: str
    seller_message: str


class GeneratedDispute(BaseModel):
    grounding_quote: str = Field(description="Exact words copied from the listing title or description that this dispute is about; empty string if the scenario is about something the listing never mentions")
    buyer_complaint: str
    buyer_photo_descriptions: list[str]
    seller_response: str
    seller_evidence: list[str]
    chat: list[ChatTurn]


# ------------------------------------------------- agent results (internal)

class EligibilityCheck(BaseModel):
    name: str
    passed: bool
    detail: str
    clause_ids: list[str] = Field(default_factory=list)


class EligibilityResult(BaseModel):
    status: Literal["eligible", "not_covered", "procedural", "out_of_scope"]
    checks: list[EligibilityCheck]
    note: str = ""

    @property
    def eligible(self) -> bool:
        """Covered by Buyer Protection (whether or not the agent then judges it)."""
        return self.status != "not_covered"


class RetrievedClause(BaseModel):
    clause_id: str
    doc_title: str
    section: str
    url: str
    text: str
    distance: float | None = None
    query: str = ""


class Recommendation(BaseModel):
    outcome: Outcome | None
    eligible: bool
    eligibility_status: str
    partial_refund_percent: int = 0
    confidence: float
    reasons: list[str]
    citations: list[str]
    escalate: bool
    escalation_reasons: list[str] = Field(default_factory=list)
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)
    summary_for_staff: str = ""
    decided_by: Literal["rules", "llm"] = "llm"
