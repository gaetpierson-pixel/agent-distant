"""Lance une tâche Claude dans le cloud (une « routine » Claude Code), par son déclencheur API."""

import json
import urllib.error
import urllib.request

# Service en aperçu de recherche chez Anthropic : la forme des requêtes peut changer.
HEADERS = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "experimental-cc-routine-2026-04-01",
    "Content-Type": "application/json",
}


def fire(url: str, token: str, text: str) -> str:
    """Démarre la routine avec la consigne `text` et renvoie le lien de la session."""
    req = urllib.request.Request(
        url.strip(),
        data=json.dumps({"text": text[:65_000]}).encode(),
        headers={**HEADERS, "Authorization": f"Bearer {token.strip()}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Claude a refusé le lancement ({e.code}) : {detail}") from e
    return out["claude_code_session_url"]
