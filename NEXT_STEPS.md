# Next steps (team working notes)

Working list for the group. Not part of the project write-up; delete before
final submission if you do not want it in the repo.

## Before submission

- [x] ~~Push the local commits to GitHub~~ (done 9 Nov: `main` matches `origin/main`).
- [x] ~~Put the names in the contribution table~~ (done 5 Nov: README and report section 12.2).
- [ ] **Check each member's row and add evidence.** The "Main contributions" and "Evidence" columns are still the role defaults; adjust them to what each person really did: `README.md` ("Team and contributions") and the `rows` list in `docs/report_build/update_report.py` (then rebuild the report, see `docs/report_build/README.md`). This is the 20% collaboration criterion: per-member evidence (commits from their own accounts, files they wrote, labelling sheets, meeting notes) matters more than the table itself.
- [x] ~~B1 and B2 label the 50 test cases by hand~~ (done 4 Nov: 25 each, final labels for all 50). Optional: both label the same 10–15 cases so `uv run dispute-agent agreement` can report agreement between them.
- [x] ~~Spot-check the citation sheet~~ (done 9 Nov: Ronak checked all 68 citations, 88% support the decision; the reasons are in `reports/citation_audit_cmp_gemini-flash-lite.csv`, and Ronak's row in the contribution table credits it).
- [x] ~~Deploy to Streamlit Community Cloud~~ (done 6 Nov: https://bc3415-carousell-dispute-agent.streamlit.app/, linked at the top of the README; every push to `main` redeploys it).
- [ ] **Confirm the real submission deadline** (15 Nov was assumed).
- [ ] **Check the Mercari competition rules** allow sharing the 300 sampled listings before making the repo public. If they do not, keep the repo private: dropping `data/listings/listings_sample.jsonl` is not enough, because every case in `data/cases/generated_cases.jsonl` embeds the full listing text and its `mercari_train:<row>` source, `data/labels/labels.csv`, `outputs/runs/` and `reports/whatif_demo.md` carry listing titles, and all of it stays in the git history.
- [ ] **Record and edit the video** (`presentation/VIDEO_SCRIPT.md`; no slides, it records the live app). Re-check the demo cases on the day in the app (S01, S16, G155, the what-if rule), early in the Gemini quota day.
- [x] ~~Remove the README's "Before submission" section~~ (done 14 Nov). This file and `SESSION_HANDOFF.md` stay in the repo but are marked `export-ignore` in `.gitattributes`, so the submitted code copy leaves them out.
- [ ] **Re-read the README** once more before submission.
- [ ] Decide whether to keep `docs/report_build/` in the submitted code: `report_orig.docx` still holds the draft's internal notes ("Not yet agreed by the group" and so on), but without it the report cannot be rebuilt.
- [ ] **Finish the submission folder and zip it** (see "Submission folder" below).

## Submission folder

`submission/` in the repo root is git-ignored: it holds the files to zip for the professor. Built on 14 Nov:

| File | From |
|---|---|
| `Carousell_Dispute_Agent_Full_Report.docx` | Google Drive (the source of truth). Same text as the repo's copy; Drive's was re-saved through Google Docs. |
| `Task_Allocation_BC3409_BC3415.docx` | Google Drive ("BC3409 and BC 3415 Group Project - Task Allocation.docx"); also in the repo root |
| `Carousell_Dispute_Agent_Pitch_Deck.pdf` | Canva export (26 slides, 14 Nov 08:11); also `presentation/` |
| `Carousell_Dispute_Agent_Video_Slides.pdf` | Google Slides export (15 slides); also `presentation/` |
| `carousell-dispute-agent-code/` | `git archive` of `main` (tracked files only: no `.env`, `.venv`, videos or team notes) |

Before zipping:

- [ ] Add the final video (Drue) as `submission/Carousell_Dispute_Agent_Demo_Video.mp4`.
- [ ] Video slides: slide 1 still says "BC3415 · GROUP [number]" (the pitch deck says Group 4).
- [ ] If the report, form or decks changed, download or export them again into `submission/` (and `presentation/`).
- [ ] Refresh the code copy after the last commit:
  `rm -rf submission/carousell-dispute-agent-code && git archive --prefix=carousell-dispute-agent-code/ HEAD | tar -x -C submission`

## Business case (B1, B2)

- [ ] Confirm by hand on Carousell's own pages: the 3.5–6% buyer fee, and the rule that delivery orders must use 'Buy'.
- [ ] Decide whether to add the business value line to the video (about S$400,000 a year in the base case) and the cost side (report section 9.6).
- [ ] Optional timing study: two or three of us each decide 5 test cases without the agent and 5 with it, timing each, to replace the vendor's 30–60 minutes per dispute.
- [ ] Look for: the share of Carousell SG orders that use 'Buy'; any public figure on dispute volumes or support team size; evidence that buyer protection increases use of protected checkout.

## More evaluation, if time allows

- [ ] Gemini ablations on all 50 test cases when the free quota allows (the current probes cover the first 25, all clear cases): `--guide rubric`, `--guide rubric --no-retrieval`, `--no-retrieval`.
- [ ] Repeat runs to measure run-to-run variation.
- [ ] A larger local model on a bigger GPU.
