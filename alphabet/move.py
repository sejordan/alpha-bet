from typing import List
from enum import StrEnum

from alphabet.player import Player
from alphabet.board import Board, Tile, Square, Coord

#class Placement:
#    def __init__(self, location: Square, tile: Tile):

class Move:
    Direction = StrEnum('Direction', ['HORIZONTAL', 'VERTICAL'])

    def __init__(self, start: Square, tiles: List[Tile], direction: Direction):
        self.start = start
        self.tiles = tiles
        self.direction = direction

        # placements: List[Placement]
        # self.placements = placements

    def score(self) -> int:
        return 5
    
    def play(self, player: Player, board: Board):
        location = self.start.coord

        print(self.tiles)
        for tile in self.tiles:
            print("play tile", tile)
            player.play_letter(tile)

            board.place_tile(tile, coord=location)

            # find the next open slot in the direction we're moving
            while board.is_occupied(location):
                rowmod = 1 if self.direction == Move.Direction.VERTICAL else 0
                colmod = 1 if rowmod == 0 else 0

                location = Coord(
                    row=location.row + rowmod,
                    col=location.col + colmod
                )

                # stop if reach out of bounds
                assert board.is_in_bounds(location), "Illegal move, extends beyond board's boundary!"

        player.add_points(self.score())

