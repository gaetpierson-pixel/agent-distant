"""Réglages de l'agent, lus depuis le fichier .env."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    # Dossier où se trouvent vos projets en cours : l'agent y lit et écrit.
    projects_dir: Path
    # Dossier où l'agent range vos notes (texte, vocal transcrit, photo lue).
    notes_dir: Path
    # Adresses autorisées à donner des ordres (les autres sont ignorées).
    allowed_senders: list[str] = field(default_factory=list)
    # Agenda Google à gérer (votre adresse, si vous l'avez partagé avec l'agent).
    calendar_id: str = "primary"
    model: str = "claude-sonnet-5-5"
    # Plafond de dépense par tâche, en dollars.
    max_budget_usd: float = 0.50
    poll_seconds: int = 60
    # Identifiants Telegram (nombres) autorisés à donner des ordres au robot de l'agent.
    telegram_allowed: list[int] = field(default_factory=list)
    # Dossiers de Gaëtan que l'agent peut lire mais jamais modifier (par exemple le SharePoint synchronisé).
    read_only_dirs: list[Path] = field(default_factory=list)
    # Modèle de transcription des vocaux (tiny, base, small, medium) : plus gros = plus juste mais plus lent.
    whisper_model: str = "small"
    # Répondre en vocal aux vocaux (voix de synthèse Piper, fabriquée sur le PC).
    # Déclencheur API d'une routine Claude Code (claude.ai/code/routines) : URL et jeton.
    routine_url: str = ""
    routine_token: str = ""
    voice_replies: bool = True
    tts_voice: str = "fr_FR-siwis-medium"
    # Dossier des chantiers (…\02 - DEVIS) où l'agent peut AJOUTER ses comptes-rendus, jamais modifier. Vide : il les garde chez lui.
    cr_root: Path | None = None
    cr_subfolder: str = "00 - ETUDE"
    state_dir: Path = ROOT / "state"


def is_inside(path, folders) -> bool:
    """Vrai si `path` est dans l'un des dossiers (comparaison insensible à la casse sous Windows)."""
    target = os.path.normcase(os.path.realpath(path))
    for folder in folders:
        root = os.path.normcase(os.path.realpath(folder))
        if target == root or target.startswith(root.rstrip(os.sep) + os.sep):
            return True
    return False


def load_config() -> Config:
    load_dotenv(ROOT / ".env")
    senders = [s.strip().lower() for s in os.getenv("ALLOWED_SENDERS", "").split(",") if s.strip()]
    cfg = Config(
        projects_dir=Path(os.getenv("PROJECTS_DIR", ROOT / "projets")).expanduser(),
        notes_dir=Path(os.getenv("NOTES_DIR", ROOT / "notes")).expanduser(),
        allowed_senders=senders,
        calendar_id=os.getenv("CALENDAR_ID", "primary"),
        model=os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"),
        max_budget_usd=float(os.getenv("MAX_BUDGET_USD", "0.50")),
        poll_seconds=int(os.getenv("POLL_SECONDS", "60")),
        telegram_allowed=[int(n) for n in (os.getenv("TELEGRAM_ALLOWED") or os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")).split(",") if n.strip()],
        whisper_model=os.getenv("WHISPER_MODEL", "small"),
        voice_replies=os.getenv("REPONSE_VOCALE", "1") != "0",
        routine_url=os.getenv("ROUTINE_URL", ""),
        routine_token=os.getenv("ROUTINE_TOKEN", ""),
        tts_voice=os.getenv("VOIX", "fr_FR-siwis-medium"),
        read_only_dirs=[Path(d.strip()).expanduser() for d in os.getenv("READ_ONLY_DIRS", "").split(";") if d.strip()],
        cr_root=Path(os.environ["CR_DOSSIER_CHANTIERS"].strip()).expanduser() if os.getenv("CR_DOSSIER_CHANTIERS", "").strip() else None,
        cr_subfolder=os.getenv("CR_SOUS_DOSSIER", "00 - ETUDE"),
    )
    for d in (cfg.projects_dir, cfg.notes_dir, cfg.state_dir):
        d.mkdir(parents=True, exist_ok=True)
    return cfg
