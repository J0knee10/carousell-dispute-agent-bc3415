"""Streamlit interface for Carousell support staff.

Run with:  uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # lets the app run without installing the package
    sys.path.insert(0, str(ROOT / "src"))

from dispute_agent.agent.graph import NODE_LABELS, build_graph  # noqa: E402
from dispute_agent.agent.runner import current_state, new_thread, resume, stream_to_review  # noqa: E402
from dispute_agent.config import load_config, path  # noqa: E402
from dispute_agent.data.cases import case_ids_for, cases_by_id  # noqa: E402
from dispute_agent.llm import LLMError, RateLimitError, gemini_available, get_llm  # noqa: E402
from dispute_agent.rag.chunker import clauses_by_id, load_clauses  # noqa: E402
from dispute_agent.rag.store import get_store  # noqa: E402
from dispute_agent.schemas import OUTCOME_LABELS, OUTCOMES, DisputeCase  # noqa: E402

st.set_page_config(page_title="Carousell Dispute Agent", page_icon="⚖️", layout="wide")

OUTCOME_COLOURS = {
    "full_refund_with_return": "orange",
    "full_refund_without_return": "red",
    "partial_refund": "blue",
    "decline": "gray",
}
WHATIF_EXAMPLE = (
    "Items listed as 'Brand new' or 'Like new' that arrive with any cosmetic flaw not shown or mentioned "
    "in the listing now qualify for a partial refund, even if the flaw does not affect use."
)


# ------------------------------------------------------------------ resources

@st.cache_resource(show_spinner="Loading the policy index...")
def store():
    return get_store()


@st.cache_resource
def agent(provider: str):
    llm = get_llm(provider=provider)
    return llm, build_graph(llm, store())


@st.cache_data
def all_cases() -> dict[str, dict]:
    return {cid: c.model_dump(mode="json") for cid, c in cases_by_id().items()}


def outcome_label(outcome: str | None) -> str:
    return OUTCOME_LABELS.get(outcome or "", "Refer to staff")


def outcome_badge(outcome: str | None) -> str:
    colour = OUTCOME_COLOURS.get(outcome or "", "violet")
    return f":{colour}-badge[{outcome_label(outcome)}]"


# ------------------------------------------------------------------- sidebar

def sidebar() -> str:
    st.sidebar.title("⚖️ Dispute Agent")
    st.sidebar.caption("Carousell Singapore · 'not as described' disputes")
    options = ["gemini", "mock"] if gemini_available() else ["mock"]
    default = load_config()["llm"]["provider"]
    provider = st.sidebar.radio(
        "LLM provider",
        options,
        index=options.index(default) if default in options else 0,
        help="mock uses keyword rules and needs no API key; its answers are not real judgements.",
    )
    if provider == "gemini":
        st.sidebar.caption(f"Judge model: `{load_config()['llm']['judge_model']}`")
    else:
        st.sidebar.warning("Mock mode: answers come from keyword rules, not an LLM.")
    if not gemini_available():
        st.sidebar.info("Add GEMINI_API_KEY to .env (or Streamlit secrets) to use Gemini.")
    return provider


# -------------------------------------------------------------- case display

def show_case(case: DisputeCase) -> None:
    li, o, d = case.listing, case.order, case.dispute
    left, right = st.columns(2)
    with left:
        st.markdown("#### Listing")
        st.markdown(f"**{li.title}**  \n{li.condition} · {li.category} · S${li.price_sgd:.2f}")
        st.markdown(f"> {li.description}")
        st.caption(f"Source: {li.source} (real Mercari listing; price converted to SGD)")
    with right:
        st.markdown("#### Order and dispute")
        paid = f"{o.payment_method} via 'Buy' button" if o.paid_via_buy_button else f"{o.payment_method} (outside 'Buy' button)"
        rows = [
            ("Paid", paid),
            ("Delivery", o.delivery_method.replace("_", " ")),
            ("Order confirmed", f"{o.order_confirmed_at:%d %b %Y %H:%M}"),
        ]
        if o.delivered_at:
            rows.append(("Delivered", f"{o.delivered_at:%d %b %Y %H:%M}"))
        if o.expected_delivery_at:
            rows.append(("Expected delivery", f"{o.expected_delivery_at:%d %b %Y %H:%M}"))
        if o.meetup_confirmed_at:
            rows.append(("Meet-up", f"{o.meetup_confirmed_at:%d %b %Y %H:%M}"))
        if o.completed_at:
            rows.append(("Marked completed", f"{o.completed_at:%d %b %Y %H:%M}"))
        rows += [("Dispute raised", f"{d.raised_at:%d %b %Y %H:%M}"), ("Reason", d.reason)]
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in rows))
        st.markdown(f"**Buyer:** {d.buyer_complaint}")
        proposal = d.buyer_proposed_resolution.replace("_", " ")
        if d.buyer_requested_refund_sgd:
            proposal += f" (S${d.buyer_requested_refund_sgd:.2f})"
        st.markdown(f"**Buyer proposes:** {proposal}")
        if d.buyer_photo_descriptions:
            st.markdown("**Buyer photos:** " + " · ".join(f"_{p}_" for p in d.buyer_photo_descriptions))
        st.markdown(f"**Seller:** {d.seller_response or '(no response)'}")
        if d.seller_counter_proposal:
            st.markdown(f"**Seller counter-proposal:** {d.seller_counter_proposal}")
        if d.seller_evidence:
            st.markdown("**Seller evidence:** " + " · ".join(f"_{e}_" for e in d.seller_evidence))
    if case.chat:
        with st.expander(f"Chat ({len(case.chat)} messages)"):
            for turn in case.chat:
                with st.chat_message("user" if turn.sender == "buyer" else "assistant", avatar="🛒" if turn.sender == "buyer" else "🏷️"):
                    st.markdown(f"**{turn.sender.title()}:** {turn.text}")


def show_clause(cid: str) -> None:
    clause = clauses_by_id().get(cid)
    if not clause:
        st.markdown(f"- `{cid}` (proposed rule)" if cid == "PROPOSED-1" else f"- `{cid}`")
        return
    with st.expander(f"`{cid}` · {clause.doc_title} > {clause.section}"):
        st.text(clause.text)
        st.markdown(f"[Open the help-centre page]({clause.url})")


def show_results(state: dict) -> None:
    rec = state.get("recommendation", {})
    el = state.get("eligibility", {})

    st.markdown("### Recommendation")
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.markdown(f"## {outcome_badge(rec.get('outcome'))}")
    if rec.get("outcome") == "partial_refund" and rec.get("partial_refund_percent"):
        amount = state["case"]["order"]["amount_paid_sgd"] * rec["partial_refund_percent"] / 100
        c1.caption(f"Suggested: {rec['partial_refund_percent']}% of the price (S${amount:.2f})")
    c2.metric("Confidence", f"{rec.get('confidence', 0):.0%}")
    c3.metric("Decided by", "Eligibility rules" if rec.get("decided_by") == "rules" else "Agent")
    if rec.get("summary_for_staff"):
        st.info(rec["summary_for_staff"])
    if rec.get("escalate"):
        st.warning("**Needs careful review:** " + "; ".join(rec.get("escalation_reasons", [])))
    if rec.get("follow_up_questions"):
        st.markdown("**Suggested follow-up questions**")
        for q in rec["follow_up_questions"]:
            st.markdown(f"- To the **{q['to']}**: {q['question']}")
    if rec.get("reasons"):
        st.markdown("**Reasons**")
        st.markdown("\n".join(f"- {r}" for r in rec["reasons"]))
    if rec.get("citations"):
        st.markdown("**Policy cited**")
        for cid in rec["citations"]:
            show_clause(cid)

    with st.expander("Eligibility checks", expanded=el.get("status") != "eligible"):
        for chk in el.get("checks", []):
            icon = "✅" if chk["passed"] else "❌"
            cites = f" ({', '.join(chk['clause_ids'])})" if chk.get("clause_ids") else ""
            st.markdown(f"{icon} **{chk['name']}**: {chk['detail']}{cites}")

    claims = state.get("claims")
    if claims:
        with st.expander("Claim matching: what was promised vs what the buyer reports", expanded=True):
            a, b = st.columns(2)
            a.markdown("**Listing promised**")
            a.markdown("\n".join(f"- `{p['claim_id']}` {p['text']} _({p['source']})_" for p in claims["promised"]) or "-")
            b.markdown("**Buyer reports**")
            b.markdown("\n".join(f"- `{r['issue_id']}` {r['text']}" for r in claims["reported"]) or "-")
            judged = {g["gap_id"]: g for g in state.get("adjudication", {}).get("gap_assessments", [])}
            st.markdown("**Gaps**")
            st.dataframe(
                [
                    {
                        "Gap": g["gap_id"],
                        "Type": g["gap_type"].replace("_", " "),
                        "Description": g["description"],
                        "Significance": judged.get(g["gap_id"], {}).get("significance", ""),
                        "Why": judged.get(g["gap_id"], {}).get("reasoning", ""),
                    }
                    for g in claims["gaps"]
                ],
                hide_index=True,
                width="stretch",
            )
    if state.get("clauses"):
        with st.expander(f"Policy clauses retrieved ({len(state['clauses'])})"):
            for c in state["clauses"]:
                st.markdown(f"**`{c['clause_id']}`** {c['section']} · _query: {c['query']}_")
                st.caption(c["text"][:400] + ("..." if len(c["text"]) > 400 else ""))


def staff_form(case_id: str, state: dict, provider: str) -> None:
    rec = state["recommendation"]
    st.markdown("### Staff decision")
    with st.form(f"decide-{case_id}"):
        action = st.radio("Decision", ["Approve the recommendation", "Override"], horizontal=True,
                          index=0 if rec.get("outcome") else 1)
        cols = st.columns(2)
        default_outcome = rec.get("outcome") or "decline"
        outcome = cols[0].selectbox("Outcome (for overrides)", OUTCOMES, index=OUTCOMES.index(default_outcome), format_func=outcome_label)
        pct = cols[1].number_input("Partial refund %", 0, 100, int(rec.get("partial_refund_percent") or 0), step=5)
        note = st.text_input("Note (required for overrides)")
        staff = st.text_input("Your name", value="")
        submitted = st.form_submit_button("Submit decision", type="primary")
    if submitted:
        approve = action.startswith("Approve")
        if not approve and not note.strip():
            st.error("Add a note explaining the override.")
            return
        if approve and not rec.get("outcome"):
            st.error("There is no recommended outcome to approve; choose Override.")
            return
        decision = {"action": "approve" if approve else "override", "note": note, "staff": staff}
        if not approve:
            decision["outcome"] = outcome
        if (approve and rec.get("outcome") == "partial_refund") or (not approve and outcome == "partial_refund"):
            decision["partial_refund_percent"] = int(pct)
        llm, graph = agent(provider)
        try:
            with st.spinner("Recording the decision and drafting messages..."):
                final = resume(graph, st.session_state.threads[case_id], decision)
        except RateLimitError as e:
            st.error(f"Gemini quota reached: {e}. The decision was not recorded; try again later.")
            return
        st.session_state.results[case_id] = final
        st.rerun()


def show_final(state: dict) -> None:
    dec = state["decision"]
    verb = "Approved" if dec["action"] == "approve" else "Overridden"
    st.success(f"{verb}: **{outcome_label(dec['final_outcome'])}**" + (f" · note: {dec['note']}" if dec.get("note") else ""))
    msgs = state.get("messages")
    if msgs:
        st.markdown("### Message drafts")
        a, b = st.columns(2)
        a.text_area("To the buyer", msgs["buyer_message"], height=220)
        b.text_area("To the seller", msgs["seller_message"], height=220)
        st.caption("Drafts only: edit before sending.")


def show_trace(state: dict) -> None:
    trace = state.get("trace", [])
    if trace:
        with st.expander("Agent steps"):
            for t in trace:
                st.markdown(f"- **{t['step']}** ({t['seconds']}s): {t['summary']}")


# --------------------------------------------------------------------- pages

def page_review(provider: str) -> None:
    st.title("Review a dispute")
    cases = all_cases()
    split = st.segmented_control("Cases", ["demo", "dev", "test", "all"], default="demo",
                                 help="demo: the four walkthrough cases. test: the held-out set used for evaluation.")
    ids = case_ids_for(split or "demo")
    if not ids:
        st.info("No cases in this set yet.")
        return
    def label(cid: str) -> str:
        c = cases[cid]
        return f"{cid} · {c['listing']['title'][:45]} · {c['dispute']['reason']}"
    case_id = st.selectbox("Case", ids, format_func=label)
    case = DisputeCase.model_validate(cases[case_id])
    if st.toggle("Show the outcome this case was written for (testing only)"):
        st.caption(f"Intended outcome: {outcome_label(case.meta.target_outcome)} · {case.meta.difficulty} · scenario: {case.meta.scenario}")
    show_case(case)
    st.divider()

    st.session_state.setdefault("threads", {})
    st.session_state.setdefault("results", {})
    if st.button("Run the agent", type="primary", key=f"run-{case_id}-{provider}"):
        llm, graph = agent(provider)
        thread = new_thread(case_id)
        try:
            with st.status("Running the agent...", expanded=True) as status:
                for node, update in stream_to_review(graph, case, thread):
                    for t in update.get("trace", []):
                        st.write(f"✓ **{t['step']}**: {t['summary']}")
                status.update(label="Waiting for your decision", state="complete", expanded=False)
        except RateLimitError as e:
            st.error(f"Gemini quota reached: {e}. Try again later or switch to mock.")
            return
        except LLMError as e:
            st.error(f"The LLM call failed: {e}")
            return
        st.session_state.threads[case_id] = thread
        st.session_state.results[case_id] = current_state(graph, thread)

    state = st.session_state.results.get(case_id)
    if not state:
        st.caption("Press **Run the agent** to get a recommendation.")
        return
    show_results(state)
    st.divider()
    if state.get("decision"):
        show_final(state)
    else:
        staff_form(case_id, state, provider)
    show_trace(state)


def page_whatif(provider: str) -> None:
    from dispute_agent.evaluation.harness import QuotaExhausted
    from dispute_agent.evaluation.whatif import run_whatif

    st.title("What-if policy test")
    st.markdown(
        "Write a proposed rule change. The agent re-judges past disputes as if the rule were in force "
        "and shows which outcomes would flip. Each case costs one LLM call (plus two the first time a case is used)."
    )
    change = st.text_area("Proposed rule", WHATIF_EXAMPLE, height=100)
    c1, c2 = st.columns(2)
    split = c1.selectbox("Past cases from", ["dev", "seed", "all"])
    limit = c2.slider("Maximum cases", 3, 60, 10)
    if st.button("Run what-if", type="primary"):
        bar = st.progress(0.0, text="Starting...")
        lines: list[str] = []
        def progress(msg: str) -> None:
            lines.append(msg)
            bar.progress(min(len(lines) / limit, 1.0), text=msg)
        try:
            llm, _ = agent(provider)
            _, result = run_whatif(change, split=split, limit=limit, llm=llm, progress=progress)
        except QuotaExhausted as e:
            st.error(f"Gemini quota reached after {e.done} cases. Try again later.")
            return
        st.session_state.whatif = result
    result = st.session_state.get("whatif")
    if not result:
        return
    s = result["summary"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Cases re-judged", s["cases"])
    m2.metric("Outcomes that flip", f"{s['flipped']} ({(s['flip_rate'] or 0):.0%})")
    m3.metric("Buyer wins", f"{(s['buyer_win_rate_after'] or 0):.0%}", delta=f"{((s['buyer_win_rate_after'] or 0) - (s['buyer_win_rate_before'] or 0)) * 100:+.0f} pts")
    if s["transitions"]:
        st.markdown("**Flips:** " + ", ".join(f"{k}: {v}" for k, v in s["transitions"].items()))
    st.dataframe(
        [
            {"Case": r["case_id"], "Item": r["title"][:40], "Gaps": ", ".join(r["gaps"]), "Before": outcome_label(r["before"]),
             "After": outcome_label(r["after"]), "Flipped": "yes" if r["flipped"] else "", "Uses new rule": "yes" if r["uses_proposed_rule"] else ""}
            for r in result["rows"]
        ],
        hide_index=True,
        width="stretch",
    )


def page_evaluation() -> None:
    st.title("Evaluation results")
    reports = sorted(path("outputs.reports_dir").glob("*.md"))
    if not reports:
        st.info("No reports yet. Run `uv run dispute-agent evaluate` first.")
        return
    choice = st.selectbox("Report", reports, format_func=lambda p: p.stem)
    st.markdown(choice.read_text(encoding="utf-8"))


def page_policy() -> None:
    st.title("Policy library")
    st.caption("Carousell SG help-centre pages, split into the clauses the agent cites.")
    query = st.text_input("Search the policy (the same hybrid search the agent uses)", placeholder="e.g. colour slightly different")
    if query:
        for c in store().retrieve(query, k=5):
            st.markdown(f"**`{c.clause_id}`** {c.doc_title} > {c.section}")
            st.text(c.text)
        st.divider()
    docs: dict[str, list] = {}
    for c in load_clauses():
        docs.setdefault(c.doc_title, []).append(c)
    for title, clauses in docs.items():
        with st.expander(f"{title} ({len(clauses)} clauses)"):
            st.markdown(f"[Source]({clauses[0].url})")
            for c in clauses:
                st.markdown(f"**`{c.clause_id}`** {c.section}")
                st.text(c.text)


def page_about() -> None:
    st.title("How it works")
    st.markdown(
        "The agent is a LangGraph workflow. Fixed rules (payment method, dispute window) are plain code; "
        "the LLM matches the buyer's claims against the listing and judges them against policy clauses "
        "found by hybrid search (ChromaDB embeddings plus BM25). Every recommendation pauses for a staff decision."
    )
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f4f4f5", fontname="Helvetica"];
          intake [label="Case intake"]; elig [label="Eligibility rules\\n(code)"]; rules [label="Rule-based\\nrecommendation"];
          claims [label="Claim matching\\n(LLM)"]; rag [label="Policy retrieval\\n(RAG)"]; judge [label="Policy judgement\\n(LLM)"];
          gate [label="Confidence and\\ncitation check"]; staff [label="Staff decides\\n(pause)", fillcolor="#fde68a"]; msgs [label="Message drafts\\n(LLM)"];
          intake -> elig; elig -> claims [label="covered"]; elig -> rules [label="not covered /\\nprocedural"];
          claims -> rag -> judge -> gate -> staff; rules -> staff; staff -> msgs;
        }
        """
    )
    st.markdown("**Nodes:** " + ", ".join(NODE_LABELS.values()))


def main() -> None:
    provider = sidebar()
    pages = {
        "Review a dispute": lambda: page_review(provider),
        "What-if policy test": lambda: page_whatif(provider),
        "Evaluation results": page_evaluation,
        "Policy library": page_policy,
        "How it works": page_about,
    }
    choice = st.sidebar.radio("Page", list(pages))
    pages[choice]()


main()
