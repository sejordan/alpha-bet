from typing import List
from enum import StrEnum

from alphabet.player import Player
from alphabet.board import Board, Tile, Square

class Placement:
    def __init__(self, location: Square, tile: Tile):
        self.location = location
        self.tile = tile

class Move:
    Direction = StrEnum('Direction', ['HORIZONTAL', 'VERTICAL'])

    def __init__(self, placements: List[Placement]):
        self.placements = placements

    def score(self) -> int:
        return 5
    
    def play(self, player: Player, board: Board):
        for placement in self.placements:
            player.play_letter(placement.tile)
            board.place_tile(placement.tile, coord=placement.location.coord)
        player.add_points(self.score())

