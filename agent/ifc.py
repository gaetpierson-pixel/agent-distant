"""Maquettes IFC (format ouvert, exportable depuis Revit) : inventaire et propriétés, lus sur le PC avec IfcOpenShell."""

from collections import Counter
from pathlib import Path

MAX_CHARS = 60_000
MAX_ELEMENTS = 300
# Lieux (projet, site, bâtiment, niveau) : ils structurent la maquette mais ne sont pas des équipements.
SPATIAL = ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace")


def _describe(el) -> str:
    import ifcopenshell.util.element as ue

    container = ue.get_container(el)
    lines = [f"- {el.is_a()} « {el.Name or 'sans nom'} »" + (f" ({el.ObjectType})" if getattr(el, "ObjectType", None) else "")
             + (f", niveau {container.Name}" if container is not None and container.Name else "")]
    for pset, props in ue.get_psets(el).items():
        values = ", ".join(f"{k} = {v}" for k, v in props.items() if k != "id" and v not in (None, ""))
        if values:
            lines.append(f"    {pset} : {values}")
    return "\n".join(lines)


def summarize(path: Path, filtre: str = "") -> str:
    """Sans filtre : inventaire par type. Avec filtre (type IFC ou mot du nom) : détail des éléments trouvés."""
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    products = [p for p in model.by_type("IfcProduct") if not p.is_a() in SPATIAL]
    project = (model.by_type("IfcProject") or [None])[0]
    out = [f"Maquette {path.name} (schéma {model.schema}), projet « {getattr(project, 'Name', None) or '?'} »."]
    storeys = [s.Name or "sans nom" for s in model.by_type("IfcBuildingStorey")]
    if storeys:
        out.append("Niveaux : " + ", ".join(storeys))

    if not filtre:
        out.append(f"{len(products)} éléments. Nombre par type :")
        out += [f"- {t} : {n}" for t, n in Counter(p.is_a() for p in products).most_common()]
        out.append("Pour le détail, relance avec un filtre (un type comme IfcValve, ou un mot du nom comme « papillon »).")
        return "\n".join(out)

    needle = filtre.strip().lower()
    found = [p for p in products if needle in p.is_a().lower() or needle in (p.Name or "").lower()
             or needle in (getattr(p, "ObjectType", None) or "").lower()]
    out.append(f"{len(found)} élément(s) pour « {filtre} »" + (f", {MAX_ELEMENTS} premiers :" if len(found) > MAX_ELEMENTS else " :"))
    out += [_describe(p) for p in found[:MAX_ELEMENTS]]
    text = "\n".join(out)
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n[… coupé : affine le filtre]"
