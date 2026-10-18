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


# Si le clic de refus échoue, on masque simplement le bandeau : rien n'est accepté pour autant.
HIDE_BANNERS = "#onetrust-consent-sdk, #onetrust-banner-sdk, [id*='cookie' i], [class*='cookie-banner' i] { display: none !important; }"


async def _decline_cookies(page) -> None:
    try:
        await page.add_style_tag(content=HIDE_BANNERS)
    except Exception:  # noqa: BLE001
        pass
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
            # Pour une feuille, image trois fois plus fine : les cotes et le cartouche restent lisibles.
            page = await browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=3 if feuille else 1)
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


def zoom(src: Path, dest: Path, zone: str) -> Path:
    """Agrandit une partie d'une capture. zone = « gauche,haut,droite,bas » en % de l'image (ex. « 50,40,100,100 »)."""
    from PIL import Image

    g, h, d, b = (float(x) for x in zone.replace(" ", "").split(","))
    if not (0 <= g < d <= 100 and 0 <= h < b <= 100):
        raise ValueError("zone attendue : gauche,haut,droite,bas en %, avec gauche < droite et haut < bas")
    img = Image.open(src)
    w, ht = img.size
    part = img.crop((int(w * g / 100), int(ht * h / 100), int(w * d / 100), int(ht * b / 100)))
    # Petite zone : on l'agrandit pour que les cotes restent lisibles à l'écran du téléphone.
    if part.width < 1600:
        ratio = 1600 / part.width
        part = part.resize((1600, round(part.height * ratio)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part.save(dest)
    return dest
