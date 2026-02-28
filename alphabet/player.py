from typing import List

from alphabet.bag import LetterBag
from alphabet.board import Tile


class Player:
    def __init__(self, name: str):
        self.name = name
        self.tiles: List[Tile] = []
        self.score = 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Player(name=self.name)"

    def add_points(self, score: int):
        self.score += score

    def add_tiles(self, tiles: List[Tile]):
        self.tiles += tiles

    def play_letter(self, tile: Tile):
        self.tiles.remove(tile)

    def draw(self, bag: LetterBag, n: int):
        self.add_tiles(bag.grab_random_tiles(n))