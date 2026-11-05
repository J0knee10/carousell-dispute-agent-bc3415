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
REASON_LABELS = {
    "snad": "not as described",
    "incomplete": "missing parts",
    "damaged": "damaged",
    "counterfeit": "counterfeit",
    "not_received": "not received",
}
WHATIF_EXAMPLES = [
    "Items listed as 'Brand new' or 'Like new' that arrive with any cosmetic flaw not shown or mentioned "
    "in the listing now qualify for a partial refund, even if the flaw does not affect use.",
    "A missing accessory worth less than a tenth of the price is settled with a partial refund, "
    "never a full refund with return.",
    "If the seller does not respond to the dispute, the buyer's description of the problem is taken as accurate.",
]
AVATARS = {"staff": "🧑‍💼", "agent": "⚖️", "case": "📦"}
SPLIT_HELP = "demo: the four walkthrough cases. dev: cases used while building. test: the held-out set used for evaluation."


# ------------------------------------------------------------------ resources

@st.cache_resource(show_spinner="Loading the policy index...")
def store():
    return get_store()


def agent(provider: str, model: str | None = None):
    """One LLM client and graph per browser session.

    The client falls back to OpenAI when a Gemini call fails (config llm.fallback),
    and remembers which model answered last; sharing it between sessions could
    show one user another user's model.
    """
    agents = st.session_state.setdefault("agents", {})
    if (provider, model) not in agents:
        llm = get_llm(provider=provider, model=model, for_app=True)
        agents[(provider, model)] = (llm, build_graph(llm, store()))
    return agents[(provider, model)]


@st.cache_data(ttl=60, show_spinner=False)
def providers_here() -> list[str]:
    # Cached: checking for a local Ollama server takes up to 1.5 s when there is none.
    # OpenAI is not offered as a judge: it is only Gemini's fallback (see sidebar()).
    return [p for p in available_providers() if p != "openai"]


@st.cache_data(ttl=60, show_spinner=False)
def ollama_models() -> list[str]:
    return installed_models(load_config()["llm"]["ollama"]["host"])


PROVIDER_LABELS = {
    "gemini": "Gemini (Google cloud, free tier)",
    "ollama": "Local model (Ollama, this computer)",
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


def reason_label(reason: str) -> str:
    return REASON_LABELS.get(reason, reason.replace("_", " "))


def case_label(cid: str) -> str:
    c = all_cases()[cid]
    return f"{cid} · {c['listing']['title'][:45]} · {reason_label(c['dispute']['reason'])}"


def next_id() -> int:
    st.session_state["_next_id"] = st.session_state.get("_next_id", 0) + 1
    return st.session_state["_next_id"]


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
            st.sidebar.caption(f"If {provider} fails or its free quota runs out: `{judge_model(fb)}` ({fb}, "
                               "free usage tier, about 50 requests a day). Not tested on our test set.")
    if "gemini" not in options:
        st.sidebar.info("Add GEMINI_API_KEY to .env (or the app's Streamlit secrets) to use Gemini.")
    return provider, model


def staff_settings() -> None:
    """Review-page settings that belong to the person, not to one case."""
    with st.sidebar.expander("Your details and testing options"):
        st.text_input("Your name (saved with each decision)", key="staff_name")
        st.toggle("Show the outcome each case was written for (testing only)", key="show_intended")


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
        rows += [("Dispute raised", f"{d.raised_at:%d %b %Y %H:%M}"), ("Reason", reason_label(d.reason))]
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in rows))
        proposal = d.buyer_proposed_resolution.replace("_", " ")
        if d.buyer_requested_refund_sgd:
            proposal += f" (S${d.buyer_requested_refund_sgd:.2f})"
        st.markdown(f"**Buyer proposes:** {proposal}")
        if d.buyer_photo_descriptions:
            st.markdown("**Buyer photos:** " + " · ".join(f"_{p}_" for p in d.buyer_photo_descriptions))
        if d.seller_counter_proposal:
            st.markdown(f"**Seller counter-proposal:** {d.seller_counter_proposal}")
        if d.seller_evidence:
            st.markdown("**Seller evidence:** " + " · ".join(f"_{e}_" for e in d.seller_evidence))
    if case.chat:
        st.markdown(f"#### Chat between buyer and seller ({len(case.chat)} messages)")
        for turn in case.chat:
            icon = "🛒" if turn.sender == "buyer" else "🏷️"
            st.markdown(f"{icon} **{turn.sender.title()}:** {turn.text}")


