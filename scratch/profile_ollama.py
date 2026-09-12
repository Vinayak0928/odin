import sys
import time
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.rag_manager import RAGManager
from src.llm_core import _build_ollama_payload

query = "What is the design temperature and pressure for DHT Stripper Column in MRPL Phase III?"
rag = RAGManager()
results = rag.search(query, k=3)
doc_texts = [f"[{r.get('metadata', {}).get('filename', 'doc')}]\n{r['document'][:800]}" for r in results]
rag_context = "\n\n---\n\n".join(doc_texts)[:3000]

messages = [
    {"role": "system", "content": "You are Odysseus, an industrial engineering AI for MRPL Mangalore Refinery. Answer accurately based on provided technical documentation."},
    {"role": "user", "content": f"Context:\n{rag_context}\n\nQuestion: {query}"}
]

for ctx_val in [131072, 8192, 4096]:
    print(f"\n--- Testing with num_ctx = {ctx_val} ---")
    payload = _build_ollama_payload("qwen2.5-coder:1.5b", messages, 0.2, 100, stream=False, num_ctx=ctx_val)
    t0 = time.time()
    res = requests.post("http://localhost:11434/api/chat", json=payload, timeout=120).json()
    total_sec = time.time() - t0

    print(f"Total elapsed: {total_sec:.2f}s")
    print(f"load_duration: {res.get('load_duration', 0) / 1e6:.1f}ms")
    print(f"prompt_eval_count: {res.get('prompt_eval_count')}")
    print(f"prompt_eval_duration: {res.get('prompt_eval_duration', 0) / 1e6:.1f}ms")
    print(f"eval_count: {res.get('eval_count')}")
    print(f"eval_duration: {res.get('eval_duration', 0) / 1e6:.1f}ms")
    print("Response excerpt:", res.get("message", {}).get("content", "")[:150])
