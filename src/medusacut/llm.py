"""Cliente de LLM (ganchos + score de viralizacao).

Le a chave do `.env` (`LLM_API_KEY`) e fala com a OpenRouter (compativel com a
API da OpenAI). Modelo via `LLM_MODEL` (default forte). Em uso pessoal o custo e
irrelevante — use o melhor modelo.

`openai` importado DENTRO das funcoes (dep pesada).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o"


@dataclass
class Usage:
    """Consumo de uma ou mais chamadas de LLM (tokens + custo em USD)."""

    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    calls: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        cost = None
        if self.cost_usd is not None or other.cost_usd is not None:
            cost = (self.cost_usd or 0.0) + (other.cost_usd or 0.0)
        model = self.model or other.model
        if self.model and other.model and self.model != other.model:
            model = "varios"
        return Usage(
            model=model,
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=cost,
            calls=self.calls + other.calls,
        )

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "calls": self.calls,
        }


def load_dotenv(path: str = ".env") -> None:
    """Carrega pares KEY=VALUE do `.env` pro ambiente (sem sobrescrever)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def get_client():
    """Instancia o cliente OpenAI apontando pra OpenRouter, com a chave do .env."""
    from openai import OpenAI  # noqa: PLC0415

    load_dotenv()
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LLM_API_KEY ausente — coloque sua chave da OpenRouter no .env"
        )
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=key, base_url=base_url)


def chat_json(
    system: str, user: str, *, model: str | None = None, temperature: float = 0.4
) -> tuple[dict, Usage]:
    """Manda system+user e devolve (JSON, Usage com tokens+custo)."""
    client = get_client()
    model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
        # OpenRouter: devolve o custo (USD) junto do usage.
        extra_body={"usage": {"include": True}},
    )
    data = parse_json(resp.choices[0].message.content or "")
    return data, extract_usage(resp, model)


def extract_usage(resp, model: str) -> Usage:
    """Le tokens e custo (se houver) do objeto de resposta do SDK."""
    u = getattr(resp, "usage", None)
    if u is None:
        return Usage(model=model, calls=1)
    raw = {}
    try:
        raw = u.model_dump()
    except Exception:
        raw = {}
    pt = int(raw.get("prompt_tokens") or getattr(u, "prompt_tokens", 0) or 0)
    ct = int(raw.get("completion_tokens") or getattr(u, "completion_tokens", 0) or 0)
    tt = int(raw.get("total_tokens") or getattr(u, "total_tokens", 0) or (pt + ct))
    cost = raw.get("cost", getattr(u, "cost", None))
    return Usage(
        model=model, prompt_tokens=pt, completion_tokens=ct,
        total_tokens=tt, cost_usd=cost, calls=1,
    )


def parse_json(text: str) -> dict:
    """Tolerante: aceita JSON puro, com cercas ``` ou cercado de texto."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"resposta do LLM nao era JSON: {text[:200]!r}")
