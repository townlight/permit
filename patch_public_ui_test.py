"""Patch: update the public-UI test to the new interactive-but-honest contract.

The old test asserted the public page had no interactive controls at all, because
the page was a static sample. That static sample was the recorded beta gap
(outputs/Townlight-Minimum-Beta-Scope-Audit-2026-10-27.md §2.2: "The public page
is a static sample"). The page now offers a real project-description form that
calls the cited pathway API, so the test asserts the new contract while keeping
every honesty assertion the old test made about the boundary text.

Idempotent.
"""
from pathlib import Path

P = Path(__file__).resolve().parent / "tests" / "test_permit_foundation.py"
text = P.read_text(encoding="utf-8")

OLD = '''    assert "v0.2.2 permit pre-application + staff review queues" in text
    assert "<button" not in text
    assert "<textarea" not in text
    assert "Static sample proposal" in text
    assert "does not approve permits" in text
    assert "permitting system of record" in text'''

NEW = '''    assert "v0.2.2 permit pre-application + staff review queues" in text
    # The page now submits a real project description to the cited pathway API;
    # it no longer claims to be only a static sample.
    assert 'id="pathway-form"' in text
    assert "/api/v1/civicpermit/pathway/explain" in text
    assert "Describe your project" in text
    assert "Static sample" in text  # the original ADU sample is kept, labelled
    assert "likely review steps" in text.lower()
    assert "Unavailable, not assumed" in text
    assert "does not approve permits" in text
    assert "permitting system of record" in text
    assert "calculate official fees" in text'''

if NEW in text:
    print("already patched")
    raise SystemExit(0)

assert OLD in text, "expected public-UI assertions not found"
P.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print("test_permit_foundation.py public-UI test updated")
