"""Build Carousell_Dispute_Agent_Full_Report.docx from report_orig.docx for the 4 Nov 2026 changes.

build_report.py runs this with the right arguments. To run it by hand, from the repo root:
  uv run --no-project --with python-docx --with pillow python -I <this file> docs/report_build <findings.json> <output .docx>
The output must not be report_orig.docx: every build starts from it.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit("usage: update_report.py <report_build dir> <findings.json> <output .docx> (or run build_report.py)")
sys.path.insert(0, sys.argv[1])
from docx import Document  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Pt  # noqa: E402
from docx_helpers import (  # noqa: E402
    insert_paragraph_after, insert_table_after, keep_columns, para, remove, resize_rows, set_cell, set_row, set_runs,
    set_widths, stripe_rows, table_after, update_fields_on_open,
)

REPO = Path(".")
SRC = Path(sys.argv[1]) / "report_orig.docx"  # always start from the original (commit 48bcbba)
OUT = Path(sys.argv[3])
if OUT.resolve() == SRC.resolve():
    sys.exit(f"refusing to save over {SRC}: every build starts from it, so give another output path")
F = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))  # findings and numbers written after the runs
FIGURE = REPO / "docs/figures/agent_workflow.png"
N_TESTS = 76  # uv run pytest

doc = Document(SRC)


def lead(text, sep=". "):
    """Bold lead-in up to the first sep, the rest plain (the report's bullet style)."""
    i = text.index(sep) + len(sep.rstrip())
    return [(text[:i], True), (text[i:], False)]


def plain(text):
    return [(text, False)]

H1 = para(doc, "1. Summary", "Heading 1")
H2 = para(doc, "Our verdict on the business case", "Heading 2")
NORMAL = para(doc, "We built a working AI agent")
BULLET = para(doc, "Condition is subjective.", "List Bullet")
SPACER = doc.paragraphs[71] if doc.paragraphs[71].text == "" else None

# ------------------------------------------------------------- contents page
toc = [p for p in doc.paragraphs if p.style.name in ("toc 1", "toc 2")]
first = toc[0]
for p in toc[1:]:
    remove(p)
# Replace the static list with a real TOC field; Word fills it in (render step updates it).
p = first._p
for child in list(p):
    if child.tag != qn("w:pPr"):
        p.remove(child)
fld = p.makeelement(qn("w:fldSimple"), {qn("w:instr"): 'TOC \\o "1-2" \\h \\z \\u'})
r = fld.makeelement(qn("w:r"), {})
t = r.makeelement(qn("w:t"), {})
t.text = "Right-click and choose Update Field to refresh the contents."
r.append(t)
fld.append(r)
p.append(fld)
update_fields_on_open(doc)

# ----------------------------------------------------------------- summary
set_runs(NORMAL, "We built a working AI agent that helps Carousell Singapore’s support team decide buyer–seller disputes where the buyer says a second-hand item is “significantly not as described”. The agent reads the listing, the order, the buyer’s complaint, the seller’s reply and the chat. It checks the fixed rules in plain code, finds the relevant clauses of Carousell’s Buyer Protection policy with retrieval-augmented generation (RAG), can search the policy again through a tool if those clauses are not enough (a fallback the test set never needed), and recommends one of Carousell’s four outcomes with reasons and clause citations. A staff member always approves or overrides it. We compared judge models (Gemini in the cloud, Llama and Qwen running locally) and other retrieval designs, and the team labelled the test set by hand; section 8.5 has the results and our choice.")
t = table_after(doc, "We built a working AI agent")
set_cell(t, 3, 1, "A LangGraph agent (Python) with plain-code eligibility rules, an LLM for claim matching and judgement, hybrid policy search (ChromaDB + BM25), a search_policy tool the judge can call, a code check on confidence and citations, a pause for a staff decision, message drafts, a what-if policy test and a Streamlit app. The judge can be Gemini (cloud) or a local model through Ollama; in the cloud app OpenAI takes over when a Gemini call fails.")
set_cell(t, 4, 1, F["summary_does_it_work"])
set_cell(t, 6, 1, "Two people label the test set by hand; spot-check the citation sheet; deploy to Streamlit Cloud (manual, steps in the README); fill in the contribution table; confirm the deadline; record the video; check two business figures by hand.")
resize_rows(t, 8)
set_row(t, 7, ["Which model?", F["summary_which_model"]])
# The new row copied "What is left?"; move it above that row.
rows = t._tbl.findall(qn("w:tr"))
rows[6].addprevious(rows[7])

v = para(doc, "It has four weak spots worth fixing before the video")
bullets = [para(doc, "80% of the value rests"), para(doc, "There is no cost side"), para(doc, "Two figures still need"), para(doc, "The slides and video script do not mention")]
set_runs(bullets[3], lead("The slides and video script still do not mention the business value. The S$400,000 line should go into the video (not changed on 4 November because the group has not agreed it)."))

# -------------------------------------------------- 2. assignment criteria
p2 = para(doc, "BC3415 group assignment:")
t = table_after(doc, "BC3415 group assignment:")
set_row(t, 0, ["Criterion (weight)", "How the project meets it", "Where to look"])
set_row(t, 1, ["Problem relevance and originality (15%)", None, None])
set_row(t, 2, ["Technical design and implementation (20%)",
               f"Real retrieval over a vector database (ChromaDB) plus BM25; a LangGraph graph with conditional routing, a tool loop (search_policy) and a human-approval pause; rules in code where rules are exact; structured JSON output from three providers; Streamlit app deployed on Community Cloud; {N_TESTS} offline tests; resumable jobs.", "Sections 5 and 6"])
set_row(t, 3, ["Effectiveness of the AI / agent (25%)",
               "Held-out test set of 50 cases against a single-prompt baseline, for three judge models; grounded answers (citations checked by code), tool use, and a fallback (escalation to a person with follow-up questions). Honest about the tie on judgement with the strongest model.", "Section 8"])
set_row(t, 4, ["Creativity and RAG / GenAI integration (20%)",
               "Each claim gap becomes its own retrieval query; the judge can search again; citations are checked by code; ablations show what retrieval adds (no retrieval, agent-driven retrieval); a what-if test re-judges past disputes under a proposed rule; synthetic disputes generated on real listings by a different model from the judge.", "Sections 5.2, 6.3, 7.1, 8.5 and 8.6"])
set_row(t, 5, ["Collaboration and division of work (20%)",
               "Six roles defined (C1–C4 coders, B1–B2 business). A contribution table template is ready in the README and section 12.3; the team fills in names and evidence. The commit history shows one author because the code was pushed from one machine.", "Section 12"])
set_runs(para(doc, "The assignment also asks for"), "The rubric weights above are from the marking scheme (GradingCriteria.jpg in the repo). The assignment also asks for “business value” and the module’s model projects include a financial-impact section (for example UpSkill Lens for Udemy). Section 9 covers this.")

# --------------------------------------------------------- 3. timeline
t = table_after(doc, "We went through three ideas")
for i, row in enumerate(t.rows):
    if "written before it knew about the build" in row.cells[1].text:
        set_cell(t, i, 1, "Project Report for slides and video (written before the prototype was built)")
    if "test run 2: agent 88%, baseline 86%" in row.cells[2].text:
        set_cell(t, i, 2, "Test run 1: agent 82%, baseline 84%. Decision guide fixed on dev cases; test run 2: agent 88%, baseline 90% (both against the later hand labels)")
resize_rows(t, len(t.rows) + 1)
set_row(t, len(t.rows) - 1, ["4 Nov", "Professor asked us to compare models. Added the search_policy tool, Ollama and OpenAI providers, the model comparison and retrieval ablations; app made ready for Streamlit Cloud", F["timeline_outcome"]])
resize_rows(t, len(t.rows) + 1)
set_row(t, len(t.rows) - 1, ["4–5 Nov", "OpenAI gpt-5.4-mini added as the cloud app's fallback when a Gemini call fails. Planned as a fourth judge, then dropped from the comparison: the key stays unpaid (about 50 requests a day)", F["timeline_openai"]])
resize_rows(t, len(t.rows) + 1)
set_row(t, len(t.rows) - 1, ["6 Nov", "App deployed on Streamlit Community Cloud. The review and what-if pages became a guided chat, and the evaluation page a summary for non-technical readers. The slide deck was dropped: the video shows the app itself", "Live at bc3415-carousell-dispute-agent.streamlit.app"])

# ----------------------------------------------------------- 5. solution
fig_par = [p for p in doc.paragraphs if p._p.xpath(".//w:drawing")][0]
blip = fig_par._p.xpath(".//a:blip")[0]
rid = blip.get(qn("r:embed"))
doc.part.related_parts[rid]._blob = FIGURE.read_bytes()
from PIL import Image  # noqa: E402

w, h = Image.open(FIGURE).size
shape = doc.inline_shapes[0]
shape.height = int(shape.width * h / w)
set_runs(para(doc, "Figure 1. The agent workflow."), "Figure 1. The agent workflow. Exact rules run in code; judgement goes to the LLM, which can call the search_policy tool for more policy; the workflow pauses until a person decides.")

t = table_after(doc, "5.1 The steps")
set_cell(t, 6, 2, "Judges each gap as significant, not significant or unclear; recommends an outcome, a partial-refund %, a confidence score, reasons, clause citations and follow-up questions. If the clauses do not cover a gap it calls search_policy with up to 2 queries; code runs the search and the graph returns to the judge once with the new clauses")
set_cell(t, 7, 2, "Drops citations to clauses that were not retrieved and escalates if: confidence < 0.7 (checked against costs in section 9.7), no valid citation, more evidence needed, a gap is unclear, the outcome contradicts the gap assessment, or the judge still wants policy the tool could not find")

b = para(doc, "Mock mode. Without an API key")
insert_paragraph_after(b, BULLET, lead("Choice of judge model. The same agent runs on Gemini (cloud, free tier) or a local model through Ollama (nothing leaves the machine). In the app, OpenAI takes over when a Gemini call fails (an unpaid key on OpenAI’s free usage tier, about 50 requests a day), and the recommendation is marked as a fallback answer. The app lists only the providers that can run where it is opened."))
b = para(doc, "Rules in code, judgement in the LLM.")
set_runs(b, lead("Rules in code, judgement in the LLM. Payment method, dates and tracking are exact, so code gets them right every time and costs nothing. This is where the agent beats the baseline most clearly (100% vs 68% eligibility with Gemini)."))
b = para(doc, "Every recommendation cites a clause")
insert_paragraph_after(b, BULLET, lead(F["design_tool_bullet"]))

# ------------------------------------------------------- 6. technical
t = table_after(doc, "6.1 Tech stack")
set_row(t, 1, [None, "LangGraph (StateGraph, conditional edges for the tool loop, interrupt, in-memory checkpointer)", None])
set_row(t, 2, [None, "Gemini API (free tier, google-genai), Ollama (local Llama 3.1 8B and Qwen 3 8B), OpenAI (gpt-5.4-mini, free usage tier; only the app's fallback); Pydantic schemas; temperature 0 where the model allows it", None])
set_row(t, 5, [None, "uv (Python 3.12, uv.lock), optional Docker, deployed on Streamlit Community Cloud (bc3415-carousell-dispute-agent.streamlit.app; redeploys on every push), GitHub", None])
t = table_after(doc, "6.2 Models")
resize_rows(t, 6)
set_row(t, 5, ["Dispute generator", "gemma-4-26b-a4b-it, gemini-3-flash-preview and gemini-3.5-flash", "Different from every judge, so no model grades its own writing. 154 disputes were written by Gemma 4, 19 by gemini-3-flash-preview and 7 by gemini-3.5-flash (each used as the previous one’s free quota ran out)"])
set_row(t, 1, ["Judge (default, cloud)", "gemini-flash-lite-latest", F["model_row_gemini"]])
set_row(t, 2, ["Judge (local, compared)", "llama3.1:8b via Ollama", F["model_row_llama"]])
set_row(t, 3, ["Judge (local, compared)", "qwen3:8b via Ollama (thinking off)", F["model_row_qwen"]])
set_row(t, 4, ["Fallback (cloud app only)", "gpt-5.4-mini (OpenAI), low reasoning effort", F["model_row_openai"]])
p = para(doc, "Calls are paced (at least 4.5 seconds apart).")
set_runs(p, "Gemini calls are paced (at least 4.5 seconds apart). Short rate-limit waits are retried; if the daily quota runs out, long jobs stop with exit code 75 and resume where they stopped. wait-for-quota waits until the quota is back. Local models need no pacing; a prompt that would not fit the model’s context window is refused rather than silently cut.")
insert_paragraph_after(p, NORMAL, [("Hardware. ", True), (F["hardware"], False)])

b = para(doc, "Why hybrid:")
set_runs(b, lead("Why hybrid: on 25 test queries it puts the right clause first 76% of the time, against 52% for either method alone, and has the best mean reciprocal rank (0.81, against 0.67 for embeddings and 0.71 for keywords). Within the top 3 that the agent uses, keyword search alone finds slightly more (92% against 88%). That is one query: for non-receipt by untracked mail, rank fusion pushes the answer to fourth place, and the agent decides that case with an eligibility rule in code anyway (reports/retrieval.md explains it). Hybrid finds the most within the top 5 (96%). Section 8.6 tests whether retrieval changes the decisions, not just the citations.", ": "))

t = table_after(doc, "6.4 Code layout")
set_row(t, 1, [None, "Staff app: review a dispute as a guided chat (pick or type a case; recommendation with cited clauses and the judge’s tool calls; approve or override; message drafts), what-if policy test (type a rule), evaluation summary, policy library, how it works. AI model picker in the sidebar", ])
set_row(t, 2, [None, "LangGraph graph with the search_policy tool loop, eligibility rules, prompts and decision guide, runner, photo interface"])
set_row(t, 4, [None, "Gemini, Ollama and OpenAI clients, mock provider, model fallback, rate-limit handling, token counts"])
set_row(t, 6, [None, "Harness, metrics, report writer, model comparison, retrieval evaluation, what-if, cost check of the escalation threshold"])
set_row(t, 7, [None, "Command line: run-case, evaluate (with --provider, --model, --retrieval), compare, eval-retrieval, whatif, review-cost, generate, split, export-labels, agreement, check-llm, wait-for-quota"])
set_row(t, 9, [None, "Evaluation reports (Markdown and JSON), the model comparison, the escalation-threshold cost check and citation-check sheets"])
set_row(t, 11, [None, f"{N_TESTS} pytest tests that run offline (mock LLM; Ollama and OpenAI calls answered by fakes)"])
for i, row in enumerate(t.rows):
    if row.cells[0].text.strip() == "presentation/":
        set_row(t, i, [None, "VIDEO_SCRIPT.md, the demo video script"])

p = para(doc, "3.  Put a free Gemini key")
insert_paragraph_after(p, p, "4.  Optional: install Ollama and run ollama pull llama3.1:8b (the default local model) to use it; choose it in the app’s sidebar or pass --provider ollama. Add OPENAI_API_KEY to .env to enable the OpenAI fallback (an unpaid key on the free usage tier is enough).")
set_runs(para(doc, "4.  Start the app with"), "5.  Start the app with uv run streamlit run app/streamlit_app.py, or run one case with uv run dispute-agent run-case S01.")
set_runs(para(doc, "5.  Run the tests with"), f"6.  Run the tests with uv run pytest ({N_TESTS} tests, no network needed).")

# ------------------------------------------------------- 7. data
set_runs(para(doc, "Provisional labels are the outcomes"), "Labels: the outcome each case was written for is its provisional label. For the 50 test cases the team labelled each case by hand on 4 November (B1 25 cases, B2 the other 25; final_outcome in data/labels/labels.csv), and every result below uses those hand labels. They differ from the provisional labels on two cases: G134 (decline instead of a partial refund) and G147 (a partial refund instead of a decline).")
set_runs(para(doc, "Human labels: B1 and B2 each label"), "Labelling guide: docs/labelling_guide.md. Each test case was labelled by one person, so there is no agreement score between labellers; uv run dispute-agent agreement reports it once some cases are labelled by both.")
set_runs(para(doc, "AI reviewer: Claude"), "AI reviewer: Claude (separate from every judge model) also labelled the 50 test cases in its own claude_* columns. It agrees with the hand labels on 47 of 50 (Cohen’s kappa 0.90); the differences are G059, G129 and G147, all judgement calls. These columns never replace the human labels.")
b = para(doc, "Generator and judge are different models")
set_runs(b, "Generator and judge are different models (true for all three judges compared), so no model grades its own writing.")

# ------------------------------------------------------- 8. evaluation
p = para(doc, "The agent is compared with a single-prompt baseline")
set_runs(p, "The agent is compared with a single-prompt baseline: one LLM call with the whole policy pasted in, the same decision guide, and the case with its timeline, but no rules in code, no retrieval and no agent steps. Both use the same judge model at temperature 0, and the comparison is repeated for each judge model (section 8.5). A case where the model gives no valid answer counts as wrong.")
h = para(doc, "8.2 Headline results", "Heading 2")
set_runs(h, "8.2 Headline results (test set, 50 cases, Gemini, run cmp_gemini-flash-lite)")
t = table_after(doc, "8.2 Headline results")
G = F["gemini"]
for i, (label, a, b_) in enumerate(G["headline_rows"], start=1):
    set_row(t, i, [label, a, b_])
set_runs(para(doc, "How to read this."), lead(F["how_to_read"]))

t = table_after(doc, "8.3 Where the agent went wrong")
resize_rows(t, 1 + len(G["wrong"]))
for i, row in enumerate(G["wrong"], start=1):
    set_row(t, i, row)
set_runs(para(doc, "G059, G129, G134 and G147 are the cases"), "G059, G129, G134 and G147 are the cases where reasonable people could disagree, and three of them are among the agent’s mistakes. On G129 and G147 the labeller chose a partial refund and the agent declined; the AI reviewer sided with the agent on all three, which is why we score only against the human labels. G155, wrong in the previous run, was right this time (and escalated both times).")

t = table_after(doc, "8.4 Other results")
set_row(t, 1, [None, "Agent 100%, baseline 80% on the 20 hand-written cases (28 Oct; the 4 that are also test cases are scored against the hand labels, the other 16 against the outcomes they were written for). Not held out: these cases were used while writing the prompts"])
set_row(t, 3, ["Citation check (by a person)", "60 of the agent’s 68 citations (88%) support the decision, just under the 90% target: 41 of 42 on refunds but 19 of 26 on declines, which sometimes cite the wrong exclusion (BPR-03 instead of BPR-04). The AI reviewer agreed on 67 of 68"])
resize_rows(t, 6)
set_row(t, 5, ["search_policy tool (default design)", F["tool_use_row"]])

# 8.5 model comparison and 8.6 retrieval design, inserted before the old 8.5
old85 = para(doc, "8.5 The decision-guide fix", "Heading 2")
anchor = old85._p.getprevious()
from docx.text.paragraph import Paragraph  # noqa: E402
from docx.table import Table  # noqa: E402

anchor_item = Paragraph(anchor, H2._parent) if anchor.tag == qn("w:p") else Table(anchor, H2._parent)
h85 = insert_paragraph_after(anchor_item, H2, "8.5 Model comparison: which LLM should judge?")
cur = insert_paragraph_after(h85, NORMAL, F["comparison_intro"])
template3 = table_after(doc, "8.4 Other results")  # 2 columns
template_hdr = table_after(doc, "8.3 Where the agent went wrong")  # 4 columns
template5 = table_after(doc, "The slides (presentation")  # 5 columns (section 11 is renamed further down)


def _tpl(rows):
    return template5 if len(rows[0]) == 5 else template_hdr
cur = insert_table_after(cur, _tpl(F["comparison_table"]), F["comparison_table"])
set_widths(cur, [1.75, 1.45, 1.45, 1.85])
cur = insert_paragraph_after(cur, NORMAL, "")
cur = insert_paragraph_after(cur, NORMAL, [("What we found. ", True), (F["comparison_found"], False)])
for line in F["comparison_bullets"]:
    cur = insert_paragraph_after(cur, BULLET, plain(line))
cur = insert_paragraph_after(cur, NORMAL, [("Our choice and why. ", True), (F["comparison_choice"], False)])
cur = insert_paragraph_after(cur, NORMAL, [("Hardware limits. ", True), (F["comparison_hardware"], False)])
h86 = insert_paragraph_after(cur, H2, "8.6 Retrieval design: per gap, agent-driven, or none")
cur = insert_paragraph_after(h86, NORMAL, F["retrieval_intro"])
cur = insert_table_after(cur, _tpl(F["retrieval_table"]), F["retrieval_table"])
set_widths(cur, [1.75, 0.95, 0.95, 2.85])
cur = insert_paragraph_after(cur, NORMAL, "")
cur = insert_paragraph_after(cur, NORMAL, [("What we found. ", True), (F["retrieval_found"], False)])
cur = insert_paragraph_after(cur, NORMAL, [("Without the policy in the prompt. ", True), (F["rubric_intro"], False)])
cur = insert_table_after(cur, _tpl(F["rubric_table"]), F["rubric_table"])
set_widths(cur, [2.2, 1.2, 1.2, 1.9])
cur = insert_paragraph_after(cur, NORMAL, "")
cur = insert_paragraph_after(cur, NORMAL, [("What we found. ", True), (F["rubric_found"], False)])

set_runs(old85, "8.7 The decision-guide fix, and how often the test set was used")
set_runs(para(doc, "The first test run gave agent 82%"), "The first test run gave agent 82%, baseline 84%. Both systems declined every small undisclosed flaw on items listed as new or like new, because two lines of our decision guide contradicted each other. We clarified the rule (a small specific flaw on a new or like-new item is a partial refund) and checked it on dev cases only: agent 81% → 89%, baseline 78% → 81% on 36 borderline dev cases. Then we re-ran the test set (agent 88%, baseline 90%: the fix helped both). On 4 November we added the search tool and ran the test set once per judge model; the team then labelled the test set by hand, and against those labels Gemini’s agent gets 90% and the baseline 88%. Every test-set number in this report, the early runs included, uses the hand labels; the dev cases were not labelled by hand, so the dev numbers use the outcomes the cases were written for. Nothing was tuned on the test set, but it has now been used three times and the default local model was picked from these results, so its numbers are slightly optimistic. All runs are in reports/.")
set_runs(para(doc, "8.6 Limits of the evaluation", "Heading 2"), "8.8 Limits of the evaluation")
set_runs(para(doc, "Labels are still provisional"), plain("Each test case was hand-labelled by one person, after the runs; there is no agreement score between labellers yet."))
b = para(doc, "LLM answers vary between runs")
set_runs(b, "LLM answers vary between runs even at temperature 0: G155 was a partial refund in the first test run, a full refund with return in the second, and a decline in the 4 Nov run and in the demo checks on 28 Oct and 4 Nov.")
insert_paragraph_after(b, BULLET, plain("The local models were limited to 8B parameters by an 8 GB GPU; larger open models might close the gap with Gemini."))

# ------------------------------------------------------------ 10. risks
t = table_after(doc, "10. Risks, ethics and limitations")
set_row(t, 1, [None, None, None, F["risk_invented"]])
set_row(t, 2, [None, None, None, "With Gemini the agent leans to decline: 83% of buyer wins vs 96% of seller wins; the baseline the reverse (81% of seller wins). The local 8B models refund almost everything"])
set_row(t, 3, [None, None, None, "6% escalated, including 2 of 5 wrong answers (Gemini). Section 9.7 checks the 0.7 threshold against staff and mistake costs"])
set_row(t, 4, [None, None, "Different models write and judge; people wrote 20 hard cases; the test set is labelled by hand; said openly", "Hand labels for all 50 test cases (one labeller per case)"])
set_row(t, 5, [None, None, "Only public or made-up data. A deployment would remove personal details and use a paid tier or a local model (free-tier prompts may be used by Google)", "Local models keep case data on the machine"])
set_row(t, 6, [None, None, None, "G155 changed between runs (escalated every time)"])
resize_rows(t, len(t.rows) + 1)
set_row(t, len(t.rows) - 1, ["Model dependence", "A weaker or different model may judge very differently", "Model comparison on the same test set; the provider is a setting, so the model can be changed and re-tested", F["risk_model"]])
set_runs(para(doc, "Recommendation to Carousell (as in the video)"), lead(F["recommendation"], ": "))

# -------------------------------------------------------- 11. video
set_runs(para(doc, "11. Slides and video", "Heading 1"), "11. Video")
set_runs(para(doc, "The slides (presentation/Carousell_Dispute_Agent_Slides.pptx"), "The video script (presentation/VIDEO_SCRIPT.md) gives all six members a part; the target is about 4:55, inside the 3 to 5 minutes allowed. There are no slides: the video records the live app, whose How it works, Policy library and Evaluation results pages show the workflow, the search and the results, and each speaker appears on camera, with text cards added in editing where no page fits.")
t = table_after(doc, "The video script (presentation")
set_cell(t, 0, 3, "On screen")
slide_rows = [
    ["The problem", "0:00–0:50", "B1", "On camera, text cards", "Scams on Carousell, the ‘Buy’ button, the judgement call (light pink vs rose pink)"],
    ["How it works", "0:50–1:25", "C1", "How it works page", "Workflow with the search tool; rules in code, judgement in the LLM"],
    ["The policy search", "1:25–1:40", "C2", "Policy library page", "37 clauses, a search per gap, why hybrid (right clause first 76% vs 52%)"],
    ["Live demo", "1:40–3:00", "C4", "Review and What-if pages", "S01 partial refund 15%; S16 not covered by rules; G155 escalated (confidence 0.5 in the 4 Nov demo check; 0.7 in the 4 Nov test run, escalated for other reasons); what-if test"],
    ["Does it work?", "3:00–3:55", "C3", "Evaluation results page", F["slides_eval_row"]],
    ["Risks", "3:55–4:20", "B2", "On camera", "Invented policy, bias, rubber-stamping, made-up data"],
    ["Recommendation", "4:20–4:50", "B1", "On camera, end card", "Staff-assist pilot; pilot KPIs; team; thank you"],
]
resize_rows(t, 1 + len(slide_rows), template_row=1)
for i, row in enumerate(slide_rows, start=1):
    set_row(t, i, row)
p = para(doc, "Demo backups:")
set_runs(p, "Demo backups: S02 (iPhone 64GB received as 16GB: full refund with return) and S10 (pilling the listing disclosed: decline). S01 and G155 were re-checked with Gemini on 4 November and still give the answers in the script. Before recording: check uv run dispute-agent check-llm, rehearse once, keep .env and the app's Secrets off screen. The decision-guide story (first run lost 82 to 84) moved to the Q&A notes to make room for the model comparison.")

tc = table_after(doc, "Suggested cost side")
set_cell(tc, 1, 2, "Measured on the 4 Nov test run: 1.8 LLM calls and about 2,250 input and 590 output tokens per case for claim matching and judgement; message drafts add one more call. The judge alias gemini-flash-lite-latest pointed to gemini-3.5-flash-lite (checked through the API on 5 Nov 2026). At Google’s paid-tier price for it (US$0.30 in / US$2.50 out per million tokens, Gemini API pricing page, 5 Nov 2026) that is about US$0.002 a case, still well under US$0.01 with the message drafts; on the free tier it costs nothing")
b = para(doc, "Measured: about 9 seconds")
set_runs(b, [("Measured:", True), (" about 9 seconds and 1.8 LLM calls per case; 6% of cases escalated; 94% accuracy on cases not escalated (Gemini, 4 Nov run, hand labels).", False)])

# ------------------------------------------------------- 12. status
b = para(doc, "Working agent, hybrid retrieval, what-if test")
set_runs(b, f"Working agent with the search_policy tool, hybrid retrieval, what-if test, evaluation harness, Streamlit app, CLI, {N_TESTS} offline tests, Docker files.")
b = para(doc, "Two test runs, seed run, dev runs")
set_runs(b, "Three test runs with Gemini; the model comparison with two local models (Llama 3.1 8B, Qwen 3 8B); retrieval and decision-guide ablations; seed run, dev runs and retrieval evaluation, all in reports/; a person’s check of all 68 citations (88% support the decision), with AI citation and label checks in separate columns; a cost check of the escalation threshold (section 9.7).")
b = para(doc, "GitHub repo linked on this machine (3 Nov).")
insert_paragraph_after(b, BULLET, plain("App deployed on Streamlit Community Cloud at bc3415-carousell-dispute-agent.streamlit.app (6 Nov): keys from Streamlit secrets, Gemini first with OpenAI (free usage tier) as a fallback."))
set_runs(para(doc, "Slides and video script"), "Video script for all six members (presentation/VIDEO_SCRIPT.md).")
t = table_after(doc, "12.2 What is left")
set_row(t, 1, [None, "Fill in the contribution table (README and section 12.3)", "All", "Needed for the collaboration criterion (20%)"])
set_row(t, 4, [None, "Settle disagreements, then re-run evaluate --split test (and the model comparison if time allows)", None, "One Gemini run uses about the whole free daily quota; local runs are free"])
set_row(t, 5, [None, None, None, "reports/citation_check_cmp_gemini-flash-lite.csv"])
set_row(t, 8, [None, "Deploy to Streamlit Community Cloud", "C4", "Manual; exact steps in the README. Key goes in Streamlit Secrets"])
set_row(t, 11, [None, "Re-check the README before submission", None, "Working notes were removed on 4 Nov"])

h = para(doc, "12.3 Team roles", "Heading 2")
set_runs(h, "12.3 Contribution table (template)")
t = table_after(doc, "12.3 Team roles") if False else table_after(doc, "12.3 Contribution table")
anchor = insert_paragraph_after(h, NORMAL, "Fill in one row per member. Evidence can be commits, files, documents or meeting notes. The same table is in the README.")
rows = [
    ["Member", "Role", "Main contributions", "Evidence", "In the video"],
    ["Ronak", "C1: Agent lead", "LangGraph workflow, tool loop, confidence check, staff pause; checked all 68 test-set citations by hand", "src/dispute_agent/agent/, reports/citation_audit_cmp_gemini-flash-lite.csv", "How it works"],
    ["Akshaya", "C2: RAG and policy", "Policy clauses, hybrid search, citations, retrieval evaluation", "src/dispute_agent/rag/, reports/retrieval.md", "Policy search"],
    ["Evelyn", "C3: Data and evaluation", "Listings, dispute generator, labels, harness, baseline, model comparison", "src/dispute_agent/data/, evaluation/, reports/", "Does it work?"],
    ["Jonathan", "C4: App and deployment", "Streamlit app, local models, cloud deployment, repo and README", "app/, src/dispute_agent/llm/, README.md", "Live demo"],
    ["Dan Yu", "B1: Business lead", "Problem, evidence, competitors, business case, recommendation", "Project Brief, Business Case", "Problem; recommendation"],
    ["Drue", "B2: Policy and story lead", "Policy corpus, hard cases, labelling, risks and ethics, video editing", "data/policy/, data/labels/, presentation/", "Risks; edits the video"],
]
five_col = table_after(doc, "The video script (presentation")  # 5 columns
contrib = insert_table_after(anchor, five_col, rows)
set_widths(contrib, [0.8, 1.35, 2.05, 1.5, 0.8])
remove(t)

# ------------------------------------------------------- appendix
t = table_after(doc, "Appendix A. Glossary")
set_row(t, 3, [None, "Large language model, here Google Gemini, Meta’s Llama 3.1 or Alibaba’s Qwen 3 (and OpenAI GPT-5.4 mini as the app’s fallback)"])
resize_rows(t, len(t.rows) + 4)
n = len(t.rows)
set_row(t, n - 4, ["Reject option", "Sending a case to a person instead of acting on the model’s answer; cost-sensitive when the cut-off weighs the cost of a careful review against the cost of a mistake (section 9.7)"])
set_row(t, n - 3, ["Tool call", "The LLM asks the program to run a function (here search_policy) and continues with the result"])
set_row(t, n - 2, ["Ollama", "Free software that runs open LLMs on your own computer"])
set_row(t, n - 1, ["Ablation", "Removing or changing one part of a system to measure what that part contributes"])
t = table_after(doc, "Appendix C. Where everything lives")
set_row(t, 4, [None, "reports/evaluation_cmp_gemini-flash-lite.md; model comparison in reports/model_comparison.md"])

# ---------------------------------------------------------------------------
# Standalone edition: written for a reader who has never seen the project.
# Internal notes (to-dos, "not yet agreed" boxes, self-assessments) are removed;
# the team's to-do list lives in NEXT_STEPS.md instead.
# ---------------------------------------------------------------------------
from docx.text.paragraph import Paragraph as _P  # noqa: E402


def _remove_from(first, stop):
    """Remove `first` and every element after it until a paragraph for which stop(p) is true."""
    el = first._p if hasattr(first, "_p") else first._tbl
    parent = el.getparent()
    while el is not None:
        nxt = el.getnext()
        parent.remove(el)
        el = nxt
        if el is None or (el.tag == qn("w:p") and stop(_P(el, H2._parent))):
            break


def _heading(prefix, level):
    return lambda p: p.style.name == f"Heading {level}" and p.text.startswith(prefix)


# Summary table: a status row instead of a to-do row
t = table_after(doc, "We built a working AI agent")
for i, row in enumerate(t.rows):
    if row.cells[0].text.startswith("What is left"):
        set_row(t, i, ["Status", f"Working prototype with {N_TESTS} offline tests, evaluated against the team’s hand labels with Gemini and two local models; deployed on Streamlit Community Cloud (bc3415-carousell-dispute-agent.streamlit.app) with Gemini first and OpenAI (free usage tier) as a fallback."])

# Summary: the business-case self-assessment
_remove_from(para(doc, "Our verdict on the business case", "Heading 2"), _heading("2. The assignment", 1))

# 2. Criteria table and note
t = table_after(doc, "BC3415 group assignment:")
set_row(t, 5, [None, "Six roles: four coders (C1–C4) and two business roles (B1–B2); section 12 lists who did what and where the evidence is.", None])
set_runs(para(doc, "The rubric weights above are from the marking scheme"),
         "The weights are from the assignment’s marking scheme. The assignment also asks for “business value”, and the module’s model projects include a financial-impact section (for example UpSkill Lens for Udemy). Section 9 covers this.")

# 3. Timeline: no notes about this document itself
t = table_after(doc, "We went through three ideas")
for i, row in enumerate(t.rows):
    if "Superseded by this report" in row.cells[2].text:
        set_cell(t, i, 2, "Replaced by this report")
    if "this full report written" in row.cells[1].text:
        set_row(t, i, [None, "Code published on GitHub; first full project report", "—"])

# 9. Business case
set_runs(para(doc, "This section restates the business case"),
         "This section sets out what the agent could be worth to Carousell in Singapore: the value formula, its inputs (each with a low, base and high value, marked as sourced, derived or assumed), the results, how we estimated Carousell’s transaction volume, and the costs, break-even point and caveats. Section 9.7 uses the same inputs to check the confidence threshold at which the agent escalates a dispute.")
h96 = para(doc, "9.6 Is the business case strong enough?", "Heading 2")
set_runs(h96, "9.6 Costs, break-even and caveats")
box = table_after(doc, "9.6 Costs, break-even and caveats")
remove(box)
set_runs(para(doc, "Verdict: yes, it is strong enough to present."),
         plain("Every input is sourced, derived or labelled as an assumption, and each has a range. The case still has three caveats:"))
weak = table_after(doc, "9.6 Costs, break-even and caveats")
resize_rows(weak, 4)
set_row(weak, 0, ["Caveat", "Why it matters", "What would firm it up"])
set_row(weak, 1, ["Most of the value is the trust term",
                  "The +1 point shift of deals onto ‘Buy’ is an assumption with no direct evidence",
                  "The break-even shift is only +0.06 points (below), so even a small trust effect covers the costs"])
set_row(weak, 2, ["Staff-time inputs are estimates",
                  "30–60 minutes per dispute comes from a vendor that sells chargeback automation; the 50% saving is assumed",
                  "A timing study with the prototype would measure both"])
set_row(weak, 3, ["Two figures come from search results",
                  "The 3.5–6% buyer fee and the rule that delivery orders must use ‘Buy’",
                  "Confirm both on Carousell’s own pages"])
set_runs(para(doc, "Suggested cost side", "Heading 3"), "Cost side")
set_runs(para(doc, "Numbers the prototype can now supply", "Heading 3"), "Measured by the prototype")
set_runs(para(doc, "Timing study (any group member"),
         [("Timing study:", True), (" a few people each decide 5 test cases from the case alone and 5 others with the agent’s recommendation and citations, timing each. The median time without the agent would replace the vendor’s 30–60 minutes, and the reduction would replace the assumed 50% saving. Students are not trained support staff, so this is only a first estimate.", False)])
_remove_from(para(doc, "Figures a group member could look for", "Heading 3"), _heading("10.", 1))

# 9.7 The escalation threshold, priced (reports/review_cost.md), at the end of section 9
h10 = para(doc, "10. Risks, ethics and limitations", "Heading 1")
prev = h10._p.getprevious()
prev = _P(prev, H2._parent) if prev.tag == qn("w:p") else Table(prev, H2._parent)
cur = insert_paragraph_after(prev, H2, "9.7 Is 0.7 the right escalation threshold?")
cur = insert_paragraph_after(cur, NORMAL, F["threshold_intro"])


def _body(rows):
    """Header row keeps the template's bold; body cells are plain (the template's last row may not be)."""
    return [rows[0]] + [[plain(c) for c in r] for r in rows[1:]]


def _band(table):
    """Alternate the row shading like the other tables: rows added by resize_rows all copy the last row's."""
    rows = table.rows
    for i in range(3, len(rows)):
        model = rows[1 if i % 2 else 2]
        for cell, src in zip(rows[i].cells, model.cells):
            cell._tc.remove(cell._tc.tcPr)
            cell._tc.insert(0, copy.deepcopy(src._tc.tcPr))


cur = insert_table_after(cur, _tpl(F["threshold_costs_table"]), _body(F["threshold_costs_table"]))
_band(cur)
set_widths(cur, [3.5, 1.0, 1.0, 1.0])
cur = insert_paragraph_after(cur, NORMAL, "")
cur = insert_paragraph_after(cur, NORMAL, F["threshold_costs_note"])
cur = insert_paragraph_after(cur, NORMAL, [("Cost per dispute by threshold. ", True), (F["threshold_table_note"], False)])
cur = insert_table_after(cur, _tpl(F["threshold_table"]), _body(F["threshold_table"]))
_band(cur)
set_widths(cur, [1.0, 1.65, 1.1, 1.65, 1.1])
cur = insert_paragraph_after(cur, NORMAL, "")
cur = insert_paragraph_after(cur, NORMAL, [("What we found.", True)])
for line in F["threshold_found"]:
    cur = insert_paragraph_after(cur, BULLET, plain(line))
cur = insert_paragraph_after(cur, NORMAL, [("Our choice and why. ", True), (F["threshold_choice"], False)])
cur = insert_paragraph_after(cur, NORMAL, [("Limits of this check.", True)])
for line in F["threshold_limits"]:
    cur = insert_paragraph_after(cur, BULLET, plain(line))

# 10. Recommendation
p = para(doc, "Recommendation to Carousell (as in the video)")
set_runs(p, lead(p.text.replace("Recommendation to Carousell (as in the video):", "Recommendation to Carousell:"), ": "))

# 11. Slides and video: no suggestion box or recording checklist
remove(table_after(doc, "Demo backups:"))
set_runs(para(doc, "Demo backups:"),
         "The demo uses S01 (missing SD card: partial refund), S16 (paid by bank transfer: not covered, decided by the rules), G155 (conflicting accounts: escalated with a follow-up question) and the what-if test. Backups: S02 (iPhone 64GB received as 16GB: full refund with return) and S10 (pilling the listing disclosed: decline).")

# 12. Status and team
set_runs(para(doc, "12. Status and next steps", "Heading 1"), "12. Status and team")
set_runs(para(doc, "12.1 What is done", "Heading 2"), "12.1 Status")
remove(para(doc, "GitHub repo linked on this machine (3 Nov)."))
b = para(doc, "App deployed on Streamlit Community Cloud")
insert_paragraph_after(b, BULLET, plain(F["status_not_done"]))
_remove_from(para(doc, "12.2 What is left", "Heading 2"), _heading("12.3", 2))
h = set_runs(para(doc, "12.3 Contribution table (template)", "Heading 2"), "12.2 Team and contributions (Task Allocation)")
intro = set_runs(para(doc, "Fill in one row per member."),
                 "Each member’s role, main contributions, where the evidence is, and their part in the video.")

# The course's Task Allocation form, as the team filled it in on Google Drive (13 Nov):
# equal contribution, then each task and the member in charge of it
insert_paragraph_after(h, intro, "All six members contributed equally to all tasks.")
roles = table_after(doc, "Each member’s role, main contributions")
cap = insert_paragraph_after(roles, intro, "Task allocation: each task and the member in charge of it.")
cap.paragraph_format.space_before = Pt(8)  # the intro style has no space above, and this one follows a table
tasks = insert_table_after(cap, roles, [
    ["S/N", "Tasks", "Member in charge"],
    ["1", "Agent workflow: LangGraph steps, tool loop, confidence check, staff pause", "Ronak (C1)"],
    ["2", "Citation check: all 68 test-set citations checked by hand", "Ronak (C1)"],
    ["3", "Policy search: policy clauses, hybrid search, citations, retrieval evaluation", "Akshaya (C2)"],
    ["4", "Data and evaluation: listings, dispute generator, labels, test harness, baseline, model comparison", "Evelyn (C3)"],
    ["5", "App and deployment: Streamlit app, local models, cloud deployment, repo and README", "Jonathan (C4)"],
    ["6", "Business case: problem, evidence, competitors, value and costs, recommendation", "Dan Yu (B1)"],
    ["7", "Presentation slides", "Dan Yu (B1)"],
    ["8", "Policy corpus, hard cases, labelling, risks and ethics", "Drue (B2)"],
    ["9", "Video: planning and editing", "Drue (B2)"],
    ["10", "Presenting: each member presents their own slides and their part of the video", "All members"],
])
keep_columns(tasks, 3)
set_widths(tasks, [0.5, 4.5, 1.5])
stripe_rows(tasks)

# Appendix B: the price was checked on Google's own page (section 9.6)
b = set_runs(para(doc, "Gemini API pricing:"),
             "Gemini API pricing: Google’s pricing page, ai.google.dev/gemini-api/docs/pricing (5 Nov 2026, paid-tier price for gemini-3.5-flash-lite).")
insert_paragraph_after(b, b, "Chow, C. K. (1970). On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory, 16(1), 41–46. The reject-option rule behind section 9.7 (a standard method reference, not one of the pages read on 31 Oct).")
t = table_after(doc, "Appendix C. Where everything lives")
resize_rows(t, len(t.rows) + 1)
set_row(t, len(t.rows) - 1, ["Escalation threshold cost check", "reports/review_cost.md (uv run dispute-agent review-cost; inputs in config.yaml under review_cost)"])

# Appendix C: no slides any more
for tbl in doc.tables:
    for i, row in enumerate(tbl.rows):
        if row.cells[0].text.strip() == "Code, data, reports, slides, video script":
            set_cell(tbl, i, 0, "Code, data, reports, video script")

doc.save(OUT)
print("saved", OUT)
