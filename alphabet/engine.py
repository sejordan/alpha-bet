from typing import Self, List

from alphabet.move import Move, Placement
from alphabet.game import Game, Board, Tile, Player
from alphabet.position import Position, Axis


class GameEngine:
    def reset(self) -> Self:
        return self
    
    def valid_starting_positions(self, game: Game) -> List[Position]:
        candidates: List[Position] = []

        # if its the opening move, there are special restrictions
        is_opening_move = game.turn == 1 and game.round == 1
        if is_opening_move:
            center = game.variant.n // 2
            low = 1 + center - game.variant.starting_tiles
            high = center + game.variant.starting_tiles - 1
            valid_range = range(low, high+1)
            candidates += [Position(row=center, col=col) for col in valid_range]
            candidates += [Position(row=row, col=center) for row in valid_range]
        else:
            candidates += [Position(row=row, col=col) for row in range(game.variant.n) for col in range(game.variant.n)]

        selected: List[Position] = []

        for position in candidates:
            if game.board.is_empty(position):
                selected.append(position)

        return selected
    
    def valid_moves(self, game: Game, tiles: List[Tile], starting_positions: List[Position]) -> List[Move]:
        candidates: List[Move] = []

        for position in starting_positions:
            candidates += self.possible_words(game.board, position, tiles)

        selected = candidates
        return selected
    
    def possible_words(self, board: Board, position: Position, tiles: List[Tile]) -> List[Move]:
        words: List[Move] = []


        
        return words
            
    def select_move(self, game: Game, player: Player) -> Move:

        candidates = self.valid_moves(
            game,
            player.tiles,
            self.valid_starting_positions(game)
        )

        print(candidates)

        # for now, play all tiles at center, only move we know
        current = Position(row=7, col=7)

        placements: List[Placement] = []
        for tile in player.tiles:
            placements.append(
                Placement(game.board.at(current), tile)
            )
            
            current = current.next(Axis.HORIZONTAL)

        return Move(placements)
