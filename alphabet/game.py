from typing import List
import pandas as pd

from alphabet.board import Board, Tile
from alphabet.variant import GameVariant, VariantFactory

class Player:
    def __init__(self):
        self.tiles: List[Tile] = []
        self.score = 0

    def add_points(self, score: int):
        self.score += score

    def add_tiles(self, tiles: List[Tile]):
        self.tiles += tiles

class Game:
    def __init__(self, dictionary: pd.Series, variant: GameVariant.Type = GameVariant.Type.CLASSIC):
        self.round = 0
        self.variant = VariantFactory.build(variant)
        self.dictionary = dictionary
        self.board = Board(self.variant)
        self.bag = self.variant.create_bag()
        self.players = (
            Player(),
            Player()
        )

    def start(self):
        # initialize the game, start each player with random selection of letters
        pass

    def score(self, tiles: List[Tile]) -> int:
        return self.score_word("".join([Tile.WILDCARD if tile.wildcard else tile.letter for tile in tiles]))

    def score_word(self, word: str) -> int:
        """
        Returns the point value of the word, based on the game's bag
        """
        if not self.valid_word(word):
            return 0
        
        return sum([self.bag.get_letter_value(letter) for letter in word])
    
    def valid_word(self, word: str) -> bool:
        return bool(self.dictionary.isin([word]).any())