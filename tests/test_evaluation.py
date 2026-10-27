from dispute_agent.evaluation.metrics import compute_metrics
from dispute_agent.evaluation.whatif import run_whatif


def _rec(cid, pred, eligible=True, escalate=False):
    return {"case_id": cid, "predicted_outcome": pred, "predicted_eligible": eligible, "escalate": escalate,
            "citations": ["BPR-02"], "seconds": 1.0, "llm_calls": 2, "decided_by": "llm"}


def test_metrics():
    labels = {
        "A": {"outcome": "decline", "eligible": True, "source": "provisional"},
        "B": {"outcome": "partial_refund", "eligible": True, "source": "provisional"},
        "C": {"outcome": "decline", "eligible": False, "source": "agreed"},
        "D": {"outcome": "full_refund_with_return", "eligible": True, "source": "provisional"},
    }
    meta = {"A": {"difficulty": "clear"}, "B": {"difficulty": "borderline"}, "C": {"difficulty": "ineligible"}, "D": {"difficulty": "clear"}}
    records = [
        _rec("A", "decline"),
        _rec("B", "full_refund_with_return", escalate=True),
        _rec("C", "decline", eligible=False),
        _rec("D", "decline"),
    ]
    m = compute_metrics(records, labels, meta)
    assert m["n"] == 4
    assert m["decision_accuracy"] == 0.5
    assert m["direction_accuracy"] == 0.75
    assert m["eligibility_accuracy"] == 1.0
    assert m["ineligible_flagged"]["share"] == 1.0
    assert m["escalation"]["wrong_decisions_escalated"] == 0.5
    assert m["confusion"]["partial_refund"]["full_refund_with_return"] == 1


def test_later_records_replace_earlier_ones():
    labels = {"A": {"outcome": "decline", "eligible": True, "source": "provisional"}}
    meta = {"A": {"difficulty": "clear"}}
    m = compute_metrics([_rec("A", "partial_refund"), _rec("A", "decline")], labels, meta)
    assert m["n"] == 1 and m["decision_accuracy"] == 1.0


def test_whatif_runs_on_mock(mock_llm):
    _, result = run_whatif("Wear on used items now qualifies for a partial refund.", split="seed", limit=4, llm=mock_llm, progress=lambda m: None)
    s = result["summary"]
    assert s["cases"] == 4
    assert 0 <= s["flipped"] <= 4
