Townlight Permitting
===========

Townlight Permitting is the Townlight module for permit pre-application and development-review intake support.

Unpublished source: 0.3.0+dev.1 connected staff candidate. Configured municipal requirements, immutable case revisions, current permission-checked Code/Zoning evidence, attributed human review and an explicit Records copy. See docs/connected-workflow.md. Historical release context follows; this source change does not publish or sign an installer.

Current state: v0.2.2 corrective demotion state. The previous v1.0.0 release was published in error. This narrow truth-repair release is no functional upgrade; it exists solely to supersede the false v1.0.0 release from 2026-05-21 in GitHub's Latest impression, with the Townlight Core pin unchanged. This repo contains a deterministic scaffold aligned to the published Townlight Core v1.1.0 release wheel, health/root endpoints, documentation gates, deterministic and database-backed permit requirement lookup, staff-gated persisted intake records, staff review queues, review-required CivicZone/CivicCode context packets, adversarial local integration mocks, intake-readiness review, submittal outline support, records-ready export checklist, and accessible public sample UI at /civicpermit.

It does not ship permit approvals, official completeness determinations, fee calculations, inspections, legal advice, live GIS, live LLM calls, permit-system writeback, or system-of-record behavior.

Core API:
- GET /
- GET /health
- GET /civicpermit
- POST /api/v1/civicpermit/requirements/lookup
- POST /api/v1/civicpermit/context/development-review
- POST /api/v1/civicpermit/integrations/mock/development-review
- POST /api/v1/civicpermit/intake/review
- GET /api/v1/civicpermit/intake/{intake_id}
- POST /api/v1/civicpermit/staff/reviews
- GET /api/v1/civicpermit/staff/reviews
- PATCH /api/v1/civicpermit/staff/reviews/{review_id}
- GET /api/v1/civicpermit/staff/reviews/summary
- POST /api/v1/civicpermit/submittal/outline
- POST /api/v1/civicpermit/export

Quickstart: install Townlight Core first with python -m pip install https://github.com/CivicSuite/civiccore/releases/download/v1.1.0/civiccore-1.1.0-py3-none-any.whl, then run python -m pip install -e ".[dev]".

Set CIVICPERMIT_INTAKE_DB_URL to enable persistent permit requirement, intake review, and staff review queue records. Persisted staff routes require CIVICPERMIT_STAFF_API_KEY, X-CivicPermit-Role: staff, and matching X-CivicPermit-Staff-Key from a trusted staff or service workflow. When unset, Townlight Permitting continues to use deterministic in-memory sample data for public applicant guidance.

Code license: AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. See LICENSE and LICENSE-EXCEPTION.md. Documentation license: CC BY 4.0 (LICENSE-DOCS).
