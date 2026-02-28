import pandas as pd

from alphabet.board import Board
from alphabet.variant import GameVariant

class Game:
    def __init__(self, dictionary: pd.Series, variant: GameVariant = GameVariant.CLASSIC):
        self.dictionary = dictionary
        self.board = Board(variant)
        self.bag = variant.create_bag()

    def score(self, word: str) -> int:
        if not self.valid_word(word):
            return 0
        
        

        return 0
    
    def valid_word(self, word: str) -> bool:
        return bool(self.dictionary.isin([word]).any())

if __name__ == '__main__':
    dictionary = pd.read_csv('/usr/share/dict/words', names=['word'])
    dictionary['word'] = dictionary['word'].str.lower()

    game = Game(dictionary['word'])

    print('zythem is worth', game.score('zythem'), 'points')