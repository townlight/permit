"""Patch: run the two async provider tests through asyncio.run (no async plugin)."""
from pathlib import Path

P = Path(__file__).resolve().parent / "tests" / "test_pathway.py"
text = P.read_text(encoding="utf-8")

if "asyncio.run(" in text:
    print("already patched")
    raise SystemExit(0)

OLD_HEAD = "import hashlib\nimport json\nfrom pathlib import Path"
NEW_HEAD = "import asyncio\nimport hashlib\nimport json\nfrom pathlib import Path"
assert OLD_HEAD in text
text = text.replace(OLD_HEAD, NEW_HEAD, 1)

OLD_1 = '''async def test_stub_provider_execution_is_labelled_and_staff_review_kept(providers):
    stub = _StubProvider()
    result = await explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=stub, model="stub-model")'''
NEW_1 = '''def test_stub_provider_execution_is_labelled_and_staff_review_kept(providers):
    stub = _StubProvider()
    result = asyncio.run(explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=stub, model="stub-model"))'''
assert OLD_1 in text
text = text.replace(OLD_1, NEW_1, 1)

OLD_2 = '''async def test_provider_failure_and_empty_output_are_reported(providers):
    failing = _StubProvider(raises=RuntimeError("daemon down"))
    result = await explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=failing)'''
NEW_2 = '''def test_provider_failure_and_empty_output_are_reported(providers):
    failing = _StubProvider(raises=RuntimeError("daemon down"))
    result = asyncio.run(explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=failing))'''
assert OLD_2 in text
text = text.replace(OLD_2, NEW_2, 1)

OLD_3 = '''    empty = _StubProvider(text="   ")
    empty_result = await explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=empty)'''
NEW_3 = '''    empty = _StubProvider(text="   ")
    empty_result = asyncio.run(explain_pathway_with_assistant(
        project_type="adu", source_providers=providers, provider=empty))'''
assert OLD_3 in text
text = text.replace(OLD_3, NEW_3, 1)

P.write_text(text, encoding="utf-8")
print("async tests converted to asyncio.run")
