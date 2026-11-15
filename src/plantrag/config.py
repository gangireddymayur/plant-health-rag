"""Settings shared by indexing, search and answering."""

EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # small, MIT-licensed, strong at retrieval
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
COLLECTION = "plant_health"


def device():
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"
