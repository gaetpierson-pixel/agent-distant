"""Recherche en LECTURE SEULE dans le Gmail perso de Gaëtan, par IMAP et un mot de passe d'application.
La boîte est ouverte en lecture seule et les mails lus avec BODY.PEEK : rien n'est marqué, déplacé ni supprimé."""

import email
import email.header
import imaplib
import re
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from .imap_mail import _text_of

IMAP_HOST = "imap.gmail.com"
MAX_RESULTS = 25
MAX_BODY = 20_000


def _decode(value: str) -> str:
    return str(email.header.make_header(email.header.decode_header(value or "")))


class GmailSearch:
    def __init__(self, address: str, password: str, connect=None):
        self.address, self.password = address, password.replace(" ", "")
        self._connect = connect or (lambda: imaplib.IMAP4_SSL(IMAP_HOST))

    def _open(self):
        imap = self._connect()
        imap.login(self.address, self.password)
        # « Tous les messages » porte un nom traduit selon la langue du compte : on le trouve par son drapeau \All.
        _, folders = imap.list()
        all_mail = next((f.decode().split(' "/" ')[-1] for f in folders if b"\\All" in f), '"[Gmail]/All Mail"')
        imap.select(all_mail, readonly=True)
        return imap

    def search(self, words: str, sender: str = "", days: int = 180) -> str:
        query = f"{words} newer_than:{days}d" + (f" from:{sender}" if sender else "")
        imap = self._open()
        try:
            _, data = imap.uid("SEARCH", "X-GM-RAW", '"' + query.replace('"', "") + '"')
            uids = data[0].split()[::-1][:MAX_RESULTS]  # les plus récents d'abord
            if not uids:
                return f"Aucun mail trouvé dans le Gmail perso pour « {words} »."
            lines = [f"{len(data[0].split())} mail(s) dans le Gmail perso, les {len(uids)} plus récents :"]
            for uid in uids:
                _, msg_data = imap.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                head = email.message_from_bytes(msg_data[0][1])
                when = parsedate_to_datetime(head["Date"]).strftime("%d/%m/%Y %H:%M") if head["Date"] else "?"
                lines.append(f"- {when} | {_decode(head['From'])} | {_decode(head['Subject'])} | id=gmail:{uid.decode()}")
            return "\n".join(lines)
        finally:
            imap.logout()

    def read(self, uid: str, attachments_dir: Path) -> str:
        imap = self._open()
        try:
            _, msg_data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
        finally:
            imap.logout()
        msg = email.message_from_bytes(msg_data[0][1])
        lines = [
            f"Date : {msg['Date']}",
            f"De : {_decode(msg['From'])}",
            f"À : {_decode(msg['To'])}",
            f"Objet : {_decode(msg['Subject'])}",
            "",
            _text_of(msg)[:MAX_BODY],
        ]
        saved = []
        for part in msg.walk():
            name = part.get_filename()
            if name:
                attachments_dir.mkdir(parents=True, exist_ok=True)
                dest = attachments_dir / re.sub(r'[\\/:*?"<>|]+', "_", _decode(name))
                dest.write_bytes(part.get_payload(decode=True) or b"")
                saved.append(f"- {dest}")
        if saved:
            lines += ["", "Pièces jointes (copies sur le PC, lisibles avec lire_document ou Read) :", *saved]
        return "\n".join(lines)
