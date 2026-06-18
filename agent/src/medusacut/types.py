"""Tipos compartilhados do pipeline. Modulo LEVE (so stdlib)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Media:
    """Video baixado + metadados lidos no preprocess."""

    path: str
    fps: float
    width: int
    height: int
    duration: float  # segundos


@dataclass
class ScoreTrack:
    """Uma trilha de score no tempo (saida de um sinal).

    `times[i]` e o instante (s) do centro da janela `i`; `scores[i]` seu valor
    (z-score, ja normalizado). `hop` e o passo entre janelas, em segundos.
    """

    times: list[float]
    scores: list[float]
    hop: float
    name: str = "signal"


@dataclass
class Word:
    """Uma palavra transcrita com timestamps ABSOLUTOS (s) no video."""

    text: str
    start: float
    end: float


@dataclass
class Candidate:
    """Um momento candidato a virar corte, antes do render."""

    start: float
    end: float
    score: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Clip:
    """Um corte renderizado em disco + metadados pro manifest.

    No Marco 1 `hook`/`reason`/`virality_score` ficam vazios — sao preenchidos
    no Marco 3 (hooks.generate_hook).
    """

    index: int
    start: float
    end: float
    score: float
    file: str
    hook: str = ""
    reason: str = ""
    virality_score: float | None = None
    description: str = ""  # legenda/descricao pronta pra postar (TikTok)

    def to_manifest_entry(self) -> dict:
        return {
            "index": self.index,
            "file": self.file,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "score": round(self.score, 4),
            "hook": self.hook,
            "reason": self.reason,
            "virality_score": self.virality_score,
            "description": self.description,
        }
