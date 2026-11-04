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
        search_policy=[], needs_more_evidence=False, follow_up_questions=[], summary_for_staff="",
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


def test_gate_escalates_when_the_judge_still_wants_policy():
    rec = review_gate(_adj(), ELIGIBLE, {"BPR-02"}, 0.7, wanted_more_policy=True)
    assert rec.escalate and "search tool" in rec.escalation_reasons[0]


# ------------------------------------------------------- search_policy tool loop

class ScriptedJudge:
    """Wraps the mock: the judge's first answer calls search_policy, the second decides."""

    def __init__(self, mock, queries):
        self.mock, self.queries = mock, queries
        self.name, self.model, self.stats = "scripted", "scripted", mock.stats
        self.prompts: list[str] = []

    def generate(self, **kw):
        result = self.mock.generate(**kw)
        if kw["task"] == "adjudication":
            self.prompts.append(kw["prompt"])
            first = len(self.prompts) == 1
            result = result.model_copy(update={"search_policy": self.queries if first else []})
        return result


def test_judge_calls_search_policy_and_rejudges_with_new_clauses(mock_llm, store, seeds):
    llm = ScriptedJudge(mock_llm, ["damage during delivery courier"])
    graph = build_graph(llm, store, decision_logger=None)
    r = run_to_review(graph, seeds["S01"], llm)
    st = r.state
    assert len(st["tool_calls"]) == 1 and st["tool_calls"][0]["tool"] == "search_policy"
    new = st["tool_calls"][0]["new_clauses"]
    assert new and set(new) <= {c["clause_id"] for c in st["clauses"]}
    assert st["judge_rounds"] == 2 and r.llm_calls == 3
    assert "search_policy (available)" in llm.prompts[0]
    assert "already used" in llm.prompts[1]
    assert any(t["step"] == "Policy search tool" for t in r.trace)
    assert not any("search tool" in e for e in st["recommendation"]["escalation_reasons"])


def test_search_that_finds_nothing_new_skips_the_second_judgement(mock_llm, store, seeds):
    case = seeds["S01"]
    graph = build_graph(mock_llm, store, decision_logger=None)
    first = run_to_review(graph, case, mock_llm).state
    # Repeat the first retrieval query: its top clauses are all retrieved already
    # (two queries x top 3 stays under the 8-clause cap), so there is nothing new.
    queries = [first["clauses"][0]["query"]]
    llm = ScriptedJudge(mock_llm, queries)
    st = run_to_review(build_graph(llm, store, decision_logger=None), case, llm).state
    assert st["tool_calls"][0]["new_clauses"] == []
    assert st["judge_rounds"] == 1
    assert any("search tool" in e for e in st["recommendation"]["escalation_reasons"])


def test_tool_can_be_switched_off(mock_llm, store, seeds):
    llm = ScriptedJudge(mock_llm, ["damage during delivery"])
    st = run_to_review(build_graph(llm, store, decision_logger=None, max_tool_rounds=0), seeds["S01"], llm).state
    assert st.get("tool_calls", []) == [] and st["judge_rounds"] == 1
    assert "No tools are available" in llm.prompts[0]


def test_agent_driven_retrieval_starts_general_and_searches_per_gap(mock_llm, store, seeds):
    graph = build_graph(mock_llm, store, decision_logger=None, retrieval="agentic")
    r = run_to_review(graph, seeds["S01"], mock_llm)
    st = r.state
    general = {c.clause_id for c in store.retrieve("incomplete item with missing parts: refund or seller sends the missing part")}
    assert st["tool_calls"], "the judge has to search for the gap itself"
    assert {c["clause_id"] for c in st["clauses"]} >= general
    assert any("General clauses only" in t["summary"] for t in r.trace)


def test_no_retrieval_ablation_gives_the_judge_no_clauses(mock_llm, store, seeds):
    graph = build_graph(mock_llm, store, decision_logger=None, use_retrieval=False)
    st = run_to_review(graph, seeds["S01"], mock_llm).state
    assert st["clauses"] == []
    assert st["recommendation"]["escalate"]  # nothing to cite
