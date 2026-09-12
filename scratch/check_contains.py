import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from src.rag_singleton import get_rag_manager

rm = get_rag_manager()
lane = rm._lanes[0]
res = lane.collection.get(where_document={"$contains": "WO-4000101"})
print("Contains WO-4000101 count:", len(res["ids"]), res["ids"])

res2 = lane.collection.get(where_document={"$contains": "CML-MRPL-UT-0101"})
print("Contains CML-MRPL-UT-0101 count:", len(res2["ids"]), res2["ids"])

res3 = lane.collection.get(where_document={"$contains": "HAZOP-MRPL-NODE-01"})
print("Contains HAZOP-MRPL-NODE-01 count:", len(res3["ids"]), res3["ids"])
