from alembic import command
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


APPLICATION_TABLES = {
    "users",
    "tournaments",
    "teams",
    "players",
    "matches",
    "match_squad",
    "events",
    "clips",
    "official_snapshots",
    "official_snapshot_players",
    "analysis_codebook_entries",
    "analysis_events",
    "analysis_event_revisions",
    "video_sources",
    "analysis_sessions",
    "time_anchors",
    "time_segments",
}


def test_baseline_upgrade_and_downgrade(alembic_config):
    config, database_url = alembic_config
    expected_head = ScriptDirectory.from_config(config).get_current_head()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert APPLICATION_TABLES <= set(inspector.get_table_names())
        assert {"period", "video_start_seconds", "video_end_seconds", "regulation_start_seconds", "regulation_end_seconds", "uncertainty_seconds", "coverage", "clock_unverified"} <= {column["name"] for column in inspector.get_columns("time_segments")}
        assert inspector.get_columns("alembic_version")[0]["name"] == "version_num"
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one() == expected_head

        command.downgrade(config, "base")

        assert not APPLICATION_TABLES & set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT COUNT(*) FROM alembic_version"
            ).scalar_one() == 0
    finally:
        engine.dispose()


def test_historical_external_code_revision_is_a_schema_noop(alembic_config):
    config, database_url = alembic_config
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    command.upgrade(config, "600464b8cb43")
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        columns_before = {
            column["name"] for column in inspector.get_columns("competition_teams")
        }
        indexes_before = {
            index["name"] for index in inspector.get_indexes("competition_teams")
        }

        command.upgrade(config, "head")

        inspector = inspect(engine)
        assert {
            column["name"] for column in inspector.get_columns("competition_teams")
        } == columns_before
        assert {
            index["name"] for index in inspector.get_indexes("competition_teams")
        } == indexes_before
        assert "external_code" in columns_before
        assert "ix_competition_teams_external_code" in indexes_before
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one() == expected_head

        command.downgrade(config, "600464b8cb43")
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one() == "600464b8cb43"
    finally:
        engine.dispose()


