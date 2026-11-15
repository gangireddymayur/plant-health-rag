"""A local chat page for asking questions. Run: python -m plantrag.app

A small FastAPI server: it serves one HTML page (src/plantrag/web/index.html) and two endpoints.
The page calls the same `ask()` function as the command line, so answers, citations and
refusals are identical. Chat history is kept in the browser (localStorage), never on a server.
"""
import re
import threading
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .answer import DEFAULT_MODEL, ask
from .retrieve import Retriever

WEB = Path(__file__).parent / "web"
OLLAMA_TAGS = "http://localhost:11434/api/tags"

app = FastAPI(title="Plant Health RAG")
_retriever = None
_lock = threading.Lock()


def retriever():
    global _retriever
    with _lock:  # load the embedding model and index once, on first use
        if _retriever is None:
            _retriever = Retriever()
        return _retriever


INTRO = ("I'm Plant Health RAG. I answer questions about plant diseases, pests and crop protection "
         "using 36 Wikipedia articles, and I cite my sources. Try asking how a disease spreads or what causes it.")
_SMALLTALK = [
    (r"(hi+|hello+|hey+|hiya|yo|hola|namaste|good (morning|afternoon|evening)|greetings)( (there|bot|everyone))?",
     "Hi! " + INTRO),
    (r"(how are you|how are you doing|how's it going|whats up|what's up|sup)",
     "Doing well, thanks for asking! " + INTRO),
    (r"(who are you|what are you|what is this|what can you do|what do you do|help|how do you work|how does this work)",
     INTRO + " If the articles don't contain the answer, I say so instead of guessing."),
    (r"(thanks|thank you|thank u|thx|ty|cheers|great|awesome|nice|cool|ok|okay)( a lot| so much)?",
     "You're welcome! Ask me another plant-health question any time."),
    (r"(bye|goodbye|see you|see ya|good night|cya)",
     "Goodbye! Come back with more plant-health questions."),
]


def small_talk(question):
    """A fixed, friendly reply for greetings and chit-chat, or None. No language model is involved,
    so nothing can be made up; factual questions never match and go to the cited RAG path."""
    q = re.sub(r"[^\w\s']", "", question.lower()).strip()
    for pattern, reply in _SMALLTALK:
        if re.fullmatch(pattern, q):
            return reply
    return None


class Question(BaseModel):
    question: str
    model: str = DEFAULT_MODEL


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/models")
def models():
    """Chat models installed in Ollama (embedding models are left out)."""
    try:
        r = requests.get(OLLAMA_TAGS, timeout=5)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", []) if "embed" not in m["name"]]
    except Exception:
        return {"models": [], "default": DEFAULT_MODEL, "ollama": False}
    return {"models": names, "default": DEFAULT_MODEL if DEFAULT_MODEL in names else (names or [DEFAULT_MODEL])[0],
            "ollama": True}


@app.post("/api/ask")
def ask_endpoint(body: Question):
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")
    if len(question) > 1000:
        raise HTTPException(400, "Question is too long (max 1000 characters)")
    reply = small_talk(question)
    if reply:
        return {"question": question, "answer": reply, "reason": "small_talk", "abstained": False,
                "top_similarity": 0.0, "seconds": 0.0, "model": body.model, "sources": [], "cited": []}
    try:
        return ask(question, retriever(), body.model)
    except requests.RequestException as e:
        raise HTTPException(503, f"Could not reach Ollama or the model '{body.model}': {e}")


def main():
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="warning")


if __name__ == "__main__":
    print("Plant Health RAG running at http://127.0.0.1:7860  (Ctrl-C to stop)")
    main()
