import pytest

from dispute_agent.agent.graph import build_graph, review_gate
from dispute_agent.agent.runner import resume, run_to_review
from dispute_agent.schemas import Adjudication, EligibilityResult, GapAssessment


@pytest.fixture
def graph(mock_llm, store):
    return build_graph(mock_llm, store, decision_logger=None)


def test_every_seed_case_pauses_for_staff(graph, mock_llm, seeds):
    for case in seeds.values():
        r = run_to_review(graph, case, mock_llm)
        assert r.waiting_for_staff, case.case_id
        rec = r.state["recommendation"]
        assert rec["eligible"] == case.meta.target_eligible


def test_ineligible_cases_skip_the_llm(graph, mock_llm, seeds):
    r = run_to_review(graph, seeds["S16"], mock_llm)
    assert r.llm_calls == 0
    assert r.state["recommendation"]["outcome"] == "decline"
    assert r.state["recommendation"]["decided_by"] == "rules"


def test_procedural_case_follows_buyer_proposal(graph, mock_llm, seeds):
    rec = run_to_review(graph, seeds["S20"], mock_llm).state["recommendation"]
    assert rec["outcome"] == "partial_refund"
    assert rec["partial_refund_percent"] > 0


def test_eligible_case_uses_two_llm_calls_and_cites_retrieved_clauses(graph, mock_llm, seeds):
    r = run_to_review(graph, seeds["S01"], mock_llm)
    assert r.llm_calls == 2
    retrieved = {c["clause_id"] for c in r.state["clauses"]}
    assert set(r.state["recommendation"]["citations"]) <= retrieved


def test_approve_then_draft_messages(graph, mock_llm, seeds):
    r = run_to_review(graph, seeds["S02"], mock_llm)
    final = resume(graph, r.thread_id, {"action": "approve", "staff": "test"})
    assert final["decision"]["final_outcome"] == r.state["recommendation"]["outcome"]
    assert final["messages"]["buyer_message"] and final["messages"]["seller_message"]


def test_override_records_staff_outcome(mock_llm, store, seeds):
    log = []
    graph = build_graph(mock_llm, store, decision_logger=log.append)
    r = run_to_review(graph, seeds["S01"], mock_llm)
    final = resume(graph, r.thread_id, {"action": "override", "outcome": "decline", "note": "photo shows the card"})
    assert final["decision"]["final_outcome"] == "decline"
    assert final["decision"]["partial_refund_percent"] == 0
    assert log and log[0]["action"] == "override"


def _adj(**kw):
    base = dict(
        gap_assessments=[GapAssessment(gap_id="G1", significance="significant", reasoning="", clause_ids=["BPR-02"])],
        outcome="partial_refund", partial_refund_percent=20, confidence=0.9, reasons=["r"], citations=["BPR-02"],
        needs_more_evidence=False, follow_up_questions=[], summary_for_staff="",
    )
    base.update(kw)
    return Adjudication(**base)


ELIGIBLE = EligibilityResult(status="eligible", checks=[])


def test_gate_passes_a_clean_judgement():
    rec = review_gate(_adj(), ELIGIBLE, {"BPR-02"}, 0.7)
    assert not rec.escalate


def test_gate_drops_invented_citations():
    rec = review_gate(_adj(citations=["BPR-02", "XYZ-99"]), ELIGIBLE, {"BPR-02"}, 0.7)
    assert rec.citations == ["BPR-02"]
    assert rec.escalate and "XYZ-99" in rec.escalation_reasons[0]


def test_gate_escalates_low_confidence_and_inconsistency():
    rec = review_gate(_adj(confidence=0.5, outcome="decline"), ELIGIBLE, {"BPR-02"}, 0.7)
    assert rec.escalate
    assert any("below" in r for r in rec.escalation_reasons)
    assert any("Declines although" in r for r in rec.escalation_reasons)
