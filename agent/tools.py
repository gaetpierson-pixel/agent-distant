"""Outils que l'agent peut utiliser en plus de ses outils de base (fichiers, web)."""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from .config import Config
from .notes import add_note


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def build_tools(cfg: Config, gmail=None, calendar=None):
    """Construit le serveur d'outils. gmail/calendar peuvent être absents (tests, mode local)."""

    @tool("noter", "Enregistre une note de Gaëtan dans son carnet du jour.", {"texte": str, "source": str})
    async def noter(args):
        path = add_note(cfg.notes_dir, args["texte"], args.get("source", "inconnue"))
        return _text(f"Note enregistrée dans {path.name}.")

    @tool(
        "preparer_mail",
        "Prépare un mail pour un tiers sous forme de BROUILLON (jamais envoyé). Gaëtan le relira.",
        {"destinataire": str, "objet": str, "texte": str},
    )
    async def preparer_mail(args):
        if gmail is None:
            return _text("Gmail n'est pas connecté : brouillon non créé.")
        draft_id = gmail.create_draft(args["destinataire"], args["objet"], args["texte"])
        return _text(f"Brouillon créé (id {draft_id}).")

    @tool(
        "agenda_lister",
        "Liste les événements de l'agenda entre deux dates ISO 8601 (ex. 2026-10-20T00:00:00+02:00).",
        {"debut": str, "fin": str},
    )
    async def agenda_lister(args):
        if calendar is None:
            return _text("L'agenda n'est pas connecté.")
        return _text(calendar.list_events(args["debut"], args["fin"]))

    @tool(
        "agenda_ajouter",
        "Ajoute un événement à l'agenda. Dates au format ISO 8601 avec fuseau.",
        {"titre": str, "debut": str, "fin": str, "description": str},
    )
    async def agenda_ajouter(args):
        if calendar is None:
            return _text("L'agenda n'est pas connecté.")
        return _text(calendar.add_event(args["titre"], args["debut"], args["fin"], args.get("description", "")))

    tools = [noter, preparer_mail, agenda_lister, agenda_ajouter]
    server = create_sdk_mcp_server(name="perso", tools=tools)
    names = [f"mcp__perso__{t.name}" for t in tools]
    return server, names
