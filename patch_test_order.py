"""Patch: move the module-level FEE_LINK digest helper above its first use."""
from pathlib import Path

P = Path(__file__).resolve().parent / "tests" / "test_pathway.py"
text = P.read_text(encoding="utf-8")

if "def _digest(text: str) -> str:" in text.split("FEE_LINK =")[0]:
    print("already patched")
    raise SystemExit(0)

OLD_HEAD = '''import json
from pathlib import Path'''
NEW_HEAD = '''import hashlib
import json
from pathlib import Path'''
assert OLD_HEAD in text
text = text.replace(OLD_HEAD, NEW_HEAD, 1)

OLD_DEF = '''def _digest(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


'''
assert OLD_DEF in text
text = text.replace(OLD_DEF, "", 1)

OLD_LINK = '''FEE_LINK = {'''
NEW_LINK = '''def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


FEE_LINK = {'''
assert OLD_LINK in text
text = text.replace(OLD_LINK, NEW_LINK, 1)

P.write_text(text, encoding="utf-8")
print("test_pathway.py digest helper relocated")