def test_publication_control_migration_keeps_local_versions_and_recovery_attestation(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20260822_0008")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("""
                INSERT INTO report_packages (
                    id, match_id, analyst_id, report_version, schema_version,
                    coaching_question, pattern_statement, action_kind, action_text,
                    uncertainty_disclosure, metrics, reconciliation, created_at
                ) VALUES
                    (10, 1, 1, 1, 'public-report-v1', 'First?', 'First.', 'keep', 'Keep it.', 'None.', '{}', '[]', '2026-08-20 10:00:00'),
                    (11, 1, 1, 1, 'public-report-v1', 'Second?', 'Second.', 'change', 'Change it.', 'None.', '{}', '[]', '2026-08-20 10:00:00')
            """)
            connection.exec_driver_sql("""
                INSERT INTO report_publications (package_id, report_version, schema_version, status)
                VALUES (11, 1, 'public-report-v1', 'published')
            """)
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT report_version FROM report_packages ORDER BY id"
            ).scalars().all() == [1, 1]
            assert "report_publication_state" not in inspect(engine).get_table_names()
            assert "replaces_package_id" not in {
                column["name"] for column in inspect(engine).get_columns("report_packages")
            }
            columns = {column["name"] for column in inspect(engine).get_columns("recovery_artifacts")}
            assert {"attested_at", "attested_by_user_id"} <= columns
            assert "verified_at" not in columns

        command.downgrade(config, "20260823_0009")
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT report_version FROM report_packages ORDER BY id"
            ).scalars().all() == [1, 2]
            assert connection.exec_driver_sql(
                "SELECT current_package_id, current_report_version, next_report_version FROM report_publication_state"
            ).one() == (11, 2, 3)
    finally:
        engine.dispose()


def test_canonical_evidence_links_migration_is_typed_and_reversible(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20260825_0016")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO canonical_events (id, match_id, sequence, created_at)"
                " VALUES (1, 1, 1, '2026-08-25 10:00:00')"
            ))
            connection.execute(text(
                "INSERT INTO canonical_event_revisions (id, event_id, revision, actor_id, payload, reason, created_at)"
                " VALUES (1, 1, 1, 1, '{}', 'created', '2026-08-25 10:00:00')"
            ))

        command.upgrade(config, "head")
        inspector = inspect(engine)
        columns = {column["name"] for column in inspector.get_columns("canonical_evidence")}
        assert {"scheduled_match_id", "official_snapshot_id", "video_source_id",
                "video_anchor_seconds", "report_package_id"} <= columns
        referred_tables = {
            (foreign_key["constrained_columns"][0], foreign_key["referred_table"])
            for foreign_key in inspector.get_foreign_keys("canonical_evidence")
        }
        assert {("scheduled_match_id", "scheduled_matches"), ("official_snapshot_id", "official_snapshots"),
                ("video_source_id", "video_sources"), ("report_package_id", "report_packages")} <= referred_tables
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO canonical_evidence (revision_id, kind, reference, video_source_id, video_anchor_seconds, uncertainty, created_at)"
                " VALUES (1, 'video', 'clip.mp4', NULL, 12.5, '[]', '2026-08-25 10:00:00')"
            ))

        command.downgrade(config, "20260825_0016")
        columns = {column["name"] for column in inspect(engine).get_columns("canonical_evidence")}
        assert not {"scheduled_match_id", "official_snapshot_id", "video_source_id",
                    "video_anchor_seconds", "report_package_id"} & columns
    finally:
        engine.dispose()


def test_video_source_identity_migration_reconciles_references_and_enforces_uniqueness(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20260829_0019")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id, email, hashed_password, full_name, role) VALUES (1, 'analyst@example.com', 'x', 'Analyst', 'analyst')"))
            connection.execute(text("INSERT INTO matches (id) VALUES (1)"))
            connection.execute(text("""
                INSERT INTO video_sources (id, match_id, original_url, provider, provider_video_id, availability_state, created_at)
                VALUES
                    (7, 1, 'https://youtu.be/abcdefghijk', 'youtube', 'abcdefghijk', 'ready', '2026-10-03 10:00:00'),
                    (10, 1, 'https://www.youtube.com/watch?v=abcdefghijk', 'youtube', 'abcdefghijk', 'unavailable', '2026-10-03 10:01:00'),
                    (11, 1, 'https://youtube-nocookie.com/embed/abcdefghijk', 'youtube', 'abcdefghijk', 'unavailable', '2026-10-03 10:02:00')
            """))
            connection.execute(text("""
                INSERT INTO analysis_sessions (id, match_id, analyst_id, video_source_id, mode, profile, video_position_seconds, clock_start_video_seconds, filters, draft, queue, updated_at)
                VALUES (2, 1, 1, 11, 'video', 'complete', 50, 17, '{}', '{}', '[]', '2026-10-03 10:03:00')
            """))
            connection.execute(text("INSERT INTO canonical_events (id, match_id, sequence, created_at) VALUES (3, 1, 1, '2026-10-03 10:04:00')"))
            connection.exec_driver_sql("""
                INSERT INTO canonical_event_revisions (id, event_id, revision, actor_id, payload, reason, created_at)
                VALUES
                    (4, 3, 1, 1, '{"kind":"other","outcome":"kickoff","regulation_seconds":0,"clock_unverified":false}', 'created', '2026-10-03 10:04:00'),
                    (5, 3, 2, 1, '{"kind":"shot","outcome":"goal","regulation_seconds":40,"clock_unverified":false}', 'saved', '2026-10-03 10:05:00')
            """)
            connection.execute(text("""
                INSERT INTO canonical_evidence (id, revision_id, kind, reference, video_source_id, video_anchor_seconds, uncertainty, created_at)
                VALUES
                    (3, 4, 'video', 'https://youtu.be/abcdefghijk', 10, 17, '[]', '2026-10-03 10:04:00'),
                    (4, 5, 'video', 'https://youtu.be/abcdefghijk', 11, 57, '["camera_angle"]', '2026-10-03 10:05:00')
            """))

        command.upgrade(config, "head")

        with engine.connect() as connection:
            assert connection.execute(text("SELECT id FROM video_sources ORDER BY id")).scalars().all() == [7]
            assert connection.execute(text("SELECT video_source_id FROM analysis_sessions WHERE id = 2")).scalar_one() == 7
            assert connection.execute(text("SELECT video_source_id FROM canonical_evidence ORDER BY id")).scalars().all() == [7, 7]
            assert connection.execute(text("SELECT video_anchor_seconds FROM canonical_evidence ORDER BY id")).scalars().all() == [17.0, 57.0]
            assert connection.execute(text("SELECT payload FROM canonical_event_revisions ORDER BY id")).scalars().all() == [
                '{"kind":"other","outcome":"kickoff","regulation_seconds":0,"clock_unverified":false}',
                '{"kind":"shot","outcome":"goal","regulation_seconds":40,"clock_unverified":false}',
            ]
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text("""
                    INSERT INTO video_sources (match_id, original_url, provider, provider_video_id, availability_state, created_at)
                    VALUES (1, 'https://youtu.be/abcdefghijk', 'youtube', 'abcdefghijk', 'ready', '2026-10-03 10:06:00')
                """))
    finally:
        engine.dispose()


def test_match_audit_timestamp_migration_backfills_only_missing_values(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20261004_0021")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO matches (id, created_at, updated_at) VALUES
                (1, '2026-10-01 10:00:00', '2026-10-02 11:00:00'),
                (2, NULL, '2026-10-03 12:00:00')
            """))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT created_at, updated_at FROM matches WHERE id = 1")).one() == (
                '2026-10-01 10:00:00', '2026-10-02 11:00:00')
            assert connection.execute(text("SELECT created_at, updated_at FROM matches WHERE id = 2")).one() == (
                '2026-10-03 12:00:00', '2026-10-03 12:00:00')
            columns = {column["name"]: column for column in inspect(engine).get_columns("matches")}
            assert not columns["created_at"]["nullable"]
            assert not columns["updated_at"]["nullable"]
    finally:
        engine.dispose()


