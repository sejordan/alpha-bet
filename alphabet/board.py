from typing import Self, List

from alphabet.variant import GameVariant
from alphabet.modifier import Modifier
from alphabet.bag import Tile
from alphabet.position import Position

class Square:
    def __init__(self, position: Position, tile: Tile | None = None,
                 modifier: Modifier = Modifier.NONE, special_display: str | None = None):
        self.position = position
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
                    Square(Position(row=row, col=col), special_display='*' if row == 7 and col == 7 else None)
                )
        
        for row, modifiers in enumerate(variant.modifiers):
            for col, modifier in modifiers:
                self.board[row][col].set_modifier(modifier)

    def get_board(self) -> List[List[Square]]:
        return self.board
    
    def is_empty(self, position: Position) -> bool:
        return not self.is_occupied(position)
    
    def is_occupied(self, position: Position) -> bool:
        return self.at(position).tile is not None
    
    def is_in_bounds(self, position: Position) -> bool:
        try:
            self.at(position)
        except IndexError:
            return False
        
        return True
    
    def at(self, position: Position) -> Square:
        return self.board[position.row][position.col]
    
    def place_tile(self, tile: Tile, position: Position):
        if tile.wildcard and tile.letter == Tile.WILDCARD:
            raise RuntimeError("Must specify wildcard letter before placing")

        self.at(position).set_tile(tile)
