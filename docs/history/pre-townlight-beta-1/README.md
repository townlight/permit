# Townlight Permitting

**Complete the intake workpaper before the official decision.**

Permitting supports pre-application and intake preparation. The city’s permitting system remains the system of record. A material assessment is staff work, not an official completeness decision.

## Use this product

- [Current user manual](USER-MANUAL.md): installed workflow, roles, sources, review, export, recovery and limits.
- [Product landing page](https://townlight.github.io/products/permitting/).
- [Overall eight-product manual](https://github.com/townlight/townlight/blob/main/USER-MANUAL.md) and [feature/integration assessment](https://github.com/townlight/townlight/blob/main/docs/assessment/feature-and-integration-review.md).
- [Signed composition and acceptance](https://github.com/townlight/townlight/releases/tag/townlight-records-meetings-code-zoning-planning-permitting-v1.6.0-beta.1): Signed Permitting 1.6.0-beta.1.

Permitting consumes Core, Code and Zoning, and sends a reviewed copy to Records. The release does not connect every permitting vendor or automatically create an Inspections case.

## Release scope

No permit issuance, fee collection, inspection scheduling, official entitlement determination, public applicant portal or live permit-system writeback is provided. Read-only vendor status mirroring and hearing-notice integration from the broader catalog have not been established by the installed acceptance.

Documentation reviewed 2026-10-26. Installed acceptance, source/API implementation and future requirements are different evidence. Code is AGPL-3.0-only with the repository’s public institution exception where applicable; documentation is CC BY 4.0. See the repository license files.

## Historical repository reference

The earlier README below is retained for package history and contributor commands. Older maturity/version statements describe that historical reference and are superseded by the current operating guide and linked release evidence.

<a id="civicpermit"></a>

# Townlight Permitting

Townlight Permitting is the Townlight module for permit pre-application and development-review intake support.

Historical published state: **v0.2.2 corrective demotion state - deterministic scaffold; no real AI layer, full frontend, Alembic migrations, real municipal data/search, or public-use gate. The previous v1.0.0 release was published in error. This narrow truth-repair release is no functional upgrade; it exists solely to supersede the false v1.0.0 release from 2026-05-21 in GitHub's Latest impression. The Townlight Core pin is unchanged.**. This repo contains a FastAPI package aligned to the published Townlight Core v1.1.0 release wheel, health/root endpoints, documentation gates, deterministic and database-backed permit requirement lookup, staff-gated persisted intake records, staff review queues, review-required CivicZone/CivicCode context packets, adversarial local integration mocks, intake-readiness review, submittal outline support, records-ready export checklist, and accessible public sample UI at `/civicpermit`. See [docs/release-recovery-status.md](docs/release-recovery-status.md) for the local release gate, browser QA, and CI evidence.

It does **not** ship permit approvals, official completeness determinations, fee calculations, inspections, legal advice, live GIS, live LLM calls, permit-system writeback, or system-of-record behavior.

<a id="what-civicpermit-does"></a>

## What Townlight Permitting Does

- Looks up permit requirement checklists for common applicant scenarios.
- Supports locally configured requirement records through `CIVICPERMIT_INTAKE_DB_URL`.
- Returns review-required development-review context packets that can carry Townlight Zoning and Townlight Code context IDs without calling those systems live.
- Flags missing or unclear intake materials while keeping permit-counter staff responsible for official completeness review.
- Creates staff-only review queue items for persisted deficient intakes.
- Drafts submittal outlines that require staff review.
- Builds records-ready export checklists that preserve inquiry, checklist, reviewer, queue, and generated-output provenance.
- Validates local adversarial integration mocks for missing context, spoofed approvals, fee attempts, stale sources, and role spoofing.
- Demonstrates a public pre-application intake UI at `/civicpermit`.

## Connected staff development workflow - 0.3.0+dev.1

An unpublished connected workflow now adds versioned municipal requirement originals, intake cases, explicit material review, staff-attributed review, permission/hash checked Code and Zoning citations, immutable staff packets and separately edited Records copies. It runs through the opt-in Townlight desktop candidate using canonical native sessions and PostgreSQL. No signing or publication is claimed. See [the connected workflow guide](docs/connected-workflow.md). The sample endpoints below remain historical scaffolding and are not the connected staff API.

## Developer Quickstart

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install https://github.com/townlight/core/releases/download/v1.2.1/civiccore-1.2.1-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pytest -q
bash scripts/verify-release.sh
```

For WSL verification:

```bash
python3 -m venv .venv-wsl
. .venv-wsl/bin/activate
python -m pip install https://github.com/townlight/core/releases/download/v1.2.1/civiccore-1.2.1-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pytest -q
bash scripts/verify-release.sh
```

## API Surface

- `GET /` returns current module status and product boundary.
- `GET /health` returns package and Townlight Core version information.
- `GET /civicpermit` returns the accessible public sample UI.
- `POST /api/v1/civicpermit/requirements/lookup` returns a permit requirement checklist.
- `POST /api/v1/civicpermit/context/development-review` returns review-required permit intake context with optional CivicZone/CivicCode context IDs.
- `POST /api/v1/civicpermit/integrations/mock/development-review` validates local adversarial integration payloads.
- `POST /api/v1/civicpermit/intake/review` returns intake-readiness factors; persisted records require `X-CivicPermit-Role: staff` and `X-CivicPermit-Staff-Key` when `CIVICPERMIT_INTAKE_DB_URL` is configured.
- `GET /api/v1/civicpermit/intake/{intake_id}` retrieves persisted intake records when `CIVICPERMIT_INTAKE_DB_URL` and `CIVICPERMIT_STAFF_API_KEY` are configured and both staff headers are present.
- `POST /api/v1/civicpermit/staff/reviews` creates a staff-only review queue item.
- `GET /api/v1/civicpermit/staff/reviews` lists staff-only review queue items.
- `PATCH /api/v1/civicpermit/staff/reviews/{review_id}` updates staff-only review queue status, assignment, and resolution.
- `GET /api/v1/civicpermit/staff/reviews/summary` returns staff queue counts.
- `POST /api/v1/civicpermit/submittal/outline` returns a review-required submittal outline.
- `POST /api/v1/civicpermit/export` returns a records-ready permit-intake export checklist.

Set `CIVICPERMIT_INTAKE_DB_URL` to enable persistent permit requirement, intake review, and staff review queue records. Persisted staff routes require `CIVICPERMIT_STAFF_API_KEY`, `X-CivicPermit-Role: staff`, and matching `X-CivicPermit-Staff-Key` from a trusted staff workflow. Townlight Permitting uses Townlight Core `staff_key_gate` for timing-safe key comparison. When unset, Townlight Permitting continues to use deterministic in-memory sample data for public applicant guidance.

## License

Code: AGPL-3.0-only, with no additional permission for this candidate; the historical Public Institution Exception is retained under [docs/licensing/history/](docs/licensing/history/). See [LICENSE](LICENSE).
Documentation: CC BY 4.0 ([LICENSE-DOCS](LICENSE-DOCS)).
