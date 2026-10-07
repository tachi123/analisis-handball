"""Tests for competition layer and fixture foundation migrations.

Covers:
- Migration upgrade creates all 8 tables with FKs and indexes
- Migration downgrade drops all 8 tables in reverse dependency order
- Real Alembic upgrade/downgrade path using project test infrastructure
"""

import os
import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text


class TestMigrationUpgrade:
    """Migration upgrade creates all competition layer tables."""

    def test_upgrade_creates_fixture_foundation_tables_and_columns(self, migrated_db):
        """Migration creates fixture provenance and identity without legacy changes."""
        inspector = inspect(migrated_db)

        actual_tables = set(inspector.get_table_names())
        assert {"fixture_imports", "fixture_import_entries"} <= actual_tables
        assert {"variant_key", "suffix"} <= {column["name"] for column in inspector.get_columns("competition_teams")}
        assert {"fixture_key", "source_home_score", "source_away_score", "result_status"} <= {
            column["name"] for column in inspector.get_columns("scheduled_matches")
        }

    def test_upgrade_backfills_variant_and_fixture_identity(self, alembic_config):
        config, database_url = alembic_config
        command.upgrade(config, "20260824_0012")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO seasons (id, year) VALUES (1, 2026)"))
            connection.execute(text("INSERT INTO tournament_stages (id, season_id, name, category, division, gender) VALUES (1, 1, 'Stage', 'Senior', '4th', 'M')"))
            connection.execute(text("INSERT INTO clubs (id, name) VALUES (1, 'Club')"))
            connection.execute(text("INSERT INTO competition_teams (id, club_id, stage_id, suffix) VALUES (1, 1, 1, 'B')"))
            connection.execute(text("INSERT INTO team_registrations (id, competition_team_id, stage_id) VALUES (1, 1, 1)"))
            connection.execute(text("INSERT INTO rounds (id, stage_id, round_number) VALUES (1, 1, 1)"))
            connection.execute(text("INSERT INTO scheduled_matches (id, stage_id, round_id, home_registration_id, away_registration_id, match_number_label, status) VALUES (1, 1, 1, 1, 1, 'F1', 'scheduled')"))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT variant_key FROM competition_teams")).scalar_one() == "B"
            assert connection.execute(text("SELECT fixture_key FROM scheduled_matches")).scalar_one() == "legacy:1:1:1:1:1"
        engine.dispose()

    def test_fixture_migration_leaves_legacy_analysis_tables_unchanged(self, migrated_db):
        inspector = inspect(migrated_db)

        assert {"id", "tournament_id", "home_team_id", "away_team_id"} <= {
            column["name"] for column in inspector.get_columns("matches")
        }
        assert "fixture_key" not in {column["name"] for column in inspector.get_columns("matches")}

    def test_upgrade_creates_expected_columns(self, migrated_db):
        """Migration creates expected columns on each table."""
        inspector = inspect(migrated_db)

        # seasons
        seasons_cols = {c["name"] for c in inspector.get_columns("seasons")}
        assert {"id", "year", "description"} <= seasons_cols

        # tournament_stages
        stages_cols = {c["name"] for c in inspector.get_columns("tournament_stages")}
        assert {"id", "season_id", "name", "category", "division", "gender"} <= stages_cols

        # clubs
        clubs_cols = {c["name"] for c in inspector.get_columns("clubs")}
        assert {"id", "name", "short_name"} <= clubs_cols

        # competition_teams
        comp_teams_cols = {c["name"] for c in inspector.get_columns("competition_teams")}
        assert {"id", "club_id", "stage_id", "suffix"} <= comp_teams_cols

        # team_registrations
        regs_cols = {c["name"] for c in inspector.get_columns("team_registrations")}
        assert {"id", "competition_team_id", "stage_id", "group", "seed_order"} <= regs_cols

        # rounds
        rounds_cols = {c["name"] for c in inspector.get_columns("rounds")}
        assert {"id", "stage_id", "round_number", "date_range_start", "date_range_end"} <= rounds_cols

        # scheduled_matches
        matches_cols = {c["name"] for c in inspector.get_columns("scheduled_matches")}
        assert {
            "id",
            "stage_id",
            "round_id",
            "home_registration_id",
            "away_registration_id",
            "scheduled_date",
            "venue",
            "court",
            "match_time",
            "match_number_label",
            "status",
        } <= matches_cols

        # stage_rosters
        rosters_cols = {c["name"] for c in inspector.get_columns("stage_rosters")}
        assert {"id", "registration_id", "player_id", "jersey_number"} <= rosters_cols

    def test_upgrade_creates_unique_constraints(self, migrated_db):
        """Migration creates expected unique constraints."""
        inspector = inspect(migrated_db)

        # seasons: year unique
        seasons_uniques = inspector.get_unique_constraints("seasons")
        year_unique = any("year" in uc["column_names"] for uc in seasons_uniques)
        assert year_unique

        # tournament_stages: (season_id, name) unique
        stages_uniques = inspector.get_unique_constraints("tournament_stages")
        stage_name_unique = any(
            set(uc["column_names"]) == {"season_id", "name"} for uc in stages_uniques
        )
        assert stage_name_unique

        # clubs: name unique
        clubs_uniques = inspector.get_unique_constraints("clubs")
        club_name_unique = any("name" in uc["column_names"] for uc in clubs_uniques)
        assert club_name_unique

        # competition_teams: absent/supplied variant identity is non-null and unique
        comp_teams_uniques = inspector.get_unique_constraints("competition_teams")
        comp_team_identity_unique = any(
            set(uc["column_names"]) == {"club_id", "stage_id", "variant_key"} for uc in comp_teams_uniques
        )
        assert comp_team_identity_unique

        # team_registrations: (competition_team_id, stage_id) unique
        regs_uniques = inspector.get_unique_constraints("team_registrations")
        reg_unique = any(
            set(uc["column_names"]) == {"competition_team_id", "stage_id"} for uc in regs_uniques
        )
        assert reg_unique

        # rounds: (stage_id, round_number) unique
        rounds_uniques = inspector.get_unique_constraints("rounds")
        round_unique = any(
            set(uc["column_names"]) == {"stage_id", "round_number"} for uc in rounds_uniques
        )
        assert round_unique

        # scheduled_matches: (round_id, match_number_label) unique
        matches_uniques = inspector.get_unique_constraints("scheduled_matches")
        match_unique = any(
            set(uc["column_names"]) == {"round_id", "match_number_label"} for uc in matches_uniques
        )
        assert match_unique

        # stage_rosters: (registration_id, jersey_number) unique
        rosters_uniques = inspector.get_unique_constraints("stage_rosters")
        roster_unique = any(
            set(uc["column_names"]) == {"registration_id", "jersey_number"} for uc in rosters_uniques
        )
        assert roster_unique

    def test_upgrade_creates_foreign_keys(self, migrated_db):
        """Migration creates expected foreign keys."""
        inspector = inspect(migrated_db)

        # tournament_stages -> seasons
        stages_fks = inspector.get_foreign_keys("tournament_stages")
        season_fk = any(fk["referred_table"] == "seasons" for fk in stages_fks)
        assert season_fk

        # competition_teams -> clubs
        comp_teams_fks = inspector.get_foreign_keys("competition_teams")
        club_fk = any(fk["referred_table"] == "clubs" for fk in comp_teams_fks)
        assert club_fk

        # competition_teams -> tournament_stages
        stage_fk = any(fk["referred_table"] == "tournament_stages" for fk in comp_teams_fks)
        assert stage_fk

        # team_registrations -> competition_teams
        regs_fks = inspector.get_foreign_keys("team_registrations")
        comp_team_fk = any(fk["referred_table"] == "competition_teams" for fk in regs_fks)
        assert comp_team_fk

        # team_registrations -> tournament_stages
        stage_fk = any(fk["referred_table"] == "tournament_stages" for fk in regs_fks)
        assert stage_fk

        # rounds -> tournament_stages
        rounds_fks = inspector.get_foreign_keys("rounds")
        stage_fk = any(fk["referred_table"] == "tournament_stages" for fk in rounds_fks)
        assert stage_fk

        # scheduled_matches -> tournament_stages
        matches_fks = inspector.get_foreign_keys("scheduled_matches")
        stage_fk = any(fk["referred_table"] == "tournament_stages" for fk in matches_fks)
        assert stage_fk

        # scheduled_matches -> rounds
        round_fk = any(fk["referred_table"] == "rounds" for fk in matches_fks)
        assert round_fk

        # scheduled_matches -> team_registrations (home)
        home_reg_fk = any(
            fk["referred_table"] == "team_registrations" and fk["constrained_columns"] == ["home_registration_id"]
            for fk in matches_fks
        )
        assert home_reg_fk

        # scheduled_matches -> team_registrations (away)
        away_reg_fk = any(
            fk["referred_table"] == "team_registrations" and fk["constrained_columns"] == ["away_registration_id"]
            for fk in matches_fks
        )
        assert away_reg_fk

        # stage_rosters -> team_registrations
        rosters_fks = inspector.get_foreign_keys("stage_rosters")
        reg_fk = any(fk["referred_table"] == "team_registrations" for fk in rosters_fks)
        assert reg_fk

        # stage_rosters -> players
        player_fk = any(fk["referred_table"] == "players" for fk in rosters_fks)
        assert player_fk

    def test_upgrade_creates_indexes(self, migrated_db):
        """Migration creates expected indexes."""
        inspector = inspect(migrated_db)

        # Check key indexes exist
        comp_teams_indexes = {idx["name"] for idx in inspector.get_indexes("competition_teams")}
        assert any("club_id" in name for name in comp_teams_indexes)
        assert any("stage_id" in name for name in comp_teams_indexes)

        matches_indexes = {idx["name"] for idx in inspector.get_indexes("scheduled_matches")}
        assert any("home_registration_id" in name for name in matches_indexes)
        assert any("away_registration_id" in name for name in matches_indexes)
        assert any("match_number_label" in name for name in matches_indexes)


