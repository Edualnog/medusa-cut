"""Testes das partes puras do LLM/hooks (sem rede)."""

from __future__ import annotations

import pytest
from pytest import approx

from medusacut.hooks.base import _clamp, _refined
from medusacut.llm import (
    Usage,
    _anthropic_image_block,
    _usage_from_tokens,
    extract_usage,
    image_data_uri,
    is_reasoning_model,
    load_dotenv,
    parse_json,
    provider,
)


def test_parse_json_plain():
    assert parse_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_json_with_code_fence():
    txt = "```json\n{\"hook\": \"vish\", \"virality_score\": 80}\n```"
    assert parse_json(txt) == {"hook": "vish", "virality_score": 80}


def test_parse_json_embedded_in_text():
    txt = 'Claro! Aqui esta: {"hook": "clutch"} — espero que ajude.'
    assert parse_json(txt) == {"hook": "clutch"}


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError):
        parse_json("nao tem json nenhum aqui")


def test_load_dotenv_sets_without_overwriting(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comentario\nMEDUSA_TEST_KEY=abc123\nVAZIO=\n")
    monkeypatch.delenv("MEDUSA_TEST_KEY", raising=False)
    load_dotenv(str(env))
    import os

    assert os.environ["MEDUSA_TEST_KEY"] == "abc123"
    # nao sobrescreve valor ja existente
    monkeypatch.setenv("MEDUSA_TEST_KEY", "ja-existe")
    load_dotenv(str(env))
    assert os.environ["MEDUSA_TEST_KEY"] == "ja-existe"


def test_usage_add_accumulates():
    s = Usage("m", 10, 5, 15, 0.001, 1) + Usage("m", 20, 10, 30, 0.002, 1)
    assert (s.prompt_tokens, s.completion_tokens, s.total_tokens, s.calls) == (30, 15, 45, 2)
    assert s.cost_usd == approx(0.003)
    assert s.model == "m"


def test_usage_add_different_models_and_partial_cost():
    s = Usage("a", 1, 1, 2, None, 1) + Usage("b", 1, 1, 2, 0.001, 1)
    assert s.model == "varios"
    assert s.cost_usd == approx(0.001)  # soma ignorando o None


def test_extract_usage_reads_tokens_and_cost():
    class U:
        def model_dump(self):
            return {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14, "cost": 0.0009}

    class R:
        usage = U()

    u = extract_usage(R(), "openai/gpt-4o")
    assert (u.prompt_tokens, u.completion_tokens, u.total_tokens) == (10, 4, 14)
    assert u.cost_usd == approx(0.0009)
    assert u.calls == 1


def test_extract_usage_handles_missing():
    class R:
        usage = None

    u = extract_usage(R(), "m")
    assert u.total_tokens == 0 and u.calls == 1 and u.cost_usd is None


def test_is_reasoning_model():
    assert is_reasoning_model("openai/o3") is True
    assert is_reasoning_model("openai/o4-mini") is True
    assert is_reasoning_model("o1-preview") is True
    assert is_reasoning_model("openai/gpt-4.1") is False
    assert is_reasoning_model("openai/gpt-4o-mini") is False  # '4o' != 'o4'


def test_image_data_uri(tmp_path):
    import base64

    p = tmp_path / "f.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0jpeg-bytes")
    uri = image_data_uri(str(p))
    assert uri.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == b"\xff\xd8\xff\xe0jpeg-bytes"


def test_provider_normalizes(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert provider() == "openrouter"  # padrao
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")  # case-insensitive
    assert provider() == "openai"
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert provider() == "anthropic"
    monkeypatch.setenv("LLM_PROVIDER", "inexistente")
    assert provider() == "openrouter"  # fallback


def test_usage_from_tokens_computes_cost_from_price_table():
    # OpenAI/Anthropic nao devolvem custo -> calculamos pela tabela.
    # gpt-4o = (2.5, 10.0) USD/1M: 1M in + 0.5M out = 2.5 + 5.0 = 7.5
    u = _usage_from_tokens("gpt-4o", 1_000_000, 500_000, None)
    assert u.cost_usd == approx(7.5)
    # claude-opus-4-8 = (5.0, 25.0): 1M in + 0.2M out = 5.0 + 5.0 = 10.0
    u2 = _usage_from_tokens("claude-opus-4-8", 1_000_000, 200_000, None)
    assert u2.cost_usd == approx(10.0)


def test_usage_from_tokens_keeps_provider_cost_when_given():
    # OpenRouter ja manda o custo -> nao recalculamos.
    u = _usage_from_tokens("openai/gpt-4o", 100, 50, 0.123)
    assert u.cost_usd == approx(0.123)


def test_usage_from_tokens_unknown_model_no_cost():
    u = _usage_from_tokens("modelo-desconhecido", 100, 50, None)
    assert u.cost_usd is None
    assert u.total_tokens == 150


def test_anthropic_image_block(tmp_path):
    import base64

    p = tmp_path / "f.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0jpeg")
    block = _anthropic_image_block(str(p))
    assert block["type"] == "image"
    assert block["source"]["type"] == "base64"
    assert block["source"]["media_type"] == "image/jpeg"
    assert base64.b64decode(block["source"]["data"]) == b"\xff\xd8\xff\xe0jpeg"


def test_clamp_and_refined():
    assert _clamp(150.0, 0.0, 100.0) == 100.0
    assert _clamp(-5.0, 0.0, 100.0) == 0.0
    assert _refined(None, 10.0, 20.0) is None
    assert _refined("nao-numero", 10.0, 20.0) is None
    assert _refined(25.0, 10.0, 20.0) == 20.0  # preso na janela
    assert _refined(15.0, 10.0, 20.0) == 15.0
