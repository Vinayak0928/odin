import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.rag_singleton import get_rag_manager

rm = get_rag_manager()
lane = rm._lanes[0]
query = "What is the priority and description for work order WO-4000101?"
res = lane.collection.query(query_texts=[query], n_results=80)
ids = res["ids"][0]
print("Is doc_454f03990c15023c in top 80 vector results?", "doc_454f03990c15023c" in ids)
if "doc_454f03990c15023c" in ids:
    idx = ids.index("doc_454f03990c15023c")
    print("Rank in 80:", idx, "Distance:", res["distances"][0][idx])
