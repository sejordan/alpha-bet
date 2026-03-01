from typing import Self, List

from alphabet.move import Move, Placement
from alphabet.game import Game, Board, Tile, Player
from alphabet.position import Position, Axis


class GameEngine:
    def reset(self) -> Self:
        return self
    
    def next_empty_position(self, board: Board, position: Position, axis: Axis) -> Position | None:
        cursor = position.next(axis)
        while board.is_in_bounds(cursor) and board.is_occupied(cursor):
            cursor = cursor.next(axis)
        
        # we either ran off the board or found an empty position
        if board.is_in_bounds(cursor):
            return cursor
        
        # there are no more empty forward-positions on this axis
        return None
    
    def can_start_at_position(self, board: Board, position: Position, tile_count: int) -> bool:
        """
        Checks if a position is valid for starting a new word.
        If we can connect to the graph with the number of tiles we have, then it is valid.
        """
        # check that position is in bounds
        if not board.is_in_bounds(position):
            return False
        
        if board.is_occupied(position):
            # if the position is occupied that means we can definitely connect to the graph
            # but we still need to make sure we can actually place tiles on this line
            empty_pos_on_h = self.next_empty_position(board, position, Axis.HORIZONTAL)
            empty_pos_on_v = self.next_empty_position(board, position, Axis.VERTICAL)

            if empty_pos_on_h is None and empty_pos_on_v is None:
                # moving forward, the board is already filled from
                # this starting position along both axes, so there is no room to play
                return False

            # at least one of the axes is playable
            return True
        
        # the position is empty, but we can still play starting from here if we can
        # connect to the graph with an adjacent position
        current = position
        for _ in range(tile_count):
            if board.is_occupied(current):
                # we ran straight into an occupied square!
                return True
            for pos in current.neighbors():
                if board.is_in_bounds(pos) and board.is_occupied(pos):
                    return True
            current = current.next(Axis.HORIZONTAL)

        current = position
        for _ in range(tile_count): 
            if board.is_occupied(current):
                # we ran straight into an occupied square!
                return True
            for pos in current.neighbors():
                if board.is_in_bounds(pos) and board.is_occupied(pos):
                    return True
            current = current.next(Axis.VERTICAL)

        # we can't reach the graph from this starting position
        return False
    
    def valid_starting_positions(self, game: Game, tile_count: int) -> List[Position]:
        candidates: List[Position] = []

        # if its the opening move, there are special restrictions
        is_opening_move = game.turn == 1 and game.round == 1
        if is_opening_move:
            center = game.variant.n // 2
            low = 1 + center - game.variant.starting_tiles
            # word must cross the center square
            # word can start before the center square, but not after it
            valid_range = range(low, center+1)
            candidates += [Position(row=center, col=col) for col in valid_range]
            candidates += [Position(row=row, col=center) for row in valid_range]

            # all candidates are valid because the board is currently empty
            return candidates
        else:
            candidates += [Position(row=row, col=col) for row in range(game.variant.n) for col in range(game.variant.n)]

        return [p for p in candidates if self.can_start_at_position(game.board, p, tile_count)]
    
    def valid_moves(self, game: Game, tiles: List[Tile], starting_positions: List[Position]) -> List[Move]:
        candidates: List[Move] = []

        for position in starting_positions:
            candidates += self.possible_words(game, position, tiles, Axis.HORIZONTAL)
            candidates += self.possible_words(game, position, tiles, Axis.VERTICAL)

        selected = candidates
        return selected
    
    def possible_words(self, game: Game, position: Position, tiles: List[Tile], axis: Axis) -> List[Move]:
        candidates: List[Move] = []

        # what's the longest word we could possible place at this position?

        index = position.row if axis == Axis.VERTICAL else position.col
        longest_possible_word_len = game.variant.n - index

        print(f"Longest word you could place, starting at cell={index} along axis={axis.name}: {longest_possible_word_len}")

        for word_len in range(2, longest_possible_word_len+1):
            word_template: List[None | str] = [None] * word_len
            
            cursor = position
            tiles_remaining = len(tiles)
            letter_index = 0

            while letter_index < word_len and tiles_remaining > 0 and game.board.is_in_bounds(cursor):
                tile_under_cursor = game.board.at(cursor).tile
                if tile_under_cursor is None:
                    # our word template will be empty at this slot (we'll have to use a tile to fill it)
                    tiles_remaining -= 1
                else:
                    # this slot is occupied, we can't place a tile on it
                    word_template[letter_index] = tile_under_cursor.letter
                cursor = cursor.next(axis)
                letter_index += 1

            print(word_template)

        # todo: filter candidates
        
        return candidates
            
    def select_move(self, game: Game, player: Player) -> Move:
        candidates = self.valid_moves(
            game,
            player.tiles,
            self.valid_starting_positions(game, len(player.tiles))
        )

        print(candidates)

        # for now, play all tiles at center, only move we know
        current = Position(row=7, col=7)

        placements: List[Placement] = []
        for tile in player.tiles:
            placements.append(Placement(game.board.at(current), tile))
            current = current.next(Axis.HORIZONTAL)

        return Move(placements)
