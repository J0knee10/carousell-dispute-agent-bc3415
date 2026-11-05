# Carousell Dispute Agent: video script

Audience: Carousell's support and Trust & Safety leads (and the BC3415 markers). The brief asks for 3 to 5 minutes; the target is about 4:55. That's about 4:35 of speech (about 690 words at 150 a minute), plus clicks and Gemini waits. Cut the waits in editing; a live LLM step takes 10 to 20 seconds on the free tier.

All six members speak, following the project brief: **B1** (Dan Yu) presents the problem and the recommendation, **C1** (Ronak) explains the workflow, **C2** (Akshaya) the policy search, **C4** (Jonathan) records the live demo, **C3** (Evelyn) presents the evaluation, and **B2** (Drue) presents the risks and edits the video. Swap names freely; the lines don't depend on who says them.

Every number here comes from `reports/` or the SPF brief named on slide 2. The slides are `Carousell_Dispute_Agent_Slides.pptx` in this folder; their speaker notes hold every line below.

---

## Before you hit record

- [ ] Say your group number on slide 1 (the notes have "[number]").
- [ ] Start the app from the repo root: `uv run streamlit run app/streamlit_app.py`. In the sidebar, choose **Gemini**. Check `uv run dispute-agent check-llm` says OK first: the free daily quota resets at midnight Pacific time (3 PM Singapore until 1 Nov, then 4 PM).
- [ ] Do one full rehearsal of the demo on the day. The LLM can give a different answer between runs; the expected answers below were checked on 28 Oct 2026 and again (S01, G155) on 4 Nov 2026 with the current agent.
- [ ] **Show every speaker.** The marking scheme asks that the video features the team: each person appears on camera for their part (a webcam corner over the slides, or a short clip before their section), with their name on screen the first time.
- [ ] **Never open `.env` on screen.** It holds the API key.
- [ ] Close other tabs and notifications. Zoom the browser to 110–125% so the text is readable in the recording.

---

## 1. The problem (B1, 0:00–0:50)

**(next)** in the lines below means: click to the next slide at that point. Start recording on slide 1.

**Screen:** slides 1–3 (cover, scams on Carousell, the judgement call).

> "Hi, we're Group [number]. This is the Carousell Dispute Agent. It helps Carousell's support team settle 'not as described' disputes, and a person makes every final call.
>
> **(next)** Scams on Carousell are rising: 1,555 cases in the first half of this year, up 17%, the only major online service where scams went up. Carousell's answer is the Buy button, which holds the payment until the item arrives. That only works if buyers trust how disputes are settled.
>
> **(next)** And these disputes are judgement calls. The policy covers a wrong model, missing parts or a hidden defect, but not 'light pink versus rose pink'. Lean too far towards buyers and honest sellers lose. Too far towards sellers, and buyers pay outside the app, where scams happen."

## 2. How it works (C1, 0:50–1:25)

**Screen:** slide 4 (the workflow).

> "**(next)** How does it work? It's a LangGraph workflow. Exact rules are plain code: did the buyer use the Buy button, inside the window? If not, the case goes straight to staff. Judgement goes to an LLM: it matches what the listing promised against what the buyer reports, retrieves the policy clauses for each gap, and recommends an outcome with citations. If those clauses don't cover a gap, it can call a policy search tool and decide again. Code checks the citations, and the workflow pauses until a person decides."

## 3. The policy search (C2, 1:25–1:40)

**Screen:** slide 5 (the stack, and why the search is hybrid).

> "**(next)** The policy search: Carousell's four help pages are split into 37 clauses, and every gap gets its own search. It's hybrid, ChromaDB embeddings plus keyword search, because that puts the right clause first 76% of the time, against 52% for either one alone."

## 4. Live demo (C4, 1:40–3:00)

**(next)** **Screen:** slide 6 (blank), with the app recording placed over it. Sidebar: provider **Gemini**, page **Review a dispute**.