class TestMigrationDowngrade:
    """Migration downgrade drops all tables in reverse dependency order."""

    def test_downgrade_drops_all_tables(self, alembic_config):
        """Downgrade drops all 8 competition layer tables."""
        config, database_url = alembic_config
        command.upgrade(config, "head")

        from sqlalchemy import create_engine, inspect

        engine = create_engine(database_url)
        inspector = inspect(engine)

        expected_tables = {
            "seasons",
            "tournament_stages",
            "clubs",
            "competition_teams",
            "team_registrations",
            "rounds",
            "scheduled_matches",
            "stage_rosters",
        }
        actual_tables = set(inspector.get_table_names())
        assert expected_tables <= actual_tables

        command.downgrade(config, "base")

        inspector = inspect(engine)
        actual_tables_after = set(inspector.get_table_names())
        assert expected_tables.isdisjoint(actual_tables_after)

        engine.dispose()

    def test_downgrade_preserves_absent_variant_as_legacy_non_null_value(self, alembic_config):
        config, database_url = alembic_config
        command.upgrade(config, "20260824_0012")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO seasons (id, year) VALUES (1, 2026)"))
            connection.execute(text("INSERT INTO tournament_stages (id, season_id, name, category, division, gender) VALUES (1, 1, 'Stage', 'Senior', '4th', 'M')"))
            connection.execute(text("INSERT INTO clubs (id, name) VALUES (1, 'Club')"))
            connection.execute(text("INSERT INTO competition_teams (id, club_id, stage_id, suffix) VALUES (1, 1, 1, 'B')"))
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text("UPDATE competition_teams SET suffix = NULL, variant_key = '' WHERE id = 1"))

        command.downgrade(config, "20260824_0012")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT suffix FROM competition_teams WHERE id = 1")).scalar_one() == ""
        engine.dispose()

    def test_downgrade_order_reverse_dependency(self, alembic_config):
        """Downgrade drops tables in reverse dependency order.
        
        Order: stage_rosters, scheduled_matches, rounds,
               team_registrations, competition_teams, clubs,
               tournament_stages, seasons
        """
        config, database_url = alembic_config

        # Read the migration file to verify downgrade order
        import os

        full_path = os.path.join(
            os.path.dirname(__file__), "..", "alembic", "versions", "20260824_0012_competition_layer.py"
        )

        with open(full_path) as f:
            content = f.read()

        downgrade_section = content.split("def downgrade():")[1]

        expected_order = [
            "stage_rosters",
            "scheduled_matches",
            "rounds",
            "team_registrations",
            "competition_teams",
            "clubs",
            "tournament_stages",
            "seasons",
        ]

        for i, table in enumerate(expected_order):
            assert f'drop_table("{table}")' in downgrade_section
            if i > 0:
                prev_table = expected_order[i - 1]
                prev_pos = downgrade_section.index(f'drop_table("{prev_table}")')
                curr_pos = downgrade_section.index(f'drop_table("{table}")')
                assert curr_pos > prev_pos, f"{table} should be dropped after {prev_table}"


class TestMigrationRoundTrip:
    """Full upgrade/downgrade/upgrade round trip."""

    def test_full_round_trip(self, alembic_config):
        """Upgrade -> downgrade -> upgrade works correctly."""
        config, database_url = alembic_config

        # First upgrade
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        inspector = inspect(engine)
        tables_after_first_upgrade = set(inspector.get_table_names())
        engine.dispose()

        # Downgrade
        command.downgrade(config, "base")

        # Second upgrade
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        inspector = inspect(engine)
        tables_after_second_upgrade = set(inspector.get_table_names())
        engine.dispose()

        expected_tables = {
            "seasons",
            "tournament_stages",
            "clubs",
            "competition_teams",
            "team_registrations",
            "rounds",
            "scheduled_matches",
            "stage_rosters",
        }
        assert expected_tables <= tables_after_first_upgrade
        assert expected_tables <= tables_after_second_upgrade
        assert tables_after_first_upgrade == tables_after_second_upgrade
