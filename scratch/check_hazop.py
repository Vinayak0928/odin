import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.rag_singleton import get_rag_manager
from src.embedding_lanes import query_lanes

rm = get_rag_manager()
q = "Tell me about HAZOP reverse flow in Node 1"
for lane, res in query_lanes(rm._lanes, q, n_results=lambda l: 100, include=["documents", "metadatas", "distances"]):
    secs = [m.get("section") for m in res["metadatas"][0]]
    print("Sections in top 100:", set(secs))
    hazop_count = sum(1 for s in secs if s == "hazop_risk_assessment_worksheets")
    print("HAZOP records in top 100:", hazop_count)
