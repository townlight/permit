# Connected Permitting staff workflow

The 0.3.0+dev.1 package described here is included in the signed 1.6.0-beta.1 composition. Package version and desktop release identity differ. Use the [current manual](../USER-MANUAL.md) for publication/installation status; the staff workflow and limits below remain applicable.


This 0.3.0+dev.1 source adds intake support; it does not issue permits,
determine official completeness, calculate fees, schedule inspections or write to
a permitting system of record. Historical 0.2.2 release evidence remains intact.

The installed Townlight candidate owns authentication, localhost transport and
explicit migration. `civicpermit` owns the additive `civicpermit_0001` schema,
requirement/case history, material assessments, review attribution and packet
bytes. Request handlers do not create schema or seed sample municipal authority.
Core is pinned to the implemented 1.2.1 audit/auth contracts.

1. In the requirement library, select a JSON bundle containing requirement ID,
   title, jurisdiction, project type, source reference/date/effective date,
   municipal or fictional dataset kind, original filename/base64/SHA256, a list
   of material IDs/descriptions/citations and a change note. Inspect it and
   explicitly import. Originals and earlier versions are retained.
2. Start an intake case with a selected requirement revision. Enter project,
   location, applicant contact and assigned staff. Mark each material as not
   reviewed, provided, missing or unclear, with staff notes as needed. These
   are staff assessments, never an automatic completeness determination.
3. Search actual permitted Code or Zoning documents and select exact source
   versions. The runtime supplies trusted providers; callers cannot supply URLs.
   No sample data or stale cached text is substituted when evidence is unavailable.
4. Save and reopen. Revision conflicts require explicit reconciliation. A changed
   workpaper becomes a draft; record a new review with notes. The reviewer comes
   from the authenticated native account, not an editable name or role header.
5. Create an exact staff packet, or write/review a separate public summary and
   create a Records copy. The Records copy excludes contact, location, proposal,
   material notes and private staff notes. Its selected Code/Zoning evidence is
   already permission-checked public material. Inspect the packet before use.
6. Save the hash-verified packet, or explicitly attach the reviewed copy to an
   existing Records request. Records retains its own review/release approvals.
   Source permissions and hashes are rechecked during later Records release work;
   attaching does not grant permanent permission or publish anything.

Drafts require an explicit Save before closing. No optional AI/model download is
required. The candidate has no public applicant portal, live permit-system
writeback, automatic approvals or official determinations. Installed acceptance
is recorded separately by the umbrella project; source checks alone are not an
installed acceptance claim.
