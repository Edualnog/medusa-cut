"""Cliente de LLM (ganchos + score de viralizacao) — multi-provedor.

O usuario escolhe o provedor pela env `LLM_PROVIDER`:
  - "openrouter" (padrao): compativel com a API da OpenAI; devolve custo no usage.
  - "openai":             API oficial da OpenAI (chave sk-...); custo calculado aqui.
  - "anthropic":          API oficial da Anthropic (Claude, chave sk-ant-...) via SDK
                          nativo `anthropic` — a API NAO e compativel com a da OpenAI
                          (system separado, imagens em base64, sem temperature no Opus).

A chave vem de `LLM_API_KEY` (mesma env pros tres — o desktop manda a do provedor
ativo). Modelos por etapa: triagem barata -> juiz forte multimodal; defaults por
provedor, com override via `LLM_MODEL`/`LLM_MODEL_TRIAGE`/`LLM_MODEL_JUDGE`.

`openai`/`anthropic` importados DENTRO das funcoes (deps pesadas).
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass

# --- Provedores -------------------------------------------------------------
# Cada provedor define base_url (so openai-compat) e os modelos padrao por etapa.
PROVIDERS = {
    "openrouter": {
        "openai_compat": True,
        "base_url": "https://openrouter.ai/api/v1",
        "default": "openai/gpt-4o",
        "triage": "openai/gpt-4o-mini",
        "judge": "openai/gpt-4.1",
    },
    "openai": {
        "openai_compat": True,
        "base_url": "https://api.openai.com/v1",
        "default": "gpt-4o",
        "triage": "gpt-4o-mini",
        "judge": "gpt-4.1",
    },
    "anthropic": {
        "openai_compat": False,
        "base_url": None,
        "default": "claude-opus-4-8",
        "triage": "claude-haiku-4-5",
        "judge": "claude-opus-4-8",
    },
}

# Preco em USD por 1M de tokens (entrada, saida). Usado p/ estimar custo onde o
# provedor NAO devolve custo (OpenAI e Anthropic). A OpenRouter ja manda no usage.
PRICES = {
    # Anthropic
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
}

# Anthropic exige max_tokens; as saidas aqui sao JSONs curtos/medios.
ANTHROPIC_MAX_TOKENS = 8192


def provider() -> str:
    """Provedor ativo (normalizado), padrao 'openrouter'."""
    p = os.environ.get("LLM_PROVIDER", "openrouter").strip().lower()
    return p if p in PROVIDERS else "openrouter"


def _cfg() -> dict:
    return PROVIDERS[provider()]


# Defaults por etapa, resolvidos no import a partir do provedor ativo. Mantidos
# como constantes p/ nao quebrar os call-sites (hooks/pipeline importam estes nomes).
DEFAULT_MODEL = _cfg()["default"]
DEFAULT_TRIAGE_MODEL = _cfg()["triage"]
DEFAULT_JUDGE_MODEL = _cfg()["judge"]
# Compat: alguns trechos antigos liam DEFAULT_BASE_URL.
DEFAULT_BASE_URL = _cfg()["base_url"] or "https://openrouter.ai/api/v1"


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


def _api_key() -> str:
    load_dotenv()
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "LLM_API_KEY ausente — conecte sua chave do provedor de IA "
            f"({provider()}) no app (ou no .env)."
        )
    return key


def get_client():
    """Cliente OpenAI-compat (OpenRouter/OpenAI), com a chave e base_url corretos."""
    from openai import OpenAI  # noqa: PLC0415

    cfg = _cfg()
    base_url = os.environ.get("LLM_BASE_URL") or cfg["base_url"]
    return OpenAI(api_key=_api_key(), base_url=base_url)


def get_anthropic_client():
    """Cliente nativo da Anthropic (Claude)."""
    from anthropic import Anthropic  # noqa: PLC0415

    base_url = os.environ.get("LLM_BASE_URL")  # opcional (proxy)
    kwargs = {"api_key": _api_key()}
    if base_url:
        kwargs["base_url"] = base_url
    return Anthropic(**kwargs)


def chat_json(
    system: str, user: str, *, model: str | None = None, temperature: float = 0.4
) -> tuple[dict, Usage]:
    """Manda system+user (texto) e devolve (JSON, Usage com tokens+custo)."""
    model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    if provider() == "anthropic":
        return _chat_anthropic(model, system, user, [])
    return _chat_openai(model, system, user, temperature)


def chat_json_multimodal(
    system: str,
    user_text: str,
    image_paths: list[str],
    *,
    model: str | None = None,
    temperature: float = 0.3,
) -> tuple[dict, Usage]:
    """Igual ao chat_json, mas anexa imagens (keyframes) pro modelo VER a cena."""
    model = model or os.environ.get("LLM_MODEL_JUDGE", DEFAULT_JUDGE_MODEL)
    if provider() == "anthropic":
        return _chat_anthropic(model, system, user_text, image_paths)
    content: list[dict] = [{"type": "text", "text": user_text}]
    for p in image_paths:
        content.append({"type": "image_url", "image_url": {"url": image_data_uri(p)}})
    return _chat_openai(model, system, content, temperature)


def _chat_openai(model: str, system: str, content, temperature: float | None) -> tuple[dict, Usage]:
    """Caminho OpenAI-compat (OpenRouter/OpenAI)."""
    client = get_client()
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        response_format={"type": "json_object"},
    )
    # Modelos de raciocinio (o1/o3/o4…) nao aceitam temperature custom.
    if temperature is not None and not is_reasoning_model(model):
        kwargs["temperature"] = temperature
    # Só a OpenRouter aceita/usa o flag de incluir custo no usage; na OpenAI
    # oficial esse campo extra seria rejeitado.
    if provider() == "openrouter":
        kwargs["extra_body"] = {"usage": {"include": True}}
    resp = client.chat.completions.create(**kwargs)
    data = parse_json(resp.choices[0].message.content or "")
    return data, extract_usage(resp, model)


_JSON_HINT = (
    "\n\nIMPORTANTE: responda APENAS com um objeto JSON válido — sem markdown, "
    "sem cercas de código, sem texto fora do JSON."
)


def _chat_anthropic(model: str, system: str, user_text: str, image_paths: list[str]) -> tuple[dict, Usage]:
    """Caminho nativo da Anthropic (Claude). System separado; imagens em base64.

    Não passamos `temperature`: os modelos Opus 4.x rejeitam parâmetros de
    amostragem (400). O JSON é pedido via instrução no system + parser tolerante.
    """
    client = get_anthropic_client()
    content: list[dict] = [{"type": "text", "text": user_text}]
    for p in image_paths:
        content.append(_anthropic_image_block(p))
    resp = client.messages.create(
        model=model,
        max_tokens=ANTHROPIC_MAX_TOKENS,
        system=system + _JSON_HINT,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    data = parse_json(text)
    u = getattr(resp, "usage", None)
    pt = int(getattr(u, "input_tokens", 0) or 0)
    ct = int(getattr(u, "output_tokens", 0) or 0)
    return data, _usage_from_tokens(model, pt, ct, None)


def is_reasoning_model(model: str) -> bool:
    name = model.split("/")[-1].lower()
    return name.startswith(("o1", "o3", "o4"))


def image_data_uri(path: str) -> str:
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _anthropic_image_block(path: str) -> dict:
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
    }


def _price_for(model: str) -> tuple[float, float] | None:
    name = model.split("/")[-1].lower()
    return PRICES.get(name)


def _usage_from_tokens(model: str, pt: int, ct: int, cost: float | None) -> Usage:
    """Monta Usage; calcula custo pela tabela de precos se o provedor nao mandou."""
    if cost is None:
        price = _price_for(model)
        if price:
            cost = pt / 1_000_000 * price[0] + ct / 1_000_000 * price[1]
    return Usage(
        model=model, prompt_tokens=pt, completion_tokens=ct,
        total_tokens=pt + ct, cost_usd=cost, calls=1,
    )


def extract_usage(resp, model: str) -> Usage:
    """Le tokens e custo (se houver) do objeto de resposta do SDK OpenAI-compat."""
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
    cost = raw.get("cost", getattr(u, "cost", None))
    return _usage_from_tokens(model, pt, ct, cost)


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
