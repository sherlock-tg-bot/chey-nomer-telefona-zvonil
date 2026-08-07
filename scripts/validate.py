#!/usr/bin/env python3
"""Small dependency-free content and HTML validation for this repository."""
from pathlib import Path
import html.parser
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["metadata.json", "README.md", "FAQ.md", "SECURITY.md", "index.html", "scripts/validate.py", ".github/workflows/validate.yml"]

class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.h1 = 0; self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "h1": self.h1 += 1
        if tag == "a": self.links.append(dict(attrs).get("href", ""))

def fail(errors, message): errors.append(message)

def main():
    errors = []
    for name in REQUIRED:
        if not (ROOT / name).is_file(): fail(errors, f"missing file: {name}")
    try:
        meta = json.loads((ROOT / "metadata.json").read_text(encoding="utf-8"))
    except Exception as exc:
        fail(errors, f"metadata.json is invalid: {exc}"); meta = {}
    keyword, target = meta.get("keyword", ""), meta.get("target_url", "")
    if not keyword: fail(errors, "metadata.keyword is empty")
    if not target: fail(errors, "metadata.target_url is empty")
    texts = {}
    for name in ("README.md", "FAQ.md", "SECURITY.md", "index.html", ".github/workflows/validate.yml"):
        path = ROOT / name
        if path.exists(): texts[name] = path.read_text(encoding="utf-8")
    if keyword and keyword.lower() not in texts.get("README.md", "").lower(): fail(errors, "keyword missing from README")
    if not re.search(r"^#\s+.*" + re.escape(keyword), texts.get("README.md", ""), re.I | re.M): fail(errors, "README H1 does not contain exact keyword")
    for name in ("README.md", "index.html"):
        if target and target not in texts.get(name, ""): fail(errors, f"target_url missing from {name}")
    if target and target not in texts.get("FAQ.md", ""): fail(errors, "target_url missing from FAQ")
    if len(re.findall(r"^#{2,3}\s+", texts.get("FAQ.md", ""), re.M)) not in range(4, 8): fail(errors, "FAQ must contain 4-7 questions")
    for forbidden in ("https://sherlockbot.is", "https://glazboga.is", "https://t.me", "https://telegram.me"):
        for name, content in texts.items():
            if forbidden in content: fail(errors, f"forbidden URL in {name}: {forbidden}")
    for bad in ("официальн", "гарантированн", "анонимност", "в реальном времени", "за пять секунд", "доступ к закрыт\w* баз"):
        if re.search(bad, texts.get("README.md", "") + texts.get("FAQ.md", "") + texts.get("SECURITY.md", ""), re.I):
            # Official is allowed only for checking an organization's primary source, not the product.
            if bad == "официальн" and re.search(r"официальн\w+\s+(сайт|канал|первоисточник|номер|источник|помощь)", texts["README.md"], re.I): continue
            fail(errors, f"unsafe marketing claim/pattern: {bad}")
    parser = Parser()
    try: parser.feed(texts.get("index.html", ""))
    except Exception as exc: fail(errors, f"HTML parse error: {exc}")
    if parser.h1 != 1: fail(errors, "index.html must have exactly one H1")
    if keyword and keyword.lower() not in texts.get("index.html", "").lower(): fail(errors, "keyword missing from index.html")
    workflow = texts.get(".github/workflows/validate.yml", "")
    if "name: Content validation" not in workflow or "python3 scripts/validate.py" not in workflow: fail(errors, "workflow is incomplete")
    if errors:
        print("Validation failed:"); print("\n".join(f"- {e}" for e in errors)); return 1
    print("Validation passed: required files, keyword, CTA, FAQ, safety rules, and HTML are valid."); return 0

if __name__ == "__main__": sys.exit(main())
