"""Canal Telegram : l'agent va chercher lui-même les messages de son robot (pas de webhook, pas de tunnel)."""

import asyncio
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from .brain import Brain
from .config import Config

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"
FILES = "https://api.telegram.org/file/bot{token}/{path}"
# Telegram refuse les messages de plus de 4096 caractères : on découpe un peu avant.
CHUNK = 4000


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


class TelegramBot:
    def __init__(self, token: str):
        self.token = token.strip()

    def _call(self, method: str, params: dict, timeout: int = 30) -> dict:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(API.format(token=self.token, method=method), data=data)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.load(resp)
        if not out.get("ok"):
            raise RuntimeError(f"Telegram {method} : {out.get('description')}")
        return out["result"]

    def updates(self, offset: int, wait: int = 50) -> list[dict]:
        # Attente longue : Telegram répond dès qu'un message arrive, ou au bout de `wait` secondes.
        return self._call("getUpdates", {"offset": offset, "timeout": wait}, timeout=wait + 10)

    def download(self, file_id: str, dest: Path) -> Path:
        info = self._call("getFile", {"file_id": file_id})
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(FILES.format(token=self.token, path=info["file_path"]), timeout=60) as resp:
            dest.write_bytes(resp.read())
        return dest

    def _upload(self, method: str, field: str, chat_id: int, path: Path, mime: str) -> None:
        boundary = "agent-distant-fichier"
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            API.format(token=self.token, method=method),
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.load(resp)
        if not out.get("ok"):
            raise RuntimeError(f"Telegram {method} : {out.get('description')}")

    def send_voice(self, chat_id: int, ogg: Path) -> None:
        self._upload("sendVoice", "voice", chat_id, ogg, "audio/ogg")

    def send_file(self, chat_id: int, path: Path) -> None:
        if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            self._upload("sendPhoto", "photo", chat_id, path, mime)
            return
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        self._upload("sendDocument", "document", chat_id, path, mime)

    def send(self, chat_id: int, text: str) -> None:
        for chunk in split_text(text):
            self._call("sendMessage", {"chat_id": chat_id, "text": chunk})


class Offset:
    """Dernier message traité, gardé dans state/ pour ne rien retraiter après un redémarrage."""

    def __init__(self, cfg: Config):
        self.path = cfg.state_dir / "telegram_offset.txt"
        self.value = int(self.path.read_text()) if self.path.exists() else 0

    def set(self, value: int) -> None:
        self.value = value
        self.path.write_text(str(value))


def _media(msg: dict) -> tuple[str, str, str] | None:
    """(file_id, type, nom de fichier) d'une photo, d'une vidéo ou d'un fichier joint (PDF, Excel, Word…)."""
    if msg.get("photo"):
        # Telegram donne plusieurs tailles : la dernière est la plus grande.
        return msg["photo"][-1]["file_id"], "photo", "photo.jpg"
    for key in ("video", "video_note"):
        if msg.get(key):
            return msg[key]["file_id"], "video", "video.mp4"
    doc = msg.get("document")
    if doc:
        mime = doc.get("mime_type", "")
        if mime.startswith("image/"):
            return doc["file_id"], "photo", "photo.png" if mime == "image/png" else "photo.jpg"
        if mime.startswith("video/"):
            return doc["file_id"], "video", "video" + (Path(doc.get("file_name", "")).suffix or ".mp4")
        name = re.sub(r'[\\/:*?"<>|]+', "_", doc.get("file_name") or "fichier")
        return doc["file_id"], "fichier", name
    return None


def _video_request(path: Path, cfg: Config, caption: str) -> str:
    from .video import frames, has_audio

    shots = frames(path, path.parent / f"{path.stem}_images")
    lines = [f"[Vidéo envoyée par Gaëtan, enregistrée ici : {path}. Images extraites (lis-les avec Read) :"]
    lines += [f"- {s}" for s in shots]
    if has_audio(path):
        from .voice import transcribe

        lines.append(f"Son de la vidéo, transcription automatique : {transcribe(path, cfg.whisper_model, cfg.vocabulary)}")
    lines.append("]")
    lines.append(caption or "Pas de légende : décris en deux lignes ce que montre la vidéo ; elle est gardée pour le prochain compte-rendu.")
    return "\n".join(lines)


