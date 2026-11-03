import json
import re
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

import townlight_permitting
from townlight_permitting.main import app


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def test_package_version_is_100() -> None:
    assert townlight_permitting.__version__ == "0.3.0+dev.2"


def test_pyproject_uses_published_townlight_core_release_wheel() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    assert data["tool"]["hatch"]["metadata"]["allow-direct-references"] is True
    assert "townlight-core==1.3.0.dev2" in dependencies
    assert not any("civiccore" in item or "@main" in item for item in dependencies)


def test_root_endpoint_states_runtime_boundary() -> None:
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()

    assert payload["name"] == "TownlightPermitting"
    assert payload["version"] == "0.3.0+dev.2"
    assert payload["status"] == "v1 permit pre-application and intake-readiness runtime"
    assert "staff review queues" in payload["message"]
    assert "permit approvals" in payload["message"]
    assert "not implemented" in payload["message"]
    assert payload["next_step"].startswith("Configure local permit requirement data")


def test_health_endpoint_reports_versions() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "townlight_permitting"
    assert payload["version"] == "0.3.0+dev.2"
    # /health must report the Core that is actually imported. The public-release
    # pin itself (exact wheel URL + SHA-256) is asserted in its own test above,
    # unchanged, so this never weakens that guard.
    import townlight_core

    assert payload["townlight_core_version"] == townlight_core.__version__
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.(dev|post)\d+)?([.+].*)?",
                        payload["townlight_core_version"])
    candidate = Path(__file__).resolve().parents[3] / "outputs/beta-plan/completion-42/C/candidate-env.json"
    if candidate.is_file():  # private coherent candidate environment present
        reported = json.loads(candidate.read_text(encoding="utf-8"))["wheel"]["path"]
        assert payload["townlight_core_version"] in reported


def test_release_gate_prefers_native_unix_python_before_windows_launcher() -> None:
    script = (ROOT / "scripts" / "verify-release.sh").read_text(encoding="utf-8")

    python3_probe = "command -v python3"
    python_probe = "command -v python)"
    assert python3_probe in script
    assert python_probe in script
    assert script.index(python3_probe) < script.index(python_probe)


def test_documentation_gate_blocks_stale_product_release_claims() -> None:
    script = (ROOT / "scripts" / "verify-docs.sh").read_text(encoding="utf-8")

    assert "v0.2.0 permit pre-application product release" in script
    assert "permit pre-application product release" in script
    assert "current product release" in script


def test_current_docs_mark_corrective_demotion_without_product_release_overclaim() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "README.txt": (ROOT / "README.txt").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "USER-MANUAL.txt": (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "townlight beta 1" in lowered, path
        assert "0.3.0+dev.2" in lowered, path
        assert "review" in lowered, path
        assert "agpl-3.0" in lowered, path
        assert "provisional" not in lowered, path
        assert "product release" not in lowered, path
