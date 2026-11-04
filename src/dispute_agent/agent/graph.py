"""The dispute agent as a LangGraph workflow.

intake -> eligibility --(covered)--> claim matching -> policy retrieval -> judgement <-> search_policy tool
                      |                                                       |
                      |                                                       v
                      |                                          confidence and citation check -> staff review -> message drafts
                      \\--(not covered / procedural / out of scope)--> rule-based recommendation -> staff review

The judge can call the search_policy tool when the clauses it was given do not
cover a gap; the graph then loops back to the judge with the new clauses (at
most `agent.max_tool_rounds` times). The graph pauses at staff review (a
LangGraph interrupt) until a person approves or overrides the recommendation.
"""

from __future__ import annotations

import json
import operator
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Callable, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ..config import load_config, path
from ..llm import LLMClient
from ..rag.chunker import clauses_by_id, find_clause_id
from ..rag.store import PolicyStore
from ..schemas import (
    OUTCOMES,
    Adjudication,
    ClaimMatchResult,
    DisputeCase,
    EligibilityResult,
    MessageDrafts,
    ResearchPlan,
    Recommendation,
    RetrievedClause,
)
from . import prompts
from .eligibility import check_eligibility

REASON_QUERIES = {
    "snad": "what counts as significantly not as described and which variations are not covered",
    "incomplete": "incomplete item with missing parts: refund or seller sends the missing part",
    "not_received": "item not received tracked and untracked mail",
}

# Retrieval designs compared in reports/model_comparison.md:
#   per_gap: one search per gap found by claim matching (the default), plus the search_policy tool as a fallback
#   agentic: only a general search on the dispute reason; a planning step (LLM) decides which gaps the
#            clauses cover and calls search_policy for the rest, then the judge decides
#   none:    no policy clauses at all (ablation)
RETRIEVAL_MODES = ("per_gap", "agentic", "none")
AGENTIC_SEARCHES = 3

PROPOSAL_TO_OUTCOME = {
    "return_and_refund": "full_refund_with_return",
    "partial_refund": "partial_refund",
    "full_refund": "full_refund_without_return",
}


class AgentState(TypedDict, total=False):
    case: dict
    eligibility: dict
    claims: dict
    clauses: list[dict]
    adjudication: dict
    recommendation: dict
    decision: dict
    messages: dict
    proposed_rule: str
    judge_rounds: int
    plan: dict
    pending_searches: list[str]
    search_found: int
    tool_calls: Annotated[list[dict], operator.add]
    trace: Annotated[list[dict], operator.add]


def _step(name: str, start: float, summary: str) -> list[dict]:
    return [{"step": name, "seconds": round(time.monotonic() - start, 2), "summary": summary}]


def retrieve_for_gaps(store: PolicyStore, reason: str, claims: ClaimMatchResult, max_clauses: int) -> list[RetrievedClause]:
    queries = [REASON_QUERIES.get(reason, REASON_QUERIES["snad"])] + [g.retrieval_query for g in claims.gaps]
    seen: dict[str, RetrievedClause] = {}
    # Round-robin over queries so every gap gets its best clause before any gets its third.
    per_query = [store.retrieve(q) for q in queries]
    for rank in range(max(len(r) for r in per_query) if per_query else 0):
        for results in per_query:
            if rank < len(results) and results[rank].clause_id not in seen:
                seen[results[rank].clause_id] = results[rank]
    return list(seen.values())[:max_clauses]


