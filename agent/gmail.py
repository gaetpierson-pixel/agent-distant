"""Lecture et envoi de mails avec la boîte Gmail de l'agent."""

import base64
from email.message import EmailMessage
from email.utils import parseaddr


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def extract_text(payload: dict) -> str:
    """Renvoie le texte brut d'un message Gmail (format 'full')."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        text = extract_text(part)
        if text:
            return text
    return ""


def strip_quoted(text: str) -> str:
    """Retire la partie citée d'une réponse (lignes '>' et 'Le ... a écrit :')."""
    kept = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">") or (s.startswith(("Le ", "On ")) and s.endswith(("a écrit :", "wrote:"))):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def parse_message(msg: dict) -> dict:
    headers = msg["payload"].get("headers", [])
    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "from": parseaddr(_header(headers, "From"))[1].lower(),
        "subject": _header(headers, "Subject"),
        "message_id": _header(headers, "Message-ID"),
        "body": strip_quoted(extract_text(msg["payload"])),
    }


def build_raw(to: str, subject: str, body: str, in_reply_to: str = "") -> str:
    m = EmailMessage()
    m["To"] = to
    m["Subject"] = subject
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
        m["References"] = in_reply_to
    m.set_content(body)
    return base64.urlsafe_b64encode(m.as_bytes()).decode()


class Gmail:
    def __init__(self, creds):
        from googleapiclient.discovery import build

        self.api = build("gmail", "v1", credentials=creds, cache_discovery=False).users()

    def unread(self) -> list[dict]:
        res = self.api.messages().list(userId="me", q="is:unread in:inbox").execute()
        out = []
        for ref in res.get("messages", []):
            msg = self.api.messages().get(userId="me", id=ref["id"], format="full").execute()
            out.append(parse_message(msg))
        return out

    def mark_read(self, msg_id: str) -> None:
        self.api.messages().modify(userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}).execute()

    def reply(self, original: dict, body: str) -> None:
        subject = original["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        raw = build_raw(original["from"], subject, body, original["message_id"])
        self.api.messages().send(userId="me", body={"raw": raw, "threadId": original["thread_id"]}).execute()

    def send(self, to: str, subject: str, body: str) -> None:
        self.api.messages().send(userId="me", body={"raw": build_raw(to, subject, body)}).execute()

    def create_draft(self, to: str, subject: str, body: str) -> str:
        res = self.api.drafts().create(userId="me", body={"message": {"raw": build_raw(to, subject, body)}}).execute()
        return res["id"]
