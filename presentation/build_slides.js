// Builds Carousell_Dispute_Agent_Slides.pptx: one slide per beat of VIDEO_SCRIPT.md,
// with the spoken lines as speaker notes. The demo slide is left blank on purpose.
//
//   cd presentation && npm install && node build_slides.js
//
// Every number on a slide comes from reports/ or the SPF brief named in its source line.
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const OUT = process.argv[2] || "Carousell_Dispute_Agent_Slides.pptx";

// Fill in the names, then rebuild. Empty names show the role only.
const TEAM = {
  C1: "", C2: "", C3: "", C4: "", B1: "", B2: "",
};
const REPO = "github.com/J0knee10/carousell-dispute-agent-bc3415";

const THEME = {
  name: "Carousell Dispute Agent",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B1E26", lt1: "FFFFFF", dk2: "4A505E", lt2: "F3F4F6",
    accent1: "C8323F", accent2: "16796F", accent3: "687080",
    accent4: "FF8C82", accent5: "6CC7B8", accent6: "BCC3CD",
    hlink: "16796F", folHlink: "687080",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Carousell Dispute Agent";
pres.author = "BC3415 group project";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const S = pres.shapes;
const HEAD = "+mj-lt"; // theme heading font, for big numbers
const BODY = "+mn-lt"; // theme body font, for chart text
const DIVIDER = "D5DAE1";
const DARK_CARD = "2A2F3A";
const HIGHLIGHT = "E3F1EF";

// --- Layouts -------------------------------------------------------------
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.8, y: 0.7, w: 11.7, h: 0.4, fontSize: 14, bold: true, color: C.accent4, charSpacing: 3, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.1, w: 11.7, h: 1.4, align: "left", fontSize: 64, bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.7, w: 11.7, h: 1.1, fontSize: 26, color: C.accent6, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.6, y: 0.45, w: 12.1, h: 0.35, fontSize: 13, bold: true, color: C.accent1, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.8, w: 12.1, h: 0.8, align: "left", fontSize: 34, bold: true, color: C.text1, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "source", type: "body", x: 0.6, y: 6.95, w: 11.2, h: 0.3, fontSize: 11, color: C.accent3, valign: "top", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.23, y: 6.95, w: 0.5, h: 0.3, fontSize: 11, color: C.accent3, align: "right" },
});
pres.defineSlideMaster({
  title: "STATEMENT",
  background: { color: C.accent1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.8, y: 0.7, w: 11.7, h: 0.4, fontSize: 14, bold: true, color: C.background1, charSpacing: 3, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.4, w: 11.7, h: 1.2, align: "left", fontSize: 54, bold: true, color: C.background1, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({ title: "BLANK_DARK", background: { color: C.text1 }, objects: [] });

// --- Helpers -------------------------------------------------------------
function box(slide, name, x, y, w, h, fill) {
  slide.addShape(S.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { type: "none" }, rectRadius: 0.12, objectName: name });
}
function text(slide, name, t, opts) {
  slide.addText(t, Object.assign({ margin: 0, isTextBox: true, valign: "top", objectName: name }, opts));
}
function dot(slide, name, x, y, size, color) {
  slide.addShape(S.OVAL, { x, y, w: size, h: size, fill: { color }, line: { type: "none" }, objectName: name });
}
function content(section, eyebrow, title, source) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(eyebrow, { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
  if (source) s.addText(source, { placeholder: "source" });
  return s;
}
function callout(slide, name, y, h, runs, fontSize = 20) {
  box(slide, name, 0.6, y, 12.13, h, C.text1);
  text(slide, `${name} text`, runs, { x: 0.95, y, w: 11.5, h, fontSize, valign: "middle" });
}
function bullets(items, color) {
  return items.map((t, i) => ({ text: t, options: { bullet: true, color, breakLine: i < items.length - 1, paraSpaceAfter: 8 } }));
}

// --- 1. The problem (B1) ---------------------------------------------------
const SEC1 = "1 · The problem";
pres.addSection({ title: SEC1 });

{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: SEC1 });
  s.addText("BC3415 · GROUP PROJECT · OPTION A", { placeholder: "eyebrow" });
  s.addText("Carousell Dispute Agent", { placeholder: "title" });
  s.addText("Helps Carousell’s support team settle “not as described” disputes. A person makes every final call.", { placeholder: "body" });
  const pills = [["Refund with return", C.accent5], ["Partial refund", C.accent6], ["Decline", C.accent4]];
  const widths = [2.55, 2.0, 1.35];
  let px = 12.5 - widths.reduce((a, b) => a + b, 0) - 0.15 * (widths.length - 1);
  pills.forEach(([label, color], i) => {
    s.addShape(S.ROUNDED_RECTANGLE, { x: px, y: 6.2, w: widths[i], h: 0.45, fill: { color: DARK_CARD }, line: { type: "none" }, rectRadius: 0.22, objectName: `Pill ${label}` });
    text(s, `Pill text ${label}`, label, { x: px, y: 6.2, w: widths[i], h: 0.45, fontSize: 15, bold: true, color, align: "center", valign: "middle" });
    px += widths[i] + 0.15;
  });
  const names = Object.values(TEAM).filter(Boolean);
  if (names.length) text(s, "Team", names.join(" · "), { x: 0.8, y: 6.2, w: 5.6, h: 0.45, fontSize: 16, color: C.background1, valign: "middle" });
  s.addNotes(`[0:00] B1: "Hi, we're Group [number]. This is the Carousell Dispute Agent. It helps Carousell's support team settle 'not as described' disputes, and a person makes every final call."`);
}

{
  const s = content(SEC1, "1 · THE PROBLEM", "Scams on Carousell are rising",
    "Source: Singapore Police Force, Mid-Year Scam and Cybercrime Brief 2026, pages 2, 10, 23 and 36 (January to June 2026).");
  const stats = [
    ["1,555", "scam cases on Carousell, up 17.1% on a year earlier", C.accent1],
    ["82.3%", "of scams on online shopping platforms happened on Carousell", C.text1],
    ["S$1.0m", "lost to e-commerce scams on Carousell, the platform with the most cases", C.text1],
  ];
  const w = 3.777;
  stats.forEach(([num, label, color], i) => {
    const x = 0.6 + i * (w + 0.4);
    box(s, `Stat card ${i + 1}`, x, 1.95, w, 2.75, C.background2);
    text(s, `Stat ${i + 1}`, num, { x: x + 0.4, y: 2.3, w: w - 0.8, h: 1.0, fontSize: 48, bold: true, fontFace: HEAD, color });
    text(s, `Stat label ${i + 1}`, label, { x: x + 0.4, y: 3.4, w: w - 0.8, h: 1.1, fontSize: 19, color: C.text2 });
  });
  callout(s, "Buy button callout", 5.1, 1.45, [
    { text: "Carousell’s answer is the ‘Buy’ button: ", options: { bold: true, color: C.accent4 } },
    { text: "the payment is held until the item arrives. It only works if buyers trust how disputes are settled.", options: { color: C.background1 } },
  ]);
  s.addNotes(`B1: "Scams on Carousell are rising: 1,555 cases in the first half of this year, up 17%, the only major online service where scams went up. Carousell's answer is the Buy button, which holds the payment until the item arrives. That only works if buyers trust how disputes are settled."`);
}

{
  const s = content(SEC1, "1 · THE PROBLEM", "“Not as described” is a judgement call",
    "Source: Carousell SG, Buyer Protection and Certified Refund Policy (data/policy/ in the repo).");
  const cols = [
    ["COVERED", C.accent2, ["A different size, colour, model or version", "Missing parts the listing promised", "Damage or defects the seller didn’t mention"]],
    ["NOT COVERED", C.accent1, ["Listed “light pink”, received “rose pink”", "Listed 8/10, the buyer says 6/10", "Wear on an item listed as used", "The buyer changed their mind"]],
  ];
  const w = 5.9;
  cols.forEach(([label, color, items], i) => {
    const x = 0.6 + i * (w + 0.33);
    box(s, `${label} card`, x, 1.95, w, 2.95, C.background2);
    dot(s, `${label} dot`, x + 0.4, 2.3, 0.3, color);
    text(s, `${label} label`, label, { x: x + 0.85, y: 2.27, w: w - 1.3, h: 0.36, fontSize: 15, bold: true, color, charSpacing: 2, valign: "middle" });
    text(s, `${label} list`, bullets(items, C.text1), { x: x + 0.4, y: 2.85, w: w - 0.8, h: 1.9, fontSize: 18 });
  });
  callout(s, "Balance callout", 5.25, 1.3, [
    { text: "Too far towards buyers: ", options: { bold: true, color: C.accent4 } },
    { text: "honest sellers lose. ", options: { color: C.background1 } },
    { text: "Too far towards sellers: ", options: { bold: true, color: C.accent4 } },
    { text: "buyers pay outside the app, where scams happen.", options: { color: C.background1 } },
  ]);
  s.addNotes(`[ends 0:50] B1: "And these disputes are judgement calls. The policy covers a wrong model, missing parts or a hidden defect, but not 'light pink versus rose pink'. Lean too far towards buyers and honest sellers lose. Too far towards sellers, and buyers pay outside the app, where scams happen."`);
}

// --- 2. How it works (C1) --------------------------------------------------
const SEC2 = "2 · How it works";
pres.addSection({ title: SEC2 });

{
  const s = content(SEC2, "2 · HOW IT WORKS", "Code for exact rules, an LLM for judgement",
    "LangGraph workflow in src/dispute_agent/agent/graph.py. The confidence threshold for escalation is 0.7 (config.yaml).");
  const KIND = {
    code: ["Plain code", C.accent3],
    llm: ["LLM (judge model)", C.accent1],
    rag: ["Retrieval", C.accent2],
    person: ["Person", C.text1],
  };
  const steps = [
    ["Eligibility rules", "Buy button? Inside the window?", "code"],
    ["Claim matching", "Listing’s promises vs the buyer’s report", "llm"],
    ["Policy retrieval", "Clauses for each gap", "rag"],
    ["Judgement", "Outcome, clause IDs; can search again", "llm"],
    ["Check", "Citations real? Confident?", "code"],
    ["Staff decides", "Approve or override", "person"],
    ["Message drafts", "To the buyer and the seller", "llm"],
  ];
  const w = 1.55, gap = 0.215, y = 2.05, h = 2.25;
  steps.forEach(([name, desc, kind], i) => {
    const x = 0.6 + i * (w + gap);
    const dark = kind === "person";
    box(s, `Step card ${i + 1}`, x, y, w, h, dark ? C.text1 : C.background2);
    if (!dark) dot(s, `Step dot ${i + 1}`, x + 0.2, y + 0.25, 0.28, KIND[kind][1]);
    text(s, `Step name ${i + 1}`, name, { x: x + 0.2, y: y + 0.7, w: w - 0.35, h: 0.65, fontSize: 16, bold: true, color: dark ? C.background1 : C.text1 });
    text(s, `Step desc ${i + 1}`, desc, { x: x + 0.2, y: y + 1.35, w: w - 0.35, h: 0.8, fontSize: 13, color: dark ? C.accent6 : C.text2 });
    if (i < steps.length - 1) {
      s.addShape(S.RIGHT_ARROW, { x: x + w + 0.03, y: y + h / 2 - 0.09, w: gap - 0.06, h: 0.18, fill: { color: C.accent3 }, line: { type: "none" }, objectName: `Step arrow ${i + 1}` });
    }
  });
  // "Not covered" path: from under Eligibility to under Staff decides.
  const x1 = 0.6 + w / 2, x6 = 0.6 + 5 * (w + gap) + w / 2, yb = y + h + 0.45;
  const line = { color: C.accent3, width: 1.75 };
  s.addShape(S.LINE, { x: x1, y: y + h, w: 0, h: 0.45, line, objectName: "Bypass down" });
  s.addShape(S.LINE, { x: x1, y: yb, w: x6 - x1, h: 0, line, objectName: "Bypass across" });
  s.addShape(S.LINE, { x: x6, y: y + h, w: 0, h: 0.45, line: { ...line, beginArrowType: "triangle" }, objectName: "Bypass up" });
  text(s, "Bypass label", "Not covered or late: straight to staff with a rule-based note, no LLM call", {
    x: x1 + 0.2, y: yb + 0.08, w: x6 - x1 - 0.4, h: 0.4, fontSize: 14, color: C.text2, align: "center",
  });
  // Legend
  let lx = 0.6;
  Object.entries(KIND).forEach(([key, [label, color]]) => {
    dot(s, `Legend dot ${key}`, lx, 5.62, 0.22, color);
    text(s, `Legend ${key}`, label, { x: lx + 0.32, y: 5.55, w: 1.9, h: 0.36, fontSize: 15, color: C.text1, valign: "middle" });
    lx += 2.3;
  });
  text(s, "Escalation note", "Missing policy: the judge calls search_policy and decides again. Unsure or uncited: the check sends the case to a person.", {
    x: 0.6, y: 6.1, w: 12.1, h: 0.4, fontSize: 15, italic: true, color: C.text2,
  });
  s.addNotes(`[0:50] C1: "How does it work? It's a LangGraph workflow. Exact rules are plain code: did the buyer use the Buy button, inside the window? If not, the case goes straight to staff. Judgement goes to an LLM: it matches what the listing promised against what the buyer reports, retrieves the policy clauses for each gap, and recommends an outcome with citations. If those clauses don't cover a gap, it can call a policy search tool and decide again. Code checks the citations, and the workflow pauses until a person decides."`);
}

{
  const s = content(SEC2, "2 · HOW IT WORKS", "The stack, and why the search is hybrid",
    "Source: reports/retrieval.md (25 test questions over the 37 policy clauses).");
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  const row = (part, tool) => [{ text: part, options: { bold: true } }, { text: tool, options: { color: C.text2 } }];
  s.addTable([
    [hdr("Part"), hdr("Tool")],
    row("Workflow, pause for a person", "LangGraph (interrupt)"),
    row("Judge model", "Gemini (cloud) or Llama / Qwen (local), JSON output"),
    row("Policy search", "ChromaDB embeddings + BM25 keywords, rank fusion"),
    row("Policy text", "4 Carousell help pages, 37 clauses, copied by hand"),
    row("Interface", "Streamlit, on Community Cloud"),
    row("Environment", "uv with Python 3.12 locked; Docker optional"),
  ], { x: 0.6, y: 1.95, w: 7.3, colW: [2.8, 4.5], rowH: 0.62, fontSize: 16, color: C.text1, valign: "middle", border: { type: "solid", pt: 0.75, color: DIVIDER }, margin: 0.1, objectName: "Stack table" });

  box(s, "Retrieval card", 8.3, 1.95, 4.43, 4.34, C.background2);
  text(s, "Retrieval label", "RIGHT CLAUSE RANKED FIRST", { x: 8.65, y: 2.25, w: 3.8, h: 0.35, fontSize: 13, bold: true, color: C.accent2, charSpacing: 2 });
  const bars = [["Embeddings only", 52, C.accent6], ["Keywords only", 52, C.accent6], ["Hybrid", 76, C.accent2]];
  const maxW = 2.2;
  bars.forEach(([label, pct, color], i) => {
    const by = 2.85 + i * 0.95;
    text(s, `Bar label ${i + 1}`, label, { x: 8.65, y: by, w: 3.8, h: 0.32, fontSize: 15, color: C.text1 });
    s.addShape(S.RECTANGLE, { x: 8.65, y: by + 0.36, w: maxW * pct / 100, h: 0.38, fill: { color }, line: { type: "none" }, objectName: `Bar ${i + 1}` });
    text(s, `Bar value ${i + 1}`, `${pct}%`, { x: 8.65 + maxW * pct / 100 + 0.12, y: by + 0.36, w: 1.0, h: 0.38, fontSize: 18, bold: true, fontFace: HEAD, color: C.text1, valign: "middle" });
  });
  text(s, "Retrieval note", "Hybrid has the right clause in its top five 96% of the time.", { x: 8.65, y: 5.6, w: 3.8, h: 0.55, fontSize: 14, color: C.text2 });
  s.addNotes(`[ends 1:40] C1: "The stack: LangGraph, Gemini's free tier or a local model with structured JSON output, ChromaDB plus keyword search, and Streamlit. The search is hybrid because it ranks the right clause first 76% of the time, against 52% for embeddings or keywords alone."`);
}

// --- 3. Demo (C4; blank: the screen recording goes over this slide) -------
const SEC3 = "3 · Live demo";
pres.addSection({ title: SEC3 });
{
  const s = pres.addSlide({ masterName: "BLANK_DARK", sectionTitle: SEC3 });
  s.addNotes([
    "[1:40-3:00] LIVE DEMO (C4) - blank on purpose. Place the screen recording over this slide.",
    "App: uv run streamlit run app/streamlit_app.py. Sidebar: provider Gemini, page 'Review a dispute'.",
    "",
    "1. Cases: demo. Pick S01 (PS Vita Slim). Click 'Run the agent'.",
    "Expect: eligible; 1 gap, missing_part; Partial refund 15%, confidence 0.90, cites BPR-02, DPO-08, DPO-02.",
    "\"A PS Vita listed with an 8GB SD card, and the buyer says there's no card. Eligibility passes. The agent finds one gap, a missing part, and recommends a 15% partial refund, citing the clauses on incomplete items. I approve it, and it drafts the messages to the buyer and the seller.\"",
    "Then: Decision 'Approve the recommendation', type a name, 'Submit decision'. Scroll to the message drafts.",
    "",
    "2. Pick S16 (Fushigi Yuugi anime DVD). Run the agent.",
    "Expect: Not covered, straight to staff, no LLM call.",
    "\"This buyer paid by bank transfer. That's outside Buyer Protection, so the rules say 'not covered' straight away, with no LLM call.\"",
    "",
    "3. Cases: all. Pick G155 (Old Nintendo Games). Run the agent.",
    "Expect: Decline at confidence 0.50, escalated, with a follow-up question asking the buyer for photos of the packaging.",
    "\"Here the listing promised three games, the buyer got two, and the seller has a photo of all three in the box. The agent isn't sure: confidence 0.5. So it sends the case to a person, and suggests asking the buyer for photos of the packaging.\"",
    "",
    "4. Page 'What-if policy test'. Paste the rule below. Past cases from: seed. Maximum cases: 10. Run what-if.",
    "Rule: If a promised accessory is missing, the buyer gets a full refund with return instead of a partial refund.",
    "Expect: about 3 of 10 flip to a full refund with return: S01, S04 and S09 (S09 is a wrong flip: that listing never promised the accessory).",
    "\"Last, the what-if test. Carousell writes a proposed rule, and the agent re-judges past disputes under it. Here 3 of 10 would flip. One flip, S09, is wrong: that listing never promised the accessory, so a person still checks the results.\"",
  ].join("\n"));
}

// --- 4. Does it work (C3) --------------------------------------------------
const SEC4 = "4 · Does it work";
pres.addSection({ title: SEC4 });

{
  const s = content(SEC4, "4 · DOES IT WORK", "200 disputes on real listings",
    "Listings: Mercari Price Suggestion dataset (Kaggle), prices converted to S$. Disputes: data/cases/ in the repo.");
  const steps = [
    ["300", "real listings", "second-hand items from Mercari, a US marketplace"],
    ["200", "disputes written on top", "20 by hand, 180 by a generator model"],
    ["50", "held out as the test set", "prompts were never tuned on them"],
  ];
  const w = 3.543;
  steps.forEach(([num, head, body], i) => {
    const x = 0.6 + i * (w + 0.75);
    box(s, `Data card ${i + 1}`, x, 1.95, w, 2.9, i === 2 ? C.text1 : C.background2);
    text(s, `Data number ${i + 1}`, num, { x: x + 0.4, y: 2.25, w: w - 0.8, h: 0.95, fontSize: 54, bold: true, fontFace: HEAD, color: i === 2 ? C.accent4 : C.accent1 });
    text(s, `Data head ${i + 1}`, head, { x: x + 0.4, y: 3.3, w: w - 0.8, h: 0.5, fontSize: 20, bold: true, color: i === 2 ? C.background1 : C.text1 });
    text(s, `Data body ${i + 1}`, body, { x: x + 0.4, y: 3.85, w: w - 0.8, h: 0.8, fontSize: 16, color: i === 2 ? C.accent6 : C.text2 });
    if (i < 2) s.addShape(S.RIGHT_ARROW, { x: x + w + 0.15, y: 3.22, w: 0.45, h: 0.36, fill: { color: C.accent3 }, line: { type: "none" }, objectName: `Data arrow ${i + 1}` });
  });
  const facts = [
    ["Mix", "60% clear, 30% borderline, 10% ineligible, as the brief planned"],
    ["No self-grading", "the models that wrote the disputes never judge them"],
    ["Exact eligibility", "code sets the payment and delivery dates, so those labels are certain"],
  ];
  facts.forEach(([head, body], i) => {
    const y = 5.15 + i * 0.55;
    dot(s, `Fact dot ${i + 1}`, 0.6, y + 0.1, 0.2, C.accent2);
    text(s, `Fact ${i + 1}`, [
      { text: `${head}: `, options: { bold: true, color: C.text1 } },
      { text: body, options: { color: C.text2 } },
    ], { x: 0.95, y, w: 11.8, h: 0.42, fontSize: 17, valign: "middle" });
  });
  s.addNotes(`[1:40 after the demo, about 3:00] C3: "Does it work? We sampled 300 real second-hand listings and wrote 200 disputes on top: 20 by hand and 180 with a generator model. The models that write the disputes never judge them. 50 cases are held out as the test set."`);
}

{
  const s = content(SEC4, "4 · DOES IT WORK", "Level on judgement, ahead on the rules",
    "Source: reports/evaluation_cmp_gemini-flash-lite.md, 50 held-out cases, judge gemini-flash-lite-latest. Labels are provisional until two team members finish labelling.");
  s.addChart(pres.charts.BAR, [
    { name: "Agent", labels: ["Clear (30)", "Borderline (15)", "Ineligible (5)", "All 50"], values: [93, 80, 100, 90] },
    { name: "Single-prompt baseline", labels: ["Clear (30)", "Borderline (15)", "Ineligible (5)", "All 50"], values: [97, 80, 60, 88] },
  ], {
    x: 0.6, y: 1.85, w: 7.2, h: 4.85, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [THEME.colors.accent1, THEME.colors.accent6],
    showTitle: true, title: "Decisions right (%)", titleFontSize: 15, titleColor: THEME.colors.dk1, titleFontFace: BODY,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', dataLabelFontSize: 13, dataLabelColor: THEME.colors.dk1, dataLabelFontFace: BODY,
    valAxisHidden: true, valAxisMaxVal: 110, valAxisMinVal: 0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisLabelColor: THEME.colors.dk2, catAxisLabelFontSize: 13, catAxisLabelFontFace: BODY, catAxisLineShow: false,
    showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: BODY, legendColor: THEME.colors.dk2,
    objectName: "Accuracy chart",
  });
  const rows = [
    ["100%", "vs 68%", "eligibility right: the rules never miss a bank transfer or a late dispute"],
    ["2 of 5", "vs 1 of 6", "wrong answers sent to a person as unsure"],
    ["90%", "of 68", "citations support the decision (an AI-assisted check, to be confirmed by hand)"],
  ];
  rows.forEach(([num, vs, cap], i) => {
    const y = 1.95 + i * 1.6;
    if (i > 0) s.addShape(S.LINE, { x: 8.2, y: y - 0.1, w: 4.53, h: 0, line: { color: DIVIDER, width: 1 }, objectName: `Row divider ${i}` });
    text(s, `Result ${i + 1}`, [
      { text: num, options: { bold: true, fontFace: HEAD, color: C.accent1, fontSize: 34 } },
      { text: `  ${vs}`, options: { color: C.text2, fontSize: 17 } },
    ], { x: 8.2, y, w: 4.53, h: 0.65, valign: "middle" });
    text(s, `Result caption ${i + 1}`, cap, { x: 8.2, y: y + 0.65, w: 4.53, h: 0.75, fontSize: 15, color: C.text1 });
  });
  s.addNotes(`C3: "On those 50, the agent gets 90% right; a single prompt with the whole policy pasted in gets 88%. That's one case, a tie on judgement. The gain is on the rules: eligibility is 100% against 68%. And 2 of its 5 mistakes go to a person."`);
}

{
  const s = content(SEC4, "4 · DOES IT WORK", "We tried three judge models: Gemini stays",
    "Source: reports/model_comparison.md, same 50 test cases. Local models ran on our own PC (RTX 4060 Ti, 8 GB GPU memory), which limits them to about 8 billion parameters.");
  const labels = ["Gemini Flash-Lite (cloud)", "Llama 3.1 8B (local)", "Qwen 3 8B (local)"];
  s.addChart(pres.charts.BAR, [
    { name: "Agent", labels, values: [90, 52, 48] },
    { name: "Single-prompt baseline", labels, values: [88, 34, 44] },
  ], {
    x: 0.6, y: 1.85, w: 7.2, h: 4.85, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [THEME.colors.accent1, THEME.colors.accent6],
    showTitle: true, title: "Decisions right (%), 50 test cases", titleFontSize: 15, titleColor: THEME.colors.dk1, titleFontFace: BODY,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0"%"', dataLabelFontSize: 13, dataLabelColor: THEME.colors.dk1, dataLabelFontFace: BODY,
    valAxisHidden: true, valAxisMaxVal: 110, valAxisMinVal: 0, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    catAxisLabelColor: THEME.colors.dk2, catAxisLabelFontSize: 13, catAxisLabelFontFace: BODY, catAxisLineShow: false,
    showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: BODY, legendColor: THEME.colors.dk2,
    objectName: "Model chart",
  });
  const rows = [
    ["+18 pts", "with Llama", "the agent’s largest gain over a single prompt (Gemini: +2); not significant on 50 cases"],
    ["19 of 21", "for Llama", "cases that should be declined were refunded by the local model (Gemini: 1)"],
    ["Private", "but slower", "local models keep case data on the PC, at 15 to 19 s a case against 9 s"],
  ];
  rows.forEach(([num, vs, cap], i) => {
    const y = 1.95 + i * 1.6;
    if (i > 0) s.addShape(S.LINE, { x: 8.2, y: y - 0.1, w: 4.53, h: 0, line: { color: DIVIDER, width: 1 }, objectName: `Model divider ${i}` });
    text(s, `Model result ${i + 1}`, [
      { text: num, options: { bold: true, fontFace: HEAD, color: C.accent1, fontSize: 34 } },
      { text: `  ${vs}`, options: { color: C.text2, fontSize: 17 } },
    ], { x: 8.2, y, w: 4.53, h: 0.65, valign: "middle" });
    text(s, `Model caption ${i + 1}`, cap, { x: 8.2, y: y + 0.65, w: 4.53, h: 0.75, fontSize: 15, color: C.text1 });
  });
  s.addNotes(`[ends about 3:55] C3: "We also tried two open models on our own 8 GB graphics card, Llama and Qwen. They got only about half right: they refund almost everything, even a change of mind. The agent helped them most, 18 points for Llama, because the rules are code. So Gemini stays the judge; local models keep data private but need bigger hardware."`);
}

// --- 5. Risks and recommendation (B1) --------------------------------------
const SEC5 = "5 · Risks and next steps";
pres.addSection({ title: SEC5 });

{
  const s = content(SEC5, "5 · RISKS", "Where it can go wrong, and what we do",
    "Source: reports/evaluation_cmp_gemini-flash-lite.md and reports/model_comparison.md. Buyer-win cases are those labelled as a refund; seller-win cases, a decline.");
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 } } });
  const row = (risk, guard, result) => [
    { text: risk, options: { bold: true } },
    { text: guard, options: { color: C.text2 } },
    { text: result, options: { bold: true } },
  ];
  s.addTable([
    [hdr("Risk"), hdr("Safeguard"), hdr("On the test set")],
    row("Invented policy", "Every citation must be a clause it retrieved; code drops the rest", "0 invented clause IDs in final answers"),
    row("Leaning to one side", "Accuracy measured separately for buyer wins and seller wins", "96% of seller wins, 83% of buyer wins: it leans to declining"),
    row("Staff rubber-stamping", "Confidence score, escalation, every override logged", "6% of cases escalated"),
    row("Personal data", "Made-up disputes only", "A deployment would remove personal details first"),
  ], { x: 0.6, y: 1.95, w: 12.13, colW: [2.7, 5.0, 4.43], rowH: 0.85, fontSize: 17, color: C.text1, valign: "middle", border: { type: "solid", pt: 0.75, color: DIVIDER }, margin: 0.12, objectName: "Risk table" });
  s.addNotes(`[3:55] B1: "The risks. Invented policy: none of its citations were invented. Bias: it gets 96% of seller wins right but 83% of buyer wins, so it leans towards declining, and we track that. Rubber-stamping: unsure cases go to a person, and every override is logged. And our data is made up; a deployment would remove personal details first."`);
}