def review_gate(
    adj: Adjudication,
    eligibility: EligibilityResult,
    retrieved_ids: set[str],
    threshold: float,
    wanted_more_policy: bool = False,
) -> Recommendation:
    """Code checks on the LLM's judgement: confidence, evidence, citations and consistency."""
    reasons = []
    if wanted_more_policy:
        reasons.append("The judge asked for policy the search tool could not supply")
    allowed = retrieved_ids | {"PROPOSED-1"}
    citations = [c for c in adj.citations if c in allowed]
    invented = sorted(set(adj.citations) - allowed)
    if invented:
        reasons.append(f"Cited clauses that were not retrieved: {', '.join(invented)}")
    if not citations:
        reasons.append("No valid policy citation supports the outcome")
    if adj.confidence < threshold:
        reasons.append(f"Confidence {adj.confidence:.2f} is below {threshold:.2f}")
    if adj.needs_more_evidence:
        reasons.append("More evidence needed")
    if any(g.significance == "unclear" for g in adj.gap_assessments):
        reasons.append("At least one gap is unclear")
    significant = any(g.significance == "significant" for g in adj.gap_assessments)
    if adj.outcome == "decline" and significant:
        reasons.append("Declines although a gap was judged significant")
    if adj.outcome != "decline" and adj.gap_assessments and not significant:
        reasons.append("Refunds although no gap was judged significant")
    return Recommendation(
        outcome=adj.outcome,
        eligible=eligibility.eligible,
        eligibility_status=eligibility.status,
        partial_refund_percent=adj.partial_refund_percent if adj.outcome == "partial_refund" else 0,
        confidence=adj.confidence,
        reasons=adj.reasons,
        citations=citations,
        escalate=bool(reasons),
        escalation_reasons=reasons,
        follow_up_questions=adj.follow_up_questions,
        summary_for_staff=adj.summary_for_staff,
        decided_by="llm",
    )


def rule_recommendation(case: DisputeCase, el: EligibilityResult) -> Recommendation:
    cited = sorted({cid for c in el.checks if not c.passed for cid in c.clause_ids})
    if el.status == "not_covered":
        return Recommendation(
            outcome="decline", eligible=False, eligibility_status=el.status, confidence=1.0,
            reasons=[c.detail for c in el.checks if not c.passed], citations=cited, escalate=False,
            summary_for_staff=el.note, decided_by="rules",
        )
    if el.status == "procedural":
        d = case.dispute
        outcome = PROPOSAL_TO_OUTCOME[d.buyer_proposed_resolution]
        pct = 0
        if outcome == "partial_refund" and d.buyer_requested_refund_sgd and case.order.amount_paid_sgd:
            pct = round(100 * d.buyer_requested_refund_sgd / case.order.amount_paid_sgd)
        return Recommendation(
            outcome=outcome, eligible=True, eligibility_status=el.status, partial_refund_percent=pct, confidence=0.95,
            reasons=[c.detail for c in el.checks if not c.passed], citations=cited, escalate=False,
            summary_for_staff=el.note, decided_by="rules",
        )
    return Recommendation(
        outcome=None, eligible=True, eligibility_status=el.status, confidence=0.0, reasons=[el.note], citations=cited,
        escalate=True, escalation_reasons=["Outside what the agent judges"], summary_for_staff=el.note, decided_by="rules",
    )


