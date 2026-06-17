"""Layouts de reframe 9:16.

Marco 1: `GameplayOnly` — crop central 9:16 da gameplay, sem facecam. Cada
layout sabe traduzir as dimensoes da fonte num filtro ffmpeg que produz o frame
vertical final (1080x1920).

Marco 4 adiciona `FacecamTopGameplayBottom` (facecam detectada em cima, acao
embaixo) — por isso `build` recebe o Media inteiro.
"""

from __future__ import annotations

from medusacut.types import Media

TARGET_W = 1080
TARGET_H = 1920  # 9:16


class GameplayOnly:
    """Crop central no aspecto 9:16 e escala pra 1080x1920."""

    name = "gameplay_only"

    def video_filter(self, media: Media, target_w: int = TARGET_W, target_h: int = TARGET_H) -> str:
        cw, ch, x, y = self._center_crop(media.width, media.height, target_w, target_h)
        return f"crop={cw}:{ch}:{x}:{y},scale={target_w}:{target_h}"

    @staticmethod
    def _center_crop(w: int, h: int, tw: int, th: int) -> tuple[int, int, int, int]:
        """Maior retangulo de aspecto tw:th centrado em (w x h)."""
        target_ar = tw / th
        source_ar = w / h
        if source_ar > target_ar:
            # fonte mais larga: limita pela altura
            cw = int(round(h * target_ar))
            ch = h
        else:
            # fonte mais alta/estreita: limita pela largura
            cw = w
            ch = int(round(w / target_ar))
        cw -= cw % 2  # ffmpeg/H.264 querem dimensoes pares
        ch -= ch % 2
        x = (w - cw) // 2
        y = (h - ch) // 2
        return cw, ch, x, y


# Registro de layouts disponiveis. Facecam (M4) ainda nao implementado.
_LAYOUTS = {GameplayOnly.name: GameplayOnly}


def get_layout(name: str):
    """Resolve um layout pelo nome. Cai em GameplayOnly p/ layouts ainda nao
    implementados (ex.: o default facecam do Marco 4), avisando no stderr."""
    cls = _LAYOUTS.get(name)
    if cls is None:
        import sys

        print(
            f"[medusacut] layout {name!r} ainda nao implementado; "
            f"usando 'gameplay_only' (Marco 1).",
            file=sys.stderr,
        )
        cls = GameplayOnly
    return cls()
