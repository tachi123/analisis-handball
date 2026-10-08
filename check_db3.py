import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5435/sapa_stats")
cur = conn.cursor()
cur.execute("SELECT id, sequence FROM canonical_events WHERE match_id = 99 LIMIT 3")
print("Canonical events sample:", cur.fetchall())
cur.execute("SELECT id, event_id, revision, payload FROM canonical_event_revisions LIMIT 3")
print("Revision sample:", cur.fetchall())
cur.close()
conn.close()