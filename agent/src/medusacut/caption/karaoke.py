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
Y_CENTER_FRAC = 0.80               # centro vertical da legenda (mais p/ baixo;
#                                    nao tampa a cena, mas acima da UI do TikTok)


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
    words: list[Word], *, clip_start: float, clip_dur: float, out_dir: str,
    y_frac: float = Y_CENTER_FRAC,
) -> list[tuple[float, float, str]]:
    """Gera as imagens (uma por palavra ativa) e devolve [(t0, t1, png), …].

    `y_frac` e o centro vertical da legenda (0=topo, 1=base)."""
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
            _draw_lines(draw, lines, font, active_word=phrase[active], y_frac=y_frac)
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


def _draw_lines(draw, lines: list[list[Word]], font, *, active_word: Word, y_frac: float = Y_CENTER_FRAC) -> None:
    ascent, descent = font.getmetrics()
    line_h = ascent + descent + 14
    total_h = line_h * len(lines)
    y = int(H * y_frac - total_h / 2)
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


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ({cmd[-1]}):\n{proc.stderr.strip()[-600:]}")


def _write_blank(path: str) -> None:
    from PIL import Image  # noqa: PLC0415

    if not os.path.exists(path):
        Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(path)


def burn(clip_path: str, states: list[tuple[float, float, str]], out_path: str) -> str:
    """Queima a legenda compondo UMA faixa transparente (alpha) e fazendo UM overlay.

    A versao antiga passava 1 input `-i` por PALAVRA pro ffmpeg + uma cadeia de N
    overlays — em corte longo (centenas de palavras) isso estourava o limite de
    inputs/descritores do ffmpeg ("Resource temporarily unavailable") e o corte saia
    SEM legenda. Aqui montamos uma faixa de legenda no tempo (concat das PNGs com
    duracao, e PNG transparente nos silencios) e compomos com um unico overlay —
    escala pra qualquer duracao, com 2 passadas baratas.
    """
    if not states:
        raise ValueError("sem estados de legenda pra queimar")

    work = os.path.dirname(states[0][2]) or os.path.dirname(out_path) or "."
    os.makedirs(work, exist_ok=True)
    blank = os.path.join(work, "_blank.png")
    _write_blank(blank)

    # 1) lista do concat: PNG de cada palavra pela sua duracao; transparente nos gaps.
    lines: list[str] = []
    prev = 0.0
    for t0, t1, png in states:
        if t0 - prev > 1e-3:  # silencio antes desta palavra -> transparente
            lines.append(f"file '{blank}'")
            lines.append(f"duration {t0 - prev:.3f}")
        lines.append(f"file '{png}'")
        lines.append(f"duration {max(0.001, t1 - t0):.3f}")
        prev = t1
    lines.append(f"file '{blank}'")  # entrada final (concat ignora a duracao do ultimo)
    list_path = os.path.join(work, "_caption_track.txt")
    with open(list_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # 2) faixa de legenda transparente (qtrle preserva alpha; ffmpeg minimo tem).
    track = os.path.join(work, "_caption_track.mov")
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-vsync", "vfr", "-pix_fmt", "argb", "-c:v", "qtrle", track,
    ])

    # 3) UM overlay da faixa sobre o clipe.
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", clip_path, "-i", track,
        "-filter_complex", "[0:v][1:v]overlay=0:0[outv]",
        "-map", "[outv]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "copy",
        out_path,
    ])
    return out_path
