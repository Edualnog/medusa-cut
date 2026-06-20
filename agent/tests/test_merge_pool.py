"""Testes da fusao pool (propostas do LLM + candidatos de energia)."""

from __future__ import annotations

from medusacut.pipeline import _merge_pool
from medusacut.types import Candidate


def test_no_proposals_returns_energy():
    energy = [Candidate(0, 60, 3.0), Candidate(100, 160, 2.0)]
    assert _merge_pool([], energy) is energy


def test_proposals_get_median_energy_score():
    energy = [Candidate(0, 60, 1.0), Candidate(100, 160, 3.0), Candidate(200, 260, 5.0)]
    props = [Candidate(500, 600, 0.0)]
    pool = _merge_pool(props, energy)
    prop = next(c for c in pool if c.start == 500)
    assert prop.score == 3.0  # mediana de [1,3,5]


def test_energy_overlapping_proposal_is_dropped():
    energy = [Candidate(90, 200, 4.0)]      # sobrepoe a proposta
    props = [Candidate(100, 180, 0.0)]
    pool = _merge_pool(props, energy)
    assert len(pool) == 1 and pool[0].start == 100  # so a proposta sobrou


def test_non_overlapping_energy_kept():
    energy = [Candidate(500, 560, 4.0)]
    props = [Candidate(100, 180, 0.0)]
    pool = _merge_pool(props, energy)
    starts = sorted(c.start for c in pool)
    assert starts == [100, 500]
