"""Cited pre-application pathway, attachments, timeline and resident explainer.

Beta scope (see outputs/Townlight-Minimum-Beta-Scope-Audit-2026-10-27.md §2.2):
turn an applicant's plain project description into the *likely* permit pathway,
the required attachments, the typical review timeline and a resident-readable
explanation - every element carrying a citation that resolved from a configured
public source.

Deliberate boundaries:

* No official fee computation, no payment, no issuance, no scheduling, no
  completeness determination.
* Fee amounts are used only when a cited official fee source resolves; when none
  is configured the fee block says so explicitly instead of inventing a number.
* Every citation is the `citation` field of a source that resolved with a
  matching SHA256 through :mod:`civicpermit.connections`; a stage whose source
  does not resolve is withheld and reported as unavailable, never paraphrased
  from memory.
* Model assistance is optional and reported honestly: `executed` is true only
  when a provider actually produced text, and `provider` names what ran so a
  stub can never be mistaken for a live model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from civicpermit.connections import SourceUnavailable, resolve
from civicpermit.requirement_lookup import DISCLAIMER
from civicpermit.workflow_models import RequirementBundle
from datetime import date
import base64
import io
import re
import zipfile
from xml.etree import ElementTree


def _source_text(bundle):
    raw = base64.b64decode(bundle.content_base64)
    try:
        if bundle.filename.lower().endswith('.pdf'):
            import fitz
            with fitz.open(stream=raw, filetype='pdf') as document:
                return '\n'.join(page.get_text() for page in document)
        if bundle.filename.lower().endswith('.docx'):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                root = ElementTree.fromstring(archive.read('word/document.xml'))
                return ' '.join(node.text or '' for node in root.iter()
                                if node.tag.endswith('}t'))
        return raw.decode('utf-8')
    except (ValueError, UnicodeDecodeError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        return ''


def _occurs(excerpt, original):
    return re.sub(r'\s+', ' ', excerpt).strip() in re.sub(r'\s+', ' ', original).strip()


BOUNDARY = (
    "This is pre-application assistance. It names likely permits, attachments and "
    "typical review timing from cited public sources; it is not an official "
    "determination, not an official fee calculation, and it does not schedule, "
    "issue or approve anything. Staff must confirm the official application type."
)

NO_FEE_SOURCE = (
    "No cited official fee schedule is configured, so no fee amount or estimate is "
    "given. Staff must quote the official fee at intake."
)


class AssistantProvider(Protocol):
    """Structural type of the civiccore LLM provider used for the explainer."""

    name: str

    async def generate(
        self,
        *,
        system_prompt: str,
        user_content: str,
        model: str | None = None,
        chunks: list[str] | None = None,
        **kwargs: Any,
    ) -> str: ...


@dataclass(frozen=True)
class PathwayStage:
    """A cited step in the pre-application pathway.

    ``source_id`` is resolved through the configured public source providers;
    the displayed citation and text are copied from the resolved source so the
    pathway can never show a citation that does not exist.
    """

    key: str
    label: str
    source_id: str
    typical_time: str


@dataclass(frozen=True)
class Pathway:
    project_type: str
    title: str
    stages: tuple[PathwayStage, ...]
    attachments_citation: str
    attachments: tuple[str, ...]
    note: str = ""


SYSTEM_PROMPT = (
    "You are a municipal permit intake assistant. Using ONLY the numbered cited "
    "excerpts provided, write a short plain-language explanation of the likely "
    "permit pathway, the attachments the applicant should gather, and typical "
    "review timing. Do not state fee amounts, do not promise approval, and do not "
    "cite anything that is not in the excerpts. End by saying staff confirm the "
    "official application type."
)


def select_pathway(project_type: str) -> Pathway:
    """Label a request; all municipal content must come from imported evidence."""
    return Pathway(project_type=project_type, title=f"Likely pathway: {project_type}",
                   stages=(), attachments_citation="", attachments=())


@dataclass
class PathwayExplanation:
    """Assembled, citation-checked pre-application explanation."""

    project_type: str
    title: str
    likely_permits: list[dict[str, str]] = field(default_factory=list)
    attachments: list[dict[str, str]] = field(default_factory=list)
    timeline: list[dict[str, str]] = field(default_factory=list)
    unavailable: list[dict[str, str]] = field(default_factory=list)
    fee: dict[str, object] = field(default_factory=dict)
    resident_explanation: str = ""
    assistance: dict[str, object] = field(default_factory=dict)
    review_required: bool = True
    determination_made: bool = False
    citations: list[str] = field(default_factory=list)
    boundary: str = BOUNDARY
    disclaimer: str = DISCLAIMER


def explain_pathway(
    *,
    project_type: str,
    proposal: str = "",
    location_context: str = "",
    source_providers: Mapping[str, Callable[..., Any]] | None = None,
    fee_link: Mapping[str, str] | None = None,
    requirement: Mapping[str, Any] | None = None,
    provider: AssistantProvider | None = None,
    model: str | None = None,
) -> PathwayExplanation:
    """Build the cited pathway explanation; never decides or prices anything."""

    providers: Mapping[str, Callable[..., Any]] = source_providers or {}
    result = PathwayExplanation(project_type=project_type,
                                title=select_pathway(project_type).title)
    if requirement is not None:
        bundle = RequirementBundle.model_validate(requirement)
        if bundle.project_type.casefold() != project_type.strip().casefold():
            raise ValueError("Choose the project type of the selected requirement revision.")
        if bundle.effective_on > date.today():
            raise ValueError("The selected requirement revision is not effective yet.")
        result.title = bundle.title
        # Staff import verified extracts against the retained original. Never
        # attach a valid unrelated citation to fixed sample prose.
        original = _source_text(bundle)
        for material in bundle.materials:
            if _occurs(material.description, original):
                result.attachments.append({"material": material.description,
                    "citation": material.citation, "source_id": bundle.requirement_id,
                    "source_sha256": bundle.sha256})
                result.citations.append(material.citation)
            else:
                result.unavailable.append({"item": "required attachment",
                    "reason": "The imported material is not present in extracted source text; staff must supply a supported extract."})
        for stage in bundle.pathway:
            if not _occurs(stage.step, original) or (stage.typical_time and not _occurs(stage.typical_time, original)):
                result.unavailable.append({"item": "pathway stage",
                    "reason": "The stage or timing is not present in the retained source."})
                continue
            item = {"step": stage.step, "typical_time": stage.typical_time or "Unavailable in the cited source",
                    "citation": stage.citation, "source_id": bundle.requirement_id,
                    "source_version": str(requirement.get("revision_id", bundle.source_date)),
                    "source_sha256": bundle.sha256}
            result.likely_permits.append(item)
            if stage.typical_time:
                result.timeline.append(dict(item))
            else:
                result.unavailable.append({"item": "review timing", "reason": "The imported stage supplies no supported timing."})
            result.citations.append(stage.citation)
        if fee_link is None and bundle.fee_link is not None:
            fee_link = bundle.fee_link.model_dump()
    if not result.likely_permits:
        result.unavailable.append({"item": "review pathway and timing",
            "reason": "No supported effective imported pathway is available; staff must supply it."})
    if not result.attachments:
        result.unavailable.append({"item": "required attachments",
            "reason": "No supported effective imported checklist is available; staff must supply it."})
    result.citations = list(dict.fromkeys(result.citations))

    # 3. Fees: only from a cited official source; otherwise explicit.
    if fee_link and providers:
        try:
            fee_source = resolve(providers, dict(fee_link))
        except SourceUnavailable:
            result.fee = {"status": "unavailable", "amount": None,
                          "reason": "the configured fee source did not resolve; no "
                                    "amount or estimate is given",
                          "official_calculation": False}
        else:
            result.fee = {"status": "cited_source",
                          "as_published": fee_source["text"].strip(),
                          "citation": fee_source["citation"],
                          "source_id": fee_source["source_id"],
                          "official_calculation": False,
                          "note": "Copied from the cited source; this is informational "
                                  "and staff confirm the official fee at intake."}
            if fee_source["citation"] not in result.citations:
                result.citations.append(fee_source["citation"])
    else:
        result.fee = {"status": "unavailable", "amount": None, "reason": NO_FEE_SOURCE,
                      "official_calculation": False}

    # 4. Deterministic resident explanation built from the cited set only.
    result.resident_explanation = _deterministic_explainer(result, proposal)

    # 5. Optional model assistance, reported exactly as executed.
    result.assistance = _assistance_record(provider, model, result)
    return result


def _deterministic_explainer(result: PathwayExplanation, proposal: str) -> str:
    lines: list[str] = []
    if result.likely_permits:
        steps = "; ".join(f"{item['step']} ({item['typical_time']})"
                          for item in result.likely_permits)
        lines.append(f"Based on the description, the likely pathway is: {steps}.")
    else:
        lines.append("No cited review pathway could be assembled for this description.")
    if result.attachments:
        lines.append("Gather these attachments first: "
                     + "; ".join(item["material"] for item in result.attachments))
    else:
        lines.append("No cited attachment list is available; staff will supply it.")
    if result.fee.get("status") == "unavailable":
        lines.append(str(result.fee["reason"]))
    else:
        lines.append(f"Published fee information: {result.fee.get('as_published')}")
    lines.append("Staff confirm the official application type, completeness and fees.")
    return " ".join(lines)


def _assistance_record(provider: AssistantProvider | None, model: str | None,
                       result: PathwayExplanation) -> dict[str, object]:
    if provider is None:
        return {"requested": False, "executed": False,
                "reason": "no live model provider is configured for this deployment; "
                          "the explanation above is generated deterministically from "
                          "the cited sources",
                "provider": None, "model": None}
    return {"requested": True, "executed": False,
            "reason": "provider configured; call explain_pathway_with_assistant to run it",
            "provider": getattr(provider, "name", "unknown"), "model": model}


async def explain_pathway_with_assistant(
    *,
    project_type: str,
    proposal: str = "",
    location_context: str = "",
    source_providers: Mapping[str, Callable[..., Any]] | None = None,
    fee_link: Mapping[str, str] | None = None,
    requirement: Mapping[str, Any] | None = None,
    provider: AssistantProvider | None = None,
    model: str | None = None,
) -> PathwayExplanation:
    """Same as :func:`explain_pathway`, plus an actual provider call when configured."""

    result = explain_pathway(
        project_type=project_type, proposal=proposal,
        location_context=location_context, source_providers=source_providers,
        fee_link=fee_link, requirement=requirement, provider=provider, model=model)
    if provider is None:
        return result

    chunks = [f"[{index}] {item['citation']}: {item['step']} — {item['typical_time']}"
              for index, item in enumerate(result.likely_permits, start=1)]
    chunks += [f"Attachment: {item['material']} ({item['citation']})"
               for item in result.attachments]
    user_content = (
        f"Project description: {proposal or project_type}\n"
        f"Location context: {location_context or 'not supplied'}\n"
        "Cited excerpts:\n" + "\n".join(chunks)
    )
    try:
        text = await provider.generate(
            system_prompt=SYSTEM_PROMPT, user_content=user_content,
            model=model, chunks=chunks)
    except Exception as exc:  # provider/runtime failure is reported, not hidden
        result.assistance = {
            "requested": True, "executed": False,
            "provider": getattr(provider, "name", "unknown"), "model": model,
            "reason": f"provider call failed: {type(exc).__name__}",
        }
        return result
    if not text or not text.strip():
        result.assistance = {
            "requested": True, "executed": False,
            "provider": getattr(provider, "name", "unknown"), "model": model,
            "reason": "provider returned no text",
        }
        return result
    result.resident_explanation = text.strip()
    result.assistance = {
        "requested": True, "executed": True,
        "provider": getattr(provider, "name", "unknown"), "model": model,
        "reason": "provider generated the explanation from the cited excerpts only",
        "review_required": True,
    }
    return result
