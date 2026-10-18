"""Outils que l'agent peut utiliser en plus de ses outils de base (fichiers, web)."""

import asyncio
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from pathlib import Path

from .config import Config, is_inside
from .documents import extract
from .capture import SheetNotFound, allowed_url, capture, zoom
from .ifc import summarize as ifc_summary
import shutil
import time

from .compte_rendu import SeveralFolders, build, chantier_folder, file_name, free_path, pending_media
from .routine import fire
from .notes import add_note


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def build_tools(cfg: Config, gmail=None, calendar=None, outbox: list | None = None):
    """Construit le serveur d'outils. gmail/calendar peuvent être absents (tests, mode local).
    `outbox` reçoit les fichiers produits (comptes-rendus Word) que le canal renvoie à Gaëtan."""

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

    @tool(
        "compte_rendu_visite",
        "Rédige un compte-rendu de visite en Word à partir de ce que Gaëtan a dicté, et le lui envoie. "
        "date au format AAAA-MM-JJ. chantier et client (seulement s'il les a dits) servent à trouver ou créer le dossier du chantier. "
        "Les photos et vidéos reçues ce jour-là depuis le dernier compte-rendu sont jointes d'office ; "
        "photos sert seulement à leur donner une légende tirée de ce qu'il a dit. Cet outil INSÈRE lui-même les photos dans le Word. "
        "N'invente rien : un champ non dicté reste vide.",
        {
            "type": "object",
            "properties": {
                "affaire": {"type": "string"},
                "chantier": {"type": "string"},
                "client": {"type": "string"},
                "date": {"type": "string"},
                "lieu": {"type": "string"},
                "participants": {"type": "string"},
                "objet": {"type": "string"},
                "constats": {"type": "array", "items": {"type": "string"}},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"action": {"type": "string"}, "qui": {"type": "string"}, "echeance": {"type": "string"}},
                        "required": ["action"],
                    },
                },
                "remarques": {"type": "string"},
                "photos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"chemin": {"type": "string"}, "legende": {"type": "string"}},
                        "required": ["chemin"],
                    },
                },
            },
            "required": ["affaire", "date"],
        },
    )
    async def compte_rendu_visite(args):
        allowed = [cfg.projects_dir, cfg.notes_dir, *cfg.read_only_dirs]
        captions = {}
        for ph in args.get("photos") or []:
            path = Path(ph["chemin"]).expanduser()
            if not is_inside(path, allowed) or not path.is_file():
                return _text(f"Photo introuvable ou hors des dossiers autorisés : {path}")
            captions[path.resolve()] = ph.get("legende", "")
        last = cfg.state_dir / "dernier_cr.txt"
        since = float(last.read_text()) if last.exists() else 0.0
        new_photos, videos = pending_media(cfg.notes_dir / "medias", since, args["date"])
        # Photos citées par le modèle d'abord (dans son ordre), puis celles du jour qu'il n'a pas citées.
        ordered = list(captions) + [p.resolve() for p in new_photos if p.resolve() not in captions]
        photos = [{"chemin": p, "legende": captions.get(p, "")} for p in ordered]

        folder = cfg.projects_dir / "comptes-rendus"
        if cfg.cr_root:
            try:
                # Seul endroit où l'agent écrit dans les dossiers partagés : ajout de fichiers neufs uniquement.
                chantier = chantier_folder(cfg.cr_root, args["date"][:4], args.get("chantier") or args["affaire"], args.get("client", ""))
            except SeveralFolders as e:
                return _text(f"Plusieurs dossiers de chantier correspondent : {e}. Demande à Gaëtan lequel, puis recommence avec le client ou un nom plus précis.")
            folder = chantier / cfg.cr_subfolder
        dest = free_path(folder / file_name(args["date"], args["affaire"]))
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            for v in videos:
                shutil.copy2(v, free_path(dest.parent / v.name))
            build(
                dest,
                affaire=args["affaire"],
                date=args["date"],
                lieu=args.get("lieu", ""),
                participants=args.get("participants", ""),
                objet=args.get("objet", ""),
                constats=args.get("constats") or [],
                actions=args.get("actions") or [],
                remarques=args.get("remarques", ""),
                photos=photos,
                videos=[v.name for v in videos],
            )
        except Exception as e:  # noqa: BLE001
            return _text(f"Compte-rendu non créé : {e}")
        last.write_text(str(time.time()))
        if outbox is not None:
            outbox.append(dest)
        return _text(
            f"Compte-rendu enregistré ici : {dest} ({len(photos)} photo(s), {len(videos)} vidéo(s)). "
            "Il sera envoyé à Gaëtan avec ta réponse : dis-lui où il est rangé, et si un dossier de chantier a été créé."
        )

    @tool(
        "lire_maquette_ifc",
        "Lit une maquette IFC (chemin complet). Sans filtre : inventaire par type. Avec filtre (type IFC comme IfcValve, "
        "ou mot du nom comme « papillon ») : liste des éléments avec leurs propriétés (DN, matériau…).",
        {"type": "object", "properties": {"chemin": {"type": "string"}, "filtre": {"type": "string"}}, "required": ["chemin"]},
    )
    async def lire_maquette_ifc(args):
        path = Path(args["chemin"]).expanduser()
        if not is_inside(path, [cfg.projects_dir, cfg.notes_dir, *cfg.read_only_dirs]):
            return _text("Cette maquette est hors des dossiers autorisés.")
        if not path.is_file():
            return _text("Maquette introuvable.")
        try:
            return _text(ifc_summary(path, args.get("filtre", "")))
        except Exception as e:  # noqa: BLE001 - fichier abîmé ou schéma inconnu
            return _text(f"Impossible de lire cette maquette : {e}")

    @tool(
        "capturer_maquette",
        "Fait une image de la vue d'une maquette 3D et l'envoie à Gaëtan : lien Autodesk Viewer (https://viewer.autodesk.com/…) "
        "ou maquette HTML (chemin complet). feuille (facultatif) : numéro ou nom d'une feuille du lien Autodesk "
        "(« AO-105 », « coupe A-B », « plan radier »), capturée en haute définition. Regarde ensuite l'image avec Read.",
        {
            "type": "object",
            "properties": {"adresse": {"type": "string"}, "feuille": {"type": "string"}},
            "required": ["adresse"],
        },
    )
    async def capturer_maquette(args):
        target = args["adresse"].strip()
        if target.startswith("http"):
            if not allowed_url(target):
                return _text("Je n'ouvre que les liens Autodesk Viewer.")
        else:
            path = Path(target).expanduser()
            if path.suffix.lower() not in (".html", ".htm") or not is_inside(path, [cfg.projects_dir, cfg.notes_dir, *cfg.read_only_dirs]):
                return _text("Je ne capture que les maquettes HTML des dossiers autorisés.")
            if not path.is_file():
                return _text("Maquette introuvable.")
        dest = free_path(cfg.notes_dir / "medias" / f"{time.strftime('%Y-%m-%d_%H%M%S')}_capture.png")
        try:
            await capture(target, dest, feuille=args.get("feuille", ""))
        except SheetNotFound as e:
            return _text(f"{e}. Demande à Gaëtan laquelle il veut.")
        except Exception as e:  # noqa: BLE001 - navigateur absent, lien expiré, délai dépassé…
            return _text(f"Capture impossible : {e}")
        if outbox is not None:
            outbox.append(dest)
        return _text(f"Capture enregistrée ici : {dest}. Elle sera envoyée à Gaëtan. Regarde-la avec Read avant de la décrire.")

    @tool(
        "zoomer_image",
        "Agrandit une zone d'une capture ou d'une photo pour lire les cotes, DN et niveaux, et l'envoie à Gaëtan. "
        "zone = « gauche,haut,droite,bas » en % de l'image (ex. « 50,40,100,100 » pour le quart bas droit). "
        "Regarde d'abord l'image entière avec Read pour situer la zone, puis le zoom avec Read.",
        {"type": "object", "properties": {"chemin": {"type": "string"}, "zone": {"type": "string"}}, "required": ["chemin", "zone"]},
    )
    async def zoomer_image(args):
        src = Path(args["chemin"]).expanduser()
        if not is_inside(src, [cfg.projects_dir, cfg.notes_dir, *cfg.read_only_dirs]) or not src.is_file():
            return _text("Image introuvable ou hors des dossiers autorisés.")
        dest = free_path(cfg.notes_dir / "medias" / f"{src.stem}_zoom.png")
        try:
            zoom(src, dest, args["zone"])
        except Exception as e:  # noqa: BLE001
            return _text(f"Zoom impossible : {e}")
        if outbox is not None:
            outbox.append(dest)
        return _text(f"Zoom enregistré ici : {dest}. Il sera envoyé à Gaëtan. Lis-le avec Read ; ne donne une cote que si elle est lisible.")

    def _gmail():
        from .gmail_search import GmailSearch

        return GmailSearch(cfg.gmail_perso, cfg.gmail_perso_password) if cfg.gmail_perso and cfg.gmail_perso_password else None

    @tool(
        "chercher_mails",
        "Cherche dans les mails de Gaëtan, en lecture seule : sa boîte pro (Outlook du PC) et son Gmail perso. "
        "mots : mots à trouver ; expediteur (facultatif) ; jours : période (180 par défaut) ; boite : pro, perso ou vide pour les deux.",
        {
            "type": "object",
            "properties": {
                "mots": {"type": "string"},
                "expediteur": {"type": "string"},
                "jours": {"type": "integer"},
                "boite": {"type": "string", "enum": ["", "pro", "perso"]},
            },
            "required": ["mots"],
        },
    )
    async def chercher_mails(args):
        from .outlook import NotAllowed, search

        words, sender, days, box = args["mots"], args.get("expediteur", ""), args.get("jours", 180), args.get("boite", "")
        parts = []
        if box in ("", "pro"):
            try:
                parts.append("Boîte pro (Outlook) :\n" + await asyncio.to_thread(search, words, sender, days, cfg.outlook_accounts))
            except NotAllowed as e:
                parts.append(f"Boîte pro : recherche refusée ({e}).")
            except Exception as e:  # noqa: BLE001 - Outlook fermé, pas sous Windows…
                parts.append(f"Boîte pro : recherche impossible ({e}). Outlook doit être ouvert sur le PC.")
        if box in ("", "perso"):
            gmail = _gmail()
            if gmail is None:
                parts.append("Gmail perso : pas encore branché.")
            else:
                try:
                    parts.append("Gmail perso :\n" + await asyncio.to_thread(gmail.search, words, sender, days))
                except Exception as e:  # noqa: BLE001
                    parts.append(f"Gmail perso : recherche impossible ({e}).")
        return _text("\n\n".join(parts))

    @tool(
        "lire_mail",
        "Lit un mail trouvé par chercher_mails (son id), en lecture seule, et copie ses pièces jointes pour les lire ensuite.",
        {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
    )
    async def lire_mail(args):
        from .outlook import read

        folder = cfg.notes_dir / "medias" / "pieces-jointes"
        try:
            if args["id"].startswith("gmail:"):
                gmail = _gmail()
                if gmail is None:
                    return _text("Gmail perso : pas encore branché.")
                return _text(await asyncio.to_thread(gmail.read, args["id"][len("gmail:"):], folder))
            return _text(await asyncio.to_thread(read, args["id"], folder, cfg.outlook_accounts))
        except Exception as e:  # noqa: BLE001
            return _text(f"Lecture impossible : {e}")

    tools = [noter, preparer_mail, agenda_lister, agenda_ajouter, lire_document, lancer_tache_claude, compte_rendu_visite, lire_maquette_ifc, capturer_maquette, zoomer_image, chercher_mails, lire_mail]
    server = create_sdk_mcp_server(name="perso", tools=tools)
    names = [f"mcp__perso__{t.name}" for t in tools]
    return server, names
