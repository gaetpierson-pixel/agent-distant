"""Outils que l'agent peut utiliser en plus de ses outils de base (fichiers, web)."""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from pathlib import Path

from .config import Config, is_inside
from .documents import extract
from .routine import fire
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

    @tool(
        "lire_document",
        "Lit le texte d'un fichier Excel (.xlsx), Word (.docx) ou PDF. Chemin complet du fichier.",
        {"chemin": str},
    )
    async def lire_document(args):
        path = Path(args["chemin"]).expanduser()
        allowed = [cfg.projects_dir, cfg.notes_dir, *cfg.read_only_dirs]
        if not is_inside(path, allowed):
            return _text("Ce fichier est hors des dossiers autorisés.")
        if not path.is_file():
            return _text("Fichier introuvable.")
        try:
            return _text(extract(path))
        except Exception as e:  # noqa: BLE001 - fichier abîmé, protégé par mot de passe…
            return _text(f"Impossible de lire ce fichier : {e}")

    @tool(
        "lancer_tache_claude",
        "Lance une tâche longue chez Claude, dans le cloud (sans accès aux fichiers du PC). "
        "Donne une consigne complète et autonome. Renvoie le lien de la session à transmettre à Gaëtan.",
        {"consigne": str},
    )
    async def lancer_tache_claude(args):
        if not (cfg.routine_url and cfg.routine_token):
            return _text("Les tâches Claude ne sont pas configurées (ROUTINE_URL et ROUTINE_TOKEN).")
        try:
            return _text(f"Tâche lancée. Lien de la session : {fire(cfg.routine_url, cfg.routine_token, args['consigne'])}")
        except Exception as e:  # noqa: BLE001 - réseau, jeton refusé, limite horaire…
            return _text(f"Échec du lancement : {e}")

    tools = [noter, preparer_mail, agenda_lister, agenda_ajouter, lire_document, lancer_tache_claude]
    server = create_sdk_mcp_server(name="perso", tools=tools)
    names = [f"mcp__perso__{t.name}" for t in tools]
    return server, names
