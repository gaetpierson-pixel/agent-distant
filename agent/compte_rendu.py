"""Compte-rendu de visite en Word, à partir de ce que Gaëtan a dicté."""

import re
import unicodedata
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def file_name(date: str, affaire: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", affaire.strip(), flags=re.UNICODE).strip("-")[:60] or "visite"
    return f"CR_{date}_{slug}.docx"


def build(dest: Path, affaire: str, date: str, lieu: str = "", participants: str = "", objet: str = "",
          constats: list[str] | None = None, actions: list[dict] | None = None, remarques: str = "",
          photos: list[dict] | None = None, videos: list[str] | None = None) -> Path:
    """photos : [{"chemin": ..., "legende": ...}], placées à la fin, une par ligne, avec leur légende."""
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading(f"Compte-rendu de visite – {affaire}", level=1)

    infos = [("Date", date), ("Lieu", lieu), ("Participants", participants), ("Objet", objet)]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for label, value in infos:
        if value:
            row = table.add_row().cells
            row[0].text, row[1].text = label, value

    if constats:
        doc.add_heading("Constats", level=2)
        for c in constats:
            doc.add_paragraph(c, style="List Bullet")

    if actions:
        doc.add_heading("Actions", level=2)
        grid = doc.add_table(rows=1, cols=3)
        grid.style = "Table Grid"
        for cell, title in zip(grid.rows[0].cells, ("Action", "Qui", "Échéance")):
            cell.text = title
            cell.paragraphs[0].runs[0].bold = True
        for a in actions:
            row = grid.add_row().cells
            # Une case non dictée reste vide : on n'invente ni responsable ni date.
            row[0].text, row[1].text, row[2].text = a.get("action", ""), a.get("qui", ""), a.get("echeance", "")

    if remarques:
        doc.add_heading("Remarques", level=2)
        doc.add_paragraph(remarques)

    if photos:
        doc.add_heading("Photos", level=2)
        for n, ph in enumerate(photos, 1):
            doc.add_picture(str(ph["chemin"]), width=Cm(15))
            caption = doc.add_paragraph(f"Photo {n}" + (f" – {ph['legende']}" if ph.get("legende") else ""))
            caption.runs[0].italic = True

    if videos:
        doc.add_heading("Vidéos", level=2)
        doc.add_paragraph("Fichiers rangés à côté de ce compte-rendu :")
        for v in videos:
            doc.add_paragraph(v, style="List Bullet")

    dest.parent.mkdir(parents=True, exist_ok=True)
    doc.save(dest)
    return dest


def pending_media(medias: Path, since: float, day: str) -> tuple[list[Path], list[Path]]:
    """Photos et vidéos reçues ce jour-là depuis le dernier compte-rendu, dans l'ordre d'arrivée."""
    if not medias.is_dir():
        return [], []
    files = sorted(f for f in medias.iterdir() if f.name.startswith(day) and f.stat().st_mtime > since)
    return [f for f in files if "_photo." in f.name], [f for f in files if "_video." in f.name and f.is_file()]


def free_path(path: Path) -> Path:
    """Jamais d'écrasement : CR.docx, puis CR_2.docx, CR_3.docx…"""
    n, candidate = 2, path
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
        n += 1
    return candidate


def _words(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()
    return re.findall(r"[A-Z0-9]+", plain)


class SeveralFolders(Exception):
    def __init__(self, folders: list[Path]):
        super().__init__(" ; ".join(f.name for f in folders))
        self.folders = folders


def chantier_folder(root: Path, year: str, chantier: str, client: str = "") -> Path:
    """Dossier du chantier dans root/année : celui dont le nom contient tous les mots dictés (chantier et client).
    Sinon, il en crée un sur le modèle « 2026-XXX-X - CLIENT - NOM » ; Gaëtan le renumérote ensuite."""
    wanted = _words(f"{client} {chantier}")
    year_dir = root / year
    matches = []
    if year_dir.is_dir():
        matches = [d for d in year_dir.iterdir() if d.is_dir() and all(w in _words(d.name) for w in wanted)]
    if len(matches) > 1:
        raise SeveralFolders(matches)
    if matches:
        return matches[0]
    name = " ".join(_words(chantier)) or "NOM"
    folder = year_dir / f"{year}-XXX-X - {' '.join(_words(client)) or 'CLIENT'} - {name}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
