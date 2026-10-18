"""Compte-rendu de visite en Word, à partir de ce que Gaëtan a dicté."""

import re
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt


def file_name(date: str, affaire: str) -> str:
    slug = re.sub(r"[^\w-]+", "-", affaire.strip(), flags=re.UNICODE).strip("-")[:60] or "visite"
    return f"CR_{date}_{slug}.docx"


def build(dest: Path, affaire: str, date: str, lieu: str = "", participants: str = "", objet: str = "",
          constats: list[str] | None = None, actions: list[dict] | None = None, remarques: str = "",
          photos: list[dict] | None = None) -> Path:
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

    dest.parent.mkdir(parents=True, exist_ok=True)
    doc.save(dest)
    return dest