1. **S01, partial refund.** Cases: **demo**. Pick **S01 · PS Vita Slim**. Click **Run the agent**.
   Expect: eligible; one gap, `missing_part`; **Partial refund, 15%**, confidence 0.90, citing BPR-02, DPO-08 and DPO-02.
   > "A PS Vita listed with an 8GB SD card, and the buyer says there's no card. Eligibility passes. The agent finds one gap, a missing part, and recommends a 15% partial refund, citing the clauses on incomplete items."

   Then choose **Approve the recommendation**, type a name, click **Submit decision**, and scroll to the message drafts.
   > "I approve it, and it drafts the messages to the buyer and the seller."
2. **S16, not covered.** Pick **S16 · Fushigi Yuugi anime DVD**. Run the agent.
   Expect: **not covered**, decided by the rules, no LLM call.
   > "This buyer paid by bank transfer. That's outside Buyer Protection, so the rules say 'not covered' straight away, with no LLM call."
3. **G155, the agent asks for help.** Cases: **all**. Pick **G155 · Old Nintendo Games**. Run the agent.
   Expect: decline at **confidence 0.50**, **escalated**, with a follow-up question asking the buyer for photos of the outer packaging and shipping label.
   > "Here the listing promised three games, the buyer got two, and the seller has a photo of all three in the box. The agent isn't sure: confidence 0.5. So it sends the case to a person, and suggests asking the buyer for photos of the packaging."
4. **What-if.** Page **What-if policy test**. Replace the rule with:
   ```
   If a promised accessory is missing, the buyer gets a full refund with return instead of a partial refund.
   ```
   Past cases from: **seed**. Maximum cases: **10**. Click **Run what-if**.
   Expect: about 3 of 10 cases flip to a full refund with return: S01 and S04 (missing accessories, as intended) and S09, which is a wrong flip (that buyer wanted accessories the listing never promised). Checked on 28 Oct over 15 seed cases: 4 flipped (S01, S04, S15 and S09).
   > "Last, the what-if test. Carousell writes a proposed rule, and the agent re-judges past disputes under it. Here 3 of 10 would flip. One flip, S09, is wrong: that listing never promised the accessory, so a person still checks the results."

If a step gives a different answer from the one expected, keep going: say what the agent did and why, and use a backup case. Backups on the demo list: **S02** (iPhone 64GB received as 16GB: full refund with return) and **S10** (sweater with pilling the listing disclosed: decline).

## 5. Does it work? (C3, 3:00–3:55)

**Screen:** slide 7 (the data), slide 8 (the results) from "On those 50", slide 9 (the models) from "We also tried".

> "**(next)** Does it work? We sampled 300 real second-hand listings and wrote 200 disputes on top: 20 by hand and 180 with a generator model. The models that write the disputes never judge them. 50 cases are held out as the test set.
>
> **(next)** On those 50, labelled by hand, the agent gets 90% right; a single prompt with the whole policy pasted in gets 88%. That's one case, a tie on judgement. The gain is on the rules: eligibility is 100% against 68%. And 2 of its 5 mistakes go to a person.
>
> **(next)** We also tried two open models on our own 8 GB graphics card, Llama and Qwen. They got only about half right: they refund almost everything, even a change of mind. The agent helped them most, 20 points for Llama, because the rules are code. So Gemini stays the judge; local models keep data private but need bigger hardware."

## 6. Risks (B2, 3:55–4:20)

**Screen:** slide 10 (risks).

> "**(next)** The risks. Invented policy: none of its citations were invented. Bias: it gets 96% of seller wins right but 83% of buyer wins, so it leans towards declining, and we track that. Rubber-stamping: unsure cases go to a person, and every override is logged. And our data is made up; a deployment would remove personal details first."

## 7. Recommendation (B1, 4:20–4:50)

**Screen:** slide 11 (recommendation), slide 12 (pilot) from "A pilot would measure", slide 13 (team), slide 14 on "Thank you".

