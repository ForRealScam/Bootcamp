import json
import time
import chromadb
from openai import OpenAI

import config


def embed_query(query: str) -> list[float]:
    """Embed a user query using the configured local embedding model with search_query prefix."""
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=f"search_query: {query}",
    )
    return response.data[0].embedding


def retrieve_chunks(query: str, top_k: int = config.TOP_K) -> dict:
    """Query the local ChromaDB vector store and return top_k chunks with metadata and cosine similarity."""
    start = time.time()
    query_embedding = embed_query(query)

    chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
    collection = chroma_client.get_collection(name=config.COLLECTION_NAME)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    elapsed_ms = round((time.time() - start) * 1000)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved_chunks = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Cosine similarity = 1 - cosine_distance
        similarity = round(1.0 - float(dist), 4)
        retrieved_chunks.append(
            {
                "content": doc,
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", 0),
                "relevance_score": similarity,
            }
        )

    return {
        "query": query,
        "retrieved_chunks": retrieved_chunks,
        "retrieval_time_ms": elapsed_ms,
        "embedding_model": config.EMBEDDING_MODEL,
    }


if __name__ == "__main__":
    sample_query = "What is the maximum number of remote work days per week?"
    res = retrieve_chunks(sample_query)
    print(json.dumps(res, indent=2, ensure_ascii=False))