def test_match_fixture_link_migration_is_unique_and_reversible(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20260824_0013")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO seasons (id, year) VALUES (1, 2026)"))
            connection.execute(text("INSERT INTO tournament_stages (id, season_id, name, category, division, gender) VALUES (1, 1, 'Stage', 'Senior', '4th', 'M')"))
            connection.execute(text("INSERT INTO clubs (id, name) VALUES (1, 'Club')"))
            connection.execute(text("INSERT INTO competition_teams (id, club_id, stage_id, suffix, variant_key) VALUES (1, 1, 1, 'B', 'B')"))
            connection.execute(text("INSERT INTO team_registrations (id, competition_team_id, stage_id) VALUES (1, 1, 1)"))
            connection.execute(text("INSERT INTO rounds (id, stage_id, round_number) VALUES (1, 1, 1)"))
            connection.execute(text("INSERT INTO scheduled_matches (id, stage_id, round_id, home_registration_id, away_registration_id, match_number_label, status, fixture_key, result_status) VALUES (1, 1, 1, 1, 1, 'F1', 'scheduled', 'fixture:1', 'unreported')"))
            connection.execute(text("INSERT INTO matches (id) VALUES (1), (2)"))

        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "scheduled_match_id" in {column["name"] for column in inspector.get_columns("matches")}
        assert any(
            foreign_key["referred_table"] == "scheduled_matches"
            and foreign_key["constrained_columns"] == ["scheduled_match_id"]
            for foreign_key in inspector.get_foreign_keys("matches")
        )

        with engine.begin() as connection:
            connection.execute(text("UPDATE matches SET scheduled_match_id = 1 WHERE id = 1"))
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text("UPDATE matches SET scheduled_match_id = 1 WHERE id = 2"))

        command.downgrade(config, "20260824_0013")
        assert "scheduled_match_id" not in {
            column["name"] for column in inspect(engine).get_columns("matches")
        }
    finally:
        engine.dispose()


def test_official_batch_provenance_migration_is_reversible(alembic_config):
    config, database_url = alembic_config
    command.upgrade(config, "20260825_0017")
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "head")
        assert "official_batch_runs" in inspect(engine).get_table_names()
        columns = {column["name"] for column in inspect(engine).get_columns("official_snapshots")}
        assert {"batch_run_id", "is_confirmed"} <= columns

        command.downgrade(config, "20260825_0017")
        assert "official_batch_runs" not in inspect(engine).get_table_names()
        columns = {column["name"] for column in inspect(engine).get_columns("official_snapshots")}
        assert not {"batch_run_id", "is_confirmed"} & columns
    finally:
        engine.dispose()
