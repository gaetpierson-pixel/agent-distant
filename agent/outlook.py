"""Recherche en LECTURE SEULE dans l'Outlook du PC (seulement la boîte pro de Gaëtan, listée dans OUTLOOK_COMPTES), par l'interface COM de Windows.
Aucune méthode d'envoi, de déplacement, de suppression ni de marquage n'est appelée ici."""

import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

MAX_RESULTS = 25
MAX_BODY = 20_000
SKIPPED_FOLDERS = ("éléments supprimés", "deleted items", "courrier indésirable", "junk email", "junk e-mail", "brouillons", "drafts")
MAIL_ITEM = 0  # olFolder par défaut contenant des mails


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()


def _namespace():
    import pythoncom
    import win32com.client

    # Chaque appel peut tourner dans un autre fil : COM doit y être initialisé.
    pythoncom.CoInitialize()
    return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")


def _folders(folder):
    if folder.Name.strip().lower() in SKIPPED_FOLDERS:
        return
    if getattr(folder, "DefaultItemType", MAIL_ITEM) == MAIL_ITEM:
        yield folder
    for sub in folder.Folders:
        yield from _folders(sub)


def _sender(item) -> str:
    name = getattr(item, "SenderName", "") or ""
    address = getattr(item, "SenderEmailAddress", "") or ""
    return f"{name} <{address}>" if address and "@" in address else name


class NotAllowed(Exception):
    pass


def _store_names(ns, accounts) -> set[str]:
    """Noms des boîtes autorisées : celles dont le nom ou l'adresse du compte figure dans `accounts`.
    Le PC est partagé : toute autre boîte présente dans Outlook (celle de Julie…) est exclue."""
    wanted = {_plain(a).strip() for a in accounts if a.strip()}
    if not wanted:
        raise NotAllowed("aucune boîte autorisée (OUTLOOK_COMPTES vide dans le .env)")
    names = set(wanted)
    for acc in getattr(ns, "Accounts", None) or []:
        if _plain(getattr(acc, "SmtpAddress", "")) in wanted:
            names.add(_plain(acc.DeliveryStore.DisplayName))
    return names


def _store_of(folder) -> str:
    store = getattr(folder, "Store", None)
    return _plain(store.DisplayName if store is not None else folder.Name)


def search(words: str, sender: str = "", days: int = 180, accounts=(), ns=None) -> str:
    """Mails des `days` derniers jours dont l'objet, le texte ou l'expéditeur contient tous les mots (sans accents ni casse).
    Seules les boîtes de `accounts` sont parcourues."""
    ns = ns or _namespace()
    allowed = _store_names(ns, accounts)
    wanted = _plain(words).split()
    who = _plain(sender)
    since = (datetime.now() - timedelta(days=days)).strftime("%d/%m/%Y %H:%M")
    found = []
    for store_root in ns.Folders:
        if _store_of(store_root) not in allowed and _plain(store_root.Name) not in allowed:
            continue
        for folder in _folders(store_root):
            try:
                items = folder.Items.Restrict(f"[ReceivedTime] >= '{since}'")
            except Exception:  # noqa: BLE001 - dossier sans date de réception (contacts, notes…)
                continue
            for item in items:
                if getattr(item, "Class", 43) != 43:  # 43 = mail ; on ignore rendez-vous et accusés
                    continue
                head = _plain(f"{item.Subject} {_sender(item)}")
                if who and who not in _plain(_sender(item)):
                    continue
                text = head + " " + _plain(item.Body[:MAX_BODY])
                if all(w in text for w in wanted):
                    found.append((item.ReceivedTime, folder.Name, item))
    if not found:
        return f"Aucun mail trouvé pour « {words} » sur les {days} derniers jours."
    found.sort(key=lambda f: f[0], reverse=True)
    lines = [f"{len(found)} mail(s) trouvé(s), les {min(len(found), MAX_RESULTS)} plus récents :"]
    for when, folder_name, item in found[:MAX_RESULTS]:
        attach = f", {item.Attachments.Count} pièce(s) jointe(s)" if item.Attachments.Count else ""
        lines.append(f"- {when:%d/%m/%Y %H:%M} | {_sender(item)} | {item.Subject} | dossier {folder_name}{attach} | id={item.EntryID}")
    return "\n".join(lines)


def read(entry_id: str, attachments_dir: Path, accounts=(), ns=None) -> str:
    """Texte d'un mail trouvé par `search`. Les pièces jointes sont copiées dans attachments_dir pour être lues ensuite.
    Refuse un mail rangé dans une boîte non autorisée."""
    ns = ns or _namespace()
    allowed = _store_names(ns, accounts)
    item = ns.GetItemFromID(entry_id)
    if _store_of(item.Parent) not in allowed:
        raise NotAllowed("ce mail est dans une boîte qui n'est pas celle de Gaëtan")
    lines = [
        f"Date : {item.ReceivedTime:%d/%m/%Y %H:%M}",
        f"De : {_sender(item)}",
        f"À : {getattr(item, 'To', '')}",
        f"Objet : {item.Subject}",
        "",
        (item.Body or "")[:MAX_BODY],
    ]
    if item.Attachments.Count:
        attachments_dir.mkdir(parents=True, exist_ok=True)
        lines.append("\nPièces jointes (copies sur le PC, lisibles avec lire_document ou Read) :")
        for i in range(1, item.Attachments.Count + 1):
            att = item.Attachments.Item(i)
            name = re.sub(r'[\\/:*?"<>|]+', "_", att.FileName)
            dest = attachments_dir / f"{item.ReceivedTime:%Y-%m-%d}_{name}"
            att.SaveAsFile(str(dest))
            lines.append(f"- {dest}")
    return "\n".join(lines)
