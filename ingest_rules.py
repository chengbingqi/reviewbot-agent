import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from rag_db import content_hash, ingest_knowledge, init_rag_db


@dataclass
class RuleDocument:
    content: str
    source: str
    rule_id: str
    title: str


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip()).strip("-")
    return slug[:80] or "rule"


def parse_rule_file(path: Path) -> list[RuleDocument]:
    text = path.read_text(encoding="utf-8")
    sections: list[RuleDocument] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        if current_title is None:
            return
        title = current_title or path.stem
        content = "\n".join(current_lines).strip()
        if not content:
            content = title
        sections.append(
            RuleDocument(
                content=content,
                source=str(path.as_posix()),
                rule_id=f"{path.stem.upper()}-{_slugify(title)}",
                title=title,
            )
        )

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            current_title = line.removeprefix("## ").strip()
            current_lines = [current_title]
        else:
            current_lines.append(line)
    flush()

    if not sections and text.strip():
        title = path.stem.replace("_", " ").title()
        sections.append(
            RuleDocument(
                content=text.strip(),
                source=str(path.as_posix()),
                rule_id=f"{path.stem.upper()}-{content_hash(text)[:8]}",
                title=title,
            )
        )
    return sections


def iter_rule_files(file: str | None, directory: str | None) -> list[Path]:
    paths: list[Path] = []
    if file:
        paths.append(Path(file))
    if directory:
        paths.extend(sorted(Path(directory).rglob("*.md")))
    return [path for path in paths if path.is_file()]


def ingest_rules(file: str | None = None, directory: str | None = None) -> tuple[int, int]:
    db = init_rag_db()
    inserted = 0
    skipped = 0
    for path in iter_rule_files(file, directory):
        for rule in parse_rule_file(path):
            digest = content_hash(rule.content)
            exists = db.execute(
                "SELECT id FROM code_chunks WHERE content_hash = ? LIMIT 1", (digest,)
            ).fetchone()
            if exists:
                skipped += 1
                continue
            ingest_knowledge(
                db,
                rule.content,
                source=rule.source,
                rule_id=rule.rule_id,
                title=rule.title,
                skip_duplicates=True,
            )
            inserted += 1
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Markdown rules into sqlite-vec RAG database.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Markdown rule file to import.")
    group.add_argument("--dir", help="Directory containing Markdown rule files.")
    args = parser.parse_args()

    inserted, skipped = ingest_rules(file=args.file, directory=args.dir)
    print(f"Rules imported. inserted={inserted} skipped={skipped}")


if __name__ == "__main__":
    main()
