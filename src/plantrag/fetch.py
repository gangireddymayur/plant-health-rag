"""Download the plant-health articles from Wikipedia with their exact revision ids.

Wikipedia text is licensed CC BY-SA 4.0. The articles are fetched on demand and are not stored in
this repository. `data/corpus_manifest.json` records every title, revision and URL, so the
corpus can be rebuilt exactly and every answer can be attributed.
"""
import argparse
import json
import re
import time
from pathlib import Path

import requests

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "plant-doctor-rag/0.1 (portfolio learning project)"}

# Diseases and pests that the LeafLens app can name, plus general background articles.
TITLES = [
    "Apple scab", "Botryosphaeria obtusa", "Gymnosporangium juniperi-virginianae", "Powdery mildew",
    "Corn grey leaf spot", "Puccinia sorghi", "Northern corn leaf blight", "Black rot (grape disease)",
    "Esca (grape disease)", "Citrus greening disease", "Diaphorina citri", "Xanthomonas arboricola pv. pruni",
    "Bacterial leaf spot of peppers and tomato", "Alternaria solani", "Phytophthora infestans",
    "Diplocarpon earlianum", "Tomato leaf mold", "Septoria lycopersici", "Tetranychus urticae",
    "Corynespora cassiicola", "Tomato yellow leaf curl virus", "Tomato mosaic virus",
    "Plant pathology", "Plant disease", "Plant disease resistance", "Plant disease epidemiology",
    "Fungicide", "Crop rotation", "Integrated pest management", "Plant virus", "Whitefly", "Mulch",
    "Leaf spot", "Blight", "Rust (fungus)", "Oomycete",
]


def get(params):
    for attempt in range(6):
        r = requests.get(API, params={**params, "format": "json"}, headers=HEADERS, timeout=60)
        if r.status_code == 200 and r.text.startswith("{"):
            return r.json()
        time.sleep(4 * (attempt + 1))  # polite back-off when rate limited
    raise RuntimeError(f"Wikipedia request failed ({r.status_code}) for {params.get('titles')}")


def fetch_article(title):
    data = get({
        "action": "query", "titles": title, "redirects": 1,
        "prop": "extracts|revisions|info", "explaintext": 1, "exsectionformat": "wiki",
        "rvprop": "ids|timestamp", "inprop": "url",
    })
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page:
        raise ValueError(f"No Wikipedia article called {title!r}")
    rev = page["revisions"][0]
    return {
        "title": page["title"], "requested_title": title, "pageid": page["pageid"],
        "revid": rev["revid"], "timestamp": rev["timestamp"], "url": page["fullurl"],
        "license": "CC BY-SA 4.0", "text": page["extract"],
        "words": len(re.findall(r"\w+", page["extract"])),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="data/corpus")
    ap.add_argument("--manifest", default="data/corpus_manifest.json")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, title in enumerate(TITLES, 1):
        art = fetch_article(title)
        (out / f"{art['pageid']}.json").write_text(json.dumps(art, ensure_ascii=False))
        manifest.append({k: art[k] for k in ("title", "requested_title", "pageid", "revid", "timestamp", "url", "license", "words")})
        print(f"[{i:2d}/{len(TITLES)}] {art['title']:46s} {art['words']:6d} words  rev {art['revid']}")
        time.sleep(1.5)
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\n{len(manifest)} articles, {sum(m['words'] for m in manifest):,} words in total")


if __name__ == "__main__":
    main()
