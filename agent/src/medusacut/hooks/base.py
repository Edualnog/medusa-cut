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
    "Voce e um editor especialista em cortes de GAMEPLAY pro TikTok (vertical 9:16), no "
    "formato de 1 a 5 MINUTOS — cortes COM CONTEXTO, nao shorts soltos de 2s. Um bom corte "
    "tem ARCO: setup (o lance comecando a se montar), build-up/tensao, climax e payoff/reacao "
    "— precisa fazer sentido sozinho pra quem nunca viu a live. O comeco tem que prender, mas "
    "o valor esta no MOMENTO COMPLETO. Avalie pela chance real de prender e viralizar "
    "(tensao, reviravolta, clutch, fail, reacao forte). Seja honesto e calibrado: a maioria "
    "NAO viraliza; reserve notas altas (>75) pra momentos realmente fortes. Responda em "
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


def _judge_user(
    transcript_ts: str,
    game_context: str,
    *,
    win_start: float,
    win_end: float,
    anchor_s: float | None = None,
    scene_cuts: list[float] | None = None,
    min_len: float | None = None,
    max_len: float | None = None,
) -> str:
    if min_len is not None and max_len is not None:
        dur_rule = (
            f"O corte DEVE ter entre {min_len:.0f} e {max_len:.0f} segundos — escolha a "
            f"duracao pelo conteudo (um lance com contexto costuma pedir mais). "
            f"best_start_s/best_end_s devem respeitar essa faixa."
        )
    else:
        dur_rule = "Escolha o melhor inicio/fim do momento (best_start_s/best_end_s)."
    anchor_line = f"Pico de acao por volta de ~{anchor_s:.1f}s.\n" if anchor_s is not None else ""
    cuts_line = ""
    if scene_cuts:
        shown = ", ".join(f"{c:.1f}" for c in scene_cuts[:30])
        cuts_line = f"Quebras de cena (s), bons pontos pra comecar/terminar: {shown}\n"
    return (
        f"Contexto do jogo/canal: {game_context or 'desconhecido'}\n"
        f"Janela analisada: {win_start:.1f}s a {win_end:.1f}s.\n"
        f"{anchor_line}{cuts_line}"
        f'Transcricao COM TEMPO (segundos absolutos):\n"""\n{transcript_ts or "(sem fala)"}\n"""\n\n'
        "Escolha o MOMENTO COMPLETO pra virar um corte: comece onde o lance comeca a se "
        "montar (setup) e termine no payoff/reacao. NAO corte no meio de uma acao; alinhe a "
        "uma quebra de cena quando fizer sentido. Os tempos devem ficar DENTRO da janela.\n"
        "NAO comece em intro/vinheta, leitura de PATROCINIO/ANUNCIO, divulgacao de app/produto/"
        "cupom ou pedido de inscricao — se a janela abrir com isso, mova best_start_s pra DEPOIS, "
        "no comeco do conteudo real.\n"
        f"{dur_rule}\n"
        "Responda um JSON com as chaves:\n"
        '  "hook": titulo/gancho curto e punchy (max ~60 caracteres),\n'
        '  "reason": 1-2 frases dizendo POR QUE prende (cite o principio de retencao),\n'
        '  "virality_score": inteiro 0-100 calibrado,\n'
        '  "description": legenda PRONTA PRA POSTAR no TikTok (1-2 frases chamativas '
        "em PT-BR + 3-5 hashtags relevantes de games no final),\n"
        '  "best_start_s": melhor inicio (segundos absolutos, dentro da janela),\n'
        '  "best_end_s": melhor fim (segundos absolutos, dentro da janela).\n'
    )


def _hook_from_data(data: dict, lo: float, hi: float, usage) -> HookResult:
    score = _clamp(_to_float(data.get("virality_score"), 0.0), 0.0, 100.0)
    rs = _refined(data.get("best_start_s"), lo, hi)
    re_ = _refined(data.get("best_end_s"), lo, hi)
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
    transcript_ts: str,
    frame_paths: list[str],
    game_context: str = "",
    *,
    win_start: float,
    win_end: float,
    anchor_s: float | None = None,
    scene_cuts: list[float] | None = None,
    min_len: float | None = None,
    max_len: float | None = None,
) -> HookResult:
    """Etapa 2 (forte, MULTIMODAL): ve os frames + transcricao COM TEMPO da janela
    larga -> gancho/nota e ESCOLHE as fronteiras do momento completo dentro da janela.
    """
    from medusacut.llm import chat_json_multimodal

    user = _judge_user(
        transcript_ts, game_context, win_start=win_start, win_end=win_end,
        anchor_s=anchor_s, scene_cuts=scene_cuts, min_len=min_len, max_len=max_len,
    )
    data, usage = chat_json_multimodal(_JUDGE_SYSTEM, user, frame_paths)
    return _hook_from_data(data, win_start, win_end, usage)


def score_candidate(
    candidate: Candidate,
    transcript_slice: str,
    game_context: str = "",
) -> HookResult:
    """Caminho single-stage (texto, sem frames) — usado como fallback/historico."""
    from medusacut.llm import chat_json

    user = _judge_user(
        transcript_slice, game_context, win_start=candidate.start, win_end=candidate.end,
    )
    data, usage = chat_json(_SYSTEM, user)
    return _hook_from_data(data, candidate.start, candidate.end, usage)


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