def log_decision(record: dict) -> None:
    log = path("outputs.decision_log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def build_graph(
    llm: LLMClient,
    store: PolicyStore,
    *,
    checkpointer: Any | None = None,
    draft_messages: bool = True,
    confidence_threshold: float | None = None,
    decision_logger: Callable[[dict], None] | None = log_decision,
    use_retrieval: bool = True,
    max_tool_rounds: int | None = None,
    retrieval: str = "per_gap",
):
    """retrieval: per_gap (default), agentic or none (see RETRIEVAL_MODES). use_retrieval=False means none."""
    cfg = load_config()
    threshold = confidence_threshold if confidence_threshold is not None else cfg["agent"]["confidence_threshold"]
    max_clauses = cfg["rag"]["max_clauses"]
    if not use_retrieval:
        retrieval = "none"
    if retrieval not in RETRIEVAL_MODES:
        raise ValueError(f"retrieval must be one of {RETRIEVAL_MODES}, got {retrieval!r}")
    use_retrieval = retrieval != "none"
    tool_rounds = cfg["agent"].get("max_tool_rounds", 1) if max_tool_rounds is None else max_tool_rounds
    max_searches = cfg["agent"].get("max_searches_per_round", 2)
    if retrieval == "agentic":
        # The planning step does the searching, so the judge itself gets no tool.
        tool_rounds, max_searches = 0, AGENTIC_SEARCHES
    if not use_retrieval:
        tool_rounds = 0

    def intake(state: AgentState) -> AgentState:
        t = time.monotonic()
        case = DisputeCase.model_validate(state["case"])
        return {"case": case.model_dump(mode="json"), "trace": _step(
            "Case intake", t, f"Case {case.case_id}: '{case.listing.title}' ({case.listing.condition}), reason: {case.dispute.reason}")}

    def eligibility(state: AgentState) -> AgentState:
        t = time.monotonic()
        el = check_eligibility(DisputeCase.model_validate(state["case"]))
        return {"eligibility": el.model_dump(), "trace": _step("Eligibility check", t, f"{el.status}: {el.note}")}

    def route(state: AgentState) -> str:
        return "claims" if state["eligibility"]["status"] == "eligible" else "rules"

    def rules(state: AgentState) -> AgentState:
        t = time.monotonic()
        rec = rule_recommendation(DisputeCase.model_validate(state["case"]), EligibilityResult.model_validate(state["eligibility"]))
        return {"recommendation": rec.model_dump(), "trace": _step(
            "Rule-based recommendation", t, f"{rec.outcome or 'refer to staff'} (decided by eligibility rules)")}

    def claims(state: AgentState) -> AgentState:
        t = time.monotonic()
        case = DisputeCase.model_validate(state["case"])
        result = llm.generate(
            task="claim_matching", system=prompts.CLAIMS_SYSTEM, prompt=prompts.claims_prompt(case),
            schema=ClaimMatchResult, hints={"case": state["case"]},
        )
        kinds = ", ".join(g.gap_type for g in result.gaps) or "none"
        return {"claims": result.model_dump(), "trace": _step("Claim matching", t, f"{len(result.gaps)} gap(s): {kinds}")}

    def retrieve(state: AgentState) -> AgentState:
        t = time.monotonic()
        if not use_retrieval:
            return {"clauses": [], "trace": _step("Policy retrieval", t, "Switched off (no-RAG ablation)")}
        if retrieval == "agentic":
            reason = state["case"]["dispute"]["reason"]
            found = store.retrieve(REASON_QUERIES.get(reason, REASON_QUERIES["snad"]))
            return {"clauses": [c.model_dump() for c in found], "trace": _step(
                "Policy retrieval", t, "General clauses only (agent-driven retrieval): " + ", ".join(c.clause_id for c in found))}
        claims_obj = ClaimMatchResult.model_validate(state["claims"])
        found = retrieve_for_gaps(store, state["case"]["dispute"]["reason"], claims_obj, max_clauses)
        return {"clauses": [c.model_dump() for c in found], "trace": _step(
            "Policy retrieval", t, "Clauses: " + ", ".join(c.clause_id for c in found))}

    def judge(state: AgentState) -> AgentState:
        t = time.monotonic()
        case = DisputeCase.model_validate(state["case"])
        clauses = [RetrievedClause.model_validate(c) for c in state["clauses"]]
        proposed = state.get("proposed_rule")
        rounds = state.get("judge_rounds", 0)
        if tool_rounds == 0:
            tool = "none"
        else:
            tool = "available" if rounds < tool_rounds else "used"
        result = llm.generate(
            task="whatif_adjudication" if proposed else "adjudication",
            system=prompts.JUDGE_SYSTEM,
            prompt=prompts.judge_prompt(
                case, json.dumps(state["claims"]["gaps"], indent=1), clauses, proposed, tool, max_searches
            ),
            schema=Adjudication,
            hints={"case": state["case"], "gaps": state["claims"]["gaps"], "clauses": state["clauses"],
                   "proposed_rule": proposed, "tool": tool},
        )
        summary = f"{result.outcome} (confidence {result.confidence:.2f})"
        pending = result.search_policy[:max_searches] if tool == "available" else []
        if pending:
            summary += "; calls search_policy: " + "; ".join(f"'{q}'" for q in pending)
        return {"adjudication": result.model_dump(), "judge_rounds": rounds + 1, "pending_searches": pending,
                "trace": _step("Policy judgement", t, summary)}

    def after_judge(state: AgentState) -> str:
        wants = bool(state.get("pending_searches"))
        return "search" if wants and state.get("judge_rounds", 0) <= tool_rounds else "gate"

    def plan(state: AgentState) -> AgentState:
        """Agent-driven retrieval: the LLM decides what the general clauses miss and what to search for."""
        t = time.monotonic()
        clauses = [RetrievedClause.model_validate(c) for c in state["clauses"]]
        result = llm.generate(
            task="research_plan", system=prompts.PLAN_SYSTEM.format(n=max_searches),
            prompt=prompts.plan_prompt(json.dumps(state["claims"]["gaps"], indent=1), clauses),
            schema=ResearchPlan, hints={"gaps": state["claims"]["gaps"], "clauses": state["clauses"]},
        )
        pending = [q for q in result.search_policy if q.strip()][:max_searches]
        covered = sum(bool(c.clause_ids) for c in result.coverage)
        summary = f"{covered} of {len(result.coverage)} gap(s) covered by the general clauses"
        summary += ("; calls search_policy: " + "; ".join(f"'{q}'" for q in pending)) if pending else "; no search needed"
        return {"plan": result.model_dump(), "pending_searches": pending, "trace": _step("Research plan", t, summary)}

    def after_plan(state: AgentState) -> str:
        return "search" if state.get("pending_searches") else "judge"

    def search(state: AgentState) -> AgentState:
        """The search_policy tool: run the judge's queries and add clauses it has not seen."""
        t = time.monotonic()
        queries = state.get("pending_searches", [])[:max_searches]
        known = {c["clause_id"] for c in state["clauses"]}
        found: list[dict] = []
        calls = []
        for q in queries:
            new = [c for c in store.retrieve(q) if c.clause_id not in known]
            known |= {c.clause_id for c in new}
            found += [c.model_dump() for c in new]
            calls.append({"tool": "search_policy", "query": q, "new_clauses": [c.clause_id for c in new]})
        summary = "; ".join(f"'{c['query']}' -> {', '.join(c['new_clauses']) or 'nothing new'}" for c in calls)
        return {
            "clauses": state["clauses"] + found,
            "search_found": len(found),
            "pending_searches": [],
            "tool_calls": calls,
            "trace": _step("Policy search tool", t, summary),
        }

    def after_search(state: AgentState) -> str:
        if retrieval == "agentic":
            return "judge"  # the plan searched before any judgement was made
        # Nothing new found: the judgement already made stands, with no second LLM call.
        return "judge" if state.get("search_found") else "gate"

    def gate(state: AgentState) -> AgentState:
        t = time.monotonic()
        adj = Adjudication.model_validate(state["adjudication"])
        # The final judgement still asks for more policy: the tool was used up,
        # or its search found nothing new.
        wanted_more = bool(adj.search_policy) and tool_rounds > 0
        rec = review_gate(
            adj,
            EligibilityResult.model_validate(state["eligibility"]),
            {c["clause_id"] for c in state["clauses"]},
            threshold,
            wanted_more_policy=wanted_more,
        )
        summary = "Escalate: " + "; ".join(rec.escalation_reasons) if rec.escalate else "Confident; standard review"
        return {"recommendation": rec.model_dump(), "trace": _step("Confidence and citation check", t, summary)}

    def staff_review(state: AgentState) -> AgentState:
        rec = state["recommendation"]
        decision = interrupt({"case_id": state["case"]["case_id"], "recommendation": rec})
        t = time.monotonic()
        action = decision.get("action", "approve")
        final = rec["outcome"] if action == "approve" else decision.get("outcome")
        if final not in OUTCOMES:
            raise ValueError(f"Staff decision needs a valid outcome, got {final!r}")
        record = {
            "case_id": state["case"]["case_id"],
            "action": action,
            "recommended": rec["outcome"],
            "final_outcome": final,
            "partial_refund_percent": (
                decision.get("partial_refund_percent", rec.get("partial_refund_percent", 0) if final == rec["outcome"] else 0)
                if final == "partial_refund" else 0
            ),
            "note": decision.get("note", ""),
            "staff": decision.get("staff", ""),
            "escalated": rec["escalate"],
            "confidence": rec["confidence"],
            "decided_at": datetime.now().isoformat(timespec="seconds"),
        }
        if decision_logger:
            decision_logger(record)
        verb = "approved" if action == "approve" else f"overrode to {final}"
        return {"decision": record, "trace": _step("Staff decision", t, f"Staff {verb}")}

    def messages(state: AgentState) -> AgentState:
        t = time.monotonic()
        case = DisputeCase.model_validate(state["case"])
        dec, rec = state["decision"], state["recommendation"]
        by_id = clauses_by_id()
        step_ids = [find_clause_id("refund_return_request", "Full refund with returns"),
                    find_clause_id("dispute_process_overview", "within 7 days of the decision")]
        if dec["final_outcome"] == "decline":
            step_ids.append(find_clause_id("refund_return_request", "invalid dispute"))
        steps = [by_id[c].as_retrieved() for c in dict.fromkeys(step_ids) if c]
        pct = dec.get("partial_refund_percent") or 0
        note = f" of {pct}% (S${case.order.amount_paid_sgd * pct / 100:.2f})" if dec["final_outcome"] == "partial_refund" and pct else ""
        reasons = rec["reasons"] + ([f"Staff note: {dec['note']}"] if dec.get("note") else [])
        drafts = llm.generate(
            task="message_drafts", system=prompts.MESSAGES_SYSTEM,
            prompt=prompts.messages_prompt(case, dec["final_outcome"], reasons, note, steps),
            schema=MessageDrafts, hints={"outcome": dec["final_outcome"]},
        )
        return {"messages": drafts.model_dump(), "trace": _step("Message drafts", t, "Drafted buyer and seller messages")}

    g = StateGraph(AgentState)
    g.add_node("intake", intake)
    g.add_node("eligibility", eligibility)
    g.add_node("rules", rules)
    g.add_node("claims", claims)
    g.add_node("retrieve", retrieve)
    g.add_node("judge", judge)
    g.add_node("search", search)
    g.add_node("plan", plan)
    g.add_node("gate", gate)
    g.add_node("staff_review", staff_review)
    g.add_edge(START, "intake")
    g.add_edge("intake", "eligibility")
    g.add_conditional_edges("eligibility", route, {"claims": "claims", "rules": "rules"})
    g.add_edge("claims", "retrieve")
    g.add_conditional_edges("retrieve", lambda s: "plan" if retrieval == "agentic" else "judge", {"plan": "plan", "judge": "judge"})
    g.add_conditional_edges("plan", after_plan, {"search": "search", "judge": "judge"})
    g.add_conditional_edges("judge", after_judge, {"search": "search", "gate": "gate"})
    g.add_conditional_edges("search", after_search, {"judge": "judge", "gate": "gate"})
    g.add_edge("gate", "staff_review")
    g.add_edge("rules", "staff_review")
    if draft_messages:
        g.add_node("messages", messages)
        g.add_edge("staff_review", "messages")
        g.add_edge("messages", END)
    else:
        g.add_edge("staff_review", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())


NODE_LABELS = {
    "intake": "Case intake",
    "eligibility": "Eligibility check",
    "rules": "Rule-based recommendation",
    "claims": "Claim matching",
    "retrieve": "Policy retrieval",
    "judge": "Policy judgement",
    "search": "Policy search tool",
    "plan": "Research plan",
    "gate": "Confidence and citation check",
    "staff_review": "Staff decision",
    "messages": "Message drafts",
}


def mermaid_diagram(graph) -> str:
    return graph.get_graph().draw_mermaid()


def save_diagram(graph, out: Path) -> Path:
    out.write_text(mermaid_diagram(graph), encoding="utf-8")
    return out
