import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from src.rag_singleton import get_rag_manager

rm = get_rag_manager()
lane = rm._lanes[0]
res = lane.collection.get(ids=['doc_454f03990c15023c'])
print("Document text:\n", res["documents"][0])
