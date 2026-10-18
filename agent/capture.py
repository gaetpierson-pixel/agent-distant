"""Vues de maquettes en image : capture d'un lien Autodesk Viewer ou d'une maquette HTML, dans le navigateur Edge du PC."""

import asyncio
import os
import re
from pathlib import Path
from urllib.parse import urlparse

# Seules ces adresses peuvent être ouvertes : l'agent ne navigue pas ailleurs.
ALLOWED_HOSTS = ("viewer.autodesk.com", "a360.co", "autodesk360.com")
WAIT_SECONDS = 40  # la visionneuse Autodesk charge la 3D en plusieurs dizaines de secondes
SHEET_WAIT_SECONDS = 25
# Bandeau cookies (OneTrust sur Autodesk) : on refuse, ce qui le ferme sans rien accepter.
COOKIE_BUTTONS = ("#onetrust-reject-all-handler", "button:has-text('Decline')", "button:has-text('Refuser')", "button:has-text('Tout refuser')")
# Numéros de feuille du type AO-105, PLN-01… : servent à dire à Gaëtan ce qui existe quand la feuille demandée manque.
SHEET_NUMBER = re.compile(r"^[A-Z]{1,5}-\d{2,4}\b")


class SheetNotFound(Exception):
    pass


def allowed_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return urlparse(url).scheme == "https" and any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


async def _decline_cookies(page) -> None:
    for selector in COOKIE_BUTTONS:
        button = page.locator(selector).first
        try:
            if await button.is_visible():
                await button.click()
                await asyncio.sleep(1)
                return
        except Exception:  # noqa: BLE001 - pas de bandeau : rien à fermer
            continue


async def _open_sheet(page, feuille: str) -> None:
    """Clique sur la feuille dont le nom contient `feuille` (ex. « AO-105 », « coupe A-B », « plan radier »)."""
    wanted = page.get_by_text(re.compile(re.escape(feuille.strip()), re.IGNORECASE))
    count = await wanted.count()
    for i in range(count):
        item = wanted.nth(i)
        if await item.is_visible():
            await item.click()
            return
    texts = await page.locator("body").inner_text()
    sheets = sorted({line.strip() for line in texts.splitlines() if SHEET_NUMBER.match(line.strip())})
    raise SheetNotFound(f"Feuille « {feuille} » introuvable. Feuilles visibles : {', '.join(sheets) or 'aucune'}")


async def capture(target: str, dest: Path, wait: int = WAIT_SECONDS, feuille: str = "") -> Path:
    """target : adresse https autorisée, ou chemin d'un fichier .html local. Renvoie l'image PNG."""
    from playwright.async_api import async_playwright

    url = target if target.startswith("https://") else Path(target).resolve().as_uri()
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        # Edge est déjà sur Windows : rien à télécharger. NAVIGATEUR=chromium pour un autre navigateur.
        channel = os.getenv("NAVIGATEUR", "msedge")
        browser = await p.chromium.launch(
            channel=None if channel == "chromium" else channel,
            args=["--ignore-gpu-blocklist", "--enable-webgl", "--use-angle=swiftshader"],
        )
        try:
            # Pour une feuille, image deux fois plus fine : les cotes et le cartouche restent lisibles.
            page = await browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2 if feuille else 1)
            await page.goto(url, timeout=90_000)
            await asyncio.sleep(wait)
            await _decline_cookies(page)
            if feuille:
                await _open_sheet(page, feuille)
                await asyncio.sleep(SHEET_WAIT_SECONDS)
                await _decline_cookies(page)
            await page.screenshot(path=str(dest))
        finally:
            await browser.close()
    return dest
