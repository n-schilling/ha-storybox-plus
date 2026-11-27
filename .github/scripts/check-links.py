"""Check that the links between the README and the documents in docs/ lead somewhere.

Every relative link and picture in README.md and docs/*.md must name a file
that exists, and every anchor a heading of the file it points into. Links to
the web are not followed.

Usage: python3 .github/scripts/check-links.py
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\]\(([^)\s]+)\)|(?:src|href)=\"([^\"]+)\"")
HEADING = re.compile(r"^#{1,6} (.+)$")


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading."""
    text = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    """The anchors of a Markdown file; headings inside code blocks are none."""
    found: set[str] = set()
    code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            code = not code
        elif not code and (match := HEADING.match(line)):
            found.add(slug(match[1]))
    return found


def problems(path: Path) -> list[str]:
    """The links of one file that lead nowhere."""
    out: list[str] = []
    code = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            code = not code
            continue
        if code:
            continue
        for match in LINK.finditer(line):
            target = match[1] or match[2]
            if re.match(r"[a-z]+:", target):
                continue
            file, _, anchor = target.partition("#")
            other = (path.parent / file).resolve() if file else path
            where = f"{path.relative_to(ROOT)}:{number}"
            if not other.exists():
                out.append(f"{where}: {target} names no file")
            elif anchor and other.suffix == ".md" and anchor not in anchors(other):
                out.append(f"{where}: {target} names no heading")
    return out


def main() -> int:
    found: list[str] = []
    for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]:
        found += problems(path)
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
