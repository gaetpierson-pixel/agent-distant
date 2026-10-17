"""Canal e-mail : lit les mails de Gaëtan arrivés dans la boîte de l'agent et y répond."""

import asyncio
import logging

from .brain import Brain
from .config import Config

log = logging.getLogger(__name__)


def is_allowed(sender: str, cfg: Config) -> bool:
    return sender.lower() in cfg.allowed_senders


async def process_once(gmail, brain: Brain, cfg: Config) -> int:
    handled = 0
    for msg in gmail.unread():
        # Marqué lu d'abord : un mail qui fait planter l'agent n'est pas retraité en boucle.
        gmail.mark_read(msg["id"])
        if not is_allowed(msg["from"], cfg):
            log.warning("Mail ignoré, expéditeur non autorisé : %s", msg["from"])
            continue
        request = f"Objet : {msg['subject']}\n\n{msg['body']}"
        log.info("Tâche reçue de %s : %s", msg["from"], msg["subject"])
        try:
            answer = await brain.handle(request, channel="email")
        except Exception as e:  # noqa: BLE001 - on prévient Gaëtan plutôt que de se taire
            log.exception("Échec de la tâche")
            answer = f"Erreur pendant la tâche : {e}"
        gmail.reply(msg, answer)
        handled += 1
    return handled


async def run(gmail, brain: Brain, cfg: Config) -> None:
    log.info("Canal e-mail démarré, vérification toutes les %s s.", cfg.poll_seconds)
    while True:
        try:
            await process_once(gmail, brain, cfg)
        except Exception:  # noqa: BLE001 - une coupure réseau ne doit pas arrêter l'agent
            log.exception("Erreur pendant la lecture des mails")
        await asyncio.sleep(cfg.poll_seconds)
