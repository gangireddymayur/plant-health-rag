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


SYSTEM_DETAILED = f"""You answer questions about plant health and plant diseases using ONLY the numbered passages provided.
Rules:
- Use only facts stated in the passages. Do not add outside knowledge and do not guess.
- Organise the answer under 2 to 4 short bold headings chosen from what the passages actually contain, for example
  **What it is**, **Symptoms**, **How it spreads**, **Management**, **Where it occurs**. Leave out any heading the passages do not support.
- Under each heading write 1 to 3 short bullet points starting with "- ". Cite the passages you used like [1] or [2][3] at the end of every bullet.
- If the passages do not contain the answer, reply with exactly: {REFUSAL}
- At most about 180 words in total. Do not give chemical product names, doses or schedules."""

STYLES = {"concise": SYSTEM, "detailed": SYSTEM_DETAILED}


SYSTEM_TABLE = f"""You compare two plant-health topics using ONLY the numbered passages provided.
Rules:
- Use only facts stated in the passages. Do not add outside knowledge and do not guess.
- Reply with a markdown table with exactly three columns: Aspect, then one column for each of the two topics (use the topic names as headers).
- Use 4 to 7 rows chosen from what the passages actually contain (for example cause, host crops, symptoms, spread, management).
  Cite passages like [1] inside every cell that states a fact. If the passages do not say something for one topic, write "Not stated in the articles" in that cell.
- After the table add one short sentence summarising the main difference, with a citation.
- If the passages contain nothing about either topic, reply with exactly: {REFUSAL}
- Do not give chemical product names, doses or schedules."""

SYSTEM_LIST = """You answer questions about plant health and plant diseases using ONLY the numbered passages provided.
Rules:
- Use only facts stated in the passages. Do not add outside knowledge and do not guess.
- The user asked for {n} points. Give exactly {n} numbered points (1., 2., ...) if the passages support that many distinct points.
  If they support fewer, give only the supported points and say in one sentence "The articles support only M points on this."  Never invent a point to reach {n}.
- Keep each point to one or two sentences and cite the passages like [1] or [2][3] at the end of every point.
- If the passages do not contain the answer, reply with exactly: """ + REFUSAL + """
- Do not give chemical product names, doses or schedules."""

CONDENSE_SYSTEM = """Rewrite the user's latest question so that it can be understood without the chat history.
Replace pronouns and vague references (it, that, this disease, they, the first one, "the other") with the specific names from the chat.
Do NOT answer the question, do NOT add facts, and keep the meaning. If the question is already self-contained, return it unchanged.
Output only the rewritten question."""

COUNT_RE = re.compile(r"\b(\d{1,2})\s+(?:key\s+|main\s+|important\s+|short\s+)?(points?|bullets?|bullet points|steps|reasons|ways|facts|things|symptoms|differences|tips|methods|causes|signs|examples)\b", re.I)
COMPARE_RES = [
    re.compile(r"differences?\s+(?:between|of)\s+(?P<a>.+?)\s+(?:and|vs\.?|versus|&)\s+(?P<b>.+)$", re.I),
    re.compile(r"\bcompare\s+(?P<a>.+?)\s+(?:and|with|to|vs\.?|versus)\s+(?P<b>.+)$", re.I),
    re.compile(r"\bhow\s+(?:does|do|is|are)\s+(?P<a>.+?)\s+differ\s+from\s+(?P<b>.+)$", re.I),
    re.compile(r"^(?P<a>.+?)\s+(?:vs\.?|versus)\s+(?P<b>.+)$", re.I),
]


def requested_count(question):
    """'Give me 5 points on X' -> 5. Returns None when no sensible number was asked for."""
    m = COUNT_RE.search(question)
    if not m:
        return None
    n = int(m.group(1))
    return n if 2 <= n <= 12 else None


def _clean_entity(text):
    text = COUNT_RE.sub("", text)
    text = re.sub(r"\b(in|with|using|give me|please|briefly|as a table|in a table|table)\b.*$", "", text, flags=re.I)
    return re.sub(r"^(the|a|an)\s+|[?.!,:;\s]+$", "", text.strip(), flags=re.I).strip()


def comparison(question):
    """'What is the difference between A and B?' -> ('A', 'B'), else None."""
    q = question.strip()
    for rx in COMPARE_RES:
        m = rx.search(q)
        if m:
            a, b = _clean_entity(m.group("a")), _clean_entity(m.group("b"))
            if a and b and a.lower() != b.lower() and len(a) < 80 and len(b) < 80:
                return a, b
    return None


