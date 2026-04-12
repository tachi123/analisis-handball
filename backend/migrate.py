"""One-time migration: add new Event columns."""
from sqlalchemy import create_engine, text
import os

url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5435/sapa_stats")
engine = create_engine(url)

NEW_COLS = {
    "period": "INTEGER",
    "attack_phase": "VARCHAR",
    "assist_player_id": "INTEGER REFERENCES players(id)",
    "goalkeeper_id": "INTEGER REFERENCES players(id)",
    "sub_in_player_id": "INTEGER REFERENCES players(id)",
    "sub_out_player_id": "INTEGER REFERENCES players(id)",
}

with engine.connect() as conn:
    existing = [
        r[0]
        for r in conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='events'")
        ).fetchall()
    ]
    print("Existing columns:", existing)
    for col, typ in NEW_COLS.items():
        if col not in existing:
            conn.execute(text(f"ALTER TABLE events ADD COLUMN {col} {typ}"))
            print(f"  Added: {col}")
        else:
            print(f"  Already exists: {col}")
    conn.commit()
    print("Migration complete!")
