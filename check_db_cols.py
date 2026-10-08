import psycopg2
conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5435/sapa_stats")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='match_squad'")
print("match_squad columns:", cur.fetchall())
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='matches'")
print("matches columns:", cur.fetchall())
cur.close()
conn.close()