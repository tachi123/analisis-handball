import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5435/sapa_stats")
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
tables = cur.fetchall()
print("Tables:", tables)
cur.execute("SELECT count(*) FROM matches WHERE id = 99")
row = cur.fetchone()
print("Match 99 count:", row)
cur.execute("SELECT id, date, home_team_id, away_team_id, canonical_analysis_enabled FROM matches WHERE id = 99")
row = cur.fetchone()
print("Match 99:", row)
if row:
    cur.execute("SELECT count(*) FROM events WHERE match_id = 99")
    count = cur.fetchone()[0]
    print("Events count for match 99:", count)
    cur.execute("SELECT count(*) FROM canonical_events WHERE match_id = 99")
    count = cur.fetchone()[0]
    print("Canonical events count for match 99:", count)
    cur.execute("SELECT count(*) FROM report_package WHERE match_id = 99")
    count = cur.fetchone()[0]
    print("Report packages for match 99:", count)
conn.close()