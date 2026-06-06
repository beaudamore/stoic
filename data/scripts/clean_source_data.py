#!/usr/bin/env python3
"""
Clean Stoic source-data files by removing:
  - Project Gutenberg headers/footers
  - Google cache wrappers around Internet Classics Archive text
  - HTML tags/entities in cached source dumps
  - Internet Classics Archive boilerplate
  - Repeated blank lines and trailing whitespace

Originals are never modified. Cleaned files are written to:
  data/source-clean/
preserving the original directory structure from data/source-raw/.
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_RAW = DATA_DIR / "source-raw"
SOURCE_CLEAN = DATA_DIR / "source-clean"

TEXT_EXTENSIONS = {".txt", ".md"}

START_RULES = [
    ("the discourses by epictetus", r"^BOOK ONE\s*$", 1),
    ("the enchiridion by epictetus", r"^1\. Some things", 1),
    ("the golden sayings by epictetus", r"^SECTION 1\s*$", 1),
    ("letter to menoeceus", r"^Greeting\.\s*$", 1),
    ("principal doctrines", r"^1\. A happy", 1),
    ("discourses on the first decade", r"^CHAPTER I", 1),
    ("the prince by", r"^CHAPTER I\s*$", 1),
    ("history of florence", r"^CHAPTER I\s*$", 1),
    ("la mandragola", r"^PROLOGO\s*$", 1),
    ("macchiavellis buch", r"^\s*1\. Verschiedene Arten", 1),
    ("machiavelli, volume i", r"^THE FIRST BOOKE\s*$", 2),
    ("ruhtinas", r"^1\. luku\.\s*$", 1),
    ("l. annaeus seneca on benefits", r"^ON BENEFITS\.\s*$", 1),
    ("a translation of octavia", r"^OCTAVIA, A TRAGEDY\.\s*$", 1),
    ("two tragedies of seneca", r"^MEDEA\s*$", 1),
    ("apocolocyntosis", r"^I wish to place", 1),
    ("physical science", r"^THE NATURAL QUESTIONS OF L\. ANNAEUS SENECA", 1),
    ("between heathenism", r"^\s*SELECTIONS FROM THE WRITINGS OF SENECA", 2),
    ("seneca's morals", r"^SENECA OF BENEFITS\.\s*$", 1),
    ("the tragedies of seneca", r"^OEDIPUS\s*$", 1),
    ("octavia praetexta", r"^OCTAVIA\s*$", 1),
    ("minor dialogues", r"^THE FIRST BOOK OF THE DIALOGUES", 1),
]

END_RULES = [
    ("meditations by emperor of rome marcus aurelius", r"^APPENDIX\s*$"),
    ("thoughts of marcus aurelius antoninus", r"^INDEXES\.\s*$"),
    ("la mandragola", r"^\s*INDICE\s*$"),
    ("a translation of octavia", r"^FOOTNOTES:\s*$"),
    ("physical science", r"^NOTES ON SENECA"),
    ("between heathenism", r"^NOTES\.\s*$"),
    ("the tragedies of seneca", r"^COMPARATIVE ANALYSES\s*$"),
    ("octavia praetexta", r"^INDEX NOMINVM\s*$"),
    ("minor dialogues", r"^INDEX\.\s*$"),
]

SECTION_REMOVAL_RULES = {
    "discourses on the first decade": ["PREFACE"],
    "the tragedies of seneca": ["INTRODUCTION"],
}


def strip_gutenberg(text: str) -> str:
    """Strip Project Gutenberg license wrapper when present."""
    def strip_leading_notes(value: str) -> str:
        value = re.sub(
            r"\A\s*E-text prepared by.*?\n\s*\n",
            "",
            value,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return re.sub(
            r"\A\s*Note:\s*Project Gutenberg also has.*?\n\s*\n",
            "",
            value,
            flags=re.IGNORECASE | re.DOTALL,
        )

    text = strip_leading_notes(text)

    start_pattern = re.compile(
        r"^\*{3}\s*START OF (?:THE |THIS )?PROJECT GUTENBERG.*$",
        re.IGNORECASE | re.MULTILINE,
    )
    start_match = start_pattern.search(text)
    if start_match:
        text = text[start_match.end() :]
        text = strip_leading_notes(text)

    end_patterns = [
        re.compile(
            r"^\*{3}\s*END OF (?:THE |THIS )?PROJECT GUTENBERG.*$",
            re.IGNORECASE | re.MULTILINE,
        ),
        re.compile(r"^End of (?:the )?Project Gutenberg(?:'s|’s)?.*$", re.IGNORECASE | re.MULTILINE),
    ]
    end_matches = [match for pattern in end_patterns if (match := pattern.search(text))]
    if end_matches:
        text = text[: min(match.start() for match in end_matches)]

    return text


def strip_google_cache(text: str) -> str:
    """Remove Google cache markup and keep the archived plain-text body."""
    pre_match = re.search(r"<pre[^>]*>", text, flags=re.IGNORECASE)
    if pre_match:
        text = text[pre_match.end() :]

    text = re.sub(r"</pre>.*$", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def strip_internet_classics_boilerplate(text: str) -> str:
    """Remove common MIT/Classics archive source and copyright notes."""
    text = re.sub(
        r"\n-{10,}\n\s*Copyright statement:.*\Z",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    lines = text.splitlines()
    cleaned: list[str] = []
    skip_header = True

    for line in lines:
        stripped = line.strip()
        if skip_header:
            if not stripped:
                continue
            if stripped.startswith("Provided by The Internet Classics Archive"):
                continue
            if stripped.startswith("See bottom for copyright"):
                continue
            if stripped.startswith("http://classics.mit.edu"):
                continue
            skip_header = False

        if re.search(r"The Internet Classics Archive", stripped, re.IGNORECASE):
            continue
        if re.search(r"classics\.mit\.edu", stripped, re.IGNORECASE):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)


def normalize_whitespace(text: str) -> str:
    """Normalize line endings, trim trailing spaces, and collapse long blank runs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def find_nth_match(text: str, pattern: str, occurrence: int) -> re.Match[str] | None:
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE))
    if len(matches) >= occurrence:
        return matches[occurrence - 1]
    return None


