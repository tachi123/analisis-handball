import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
SCRIPT = BACKEND_DIR / "scripts" / "group_planilla_players.py"
SERVICE = BACKEND_DIR / "app" / "services" / "planilla_player_identity_service.py"
REAL_MANIFEST = ROOT_DIR / "resources" / "planillas" / "_discovery" / "manifest.json"
ARTIFACTS = {"identities.json", "identities.csv", "conflicts.md", "identity-summary.json"}


def sample_manifest():
    def record(sha, name):
        return {
            "sha256": sha * 64,
            "source_path": f"stage/{sha}.pdf",
            "fields": {"tournament": {"value": "Metro"}, "home_name": {"value": "Club"}},
            "rosters": {"local": [{"name": name, "number": 7, "source": {"page": 1}}]},
        }

    return {"schema_version": 1, "records": [record("a", "Ana García"), record("b", "Garcia, Ana")]}


def run_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def test_cli_writes_only_identity_artifacts_and_returns_validation_codes(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(sample_manifest()), encoding="utf-8")
    output = tmp_path / "output"

    result = run_cli(manifest, output)

    assert result.returncode == 0, result.stderr
    assert {path.name for path in output.iterdir()} == ARTIFACTS
    assert "identity_count=1" in result.stdout
    missing = run_cli(tmp_path / "missing.json", output)
    assert missing.returncode == 2
    assert "manifest file does not exist" in missing.stderr
    invalid_overrides = tmp_path / "overrides.json"
    invalid_overrides.write_text("[]", encoding="utf-8")
    invalid = run_cli(manifest, tmp_path / "invalid", "--overrides", invalid_overrides)
    assert invalid.returncode == 1
    assert "overrides must contain a JSON object" in invalid.stderr


def test_identity_service_and_cli_import_paths_have_no_database_model_or_sqlalchemy_dependency():
    for source in (SERVICE, SCRIPT):
        imports = [node.module or "" for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))) if isinstance(node, ast.ImportFrom)]
        assert not any(module.startswith(("app.database", "app.models", "sqlalchemy")) for module in imports)

    code = f"""
import importlib.util
import sys
spec = importlib.util.spec_from_file_location("group_planilla_players_import_guard", {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
blocked = [name for name in sys.modules if name == "app.database" or name.startswith("app.models") or name.startswith("sqlalchemy")]
raise SystemExit(f"unexpected imports: {{blocked}}" if blocked else 0)
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.corpus
def test_cli_groups_real_manifest_read_only_byte_stably_with_sane_tiers(tmp_path):
    manifest_bytes = REAL_MANIFEST.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    outputs = []
    for name in ("first", "second"):
        output = tmp_path / name
        result = run_cli(REAL_MANIFEST, output)
        assert result.returncode == 0, result.stderr
        assert {path.name for path in output.iterdir()} == ARTIFACTS
        outputs.append(output)

    assert REAL_MANIFEST.read_bytes() == manifest_bytes
    assert hashlib.sha256(REAL_MANIFEST.read_bytes()).hexdigest() == manifest_hash
    for artifact in ARTIFACTS:
        assert (outputs[0] / artifact).read_bytes() == (outputs[1] / artifact).read_bytes()

    summary = json.loads((outputs[0] / "identity-summary.json").read_text(encoding="utf-8"))
    tiers = summary["link_tier_counts"]
    assert summary["input"]["row_count"] > 1_000
    assert sum(tiers.values()) == summary["link_count"]
    assert tiers.get("auto_group", 0) > 0
    assert tiers.get("review", 0) > 0
    assert tiers.get("conflict", 0) > 0
    assert set(tiers) <= {"auto_group", "review", "conflict"}
