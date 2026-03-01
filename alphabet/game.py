from typing import List, NamedTuple

import pandas as pd

from alphabet.player import Player
from alphabet.move import Move
from alphabet.board import Board, Tile
from alphabet.variant import GameVariant, VariantFactory


class Players(NamedTuple):
    a: Player
    b: Player

class Game:
    def __init__(self, dictionary: pd.Series, variant: GameVariant.Type = GameVariant.Type.CLASSIC):
        self.max_rounds = 30
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

    @property
    def is_over(self):
        if self.round == 0:
            return False
        
        if self.round > self.max_rounds:
            return True
        
        if len(self.players.a.tiles) == 0 or len(self.players.b.tiles) == 0:
            return True
        
        return False

    @property
    def active_player(self) -> Player:
        """
        Return the active player for this turn. Player A always goes first
        """
        return self.players.a if self.turn % 2 == 1 else self.players.b
    
    @property
    def winner(self) -> Player | None:
        if self.is_over:
            if self.players.a.score > self.players.b.score:
                return self.players.a
            elif self.players.b.score > self.players.a.score:
                return self.players.b
            # its a draw - return None

        return None
    
    @property
    def is_tie(self) -> bool:
        return self.is_over and self.winner is None

    def start(self):
        # initialize the game, start each player with random selection of letters

        # player B draws first
        # players draw full starting set of tiles each
        self.players.b.draw(self.bag, n=self.variant.starting_tiles)
        self.players.a.draw(self.bag, n=self.variant.starting_tiles)

    def next(self) -> bool:
        if self.active_player == self.players.b:
            self.round += 1
            self.turn = 1
        else:
            self.turn += 1

        return not self.is_over
    
    def play(self, move: Move):
        assert self.is_legal(move), "Illegal move!"

        # apply the move to the board
        move.play(self.active_player, self.board)

        # player tops off their tiles
        tiles_to_draw = self.variant.starting_tiles - len(self.active_player.tiles)
        self.active_player.draw(self.bag, n=tiles_to_draw)

    # TODO: check if move is legal
    def is_legal(self, move: Move) -> bool:
        if self.turn == 1 and self.round == 1:
            # must cross through center
            crosses_center = False
            center = (self.variant.n // 2)
            for placement in move.placements:
                if placement.location.position.row == center and placement.location.position.col == center:
                    crosses_center = True

            if not crosses_center:
                return False
        else:
            # TODO:
            # must touch the graph of tiles already on the board
            pass

        # TODO:
        # every word spelled must be legal
        return True

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