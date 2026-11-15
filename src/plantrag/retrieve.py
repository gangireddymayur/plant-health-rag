"""Find the passages that best match a question.

Three ways to search, so they can be compared honestly:
  bm25    keyword matching (finds exact words, misses paraphrases)
  dense   meaning-based matching with embeddings (finds paraphrases, can miss exact terms)
  hybrid  both rankings merged with Reciprocal Rank Fusion
"""
import argparse
import json
import re
from pathlib import Path

from .config import COLLECTION, EMBED_MODEL, QUERY_PREFIX, device

STOP = set("a an and are as at be by can do does for from how in is it of on or that the this to was what when where which who why will with you your".split())


def tokenize(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def rrf(rankings, k=60):
    """Reciprocal Rank Fusion: merge several ranked id lists into one. Higher is better."""
    score = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            score[cid] = score.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(score.items(), key=lambda kv: kv[1], reverse=True)


class Retriever:
    def __init__(self, chunks_file="data/chunks.jsonl", index_dir="data/index", model_name=EMBED_MODEL):
        import chromadb  # imported here so the pure helpers above load without the heavy libraries
        from rank_bm25 import BM25Okapi

        self.chunks = [json.loads(line) for line in Path(chunks_file).read_text().splitlines() if line.strip()]
        self.by_id = {c["id"]: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokenize(f"{c['title']} {c['section']} {c['text']}") for c in self.chunks])
        self.collection = chromadb.PersistentClient(path=index_dir).get_collection(COLLECTION)
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=device())
        return self._model

    def _bm25(self, query, k):
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.chunks[i]["id"], float(scores[i])) for i in order if scores[i] > 0]

    def _dense(self, query, k):
        vec = self.model.encode([QUERY_PREFIX + query], normalize_embeddings=True)[0].tolist()
        res = self.collection.query(query_embeddings=[vec], n_results=k)
        return [(cid, 1.0 - d) for cid, d in zip(res["ids"][0], res["distances"][0])]  # cosine similarity

    def search(self, query, k=5, mode="hybrid", pool=30):
        if mode == "bm25":
            hits = self._bm25(query, k)
        elif mode == "dense":
            hits = self._dense(query, k)
        elif mode == "hybrid":
            fused = rrf([[i for i, _ in self._bm25(query, pool)], [i for i, _ in self._dense(query, pool)]])
            hits = fused[:k]
        else:
            raise ValueError(f"unknown mode {mode!r}")
        return [{**self.by_id[cid], "score": s, "mode": mode} for cid, s in hits]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("question")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    args = ap.parse_args()
    for i, h in enumerate(Retriever().search(args.question, args.k, args.mode), 1):
        print(f"{i}. [{h['score']:.3f}] {h['title']} > {h['section']}\n   {h['text'][:230]}...\n")


if __name__ == "__main__":
    main()
