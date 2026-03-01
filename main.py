from typing import List

from alphabet.game import Game
from alphabet.display import GameDisplay
from alphabet.engine import GameEngine

dictionary: List[str] = []
with open('/usr/share/dict/words', 'r') as fh:
    for line in fh:
        dictionary.append(line.strip())

game = Game(dictionary)
game.start()

game_engine = GameEngine()

while game.next():
#if game.next():
    print(f"Round={game.round}; Current Turn={game.active_player}")
    GameDisplay.present(game)

    move = game_engine.select_move(game, game.active_player)
    game.play(move)

GameDisplay.present(game)
print("Winner: ", "Tie Game!" if game.is_tie else (game.winner.name if game.winner else "None!"))