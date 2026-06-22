"""Thumbnail (capa) 9:16 do corte, estilo gamer/MrBeast — montada LOCALMENTE.

Reaproveita o que o pipeline ja tem: um frame do proprio corte (cena real), a
caixa da facecam (rosto real do streamer) e a manchete (`hook`) ja gerada pela IA.
Tudo desenhado com Pillow (mesma fonte pesada das legendas) — SEM gerar imagem por
IA, SEM custo de token, SEM depender de provedor. Saida: um .jpg ao lado do corte.

Composicao (1080x1920):
  - fundo: melhor frame do corte, em cover, escurecido + vinheta + degrade embaixo;
  - facecam: recorte do rosto num painel grande no topo, com borda/brilho (se houver);
  - seta vermelha apontando da face pra acao (so quando ha facecam);
  - manchete: caixa-alta, Impact com contorno preto grosso, linhas alternando
    branco/amarelo, na base.
Sem facecam o frame vira o protagonista (igual ao layout "foco na acao").
"""

from __future__ import annotations

import os
import subprocess

W, H = 1080, 1920
MARGIN = 56
RED = (227, 38, 38)
YELLOW = (255, 209, 26)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def build_thumbnail(
    media_path: str,
    start: float,
    end: float,
    hook_text: str,
    *,
    facecam_box: tuple[float, float, float, float] | None = None,
    out_path: str,
    cache_dir: str,
) -> str | None:
    """Gera a thumbnail do corte [start, end] em `out_path` (.jpg). Devolve o caminho
    ou None se nao der (sem frame). Nunca levanta — a thumb e um extra, nao pode
    derrubar o corte."""
    try:
        from PIL import Image  # noqa: PLC0415

        os.makedirs(cache_dir, exist_ok=True)
        frame_path = _pick_frame(media_path, start, end, facecam_box, cache_dir)
        if not frame_path:
            return None
        frame = Image.open(frame_path).convert("RGB")
        canvas = _compose(frame, hook_text, facecam_box=facecam_box)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        canvas.save(out_path, "JPEG", quality=88)
        return out_path
    except Exception as exc:  # thumb e extra: nunca derruba o corte
        import sys

        print(f"[medusacut] sem thumbnail: {exc}", file=sys.stderr)
        return None


def _pick_frame(media_path, start, end, facecam_box, cache_dir, *, n=5) -> str | None:
    """Amostra `n` frames no trecho e escolhe o mais 'expressivo': maior desvio-padrao
    na regiao da facecam (proxy de boca aberta/reacao) ou no frame todo se nao houver
    facecam. Heuristica local, sem cv2, sem token."""
    from PIL import Image, ImageStat  # noqa: PLC0415

    dur = max(0.2, end - start)
    best_path, best_score = None, -1.0
    for i in range(n):
        t = start + dur * (i + 0.5) / n
        path = os.path.join(cache_dir, f"thumb_cand_{i:02d}.jpg")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{t:.3f}", "-i", media_path,
            "-frames:v", "1", "-vf", "scale=1080:-1", "-q:v", "3", path,
        ]
        if subprocess.run(cmd, capture_output=True, text=True).returncode != 0:
            continue
        if not os.path.exists(path):
            continue
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            continue
        region = img
        if facecam_box:
            x, y, w, h = _abs_box(facecam_box, img.width, img.height)
            if w > 4 and h > 4:
                region = img.crop((x, y, x + w, y + h))
        stat = ImageStat.Stat(region.convert("L"))
        score = stat.stddev[0]  # contraste/detalhe ~ expressao
        if score > best_score:
            best_score, best_path = score, path
    return best_path


def _abs_box(box, img_w, img_h) -> tuple[int, int, int, int]:
    """Caixa da facecam -> pixels (x, y, w, h) na imagem.

    O detector (reframe.facecam.consolidate) devolve CANTOS NORMALIZADOS
    (x0, y0, x1, y1) em 0..1 — esse e o formato esperado. Como fallback aceita tambem
    pixels no formato (x, y, w, h) referenciados a 1920x1080 (uso manual/legado)."""
    if max(box) > 1.5:  # pixels (x, y, w, h) @1920x1080 — fallback
        x, y, w, h = box
        sx, sy = img_w / 1920.0, img_h / 1080.0
        return round(x * sx), round(y * sy), round(w * sx), round(h * sy)
    x0, y0, x1, y1 = box  # cantos normalizados 0..1
    # converte cada canto pra pixel e subtrai (evita erro de float em (x1-x0)*W)
    x0p, y0p = round(x0 * img_w), round(y0 * img_h)
    x1p, y1p = round(x1 * img_w), round(y1 * img_h)
    return x0p, y0p, x1p - x0p, y1p - y0p


