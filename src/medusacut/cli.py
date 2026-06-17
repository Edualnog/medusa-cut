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

    try:
        clips = generate_clips(args.url, out_dir=args.out, max_clips=args.clips)
    except RuntimeError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1

    if not clips:
        print("nenhum corte gerado.", file=sys.stderr)
        return 1

    print(f"{len(clips)} corte(s) em {args.out}/ (ver {args.out}/manifest.json):")
    for c in clips:
        print(f"  {c.file}  [{c.start:6.1f}-{c.end:6.1f}s]  score={c.score:+.2f}")
    return 0


# Alias historico — a ordem de implementacao falava em cli:main.
main = app


if __name__ == "__main__":
    raise SystemExit(app())