> "**(next)** So our recommendation: it's ready for a staff-assist pilot, not for automatic decisions. It gives a cited recommendation in about 9 seconds, and flags 6% of cases for a person.
>
> **(next)** A pilot would measure time to resolve a dispute, decisions overturned on appeal, and the share of orders using the Buy button. First, a person checks the citations, and we re-measure on more cases.
>
> **(next)** Here's who built what. **(next)** Thank you."

---

## If someone asks (not in the video)

**The problem**
- **Where the scam figures come from:** SPF Mid-Year Scam and Cybercrime Brief 2026. Page 10: "Cases on Carousell rose by 17.1% to 1,555 in the first half of 2026, from 1,328" (scams where the scammer reached the victim through Carousell, all scam types). Page 2: Carousell is "the only designated online service registering an increase". Page 23: 82.3% of the 1,890 scams on online shopping platforms were on Carousell. Page 36: Carousell had the most e-commerce scam cases, with about S$1 million lost. Page 37 describes Carousell's "escrow-based payment system with trackable delivery".
- **Limit to state openly:** most scams happen outside Buyer Protection (bank transfers, pre-orders). The agent doesn't stop scams directly; the argument is that fair, fast disputes make the protected Buy button worth using. We found no public figures on Carousell's dispute volume.

**The agent**
- **Why not let the LLM do everything?** Payment method, dates and tracking are exact rules, so code gets them right every time: eligibility is 100% for the agent with every judge model, against 68% (Gemini), 86% (Llama) and 90% (Qwen) for the single prompt. Ineligible cases also cost no LLM call.
- **What counts as "unsure":** confidence below 0.7, a citation to a clause that wasn't retrieved, no citation, a gap marked unclear, an outcome that contradicts the agent's own gap assessment, or a judge that still wants policy the search tool could not find (`review_gate` in `src/dispute_agent/agent/graph.py`).
- **The search tool:** the judge can call `search_policy` when the clauses it was given don't cover a gap; the graph loops back to it with the new clauses, once at most. On the test set no model needed it, because the per-gap searches already found the clauses. When we removed the per-gap searches and gave the search to a planning step, it was used (Llama in every case, Qwen in 9%, Gemini in 3 of 10) without changing accuracy, so per-gap retrieval stays the default (`reports/model_comparison.md`).
- **The four outcomes** are Carousell's own (full refund with return, full refund without return, partial refund, decline). When to choose a partial refund over a return is our rubric (`DECISION_GUIDE` in `src/dispute_agent/agent/prompts.py`); Carousell's policy doesn't spell it out.
- **Photo checking** is an interface only (`src/dispute_agent/agent/photo.py`); cases carry text descriptions of photos.
- **G155 changed between runs:** a partial refund in the first test run, a full refund with return in the second, and a decline in the 4 Nov run and in the demo checks on 28 Oct and 4 Nov. It was escalated every time, which is the point of the escalation rule. LLM output varies even at temperature 0.

