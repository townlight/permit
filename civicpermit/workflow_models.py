"""Configured municipal intake support, never a permit determination."""
import base64
import hashlib
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

BOUNDARY = (
    "Pre-application staff workpaper only. Not a permit, official completeness determination, "
    "fee calculation, inspection, entitlement decision or permitting-system-of-record action."
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Material(Model):
    material_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    description: str = Field(min_length=1, max_length=2000)
    citation: str = Field(min_length=1, max_length=1000)


class PathwayStep(Model):
    step: str = Field(min_length=1, max_length=2000)
    citation: str = Field(min_length=1, max_length=1000)
    typical_time: str = Field(default="", max_length=1000)


class SourceLink(Model):
    provider: Literal["code", "zoning"]
    source_id: str = Field(min_length=1, max_length=500)
    expected_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RequirementBundle(Model):
    requirement_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    title: str = Field(min_length=1, max_length=500)
    jurisdiction: str = Field(min_length=1, max_length=255)
    project_type: str = Field(min_length=1, max_length=255)
    source_reference: str = Field(min_length=1, max_length=1000)
    source_date: date
    effective_on: date
    dataset_kind: Literal["municipal", "fictional"]
    filename: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,150}$")
    content_base64: str = Field(min_length=1, max_length=14_000_000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    materials: list[Material] = Field(min_length=1, max_length=100)
    pathway: list[PathwayStep] = Field(default_factory=list, max_length=100)
    fee_link: SourceLink | None = None
    staff_note: str = Field(default="", max_length=4000)
    change_note: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def original_and_materials(self):
        try:
            raw = base64.b64decode(self.content_base64, validate=True)
        except ValueError:
            raise ValueError("Original source must be valid base64.") from None
        if not raw or len(raw) > 10_000_000 or hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("Original source bytes do not match their SHA256 or size limit.")
        ids = [m.material_id for m in self.materials]
        if len(set(ids)) != len(ids):
            raise ValueError("Material identifiers must be unique.")
        return self


class MaterialReview(Model):
    material_id: str = Field(min_length=1, max_length=80)
    status: Literal["not_reviewed", "provided", "missing", "unclear"] = "not_reviewed"
    note: str = Field(default="", max_length=2000)


class IntakeInput(Model):
    expected_revision: UUID | None = None
    project_name: str = Field(min_length=1, max_length=500)
    project_description: str = Field(min_length=1, max_length=10000)
    location: str = Field(min_length=1, max_length=1000)
    applicant_contact: str = Field(default="", max_length=2000)
    requirement_revision: UUID
    materials: list[MaterialReview] = Field(min_length=1, max_length=100)
    linked_sources: list[SourceLink] = Field(default_factory=list, max_length=30)
    staff_notes: str = Field(default="", max_length=10000)
    assigned_to: str = Field(default="", max_length=255)
    review_state: Literal["draft", "follow_up", "reviewed"] = "draft"
    review_notes: str = Field(default="", max_length=4000)
    public_summary: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def review(self):
        ids = [m.material_id for m in self.materials]
        if len(set(ids)) != len(ids):
            raise ValueError("Review each checklist material once.")
        links = [(s.provider, s.source_id) for s in self.linked_sources]
        if len(set(links)) != len(links):
            raise ValueError("Select each connected source once.")
        if self.review_state == "reviewed":
            if not self.review_notes or any(m.status == "not_reviewed" for m in self.materials):
                raise ValueError("Record staff review notes and review each material explicitly.")
        return self
