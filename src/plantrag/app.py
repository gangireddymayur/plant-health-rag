"""A small local web page for asking questions. Run: python -m plantrag.app

It calls the same `ask()` function as the command line, so the answers, citations and refusals
are identical. Everything runs on this machine (Ollama for the language model).
"""
import html
import re

import gradio as gr

from .answer import DEFAULT_MODEL, ask
from .retrieve import Retriever

EXAMPLES = [
    "Which insect carries citrus greening disease, and how does it spread it?",
    "How is tomato yellow leaf curl virus transmitted?",
    "What causes late blight of potato?",
    "What is the capital of France?",
    "What exact fungicide dose should I spray on tomato early blight in Telangana?",
]

_retriever = None


def retriever():
    global _retriever
    if _retriever is None:  # load the embedding model and index once, on the first question
        _retriever = Retriever()
    return _retriever


# ---------- HTML pieces ----------

def render_answer(res):
    text = html.escape(res["answer"])
    text = re.sub(r"\[(\d+)\]", r'<sup class="cite">\1</sup>', text)
    if res["abstained"]:
        return f'<div class="card refusal"><div class="card-label">Answer</div><p class="answer">{text}</p>' \
               f'<p class="hint">{refusal_hint(res)}</p></div>'
    return f'<div class="card"><div class="card-label">Answer</div><p class="answer">{text}</p></div>'


def refusal_hint(res):
    if res["reason"] == "out_of_scope":
        return "This question is outside the 36 plant-health articles, so the language model was not asked."
    return "The retrieved passages did not contain the answer, so the model declined instead of guessing."


def render_status(res):
    ok = not res["abstained"]
    label = "Answered from sources" if ok else "Declined to answer"
    pct = max(0, min(100, round(res["top_similarity"] * 100)))
    return (
        '<div class="meta">'
        f'<span class="pill {"ok" if ok else "warn"}">{label}</span>'
        f'<span class="metric"><span class="metric-label">Match</span>'
        f'<span class="bar"><span style="width:{pct}%"></span></span><b>{res["top_similarity"]:.2f}</b></span>'
        f'<span class="metric"><span class="metric-label">Time</span><b>{res["seconds"]} s</b></span>'
        f'<span class="metric"><span class="metric-label">Model</span><b>{html.escape(res["model"])}</b></span>'
        "</div>"
    )


def render_sources(res):
    if not res["sources"]:
        return ""
    cards = "".join(
        f'<a class="source" href="{html.escape(s["url"])}" target="_blank" rel="noopener">'
        f'<span class="num">{s["n"]}</span>'
        f'<span class="src-text"><span class="src-title">{html.escape(s["title"])}</span>'
        f'<span class="src-section">{html.escape(s["section"])}</span></span>'
        f'<span class="src-open">Wikipedia ↗</span></a>'
        for s in res["sources"]
    )
    return f'<div class="card-label sources-label">Sources</div><div class="sources">{cards}</div>'


def respond(question):
    question = (question or "").strip()
    if not question:
        return "", "", ""
    try:
        res = ask(question, retriever(), DEFAULT_MODEL)
    except Exception as e:  # most likely Ollama is not running
        err = (f'<div class="card refusal"><div class="card-label">Error</div><p class="answer">'
               f'Could not get an answer: {html.escape(str(e))}</p><p class="hint">Is Ollama running with '
               f'<code>{DEFAULT_MODEL}</code> pulled?</p></div>')
        return "", err, ""
    return render_status(res), render_answer(res), render_sources(res)


# ---------- Look ----------