**The evaluation**
- **Labels:** the 50 test cases were labelled by hand: B1 took 25 and B2 the other 25 (`docs/labelling_guide.md`), so there is no agreement score between them yet. The hand labels differ from the outcomes the cases were written for on two cases (G134: decline; G147: partial refund). An AI reviewer (Claude) also labelled them in separate columns and agrees with the hand labels on 47 of 50 (kappa 0.90).
- **Citation accuracy (90%):** checked by Claude, an AI model separate from every judge model, in the `claude_supports` column of `reports/citation_check_cmp_gemini-flash-lite.csv`. A team member should spot-check it. The 7 "no" answers are mostly procedural clauses (how a return works) or clauses listing what is covered, cited on a decline.
- **Bias:** the baseline leans the other way: 96% of buyer wins right but 81% of seller wins.
- **Escalation:** 6% of test cases were escalated, including 2 of the agent's 5 wrong answers. The baseline has no review step (it counts as escalated only below 0.7 confidence: 1 of its 6 wrong answers), so the two are not like for like. On the cases it does not escalate, the agent is right 94% of the time, including the 5 ineligible cases the rules decide.
- **Generator vs judge:** 154 disputes were written by Gemma 4, 26 by Gemini 3 Flash and Gemini 3.5 Flash; the judges are Gemini Flash-Lite, Llama 3.1 8B and Qwen 3 8B. The generator had to quote the listing text each dispute is about.
- **Time per case:** median 9.1 seconds and 1.8 LLM calls on the test set with Gemini; the baseline takes 4.5 seconds and one call.
- **The first test run lost, 82 to 84.** Both systems declined every small flaw on items listed as new, because two lines of our decision guide contradicted each other. We fixed the rule on dev cases only and re-ran the test set (88 to 86). We then added the search tool and ran the test set once per model; against the hand labels, Gemini's agent gets 90% and the single prompt 88% (5 cases only the agent got right, 4 only the single prompt; McNemar p = 1.00). The early runs were scored against the outcomes the cases were written for. The test set has now been used three times; nothing was tuned on it, and all runs are in `reports/`.

**What-if**
- **How it works:** each past case keeps its current-policy result (cached), then the judge re-decides it with the proposed rule added as clause PROPOSED-1. The report gives the flips, the before-and-after outcomes and the buyer-win share (`src/dispute_agent/evaluation/whatif.py`).
- **The S09 flip** shows the judge over-applying a new rule. What-if numbers are a first estimate for a person to review, not a decision.

**The models**
- **Which models:** `gemini-flash-lite-latest` (Google cloud, free tier), and two open 8B models on our own PC through Ollama: Llama 3.1 8B and Qwen 3 8B (thinking off). Same 50 test cases, prompts and code; only the judge changes.
- **Results:** agent 90% / 54% / 52%, single prompt 88% / 34% / 44% (Gemini / Llama / Qwen); no gap is statistically significant on 50 cases (largest: Llama, p = 0.06). Of the 21 eligible cases that should be declined, Gemini refunded 1, Llama 19, Qwen 20.
- **Why Gemini stays:** by far the most accurate model we could test (90%), at about 9 s a case. Llama is the default local model, an option when data must stay on the machine.
- **Hardware limits:** one PC with an 8 GB RTX 4060 Ti, which limits local models to about 8 billion parameters at 4-bit; a 10,240-token window keeps Llama fully on the GPU (Qwen ran 11% on the CPU). Bigger models would have run mostly on the CPU, and every run had to finish in one night.
- **Does retrieval change the decisions?** Only a little on our test set. With the policy lists taken out of the prompt, Gemini got 23 of 25 clear cases right with retrieval and 22 without: without it, it declined two missing-accessory claims the policy covers, and it could cite nothing, so every case went to a person. The local models refund almost everything either way. Retrieval's main value is grounding: every recommendation cites a clause staff can check.
- **OpenAI:** not part of the comparison. GPT-5.4 mini only keeps the cloud app running when a Gemini call fails; the key is unpaid (OpenAI's free usage tier, about 50 requests a day), far short of the roughly 500 requests a test run needs, so its judgements are untested and the app marks them "(fallback)".

**Costs and deployment**
- **Free tier:** about one full test run (agent and baseline on 50 cases) uses the daily quota of `gemini-flash-lite-latest`. A real deployment would use a paid tier, which also stops Google using the prompts to improve its products, or a local model, and would remove personal details before any LLM call.
- **Cloud demo:** the app is ready for Streamlit Community Cloud (not deployed yet), with Gemini as the judge and OpenAI (free usage tier) as the fallback if Gemini fails; local models only run on a machine with Ollama.
- **Scaling:** other second-hand marketplaces (Carousell in other markets, Mercari, Vinted) need their own policy pages loaded into the search; the rules in `eligibility.py` would change with their policies.
