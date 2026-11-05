"""Smoke test of the Streamlit app with the mock provider."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    at.sidebar.radio[0].set_value("mock").run()
    return at


def test_review_flow_runs_and_records_a_decision():
    at = _app()
    assert any("Review a dispute" in t.value for t in at.title)
    demo = next(b for b in at.button if b.label.startswith("S01 "))
    demo.click().run()
    assert not at.exception
    assert any("Recommendation" in m.value for m in at.markdown)
    approve = next(b for b in at.button if b.label == "✅ Approve")
    approve.click().run()
    assert not at.exception
    assert any("Approved" in m.value for m in at.markdown)
    assert any(t.label == "To the buyer" for t in at.text_area)


def test_review_chat_finds_cases_by_id_and_by_word():
    at = _app()
    at.chat_input[0].set_value("iphone").run()
    assert not at.exception
    assert any("match **iphone**" in m.value for m in at.markdown)
    at.chat_input[0].set_value("s10").run()
    assert not at.exception
    assert any("Review case **S10**" in m.value for m in at.markdown)
    at.chat_input[0].set_value("no such words here").run()
    assert any("No case matches" in m.value for m in at.markdown)


def test_whatif_chat_runs_a_rule():
    at = _app()
    at.sidebar.radio[1].set_value("What-if policy test").run()
    assert not at.exception
    at.session_state["wi_limit"] = 3
    at.chat_input[0].set_value("Any missing accessory gets a partial refund.").run()
    assert not at.exception
    assert any("past cases would get a different outcome" in m.value for m in at.markdown)


def test_other_pages_render():
    at = _app()
    for name in ["What-if policy test", "Evaluation results", "Policy library", "How it works"]:
        at.sidebar.radio[1].set_value(name).run()
        assert not at.exception, name
