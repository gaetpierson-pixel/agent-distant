"""Vues de maquettes en image : capture d'un lien Autodesk Viewer ou d'une maquette HTML, dans le navigateur Edge du PC."""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

# Seules ces adresses peuvent être ouvertes : l'agent ne navigue pas ailleurs.
ALLOWED_HOSTS = ("viewer.autodesk.com", "a360.co", "autodesk360.com")
WAIT_SECONDS = 40  # la visionneuse Autodesk charge la 3D en plusieurs dizaines de secondes


def allowed_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return urlparse(url).scheme == "https" and any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


async def capture(target: str, dest: Path, wait: int = WAIT_SECONDS) -> Path:
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
            page = await browser.new_page(viewport={"width": 1600, "height": 1000})
            await page.goto(url, timeout=90_000)
            await asyncio.sleep(wait)
            await page.screenshot(path=str(dest))
        finally:
            await browser.close()
    return dest
