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


@dataclass
class HookResult:
    hook: str
    reason: str
    virality_score: float
    refined_start: float | None = None
    refined_end: float | None = None
    usage: object | None = None  # llm.Usage da chamada


def score_candidate(
    candidate: Candidate,
    transcript_slice: str,
    game_context: str = "",
) -> HookResult:
    """Pede ao LLM o gancho, o motivo, a nota e um in/out mais justo."""
    from medusacut.llm import chat_json

    user = (
        f"Contexto do jogo/canal: {game_context or 'desconhecido'}\n"
        f"Trecho candidato: {candidate.start:.1f}s a {candidate.end:.1f}s "
        f"(duracao {candidate.duration:.1f}s).\n"
        f'Transcricao do trecho:\n"""\n{transcript_slice or "(sem fala)"}\n"""\n\n'
        "Responda um JSON com as chaves:\n"
        '  "hook": titulo/gancho curto e punchy (max ~60 caracteres),\n'
        '  "reason": 1-2 frases dizendo POR QUE prende (cite o principio de retencao),\n'
        '  "virality_score": inteiro 0-100 calibrado,\n'
        '  "best_start_s": melhor inicio (segundos absolutos, dentro do trecho),\n'
        '  "best_end_s": melhor fim (segundos absolutos, dentro do trecho).\n'
    )
    data, usage = chat_json(_SYSTEM, user)

    score = _clamp(_to_float(data.get("virality_score"), 0.0), 0.0, 100.0)
    rs = _refined(data.get("best_start_s"), candidate.start, candidate.end)
    re_ = _refined(data.get("best_end_s"), candidate.start, candidate.end)
    if rs is not None and re_ is not None and re_ - rs < 1.0:
        rs = re_ = None  # ignora refino degenerado
    return HookResult(
        hook=str(data.get("hook", "")).strip(),
        reason=str(data.get("reason", "")).strip(),
        virality_score=score,
        refined_start=rs,
        refined_end=re_,
        usage=usage,
    )


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
