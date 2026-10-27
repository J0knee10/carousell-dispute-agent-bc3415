"""Smoke test of the Streamlit app with the mock provider."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def test_review_flow_runs_and_records_a_decision():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    assert any("Review a dispute" in t.value for t in at.title)
    at.sidebar.radio[0].set_value("mock").run()
    run_button = next(b for b in at.button if b.label == "Run the agent")
    run_button.click().run()
    assert not at.exception
    assert any("Recommendation" in m.value for m in at.markdown)
    submit = next(b for b in at.button if b.label == "Submit decision")
    submit.click().run()
    assert not at.exception
    assert any("Approved" in s.value for s in at.success)


def test_other_pages_render():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.sidebar.radio[0].set_value("mock").run()
    for name in ["What-if policy test", "Evaluation results", "Policy library", "How it works"]:
        at.sidebar.radio[1].set_value(name).run()
        assert not at.exception, name
