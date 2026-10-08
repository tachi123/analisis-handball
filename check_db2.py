import psycopg2
import json

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5435/sapa_stats")
cur = conn.cursor()

# Check match 99 details
cur.execute("SELECT id, date, home_team_id, away_team_id, canonical_analysis_enabled FROM matches WHERE id = 99")
row = cur.fetchone()
print("Match 99:", row)

# Check canonical events sample
cur.execute("SELECT id, sequence, revision FROM canonical_events WHERE match_id = 99 LIMIT 5")
canon_rows = cur.fetchall()
print("Canonical events sample:", canon_rows)

# Check a canonical event revision sample
if canon_rows:
    ce_id = canon_rows[0][0]
    cur.execute("SELECT revision, payload FROM canonical_event_revisions WHERE event_id = %s LIMIT 1", (ce_id,))
    rev_row = cur.fetchone()
    print("Revision sample:", rev_row)
    if rev_row:
        print("Payload sample:", rev_row[1])

# Check events
cur.execute("SELECT id, active, payload FROM events WHERE match_id = 99 LIMIT 5")
event_rows = cur.fetchall()
print("Events sample:", event_rows)

# Check report packages
cur.execute("SELECT id, source_status, approved_at FROM report_packages WHERE match_id = 99")
pkg_rows = cur.fetchall()
print("Report packages:", pkg_rows)

cur.close()
conn.close()