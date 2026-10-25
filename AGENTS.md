<a id="civicpermit-agent-contract"></a>

# Townlight Permitting Agent Contract

## Source Of Truth

- Upstream suite spec: `townlight/townlight/docs/CivicSuiteUnifiedSpec.md`, especially the Townlight Permitting catalog entry and suite-wide non-negotiables.
- Suite ADRs: `townlight/townlight/docs/architecture/`.
- Townlight Permitting supports permit pre-application and development-review intake workflows. It does not replace permit technicians, planners, building officials, inspectors, attorneys, boards, commissions, councils, or permitting systems of record.

## Non-Negotiables

- Townlight Permitting never issues permits, calculates official fees, decides completeness, schedules inspections, or makes zoning, land-use, environmental, legal, entitlement, or elected-body determinations.
- Every material checklist must identify the sample intake source used.
- Submittal outlines must be marked review-required.
- Public-facing warnings must be actionable and explain the fix path.
- Townlight Permitting depends on Townlight Core; Townlight Core must never depend on Townlight Permitting.
- Townlight Permitting may reference CivicCode/CivicZone concepts only through released contracts or deterministic sample data in v0.1.0.
- Code is AGPL-3.0-only, with the TownLight Public Institution Exception for qualifying deployments. Docs are CC BY 4.0.

## Placeholder Package Warning

Do not import from Townlight Core placeholder packages until Townlight Core ships real implementations for them: `catalog`, `connectors`, `exemptions`, `ingest`, `notifications`, `onboarding`, `scaffold`, `search`, `verification`.

## Milestone Rule

Work one milestone at a time. When a milestone is done, report what changed, audit it once, fix findings once, re-audit once, then continue immediately unless there is a true blocker.

The connected development workflow uses implemented Core 1.2.1 staff authentication and persisted audit hash contracts, as in the accepted Planning runtime. Legacy placeholder warnings remain for unimplemented packages.
