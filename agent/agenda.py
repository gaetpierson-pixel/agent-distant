"""Accès à l'agenda Google."""


class Calendar:
    def __init__(self, creds, calendar_id: str):
        from googleapiclient.discovery import build

        self.api = build("calendar", "v3", credentials=creds, cache_discovery=False)
        self.calendar_id = calendar_id

    def list_events(self, start: str, end: str) -> str:
        res = self.api.events().list(
            calendarId=self.calendar_id, timeMin=start, timeMax=end, singleEvents=True, orderBy="startTime"
        ).execute()
        lines = []
        for e in res.get("items", []):
            when = e["start"].get("dateTime", e["start"].get("date"))
            lines.append(f"- {when} : {e.get('summary', '(sans titre)')}")
        return "\n".join(lines) or "Aucun événement."

    def add_event(self, title: str, start: str, end: str, description: str = "") -> str:
        body = {"summary": title, "description": description, "start": {"dateTime": start}, "end": {"dateTime": end}}
        e = self.api.events().insert(calendarId=self.calendar_id, body=body).execute()
        return f"Événement créé : {e.get('htmlLink', '')}"
