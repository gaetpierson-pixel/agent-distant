"""Vidéos de chantier : quelques images réparties sur la durée, plus le son transcrit, pour que le cerveau les « regarde »."""

from pathlib import Path

MAX_FRAMES = 12
EVERY_SECONDS = 4.0


def frames(video: Path, out_dir: Path, every: float = EVERY_SECONDS, max_frames: int = MAX_FRAMES) -> list[Path]:
    import av

    out_dir.mkdir(parents=True, exist_ok=True)
    with av.open(str(video)) as container:
        stream = container.streams.video[0]
        duration = float(container.duration or 0) / 1_000_000 or 1.0
        # Une image toutes les `every` secondes, mais jamais plus de `max_frames` : on espace sur les longues vidéos.
        step = max(every, duration / max_frames)
        saved: list[Path] = []
        next_t = 0.0
        for frame in container.decode(stream):
            t = float(frame.time or 0)
            if t + 1e-6 < next_t:
                continue
            img = frame.to_image()
            img.thumbnail((1280, 1280))
            path = out_dir / f"{video.stem}_{len(saved) + 1:02d}_{int(t)}s.jpg"
            img.save(path, "JPEG", quality=85)
            saved.append(path)
            next_t = t + step
            if len(saved) >= max_frames:
                break
    return saved


def has_audio(video: Path) -> bool:
    import av

    with av.open(str(video)) as container:
        return bool(container.streams.audio)
