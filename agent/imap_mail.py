"""Boîte Gmail de l'agent via IMAP/SMTP et un mot de passe d'application (sans Google Cloud)."""

import email
import email.header
import imaplib
import smtplib
import time
from email.message import EmailMessage
from email.utils import parseaddr

from .gmail import strip_quoted

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
DRAFTS = '"[Gmail]/Drafts"'


def _text_of(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and part.get("Content-Disposition") is None:
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")


# Objets des réponses automatiques de Google Agenda, au cas où la partie agenda manquerait.
AUTO_SUBJECTS = ("accepted:", "declined:", "tentative:", "accepté :", "accepté:", "refusé :", "refusé:",
                 "provisoire :", "provisoire:", "updated invitation", "invitation mise à jour")


def _is_automatic(msg: email.message.Message, subject: str = "") -> bool:
    """Réponse d'agenda (accepté, refusé…) ou message automatique : ce n'est pas une demande de Gaëtan."""
    for part in msg.walk():
        if part.get_content_type() == "text/calendar":
            method = (part.get_param("method") or "").upper()
            payload = part.get_payload(decode=True) or b""
            if method == "REPLY" or b"METHOD:REPLY" in payload.upper():
                return True
    if subject.strip().lower().startswith(AUTO_SUBJECTS):
        return True
    return msg.get("Auto-Submitted", "no").lower() not in ("", "no")


def parse_raw(uid: str, raw: bytes) -> dict:
    msg = email.message_from_bytes(raw)
    subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
    return {
        "id": uid,
        "thread_id": "",
        "from": parseaddr(msg.get("From", ""))[1].lower(),
        "subject": subject,
        "message_id": msg.get("Message-ID", ""),
        "body": strip_quoted(_text_of(msg)),
        "automatic": _is_automatic(msg, subject),
    }


def build_message(sender: str, to: str, subject: str, body: str, in_reply_to: str = "") -> EmailMessage:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = to
    m["Subject"] = subject
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
        m["References"] = in_reply_to
    m.set_content(body)
    return m


class ImapMail:
    """Même interface que Gmail (gmail.py) : unread, mark_read, reply, send, create_draft."""

    def __init__(self, address: str, app_password: str):
        self.address = address
        self.password = app_password.replace(" ", "")

    def _imap(self) -> imaplib.IMAP4_SSL:
        box = imaplib.IMAP4_SSL(IMAP_HOST)
        box.login(self.address, self.password)
        return box

    def unread(self) -> list[dict]:
        box = self._imap()
        try:
            box.select("INBOX")
            _, data = box.uid("search", None, "UNSEEN")
            out = []
            for uid in data[0].split():
                # BODY.PEEK ne marque pas le mail comme lu : c'est process_once qui le fait.
                _, parts = box.uid("fetch", uid, "(BODY.PEEK[])")
                out.append(parse_raw(uid.decode(), parts[0][1]))
            return out
        finally:
            box.logout()

    def mark_read(self, msg_id: str) -> None:
        box = self._imap()
        try:
            box.select("INBOX")
            box.uid("store", msg_id, "+FLAGS", "(\\Seen)")
        finally:
            box.logout()

    def _send(self, m: EmailMessage) -> None:
        with smtplib.SMTP_SSL(SMTP_HOST, 465) as smtp:
            smtp.login(self.address, self.password)
            smtp.send_message(m)

    def reply(self, original: dict, body: str) -> None:
        subject = original["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        self._send(build_message(self.address, original["from"], subject, body, original["message_id"]))

    def send(self, to: str, subject: str, body: str) -> None:
        self._send(build_message(self.address, to, subject, body))

    def send_invite(self, to: str, subject: str, body: str, ics: bytes) -> None:
        m = build_message(self.address, to, subject, body)
        # Format reconnu par Gmail / Google Agenda : partie text/calendar avec method=REQUEST.
        m.add_alternative(ics, maintype="text", subtype="calendar", params={"method": "REQUEST"})
        self._send(m)

    def create_draft(self, to: str, subject: str, body: str) -> str:
        m = build_message(self.address, to, subject, body)
        box = self._imap()
        try:
            box.append(DRAFTS, "\\Draft", imaplib.Time2Internaldate(time.time()), m.as_bytes())
        finally:
            box.logout()
        return "brouillon Gmail"