def _compose(frame, hook_text, *, facecam_box=None):
    """Monta o canvas 1080x1920 a partir de um frame PIL ja aberto. Separado de
    build_thumbnail pra dar pra testar/prever o layout sem ffmpeg/video."""
    from PIL import Image, ImageFilter

    # --- fundo: cover + escurecido + vinheta + degrade na base ---
    bg = _cover(frame, W, H)
    bg = _saturate(bg, 1.15)
    bg = Image.blend(bg, Image.new("RGB", (W, H), BLACK), 0.24)
    bg = bg.filter(ImageFilter.GaussianBlur(1.2))
    bg.paste(_vignette(), (0, 0), _vignette())
    bg.paste(_bottom_gradient(), (0, 0), _bottom_gradient())
    canvas = bg.convert("RGB")

    # --- facecam: painel grande no topo, com brilho + borda ---
    has_face = False
    if facecam_box:
        fx, fy, fw, fh = _abs_box(facecam_box, frame.width, frame.height)
        if fw > 8 and fh > 8:
            face = frame.crop((fx, fy, fx + fw, fy + fh))
            has_face = True
            panel_w = int(W * 0.56)
            panel_h = int(panel_w * 1.18)
            face = _cover(face, panel_w, panel_h)
            px, py = MARGIN, int(H * 0.06)
            _paste_panel(canvas, face, px, py, glow=RED)

    # --- seta vermelha apontando da face pra acao (so com facecam) ---
    if has_face:
        ax = MARGIN + int(W * 0.56) - 30
        ay = int(H * 0.06) + int(W * 0.56 * 1.18) + 24
        _draw_arrow(canvas, ax, ay)

    # --- manchete: caixa-alta, Impact, contorno grosso, branco/amarelo, na base ---
    _draw_headline(canvas, (hook_text or "").strip().upper())
    return canvas


def _cover(img, tw, th):
    """Redimensiona cobrindo (tw, th) e corta o excesso (center-crop)."""
    from PIL import Image

    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def _saturate(img, factor):
    from PIL import ImageEnhance

    return ImageEnhance.Color(img).enhance(factor)


def _vignette():
    from PIL import Image, ImageDraw, ImageFilter

    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((-W * 0.35, -H * 0.18, W * 1.35, H * 1.18), fill=155)
    mask = mask.filter(ImageFilter.GaussianBlur(160))
    over = Image.new("RGBA", (W, H), (0, 0, 0, 200))
    over.putalpha(Image.eval(mask, lambda v: 200 - v))
    return over


def _bottom_gradient():
    from PIL import Image

    # rampa de alpha so na vertical: monta 1xH e estica pra W (rapido, sem loop por pixel)
    start_y = int(H * 0.52)
    col = Image.new("L", (1, H), 0)
    cpx = col.load()
    for y in range(start_y, H):
        cpx[0, y] = int(245 * (y - start_y) / (H - start_y))
    alpha = col.resize((W, H))
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad.putalpha(alpha)
    return grad


def _paste_panel(canvas, panel, x, y, *, glow=RED, radius=28, border=8):
    from PIL import Image, ImageDraw, ImageFilter

    pw, ph = panel.size
    # brilho externo
    pad = 46
    glow_img = Image.new("RGBA", (pw + pad * 2, ph + pad * 2), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    gd.rounded_rectangle((pad, pad, pad + pw, pad + ph), radius=radius,
                         fill=(*glow, 255))
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(26))
    canvas.paste(glow_img, (x - pad, y - pad), glow_img)
    # cantos arredondados na facecam
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, pw, ph), radius=radius, fill=255)
    canvas.paste(panel, (x, y), mask)
    # borda branca
    bd = ImageDraw.Draw(canvas)
    bd.rounded_rectangle((x, y, x + pw, y + ph), radius=radius, outline=WHITE,
                         width=border)


def _draw_arrow(canvas, x, y):
    """Seta vermelha curva-ish (poligono) com contorno branco, apontando p/ baixo-dir."""
    from PIL import ImageDraw

    d = ImageDraw.Draw(canvas)
    # haste (quadrado) + cabeca (triangulo) apontando p/ baixo
    shaft = [(x, y), (x + 70, y), (x + 70, y + 70), (x, y + 70)]
    head = [(x - 26, y + 60), (x + 96, y + 60), (x + 35, y + 150)]
    d.polygon(shaft, fill=RED, outline=WHITE)
    d.polygon(head, fill=RED, outline=WHITE)
    d.line(shaft + [shaft[0]], fill=WHITE, width=6)
    d.line(head + [head[0]], fill=WHITE, width=6)


def _load_font(size):
    # reusa a estrategia de fonte das legendas (Impact/Arial Black, ou bundlada)
    from medusacut.caption.karaoke import _load_font as _f

    return _f(size)


def _draw_headline(canvas, text):
    from PIL import ImageDraw

    if not text:
        return
    d = ImageDraw.Draw(canvas)
    max_w = W - MARGIN * 2
    # acha o maior tamanho de fonte que cabe em <=3 linhas
    for size in (150, 138, 126, 114, 104, 94, 86):
        font = _load_font(size)
        lines = _wrap(text, font, max_w)
        if len(lines) <= 3:
            break
    ascent, descent = font.getmetrics()
    lh = int((ascent + descent) * 1.02)
    stroke = max(6, size // 14)
    total_h = lh * len(lines)
    y = H - MARGIN - total_h
    for i, line in enumerate(lines):
        color = YELLOW if (len(lines) > 1 and i == len(lines) - 1) else WHITE
        w = d.textlength(line, font=font)
        x = (W - w) // 2
        d.text((x, y + i * lh), line, font=font, fill=color,
               stroke_width=stroke, stroke_fill=BLACK)
    return


def _wrap(text, font, max_w):
    from PIL import ImageDraw, Image

    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    words = text.split()
    lines, cur = [], []
    for word in words:
        trial = " ".join(cur + [word])
        if cur and d.textlength(trial, font=font) > max_w:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines
