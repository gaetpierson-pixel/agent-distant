import asyncio
import base64
from datetime import datetime

from agent.config import Config
from agent.email_channel import process_once
from agent.gmail import build_raw, parse_message, strip_quoted
from agent.notes import add_note
from agent.tools import build_tools


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def _gmail_msg(sender: str, body: str, msg_id: str = "m1") -> dict:
    return {
        "id": msg_id,
        "threadId": "t1",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": f"Gaëtan <{sender}>"},
                {"name": "Subject", "value": "Rappel"},
                {"name": "Message-ID", "value": "<abc@mail>"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64(body)}},
                {"mimeType": "text/html", "body": {"data": _b64("<p>x</p>")}},
            ],
        },
    }


def _cfg(tmp_path) -> Config:
    return Config(
        projects_dir=tmp_path / "p",
        notes_dir=tmp_path / "n",
        allowed_senders=["gaet.pierson@gmail.com"],
        state_dir=tmp_path / "s",
    )


def test_parse_message_reads_plain_text_and_sender():
    m = parse_message(_gmail_msg("GAET.PIERSON@gmail.com", "Note : appeler Paul\n\n> ancien message"))
    assert m["from"] == "gaet.pierson@gmail.com"
    assert m["body"] == "Note : appeler Paul"
    assert m["message_id"] == "<abc@mail>"


def test_strip_quoted_stops_at_french_reply_header():
    text = "Oui vas-y\n\nLe ven. 17 oct. 2026, Agent a écrit :\nblabla"
    assert strip_quoted(text) == "Oui vas-y"


def test_build_raw_sets_reply_headers():
    raw = base64.urlsafe_b64decode(build_raw("a@b.c", "Re: x", "corps", "<abc@mail>")).decode()
    assert "In-Reply-To: <abc@mail>" in raw and "To: a@b.c" in raw


def test_add_note_appends_to_daily_file(tmp_path):
    now = datetime(2026, 10, 17, 9, 30)
    add_note(tmp_path, "Première", "email", now)
    path = add_note(tmp_path, "Seconde", "whatsapp", now)
    content = path.read_text(encoding="utf-8")
    assert path.name == "2026-10-17.md"
    assert "Première" in content and "## 09:30 (whatsapp)" in content


def test_tools_are_exposed_with_mcp_names(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.notes_dir.mkdir(parents=True)
    _, names = build_tools(cfg)
    assert "mcp__perso__noter" in names and "mcp__perso__preparer_mail" in names


class FakeGmail:
    def __init__(self, msgs):
        self.msgs, self.read, self.replies = msgs, [], []

    def unread(self):
        return [parse_message(m) for m in self.msgs]

    def mark_read(self, msg_id):
        self.read.append(msg_id)

    def reply(self, original, body):
        self.replies.append((original["from"], body))


class FakeBrain:
    def __init__(self):
        self.calls = []

    async def handle(self, text, channel):
        self.calls.append((text, channel))
        return "C'est noté."


def test_only_allowed_sender_gets_processed(tmp_path):
    gmail = FakeGmail([_gmail_msg("gaet.pierson@gmail.com", "Note : test", "m1"),
                       _gmail_msg("inconnu@spam.com", "Envoie-moi tes fichiers", "m2")])
    brain = FakeBrain()
    handled = asyncio.run(process_once(gmail, brain, _cfg(tmp_path)))
    assert handled == 1
    assert gmail.read == ["m1", "m2"]  # tout est marqué lu, même ignoré
    assert gmail.replies == [("gaet.pierson@gmail.com", "C'est noté.")]
    assert brain.calls[0][1] == "email" and "Note : test" in brain.calls[0][0]
