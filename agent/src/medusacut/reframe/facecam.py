"""Auto-deteccao da caixa do facecam (rosto do streamer).

Detector de rosto rodado em frames amostrados; se um rosto aparece de forma
ESTAVEL no mesmo lugar (a webcam e fixa), devolve a caixa normalizada. Sem rosto
estavel (ex.: VTuber/handcam, ou cam do volante) -> None, e o pipeline cai pro
fallback (preset/ajuste manual, e mais a frente o juiz VLM).

Detector: **YuNet** (CNN moderno do OpenCV, robusto a angulo/luz/oculos) — bem
melhor que o Haar de 2001. O modelo (~230KB) e baixado uma vez e cacheado. Se o
YuNet nao estiver disponivel (cv2 antigo / sem rede), cai pro Haar Cascade.

cv2 importado DENTRO das funcoes (dep pesada).
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from statistics import median

# Box do rosto e menor que o quadro da webcam; expande um pouco pra emoldurar.
FACE_PAD = 1.5

# YuNet (OpenCV Zoo). Pinado por sha256 pra integridade.
_YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
_YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
_YUNET_SCORE = 0.6   # confianca minima da deteccao
_YUNET_NMS = 0.3


def _model_dir() -> str:
    d = os.environ.get("MODEL_CACHE") or os.path.join(
        os.environ.get("HF_HOME", "/tmp"), "medusacut-models"
    )
    os.makedirs(d, exist_ok=True)
    return d


def _ensure_yunet() -> str | None:
    """Caminho do .onnx do YuNet (baixa+verifica na 1a vez). None se indisponivel."""
    path = os.path.join(_model_dir(), "face_detection_yunet_2023mar.onnx")
    if os.path.exists(path) and _sha256(path) == _YUNET_SHA256:
        return path
    try:
        urllib.request.urlretrieve(_YUNET_URL, path)
    except Exception as exc:  # sem rede / URL fora: cai pro Haar
        print(f"[medusacut] YuNet indisponivel ({exc}); usando Haar", file=sys.stderr)
        return None
    if os.path.exists(path) and _sha256(path) == _YUNET_SHA256:
        return path
    print("[medusacut] YuNet baixado mas sha256 nao confere; usando Haar", file=sys.stderr)
    return None


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_facecam(
    media_path: str,
    *,
    samples: int = 40,
    min_hits_frac: float = 0.25,
) -> tuple[float, float, float, float] | None:
    """Caixa (x0,y0,x1,y1 normalizada) do facecam, ou None se nao for confiavel."""
    import cv2  # noqa: PLC0415

    cap = cv2.VideoCapture(media_path)
    if not cap.isOpened():
        return None
    try:
        w_px = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1.0
        h_px = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        step = max(1, total // samples) if total else 1

        detector = _make_detector(cv2, int(w_px), int(h_px))

        hits: list[tuple[float, float, float, float]] = []
        taken = 0
        idx = 0
        while taken < samples:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx * step)
            ok, frame = cap.read()
            if not ok:
                break
            for (x, y, fw, fh) in detector(frame):
                cx = (x + fw / 2) / w_px
                cy = (y + fh / 2) / h_px
                if _in_top_corner(cx, cy):  # 95% dos facecams ficam num canto superior
                    hits.append((cx, cy, fw / w_px, fh / h_px))
            taken += 1
            idx += 1
    finally:
        cap.release()

    return consolidate(hits, taken, min_hits_frac=min_hits_frac, pad=FACE_PAD)


def _in_top_corner(cx: float, cy: float, *, max_y: float = 0.45, side_w: float = 0.42) -> bool:
    """True se o centro do rosto cai num CANTO SUPERIOR (esq/dir). Filtra rostos de
    NPC/personagem no meio da tela e foca onde o facecam quase sempre esta — melhora
    a precisao e evita falso-positivo do gameplay."""
    return cy <= max_y and (cx <= side_w or cx >= 1.0 - side_w)


def _make_detector(cv2, w: int, h: int):
    """Devolve uma funcao frame -> [(x,y,w,h) px]. YuNet se der; senao Haar."""
    yunet_path = _ensure_yunet() if hasattr(cv2, "FaceDetectorYN") else None
    if yunet_path:
        det = cv2.FaceDetectorYN.create(
            yunet_path, "", (w, h), _YUNET_SCORE, _YUNET_NMS, 50
        )

        def run_yunet(frame):
            det.setInputSize((frame.shape[1], frame.shape[0]))
            _, faces = det.detect(frame)
            if faces is None:
                return []
            return [(float(f[0]), float(f[1]), float(f[2]), float(f[3])) for f in faces]

        return run_yunet

    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    def run_haar(frame):
        if cascade.empty():
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return [
            (float(x), float(y), float(fw), float(fh))
            for (x, y, fw, fh) in cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
        ]

    return run_haar


def consolidate(
    hits: list[tuple[float, float, float, float]],
    samples: int,
    *,
    min_hits_frac: float = 0.25,
    pad: float = FACE_PAD,
) -> tuple[float, float, float, float] | None:
    """Aglutina deteccoes (cx,cy,w,h) numa caixa estavel. Pura (testavel).

    Agrupa as deteccoes por proximidade espacial e fica com o cluster MAIS DENSO
    (a webcam e fixa -> hits do streamer formam um cluster persistente; rostos que
    aparecem dentro do gameplay sao esporadicos/espalhados). Exige que esse cluster
    seja DOMINANTE — se dois clusters tem tamanho parecido, e ambiguo -> None.
    """
    need = max(1, int(samples * min_hits_frac))
    if len(hits) < need:
        return None

    clusters = _cluster(hits, radius=0.15)
    if not clusters:
        return None
    clusters.sort(key=len, reverse=True)
    top = clusters[0]
    if len(top) < need:
        return None
    second = len(clusters[1]) if len(clusters) > 1 else 0
    if second and len(top) < 1.5 * second:
        return None  # ambiguo (dois grupos comparaveis)

    mcx = median(h[0] for h in top)
    mcy = median(h[1] for h in top)
    mw = median(h[2] for h in top) * pad
    mh = median(h[3] for h in top) * pad

    x0 = max(0.0, mcx - mw / 2)
    y0 = max(0.0, mcy - mh / 2)
    x1 = min(1.0, mcx + mw / 2)
    y1 = min(1.0, mcy + mh / 2)
    return (round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4))


def _cluster(
    hits: list[tuple[float, float, float, float]], *, radius: float
) -> list[list[tuple[float, float, float, float]]]:
    """Agrupamento espacial guloso (single-link, Chebyshev) por centro (cx,cy)."""
    clusters: list[list[tuple[float, float, float, float]]] = []
    for h in hits:
        for c in clusters:
            ccx = sum(x[0] for x in c) / len(c)
            ccy = sum(x[1] for x in c) / len(c)
            if abs(h[0] - ccx) <= radius and abs(h[1] - ccy) <= radius:
                c.append(h)
                break
        else:
            clusters.append([h])
    return clusters