def case_card(case: DisputeCase) -> None:
    """The short version of a case, as the first message of its review."""
    li, o, d = case.listing, case.order, case.dispute
    st.markdown(f"**{li.title}** · {li.condition} · S${o.amount_paid_sgd:.2f} · "
                f"dispute: **{reason_label(d.reason)}**")
    st.markdown(f"🛒 **Buyer:** {d.buyer_complaint}")
    st.markdown(f"🏷️ **Seller:** {d.seller_response or '_(no response)_'}")
    if st.session_state.get("show_intended"):
        st.caption(f"Written for: {outcome_label(case.meta.target_outcome)} · {case.meta.difficulty} · "
                   f"scenario: {case.meta.scenario}")
    with st.expander("Full case: listing, order dates, evidence and chat"):
        show_case(case)


def show_clause(cid: str) -> None:
    clause = clauses_by_id().get(cid)
    if not clause:
        st.markdown(f"- `{cid}` (proposed rule)" if cid == "PROPOSED-1" else f"- `{cid}`")
        return
    with st.expander(f"📜 `{cid}` · {clause.doc_title} > {clause.section}"):
        st.text(clause.text)
        st.markdown(f"[Open the help-centre page]({clause.url})")


def show_steps(state: dict) -> None:
    trace = [t for t in state.get("trace", []) if t["step"] not in (NODE_LABELS["staff_review"], NODE_LABELS["messages"])]
    if trace:
        total = sum(t.get("seconds") or 0 for t in trace)
        with st.expander(f"✓ Reviewed in {len(trace)} steps ({total:.1f} s)"):
            for t in trace:
                st.markdown(f"- **{t['step']}** ({t['seconds']}s): {t['summary']}")


def show_recommendation(state: dict) -> None:
    rec = state.get("recommendation", {})
    line = f"#### Recommendation: {outcome_badge(rec.get('outcome'))}"
    if rec.get("outcome") == "partial_refund" and rec.get("partial_refund_percent"):
        amount = state["case"]["order"]["amount_paid_sgd"] * rec["partial_refund_percent"] / 100
        line += f" {rec['partial_refund_percent']}% (S${amount:.2f})"
    st.markdown(line)
    who = "the eligibility rules (no LLM needed)" if rec.get("decided_by") == "rules" else "the agent"
    meta = f"Confidence {rec.get('confidence', 0):.0%} · decided by {who}"
    if state.get("judged_by") and rec.get("decided_by") == "llm":
        meta += f" · judged by {state['judged_by']}"
    st.caption(meta)
    if rec.get("summary_for_staff"):
        st.markdown(rec["summary_for_staff"])
    if rec.get("escalate"):
        st.warning("**Needs careful review:** " + "; ".join(rec.get("escalation_reasons", [])))
    if rec.get("follow_up_questions"):
        st.markdown("**Suggested follow-up questions**")
        for q in rec["follow_up_questions"]:
            st.markdown(f"- To the **{q['to']}**: {q['question']}")
    if rec.get("reasons"):
        st.markdown("**Why**")
        st.markdown("\n".join(f"- {r}" for r in rec["reasons"]))
    if rec.get("citations"):
        st.markdown("**Policy cited** (click to read the clause)")
        for cid in rec["citations"]:
            show_clause(cid)


def show_working(state: dict) -> None:
    """How the agent got there: the evidence behind the recommendation, folded away."""
    el = state.get("eligibility", {})
    st.markdown("**How I got there**")
    with st.expander("Eligibility checks", expanded=el.get("status") != "eligible"):
        for chk in el.get("checks", []):
            icon = "✅" if chk["passed"] else "❌"
            cites = f" ({', '.join(chk['clause_ids'])})" if chk.get("clause_ids") else ""
            st.markdown(f"{icon} **{chk['name']}**: {chk['detail']}{cites}")
    claims = state.get("claims")
    if claims:
        with st.expander("Claim matching: what was promised vs what the buyer reports"):
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
        with st.expander(f"Tool calls by the judge ({len(state['tool_calls'])})"):
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


