"""Point d'entrée.

  python -m agent demander "ta demande"   -> teste le cerveau seul, dans le terminal
  python -m agent connecter               -> autorise l'accès au compte Google de l'agent
  python -m agent lancer                  -> démarre l'agent (mail, et WhatsApp si Twilio est réglé)
"""

import asyncio
import logging
import os
import sys

from .brain import Brain
from .config import load_config


async def _run_channels(email_task, brain: Brain, cfg) -> None:
    """Le mail tourne toujours ; WhatsApp et Telegram s'ajoutent si leurs réglages sont remplis."""
    tasks = [email_task]
    if os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"):
        from . import whatsapp_channel

        wa = whatsapp_channel.TwilioWhatsApp(
            os.environ["TWILIO_ACCOUNT_SID"],
            os.environ["TWILIO_AUTH_TOKEN"],
            os.getenv("TWILIO_WHATSAPP_NUMBER", "+14155238886"),
        )
        tasks.append(whatsapp_channel.run(wa, brain, cfg))
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from . import telegram_channel

        bot = telegram_channel.TelegramBot(os.environ["TELEGRAM_BOT_TOKEN"])
        tasks.append(telegram_channel.run(bot, brain, cfg))
    await asyncio.gather(*tasks)


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
        brain = Brain(cfg, gmail=mail)
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
