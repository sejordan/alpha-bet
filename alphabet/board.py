from typing import Tuple, Self, List

from alphabet.variant import GameVariant
from alphabet.modifier import Modifier
from alphabet.bag import Tile


class Square:
    def __init__(self, coord: Tuple[int, int], tile: Tile | None = None, modifier: Modifier = Modifier.NONE):
        self.coord = coord
        self.tile = tile
        self.modifier = modifier

    def set_modifier(self, modifier: Modifier) -> Self:
        self.modifier = modifier
        return self
    
    def set_tile(self, tile: Tile) -> Self:
        self.tile = tile
        return self


class Board:
    def __init__(self, variant: GameVariant):
        self.board: List[List[Square]] = []
        
        # build the board
        for row in range(variant.n):
            self.board.append([])
            for col in range(variant.n):
                self.board[row].append(
                    Square((row, col))
                )
        
        for row, modifiers in enumerate(variant.modifiers):
            for col, modifier in modifiers:
                self.board[row][col].set_modifier(modifier)

                