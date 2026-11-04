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


def test_failed_answers_count_as_wrong():
    labels = {
        "A": {"outcome": "decline", "eligible": True, "source": "provisional"},
        "B": {"outcome": "decline", "eligible": True, "source": "provisional"},
    }
    meta = {"A": {"difficulty": "clear"}, "B": {"difficulty": "clear"}}
    records = [_rec("A", "decline"), {"case_id": "B", "error": "output did not match"}]
    m = compute_metrics(records, labels, meta)
    assert m["n"] == 2 and m["failed"]["n"] == 1
    assert m["decision_accuracy"] == 0.5
    assert m["llm_calls_per_case"] == 2  # averaged over answered cases only


def test_a_later_success_replaces_a_failure():
    labels = {"A": {"outcome": "decline", "eligible": True, "source": "provisional"}}
    meta = {"A": {"difficulty": "clear"}}
    m = compute_metrics([{"case_id": "A", "error": "x"}, _rec("A", "decline")], labels, meta)
    assert m["failed"]["n"] == 0 and m["decision_accuracy"] == 1.0


def test_raw_invented_citations_and_tool_use_are_reported():
    labels = {"A": {"outcome": "decline", "eligible": True, "source": "provisional"}}
    meta = {"A": {"difficulty": "clear"}}
    rec = {**_rec("A", "decline"), "raw_invalid_citations": ["XYZ-9"], "tool_calls": [{"tool": "search_policy"}]}
    m = compute_metrics([rec], labels, meta)
    assert m["invented_citation_rate"] == 0.0  # the final answer is clean
    assert m["raw_invented_citation_rate"] == 1.0
    assert m["tool_use"]["cases_using_search"] == 1.0


def test_comparison_report_on_mock_runs(mock_llm, store, seeds):
    from dispute_agent.evaluation.compare import build_comparison
    from dispute_agent.evaluation.harness import run_dir, run_system, write_run_info
    import shutil

    cases = list(seeds.values())[:4]
    run = "pytest_compare_mock"
    shutil.rmtree(run_dir(run), ignore_errors=True)
    write_run_info(run, {"split": "seed", "case_ids": [c.case_id for c in cases], "provider": "mock", "model": "mock"})
    for system in ("agent", "baseline"):
        run_system(system, cases, mock_llm, store, run, 0.7, progress=lambda m: None)
    out = build_comparison([run], out_name="pytest_model_comparison", hardware="test")
    text = out.read_text(encoding="utf-8")
    assert "## Decision accuracy" in text and "mock-keyword-rules" in text
    for f in out.parent.glob(f"*{run}*"):
        f.unlink()
    for f in out.parent.glob("pytest_model_comparison.*"):
        f.unlink()
    shutil.rmtree(run_dir(run), ignore_errors=True)


def test_whatif_runs_on_mock(mock_llm):
    _, result = run_whatif("Wear on used items now qualifies for a partial refund.", split="seed", limit=4, llm=mock_llm, progress=lambda m: None)
    s = result["summary"]
    assert s["cases"] == 4
    assert 0 <= s["flipped"] <= 4
