from typing import List, NamedTuple
import pandas as pd

from alphabet.board import Board, Tile
from alphabet.variant import GameVariant, VariantFactory



class Player:
    def __init__(self, name: str):
        self.name = name
        self.tiles: List[Tile] = []
        self.score = 0

    def add_points(self, score: int):
        self.score += score

    def add_tiles(self, tiles: List[Tile]):
        self.tiles += tiles

class Players(NamedTuple):
    a: Player
    b: Player

class Game:
    def __init__(self, dictionary: pd.Series, variant: GameVariant.Type = GameVariant.Type.CLASSIC):
        self.round = 0
        self.turn = 0
        self.variant = VariantFactory.build(variant)
        self.dictionary = dictionary
        self.board = Board(self.variant)
        self.bag = self.variant.create_bag()
        self.players = Players(
            a=Player("Player A"),
            b=Player("Player B")
        )

    def active_player(self):
        """
        Return the active player for this turn. Player A always goes first
        """
        return self.players.a if self.turn % 2 == 0 else self.players.b

    def start(self):
        # initialize the game, start each player with random selection of letters

        # player B draws first
        # players draw full starting set of tiles each
        self.players.b.add_tiles(       
            self.bag.grab_random_tiles(self.variant.starting_tiles)
        )

        self.players.a.add_tiles(       
            self.bag.grab_random_tiles(self.variant.starting_tiles)
        )

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