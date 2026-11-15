"""Answer a question from the retrieved passages, with citations, or say "I don't know".

Two guards against made-up answers:
  1. If even the best passage is not similar enough to the question, the question is outside the
     articles, so the model is not asked at all.
  2. Otherwise the model must answer only from the numbered passages and cite them, and it is told
     to refuse when the passages do not contain the answer.
"""
import argparse
import json
import re
import time

import requests

from .retrieve import Retriever

OLLAMA = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3:8b"
REFUSAL = "I don't know based on the available articles."

SYSTEM = f"""You answer questions about plant health and plant diseases using ONLY the numbered passages provided.
Rules:
- Use only facts stated in the passages. Do not add outside knowledge.
- Cite the passages you used like [1] or [2][3] right after each claim.
- If the passages do not contain the answer, reply with exactly: {REFUSAL}
- Be concise: at most 4 sentences. Do not give chemical product names, doses or schedules."""


def build_prompt(question, passages):
    blocks = [f"[{i}] {p['title']} > {p['section']}\n{p['text']}" for i, p in enumerate(passages, 1)]
    return "Passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def clean(text):
    """Remove any hidden reasoning block some models print before the answer."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def citations(answer):
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def generate(prompt, model=DEFAULT_MODEL, timeout=300):
    r = requests.post(OLLAMA, json={
        "model": model, "stream": False, "think": False,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0, "num_ctx": 6144},
    }, timeout=timeout)
    r.raise_for_status()
    return clean(r.json()["message"]["content"])


def ask(question, retriever, model=DEFAULT_MODEL, k=5, mode="dense", min_similarity=0.65):
    t0 = time.time()
    top_sim = retriever._dense(question, 1)[0][1]
    passages = retriever.search(question, k=k, mode=mode)
    out = {"question": question, "top_similarity": round(top_sim, 3), "model": model,
           "retrieved": [{"title": p["title"], "section": p["section"], "url": p["url"]} for p in passages]}
    if top_sim < min_similarity:
        out.update(answer=REFUSAL, abstained=True, reason="out_of_scope", cited=[], sources=[])
    else:
        answer = generate(build_prompt(question, passages), model)
        cited = [n for n in citations(answer) if 1 <= n <= len(passages)]
        refused = answer.startswith("I don't know")
        out.update(
            answer=answer, abstained=refused, reason="model_refused" if refused else "answered",
            cited=cited,
            sources=[{"n": n, "title": passages[n - 1]["title"], "section": passages[n - 1]["section"],
                      "url": passages[n - 1]["url"], "revid": passages[n - 1]["revid"]} for n in cited],
            invalid_citations=[n for n in citations(answer) if not 1 <= n <= len(passages)],
        )
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("question")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = ask(args.question, Retriever(), args.model)
    if args.json:
        print(json.dumps(res, indent=2))
        return
    print(f"\n{res['answer']}\n")
    for s in res["sources"]:
        print(f"  [{s['n']}] {s['title']} > {s['section']}\n      {s['url']}")
    print(f"\n({res['reason']}, best similarity {res['top_similarity']}, {res['seconds']} s)")


if __name__ == "__main__":
    main()
