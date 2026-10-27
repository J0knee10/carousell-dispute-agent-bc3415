# Labelling guide

Each dispute needs a correct outcome so we can measure the agent. Two people
label every case separately, then settle disagreements together.

## The sheet

`data/labels/labels.csv`, one row per case. Refresh it after new cases are
added with `uv run dispute-agent export-labels`; this never overwrites what you
typed.

| Column | Who fills it | What to put |
|---|---|---|
| `provisional_outcome`, `provisional_eligible` | Already filled | The outcome the case was written for. **Do not look at it before labelling.** Hide the column in Excel or Sheets. |
| `b1_outcome`, `b1_eligible` | B1 | Your own judgement |
| `b2_outcome`, `b2_eligible` | B2 | Your own judgement, without looking at B1's |
| `final_outcome`, `final_eligible` | B1 + B2 + C1 | Only where B1 and B2 disagree, after discussing |
| `notes` | Anyone | Why the case is hard, or what is wrong with it |

Outcome values (type exactly): `full_refund_with_return`, `full_refund_without_return`, `partial_refund`, `decline`.
Eligible values: `true` or `false`.

To read a case, open the app (Review a dispute, set to "all"), or run
`uv run dispute-agent run-case <case_id> --provider mock` and ignore the
mock's answer.

Afterwards, `uv run dispute-agent agreement` reports how often you agreed
(percentage and Cohen's kappa) and lists the disagreements.

## Step 1: is it eligible?

It is **not eligible** (`false`, and the outcome is `decline`) if any of these hold:

- Paid outside the 'Buy' button (bank transfer, cash, PayNow straight to the seller).
- Raised after the dispute window. The window closes at the earlier of: the buyer marking the order complete, or 2 days after tracked delivery, 6 days after expected untracked delivery, or 13 days after a meet-up (longer for Certified items).
- Not received, sent by untracked mail.
- A second dispute on the same order, or the buyer already got a refund outside Carousell.

If the seller did not respond within 24 hours, the buyer's proposal is deemed accepted: label it eligible, with the buyer's proposed outcome.

## Step 2: is the gap significant?

From Carousell's policy:

- **Significant (covered):** a different variation (size, colour, model, version, storage); missing parts or accessories the listing said were included; damage or defects the listing did not disclose, especially ones affecting function; condition clearly worse than stated; an item that deviates extensively from the listing.
- **Not significant (not covered):** wear matching a correctly stated used condition, or flaws the listing disclosed; subjective or minor variations (a slightly different shade, approximate size, "8/10 vs 6/10"); change of mind or ordering the wrong thing; claims about things the listing never promised; damage after delivery; surface wear that does not affect function.

## Step 3: which outcome?

This part is our team's rubric; Carousell's policy does not spell it out.

- `full_refund_with_return`: significant gap that makes the item substantially not what was bought (wrong variation, defect affecting function, major undisclosed damage).
- `partial_refund`: significant gap, but the item is usable and mostly as described (missing minor accessory, small undisclosed cosmetic flaw that contradicts the listing).
- `full_refund_without_return`: significant gap where returning makes no sense (worthless or unsafe to send back). Rare.
- `decline`: no significant gap, or not eligible.

When the evidence conflicts and neither side has proof, pick the outcome you
think Carousell would reach and write "conflicting evidence" in `notes`.

## How the evaluation uses labels

For each case: `final_*` if filled, otherwise B1 and B2's shared answer if they
agree, otherwise the provisional label. The report says how many cases used
each kind, so readers know how much has been checked by people.
