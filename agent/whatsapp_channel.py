"""Canal WhatsApp via Twilio : l'agent va chercher les messages reçus, sans webhook (le PC n'a pas d'adresse publique)."""

import asyncio
import base64
import json
import logging
import urllib.parse
import urllib.request
from datetime import date, timedelta

from .brain import Brain
from .config import Config, _wa

log = logging.getLogger(__name__)

API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
# Twilio refuse les messages de plus de 1600 caractères : on découpe.
CHUNK = 1500


def split_text(text: str, size: int = CHUNK) -> list[str]:
    chunks = []
    while len(text) > size:
        cut = text.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks or [""]


class TwilioWhatsApp:
    def __init__(self, account_sid: str, auth_token: str, number: str):
        self.sid = account_sid.strip()
        self.number = _wa(number)
        token = base64.b64encode(f"{self.sid}:{auth_token.strip()}".encode()).decode()
        self._auth = f"Basic {token}"

    def _call(self, url: str, data: dict | None = None) -> dict:
        body = urllib.parse.urlencode(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers={"Authorization": self._auth})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def incoming(self) -> list[dict]:
        """Messages reçus sur le numéro de l'agent depuis hier, du plus ancien au plus récent."""
        since = (date.today() - timedelta(days=1)).isoformat()
        query = urllib.parse.urlencode({"To": self.number, "DateSent>=": since, "PageSize": 50})
        page = self._call(f"{API.format(sid=self.sid)}?{query}")
        msgs = [m for m in page.get("messages", []) if m.get("direction") == "inbound"]
        return [
            {"id": m["sid"], "from": m["from"], "body": m.get("body") or "", "num_media": int(m.get("num_media") or 0)}
            for m in reversed(msgs)
        ]

    def send(self, to: str, text: str) -> None:
        for chunk in split_text(text):
            self._call(API.format(sid=self.sid), {"From": self.number, "To": _wa(to), "Body": chunk})


class Seen:
    """Identifiants des messages déjà traités, gardés dans state/ pour survivre à un redémarrage."""

    def __init__(self, cfg: Config):
        self.path = cfg.state_dir / "whatsapp_vus.json"
        self.ids: set[str] = set(json.loads(self.path.read_text())) if self.path.exists() else set()
        self.fresh = not self.path.exists()

    def add(self, msg_id: str) -> None:
        self.ids.add(msg_id)
        # On ne garde que les plus récents : la liste Twilio ne remonte qu'à hier.
        self.path.write_text(json.dumps(sorted(self.ids)[-500:]))


async def process_once(wa, brain: Brain, cfg: Config, seen: Seen) -> int:
    msgs = wa.incoming()
    if seen.fresh:
        # Premier démarrage : on ne rejoue pas l'historique, on part de maintenant.
        for m in msgs:
            seen.add(m["id"])
        seen.fresh = False
        return 0
    handled = 0
    for msg in msgs:
        if msg["id"] in seen.ids:
            continue
        # Noté d'abord : un message qui fait planter l'agent n'est pas retraité en boucle.
        seen.add(msg["id"])
        if _wa(msg["from"]) not in cfg.whatsapp_allowed:
            log.warning("WhatsApp ignoré, numéro non autorisé : %s", msg["from"])
            continue
        if msg["num_media"] and not msg["body"]:
            wa.send(msg["from"], "Je ne sais pas encore lire les vocaux ni les photos. Envoyez-moi du texte pour l'instant.")
            continue
        log.info("Tâche WhatsApp reçue : %s", msg["body"][:80])
        try:
            answer = await brain.handle(msg["body"], channel="whatsapp")
        except Exception as e:  # noqa: BLE001 - on prévient Gaëtan plutôt que de se taire
            log.exception("Échec de la tâche")
            answer = f"Erreur pendant la tâche : {e}"
        wa.send(msg["from"], answer)
        handled += 1
    return handled


async def run(wa, brain: Brain, cfg: Config) -> None:
    seen = Seen(cfg)
    log.info("Canal WhatsApp démarré, vérification toutes les %s s.", cfg.whatsapp_poll_seconds)
    while True:
        try:
            await process_once(wa, brain, cfg, seen)
        except Exception:  # noqa: BLE001 - une coupure réseau ne doit pas arrêter l'agent
            log.exception("Erreur pendant la lecture de WhatsApp")
        await asyncio.sleep(cfg.whatsapp_poll_seconds)
