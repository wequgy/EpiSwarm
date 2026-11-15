import sqlite3, json

conn = sqlite3.connect('logs/jobs.db')
cur = conn.cursor()
cur.execute("SELECT job_id, status, total_days, is_mock, request_json FROM jobs WHERE status='COMPLETED' ORDER BY rowid DESC LIMIT 10")
for r in cur.fetchall():
    req = json.loads(r[4])
    print(r[0], r[1], f"days: {r[2]}", f"mock: {r[3]}", f"agents: {req.get('scale_agents')}", f"region: {req.get('region_id')}")
