"""Build the search index: chunk every article, embed each passage and store it in Chroma."""
import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from .chunk import chunk_article, embedding_text
from .config import COLLECTION, EMBED_MODEL, device

def load_chunks(corpus_dir):
    chunks = []
    for f in sorted(Path(corpus_dir).glob("*.json")):
        chunks += chunk_article(json.loads(f.read_text()))
    return chunks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default="data/corpus")
    ap.add_argument("--index-dir", default="data/index")
    ap.add_argument("--chunks-file", default="data/chunks.jsonl")
    ap.add_argument("--model", default=EMBED_MODEL)
    args = ap.parse_args()

    chunks = load_chunks(args.corpus_dir)
    if not chunks:
        raise SystemExit("No passages found. Run `python -m plantrag.fetch` first.")
    Path(args.chunks_file).write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks))
    print(f"{len(chunks)} passages from {len({c['title'] for c in chunks})} articles "
          f"({sum(c['words'] for c in chunks):,} words)")

    model = SentenceTransformer(args.model, device=device())
    vectors = model.encode([embedding_text(c) for c in chunks], batch_size=64, normalize_embeddings=True, show_progress_bar=True)

    client = chromadb.PersistentClient(path=args.index_dir)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    for i in range(0, len(chunks), 500):
        part = chunks[i:i + 500]
        col.add(
            ids=[c["id"] for c in part], embeddings=vectors[i:i + 500].tolist(),
            documents=[c["text"] for c in part],
            metadatas=[{k: c[k] for k in ("title", "section", "url", "revid")} for c in part],
        )
    print(f"Indexed {col.count()} passages with {args.model} on {device()} into {args.index_dir}")


if __name__ == "__main__":
    main()
