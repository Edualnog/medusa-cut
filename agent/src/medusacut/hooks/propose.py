"""Proposta de cortes a partir da TRANSCRICAO INTEIRA (o LLM le o roteiro e escolhe).

Complementa a selecao por ENERGIA: momento forte que nao e ALTO (historia engracada,
reviravolta de RP, fail silencioso, build-up de tensao) a energia perde — mas o LLM
lendo o transcript com tempo acha. As janelas propostas entram no pool junto com as de
energia, e o juiz multimodal (que VE os frames) ranqueia tudo no final.

`parse_proposals` e pura (testavel sem LLM).
"""

from __future__ import annotations

from medusacut.types import Candidate

_SYSTEM = (
    "Voce e um editor especialista em cortes de GAMEPLAY pro TikTok (vertical, 1 a 3 MINUTOS, "
    "com CONTEXTO). Recebe a transcricao COM TEMPO de um video inteiro de uma live/gameplay e "
    "escolhe os MELHORES momentos pra virar cortes. Um bom corte tem ARCO completo (setup -> "
    "tensao/build-up -> climax -> payoff/reacao) e faz sentido sozinho pra quem nunca viu a live. "
    "Priorize: reviravolta, clutch, fail epico, treta/discussao, historia engracada, reacao forte, "
    "momento de tensao. Seja seletivo: poucos momentos sao realmente bons. "
    "NUNCA escolha intro/vinheta de abertura, leitura de PATROCINIO/ANUNCIO, divulgacao de "
    "app/produto/cupom, pedido de inscricao/like, ou recapitulacao — comece no CONTEUDO real "
    "(acao/gameplay/treta). Se um bom momento vier logo apos um anuncio, comece DEPOIS do anuncio. "
    "Responda SOMENTE JSON."
)


def _user(transcript_ts: str, game_context: str, video_dur: float, count: int,
          min_len: float, max_len: float) -> str:
    return (
        f"Contexto do jogo/canal: {game_context or 'desconhecido'}\n"
        f"Duracao do video: {video_dur:.0f}s.\n"
        f'Transcricao COM TEMPO (segundos absolutos):\n"""\n{transcript_ts or "(sem fala)"}\n"""\n\n'
        f"Proponha ate {count} momentos pra virar cortes. Cada corte deve ter entre "
        f"{min_len:.0f} e {max_len:.0f} segundos, comecar no setup e terminar no payoff, e os "
        f"tempos devem ficar dentro de [0, {video_dur:.0f}]. NAO proponha momentos fracos so pra "
        f"completar a lista. Responda um JSON:\n"
        '  {"clips": [ {"start_s": numero, "end_s": numero, "reason": "por que prende (1 frase)"}, ... ] }'
    )


def propose_candidates(
    transcript_ts: str,
    game_context: str,
    video_dur: float,
    *,
    count: int = 6,
    min_len: float = 60.0,
    max_len: float = 180.0,
    model: str | None = None,
):
    """Pede ao LLM (texto) janelas de corte a partir do transcript. Devolve
    (list[Candidate], Usage). Falha de LLM -> ([], None) (cai pro pool de energia)."""
    import os

    from medusacut.llm import DEFAULT_JUDGE_MODEL, chat_json

    if not (transcript_ts or "").strip():
        return [], None
    model = model or os.environ.get("LLM_MODEL_JUDGE", DEFAULT_JUDGE_MODEL)
    user = _user(transcript_ts, game_context, video_dur, count, min_len, max_len)
    try:
        data, usage = chat_json(_SYSTEM, user, model=model, temperature=0.4)
    except Exception:
        return [], None
    return parse_proposals(data, video_dur, min_len=min_len, max_len=max_len, max_count=count), usage


def parse_proposals(
    data: dict,
    video_dur: float,
    *,
    min_len: float,
    max_len: float,
    max_count: int,
) -> list[Candidate]:
    """Interpreta a resposta do LLM em Candidates validos. Pura.

    - clampa [start,end] em [0, video_dur];
    - forca a duracao pra [min_len, max_len] (cresce em torno do centro);
    - descarta degenerados e ordena por inicio; dedup de quase-iguais; corta em max_count.
    """
    items = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[Candidate] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            s = float(it.get("start_s"))
            e = float(it.get("end_s"))
        except (TypeError, ValueError):
            continue
        s, e = _fit_window(s, e, video_dur, min_len, max_len)
        if e - s < min(min_len, max_len) - 1.0:
            continue
        out.append(Candidate(start=round(s, 2), end=round(e, 2), score=0.0))
    out.sort(key=lambda c: c.start)
    return _dedupe(out)[:max_count]


def _fit_window(s: float, e: float, dur: float, min_len: float, max_len: float):
    """Clampa em [0,dur] e forca duracao em [min_len,max_len] crescendo no centro."""
    s = max(0.0, min(s, dur))
    e = max(0.0, min(e, dur))
    if e < s:
        s, e = e, s
    length = e - s
    center = (s + e) / 2.0
    if length < min_len:
        s, e = center - min_len / 2.0, center + min_len / 2.0
    elif length > max_len:
        s, e = center - max_len / 2.0, center + max_len / 2.0
    if s < 0.0:
        s, e = 0.0, min(dur, e - s)
    if e > dur:
        e, s = dur, max(0.0, dur - (e - s))
    return s, e


def _dedupe(cands: list[Candidate], *, iou: float = 0.6) -> list[Candidate]:
    """Remove propostas que se sobrepoem muito (mantem a primeira por ordem de inicio)."""
    kept: list[Candidate] = []
    for c in cands:
        if any(_overlap_frac(c, k) >= iou for k in kept):
            continue
        kept.append(c)
    return kept


def _overlap_frac(a: Candidate, b: Candidate) -> float:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    union = (a.end - a.start) + (b.end - b.start) - inter
    return inter / union if union > 0 else 0.0
