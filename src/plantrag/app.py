"""A small local web page for asking questions. Run: python -m plantrag.app

It calls the same `ask()` function as the command line, so the answers, citations and refusals
are identical. Everything runs on this machine (Ollama for the language model).
"""
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


def format_sources(res):
    if not res["sources"]:
        return "_No sources cited._"
    return "**Sources**\n\n" + "\n".join(f"- **[{s['n']}]** [{s['title']} › {s['section']}]({s['url']})" for s in res["sources"])


def format_status(res):
    label = {"answered": "Answered from the articles", "model_refused": "Refused: passages did not contain the answer",
             "out_of_scope": "Refused: question is outside the articles"}[res["reason"]]
    return f"**{label}** · best match similarity {res['top_similarity']} · {res['seconds']} s · model {res['model']}"


def respond(question):
    question = (question or "").strip()
    if not question:
        return "Type a question first.", "", ""
    try:
        res = ask(question, retriever(), DEFAULT_MODEL)
    except Exception as e:  # most likely Ollama is not running
        return f"Could not get an answer: {e}\n\nIs Ollama running with `{DEFAULT_MODEL}` pulled?", "", ""
    return res["answer"], format_sources(res), format_status(res)


with gr.Blocks(title="Plant Health RAG") as demo:
    gr.Markdown(
        "# Plant Health RAG\n"
        "Ask about plant diseases and pests. Answers come **only** from 36 Wikipedia articles, with cited "
        "sources, and the system says it doesn't know when the articles don't contain the answer. "
        "Not agronomic advice."
    )
    q = gr.Textbox(label="Your question", placeholder="e.g. How is tomato yellow leaf curl virus transmitted?", lines=2)
    btn = gr.Button("Ask", variant="primary")
    status = gr.Markdown()
    ans = gr.Textbox(label="Answer", lines=5, interactive=False)
    src = gr.Markdown(label="Sources")
    gr.Examples(EXAMPLES, inputs=q)
    for trigger in (btn.click, q.submit):
        trigger(respond, q, [ans, src, status])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1")
