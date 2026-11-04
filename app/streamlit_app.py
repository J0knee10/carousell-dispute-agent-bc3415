"""Streamlit interface for Carousell support staff.

Run with:  uv run streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:  # lets the app run without installing the package
    sys.path.insert(0, str(ROOT / "src"))

SECRET_NAMES = ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_PROVIDER", "GEMINI_MODEL", "OPENAI_MODEL", "OLLAMA_MODEL", "OLLAMA_HOST")


def secrets_to_env() -> None:
    """On Streamlit Community Cloud the key lives in the app's Secrets, not in .env."""
    try:
        for name in SECRET_NAMES:
            if name in st.secrets and not os.environ.get(name):
                os.environ[name] = str(st.secrets[name])
    except Exception:  # no secrets file: running locally with .env
        pass


secrets_to_env()

from dispute_agent.agent.graph import NODE_LABELS, build_graph  # noqa: E402
from dispute_agent.agent.runner import current_state, new_thread, resume, stream_to_review  # noqa: E402
from dispute_agent.config import judge_model, load_config, path  # noqa: E402
from dispute_agent.data.cases import case_ids_for, cases_by_id  # noqa: E402
from dispute_agent.llm import LLMError, RateLimitError, available_providers, fallback_provider, get_llm  # noqa: E402
from dispute_agent.llm.ollama import installed_models  # noqa: E402
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


def agent(provider: str, model: str | None = None):
    """One LLM client and graph per browser session.

    The client falls back to the paid provider when the free one fails (config
    llm.fallback), and remembers which model answered last; sharing it between
    sessions could show one user another user's model.
    """
    agents = st.session_state.setdefault("agents", {})
    if (provider, model) not in agents:
        llm = get_llm(provider=provider, model=model, for_app=True)
        agents[(provider, model)] = (llm, build_graph(llm, store()))
    return agents[(provider, model)]


@st.cache_data(ttl=60, show_spinner=False)
def providers_here() -> list[str]:
    # Cached: checking for a local Ollama server takes up to 1.5 s when there is none.
    return available_providers()


@st.cache_data(ttl=60, show_spinner=False)
def ollama_models() -> list[str]:
    return installed_models(load_config()["llm"]["ollama"]["host"])


PROVIDER_LABELS = {
    "gemini": "Gemini (Google cloud, free tier)",
    "ollama": "Local model (Ollama, this computer)",
    "openai": "OpenAI (cloud, paid)",
    "mock": "Mock (offline keyword rules)",
}


@st.cache_data
def all_cases() -> dict[str, dict]:
    return {cid: c.model_dump(mode="json") for cid, c in cases_by_id().items()}


def outcome_label(outcome: str | None) -> str:
    return OUTCOME_LABELS.get(outcome or "", "Refer to staff")


def outcome_badge(outcome: str | None) -> str:
    colour = OUTCOME_COLOURS.get(outcome or "", "violet")
    return f":{colour}-badge[{outcome_label(outcome)}]"


# ------------------------------------------------------------------- sidebar

def sidebar() -> tuple[str, str | None]:
    st.sidebar.title("⚖️ Dispute Agent")
    st.sidebar.caption("Carousell Singapore · 'not as described' disputes")
    options = providers_here()
    default = load_config()["llm"]["provider"]
    provider = st.sidebar.radio(
        "LLM provider",
        options,
        index=options.index(default) if default in options else 0,
        format_func=lambda p: PROVIDER_LABELS.get(p, p),
        help="Only providers that can run here are listed: a key is set, or a local Ollama server is running. "
        "Mock needs nothing; its answers are not real judgements.",
    )
    model = None
    if provider == "ollama":
        models = ollama_models() or [judge_model("ollama")]
        preferred = judge_model("ollama")
        model = st.sidebar.selectbox("Local model", models, index=models.index(preferred) if preferred in models else 0)
        st.sidebar.caption("Runs on this computer; case data never leaves it.")
    elif provider == "mock":
        st.sidebar.warning("Mock mode: answers come from keyword rules, not an LLM.")
    else:
        st.sidebar.caption(f"Judge model: `{judge_model(provider)}`")
        fb = fallback_provider(provider)
        if fb:
            budget = load_config()["llm"].get("openai", {}).get("app_budget_sgd_per_month", 100)
            st.sidebar.caption(f"If {provider} fails or its free quota runs out: `{judge_model(fb)}` ({fb}, paid; "
                               f"stops at S${budget:.0f} a month)")
        if provider == "openai":
            budget = load_config()["llm"].get("openai", {}).get("app_budget_sgd_per_month", 100)
            st.sidebar.caption(f"Paid: the app stops at S${budget:.0f} of OpenAI usage a month.")
    if "gemini" not in options:
        st.sidebar.info("Add GEMINI_API_KEY to .env (or the app's Streamlit secrets) to use Gemini.")
    return provider, model


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
    if state.get("judged_by") and rec.get("decided_by") == "llm":
        st.caption(f"Judged by {state['judged_by']}")
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
    if state.get("tool_calls"):
        with st.expander(f"Tool calls by the judge ({len(state['tool_calls'])})", expanded=True):
            st.caption("The clauses retrieved so far did not cover a gap, so the agent called the search_policy tool "
                       "(its request comes back as structured JSON; code runs the search).")
            for call in state["tool_calls"]:
                found = ", ".join(f"`{c}`" for c in call["new_clauses"]) or "nothing new"
                st.markdown(f"- `search_policy(\"{call['query']}\")` → {found}")
    if state.get("clauses"):
        with st.expander(f"Policy clauses retrieved ({len(state['clauses'])})"):
            for c in state["clauses"]:
                st.markdown(f"**`{c['clause_id']}`** {c['section']} · _query: {c['query']}_")
                st.caption(c["text"][:400] + ("..." if len(c["text"]) > 400 else ""))


