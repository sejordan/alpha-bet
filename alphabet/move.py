from typing import List

from alphabet.player import Player
from alphabet.board import Board, Tile, Square

class Placement:
    def __init__(self, location: Square, tile: Tile):
        self.location = location
        self.tile = tile

class Move:
    def __init__(self, placements: List[Placement]):
        self.placements = placements

    # TODO: this doesn't consider cross-spelling words or modifiers
    def score(self) -> int:
        return sum([placement.tile.value for placement in self.placements])
    
    def play(self, player: Player, board: Board):
        for placement in self.placements:
            player.play_letter(placement.tile)
            board.place_tile(placement.tile, position=placement.location.position)
        player.add_points(self.score())

