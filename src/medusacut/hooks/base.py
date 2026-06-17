"""Gancho (hook) + score de viralizacao por corte.

>>> ESTA E A PARTE QUE DEFINE O "NIVEL OPUS CLIP". <<<
O hook e o texto/titulo de abertura e o maior fator de retencao nos 2 primeiros
segundos. Em uso pessoal o custo de LLM e irrelevante — use um modelo FORTE.

Entrada: o trecho transcrito do candidato + contexto (jogo, o que acontece).
Saida: (hook, reason, virality_score 0..100).
"""
from __future__ import annotations
from medusacut.types import Candidate


def generate_hook(
    candidate: Candidate,
    transcript_slice: str,
    game_context: str = "",
) -> tuple[str, str, float]:
    # TODO: prompt de LLM afiado p/ gameplay. Peca:
    #  - hook curto e punchy (estilo gamer, nao corporativo)
    #  - reason: por que esse momento prende
    #  - virality_score 0..100 calibrado p/ shorts de games
    # Importar o cliente de LLM DENTRO da funcao.
    raise NotImplementedError
