from typing import List, Dict, Self, NamedTuple
import numpy as np


class LetterConfig(NamedTuple):
    quantity: int
    value: int

class Tile:
    WILDCARD = '?'

    def __init__(self, letter: str, value: int):
        self.letter = letter
        self.value = value
        self.wildcard = letter == self.WILDCARD

    def __str__(self):
        return f"{self.letter.upper()}_{self.value}"
    
    def __repr__(self):
        return f"Tile(letter={self.letter}, value={self.value})"
        
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tile):
            if self.wildcard and other.wildcard:
                return True
        
            if self.letter == other.letter:
                return True
            
        if isinstance(other, str):
            if self.wildcard or self.letter == other:
                return True
        
        return False
    
    def set_letter(self, letter: str):
        assert self.wildcard
        self.letter = letter

class LetterBag:
    def __init__(self, config: Dict[str, LetterConfig]):
        self.config = config
        self.total_tiles = 0

        # build maps for quicker lookups
        self.counts: Dict[str, int] = {}
        self.values: Dict[str, int] = {}

        for letter in self.config:
            self.counts[letter] = self.config[letter].quantity
            self.values[letter] = self.config[letter].value
            self.total_tiles += self.counts[letter]

    def add_tile(self, tile: Tile) -> Self:
        """
        Put a tile back into the letter bag
        """
        # make sure the tile belongs to this game...
        assert self.counts[tile.letter] < self.get_total_quantity(tile.letter), f"bag already contains all `{tile.letter}` tiles!"
        assert self.values[tile.letter] == tile.value, "tile face score does not match provided configuration for this letter bag!"

        self.counts[tile.letter] += 1
        self.total_tiles += 1
        return self
    
    def build_tile(self, letter: str) -> Tile:
        return Tile(letter, self.values[letter])
    
    def remaining_tiles(self) -> List[Tile]:
        """
        Dynamically builds a bag of remaining tiles
        """
        full: List[Tile] = []
        for letter in self.counts:
            full += [Tile(letter=letter, value=self.values[letter]) for _ in range(self.counts[letter])]
        return full
    
    # TODO: memoize the bag, manage cache validity
    def grab_random_tiles(self, n: int) -> List[Tile]:
        """
        Selects up to n random tiles from the bag
        """
        bag = self.remaining_tiles()

        # if requested amount is greater than or equal to
        # the quantity of tiles remaining, just give the whole bag
        if n >= len(bag):
            selected_tiles = bag
        else:
            selected_tiles = [bag[int(x)] for x in np.random.choice(len(bag), size=n, replace=False)]

        for tile in selected_tiles:
            self.counts[tile.letter] -= 1
            self.total_tiles -= 1

        return selected_tiles

    def get_total_quantity(self, letter: str) -> int:
        """
        Returns the original quantity for the letter
        """
        return self.config[letter].quantity
    
    def get_remaining_quantity(self, letter: str) -> int:
        """
        Returns the quantity of remaining tiles for the letter
        """
        return self.counts[letter]

    def get_letter_value(self, letter: str) -> int:
        """
        Returns the face value of the letter's tile
        """       
        return self.values[letter]