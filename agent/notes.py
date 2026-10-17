"""Carnet de notes : une note par jour, dans un fichier Markdown."""

from datetime import datetime
from pathlib import Path


def add_note(notes_dir: Path, text: str, source: str, now: datetime | None = None) -> Path:
    now = now or datetime.now()
    path = notes_dir / f"{now:%Y-%m-%d}.md"
    if not path.exists():
        path.write_text(f"# Notes du {now:%d/%m/%Y}\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now:%H:%M} ({source})\n\n{text.strip()}\n")
    return path
