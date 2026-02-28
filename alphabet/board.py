from typing import Self, List, NamedTuple

from alphabet.variant import GameVariant
from alphabet.modifier import Modifier
from alphabet.bag import Tile


class Coord(NamedTuple):
    row: int
    col: int


class Square:
    def __init__(self, coord: Coord, tile: Tile | None = None, modifier: Modifier = Modifier.NONE, special_display: str | None = None):
        self.coord = coord
        self.tile = tile
        self.modifier = modifier
        self.special_display = special_display

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
                    Square(Coord(row=row, col=col), special_display='*' if row == 7 and col == 7 else None)
                )
        
        for row, modifiers in enumerate(variant.modifiers):
            for col, modifier in modifiers:
                self.board[row][col].set_modifier(modifier)

    def get_board(self) -> List[List[Square]]:
        return self.board
    
    def place_tile(self, tile: Tile, coord: Coord):
        if tile.wildcard and tile.letter == Tile.WILDCARD:
            raise RuntimeError("Must specify wildcard letter before placing")

        self.board[coord.row][coord.col].set_tile(tile)