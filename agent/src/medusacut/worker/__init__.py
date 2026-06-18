"""medusacut.worker — consumidor da fila de jobs do Supabase (roda na VPS).

Mantenha leve: deps pesadas (supabase, cryptography, pipeline) sao importadas
dentro das funcoes.
"""