def staff_form(case_id: str, state: dict, provider: str, model: str | None) -> None:
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
        # Resume with the graph that ran this case, even if the sidebar changed since.
        thread, run_provider, run_model = st.session_state.threads[case_id]
        llm, graph = agent(run_provider, run_model)
        try:
            with st.spinner("Recording the decision and drafting messages..."):
                final = resume(graph, thread, decision)
        except RateLimitError as e:
            st.error(f"API quota reached: {e}. The decision was not recorded; try again later.")
            return
        except LLMError as e:
            st.error(f"The LLM call failed: {e}. The decision was not recorded.")
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

def page_review(provider: str, model: str | None) -> None:
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
    if st.button("Run the agent", type="primary", key=f"run-{case_id}-{provider}-{model}"):
        llm, graph = agent(provider, model)
        thread = new_thread(case_id)
        try:
            with st.status("Running the agent...", expanded=True) as status:
                for node, update in stream_to_review(graph, case, thread):
                    for t in update.get("trace", []):
                        st.write(f"✓ **{t['step']}**: {t['summary']}")
                status.update(label="Waiting for your decision", state="complete", expanded=False)
        except RateLimitError as e:
            st.error(f"API quota reached: {e}. Try again later or switch provider.")
            return
        except LLMError as e:
            st.error(f"The LLM call failed: {e}")
            return
        st.session_state.threads[case_id] = (thread, provider, model)
        result = current_state(graph, thread)
        # Which model actually answered: the fallback may have stepped in.
        result["judged_by"] = f"{llm.name} · {llm.model}" + (" (fallback)" if getattr(llm, "using_backup", False) else "")
        st.session_state.results[case_id] = result

    state = st.session_state.results.get(case_id)
    if not state:
        st.caption("Press **Run the agent** to get a recommendation.")
        return
    show_results(state)
    st.divider()
    if state.get("decision"):
        show_final(state)
    else:
        staff_form(case_id, state, provider, model)
    show_trace(state)


def page_whatif(provider: str, model: str | None) -> None:
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
            llm, _ = agent(provider, model)
            _, result = run_whatif(change, split=split, limit=limit, llm=llm, progress=progress)
        except QuotaExhausted as e:
            st.error(f"API quota reached after {e.done} cases. Try again later.")
            return
        except LLMError as e:
            st.error(f"The LLM call failed: {e}")
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
    # The model comparison first, then the newest runs.
    reports = sorted(path("outputs.reports_dir").glob("*.md"), key=lambda p: (p.stem != "model_comparison", -p.stat().st_mtime))
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
        "found by hybrid search (ChromaDB embeddings plus BM25). If those clauses do not cover a gap, the judge "
        "calls the `search_policy` tool and the graph loops back with the new clauses. Code then checks the "
        "citations and confidence, and every recommendation pauses for a staff decision.\n\n"
        "The judge can be Gemini (cloud), a local model through Ollama, or OpenAI; "
        "`reports/model_comparison.md` compares them on the held-out test set."
    )
    st.graphviz_chart(
        """
        digraph {
          rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#f4f4f5", fontname="Helvetica"];
          intake [label="Case intake"]; elig [label="Eligibility rules\\n(code)"]; rules [label="Rule-based\\nrecommendation"];
          claims [label="Claim matching\\n(LLM)"]; rag [label="Policy retrieval\\n(RAG)"]; judge [label="Policy judgement\\n(LLM)"];
          gate [label="Confidence and\\ncitation check"]; staff [label="Staff decides\\n(pause)", fillcolor="#fde68a"]; msgs [label="Message drafts\\n(LLM)"];
          intake -> elig; elig -> claims [label="covered"]; elig -> rules [label="not covered /\\nprocedural"];
          tool [label="search_policy\\ntool (RAG)", fillcolor="#dbeafe"];
          claims -> rag -> judge; judge -> tool [label="needs more\\npolicy"]; tool -> judge [label="new\\nclauses"];
          judge -> gate -> staff; rules -> staff; staff -> msgs;
        }
        """
    )
    st.markdown("**Nodes:** " + ", ".join(NODE_LABELS.values()))


def main() -> None:
    provider, model = sidebar()
    pages = {
        "Review a dispute": lambda: page_review(provider, model),
        "What-if policy test": lambda: page_whatif(provider, model),
        "Evaluation results": page_evaluation,
        "Policy library": page_policy,
        "How it works": page_about,
    }
    choice = st.sidebar.radio("Page", list(pages))
    pages[choice]()


main()
