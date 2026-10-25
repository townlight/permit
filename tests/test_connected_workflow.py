"""Affected invariants: municipal originals, review, conflicts, private fields and revocation."""
import base64
import hashlib
import json

import pytest
from sqlalchemy import text

from civicpermit.connections import SourceUnavailable
from civicpermit.migrations import ready, source_engine, upgrade
from civicpermit.workflow_models import IntakeInput, RequirementBundle
from civicpermit.workflow_store import IntakeRepository, Conflict


def bundle():
    raw = b"Fictional Redstone intake manual: submit a site plan and owner authorization."
    return RequirementBundle(requirement_id="adu", title="ADU intake manual", jurisdiction="Fictional Redstone",
        project_type="ADU", source_reference="Fictional intake manual, section 2", source_date="2026-01-01",
        effective_on="2026-02-01", dataset_kind="fictional", filename="intake.txt",
        content_base64=base64.b64encode(raw).decode(), sha256=hashlib.sha256(raw).hexdigest(),
        materials=[{"material_id": key, "description": description, "citation": "Fictional manual section 2"}
                   for key, description in [("site", "Site plan"), ("owner", "Owner authorization")]],
        change_note="Fictional configured municipal requirements")


@pytest.fixture
def repository(tmp_path):
    engine = source_engine("sqlite:///" + str(tmp_path / "permitting.db"))
    assert not ready(engine)
    upgrade(engine)
    assert ready(engine)
    upgrade(engine)  # Migration replay, not recreation of business state.
    source = {"source_id": "code:2", "title": "ADU section", "version": "v2", "citation": "Code 2",
              "visibility": "public", "text": "Fictional adopted ADU requirements."}
    source["sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
    available = [source]
    def provider(**_kwargs):
        return available
    repo = IntakeRepository(engine, {"code": provider, "zoning": provider})
    requirement = repo.import_requirements(bundle(), "staff-1")
    yield repo, requirement, source, available
    engine.dispose()


def draft(requirement, source, **changes):
    return IntakeInput.model_validate({"project_name": "Fictional ADU", "project_description": "PRIVATE proposal",
        "location": "PRIVATE address", "applicant_contact": "PRIVATE contact", "staff_notes": "PRIVATE notes",
        "requirement_revision": requirement["revision_id"],
        "materials": [{"material_id": "site", "status": "provided"}, {"material_id": "owner", "status": "missing"}],
        "linked_sources": [{"provider": "code", "source_id": source["source_id"], "expected_sha256": source["sha256"]}],
        **changes})


def test_saved_intake_review_packet_and_reopen(repository):
    repo, requirement, source, _ = repository
    first = repo.save_case(draft(requirement, source), "staff-1")
    case_id = first["entity_id"]
    assert repo.get_case(case_id)["requirement"]["title"] == "ADU intake manual"
    reopened = IntakeRepository(repo.engine, repo.providers)
    assert reopened.get_case(case_id)["payload"]["applicant_contact"] == "PRIVATE contact"
    with pytest.raises(ValueError, match="explicit staff review"):
        repo.packet(case_id, first["revision_id"], "staff_only", "staff-1")
    reviewed = draft(requirement, source, expected_revision=first["revision_id"], review_state="reviewed",
        review_notes="Owner authorization still required; intake support only.", public_summary="A reviewed pre-application inquiry.")
    saved = repo.save_case(reviewed, "staff-2", case_id)
    assert repo.get_case(case_id)["payload"]["reviewer_id"] == "staff-2"
    packet = repo.packet(case_id, saved["revision_id"], "records_copy", "staff-2")
    assert "PRIVATE" not in packet["text"]
    assert source["sha256"] in packet["text"] and "not automatically published" in packet["text"]
    assert hashlib.sha256(packet["text"].encode()).hexdigest() == packet["sha256"]
    private = repo.packet(case_id, saved["revision_id"], "staff_only", "staff-2")
    assert "PRIVATE contact" in private["text"]
    assert repo.records_documents(source_id=private["source_id"]) == []
    assert repo.records_documents(source_id=packet["source_id"])[0] == packet
    assert len(repo.history(case_id)["revisions"]) == 2
    assert len(repo.history(case_id)["audit"]) == 4
    with pytest.raises(Conflict):
        repo.save_case(draft(requirement, source, expected_revision=first["revision_id"], project_name="Stale editor"), "staff-1", case_id)
    # Editing creates a draft with no retained review attribution; old packet stays exact.
    changed = repo.save_case(draft(requirement, source, expected_revision=saved["revision_id"]), "staff-1", case_id)
    assert repo.get_case(case_id)["payload"]["reviewer_id"] is None
    assert repo.document(packet["packet_id"])["sha256"] == packet["sha256"]
    assert changed["revision_id"] != saved["revision_id"]
    # An amended municipal checklist retains the earlier original and the case's
    # explicitly selected revision; there is no silent migration of staff work.
    amended = bundle().model_copy(update={"change_note":"Fictional amendment", "title":"Amended intake manual"})
    later = repo.import_requirements(amended, "staff-2", requirement["revision_id"])
    assert later["revision_id"] != requirement["revision_id"]
    assert repo.get_case(case_id)["requirement"]["title"] == "ADU intake manual"
    assert repo.revision(requirement["revision_id"], "requirement")["payload"]["sha256"] == bundle().sha256
    with pytest.raises(Conflict):
        repo.import_requirements(bundle(), "staff-1", requirement["revision_id"])


def test_source_permission_and_integrity_are_rechecked(repository):
    repo, requirement, source, available = repository
    saved = repo.save_case(draft(requirement, source, review_state="reviewed", review_notes="Checked.", public_summary="Public."), "staff", None)
    packet = repo.packet(saved["entity_id"], saved["revision_id"], "records_copy", "staff")
    available.clear()
    assert repo.get_case(saved["entity_id"])["connection_error"]
    assert repo.records_documents(source_id=packet["source_id"]) == []
    with pytest.raises(SourceUnavailable):
        repo.document(packet["packet_id"])
    with pytest.raises(SourceUnavailable):
        repo.save_case(draft(requirement, source), "staff")
    available.append({**source, "visibility": "restricted"})
    assert repo.records_documents(source_id=packet["source_id"]) == []
    available[0] = {**source, "text": "Changed without hash"}
    assert repo.records_documents(source_id=packet["source_id"]) == []


def test_original_hash_materials_and_review_are_not_caller_assertions(repository):
    repo, requirement, source, _ = repository
    with pytest.raises(ValueError, match="SHA256"):
        RequirementBundle.model_validate({**bundle().model_dump(), "sha256": "0" * 64})
    with pytest.raises(ValueError, match="exactly the materials"):
        repo.save_case(draft(requirement, source, materials=[{"material_id": "fake", "status": "provided"}]), "staff")
    with pytest.raises(ValueError):
        draft(requirement, source, review_state="reviewed", reviewer_id="spoofed")
    # Database guards reject mutation rather than relying only on application code.
    with pytest.raises(Exception, match="append-only"):
        with repo.engine.begin() as connection:
            connection.execute(text("UPDATE connected_revisions SET payload=:value"), {"value": json.dumps({})})
    assert repo.inventory("case")["items"] == []
    assert repo.inventory("requirement")["items"][0]["dataset_kind"] == "fictional"