def to_request(bot, cfg: Config, msg: dict) -> str:
    """Transforme le message en demande texte : vocal transcrit, photo, vidéo ou fichier enregistrés sur le PC."""
    caption = msg.get("text") or msg.get("caption") or ""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
    media = cfg.notes_dir / "medias"
    if msg.get("voice") or msg.get("audio"):
        from .voice import transcribe

        audio = bot.download((msg.get("voice") or msg["audio"])["file_id"], media / f"{stamp}_vocal.ogg")
        return f"[Message vocal, transcription automatique, à prendre avec prudence]\n{transcribe(audio, cfg.whisper_model, cfg.vocabulary)}"
    found = _media(msg)
    if not found:
        return caption
    file_id, kind, name = found
    path = bot.download(file_id, media / f"{stamp}_{name}")
    if kind == "video":
        return _video_request(path, cfg, caption)
    if kind == "fichier":
        return (
            f"[Fichier envoyé par Gaëtan, enregistré ici : {path}. Lis-le avec `lire_document` (Excel, Word, PDF), "
            f"`lire_maquette_ifc` (.ifc) ou Read.]\n"
            + (caption or "Pas de message : résume-le en quelques lignes.")
        )
    return f"[Photo envoyée par Gaëtan, enregistrée ici : {path}. Lis-la avec l'outil Read.]\n" + (
        caption
        or "Pas de légende. Si c'est une note manuscrite, retranscris-la et enregistre-la avec `noter`. "
        "Sinon, réponds juste en une ligne que la photo est gardée pour le prochain compte-rendu."
    )


async def handle_update(bot, brain: Brain, cfg: Config, update: dict) -> bool:
    msg = update.get("message")
    if not msg:
        return False
    user = (msg.get("from") or {}).get("id")
    chat = msg["chat"]["id"]
    if user not in cfg.telegram_allowed:
        # On répond avec l'identifiant : c'est comme ça que Gaëtan trouve le sien au premier essai.
        log.warning("Telegram ignoré, compte non autorisé : %s", user)
        bot.send(chat, f"Je ne réponds qu'à mon propriétaire. Votre identifiant Telegram : {user}")
        return False
    try:
        text = await asyncio.to_thread(to_request, bot, cfg, msg)
    except Exception as e:  # noqa: BLE001
        log.exception("Échec de la lecture du vocal ou de la photo")
        bot.send(chat, f"Je n'ai pas pu lire ce message : {e}")
        return False
    if not text:
        bot.send(chat, "Je ne sais lire que le texte, les vocaux, les photos, les vidéos et les fichiers.")
        return False
    log.info("Tâche Telegram reçue : %s", text[:80])
    try:
        answer = await brain.handle(text, channel="telegram")
    except Exception as e:  # noqa: BLE001 - on prévient Gaëtan plutôt que de se taire
        log.exception("Échec de la tâche")
        answer = f"Erreur pendant la tâche : {e}"
    bot.send(chat, answer)
    for produced in list(getattr(brain, "outbox", [])):
        try:
            bot.send_file(chat, produced)
        except Exception:  # noqa: BLE001
            log.exception("Échec de l'envoi du fichier")
            bot.send(chat, f"Le fichier est sur le PC, mais je n'ai pas pu l'envoyer : {produced}")
    if cfg.voice_replies and (msg.get("voice") or msg.get("audio")):
        # Vocal reçu : on répond aussi en vocal (le texte reste, pour les liens et les détails).
        try:
            from .speech import synthesize

            ogg = cfg.notes_dir / "medias" / f"{datetime.now():%Y-%m-%d_%H%M%S}_reponse.ogg"
            await asyncio.to_thread(synthesize, answer, ogg, cfg.tts_voice, cfg.state_dir / "voix")
            bot.send_voice(chat, ogg)
        except Exception:  # noqa: BLE001 - le texte est déjà parti, on n'insiste pas
            log.exception("Échec de la réponse vocale")
    return True


async def run(bot, brain: Brain, cfg: Config) -> None:
    offset = Offset(cfg)
    log.info("Canal Telegram démarré.")
    while True:
        try:
            updates = await asyncio.to_thread(bot.updates, offset.value)
            for update in updates:
                # Avancé d'abord : un message qui fait planter l'agent n'est pas retraité en boucle.
                offset.set(update["update_id"] + 1)
                await handle_update(bot, brain, cfg, update)
        except Exception:  # noqa: BLE001 - une coupure réseau ne doit pas arrêter l'agent
            log.exception("Erreur pendant la lecture de Telegram")
            await asyncio.sleep(10)