def condense(question, history, model=DEFAULT_MODEL, timeout=60):
    """Turn a follow-up such as 'how is it managed?' into a standalone question using the recent chat.
    Falls back to the original question when anything looks wrong."""
    turns = []
    for m in history[-6:]:
        text = re.sub(r"\s+", " ", str(m.get("text", "")))[:350]
        if text:
            turns.append(f"{'User' if m.get('role') == 'user' else 'Assistant'}: {text}")
    if not turns:
        return question
    try:
        r = requests.post(OLLAMA, json={
            "model": model, "stream": False, "think": False,
            "messages": [{"role": "system", "content": CONDENSE_SYSTEM},
                         {"role": "user", "content": "Chat so far:\n" + "\n".join(turns) + f"\n\nLatest question: {question}\nStandalone question:"}],
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 80},
        }, timeout=timeout)
        r.raise_for_status()
        out = clean(r.json()["message"]["content"]).strip().strip('"').splitlines()[0].strip()
    except Exception:
        return question
    return out if 3 <= len(out) <= 300 else question


def build_prompt(question, passages):
    blocks = [f"[{i}] {p['title']} > {p['section']}\n{p['text']}" for i, p in enumerate(passages, 1)]
    return "Passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def clean(text):
    """Remove any hidden reasoning block some models print before the answer."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def citations(answer):
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def generate(prompt, model=DEFAULT_MODEL, timeout=300, style="concise", system=None):
    r = requests.post(OLLAMA, json={
        "model": model, "stream": False, "think": False,
        "messages": [{"role": "system", "content": system or STYLES[style]}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0, "num_ctx": 6144},
    }, timeout=timeout)
    r.raise_for_status()
    return clean(r.json()["message"]["content"])


def _merge(*lists):
    seen, out = set(), []
    for lst in lists:
        for p in lst:
            if p["id"] not in seen:
                seen.add(p["id"])
                out.append(p)
    return out


def ask(question, retriever, model=DEFAULT_MODEL, k=5, mode="dense", min_similarity=0.65, style="concise", history=None):
    t0 = time.time()
    asked = question
    if history:
        question = condense(question, history, model)
    n = requested_count(question)
    pair = comparison(question)
    system, kind = None, style
    if pair:  # retrieve for each side separately so both topics are represented
        sims = [retriever._dense(x, 1)[0][1] for x in pair]
        top_sim = min(sims)
        passages = _merge(retriever.search(pair[0], k=3, mode=mode), retriever.search(pair[1], k=3, mode=mode))
        system, kind = SYSTEM_TABLE, "table"
        if n:  # "in 5 points" means 5 rows, or fewer if the articles support fewer
            system = system.replace("Use 4 to 7 rows chosen from what the passages actually contain",
                                    f"Use exactly {n} rows if the passages support that many distinct aspects (fewer otherwise, and never invent a row); choose them from what the passages actually contain")
    else:
        top_sim = retriever._dense(question, 1)[0][1]
        if n:
            k = min(8, max(k, n))
            system, kind = SYSTEM_LIST.format(n=n), "list"
        passages = retriever.search(question, k=k, mode=mode)
    out = {"question": asked, "standalone_question": question if question != asked else None, "top_similarity": round(top_sim, 3),
           "model": model, "kind": kind, "count": n, "compare": list(pair) if pair else None,
           "retrieved": [{"title": p["title"], "section": p["section"], "url": p["url"]} for p in passages]}
    if top_sim < min_similarity:
        out.update(answer=REFUSAL, abstained=True, reason="out_of_scope", cited=[], sources=[], passages=[])
    else:
        answer = generate(build_prompt(question, passages), model, style=style if style in STYLES else "concise", system=system)
        cited = [i for i in citations(answer) if 1 <= i <= len(passages)]
        refused = answer.startswith("I don't know")
        out.update(
            answer=answer, abstained=refused, reason="model_refused" if refused else "answered",
            cited=cited,
            sources=[{"n": i, "title": passages[i - 1]["title"], "section": passages[i - 1]["section"],
                      "url": passages[i - 1]["url"], "revid": passages[i - 1]["revid"],
                      "text": passages[i - 1]["text"]} for i in cited],
            invalid_citations=[i for i in citations(answer) if not 1 <= i <= len(passages)],
            passages=passages,
        )
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("question")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--style", choices=list(STYLES), default="concise")
    args = ap.parse_args()
    res = ask(args.question, Retriever(), args.model, style=args.style)
    if args.json:
        print(json.dumps(res, indent=2))
        return
    print(f"\n{res['answer']}\n")
    for s in res["sources"]:
        print(f"  [{s['n']}] {s['title']} > {s['section']}\n      {s['url']}")
    print(f"\n({res['reason']}, best similarity {res['top_similarity']}, {res['seconds']} s)")


if __name__ == "__main__":
    main()
