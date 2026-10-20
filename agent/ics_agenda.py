"""Agenda sans Google Cloud : lecture par l'adresse secrète iCal, ajout par invitation envoyée par mail."""

import urllib.request
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


def _parse(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=PARIS)


def events_between(ics: bytes, start: str, end: str) -> str:
    import icalendar
    import recurring_ical_events

    cal = icalendar.Calendar.from_ical(ics)
    lines = []
    for ev in recurring_ical_events.of(cal).between(_parse(start), _parse(end)):
        begin = ev["DTSTART"].dt
        when = begin.astimezone(PARIS).strftime("%a %d/%m %H:%M") if isinstance(begin, datetime) else f"{begin:%a %d/%m} (journée)"
        where = f" ({ev['LOCATION']})" if ev.get("LOCATION") else ""
        lines.append((str(begin), f"- {when} : {ev.get('SUMMARY', '(sans titre)')}{where}"))
    return "\n".join(line for _, line in sorted(lines)) or "Aucun événement."


def build_invite(organizer: str, attendee: str, title: str, start: str, end: str, description: str = "") -> bytes:
    import icalendar

    cal = icalendar.Calendar()
    cal.add("prodid", "-//Agent distant//FR")
    cal.add("version", "2.0")
    cal.add("method", "REQUEST")
    ev = icalendar.Event()
    ev.add("uid", f"{uuid.uuid4()}@agent-distant")
    ev.add("dtstamp", datetime.now(timezone.utc))
    ev.add("dtstart", _parse(start))
    ev.add("dtend", _parse(end))
    ev.add("summary", title)
    if description:
        ev.add("description", description)
    ev.add("organizer", f"mailto:{organizer}")
    att = icalendar.vCalAddress(f"mailto:{attendee}")
    att.params["ROLE"] = icalendar.vText("REQ-PARTICIPANT")
    att.params["PARTSTAT"] = icalendar.vText("NEEDS-ACTION")
    att.params["RSVP"] = icalendar.vText("TRUE")
    ev.add("attendee", att)
    cal.add_component(ev)
    return cal.to_ical()


class IcsCalendar:
    """Même interface que agenda.Calendar : list_events et add_event."""

    def __init__(self, ics_url: str, mail, owner: str):
        self.ics_url, self.mail, self.owner = ics_url.strip(), mail, owner

    def list_events(self, start: str, end: str) -> str:
        with urllib.request.urlopen(self.ics_url, timeout=30) as resp:
            return events_between(resp.read(), start, end)

    def add_event(self, title: str, start: str, end: str, description: str = "") -> str:
        ics = build_invite(self.mail.address, self.owner, title, start, end, description)
        when = _parse(start).astimezone(PARIS).strftime("%d/%m à %H:%M")
        self.mail.send_invite(self.owner, f"Invitation : {title} ({when})", f"{title}\n{description}".strip(), ics)
        return f"Invitation envoyée à {self.owner} : elle apparaît dans son agenda (il peut la refuser)."
