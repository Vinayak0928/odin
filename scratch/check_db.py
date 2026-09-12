import sqlite3

con = sqlite3.connect('d:/odin/odin/data/app.db')
cur = con.cursor()
print("=== Model Endpoints ===")
for row in cur.execute("SELECT * FROM model_endpoints").fetchall():
    print(row)
print("=== Settings in app.db or settings.json ===")
try:
    for row in cur.execute("SELECT * FROM settings").fetchall():
        print(row)
except Exception as e:
    print(e)
