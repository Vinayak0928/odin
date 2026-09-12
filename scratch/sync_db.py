import sqlite3
import json

db_path = 'd:/odin/odin/data/app.db'
con = sqlite3.connect(db_path)
cur = con.cursor()

installed_models = ["qwen2.5-coder:3b", "llama3.2:1b", "deepseek-r1:1.5b", "qwen2.5-coder:1.5b"]

# 1. Update model_endpoints
cur.execute("""
    UPDATE model_endpoints
    SET cached_models = ?
    WHERE id = 'ollama-local' OR base_url LIKE '%11434%'
""", (json.dumps(installed_models),))

# 2. Update sessions
updated_sessions = 0
for row in cur.execute("SELECT id, model, endpoint_url FROM sessions").fetchall():
    sid, model, ep = row
    if not model or model not in installed_models:
        cur.execute("""
            UPDATE sessions
            SET model = 'qwen2.5-coder:3b',
                endpoint_url = 'http://localhost:11434/v1'
            WHERE id = ?
        """, (sid,))
        updated_sessions += 1

con.commit()
con.close()
print(f"Updated model_endpoints and {updated_sessions} sessions in app.db.")