# ---------------------------------------------------------- review: actions

def queue_case(case_id: str, provider: str, model: str | None) -> None:
    st.session_state.setdefault("review_events", []).append(
        {"id": next_id(), "kind": "case", "case_id": case_id, "provider": provider, "model": model, "status": "pending"}
    )


def find_cases(query: str) -> list[str]:
    """A case ID, or every case whose listing or dispute contains all the words."""
    q = query.strip()
    cases = all_cases()
    by_upper = {cid.upper(): cid for cid in cases}
    if q.upper() in by_upper:
        return [by_upper[q.upper()]]
    words = [w for w in q.lower().split() if w]
    def text(c: dict) -> str:
        li, d = c["listing"], c["dispute"]
        return " ".join([li["title"], li["description"], li["category"], d["buyer_complaint"],
                         d["reason"], reason_label(d["reason"])]).lower()
    demo = set(case_ids_for("demo"))
    hits = [cid for cid, c in cases.items() if words and all(w in text(c) for w in words)]
    return sorted(hits, key=lambda cid: (cid not in demo, cid))


def on_review_chat(provider: str, model: str | None) -> None:
    query = (st.session_state.get("review_chat") or "").strip()
    if not query:
        return
    hits = find_cases(query)
    if len(hits) == 1 and hits[0].upper() == query.upper():
        queue_case(hits[0], provider, model)
    else:
        st.session_state.setdefault("review_events", []).append(
            {"id": next_id(), "kind": "search", "query": query, "matches": hits}
        )


def clear_review() -> None:
    st.session_state["review_events"] = []


def record_decision(event: dict, decision: dict) -> bool:
    """Resume the paused graph with the staff decision; True when it worked."""
    # Resume with the graph that ran this case, even if the sidebar changed since.
    _, graph = agent(event["provider"], event["model"])
    try:
        with st.spinner("Recording the decision and drafting messages to the buyer and seller..."):
            event["state"] = resume(graph, event["thread"], decision)
    except RateLimitError as e:
        st.error(f"API quota reached: {e}. The decision was not recorded; try again later.")
        return False
    except LLMError as e:
        st.error(f"The LLM call failed: {e}. The decision was not recorded.")
        return False
    return True


@st.dialog("Override the recommendation")
def override_dialog(event: dict) -> None:
    rec = event["state"]["recommendation"]
    default_outcome = rec.get("outcome") or "decline"
    outcome = st.selectbox("Outcome", OUTCOMES, index=OUTCOMES.index(default_outcome), format_func=outcome_label)
    pct = st.number_input("Partial refund %", 5, 100, int(rec.get("partial_refund_percent") or 20), step=5,
                          disabled=outcome != "partial_refund")
    note = st.text_area("Why are you overriding? (required)", placeholder="e.g. the photos show the scratch was in the listing")
    if st.button("Record the override", type="primary"):
        if not note.strip():
            st.error("Add a note explaining the override.")
            return
        decision = {"action": "override", "outcome": outcome, "note": note, "staff": st.session_state.get("staff_name", "")}
        if outcome == "partial_refund":
            decision["partial_refund_percent"] = int(pct)
        if record_decision(event, decision):
            st.rerun()


# ------------------------------------------------------------ review: render

def run_case(event: dict, case: DisputeCase) -> None:
    llm, graph = agent(event["provider"], event["model"])
    thread = new_thread(event["case_id"])
    try:
        with st.status("Reviewing the case...", expanded=True) as status:
            for _, update in stream_to_review(graph, case, thread):
                for t in update.get("trace", []):
                    st.write(f"✓ **{t['step']}**: {t['summary']}")
            status.update(label="Review done: my recommendation is below", state="complete", expanded=False)
    except RateLimitError as e:
        event.update(status="error", error=f"API quota reached: {e}. Try again later or switch provider in the sidebar.")
        return
    except LLMError as e:
        event.update(status="error", error=f"The LLM call failed: {e}")
        return
    state = current_state(graph, thread)
    # Which model actually answered: the fallback may have stepped in.
    state["judged_by"] = f"{llm.name} · {llm.model}" + (" (fallback)" if getattr(llm, "using_backup", False) else "")
    event.update(status="done", thread=thread, state=state)
    st.rerun()  # redraw as a finished review, without the live progress box


