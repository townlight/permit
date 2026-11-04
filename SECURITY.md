Townlight Beta 1 source component: **0.3.0+dev.1**. Use the current suite manual and signed installer for beta installation. Earlier release-history text below retains its original scope.

# Security

Current source package: `townlight-permitting` 0.3.0+dev.2. Windows MSI 1.7.0.1 is [published](https://github.com/townlight/townlight/releases/tag/townlight-beta-1-windows-1.7.0.1). Its [acceptance summary](https://github.com/townlight/townlight/releases/download/townlight-beta-1-windows-1.7.0.1/ACCEPTANCE-Windows-1.7.0.1.md) identifies the tested workflows and limits; standalone source checks remain separate.

Townlight Permitting Current version: 0.2.3. This is a narrow truth-repair release with no functional upgrade. The previous v1.0.0 release was published in error and does not prove public-use readiness. It supports permit pre-application and intake-readiness scaffold workflows, but it is not a permitting system of record.

When `TOWNLIGHT_PERMITTING_INTAKE_DB_URL` is configured, persisted intake, staff review queue, and staff summary routes require `TOWNLIGHT_PERMITTING_STAFF_API_KEY`, `X-Townlight-Permitting-Role: staff`, and a matching `X-Townlight-Permitting-Staff-Key` from a trusted staff workflow. Townlight Permitting uses Townlight Core `staff_key_gate` for timing-safe key comparison. This local API-key gate is a release safeguard, not a replacement for production identity, tenant scoping, and audit logging.

Report suspected vulnerabilities privately to the project maintainer. Do not open public issues containing exploit details, secrets, or sensitive municipal data.
