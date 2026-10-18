"""Transcription des vocaux, sur le PC (faster-whisper) : rien n'est envoyé à un autre service."""

import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


log = logging.getLogger(__name__)


def _cuda_dlls():
    """Sous Windows, les bibliothèques NVIDIA installées par pip (nvidia-cublas-cu12, nvidia-cudnn-cu12…)
    ne sont pas trouvées toutes seules : on ajoute chaque dossier nvidia/*/bin à la recherche des DLL."""
    if os.name != "nt":
        return
    import importlib.util

    spec = importlib.util.find_spec("nvidia")
    for root in (spec.submodule_search_locations if spec else []):
        for bin_dir in Path(root).glob("*/bin"):
            os.add_dll_directory(str(bin_dir))
            os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"


@lru_cache(maxsize=2)
def _model(name: str, device: str = "cpu"):
    from faster_whisper import WhisperModel

    # Le modèle est téléchargé une seule fois au premier vocal, puis gardé sur le PC.
    if device == "cuda":
        _cuda_dlls()
        return WhisperModel(name, device="cuda", compute_type="float16")
    return WhisperModel(name, device="cpu", compute_type="int8")


def decode(audio: Path) -> np.ndarray:
    """Son mono 16 kHz pour Whisper. Fait ici, car le décodeur de faster-whisper plante avec PyAV 15 et plus."""
    import av

    resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    chunks = []
    with av.open(str(audio)) as container:
        for frame in container.decode(audio=0):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def _run(audio, model: str, device: str, prompt):
    segments, _ = _model(model, device).transcribe(audio, language="fr", initial_prompt=prompt)
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe(audio: Path, model: str = "small", vocabulary: str = "", device: str = "cpu") -> str:
    # Les noms propres de Gaëtan (EPUR, CCTI…) guident la transcription : sinon « EPUR » devient « épure » ou « et pure ».
    prompt = f"Vocabulaire : {vocabulary}." if vocabulary else None
    samples = decode(audio)
    if device == "cuda":
        try:
            return _run(samples, model, "cuda", prompt) or "(vocal vide ou inaudible)"
        except Exception as e:  # noqa: BLE001 - pilote ou bibliothèque NVIDIA absente : on retombe sur le processeur
            log.warning("Carte graphique indisponible pour la transcription (%s) : passage sur le processeur.", e)
    return _run(samples, model, "cpu", prompt) or "(vocal vide ou inaudible)"