def decision_buttons(event: dict) -> None:
    rec = event["state"]["recommendation"]
    box = st.container(border=True)
    box.markdown("**Your decision.** Nothing is sent until you decide; the messages to the buyer and seller are drafted after.")
    cols = box.columns([1, 1, 3])
    approve = cols[0].button("✅ Approve", type="primary", key=f"approve-{event['id']}",
                             disabled=not rec.get("outcome"), width="stretch",
                             help=None if rec.get("outcome") else "There is no recommended outcome to approve: override instead.")
    if cols[1].button("✏️ Override", key=f"override-{event['id']}", width="stretch"):
        override_dialog(event)
    if approve:
        decision = {"action": "approve", "note": "", "staff": st.session_state.get("staff_name", "")}
        if rec.get("outcome") == "partial_refund":
            decision["partial_refund_percent"] = int(rec.get("partial_refund_percent") or 0)
        if record_decision(event, decision):
            st.rerun()


def show_decided(event: dict) -> None:
    state = event["state"]
    dec = state["decision"]
    pct = f" ({dec['partial_refund_percent']}%)" if dec.get("final_outcome") == "partial_refund" and dec.get("partial_refund_percent") else ""
    with st.chat_message("staff", avatar=AVATARS["staff"]):
        verb = "✅ **Approved**" if dec["action"] == "approve" else "✏️ **Overridden**"
        st.markdown(f"{verb}: {outcome_label(dec['final_outcome'])}{pct}" + (f"  \n_{dec['note']}_" if dec.get("note") else ""))
    msgs = state.get("messages")
    if msgs:
        with st.chat_message("agent", avatar=AVATARS["agent"]):
            st.markdown("Decision recorded. Here are draft messages; edit them before sending.")
            buyer, seller = st.tabs(["To the buyer", "To the seller"])
            buyer.text_area("To the buyer", msgs["buyer_message"], height=200, label_visibility="collapsed", key=f"buyer-{event['id']}")
            seller.text_area("To the seller", msgs["seller_message"], height=200, label_visibility="collapsed", key=f"seller-{event['id']}")


def show_case_event(event: dict) -> None:
    cases = all_cases()
    case = DisputeCase.model_validate(cases[event["case_id"]])
    with st.chat_message("staff", avatar=AVATARS["staff"]):
        st.markdown(f"Review case **{event['case_id']}**")
    with st.chat_message("case", avatar=AVATARS["case"]):
        case_card(case)
    with st.chat_message("agent", avatar=AVATARS["agent"]):
        if event["status"] == "pending":
            run_case(event, case)
        if event["status"] == "error":
            st.error(event["error"])
            if st.button("Try again", key=f"retry-{event['id']}"):
                event["status"] = "pending"
                st.rerun()
            return
        show_steps(event["state"])
        show_recommendation(event["state"])
        show_working(event["state"])
        if not event["state"].get("decision"):
            decision_buttons(event)
    if event["state"].get("decision"):
        show_decided(event)


def show_search_event(event: dict, provider: str, model: str | None) -> None:
    with st.chat_message("staff", avatar=AVATARS["staff"]):
        st.markdown(event["query"])
    with st.chat_message("agent", avatar=AVATARS["agent"]):
        hits = event["matches"]
        if not hits:
            st.markdown(f"No case matches **{event['query']}**. Type a case ID such as `S01` or `G042`, "
                        "a word from the listing (e.g. `iphone`), or use **📂 Select a case** below.")
            return
        shown = hits[:6]
        more = f" (showing the first {len(shown)}; add words to narrow it down)" if len(hits) > len(shown) else ""
        st.markdown(f"{len(hits)} case{'s' if len(hits) != 1 else ''} match **{event['query']}**{more}. Which one should I review?")
        for cid in shown:
            st.button(case_label(cid), key=f"pick-{event['id']}-{cid}", on_click=queue_case, args=(cid, provider, model))


