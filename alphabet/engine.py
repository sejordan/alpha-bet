from typing import Self, List

from alphabet.move import Move, Placement
from alphabet.game import Game, Player
from alphabet.board import Coord

class GameEngine:

    def reset(self) -> Self:
        return self
    
    def select_move(self, game: Game, player: Player) -> Move:

        # for now, play all tiles at center, only move we know
        current = Coord(row=7, col=7)

        placements: List[Placement] = []
        for tile in player.tiles:
            placements.append(
                Placement(game.board.at(current), tile)
            )
            
            current = Coord(
                row=current.row,
                col=current.col + 1
            )

        return Move(placements)
