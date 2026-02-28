from typing import List, Dict

class Tile:
    WILDCARD = '?'

    def __init__(self, letter: str, value: int):
        self.letter = letter
        self.value = value
        self.wildcard = letter == self.WILDCARD

class LetterBag:
    def __init__(self):
        self.bag: List[Tile] = []

        # for quick lookups of values
        self.value_map: Dict[str, int] = {}

    def add_tile(self, tile: Tile):
        if tile.letter not in self.value_map:
            self.value_map[tile.letter] = tile.value

        # ensure values are consistent with previously seen tiles
        assert self.value_map[tile.letter] == tile.value

        self.bag.append(tile)