{
  const s = pres.addSlide({ masterName: "STATEMENT", sectionTitle: SEC5 });
  s.addText("5 · RECOMMENDATION", { placeholder: "eyebrow" });
  s.addText("Ready for a staff-assist pilot", { placeholder: "title" });
  const stats = [
    ["9 s", "from loading a case to a recommendation with policy citations (median)"],
    ["6%", "of cases sent to a person as unsure, with questions to ask"],
  ];
  stats.forEach(([num, cap], i) => {
    const x = 0.8 + i * 6.1;
    text(s, `Verdict stat ${i + 1}`, num, { x, y: 3.0, w: 5.6, h: 1.2, fontSize: 66, bold: true, fontFace: HEAD, color: C.background1 });
    text(s, `Verdict caption ${i + 1}`, cap, { x, y: 4.25, w: 5.4, h: 1.0, fontSize: 22, color: C.background1 });
  });
  text(s, "Not automatic", "Not for automatic decisions: a person approves every one.", { x: 0.8, y: 6.0, w: 11.7, h: 0.6, fontSize: 24, italic: true, color: C.background1 });
  s.addNotes(`B1: "So our recommendation: it's ready for a staff-assist pilot, not for automatic decisions. It gives a cited recommendation in about 9 seconds, and flags 6% of cases for a person."`);
}

