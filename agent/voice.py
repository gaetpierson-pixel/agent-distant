"""Transcription des vocaux, sur le PC (faster-whisper) : rien n'est envoyé à un autre service."""

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _model(name: str):
    from faster_whisper import WhisperModel

    # Le modèle est téléchargé une seule fois au premier vocal, puis gardé sur le PC.
    return WhisperModel(name, device="cpu", compute_type="int8")


def transcribe(audio: Path, model: str = "small") -> str:
    segments, _ = _model(model).transcribe(str(audio), language="fr")
    return " ".join(s.text.strip() for s in segments).strip() or "(vocal vide ou inaudible)"
