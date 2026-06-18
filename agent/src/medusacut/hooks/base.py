"""Gancho (hook) + score de viralizacao por corte.

>>> ESTA E A PARTE QUE DEFINE O "NIVEL OPUS CLIP". <<<
O hook e o texto/titulo de abertura e o maior fator de retencao nos 2 primeiros
segundos. Em uso pessoal o custo de LLM e irrelevante — use um modelo FORTE.

Entrada: o trecho transcrito do candidato + contexto (jogo, o que acontece).
Saida: (hook, reason, virality_score 0..100) — e, no caminho rico, um in/out mais
justo pra apertar o corte no "punchline".
"""
from __future__ import annotations

from dataclasses import dataclass

from medusacut.types import Candidate

_SYSTEM = (
    "Voce e um editor especialista em shorts virais de GAMEPLAY pro TikTok (9:16). "
    "Avalia um trecho pela chance real de prender e viralizar, com base em principios "
    "de retencao de short-form: gancho forte nos 2 primeiros segundos, pico emocional, "
    "payoff claro, e ser 'loopavel'. Seja honesto e calibrado: a maioria dos trechos NAO "
    "viraliza; reserve notas altas (>75) pra momentos realmente fortes. Responda em "
    "portugues do Brasil, tom gamer (nao corporativo). Responda SOMENTE JSON."
)

_JUDGE_SYSTEM = (
    _SYSTEM
    + " Voce TAMBEM recebe alguns frames do trecho — use o que ACONTECE na tela "
    "(acao, perigo, reacao, resultado), nao so a fala, pra julgar. Gameplay e visual."
)

_TRIAGE_SYSTEM = (
    "Voce tria trechos de gameplay por potencial viral pra TikTok, rapido e barato. "
    "Olhe a transcricao e estime a chance de prender/viralizar. Calibrado: poucos sao bons. "
    'Responda SOMENTE JSON: {"virality_score": inteiro 0-100}.'
)


@dataclass
class HookResult:
    hook: str
    reason: str
    virality_score: float
    description: str = ""  # legenda pronta pra postar (TikTok), com hashtags
    refined_start: float | None = None
    refined_end: float | None = None
    usage: object | None = None  # llm.Usage da chamada


def _judge_user(candidate: Candidate, transcript_slice: str, game_context: str) -> str:
    return (
        f"Contexto do jogo/canal: {game_context or 'desconhecido'}\n"
        f"Trecho candidato: {candidate.start:.1f}s a {candidate.end:.1f}s "
        f"(duracao {candidate.duration:.1f}s).\n"
        f'Transcricao do trecho:\n"""\n{transcript_slice or "(sem fala)"}\n"""\n\n'
        "Responda um JSON com as chaves:\n"
        '  "hook": titulo/gancho curto e punchy (max ~60 caracteres),\n'
        '  "reason": 1-2 frases dizendo POR QUE prende (cite o principio de retencao),\n'
        '  "virality_score": inteiro 0-100 calibrado,\n'
        '  "description": legenda PRONTA PRA POSTAR no TikTok (1-2 frases chamativas '
        "em PT-BR + 3-5 hashtags relevantes de games no final),\n"
        '  "best_start_s": melhor inicio (segundos absolutos, dentro do trecho),\n'
        '  "best_end_s": melhor fim (segundos absolutos, dentro do trecho).\n'
    )


def _hook_from_data(data: dict, candidate: Candidate, usage) -> HookResult:
    score = _clamp(_to_float(data.get("virality_score"), 0.0), 0.0, 100.0)
    rs = _refined(data.get("best_start_s"), candidate.start, candidate.end)
    re_ = _refined(data.get("best_end_s"), candidate.start, candidate.end)
    if rs is not None and re_ is not None and re_ - rs < 1.0:
        rs = re_ = None  # ignora refino degenerado
    return HookResult(
        hook=str(data.get("hook", "")).strip(),
        reason=str(data.get("reason", "")).strip(),
        virality_score=score,
        description=str(data.get("description", "")).strip(),
        refined_start=rs,
        refined_end=re_,
        usage=usage,
    )


def triage_score(candidate: Candidate, transcript_slice: str, game_context: str = ""):
    """Etapa 1 (barata, so texto): nota rapida 0-100. Devolve (score, Usage)."""
    import os

    from medusacut.llm import DEFAULT_TRIAGE_MODEL, chat_json

    user = (
        f"Contexto: {game_context or 'desconhecido'}. "
        f'Trecho ({candidate.duration:.0f}s). Transcricao:\n"""\n{transcript_slice or "(sem fala)"}\n"""'
    )
    model = os.environ.get("LLM_MODEL_TRIAGE", DEFAULT_TRIAGE_MODEL)
    data, usage = chat_json(_TRIAGE_SYSTEM, user, model=model, temperature=0.2)
    return _clamp(_to_float(data.get("virality_score"), 0.0), 0.0, 100.0), usage


def judge_candidate(
    candidate: Candidate,
    transcript_slice: str,
    frame_paths: list[str],
    game_context: str = "",
) -> HookResult:
    """Etapa 2 (forte, MULTIMODAL): ve os frames + transcricao -> gancho/nota/refino."""
    from medusacut.llm import chat_json_multimodal

    user = _judge_user(candidate, transcript_slice, game_context)
    data, usage = chat_json_multimodal(_JUDGE_SYSTEM, user, frame_paths)
    return _hook_from_data(data, candidate, usage)


def score_candidate(
    candidate: Candidate,
    transcript_slice: str,
    game_context: str = "",
) -> HookResult:
    """Caminho single-stage (texto, sem frames) — usado como fallback/historico."""
    from medusacut.llm import chat_json

    user = _judge_user(candidate, transcript_slice, game_context)
    data, usage = chat_json(_SYSTEM, user)
    return _hook_from_data(data, candidate, usage)


def generate_hook(
    candidate: Candidate,
    transcript_slice: str,
    game_context: str = "",
) -> tuple[str, str, float]:
    """Interface historica: (hook, reason, virality_score)."""
    r = score_candidate(candidate, transcript_slice, game_context)
    return r.hook, r.reason, r.virality_score


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _refined(value, lo: float, hi: float) -> float | None:
    """Tempo refinado preso na janela [lo, hi]; None se nao for numero."""
    if value is None:
        return None
    try:
        return _clamp(float(value), lo, hi)
    except (TypeError, ValueError):
        return None
