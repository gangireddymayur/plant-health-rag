"""Tests for the chat features: comparison tables, exact point counts and follow-up questions.

Run: PYTHONPATH=src python eval/features.py     (needs Ollama; takes about 10 minutes)
Writes eval/features_results.json. Checks are mechanical (counts, table shape, keywords) plus the same
LLM faithfulness checker used for the main evaluation.
"""
import json
import re
import time
from pathlib import Path

from plantrag.answer import ask
from plantrag.evaluate import judge
from plantrag.retrieve import Retriever

MODEL, JUDGE = "qwen3:8b", "qwen3:14b"

COMPARE = [
    "What is the difference between early blight and late blight?",
    "What is the difference between stem rust and wheat leaf rust?",
    "Compare Karnal bunt and loose smut",
    "Difference between the pink bollworm and the boll weevil",
    "What is the difference between Panama disease and black sigatoka?",
    "Compare the Colorado potato beetle and the Japanese beetle",
    "How does downy mildew differ from powdery mildew?",
    "Compare fire blight and citrus canker",
    "What is the difference between coffee leaf rust and blister blight?",
    "Compare the desert locust and the fall armyworm",
    "Difference between aphids and whiteflies",
    "Compare corn smut and loose smut",
]
COUNT = [
    ("Give me 5 points on rice blast", 5), ("Give me 3 points about aphids", 3), ("4 key facts about Karnal bunt", 4),
    ("Tell me 6 points about late blight of potato", 6), ("5 points on crop rotation", 5),
    ("10 points on integrated pest management", 10), ("Give me 7 points on the fall armyworm", 7),
    ("3 ways to manage root-knot nematodes", 3), ("5 symptoms of tomato yellow leaf curl virus", 5),
    ("Give me 8 points on the Green Revolution in India", 8),
]
# (earlier question, earlier answer, follow-up, words that must appear in the rewritten question)
FOLLOW = [
    ("Which fungus causes rice blast?", "Magnaporthe grisea causes rice blast.", "how is it spread?", ["rice blast", "magnaporthe"]),
    ("What is Karnal bunt?", "Karnal bunt is a fungal disease of wheat.", "which crop does it affect?", ["karnal"]),
    ("Tell me about the pink bollworm", "The pink bollworm is a moth pest of cotton.", "what does it damage?", ["pink bollworm"]),
    ("What causes late blight of potato?", "Phytophthora infestans causes late blight.", "and how can it be managed?", ["late blight", "phytophthora"]),
    ("What is the fall armyworm?", "The fall armyworm is a moth whose larvae damage maize.", "where is it native to?", ["fall armyworm"]),
    ("What is Panama disease?", "Panama disease is a fungal wilt of banana.", "which banana variety did it destroy?", ["panama"]),
    ("What is neem oil?", "Neem oil is a vegetable oil used as a pesticide.", "which tree does it come from?", ["neem"]),
    ("Tell me about citrus greening", "Citrus greening is a bacterial disease of citrus.", "which insect spreads it?", ["citrus greening", "huanglongbing"]),
]
# self-contained question after unrelated history: must keep its own topic and not drag in the old one
CONTROL = [
    ("Which fungus causes rice blast?", "Magnaporthe grisea causes rice blast.", "What causes late blight of potato?", ["late blight"], "rice blast"),
    ("What is Karnal bunt?", "Karnal bunt is a fungal disease of wheat.", "How is tomato yellow leaf curl virus transmitted?", ["tomato yellow leaf curl"], "karnal"),
    ("Tell me about aphids", "Aphids are small sap-sucking insects.", "What is crop rotation?", ["crop rotation"], "aphid"),
    ("What is neem oil?", "Neem oil is a vegetable oil.", "Which insect spreads citrus greening disease?", ["citrus greening"], "neem"),
]


