"""Entry-point do APP DESKTOP (roda local no PC do usuario).

Diferente da CLI pessoal: aceita arquivo LOCAL ou link, recebe a chave da OpenRouter
por --key (ou env LLM_API_KEY) e emite o progresso em **JSON por linha no stdout** —
a casca (Electron/Tauri) so le e mostra a barra. Saida final: {"type":"done",...}
ou {"type":"error",...}.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _read_cost(out_dir: str) -> dict:
    """Le o custo (USD/tokens) do manifest do motor pra mostrar no app."""
    try:
        with open(os.path.join(out_dir, "manifest.json"), encoding="utf-8") as fh:
            cost = (json.load(fh) or {}).get("cost") or {}
        return {
            "cost_usd": cost.get("cost_usd") or 0.0,
            "total_tokens": cost.get("total_tokens") or 0,
            "model": cost.get("judge_model") or cost.get("model"),
        }
    except Exception:
        return {"cost_usd": 0.0, "total_tokens": 0}


def run(argv: list[str] | None = None) -> int:
    # Empacotado (PyInstaller): impede que processos-filho (whisper/ctranslate2)
    # re-executem o app inteiro com flags do python.
    import multiprocessing  # noqa: PLC0415

    multiprocessing.freeze_support()

    p = argparse.ArgumentParser(prog="medusacut-local")
    p.add_argument("source", help="arquivo de video local OU link (Drive/YouTube/.mp4)")
    p.add_argument("--out", default="out", help="pasta de saida dos cortes")
    p.add_argument("--clips", type=int, default=3)
    # Cortes de gameplay precisam de CONTEXTO (setup -> clímax -> payoff). O motor
    # é desenhado pra 60-300s; defaults curtos faziam o corte colapsar "sem contexto".
    p.add_argument("--min-len", type=float, default=60.0)
    p.add_argument("--max-len", type=float, default=180.0)
    p.add_argument("--layout", default="facecam_top_gameplay_bottom")
    p.add_argument("--facecam", default="auto", help="auto|tl|tr|bl|br")
    p.add_argument("--no-captions", action="store_true")
    p.add_argument("--key", default=None, help="chave da OpenRouter (ou env LLM_API_KEY)")
    a = p.parse_args(argv)

    if a.key:
        os.environ["LLM_API_KEY"] = a.key

    from medusacut.pipeline import generate_clips

    def progress(frac: float, label: str) -> None:
        _emit({"type": "progress", "frac": round(float(frac), 4), "stage": label})

    is_file = os.path.exists(a.source)
    try:
        clips = generate_clips(
            a.source,
            out_dir=a.out,
            max_clips=a.clips,
            min_len=a.min_len,
            max_len=a.max_len,
            layout=a.layout,
            facecam_auto=(a.facecam == "auto"),
            facecam_corner=None if a.facecam == "auto" else a.facecam,
            captions=not a.no_captions,
            score_virality=True,
            local_source=a.source if is_file else None,
            progress=progress,
        )
    except Exception as exc:  # noqa: BLE001 — reporta limpo pro app, sem traceback
        _emit({"type": "error", "message": str(exc)})
        return 1

    # Avisa se a IA nao rodou (gancho/score vazios) — provavel chave invalida/sem
    # credito. Sem isso o usuario nao entende por que os cortes vieram "secos".
    if clips and all(not (c.hook or "").strip() for c in clips):
        _emit({
            "type": "warning",
            "message": "A IA não gerou ganchos/score — confira sua chave da OpenRouter (validade/créditos). Os cortes saíram, mas sem título.",
        })

    _emit({
        "type": "done",
        "out": os.path.abspath(a.out),
        "cost": _read_cost(a.out),
        "clips": [
            {
                "file": c.file,
                "idx": c.index,
                "start": c.start,
                "end": c.end,
                "duration_s": c.end - c.start,
                "hook": c.hook,
                "description": c.description,
                "virality_score": c.virality_score,
            }
            for c in clips
        ],
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
