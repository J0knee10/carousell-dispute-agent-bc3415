# What-if policy test: demo run

- Proposed rule: "If a promised accessory is missing, the buyer gets a full refund with return instead of a partial refund."
- Judge: `gemini/gemini-flash-lite-latest`, run on 28 Oct 2026 (source: `outputs/whatif/whatif_20261028_231316.json`)
- Seed cases re-judged: 15; outcomes that flipped: 4 (27%)
- Buyer-win share: 53% before, 60% after

| Case | Item | Gaps found | Before | After | Flipped | Cites the new rule |
|---|---|---|---|---|---|---|
| S01 | PS Vita Slim | missing_part | partial_refund | full_refund_with_return | yes | yes |
| S02 | Mint iPhone 6 AT&T 64GB | different_variation | full_refund_with_return | full_refund_with_return |  |  |
| S03 | Zte Zmax Pro | undisclosed_defect | full_refund_with_return | full_refund_with_return |  |  |
| S04 | Fitbit Alta | missing_part | partial_refund | full_refund_with_return | yes | yes |
| S05 | Stunning Vintage Dragon Ring | undisclosed_defect | full_refund_with_return | full_refund_with_return |  |  |
| S06 | Lululemon Size 2 Wunder Under Crop | different_variation | full_refund_with_return | full_refund_with_return |  |  |
| S07 | Paper Mario Sticker Star game for N 3DS | change_of_mind | decline | decline |  |  |
| S08 | New! Mainstays 8 Piece Bedding Set! | deviates_from_listing | decline | decline |  |  |
| S09 | Xbox one elite controller | not_in_listing | decline | full_refund_with_return | yes | yes |
| S10 | J. Crew French Bulldog Sweater | wear_consistent_with_listing | decline | decline |  |  |
| S11 | Camo Speed Shorts Lululemon 6 Blue Lotus | different_variation | decline | decline |  |  |
| S12 | Nike foamposite | condition_worse_than_listed, wear_consistent_with_listing | decline | decline |  |  |
| S13 | iPhone 4 | SALE HURRY FAST | wear_consistent_with_listing, wear_consistent_with_listing | decline | decline |  |  |
| S14 | Vintage Nike Sportswear Crewneck | undisclosed_defect | partial_refund | partial_refund |  |  |
| S15 | Halloween costume | missing_part | partial_refund | full_refund_with_return | yes | yes |

S01, S04 and S15 flip as intended (missing accessories). S09 is a wrong flip: that buyer wanted accessories the listing never promised. A flip also mixes the rule's effect with run-to-run variation, so what-if numbers are a first estimate for a person to review.
