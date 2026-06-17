"""Legenda karaoke queimada, estilo gamer (do print do dono).

Maiusculas, fonte pesada/condensada, branco com contorno preto grosso, e a
PALAVRA ATIVA em amarelo — palavra a palavra. Como este ffmpeg e um build minimo
(sem libass/drawtext), a legenda e desenhada com Pillow (uma imagem por estado de
palavra) e composta com o filtro `overlay` do ffmpeg (que existe).

Pillow e importado DENTRO das funcoes (dep pesada).
"""

from __future__ import annotations

import os
import subprocess

from medusacut.types import Word

W, H = 1080, 1920
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
)
FONT_SIZE = 86
STROKE = 9
COLOR_FILL = (255, 255, 255)        # branco
COLOR_ACTIVE = (255, 209, 26)       # amarelo
COLOR_STROKE = (0, 0, 0)            # contorno preto
MAX_WORDS_PER_PHRASE = 3            # poucas palavras na tela (estilo short)
MAX_GAP = 0.7                       # silencio que quebra a frase (s)
LINE_MAX_W = 980                    # largura util (margem)
Y_CENTER_FRAC = 0.60               # centro vertical da legenda (safe zone TikTok)


def group_words(
    words: list[Word],
    max_words: int = MAX_WORDS_PER_PHRASE,
    max_gap: float = MAX_GAP,
) -> list[list[Word]]:
    """Agrupa palavras em frases curtas (por quantidade e por silencio)."""
    phrases: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        if not w.text:
            continue
        if cur and (len(cur) >= max_words or w.start - cur[-1].end > max_gap):
            phrases.append(cur)
            cur = []
        cur.append(w)
    if cur:
        phrases.append(cur)
    return phrases


def word_intervals(
    phrase: list[Word], clip_start: float, clip_dur: float
) -> list[tuple[float, float]]:
    """(t0, t1) RELATIVO ao corte pra cada palavra (ativa ate a proxima)."""
    out: list[tuple[float, float]] = []
    for i, w in enumerate(phrase):
        t0 = w.start - clip_start
        t1 = (phrase[i + 1].start - clip_start) if i + 1 < len(phrase) else (w.end - clip_start)
        t0 = max(0.0, min(t0, clip_dur))
        t1 = max(t0, min(t1, clip_dur))
        out.append((t0, t1))
    return out


def _load_font(size: int):
    from PIL import ImageFont  # noqa: PLC0415

    paths = [os.environ.get("CAPTION_FONT", "")] + list(FONT_CANDIDATES)
    for p in paths:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def render_caption_images(
    words: list[Word], *, clip_start: float, clip_dur: float, out_dir: str
) -> list[tuple[float, float, str]]:
    """Gera as imagens (uma por palavra ativa) e devolve [(t0, t1, png), …]."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    os.makedirs(out_dir, exist_ok=True)
    font = _load_font(FONT_SIZE)
    states: list[tuple[float, float, str]] = []
    idx = 0
    for phrase in group_words(words):
        lines = _wrap(phrase, font)
        intervals = word_intervals(phrase, clip_start, clip_dur)
        for active in range(len(phrase)):
            t0, t1 = intervals[active]
            if t1 <= t0:
                continue
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            _draw_lines(draw, lines, font, active_word=phrase[active])
            path = os.path.join(out_dir, f"cap_{idx:03d}.png")
            img.save(path)
            states.append((t0, t1, path))
            idx += 1
    return states


def _wrap(phrase: list[Word], font) -> list[list[Word]]:
    """Quebra a frase em linhas que cabem em LINE_MAX_W."""
    lines: list[list[Word]] = []
    cur: list[Word] = []
    for w in phrase:
        trial = cur + [w]
        text = " ".join(x.text.upper() for x in trial)
        if cur and font.getlength(text) > LINE_MAX_W:
            lines.append(cur)
            cur = [w]
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _draw_lines(draw, lines: list[list[Word]], font, *, active_word: Word) -> None:
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + 14
    total_h = line_h * len(lines)
    y = int(H * Y_CENTER_FRAC - total_h / 2)
    space = font.getlength(" ")
    for line in lines:
        widths = [font.getlength(w.text.upper()) for w in line]
        line_w = sum(widths) + space * (len(line) - 1)
        x = (W - line_w) / 2
        for w, wpx in zip(line, widths):
            color = COLOR_ACTIVE if w is active_word else COLOR_FILL
            draw.text(
                (x, y), w.text.upper(), font=font, fill=color,
                stroke_width=STROKE, stroke_fill=COLOR_STROKE,
            )
            x += wpx + space
        y += line_h


def burn(clip_path: str, states: list[tuple[float, float, str]], out_path: str) -> str:
    """Compoe as imagens de legenda sobre o clipe (overlay com enable temporal)."""
    if not states:
        raise ValueError("sem estados de legenda pra queimar")

    cmd = ["ffmpeg", "-y", "-i", clip_path]
    for _, _, png in states:
        cmd += ["-i", png]

    chain = []
    label = "0:v"
    for i, (t0, t1, _png) in enumerate(states, start=1):
        nxt = f"v{i}"
        chain.append(
            f"[{label}][{i}:v]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})'[{nxt}]"
        )
        label = nxt
    filtergraph = ";".join(chain)

    cmd += [
        "-filter_complex", filtergraph,
        "-map", f"[{label}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao queimar legenda:\n{proc.stderr.strip()}")
    return out_path
