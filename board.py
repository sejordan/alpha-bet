from typing import Tuple, Self

from variant import GameVariant
from modifier import Modifier, Scope


class Square:
    LETTER = 'abcdefghijklmnopqrstuvwxyz?'
    DISTRIBUTION = [9, 2, 2, 4, 12, 2, 3, 2, 9, 1, 1, 4, 2, 6, 8, 2, 1, 6, 4, 6, 4, 2, 2, 1, 2, 1, 2]
    VALUE = [1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 0, 1, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10, 0]

    def __init__(self, coord: Tuple[int, int], letter: None, modifier: Modifier = Modifier.NONE):
        self.coord = coord
        self.letter = letter
        self.modifier = modifier

    def set_modifier(self, modifier: Modifier) -> Self:
        self.modifier = modifier
        return self
    
    def set_letter(self, letter: str) -> Self:
        self.letter = letter
        return self


class Board:
    def __init__(self, variant: GameVariant):
        self.board = []
        
        # build the board
        for row in range(variant.n):
            self.board.append([])
            for col in range(variant.n):
                self.board.append(
                    Square((row, col))
                )
        
        for row in variant.modifiers:
            for col, modifier in row:
                self.board[row][col].set_modifier(modifier)