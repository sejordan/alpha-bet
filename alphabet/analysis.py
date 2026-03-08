from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class WordScore:
    text: str
    score: int


@dataclass(frozen=True)
class MoveAnalysis:
    total_score: int
    direction: str
    word: str
    placements: List[Tuple[int, int, str, bool]]
    formed_words: List[WordScore]
