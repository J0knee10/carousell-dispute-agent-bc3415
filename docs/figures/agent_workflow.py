"""Figure 1 of the report: the agent workflow, with the search_policy tool loop."""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = sys.argv[1]
KIND = {
    "code": ("#e8f0fb", "#2f5597", "Plain code"),
    "llm": ("#fff2cc", "#b8860b", "LLM (judge model)"),
    "rag": ("#e2efda", "#548235", "Retrieval (RAG)"),
    "person": ("#fbe5d6", "#c55a11", "Person"),
}
W, H = 3.15, 1.5
fig, ax = plt.subplots(figsize=(19.8, 8.2), dpi=100)
ax.set_xlim(0, 19.8)
ax.set_ylim(0, 8.2)
ax.axis("off")


def box(x, y, title, sub, kind):
    fill, edge, _ = KIND[kind]
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0,rounding_size=0.18", fc=fill, ec=edge, lw=3))
    ax.text(x + W / 2, y + H * 0.7, title, ha="center", va="center", fontsize=15.5, weight="bold", color="#1b1e26")
    ax.text(x + W / 2, y + H * 0.33, sub, ha="center", va="center", fontsize=12.5, color="#3a3f4b", linespacing=1.3)
    return (x, y)


def arrow(p, q, rad=0.0, label="", lx=0, ly=0, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=18, lw=2.2, color="#555555",
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, ha="center", va="center", fontsize=14,
                style="italic", color="#333333")


# legend
for i, (kind, (fill, edge, label)) in enumerate(KIND.items()):
    x = 0.3 + i * 3.9
    ax.add_patch(FancyBboxPatch((x, 7.55), 0.4, 0.3, boxstyle="round,pad=0,rounding_size=0.03", fc=fill, ec=edge, lw=2))
    ax.text(x + 0.55, 7.7, label, va="center", fontsize=15, color="#333333")

top, mid, bot = 5.6, 3.25, 0.9
xs = [0.3, 4.4, 8.5, 12.6, 16.6]
box(xs[0], top, "1. Intake", "listing, order,\ndispute, chat", "code")
box(xs[1], top, "2. Eligibility", "plain-code rules\n+ clause IDs", "code")
box(xs[2], top, "3. Claim matching", "promises vs\nproblems = gaps", "llm")
box(xs[3], top, "4. Retrieval", "hybrid search,\none query per gap", "rag")
box(xs[4], top, "5. Judgement", "outcome, confidence,\nreasons, citations", "llm")
box(xs[1], mid, "Rule-based result", "not covered, or seller\nmissed 24h deadline", "code")
box(xs[3], mid, "search_policy tool", "extra clauses, only when\nthe judge asks (1 round)", "rag")
box(xs[4], bot, "6. Check", "escalate if unsure,\nuncited or inconsistent", "code")
box(xs[3] - 0.6, bot, "7. Staff decides", "pause: approve\nor override", "person")
box(xs[1] + 0.6, bot, "8. Message drafts", "to buyer\nand seller", "llm")

yc = top + H / 2
for a, b in zip(xs, xs[1:]):
    arrow((a + W, yc), (b - 0.05, yc))
ax.text(xs[1] + W + 0.47, yc - 0.32, "covered", fontsize=13, style="italic", color="#333333", ha="center")
# not covered
arrow((xs[1] + W / 2, top), (xs[1] + W / 2, mid + H + 0.03))
ax.text(xs[1] + W / 2 + 0.2, top - 0.42, "not covered or procedural", fontsize=14, style="italic", color="#333333")
arrow((xs[1] + W + 0.05, mid + H / 2), (xs[3] - 0.6 + W * 0.5, bot + H + 0.05), rad=-0.15)
# tool loop
arrow((xs[4] + 0.35, top), (xs[3] + W, mid + H * 0.75), rad=-0.25, label="calls the tool", lx=-0.9, ly=0.15)
arrow((xs[3] + W, mid + H * 0.25), (xs[4] + 0.9, top - 0.02), rad=0.45, label="new clauses", lx=1.0, ly=-0.25)
# judgement to check
arrow((xs[4] + W * 0.8, top), (xs[4] + W * 0.8, bot + H + 0.05))
arrow((xs[4], bot + H / 2), (xs[3] - 0.6 + W + 0.05, bot + H / 2))
arrow((xs[3] - 0.6, bot + H / 2), (xs[1] + 0.6 + W + 0.05, bot + H / 2), label="logged", ly=0.3)

plt.savefig(OUT, bbox_inches="tight", facecolor="white")
print("saved", OUT)
