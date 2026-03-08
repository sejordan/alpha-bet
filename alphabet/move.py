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
    
    def play(self, player: Player, board: Board):
        for placement in self.placements:
            player.play_letter(placement.tile)
            board.place_tile(placement.tile, position=placement.location.position)


class PassMove:
    pass


class ExchangeMove:
    def __init__(self, tiles: List[Tile]):
        self.tiles = tiles
