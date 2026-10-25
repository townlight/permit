"""Durable municipal requirements, staff intake revisions and exact-byte packets."""
from datetime import UTC, datetime
import hashlib
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

import sqlalchemy as sa
from civiccore.audit import ZERO_HASH, compute_persisted_audit_hash

from civicpermit.connections import resolve, SourceUnavailable
from civicpermit.migrations import ready
from civicpermit.workflow_models import BOUNDARY, RequirementBundle
from civicpermit.workflow_schema import heads, revisions, packets, events


class Conflict(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class IntakeRepository:
    def __init__(self, engine, providers=None):
        self.engine = engine
        self.providers = providers or {}
        if not ready(engine):
            raise SourceUnavailable("Permitting schema unavailable; run the installed migration step.")

    def _lock(self, connection, entity_id):
        if connection.dialect.name == "postgresql":
            key = int.from_bytes(hashlib.sha256(("permit:" + entity_id).encode()).digest()[:8], "big", signed=True)
            connection.execute(sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    def _event(self, connection, entity_id, actor, action, details):
        prior = connection.execute(sa.select(events).where(events.c.entity_id == entity_id)
            .order_by(events.c.sequence.desc()).limit(1)).mappings().first()
        previous_hash = prior["entry_hash"] if prior else ZERO_HASH
        timestamp = datetime.now(UTC).isoformat()
        connection.execute(events.insert().values(event_id=str(uuid4()), entity_id=entity_id,
            sequence=prior["sequence"] + 1 if prior else 1, timestamp=timestamp,
            actor_id=actor, action=action, details=details, previous_hash=previous_hash,
            entry_hash=compute_persisted_audit_hash(previous_hash=previous_hash, timestamp=timestamp,
                actor_id=actor, action=action, details=details)))

    def _save(self, entity_id, kind, payload, actor, expected):
        if not actor.strip():
            raise ValueError("Authenticated staff identity required.")
        digest = sha(canonical(payload))
        revision_id = str(uuid5(NAMESPACE_URL, f"townlight:permit:{entity_id}:{expected}:{digest}"))
        with self.engine.begin() as connection:
            self._lock(connection, entity_id)
            current = connection.execute(sa.select(heads).where(heads.c.entity_id == entity_id)).mappings().first()
            if current and current["kind"] != kind:
                raise Conflict("Identifier belongs to another entity kind.")
            # A lost response can be read back without creating another revision.
            if current and current["revision_id"] == revision_id:
                return {"entity_id": entity_id, "revision_id": revision_id, "sha256": digest, "created": False}
            previous = current["revision_id"] if current else None
            if previous != expected:
                raise Conflict("Saved work changed; reload and reconcile before saving.")
            if not current:
                connection.execute(heads.insert().values(entity_id=entity_id, kind=kind, revision_id=revision_id))
            connection.execute(revisions.insert().values(revision_id=revision_id, entity_id=entity_id,
                parent_revision=previous, payload=payload, sha256=digest, actor_id=actor,
                created_at=datetime.now(UTC).isoformat()))
            if current:
                connection.execute(heads.update().where(heads.c.entity_id == entity_id).values(revision_id=revision_id))
            self._event(connection, entity_id, actor, f"permitting.{kind}.save",
                        {"revision_id": revision_id, "sha256": digest})
        return {"entity_id": entity_id, "revision_id": revision_id, "sha256": digest, "created": True}

    def import_requirements(self, bundle, actor, expected=None):
        return self._save("requirement:" + bundle.requirement_id, "requirement",
                          bundle.model_dump(mode="json"), actor, expected)

    def revision(self, revision_id, kind):
        with self.engine.connect() as connection:
            row = connection.execute(sa.select(revisions).join(heads)
                .where(revisions.c.revision_id == revision_id, heads.c.kind == kind)).mappings().first()
        if row is None:
            raise ValueError("Saved revision not found.")
        item = dict(row)
        if sha(canonical(item["payload"])) != item["sha256"]:
            raise ValueError("Saved evidence integrity failed.")
        if kind == "requirement":
            RequirementBundle.model_validate(item["payload"])
        return item

    def inventory(self, kind, offset=0):
        if kind not in ("requirement", "case") or not 0 <= offset <= 100000:
            raise ValueError("Invalid inventory page.")
        with self.engine.connect() as connection:
            rows = connection.execute(sa.select(revisions).join(heads,
                heads.c.revision_id == revisions.c.revision_id).where(heads.c.kind == kind)
                .order_by(revisions.c.entity_id).limit(51).offset(offset)).mappings().all()
        fields = ("title", "jurisdiction", "project_type", "dataset_kind") if kind == "requirement" else (
            "project_name", "review_state", "assigned_to")
        items = []
        for row in rows[:50]:
            if sha(canonical(row["payload"])) != row["sha256"]:
                raise ValueError("Saved evidence integrity failed.")
            items.append({k: row[k] for k in ("entity_id", "revision_id", "sha256", "created_at")} |
                         {k: row["payload"][k] for k in fields})
        return {"items": items, "next_offset": offset + 50 if len(rows) > 50 else None}

    def _links(self, payload):
        return [{"provider": link["provider"], "source": resolve(self.providers, link)}
                for link in payload["linked_sources"]]

    def save_case(self, data, actor, case_id=None):
        if case_id is None and data.expected_revision is not None:
            raise ValueError("A new case has no previous revision.")
        if case_id is not None and data.expected_revision is None:
            raise ValueError("Reload the current case before saving.")
        requirement = self.revision(str(data.requirement_revision), "requirement")["payload"]
        if {m["material_id"] for m in requirement["materials"]} != {m.material_id for m in data.materials}:
            raise ValueError("Review exactly the materials from the selected requirement revision.")
        payload = data.model_dump(mode="json", exclude={"expected_revision"})
        self._links(payload)
        payload.update(boundary=BOUNDARY, reviewer_id=actor if data.review_state == "reviewed" else None,
                       reviewed_on=datetime.now(UTC).date().isoformat() if data.review_state == "reviewed" else None)
        return self._save(case_id or str(uuid4()), "case", payload, actor,
                          str(data.expected_revision) if data.expected_revision else None)

    def get_case(self, case_id):
        with self.engine.connect() as connection:
            current = connection.execute(sa.select(heads).where(heads.c.entity_id == case_id,
                heads.c.kind == "case")).mappings().first()
        if not current:
            raise ValueError("Intake case not found.")
        item = self.revision(current["revision_id"], "case")
        requirement = self.revision(item["payload"]["requirement_revision"], "requirement")
        item["requirement"] = {k: v for k, v in requirement["payload"].items() if k != "content_base64"}
        try:
            item["connected_sources"] = self._links(item["payload"])
            item["connection_error"] = None
        except SourceUnavailable as exc:
            # Staff can remove a revoked selection and resave their own work.
            # No cached connected content is exposed or exported.
            item["connected_sources"] = []
            item["connection_error"] = str(exc)
        item["boundary"] = BOUNDARY
        return item

    def history(self, entity_id):
        with self.engine.connect() as connection:
            rows = connection.execute(sa.select(revisions).where(revisions.c.entity_id == entity_id)
                .order_by(revisions.c.created_at).limit(100)).mappings().all()
            audit = connection.execute(sa.select(events).where(events.c.entity_id == entity_id)
                .order_by(events.c.sequence).limit(1000)).mappings().all()
        previous = ZERO_HASH
        for row in audit:
            expected = compute_persisted_audit_hash(previous_hash=previous, timestamp=row["timestamp"],
                actor_id=row["actor_id"], action=row["action"], details=row["details"])
            if row["previous_hash"] != previous or row["entry_hash"] != expected:
                raise ValueError("Audit integrity failed.")
            previous = expected
        return {"revisions": [{k: row[k] for k in ("revision_id", "parent_revision", "sha256", "actor_id", "created_at")} for row in rows],
                "audit": [dict(row) for row in audit]}

    def packet(self, case_id, expected_revision, visibility, actor):
        if visibility not in ("staff_only", "records_copy"):
            raise ValueError("Choose a staff packet or explicitly reviewed Records copy.")
        case = self.get_case(case_id)
        if case["revision_id"] != expected_revision:
            raise Conflict("Case changed; reopen the saved case before exporting.")
        payload = case["payload"]
        if case["connection_error"]:
            raise SourceUnavailable(case["connection_error"])
        if payload["review_state"] != "reviewed":
            raise ValueError("Record explicit staff review before exporting.")
        if visibility == "records_copy" and not payload["public_summary"]:
            raise ValueError("Write and review a separate public summary for the Records copy.")
        sources = case["connected_sources"]
        record = {"boundary": BOUNDARY, "case_id": case_id, "revision_id": expected_revision,
            "project_name": payload["project_name"], "dataset_kind": case["requirement"]["dataset_kind"],
            "reviewer_id": payload["reviewer_id"], "reviewed_on": payload["reviewed_on"],
            "requirement": {k: case["requirement"][k] for k in (
                "title", "jurisdiction", "source_reference", "source_date", "effective_on", "sha256")},
            "connected_sources": sources}
        if visibility == "records_copy":
            record.update(public_summary=payload["public_summary"],
                          note="Staff-selected public copy for Records review; not automatically published or approved for release.")
        else:
            record.update(staff_intake=payload, requirement_checklist=case["requirement"]["materials"])
        text = canonical(record)
        digest = sha(text)
        packet_id = str(uuid5(NAMESPACE_URL, f"townlight:permit:packet:{case_id}:{visibility}:{digest}"))
        with self.engine.begin() as connection:
            self._lock(connection, case_id)
            current = connection.scalar(sa.select(heads.c.revision_id).where(heads.c.entity_id == case_id))
            if current != expected_revision:
                raise Conflict("Case changed during export; reopen it.")
            if not connection.execute(sa.select(packets.c.packet_id).where(packets.c.packet_id == packet_id)).first():
                connection.execute(packets.insert().values(packet_id=packet_id, case_id=case_id,
                    revision_id=expected_revision, visibility=visibility, text=text, sha256=digest,
                    actor_id=actor, created_at=datetime.now(UTC).isoformat()))
                self._event(connection, case_id, actor, "permitting.packet.create",
                    {"packet_id": packet_id, "sha256": digest, "visibility": visibility})
        return self.document(packet_id)

    def document(self, packet_id, records_only=False):
        with self.engine.connect() as connection:
            row = connection.execute(sa.select(packets).where(packets.c.packet_id == packet_id)).mappings().first()
        if not row or (records_only and row["visibility"] != "records_copy"):
            raise ValueError("Reviewed Records copy not found.")
        if sha(row["text"]) != row["sha256"]:
            raise ValueError("Packet integrity failed.")
        source_case = self.revision(row["revision_id"], "case")
        self._links(source_case["payload"])
        self.revision(source_case["payload"]["requirement_revision"], "requirement")
        record = json.loads(row["text"])
        return {"source_id": "permitting:" + packet_id, "version": packet_id, "packet_id": packet_id,
            "case_id": row["case_id"], "revision_id": row["revision_id"], "title": record["project_name"],
            "citation": f"Townlight Permitting intake {row['case_id']}, revision {row['revision_id']}",
            "kind": "permitting-intake", "text": row["text"], "sha256": row["sha256"],
            "visibility": "public" if row["visibility"] == "records_copy" else "staff_only"}

    def records_documents(self, query="", source_id=None):
        if source_id is not None:
            prefix = "permitting:"
            if not source_id.startswith(prefix):
                return []
            try:
                return [self.document(source_id[len(prefix):], records_only=True)]
            except (ValueError, SourceUnavailable):
                return []
        with self.engine.connect() as connection:
            ids = connection.scalars(sa.select(packets.c.packet_id).where(packets.c.visibility == "records_copy")
                .order_by(packets.c.created_at.desc()).limit(200)).all()
        result = []
        for packet_id in ids:
            try:
                item = self.document(packet_id, records_only=True)
                if query.casefold() in (item["title"] + " " + item["text"]).casefold():
                    result.append(item)
            except (ValueError, SourceUnavailable):
                continue
        return result