def table_shape(answer):
    rows = [l for l in answer.splitlines() if l.strip().startswith("|") and not re.fullmatch(r"\s*\|?[\s:\-|]+\|?\s*", l)]
    cols = len(rows[0].strip().strip("|").split("|")) if rows else 0
    return len(rows) - 1, cols  # data rows, columns


def numbered(answer):
    return len(re.findall(r"^\s*\d+[.)]\s+", answer, flags=re.M))


def main():
    R = Retriever()
    out = {"compare": [], "count": [], "follow": [], "control": []}
    t0 = time.time()
    for q in COMPARE:
        r = ask(q, R, MODEL, style="detailed")
        rows, cols = table_shape(r["answer"]) if not r["abstained"] else (0, 0)
        cited_rows = sum(bool(re.search(r"\[\d+\]", l)) for l in r["answer"].splitlines() if l.strip().startswith("|"))
        faithful = judge(r["passages"], r["answer"], JUDGE)[0] if not r["abstained"] else None
        out["compare"].append({"q": q, "kind": r["kind"], "answered": not r["abstained"], "rows": rows, "cols": cols, "cited_rows": cited_rows,
                               "table_ok": rows >= 3 and cols == 3, "faithful": faithful, "answer": r["answer"]})
        print("compare", q[:50], r["kind"], rows, cols, faithful, flush=True)
    for q, n in COUNT:
        r = ask(q, R, MODEL, style="detailed")
        got = numbered(r["answer"]) if not r["abstained"] else 0
        says_fewer = bool(re.search(r"support only|only \d+ points", r["answer"], re.I))
        faithful = judge(r["passages"], r["answer"], JUDGE)[0] if not r["abstained"] else None
        out["count"].append({"q": q, "asked": n, "got": got, "answered": not r["abstained"], "exact": got == n,
                             "honest_if_fewer": got == n or says_fewer, "faithful": faithful, "answer": r["answer"]})
        print("count", q[:50], n, got, says_fewer, faithful, flush=True)
    for q0, a0, q1, words in FOLLOW:
        hist = [{"role": "user", "text": q0}, {"role": "bot", "text": a0}]
        r = ask(q1, R, MODEL, style="detailed", history=hist)
        s = (r["standalone_question"] or "").lower()
        out["follow"].append({"q": q1, "standalone": r["standalone_question"], "resolved": any(w in s for w in words), "answered": not r["abstained"]})
        print("follow", q1, "->", r["standalone_question"], not r["abstained"], flush=True)
    for q0, a0, q1, words, bad in CONTROL:
        hist = [{"role": "user", "text": q0}, {"role": "bot", "text": a0}]
        r = ask(q1, R, MODEL, style="detailed", history=hist)
        s = (r["standalone_question"] or q1).lower()
        out["control"].append({"q": q1, "standalone": r["standalone_question"], "kept_topic": all(w in s for w in words), "no_leak": bad not in s})
        print("control", q1, "->", r["standalone_question"], flush=True)

    def rate(rows, key):
        vals = [x[key] for x in rows if x[key] is not None]
        return round(sum(bool(v) for v in vals) / len(vals), 3) if vals else None
    out["summary"] = {
        "compare": {"n": len(out["compare"]), "answered": rate(out["compare"], "answered"), "table_ok": rate(out["compare"], "table_ok"),
                    "faithful": rate(out["compare"], "faithful")},
        "count": {"n": len(out["count"]), "answered": rate(out["count"], "answered"), "exact_count": rate(out["count"], "exact"),
                  "exact_or_honest": rate(out["count"], "honest_if_fewer"), "faithful": rate(out["count"], "faithful")},
        "follow": {"n": len(out["follow"]), "resolved": rate(out["follow"], "resolved"), "answered": rate(out["follow"], "answered")},
        "control": {"n": len(out["control"]), "kept_topic": rate(out["control"], "kept_topic"), "no_leak": rate(out["control"], "no_leak")},
        "minutes": round((time.time() - t0) / 60, 1),
    }
    Path("eval/features_results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out["summary"], indent=2))


if __name__ == "__main__":
    main()
