"""CLI do medusacut. `medusacut "<link>" --out out`.

Entry point: `medusacut = medusacut.cli:app` (ver pyproject). Usa argparse da
stdlib — sem framework de CLI, e uma ferramenta de uma pessoa so.
"""

from __future__ import annotations

import argparse
import sys


def app(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="medusacut",
        description="Link do YouTube -> cortes verticais 9:16 de gameplay.",
    )
    parser.add_argument("url", help="link do video do YouTube")
    parser.add_argument("--out", default="out", help="pasta de saida (default: out)")
    parser.add_argument(
        "--clips",
        type=int,
        default=3,
        help="numero maximo de cortes (default: 3)",
    )
    args = parser.parse_args(argv)

    # Import pesado adiado: mantem o startup do CLI leve.
    from medusacut.pipeline import generate_clips

    def progress(frac: float, label: str) -> None:
        end = "\n" if frac >= 1.0 else ""
        print(f"\r{int(frac * 100):3d}% — {label}        ", end=end, file=sys.stderr, flush=True)

    try:
        clips = generate_clips(
            args.url, out_dir=args.out, max_clips=args.clips, progress=progress
        )
    except RuntimeError as exc:
        print(f"\nerro: {exc}", file=sys.stderr)
        return 1

    if not clips:
        print("nenhum corte gerado.", file=sys.stderr)
        return 1

    print(f"{len(clips)} corte(s) em {args.out}/ (ver {args.out}/manifest.json):")
    for c in clips:
        vir = f" viral={c.virality_score:.0f}" if c.virality_score is not None else ""
        print(f"  {c.file}  [{c.start:6.1f}-{c.end:6.1f}s]  score={c.score:+.2f}{vir}")

    _print_cost(args.out)
    return 0


def _print_cost(out_dir: str) -> None:
    import json
    import os

    try:
        with open(os.path.join(out_dir, "manifest.json"), encoding="utf-8") as fh:
            cost = json.load(fh).get("cost")
    except (OSError, ValueError):
        cost = None
    if not cost:
        return
    usd = cost.get("cost_usd")
    money = f" · ${usd:.4f} USD" if usd is not None else " · custo n/d"
    print(
        f"LLM: {cost.get('total_tokens', 0)} tokens ({cost.get('model')}){money}",
        file=sys.stderr,
    )


# Alias historico — a ordem de implementacao falava em cli:main.
main = app


if __name__ == "__main__":
    raise SystemExit(app())
