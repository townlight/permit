"""Configured public source providers for cited pre-application guidance.

Sources are loaded from a JSON file named by ``CIVICPERMIT_PUBLIC_SOURCES``.
Each entry is one immutable, explicitly public record::

    {"provider": "code", "source_id": "...", "version": "...", "title": "...",
     "citation": "...", "text": "...", "visibility": "public"}

The shape matches what :mod:`civicpermit.connections` expects from an existing
trusted provider: `providers[name](source_id=...)` returns at most one row and
`providers[name](query=...)` returns candidate rows. SHA256 is computed from the
stored text here, so a caller cannot assert a digest that the text does not have.

When no file is configured the provider mapping is empty and every citation
attempt fails closed with "unavailable" - no sample text is substituted.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

ENV_VAR = "CIVICPERMIT_PUBLIC_SOURCES"


def load_requirement(project_type):
    """Explicitly published requirement bundles for the existing resident API."""
    from civicpermit.workflow_models import RequirementBundle
    path = os.environ.get(ENV_VAR)
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = payload.get("requirements", []) if isinstance(payload, dict) else []
        matches = [RequirementBundle.model_validate(row) for row in rows
                   if row.get("project_type", "").casefold() == project_type.strip().casefold()]
        return matches[0].model_dump(mode="json") if len(matches) == 1 else None
    except (OSError, ValueError, TypeError) as exc:
        raise SourceConfigError("Published requirement configuration is invalid.") from exc


class SourceConfigError(RuntimeError):
    """The configured source file is missing, unreadable or malformed."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize(row: Mapping[str, Any], provider: str) -> dict[str, Any]:
    text = str(row["text"])
    return {
        "provider": provider,
        "source_id": str(row["source_id"]),
        "version": row.get("version", "1"),
        "title": str(row.get("title", row["source_id"])),
        "citation": str(row.get("citation", row.get("title", row["source_id"]))),
        "text": text,
        "visibility": str(row.get("visibility", "public")),
        "sha256": _digest(text),
    }


def load_providers(path: str | os.PathLike[str] | None = None) -> dict[str, Callable[..., list[dict[str, Any]]]]:
    """Return ``{provider_name: callable}`` for the configured public sources."""

    raw_path = path or os.environ.get(ENV_VAR)
    if not raw_path:
        return {}
    file_path = Path(raw_path)
    if not file_path.is_file():
        raise SourceConfigError(f"{ENV_VAR} points at a missing file: {file_path}")
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceConfigError(f"{ENV_VAR} is not valid JSON: {exc}") from None

    entries = payload.get("sources", []) if isinstance(payload, dict) else payload
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        provider = str(entry.get("provider", "code"))
        by_provider.setdefault(provider, []).append(_normalize(entry, provider))

    providers: dict[str, Callable[..., list[dict[str, Any]]]] = {}
    for provider, rows in by_provider.items():
        def make(rows: list[dict[str, Any]]):
            def provider_call(*, source_id: str | None = None,
                              query: str | None = None) -> list[dict[str, Any]]:
                if source_id is not None:
                    return [dict(row) for row in rows if row["source_id"] == source_id]
                if query is None:
                    return []
                needle = query.casefold()
                return [dict(row) for row in rows
                        if needle in row["text"].casefold() or needle in row["title"].casefold()]
            return provider_call
        providers[provider] = make(rows)
    return providers