def welcome_review(provider: str, model: str | None) -> None:
    with st.chat_message("agent", avatar=AVATARS["agent"]):
        st.markdown(
            "Hi! I review **'not as described'** disputes. I check the order against Carousell's Buyer Protection rules, "
            "compare what the listing promised with what the buyer reports, find the policy that applies, and recommend "
            "an outcome with the clauses behind it. **You make the final call.**"
        )
        st.markdown("Pick a case with **📂 Select a case** below, type a case ID or a word from the listing, "
                    "or start with one of the demo cases:")
        for cid in case_ids_for("demo"):
            st.button(case_label(cid), key=f"demo-{cid}", on_click=queue_case, args=(cid, provider, model))


def review_bar(provider: str, model: str | None) -> None:
    with st.bottom:
        with st.container(horizontal=True, vertical_alignment="center"):
            with st.popover("📂 Select a case"):
                split = st.segmented_control("Case set", ["demo", "dev", "test", "all"], default="demo", help=SPLIT_HELP,
                                             key="pick_split")
                ids = case_ids_for(split or "demo")
                cid = st.selectbox("Case", ids, format_func=case_label, key="pick_case")
                st.button("Review this case", type="primary", disabled=not cid, on_click=queue_case,
                          args=(cid, provider, model), width="stretch")
            st.chat_input("Type a case ID (e.g. S01) or words from the listing (e.g. iphone)", key="review_chat",
                          on_submit=on_review_chat, args=(provider, model))
            if st.session_state.get("review_events"):
                st.button("🗑️", help="Clear the conversation", on_click=clear_review)


def page_review(provider: str, model: str | None) -> None:
    st.title("Review a dispute")
    staff_settings()
    review_bar(provider, model)
    events = st.session_state.setdefault("review_events", [])
    # Its own slot, emptied once a review starts, so the welcome does not linger
    # (greyed out) while the agent runs.
    welcome = st.empty()
    if not events:
        with welcome.container():
            welcome_review(provider, model)
    for event in events:
        if event["kind"] == "case":
            show_case_event(event)
        else:
            show_search_event(event, provider, model)


# ----------------------------------------------------------------- what-if

def queue_whatif(rule: str, provider: str, model: str | None) -> None:
    rule = rule.strip()
    if not rule:
        return
    st.session_state.setdefault("whatif_events", []).append({
        "id": next_id(), "rule": rule, "split": st.session_state.get("wi_split") or "dev",
        "limit": st.session_state.get("wi_limit", 10), "provider": provider, "model": model, "status": "pending",
    })


def on_whatif_chat(provider: str, model: str | None) -> None:
    queue_whatif(st.session_state.get("whatif_chat") or "", provider, model)


def run_whatif_event(event: dict) -> None:
    from dispute_agent.evaluation.harness import QuotaExhausted
    from dispute_agent.evaluation.whatif import run_whatif

    bar = st.progress(0.0, text="Re-judging past cases with the rule in force...")
    done: list[str] = []
    def progress(msg: str) -> None:
        done.append(msg)
        bar.progress(min(len(done) / event["limit"], 1.0), text=msg)
    try:
        llm, _ = agent(event["provider"], event["model"])
        _, result = run_whatif(event["rule"], split=event["split"], limit=event["limit"], llm=llm, progress=progress)
    except QuotaExhausted as e:
        event.update(status="error", error=f"API quota reached after {e.done} cases. Try again later.")
        return
    except LLMError as e:
        event.update(status="error", error=f"The LLM call failed: {e}")
        return
    finally:
        bar.empty()
    event.update(status="done", result=result)


