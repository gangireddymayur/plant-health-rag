import unittest

from plantrag.chunk import chunk_article, embedding_text, split_sections, split_sentences, words

TEXT = """Late blight is a disease of potato. It spreads fast in wet weather. Spores travel on the wind.

== Symptoms ==
Leaves show dark patches. A white mould appears underneath in damp conditions. Tubers rot in storage.

=== On leaves ===
Spots have a pale green edge. They grow quickly and merge into large brown areas on the leaf blade.

== Management ==
Use certified seed. Destroy cull piles. Apply protective treatment before the disease arrives.

== References ==
Smith J. 2001. A book about blight. Journal of Plants 4: 1-9. Doe A. 2005. More about plants.

== External links ==
Some link text that should never become a passage at all in any chunk.
"""


def article(text=TEXT):
    return {"pageid": 7, "title": "Late blight", "url": "https://example.org/Late_blight", "revid": 99, "text": text}


class SectionTests(unittest.TestCase):
    def test_sections_follow_headings_and_nest(self):
        secs = dict(split_sections(TEXT, "Late blight"))
        self.assertIn("Introduction", secs)
        self.assertIn("Symptoms", secs)
        self.assertIn("Symptoms > On leaves", secs)
        self.assertIn("Management", secs)

    def test_reference_sections_are_dropped(self):
        joined = " ".join(body for _, body in split_sections(TEXT, "Late blight"))
        self.assertNotIn("Journal of Plants", joined)
        self.assertNotIn("never become a passage", joined)

    def test_sentence_split(self):
        self.assertEqual(len(split_sentences("One thing. Another thing! A third?")), 3)


class ChunkTests(unittest.TestCase):
    def test_chunks_carry_source_information(self):
        chunks = chunk_article(article(), min_words=3)
        self.assertTrue(chunks)
        for c in chunks:
            self.assertEqual(c["title"], "Late blight")
            self.assertEqual(c["url"], "https://example.org/Late_blight")
            self.assertEqual(c["revid"], 99)

    def test_ids_are_unique(self):
        ids = [c["id"] for c in chunk_article(article(), min_words=3)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_long_section_is_split_within_limits(self):
        sentence = "This sentence has exactly ten words in it for counting. "
        long_text = "== Details ==\n" + sentence * 80
        chunks = chunk_article(article(long_text), target_words=60, max_words=90, min_words=10)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(c["words"] <= 90 for c in chunks))

    def test_neighbouring_chunks_overlap_by_a_sentence(self):
        sents = [f"Sentence number {i} says something about the plant disease here." for i in range(30)]
        chunks = chunk_article(article("== Details ==\n" + " ".join(sents)), target_words=40, max_words=70, min_words=5)
        self.assertGreater(len(chunks), 2)
        last_of_first = chunks[0]["text"].split(". ")[-1].strip()
        self.assertIn(last_of_first.rstrip("."), chunks[1]["text"])

    def test_tiny_passages_are_skipped(self):
        self.assertEqual(chunk_article(article("== Short ==\nToo short."), min_words=25), [])

    def test_embedding_text_includes_title_and_section(self):
        c = chunk_article(article(), min_words=3)[0]
        self.assertTrue(embedding_text(c).startswith("Late blight - "))
        self.assertGreater(words(embedding_text(c)), c["words"])


if __name__ == "__main__":
    unittest.main()
