"""Draws docs/results.png from eval/results.json (needs matplotlib: pip install matplotlib)."""
import json

import matplotlib.pyplot as plt

d = json.load(open("eval/results.json"))
ret = d["retrieval"]
names = {"bm25": "Keyword (BM25)", "hybrid": "Keyword + meaning", "dense": "Meaning (embeddings)"}
order = ["bm25", "hybrid", "dense"]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
w = 0.36
for i, (key, label, color) in enumerate([("hit1", "Right passage ranked #1", "#9bd6bd"), ("hit5", "Right passage in top 5", "#0f9d6b")]):
    vals = [ret[m]["all"][key] * 100 for m in order]
    bars = ax[0].bar([x + (i - 0.5) * w for x in range(3)], vals, w, label=label, color=color)
    for b, v in zip(bars, vals):
        ax[0].text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.0f}%", ha="center", fontsize=10)
ax[0].set_xticks(range(3)); ax[0].set_xticklabels([names[m] for m in order]); ax[0].set_ylim(0, 110)
ax[0].set_title(f"Search quality ({ret['dense']['all']['n']} answerable questions, 141 articles)", fontsize=12, loc="left")
ax[0].legend(frameon=False, loc="upper left"); ax[0].spines[["top", "right"]].set_visible(False)

rows = [json.loads(l) for l in open("eval/answers.jsonl")]
ans = [r["top_similarity"] for r in rows if r["type"] == "answerable"]
una = [r["top_similarity"] for r in rows if r["type"] != "answerable"]
bins = [i / 50 for i in range(14, 46)]
ax[1].hist(ans, bins=bins, alpha=.85, color="#0f9d6b", label=f"Answerable ({len(ans)})")
ax[1].hist(una, bins=bins, alpha=.75, color="#f0a53a", label=f"Should decline ({len(una)})")
ax[1].axvline(0.65, color="#0f172a", ls="--", lw=1.4); ax[1].text(0.655, ax[1].get_ylim()[1] * .92, "gate 0.65", fontsize=10)
ax[1].set_title("Closest-passage similarity (the gate overlaps)", fontsize=11, loc="left")
ax[1].set_xlabel("similarity of the closest passage"); ax[1].legend(frameon=False, loc="upper left"); ax[1].spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.savefig("docs/results.png", dpi=170)
