from typing import Tuple, Self

from enum import StrEnum, Enum
import numpy as np

from board import Board
from variant import GameVariant

class Game:
    def __init__(self, variant: GameVariant = GameVariant.CLASSIC):
        self.board = Board(variant)

    def score(word: str) -> int:
        return 0
    

if __name__ == '__main__':
    game = Game()