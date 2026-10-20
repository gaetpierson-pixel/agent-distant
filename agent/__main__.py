"""Point d'entrée.

  python -m agent demander "ta demande"   -> teste le cerveau seul, dans le terminal
  python -m agent connecter               -> autorise l'accès au compte Google de l'agent
  python -m agent lancer                  -> démarre l'agent (mail, et Telegram si réglé)
"""

import asyncio
import logging
import os
import socket
import sys

from .brain import Brain
from .config import load_config


async def _run_channels(email_task, brain: Brain, cfg) -> None:
    """Le mail tourne toujours ; Telegram s'ajoute si son jeton est rempli."""
    tasks = [email_task]
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from . import telegram_channel

        bot = telegram_channel.TelegramBot(os.environ["TELEGRAM_BOT_TOKEN"])
        tasks.append(telegram_channel.run(bot, brain, cfg))
    await asyncio.gather(*tasks)


# Code de sortie quand un autre agent tourne déjà : demarrer-agent.bat s'arrête alors au lieu de relancer.
ALREADY_RUNNING = 3
LOCK_PORT = 47613


def _single_instance():
    """Une seule instance à la fois : le port local reste pris tant que l'agent vit, et se libère s'il meurt."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        logging.info("Un agent tourne déjà : celui-ci s'arrête.")
        sys.exit(ALREADY_RUNNING)
    return sock


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, cfg = sys.argv[1], load_config()
    if cmd == "lancer":
        _lock = _single_instance()  # noqa: F841 - gardé ouvert jusqu'à la fin du processus

    if cmd == "demander":
        print(asyncio.run(Brain(cfg).handle(" ".join(sys.argv[2:]), channel="terminal")))
        return

    if cmd == "lancer" and os.getenv("GMAIL_APP_PASSWORD"):
        # Connexion simple à Gmail par mot de passe d'application ; agenda par l'adresse iCal si elle est réglée.
        from . import email_channel
        from .imap_mail import ImapMail

        mail = ImapMail(os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
        calendar = None
        if os.getenv("CALENDAR_ICS_URL"):
            from .ics_agenda import IcsCalendar

            calendar = IcsCalendar(os.environ["CALENDAR_ICS_URL"], mail, cfg.calendar_id)
        brain = Brain(cfg, gmail=mail, calendar=calendar)
        asyncio.run(_run_channels(email_channel.run(mail, brain, cfg), brain, cfg))
        return

    from .agenda import Calendar
    from .gmail import Gmail
    from .google_auth import get_credentials

    creds = get_credentials()
    if cmd == "connecter":
        print("Compte Google connecté.")
        return
    if cmd == "lancer":
        from . import email_channel

        gmail = Gmail(creds)
        brain = Brain(cfg, gmail=gmail, calendar=Calendar(creds, cfg.calendar_id))
        asyncio.run(_run_channels(email_channel.run(gmail, brain, cfg), brain, cfg))
        return
    print(__doc__)


if __name__ == "__main__":
    main()
