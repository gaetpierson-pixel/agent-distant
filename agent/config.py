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
    # Numéros WhatsApp autorisés (format whatsapp:+33...), et fréquence de lecture de WhatsApp.
    whatsapp_allowed: list[str] = field(default_factory=list)
    whatsapp_poll_seconds: int = 20
    # Identifiants Telegram (nombres) autorisés à donner des ordres au robot de l'agent.
    telegram_allowed: list[int] = field(default_factory=list)
    # Modèle de transcription des vocaux (tiny, base, small, medium) : plus gros = plus juste mais plus lent.
    whisper_model: str = "small"
    state_dir: Path = ROOT / "state"


def _wa(number: str) -> str:
    number = number.strip().replace(" ", "")
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


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
        whatsapp_allowed=[_wa(n) for n in os.getenv("WHATSAPP_ALLOWED", "").split(",") if n.strip()],
        whatsapp_poll_seconds=int(os.getenv("WHATSAPP_POLL_SECONDS", "20")),
        telegram_allowed=[int(n) for n in (os.getenv("TELEGRAM_ALLOWED") or os.getenv("TELEGRAM_ALLOWED_USER_IDS", "")).split(",") if n.strip()],
        whisper_model=os.getenv("WHISPER_MODEL", "small"),
    )
    for d in (cfg.projects_dir, cfg.notes_dir, cfg.state_dir):
        d.mkdir(parents=True, exist_ok=True)
    return cfg
