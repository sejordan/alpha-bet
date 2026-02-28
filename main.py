import pandas as pd

from alphabet.game import Game
from alphabet.board import Coord
from alphabet.display import GameDisplay    

dictionary = pd.read_csv('/usr/share/dict/words', names=['word'])
dictionary['word'] = dictionary['word'].str.lower()

game = Game(dictionary['word'])

#print('zythem is worth', game.score_word('zythem'), 'points')
print("remaining tiles:", game.bag.total_tiles)

#

#game.board.place_tile(handful[0], Coord(row=7, col=7))

game.start()

display = GameDisplay()
display.present(game)