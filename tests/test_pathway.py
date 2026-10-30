"""Source grounding regressions: synthetic imported requirements and real persistence."""

import asyncio
import base64
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from civicpermit import main
from civicpermit.pathway import explain_pathway, explain_pathway_with_assistant
from civicpermit.sources import load_providers, ENV_VAR
from civicpermit.workflow_models import RequirementBundle
from civicpermit.workflow_store import IntakeRepository
from civicpermit.migrations import source_engine, upgrade

FIXTURE = Path(__file__).parent / "fixtures/public-sources.json"


@pytest.fixture
def requirement():
    return json.loads(FIXTURE.read_text())["requirements"][0]


def test_imported_guidance_changes_with_source_revision(requirement):
    result = explain_pathway(project_type="adu", requirement=requirement)
    assert result.likely_permits[0]["typical_time"] == "7 business days"
    assert result.attachments[0]["material"] == "A dimensioned site plan."
    assert result.attachments[0]["source_sha256"] == requirement["sha256"]
    changed = json.loads(
        json.dumps(requirement)
        .replace("Synthetic A", "Synthetic B")
        .replace("7 business days", "11 business days")
        .replace("A dimensioned site plan.", "An elevation drawing.")
    )
    raw = b"Synthetic B\nPlanning intake followed by building review.\n11 business days\nAn elevation drawing."
    changed.update(
        content_base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest()
    )
    second = explain_pathway(project_type="adu", requirement=changed)
    assert second.likely_permits[0]["typical_time"] == "11 business days"
    assert second.attachments[0]["material"] == "An elevation drawing."
    assert second.citations == ["Synthetic B Intake 4"]
    assert second.review_required and not second.determination_made


def test_unrelated_valid_source_never_authorizes_sample_guidance():
    text = "The library opens at nine. No permit requirements are specified."
    def provider(**kw):
        return [
            dict(
                source_id=kw.get("source_id", "library"),
                text=text,
                visibility="public",
                sha256=hashlib.sha256(text.encode()).hexdigest(),
                citation="Library Hours 1",
                version="1",
                title="Library",
            )
        ]
    result = explain_pathway(project_type="adu", source_providers={"code": provider})
    assert not result.likely_permits and not result.timeline and not result.attachments
    assert result.unavailable and not result.citations


def test_imported_extract_must_occur_in_retained_original(requirement):
    raw = b"The library opens at nine."
    requirement.update(
        content_base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest()
    )
    result = explain_pathway(project_type="adu", requirement=requirement)
    assert not result.likely_permits and not result.attachments
    assert result.unavailable


def test_missing_timing_is_not_fabricated(requirement):
    requirement["pathway"][0]["typical_time"] = ""
    result = explain_pathway(project_type="adu", requirement=requirement)
    assert result.likely_permits and not result.timeline
    assert result.likely_permits[0]["typical_time"] == "Unavailable in the cited source"


def test_current_imported_requirement_not_superseded_head(tmp_path, requirement):
    engine = source_engine(f"sqlite:///{tmp_path / 'intake.db'}")
    upgrade(engine)
    repo = IntakeRepository(engine, {})
    first = repo.import_requirements(
        RequirementBundle.model_validate(requirement), "synthetic-staff"
    )
    assert repo.guidance_requirement("adu", first["revision_id"])["title"] == requirement["title"]
    requirement["change_note"] = "Second synthetic revision"
    second = repo.import_requirements(
        RequirementBundle.model_validate(requirement), "synthetic-staff", first["revision_id"]
    )
    assert second["revision_id"] != first["revision_id"]
    with pytest.raises(ValueError, match="superseded"):
        repo.guidance_requirement("adu", first["revision_id"])
    assert repo.guidance_requirement("adu")["change_note"] == "Second synthetic revision"
    engine.dispose()


def test_supplied_fee_is_copied_not_calculated(requirement):
    providers = load_providers(FIXTURE)
    row = providers["code"](source_id="sample-fee-schedule-adu")[0]
    requirement["fee_link"] = dict(
        provider="code", source_id=row["source_id"], expected_sha256=row["sha256"]
    )
    result = explain_pathway(
        project_type="adu", requirement=requirement, source_providers=providers
    )
    assert result.fee["as_published"] == row["text"]
    assert result.fee["official_calculation"] is False
    requirement["fee_link"]["expected_sha256"] = "0" * 64
    assert (
        explain_pathway(
            project_type="adu", requirement=requirement, source_providers=providers
        ).fee["status"]
        == "unavailable"
    )


def test_future_and_mismatched_requirements_are_refused(requirement):
    with pytest.raises(ValueError, match="project type"):
        explain_pathway(project_type="commercial", requirement=requirement)
    requirement["effective_on"] = "2099-01-01"
    with pytest.raises(ValueError, match="effective"):
        explain_pathway(project_type="adu", requirement=requirement)


def test_resident_api_uses_explicit_published_bundle(monkeypatch):
    monkeypatch.setenv(ENV_VAR, str(FIXTURE))
    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/civicpermit/pathway/explain",
            json={"project_type": "adu", "proposal": "Synthetic addition"},
        )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["attachments"][0]["material"] == "A dimensioned site plan."
    assert result["timeline"][0]["typical_time"] == "7 business days"
    assert result["assistance"]["executed"] is False


def test_unknown_project_has_no_generic_sample_fallback():
    result = explain_pathway(project_type="unmapped project")
    assert not result.attachments and not result.likely_permits
    assert result.fee["status"] == "unavailable"


def test_assisted_api_retains_honest_runtime_and_grounded_chunks(requirement):
    class Stub:
        name = "explicit-test-stub"

        async def generate(self, **kw):
            assert "7 business days" in " ".join(kw["chunks"])
            return "Explicit test-only explanation."

    result = asyncio.run(
        explain_pathway_with_assistant(project_type="adu", requirement=requirement, provider=Stub())
    )
    assert result.assistance["executed"] and result.assistance["provider"] == "explicit-test-stub"
    assert result.review_required and not result.determination_made


@pytest.mark.parametrize("kind", ["pdf", "docx"])
def test_retained_document_extraction_supports_guidance(requirement, kind):
    import io
    import zipfile

    text = "Planning intake followed by building review.\n7 business days\nA dimensioned site plan."
    if kind == "pdf":
        import fitz

        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((30, 40), text)
            raw = document.tobytes()
    else:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="urn:synthetic-word"><w:body><w:p><w:r><w:t>'
                + text
                + "</w:t></w:r></w:p></w:body></w:document>",
            )
        raw = buffer.getvalue()
    requirement.update(
        filename="requirements." + kind,
        content_base64=base64.b64encode(raw).decode(),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    result = explain_pathway(project_type="adu", requirement=requirement)
    assert result.timeline[0]["typical_time"] == "7 business days"
    assert result.attachments[0]["material"] == "A dimensioned site plan."


def test_invalid_published_requirement_configuration_is_unavailable(tmp_path, monkeypatch):
    path = tmp_path / "published.json"
    path.write_text(json.dumps({"sources": [], "requirements": [{"project_type": "adu"}]}))
    monkeypatch.setenv(ENV_VAR, str(path))
    with TestClient(main.app) as client:
        response = client.post("/api/v1/civicpermit/pathway/explain", json={"project_type": "adu"})
    assert response.status_code == 503
