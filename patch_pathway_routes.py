"""Patch: wire the cited pathway routes and resident explainer into main.py.

Additive only. Idempotent: refuses to apply twice.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "civicpermit" / "main.py"
text = P.read_text(encoding="utf-8")

if "pathway_explain" in text:
    print("already patched")
    raise SystemExit(0)

# 1. imports
old_imports = """from civicpermit.public_ui import render_public_lookup_page
from civicpermit.records_export import build_policy_export"""
new_imports = """from civicpermit.pathway import (
    BOUNDARY as PATHWAY_BOUNDARY,
    explain_pathway,
    explain_pathway_with_assistant,
)
from civicpermit.public_ui import render_public_lookup_page
from civicpermit.records_export import build_policy_export
from civicpermit.sources import load_providers"""
assert old_imports in text
text = text.replace(old_imports, new_imports, 1)

# 2. request models
old_model = '''class IntegrationMockRequest(BaseModel):'''
new_model = '''class PathwayRequest(BaseModel):
    project_type: str = Field(min_length=1, max_length=255)
    proposal: str = Field(default="", max_length=5000)
    location_context: str = Field(default="", max_length=500)
    use_model_assistance: bool = Field(default=False)


class IntegrationMockRequest(BaseModel):'''
assert old_model in text
text = text.replace(old_model, new_model, 1)

# 3. routes, inserted before the development-review context route
old_route = '''@app.post("/api/v1/civicpermit/context/development-review")'''
new_route = '''def _pathway_provider():
    """Return the configured live provider, or None when none is available.

    Only a genuinely constructible provider is returned; a provider that cannot
    be built is reported to the caller rather than silently replaced by a stub.
    """
    name = os.environ.get("CIVICPERMIT_LLM_PROVIDER", "").strip()
    if not name:
        return None, None
    from civiccore.llm.factory import build_provider
    from civiccore.llm.providers.config import AnthropicConfig, OllamaConfig, OpenAIConfig

    configs = {"ollama": OllamaConfig, "openai": OpenAIConfig,
               "anthropic": AnthropicConfig}
    schema = configs.get(name)
    if schema is None:
        raise HTTPException(
            status_code=503,
            detail={"message": f"Configured permit assistant provider '{name}' is not supported.",
                    "fix": "Set CIVICPERMIT_LLM_PROVIDER to ollama, openai or anthropic."},
        )
    model = os.environ.get("CIVICPERMIT_LLM_MODEL") or None
    return build_provider(name, schema()), model


def _pathway_sources():
    try:
        return load_providers()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"message": "Configured public permit sources could not be read.",
                    "fix": f"Check CIVICPERMIT_PUBLIC_SOURCES ({type(exc).__name__})."},
        ) from None


def _pathway_payload(result) -> dict[str, object]:
    return {
        "project_type": result.project_type,
        "title": result.title,
        "likely_permits": result.likely_permits,
        "attachments": result.attachments,
        "timeline": result.timeline,
        "unavailable": result.unavailable,
        "fee": result.fee,
        "resident_explanation": result.resident_explanation,
        "assistance": result.assistance,
        "citations": result.citations,
        "review_required": result.review_required,
        "determination_made": result.determination_made,
        "boundary": result.boundary,
        "disclaimer": result.disclaimer,
    }


@app.post("/api/v1/civicpermit/pathway/explain")
def pathway_explain(request: PathwayRequest) -> dict[str, object]:
    """Cited likely pathway/attachments/timeline/explainer, no model call."""

    result = explain_pathway(
        project_type=request.project_type,
        proposal=request.proposal,
        location_context=request.location_context,
        source_providers=_pathway_sources(),
    )
    return _pathway_payload(result)


@app.post("/api/v1/civicpermit/pathway/explain-assisted")
async def pathway_explain_assisted(request: PathwayRequest) -> dict[str, object]:
    """Same, plus an actual configured-provider call; `assistance` says what ran."""

    sources = _pathway_sources()
    provider, model = _pathway_provider()
    result = await explain_pathway_with_assistant(
        project_type=request.project_type,
        proposal=request.proposal,
        location_context=request.location_context,
        source_providers=sources,
        provider=provider if request.use_model_assistance else None,
        model=model,
    )
    payload = _pathway_payload(result)
    payload["boundary"] = PATHWAY_BOUNDARY
    return payload


@app.post("/api/v1/civicpermit/context/development-review")'''
assert old_route in text
text = text.replace(old_route, new_route, 1)

P.write_text(text, encoding="utf-8")
print("main.py patched: pathway routes added")
