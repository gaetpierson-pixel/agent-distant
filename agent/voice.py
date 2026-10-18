"""Transcription des vocaux, sur le PC (faster-whisper) : rien n'est envoyé à un autre service."""

from functools import lru_cache
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


@lru_cache(maxsize=1)
def _model(name: str):
    from faster_whisper import WhisperModel

    # Le modèle est téléchargé une seule fois au premier vocal, puis gardé sur le PC.
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


def transcribe(audio: Path, model: str = "small", vocabulary: str = "") -> str:
    # Les noms propres de Gaëtan (EPUR, CCTI…) guident la transcription : sinon « EPUR » devient « épure » ou « et pure ».
    prompt = f"Vocabulaire : {vocabulary}." if vocabulary else None
    segments, _ = _model(model).transcribe(decode(audio), language="fr", initial_prompt=prompt)
    return " ".join(s.text.strip() for s in segments).strip() or "(vocal vide ou inaudible)"
