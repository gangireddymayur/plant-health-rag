"""Measure the system on eval/questions.json.

Retrieval: for each answerable question, does search put a passage that really contains the
evidence in the top k? (Hit@k, and MRR = how high the first such passage ranks.)
Answers: are they correct, backed by their cited passages, and does the system refuse when it should?
Questions marked "dev" are for tuning; "test" questions are reported on without tuning.
"""
import argparse
import json
import re
import time
from pathlib import Path

from .answer import ask, build_prompt, generate
from .retrieve import Retriever

MODES = ("bm25", "dense", "hybrid")


def gold_ids(chunks, q):
    """Ids of passages that count as evidence for an answerable question."""
    section = q.get("gold_section", ".")
    return {c["id"] for c in chunks
            if c["title"] == q["gold_title"] and re.search(section, c["section"], re.I)
            and all(re.search(p, c["text"], re.I) for p in q["must_contain"])}


def reciprocal_rank(ranked_ids, gold, k=10):
    for rank, cid in enumerate(ranked_ids[:k], 1):
        if cid in gold:
            return 1.0 / rank
    return 0.0


def hit_at_k(ranked_ids, gold, k):
    return float(any(cid in gold for cid in ranked_ids[:k]))


def keyword_correct(answer, groups):
    """True when every group of keywords has at least one word present in the answer."""
    low = answer.lower()
    return all(any(w.lower() in low for w in group) for group in groups)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def subsets(rows):
    return {"dev": [r for r in rows if r["split"] == "dev"], "test": [r for r in rows if r["split"] == "test"], "all": rows}


def retrieval_report(retriever, questions):
    answerable = [q for q in questions if q["type"] == "answerable"]
    rows = {m: [] for m in MODES}
    for q in answerable:
        gold = gold_ids(retriever.chunks, q)
        for m in MODES:
            ranked = [h["id"] for h in retriever.search(q["question"], k=10, mode=m)]
            titles = [retriever.by_id[i]["title"] for i in ranked]
            rows[m].append({
                "id": q["id"], "split": q["split"], "n_gold": len(gold),
                "hit1": hit_at_k(ranked, gold, 1), "hit3": hit_at_k(ranked, gold, 3), "hit5": hit_at_k(ranked, gold, 5),
                "mrr": reciprocal_rank(ranked, gold), "article5": float(q["gold_title"] in titles[:5]),
                "missed": [q["question"]] if hit_at_k(ranked, gold, 5) == 0 else [],
            })
    out = {}
    for m in MODES:
        out[m] = {name: {k: round(mean(r[k] for r in part), 3) for k in ("hit1", "hit3", "hit5", "mrr", "article5")} | {"n": len(part)}
                  for name, part in subsets(rows[m]).items()}
        out[m]["missed_at_5"] = [x for r in rows[m] for x in r["missed"]]
    return out


def similarity_scan(retriever, questions, thresholds=(0.45, 0.5, 0.55, 0.6, 0.65, 0.7)):
    """How well does 'best passage similarity' separate answerable from unanswerable questions?"""
    sims = [(q, retriever._dense(q["question"], 1)[0][1]) for q in questions]
    out = []
    for t in thresholds:
        row = {"threshold": t}
        for name in ("dev", "test", "all"):
            part = [(q, s) for q, s in sims if name == "all" or q["split"] == name]
            ans = [s for q, s in part if q["type"] == "answerable"]
            una = [s for q, s in part if q["type"] != "answerable"]
            row[name] = {"answerable_blocked": round(mean(s < t for s in ans), 3), "unanswerable_blocked": round(mean(s < t for s in una), 3)}
        out.append(row)
    return out, {q["id"]: round(s, 3) for q, s in sims}


JUDGE_PROMPT = """You are checking an answer against source passages.
Passages:
{passages}

Answer to check:
{answer}

Is EVERY factual claim in the answer supported by the passages above (ignoring the [n] citation markers)?
Reply on one line in exactly this form: VERDICT: YES or VERDICT: NO, then a short reason."""


