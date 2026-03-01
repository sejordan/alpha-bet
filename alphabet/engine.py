from typing import Self, List, Dict

from alphabet.move import Move, Placement
from alphabet.game import Game, Board, Tile, Player
from alphabet.position import Position, Axis
from alphabet import wordsmith


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
    
    def all_valid_moves(self, game: Game, player: Player) -> List[Move]:
        # opening move has slightly different rules, handled separately
        if game.round == 1 and game.turn == 1:
            return self.all_valid_opening_moves(game, player)

        candidates: List[Move] = []

        for row in range(game.variant.n):
            for col in range(game.variant.n):
                candidates += self.all_valid_moves_at_position(game, player, Position(row, col), Axis.HORIZONTAL)
                candidates += self.all_valid_moves_at_position(game, player, Position(row, col), Axis.VERTICAL)

        return candidates
    
    def all_valid_opening_moves(self, game: Game, player: Player) -> List[Move]:
        candidates: List[Move] = []
        return candidates
    
    def all_valid_moves_at_position(self, game: Game, player: Player, position: Position, axis: Axis) -> List[Move]:
        candidates: List[Move] = []       

        for word_len in range(1, game.variant.n + 1):
            candidates += self.all_valid_moves_at_position_by_word_length(game, player, position, axis, word_len)

        return candidates
    
    def find_minimum_valid_word_length_at_position(self, game: Game, player: Player, position: Position, axis: Axis) -> int:
        """
        Returns the length of the shortest valid word that can be spelled with a given starting point.
        Validity is based on the word connecting to the pre-existing graph, making use
        of the tiles already on the board, in the line of the word, and the number of tiles the player has.
        Player must use at least 1 tile for the word to be valid.
        """
        min_len = 0
        tiles_needed = 0

        cursor = position
        while game.board.is_in_bounds(cursor):
            tile_under_cursor = game.board.at(cursor).tile

            # we've hit a tile- if we've already had to place any tiles,
            # then we've found our answer
            # if we haven't placed any tiles yet, then word len doesn't matter
            # because the whole row/col could be filled
            if tiles_needed > 0 and tile_under_cursor is not None:
                return min_len
            
            min_len += 1
                        
            if tile_under_cursor is None:
                tiles_needed += 1
                # we're at an empty square
                # if any of the adjacent squares have a tile on them, they we've connected to the graph
                for neighbor in cursor.neighbors():
                    neighboring_tile = game.board.at(neighbor).tile
                    if neighboring_tile is not None:
                        return min_len
                    # empty tile, and all neighbors are empty, we have to keep moving
            else:
                # nothing to check here, this square is filled so we move forward
                pass

            cursor = cursor.next(axis)

        # we've reached the boundary of the board
        # if we haven't exited already, then we never ran into the graph of placed tiles
        return 0
    
    def find_maximum_valid_word_length_at_position(self, game: Game, player: Player, position: Position, axis: Axis) -> int:
        """
        Returns the length of the longest valid word that can be spelled with a given starting point.
        Validity is based on the word connecting to the pre-existing graph, making use
        of the tiles already on the board, in the line of the word, and the number of tiles the player has
        """
        # if no valid words can be spelled here, then we already know the maximum is 0
        if self.find_minimum_valid_word_length_at_position(game, player, position, axis) == 0:
            return 0

        current_cell = position.row if axis == Axis.VERTICAL else position.col
        distance_to_edge = (game.variant.n - 1) - current_cell

        end = position.move(axis, distance_to_edge)
        end_cell = end.row if axis == Axis.VERTICAL else end.col

        # if we start in cell 7 and spell to the edge of the board (say cell 14),
        # then that's 1 + 14 - 7 = 8 letters
        # This is an _upper_ bound - we can reduce to this to the maximum of 
        theoretical_max = 1 + end_cell - current_cell

        filled_cells = 0
        cursor = position
        while game.board.is_in_bounds(cursor):
            tile_under_cursor = game.board.at(cursor).tile
            if tile_under_cursor is not None:
                filled_cells += 1

        # this is the longest word the player can actually spell
        practical_max = filled_cells + len(player.tiles)

        # but the practical max might run off the board
        # so we take the smaller of the two numbers
        return min(theoretical_max, practical_max)
    
    def all_valid_moves_at_position_by_word_length(self, game: Game, player: Player, position: Position, axis: Axis, word_length:  int) -> List[Move]:
        """
        Returns a list of valid Moves resulting in a word of the provided length,
        where the first letter is at the given position
        """
        # find minimum word length that works here
        min_word_len = self.find_minimum_valid_word_length_at_position(game, player, position, axis)

        # if min_word_len is longer than word_length, then we can't play any words
        # of word_length at this position
        # if min_word_len is 0, then no words can be played here
        if min_word_len == 0 or min_word_len > word_length:
            return []

        # now, find maximum word length that works here
        max_word_len = self.find_maximum_valid_word_length_at_position(game, player, position, axis)

        # if max_word_len is shorter than word_length then there's no
        # valid words that we can play of length word_length at this position
        if max_word_len < word_length:
            return []

        # build the template-
        # a list of blanks and filled slots
        # ie: [None, "s", None] equates to "_s_" where the blanks on either
        #     side of the s can be filled to make a word of length 3, but the "s" is fixed.
        cursor = position
        template: List[None | str] = [None] * word_length
        for i in range(word_length):
            # build a fresh template
            tile_under_cursor = game.board.at(cursor).tile
            if tile_under_cursor is not None:
                # there's already a tile at this spot, so fill in the blank
                template[i] = tile_under_cursor.letter

        candidate_words = wordsmith.fill_template(game.dictionary, template)
        selected: List[Move] = []
        # convert the words into moves
        for word in candidate_words:
            move = self.build_move(game, player, position, axis, word)
            
            # filter out illegal moves
            if move is not None and game.is_legal(move):
                selected.append(move)

        return selected

    def build_move(self, game: Game, player: Player, position: Position, axis: Axis, word: str) -> Move | None:
        placements: List[Placement] = []

        # build a clone of the player's tiles
        # TODO: probably make a class for this
        player_bag: Dict[str, List[Tile]] = {}
        for tile in player.tiles:
            if tile.letter not in player_bag:
                # we're using a list here for duplicate tiles
                player_bag[tile.letter] = []
            player_bag[tile.letter].append(Tile(tile.letter, tile.value))

        cursor = position
        for letter in word:
            tile_under_cursor = game.board.at(cursor).tile
            if tile_under_cursor is None:
                # get the tile from the player's bag
                if letter not in player_bag:
                    if Tile.WILDCARD in player_bag and len(player_bag[Tile.WILDCARD]) > 0:
                        tile = player_bag[Tile.WILDCARD].pop()
                        tile.set_letter(letter)
                        placements.append(Placement(game.board.at(cursor), tile))
                    else:
                        # we can't actually make this move...
                        return None
                elif len(player_bag[letter]) > 0:
                    tile = player_bag[letter].pop()
                    placements.append(Placement(game.board.at(cursor), tile))
                else:
                    # we can't actually make ths move...
                    return None

        return Move(placements)
    
    def select_move(self, game: Game, player: Player) -> Move:
        candidates = self.all_valid_moves(game, player)

        print(candidates)

        # for now, play all tiles at center, only move we know
        current = Position(row=7, col=7)

        placements: List[Placement] = []
        for tile in player.tiles:
            placements.append(Placement(game.board.at(current), tile))
            current = current.next(Axis.HORIZONTAL)

        return Move(placements)