{
  const s = content(SEC5, "5 · NEXT STEPS", "What a pilot would measure");
  const kpis = [
    ["Time to resolve", "from a dispute reaching Carousell to the decision"],
    ["Decisions overturned", "on appeal, a check on quality"],
    ["‘Buy’ button share", "of orders: does trust in disputes keep buyers in the protected flow?"],
  ];
  const w = 3.777;
  kpis.forEach(([head, body], i) => {
    const x = 0.6 + i * (w + 0.4);
    box(s, `KPI card ${i + 1}`, x, 1.95, w, 2.55, C.background2);
    s.addShape(S.OVAL, { x: x + 0.4, y: 2.3, w: 0.6, h: 0.6, fill: { color: C.accent2 }, line: { type: "none" }, objectName: `KPI number ${i + 1}` });
    text(s, `KPI number text ${i + 1}`, String(i + 1), { x: x + 0.4, y: 2.3, w: 0.6, h: 0.6, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle" });
    text(s, `KPI head ${i + 1}`, head, { x: x + 0.4, y: 3.1, w: w - 0.8, h: 0.5, fontSize: 22, bold: true, color: C.text1 });
    text(s, `KPI body ${i + 1}`, body, { x: x + 0.4, y: 3.6, w: w - 0.8, h: 0.8, fontSize: 16, color: C.text2 });
  });
  callout(s, "Before the pilot", 4.9, 1.55, [
    { text: "Before that: ", options: { bold: true, color: C.accent4 } },
    { text: "two of us label the test set by hand and we re-measure against their labels. The same agent fits other second-hand marketplaces: load their policy pages into the search.", options: { color: C.background1 } },
  ], 19);
  s.addNotes(`B1: "A pilot would measure time to resolve a dispute, decisions overturned on appeal, and the share of orders using the Buy button. First, two of us label the test set by hand, and we re-measure."`);
}

{
  const s = content(SEC5, "TEAM", "Who built what");
  const roles = [
    ["C1", "Agent lead", "LangGraph workflow, confidence check, the pause for staff"],
    ["C2", "RAG and policy", "Policy clauses, hybrid search, citations"],
    ["C3", "Data and evaluation", "200 disputes, test harness, the baseline"],
    ["C4", "App and deployment", "Streamlit app, cloud deployment, repo"],
    ["B1", "Business lead", "Problem, evidence, business case"],
    ["B2", "Policy and story", "Policy pages, hard cases, the video"],
  ];
  const w = 3.777, h = 2.2;
  roles.forEach(([code, role, owns], i) => {
    const x = 0.6 + (i % 3) * (w + 0.4), y = 1.95 + Math.floor(i / 3) * (h + 0.35);
    const name = TEAM[code];
    box(s, `Role card ${code}`, x, y, w, h, C.background2);
    dot(s, `Role dot ${code}`, x + 0.4, y + 0.35, 0.55, code.startsWith("C") ? C.accent2 : C.accent1);
    text(s, `Role code ${code}`, code, { x: x + 0.4, y: y + 0.35, w: 0.55, h: 0.55, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" });
    text(s, `Role name ${code}`, name ? [{ text: name, options: { breakLine: true } }, { text: role, options: { bold: false, fontSize: 15, color: C.text2 } }] : role,
      { x: x + 1.15, y: y + 0.3, w: w - 1.45, h: 0.7, fontSize: 19, bold: true, color: C.text1, valign: "middle" });
    text(s, `Role owns ${code}`, owns, { x: x + 0.4, y: y + 1.15, w: w - 0.8, h: 0.85, fontSize: 16, color: C.text2 });
  });
  s.addNotes(`B1: "Here's who built what." (Hold for two or three seconds.)`);
}

{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: SEC5 });
  s.addText("CAROUSELL DISPUTE AGENT", { placeholder: "eyebrow" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText(`Code and reports: ${REPO}`, { placeholder: "body" });
  s.addNotes(`[ends about 4:50] B1: "Thank you." (Hold this slide for a second or two at the end.)`);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
