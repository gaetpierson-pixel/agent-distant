"""Voix de synthèse, sur le PC (Piper) : rien n'est envoyé à un autre service."""

import io
import re
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

# Au-delà, la réponse vocale devient pénible à écouter : le détail reste dans le texte.
MAX_SPOKEN = 1200


def spoken_text(text: str) -> str:
    """Retire ce qui ne se lit pas à voix haute : liens, mise en forme."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_`#>|]", "", text)
    text = re.sub(r"\n\s*[-•]\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) > MAX_SPOKEN:
        cut = text.rfind(".", 0, MAX_SPOKEN)
        text = text[: cut + 1 if cut > 0 else MAX_SPOKEN] + " La suite est dans le message écrit."
    return text


@lru_cache(maxsize=1)
def _voice(name: str, folder: str):
    from piper import PiperVoice
    from piper.download_voices import download_voice

    model = Path(folder) / f"{name}.onnx"
    if not model.exists():
        # Téléchargée une seule fois, puis gardée sur le PC.
        Path(folder).mkdir(parents=True, exist_ok=True)
        download_voice(name, Path(folder))
    return PiperVoice.load(model)


def wav_to_ogg(wav_bytes: bytes, dest: Path) -> Path:
    """Telegram veut les vocaux en OGG Opus."""
    import av

    with wave.open(io.BytesIO(wav_bytes)) as w:
        rate = w.getframerate()
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    with av.open(str(dest), "w", format="ogg") as out:
        stream = out.add_stream("libopus", rate=48000)
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = rate
        resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
        for f in resampler.resample(frame) + resampler.resample(None):
            for packet in stream.encode(f):
                out.mux(packet)
        for packet in stream.encode(None):
            out.mux(packet)
    return dest


def synthesize(text: str, dest: Path, voice: str, folder: Path) -> Path:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        _voice(voice, str(folder)).synthesize_wav(spoken_text(text), w)
    return wav_to_ogg(buf.getvalue(), dest)
