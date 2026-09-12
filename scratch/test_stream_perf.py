import os
import sys
import time
import asyncio
from pathlib import Path

# Ensure root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.chroma_client import get_chroma_client
from src.personal_docs import PersonalDocsManager
from src.rag_manager import RAGManager
from src.llm_core import stream_llm

async def main():
    print("=== TESTING CHROMA RAG + OLLAMA STREAMING SPEED ===")
    print("1. Checking ChromaDB availability...")
    t0 = time.time()
    try:
        client = get_chroma_client()
        print(f"ChromaDB connected in {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"ChromaDB error: {e}")
        return

    rag = RAGManager()
    stats = rag.get_stats()
    print(f"Collection stats: {stats}")

    query = "What is the design temperature and pressure for DHT Stripper Column in MRPL Phase III?"
    print(f"\n2. Searching RAG for query: {query}")
    t_search = time.time()
    results = rag.search(query, k=4)
    search_duration = time.time() - t_search
    print(f"RAG search took: {search_duration:.2f}s. Results found: {len(results)}")

    relevant = [r for r in results if r.get("similarity", 0) >= 0.15]
    relevant.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    relevant = relevant[:3]

    doc_texts = []
    for r in relevant:
        doc = r["document"].strip()
        if len(doc) > 800:
            doc = doc[:800] + "\n..."
        doc_texts.append(f"[{r.get('metadata', {}).get('filename', 'doc')}]\n{doc}")

    rag_context = "\n\n---\n\n".join(doc_texts)
    if len(rag_context) > 3000:
        rag_context = rag_context[:3000]

    messages = [
        {"role": "system", "content": "You are Odysseus, an industrial engineering AI for MRPL Mangalore Refinery. Answer accurately based on provided technical documentation."},
        {"role": "user", "content": f"Context:\n{rag_context}\n\nQuestion: {query}"}
    ]

    print(f"\n3. Streaming response using qwen2.5-coder:1.5b...")
    t_gen_start = time.time()
    first_token_time = None
    chunks = []

    async for chunk in stream_llm(
        url="http://localhost:11434",
        model="qwen2.5-coder:1.5b",
        messages=messages,
        temperature=0.2,
        max_tokens=256
    ):
        if first_token_time is None:
            first_token_time = time.time() - t_gen_start
            print(f"Time to first token: {first_token_time:.2f}s")
        chunks.append(chunk)

    total_gen_time = time.time() - t_gen_start
    full_response = "".join(chunks)

    print(f"Total generation time: {total_gen_time:.2f}s")
    print(f"Chunks received: {len(chunks)}")
    print(f"Tokens/sec approx: {len(chunks)/total_gen_time:.1f} tokens/s")
    print("\n--- RESPONSE ---")
    print(full_response.strip())
    print("----------------")

if __name__ == "__main__":
    asyncio.run(main())
