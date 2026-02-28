import pandas as pd

from alphabet.game import Game
from alphabet.display import GameDisplay
from alphabet.engine import GameEngine


dictionary = pd.read_csv('/usr/share/dict/words', names=['word'])
dictionary['word'] = dictionary['word'].str.lower()

game = Game(dictionary['word'])
game.start()

game_engine = GameEngine()

#while game.next():
if game.next():
    print(f"Round={game.round}; Current Turn={game.active_player}")
    GameDisplay.present(game)

    move = game_engine.select_move(game, game.active_player)
    game.play(move)

GameDisplay.present(game)
print("Winner: ", "Tie Game!" if game.is_tie else (game.winner.name if game.winner else "None!"))