def show_whatif_result(result: dict) -> None:
    s = result["summary"]
    before, after = s["buyer_win_rate_before"] or 0, s["buyer_win_rate_after"] or 0
    st.markdown(f"With this rule in force, **{s['flipped']} of {s['cases']}** past cases would get a different outcome "
                f"({(s['flip_rate'] or 0):.0%}), and buyers would win **{after:.0%}** of them (now {before:.0%}).")
    m1, m2, _ = st.columns(3)
    m1.metric("Outcomes that flip", f"{s['flipped']} of {s['cases']}")
    change = round((after - before) * 100)
    m2.metric("Buyer wins", f"{after:.0%}", delta=f"{change:+d} pts" if change else None)
    if s["transitions"]:
        st.markdown("**What changes:** " + ", ".join(f"{k}: {v}" for k, v in s["transitions"].items()))
    with st.expander(f"Case by case ({len(result['rows'])})", expanded=bool(s["flipped"])):
        st.dataframe(
            [
                {"Case": r["case_id"], "Item": r["title"][:40], "Gaps": ", ".join(r["gaps"]), "Before": outcome_label(r["before"]),
                 "After": outcome_label(r["after"]), "Flipped": "yes" if r["flipped"] else "",
                 "Uses new rule": "yes" if r["uses_proposed_rule"] else ""}
                for r in result["rows"]
            ],
            hide_index=True,
            width="stretch",
        )
    st.caption(f"Judged by {s['model']}. A flip means the outcome differs from the current policy's outcome for that case.")


def welcome_whatif(provider: str, model: str | None) -> None:
    with st.chat_message("agent", avatar=AVATARS["agent"]):
        st.markdown(
            "Describe a **policy change** in plain English. I re-judge past disputes as if the rule were in force and "
            "show which outcomes would flip, so you can see its effect before it goes live."
        )
        st.caption("Each case costs one LLM call (plus two the first time a case is used). "
                   "Change the case set and number of cases with **⚙** below.")
        st.markdown("Try one of these:")
        for i, rule in enumerate(WHATIF_EXAMPLES):
            st.button(rule, key=f"wi-example-{i}", on_click=queue_whatif, args=(rule, provider, model))


def whatif_bar(provider: str, model: str | None) -> None:
    st.session_state.setdefault("wi_split", "dev")
    st.session_state.setdefault("wi_limit", 10)
    with st.bottom:
        with st.container(horizontal=True, vertical_alignment="center"):
            with st.popover(f"⚙ {st.session_state.wi_split} · {st.session_state.wi_limit} cases"):
                st.selectbox("Past cases from", ["dev", "seed", "all"], key="wi_split")
                st.slider("Maximum cases", 3, 60, key="wi_limit")
            st.chat_input("Describe a proposed rule change...", key="whatif_chat", on_submit=on_whatif_chat,
                          args=(provider, model))
            if st.session_state.get("whatif_events"):
                st.button("🗑️", help="Clear the conversation", on_click=lambda: st.session_state.update(whatif_events=[]))


def page_whatif(provider: str, model: str | None) -> None:
    st.title("What-if policy test")
    whatif_bar(provider, model)
    events = st.session_state.setdefault("whatif_events", [])
    welcome = st.empty()  # see page_review
    if not events:
        with welcome.container():
            welcome_whatif(provider, model)
    for event in events:
        with st.chat_message("staff", avatar=AVATARS["staff"]):
            st.markdown(event["rule"])
            st.caption(f"{event['split']} cases · up to {event['limit']}")
        with st.chat_message("agent", avatar=AVATARS["agent"]):
            if event["status"] == "pending":
                run_whatif_event(event)
            if event["status"] == "error":
                st.error(event["error"])
                if st.button("Try again", key=f"wi-retry-{event['id']}"):
                    event["status"] = "pending"
                    st.rerun()
                continue
            show_whatif_result(event["result"])


# ------------------------------------------------------------- other pages

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
        "can call the `search_policy` tool and the graph loops back with the new clauses (a fallback: on the test "
        "set the per-gap searches always found the clauses). Code then checks the citations and confidence, and "
        "every recommendation pauses for a staff decision.\n\n"
        "The judge is Gemini (cloud, the default) or a local model through Ollama; "
        "`reports/model_comparison.md` compares them on the held-out test set. If a Gemini call fails, "
        "the app makes it with OpenAI instead (a fallback for availability, not part of the comparison)."
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
