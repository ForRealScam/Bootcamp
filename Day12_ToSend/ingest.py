import re
import time
from pathlib import Path
import chromadb
import chromadb.errors
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pypdf import PdfReader

import config


def clean_layout_text(text: str) -> str:
    """Collapse excessive horizontal padding from pypdf layout mode while preserving table rows."""
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"[ \t]{2,}", "  ", line.strip())
        lines.append(cleaned)
    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def load_and_chunk_pdfs(documents_dir: str = config.DOCUMENTS_DIR) -> list[dict]:
    """Load all PDFs from documents_dir using layout mode and split into character chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    pdf_files = sorted(Path(documents_dir).glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in '{documents_dir}'")

    for pdf_path in pdf_files:
        reader = PdfReader(str(pdf_path))
        for page_num, page in enumerate(reader.pages, start=1):
            raw_text = page.extract_text(extraction_mode="layout") or ""
            page_text = clean_layout_text(raw_text)
            if not page_text:
                continue

            page_chunks = splitter.split_text(page_text)
            for chunk_idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{pdf_path.name}_p{page_num}_c{chunk_idx}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "content": chunk_text,
                        "source": pdf_path.name,
                        "page": page_num,
                    }
                )

    return chunks


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Embed a list of texts using the configured local embedding model."""
    client = OpenAI(base_url=config.EMBEDDING_BASE_URL, api_key=config.EMBEDDING_API_KEY)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model=config.EMBEDDING_MODEL,
            input=batch,
        )
        all_embeddings.extend(item.embedding for item in response.data)

    return all_embeddings


def ingest_documents() -> int:
    """Ingest all PDFs into ChromaDB with cosine distance and nomic-embed-text prefixes."""
    start_time = time.time()
    print(f"Loading PDFs from '{config.DOCUMENTS_DIR}' (chunk_size={config.CHUNK_SIZE} chars, overlap={config.CHUNK_OVERLAP} chars)...")
    chunks = load_and_chunk_pdfs(config.DOCUMENTS_DIR)
    print(f"Created {len(chunks)} chunks across PDFs.")

    # nomic-embed-text expects 'search_document: ' prefix for indexed passages
    prefixed_texts = [f"search_document: {c['content']}" for c in chunks]
    print(f"Generating embeddings with '{config.EMBEDDING_MODEL}'...")
    embeddings = embed_texts(prefixed_texts)
    dim = len(embeddings[0]) if embeddings else 0
    print(f"Generated {len(embeddings)} embeddings (dimension={dim}).")

    chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_DIR)
    try:
        chroma_client.delete_collection(name=config.COLLECTION_NAME)
        print(f"Deleted existing collection '{config.COLLECTION_NAME}' to prevent duplicates.")
    except chromadb.errors.NotFoundError:
        pass

    collection = chroma_client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c["source"], "page": c["page"]} for c in chunks],
    )

    elapsed = time.time() - start_time
    count = collection.count()
    print(f"Ingestion complete in {elapsed:.2f}s. Total chunks stored in '{config.COLLECTION_NAME}': {count}")
    return count


if __name__ == "__main__":
    ingest_documents()
