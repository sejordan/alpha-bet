from typing import Self

from alphabet.move import Move
from alphabet.game import Game, Player
from alphabet.board import Coord

class GameEngine:

    def reset(self) -> Self:
        return self
    
    def select_move(self, game: Game, player: Player) -> Move:

        # for now, play all tiles at center, only move we know

        return Move(
            start=game.board.at(Coord(row=7, col=7)),
            tiles=list(player.tiles),
            direction=Move.Direction.HORIZONTAL
        )
