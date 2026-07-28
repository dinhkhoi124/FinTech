"""Minimal exact dense retrieval primitives."""

from __future__ import annotations

import numpy as np


class DenseRetrievalError(ValueError):
    pass


def validate_embeddings(values: np.ndarray, rows: int, dimension: int = 384) -> None:
    if values.shape != (rows, dimension):
        raise DenseRetrievalError(f"embedding alignment mismatch: expected {(rows, dimension)}, got {values.shape}")
    norms = np.linalg.norm(values, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-5):
        raise DenseRetrievalError("embeddings are not normalized")


def r0_scores(query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    return corpus @ query


def r1_scores(base: np.ndarray, predicted_intent: str, intent_scopes: list[list[str]], boost: float, grid: tuple[float, ...]) -> np.ndarray:
    if boost not in grid:
        raise DenseRetrievalError("lambda outside frozen grid")
    return base + np.asarray([boost if predicted_intent in scope else 0.0 for scope in intent_scopes], dtype=np.float32)


def rank(scores: np.ndarray, chunk_ids: list[str], top_k: int = 3) -> list[dict[str, float | str]]:
    if len(scores) != len(chunk_ids):
        raise DenseRetrievalError("score/chunk alignment mismatch")
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), chunk_ids[index]))[:top_k]
    return [{"chunk_id": chunk_ids[index], "score": float(scores[index])} for index in order]