CSS = """
:root, .gradio-container { --accent:#0f9d6b; --accent-dark:#0b7a52; --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; }
body, .gradio-container { background:#f6f8f7 !important; font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif !important; }
footer, .built-with, .show-api, .settings { display:none !important; }
.gradio-container { max-width:880px !important; margin:0 auto !important; padding:0 20px 48px !important; }

.hero { text-align:center; padding:52px 0 26px; }
.badge { display:inline-flex; align-items:center; gap:8px; background:#e6f6ef; color:var(--accent-dark);
  font-size:13px; font-weight:600; padding:6px 14px; border-radius:999px; letter-spacing:.2px; }
.badge i { width:7px; height:7px; border-radius:50%; background:var(--accent); display:inline-block; }
.hero h1 { font-size:38px; text-wrap:balance; line-height:1.15; font-weight:800; color:var(--ink); margin:18px 0 10px; letter-spacing:-.8px; }
.hero h1 span { color:var(--accent); }
.hero p { font-size:16px; color:var(--muted); max-width:620px; margin:0 auto; line-height:1.6; }
.stats { display:flex; justify-content:center; gap:34px; margin-top:26px; flex-wrap:wrap; }
.stat b { display:block; font-size:22px; color:var(--ink); font-weight:800; }
.stat span { font-size:12.5px; color:var(--muted); }

.askbox { background:#fff; border:1px solid var(--line); border-radius:16px; padding:6px;
  box-shadow:0 8px 30px rgba(15,23,42,.06); }
.askbox textarea { border:none !important; box-shadow:none !important; font-size:17px !important;
  color:var(--ink) !important; background:transparent !important; padding:14px 14px 6px !important; }
.askbox label, .askbox .block, .askbox .form { background:transparent !important; border:none !important; box-shadow:none !important; }
.askbox label > span { display:none !important; }
.askbox, .askbox > *, .askbox textarea { --input-background-fill:#fff; --block-background-fill:#fff; --background-fill-secondary:#fff; }
.askbox textarea { background:#fff !important; }
.askbox div, .askbox form { background:#fff !important; }
html, body, gradio-app, .gradio-container, .main, .wrap, .app { background:#f6f8f7 !important; }
.askbox textarea::placeholder { color:#94a3b8 !important; }
#ask-btn { background:var(--accent) !important; border:none !important; color:#fff !important; font-weight:700 !important;
  font-size:15px !important; border-radius:11px !important; height:44px; margin:2px 8px 8px; box-shadow:none !important; }
#ask-btn:hover { background:var(--accent-dark) !important; }

.try { font-size:13px; color:var(--muted); margin:22px 0 10px; font-weight:600; }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.chips button { background:#fff !important; border:1px solid var(--line) !important; color:#334155 !important;
  font-size:13.5px !important; padding:8px 14px !important; border-radius:999px !important; box-shadow:none !important;
  font-weight:500 !important; width:auto !important; min-width:0 !important; flex:0 0 auto !important; }
.chips button:hover { border-color:var(--accent) !important; color:var(--accent-dark) !important; background:#f0faf5 !important; }

.meta { display:flex; align-items:center; gap:18px; flex-wrap:wrap; margin:26px 2px 12px; font-size:13px; color:var(--muted); }
.pill { font-weight:700; font-size:13px; padding:6px 13px; border-radius:999px; }
.pill.ok { background:#e6f6ef; color:var(--accent-dark); }
.pill.warn { background:#fff4e0; color:#a15c07; }
.metric { display:inline-flex; align-items:center; gap:8px; }
.metric-label { text-transform:uppercase; font-size:11px; letter-spacing:.6px; font-weight:600; }
.metric b { color:var(--ink); font-weight:700; }
.bar { width:60px; height:6px; border-radius:6px; background:#e2e8f0; overflow:hidden; display:inline-block; }
.bar span { display:block; height:100%; background:var(--accent); border-radius:6px; }

.card { background:#fff; border:1px solid var(--line); border-radius:16px; padding:22px 26px;
  box-shadow:0 8px 30px rgba(15,23,42,.05); }
.card.refusal { border-left:4px solid #f0a53a; }
.card-label { font-size:11.5px; text-transform:uppercase; letter-spacing:.8px; font-weight:700; color:var(--muted); margin-bottom:10px; }
.answer { font-size:17.5px; line-height:1.7; color:var(--ink); margin:0; }
.hint { font-size:13.5px; color:var(--muted); margin:12px 0 0; }
sup.cite { display:inline-block; background:var(--accent); color:#fff; font-size:11px; font-weight:700;
  min-width:18px; height:18px; line-height:18px; text-align:center; border-radius:6px; margin:0 2px; vertical-align:2px; }

.sources-label { margin:26px 2px 10px; }
.sources { display:grid; gap:10px; }
a.source { display:flex; align-items:center; gap:14px; background:#fff; border:1px solid var(--line); border-radius:14px;
  padding:14px 18px; text-decoration:none !important; transition:all .15s; }
a.source:hover { border-color:var(--accent); box-shadow:0 6px 18px rgba(15,157,107,.12); transform:translateY(-1px); }
.num { flex:0 0 28px; height:28px; border-radius:8px; background:var(--accent); color:#fff; font-weight:700; font-size:13px;
  display:flex; align-items:center; justify-content:center; }
.src-text { display:flex; flex-direction:column; flex:1; min-width:0; }
.src-title { color:var(--ink); font-weight:700; font-size:14.5px; }
.src-section { color:var(--muted); font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.src-open { color:var(--accent-dark); font-size:13px; font-weight:600; white-space:nowrap; }

.foot { text-align:center; color:#94a3b8; font-size:12.5px; margin-top:38px; line-height:1.7; }
"""

HERO = """
<div class="hero">
  <span class="badge"><i></i>Retrieval-augmented generation · runs 100% locally</span>
  <h1>Ask about plant diseases.<br><span>Cited answers, or an honest "I don't know".</span></h1>
  <p>Answers come only from 36 Wikipedia articles on plant diseases, pests and crop protection.
  Every claim is linked to its source, and the system declines when the articles don't contain the answer.</p>
  <div class="stats">
    <div class="stat"><b>92%</b><span>right passage in top 5</span></div>
    <div class="stat"><b>94%</b><span>answers judged correct</span></div>
    <div class="stat"><b>0 / 15</b><span>unanswerable questions answered</span></div>
  </div>
</div>
"""

FOOT = ('<div class="foot">Measured on a 65-question test set written by the author. '
        'Informational only, not agronomic advice.<br>Embeddings: BAAI/bge-small-en-v1.5 · Vector store: Chroma · '
        'LLM: qwen3:8b via Ollama</div>')

FORCE_LIGHT = "() => { document.body.classList.remove('dark'); }"

with gr.Blocks(title="Plant Health RAG", css=CSS, js=FORCE_LIGHT, theme=gr.themes.Base()) as demo:
    gr.HTML(HERO)
    with gr.Group(elem_classes="askbox"):
        q = gr.Textbox(show_label=False, container=False, lines=2,
                       placeholder="Ask a question, e.g. How is tomato yellow leaf curl virus transmitted?")
        btn = gr.Button("Ask", elem_id="ask-btn")
    gr.HTML('<div class="try">Try one of these</div>')
    with gr.Row(elem_classes="chips"):
        chips = [gr.Button(e if len(e) < 60 else e[:57] + "…", size="sm") for e in EXAMPLES]
    status = gr.HTML()
    ans = gr.HTML()
    src = gr.HTML()
    gr.HTML(FOOT)

    outputs = [status, ans, src]
    for trigger in (btn.click, q.submit):
        trigger(respond, q, outputs)
    for chip, text in zip(chips, EXAMPLES):
        chip.click(lambda t=text: t, None, q).then(respond, q, outputs)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1")
