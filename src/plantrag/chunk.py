"""Cut articles into passages for retrieval.

A passage is a few sentences from one section of one article, long enough to hold a complete idea
and short enough to be matched precisely. Each passage keeps its article title, section path and
URL, so an answer can point back to where it came from.
"""
import re

SKIP_SECTIONS = {
    "references", "external links", "see also", "further reading", "notes", "bibliography",
    "footnotes", "sources", "gallery", "citations", "general references",
}
HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def words(text):
    return len(text.split())


def split_sections(text, title):
    """Return [(section_path, body)] in reading order, dropping reference-style sections."""
    sections, stack, buf = [], [], []
    path = "Introduction"

    def flush():
        body = "\n".join(buf).strip()
        if body:
            sections.append((path, body))
        buf.clear()

    skipping = False
    for line in text.splitlines():
        m = HEADING.match(line.strip())
        if not m:
            if not skipping:
                buf.append(line)
            continue
        flush()
        level, name = len(m.group(1)), m.group(2).strip()
        stack = [(lv, nm) for lv, nm in stack if lv < level] + [(level, name)]
        skipping = name.lower() in SKIP_SECTIONS or any(nm.lower() in SKIP_SECTIONS for _, nm in stack)
        path = " > ".join(nm for _, nm in stack)
    flush()
    return sections


def split_sentences(body):
    out = []
    for para in re.split(r"\n\s*\n", body):
        para = " ".join(para.split())
        if para:
            out += [s for s in SENTENCE_END.split(para) if s.strip()]
    return out


def pack(sentences, target, max_words):
    """Group sentences into chunks of about `target` words, repeating one sentence of overlap."""
    chunks, cur = [], []
    for s in sentences:
        if cur and words(" ".join(cur)) + words(s) > max_words:
            chunks.append(" ".join(cur))
            cur = cur[-1:] if words(cur[-1]) < target // 3 else []
        cur.append(s)
        if words(" ".join(cur)) >= target:
            chunks.append(" ".join(cur))
            cur = cur[-1:] if words(cur[-1]) < target // 3 else []
    if cur and (not chunks or words(" ".join(cur)) > words(cur[-1]) or len(cur) > 1):
        tail = " ".join(cur)
        if not chunks or tail != chunks[-1]:
            chunks.append(tail)
    return chunks


def chunk_article(article, target_words=170, max_words=260, min_words=25):
    out = []
    for section, body in split_sections(article["text"], article["title"]):
        for piece in pack(split_sentences(body), target_words, max_words):
            if words(piece) < min_words:
                continue
            out.append({
                "id": f"{article['pageid']}-{len(out)}",
                "title": article["title"], "section": section, "url": article["url"],
                "revid": article["revid"], "text": piece, "words": words(piece),
            })
    return out


def embedding_text(chunk):
    """What gets embedded: the passage prefixed with where it comes from."""
    return f"{chunk['title']} - {chunk['section']}: {chunk['text']}"