def strip_between_heading_and_next_body(text: str, heading: str) -> str:
    body_boundary = (
        r"(?=^\s*(?:CHAPTER\b|BOOK\b|ACT\b|SCENE\b|I\.|1\.|"
        r"MEDEA\s*$|OCTAVIA\s*$|THE DAUGHTERS OF TROY\s*$))"
    )
    pattern = rf"^\s*{re.escape(heading)}\.?\s*$.*?{body_boundary}"
    return re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)


def strip_title_artifacts(text: str, source_path: Path) -> str:
    filename = source_path.name.lower()

    for fragment, pattern, occurrence in START_RULES:
        if fragment in filename:
            start_match = find_nth_match(text, pattern, occurrence)
            if start_match:
                text = text[start_match.start() :]
            break

    for fragment, pattern in END_RULES:
        if fragment in filename:
            end_match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if end_match:
                text = text[: end_match.start()]
            break

    for fragment, headings in SECTION_REMOVAL_RULES.items():
        if fragment in filename:
            for heading in headings:
                text = strip_between_heading_and_next_body(text, heading)
            break

    if "physical science" in filename:
        text = re.sub(r"^\s*PREFACE\s*$\n+", "", text, flags=re.IGNORECASE | re.MULTILINE)

    return text


def strip_marcus_aurelius_artifacts(text: str, source_path: Path) -> str:
    """Remove translator front/back matter from Marcus Aurelius editions."""
    if source_path.parent.name != "Marcus Aurelius":
        return text

    filename = source_path.name.lower()
    if filename.startswith("meditations by emperor of rome marcus aurelius"):
        start_match = re.search(r"^THE FIRST BOOK\s*$", text, flags=re.MULTILINE)
        if start_match:
            text = text[start_match.start() :]

        end_match = re.search(r"^APPENDIX\s*$", text, flags=re.MULTILINE)
        if end_match:
            text = text[: end_match.start()]

    elif filename.startswith("thoughts of marcus aurelius antoninus"):
        thoughts_headings = list(re.finditer(r"^THE THOUGHTS\s*$", text, flags=re.MULTILINE))
        if len(thoughts_headings) >= 2:
            text = text[thoughts_headings[1].start() :]

        end_match = re.search(r"^INDEXES\.\s*$", text, flags=re.MULTILINE)
        if end_match:
            text = text[: end_match.start()]

    return text


def clean_text(text: str, source_path: Path) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_gutenberg(text)
    text = strip_google_cache(text)
    text = strip_internet_classics_boilerplate(text)
    text = strip_title_artifacts(text, source_path)
    text = strip_marcus_aurelius_artifacts(text, source_path)
    return normalize_whitespace(text)


def output_path_for(source_path: Path) -> Path:
    return SOURCE_CLEAN / source_path.relative_to(SOURCE_RAW)


def clean_file(source_path: Path) -> Path:
    raw_text = source_path.read_text(encoding="utf-8", errors="replace")
    cleaned_text = clean_text(raw_text, source_path)
    destination = output_path_for(source_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(cleaned_text, encoding="utf-8")
    return destination


def iter_source_files() -> list[Path]:
    return sorted(
        path
        for path in SOURCE_RAW.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def main() -> None:
    if not SOURCE_RAW.exists():
        raise SystemExit(f"Missing source directory: {SOURCE_RAW}")

    if SOURCE_CLEAN.exists():
        shutil.rmtree(SOURCE_CLEAN)
    SOURCE_CLEAN.mkdir(parents=True, exist_ok=True)

    source_files = iter_source_files()
    for source_path in source_files:
        clean_file(source_path)

    print(f"Cleaned {len(source_files)} files into {SOURCE_CLEAN}")


if __name__ == "__main__":
    main()