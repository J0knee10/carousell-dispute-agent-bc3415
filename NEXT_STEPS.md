# Next steps (team working notes)

Working list for the group. Not part of the project write-up; delete before
final submission if you do not want it in the repo.

## Before submission

- [ ] **Push** the local commits to GitHub.
- [x] ~~Put the names in the contribution table~~ (done 5 Nov: README, report section 12.2, slides 1 and 13).
- [ ] **Check each member's row and add evidence.** The "Main contributions" and "Evidence" columns are still the role defaults; adjust them to what each person really did: `README.md` ("Team and contributions") and the `rows` list in `docs/report_build/update_report.py` (then rebuild the report, see `docs/report_build/README.md`). This is the 20% collaboration criterion: per-member evidence (commits from their own accounts, files they wrote, labelling sheets, meeting notes) matters more than the table itself.
- [x] ~~B1 and B2 label the 50 test cases by hand~~ (done 4 Nov: 25 each, final labels for all 50). Optional: both label the same 10–15 cases so `uv run dispute-agent agreement` can report agreement between them.
- [ ] **Spot-check the citation sheet** (`reports/citation_check_cmp_gemini-flash-lite.csv`): fill the `supports` column for about 15 rows.
- [ ] **Deploy to Streamlit Community Cloud** (steps in the README). Put `GEMINI_API_KEY` and `OPENAI_API_KEY` in the app's Secrets (the OpenAI key stays unpaid: it is only the fallback when Gemini fails, about 50 requests a day) and watch the first (Linux) build log. Put the URL in the README.
- [ ] **Confirm the real submission deadline** (15 Nov was assumed).
- [ ] **Check the Mercari competition rules** allow sharing the 300 sampled listings before making the repo public (fallback: keep it private or drop `data/listings/listings_sample.jsonl`).
- [ ] **Record and edit the video** (`presentation/VIDEO_SCRIPT.md`). Re-check the demo cases on the day: `uv run dispute-agent run-case S01 --provider gemini` and `G155`.
- [ ] **Re-read the README** once more before submission.

## Business case (B1, B2)

- [ ] Confirm by hand on Carousell's own pages: the 3.5–6% buyer fee, and the rule that delivery orders must use 'Buy'.
- [ ] Decide whether to add the business value line to the video (about S$400,000 a year in the base case) and the cost side (report section 9.6).
- [ ] Optional timing study: two or three of us each decide 5 test cases without the agent and 5 with it, timing each, to replace the vendor's 30–60 minutes per dispute.
- [ ] Look for: the share of Carousell SG orders that use 'Buy'; any public figure on dispute volumes or support team size; evidence that buyer protection increases use of protected checkout.

## More evaluation, if time allows

- [ ] Gemini ablations on all 50 test cases when the free quota allows (the current probes cover the first 25, all clear cases): `--guide rubric`, `--guide rubric --no-retrieval`, `--no-retrieval`.
- [ ] Repeat runs to measure run-to-run variation.
- [ ] A larger local model on a bigger GPU.
