import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.rag_singleton import get_rag_manager

rm = get_rag_manager()
lane = rm._lanes[0]
res = lane.collection.get(where={"record_id": "mrpl_maintenance_work_orders_WO-4000101"})
print("Direct record_id lookup:", len(res["ids"]))
if not res["ids"]:
    # Check any maintenance work orders
    res2 = lane.collection.get(where={"section": "maintenance_work_orders"}, limit=5)
    print("Sample maintenance work orders:", res2["ids"])
    print("Metadatas:", res2["metadatas"])
