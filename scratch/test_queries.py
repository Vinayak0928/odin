import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.rag_singleton import get_rag_manager

rm = get_rag_manager()
queries = [
    "What units are in MRPL refinery?",
    "What is the metallurgy and piping spec for equipment 011-C-101 in CDU Phase III?",
    "Explain SOP for CDU Crude Desalter Transformer Grid Failure MRPL-SOP-011-001",
    "What is the remaining life for CML-MRPL-UT-0101 in 011-V-1101?",
    "Tell me about HAZOP reverse flow in Node 1",
    "What is the priority and description for work order WO-4000101?",
]

for q in queries:
    print(f"\n=======================================================")
    print(f"QUERY: {q}")
    results = rm.search(q, k=2)
    print(f"RESULTS ({len(results)}):")
    for r in results:
        print(f"Similarity: {r.get('similarity'):.4f} | Section: {r.get('metadata', {}).get('section_label')} | Record: {r.get('metadata', {}).get('record_id')}")
        print("Snippet:\n", r.get('document')[:250])
        print("---")
