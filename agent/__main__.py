"""Point d'entrée.

  python -m agent demander "ta demande"   -> teste le cerveau seul, dans le terminal
  python -m agent connecter               -> autorise l'accès au compte Google de l'agent
  python -m agent lancer                  -> démarre l'agent (canal e-mail)
"""

import asyncio
import logging
import os
import sys

from .brain import Brain
from .config import load_config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, cfg = sys.argv[1], load_config()

    if cmd == "demander":
        print(asyncio.run(Brain(cfg).handle(" ".join(sys.argv[2:]), channel="terminal")))
        return

    if cmd == "lancer" and os.getenv("GMAIL_APP_PASSWORD"):
        # Connexion simple à Gmail par mot de passe d'application : pas d'agenda.
        from . import email_channel
        from .imap_mail import ImapMail

        mail = ImapMail(os.environ["GMAIL_ADDRESS"], os.environ["GMAIL_APP_PASSWORD"])
        asyncio.run(email_channel.run(mail, Brain(cfg, gmail=mail), cfg))
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
        asyncio.run(email_channel.run(gmail, brain, cfg))
        return
    print(__doc__)


if __name__ == "__main__":
    main()
