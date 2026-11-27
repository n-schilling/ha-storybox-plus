"""Check that every language has the texts English has, with the same placeholders.

Home Assistant's texts: every translations/<language>.json has the keys of
strings.json, and every value keeps the placeholders ({name}) and references
([%key:...%]) of the English one. The page's texts: every
frontend/storybox-plus-texts-<language>.js holds the keys of the English texts
in storybox-plus-common.js, with their placeholders. English and German of the
page live in storybox-plus-common.js itself and are compared the same way.

Usage: python3 .github/scripts/check-translations.py
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2] / "custom_components" / "storybox_plus"
PLACEHOLDER = re.compile(r"\{\w+\}|\[%key:[^%]+%\]")
PREFIX = "export default "


def flatten(data: object, path: str = "") -> dict[str, str]:
    """The strings of a nested JSON object by their dotted path."""
    if isinstance(data, dict):
        out: dict[str, str] = {}
        for key, value in data.items():
            out.update(flatten(value, f"{path}.{key}" if path else key))
        return out
    return {path: data if isinstance(data, str) else json.dumps(data)}


def compare(name: str, english: dict[str, str], other: dict[str, str]) -> list[str]:
    """What a language lacks, has too much or writes with other placeholders."""
    problems = [f"{name}: missing {key}" for key in english.keys() - other.keys()]
    problems += [f"{name}: unknown {key}" for key in other.keys() - english.keys()]
    for key in english.keys() & other.keys():
        want = sorted(PLACEHOLDER.findall(english[key]))
        got = sorted(PLACEHOLDER.findall(other[key]))
        if want != got:
            problems.append(f"{name}: {key} has {got}, English {want}")
    return problems


def page_texts(source: str, language: str) -> dict[str, str]:
    """The texts of one language in storybox-plus-common.js, read without running it."""
    body = source.split("export const TEXTS = {", 1)[1]
    start = body.index(f"\n  {language}: {{\n")
    block = body[start:].split("\n  },\n", 1)[0]
    texts: dict[str, str] = {}
    for key, value in re.findall(r'(\w+): ("(?:[^"\\]|\\.)*")', block):
        texts[key] = json.loads(value)
    return texts


def main() -> int:
    problems: list[str] = []
    english = flatten(json.loads((ROOT / "strings.json").read_text(encoding="utf-8")))
    for path in sorted((ROOT / "translations").glob("*.json")):
        other = flatten(json.loads(path.read_text(encoding="utf-8")))
        problems += compare(f"translations/{path.name}", english, other)

    frontend = ROOT / "frontend"
    source = (frontend / "storybox-plus-common.js").read_text(encoding="utf-8")
    page_en = page_texts(source, "en")
    problems += compare("page de", page_en, page_texts(source, "de"))
    languages = set(json.loads(re.search(r"export const LANGUAGES = (\[[^\]]*\])", source)[1]))
    for language in sorted(languages - {"en", "de"}):
        path = frontend / f"storybox-plus-texts-{language}.js"
        if not path.exists():
            problems.append(f"{path.name}: missing file")
            continue
        text = path.read_text(encoding="utf-8")
        body = text[text.index(PREFIX) + len(PREFIX) :].rstrip().removesuffix(";")
        problems += compare(path.name, page_en, json.loads(body))
        if not (ROOT / "translations" / f"{language}.json").exists():
            problems.append(f"translations/{language}.json: missing file")

    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
