import json

with open('d:/odin/odin/data/agent_workspace/mrpl_refinery_300page_corpus.json', encoding='utf-8') as f:
    data = json.load(f)

for section, records in data.items():
    print(f"=== Section: {section} ===")
    if isinstance(records, list) and records:
        print("Keys in sample record:", list(records[0].keys()))
        print("Sample:", json.dumps(records[0], indent=2)[:300])
    elif isinstance(records, dict):
        print("Dict keys:", list(records.keys()))