def judge(passages, answer, model):
    text = "\n\n".join(f"[{i}] {p['title']} > {p['section']}\n{p['text']}" for i, p in enumerate(passages, 1))
    import requests
    r = requests.post("http://localhost:11434/api/chat", json={
        "model": model, "stream": False, "think": False, "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [{"role": "user", "content": JUDGE_PROMPT.format(passages=text, answer=answer)}]}, timeout=300)
    reply = r.json()["message"]["content"].strip()
    m = re.search(r"VERDICT:\s*(YES|NO)", reply, re.I)
    return (m.group(1).upper() == "YES" if m else None), reply


def answer_report(retriever, questions, model, judge_model, k, min_similarity, out_path, mode="dense", style="concise"):
    rows = []
    for i, q in enumerate(questions, 1):
        res = ask(q["question"], retriever, model=model, k=k, mode=mode, min_similarity=min_similarity, style=style)
        row = {"id": q["id"], "split": q["split"], "type": q["type"], "question": q["question"], "answer": res["answer"],
               "abstained": res["abstained"], "reason": res["reason"], "top_similarity": res["top_similarity"], "cited": res["cited"]}
        if q["type"] == "answerable":
            passages = retriever.search(q["question"], k=k, mode=mode)
            gold = gold_ids(retriever.chunks, q)
            row["correct"] = (not res["abstained"]) and keyword_correct(res["answer"], q["answer_keywords"])
            row["cites_gold"] = any(passages[n - 1]["id"] in gold for n in res["cited"])
            row["has_citation"] = bool(res["cited"])
            if not res["abstained"]:
                row["faithful"], row["judge_reply"] = judge(passages, res["answer"], judge_model)
        rows.append(row)
        Path(out_path).write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
        print(f"[{i:2d}/{len(questions)}] {q['id']} {q['type']:19s} -> {row['reason']}", flush=True)
    summary = {}
    for name, part in subsets(rows).items():
        ans = [r for r in part if r["type"] == "answerable"]
        una = [r for r in part if r["type"] != "answerable"]
        answered = [r for r in ans if not r["abstained"]]
        summary[name] = {
            "answerable": len(ans), "unanswerable": len(una),
            "correct_rate": round(mean(r["correct"] for r in ans), 3),
            "false_refusal_rate": round(mean(r["abstained"] for r in ans), 3),
            "cites_gold_rate": round(mean(r["cites_gold"] for r in answered), 3),
            "has_citation_rate": round(mean(r["has_citation"] for r in answered), 3),
            "faithful_rate": round(mean(bool(r.get("faithful")) for r in answered), 3),
            "correct_refusal_rate": round(mean(r["abstained"] for r in una), 3),
            "hallucination_rate_on_unanswerable": round(mean(not r["abstained"] for r in una), 3),
        }
    return summary, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--retrieval", action="store_true")
    ap.add_argument("--answers", action="store_true")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--judge-model", default="qwen3:14b")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-similarity", type=float, default=0.65)
    ap.add_argument("--mode", choices=MODES, default="dense")
    ap.add_argument("--out", default="eval/results.json")
    ap.add_argument("--answers-out", default="eval/answers.jsonl")
    ap.add_argument("--style", choices=["concise", "detailed"], default="concise")
    args = ap.parse_args()
    questions = json.load(open(args.questions))
    retriever = Retriever()
    results = {"questions": len(questions)}
    if args.retrieval:
        results["retrieval"] = retrieval_report(retriever, questions)
        results["similarity_scan"], results["top_similarity_by_question"] = similarity_scan(retriever, questions)
    if args.answers:
        t0 = time.time()
        summary, _ = answer_report(retriever, questions, args.model, args.judge_model, args.k, args.min_similarity, args.answers_out, args.mode, args.style)
        results["answers"] = {"model": args.model, "judge_model": args.judge_model, "k": args.k, "mode": args.mode, "style": args.style, "min_similarity": args.min_similarity,
                              "minutes": round((time.time() - t0) / 60, 1), **summary}
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(json.dumps({k: v for k, v in results.items() if k != "top_similarity_by_question"}, indent=2))


if __name__ == "__main__":
    main()
