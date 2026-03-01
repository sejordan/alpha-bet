from typing import List, Dict

from alphabet.move import Move, Placement
from alphabet.game import Game, Tile, Player
from alphabet.position import Position, Axis
from alphabet import wordsmith


class GameEngine:
         
    def all_valid_moves(self, game: Game, player: Player) -> List[Move]:
        # opening move has slightly different rules, handled separately
        if game.round == 1 and game.turn == 1:
            return self.all_valid_opening_moves(game, player)

        candidates: List[Move] = []

        for row in range(game.variant.n):
            for col in range(game.variant.n):
                #print(f"Look for valid moves at position: Row={row} Col={col}")
                candidates += self.all_valid_moves_at_position(game, player, Position(row, col), Axis.HORIZONTAL)
                candidates += self.all_valid_moves_at_position(game, player, Position(row, col), Axis.VERTICAL)

        return candidates
    
    def all_valid_opening_moves(self, game: Game, player: Player) -> List[Move]:
        candidates: List[Move] = []

        center = game.variant.n // 2
        min_start = 1 + center - len(player.tiles)

        for row in range(min_start, center + 1):
            # column is fixed, we're spelling veritcally
            candidates += self.all_valid_opening_moves_at_position(game, player, Position(row, center), Axis.VERTICAL)
        
        for col in range(min_start, center + 1):
            # row is fixed, we're spelling horizontally
            candidates += self.all_valid_opening_moves_at_position(game, player, Position(center, col), Axis.HORIZONTAL)

        return candidates
    
    def all_valid_opening_moves_at_position(self, game: Game, player: Player, position: Position, axis: Axis) -> List[Move]:
        moves: List[Move] = []

        # if we're spelling vertically, starting cell is the row index, otherwise the col index
        starting_cell = position.row if axis == Axis.VERTICAL else position.col
        center = game.variant.n // 2

        # min word length is distance to the center
        # but word has to be at least 2 letters long
        min_word_length = max(2, 1 + center - starting_cell)

        # max word length is distance from starting cell to the edge of the board
        # or however many tiles the player has, whichever is shorter
        max_word_length = min(len(player.tiles), 1 + game.variant.n - starting_cell)

        for word_length in range(min_word_length, max_word_length + 1):
            template: List[None | str] = [None] * word_length
            for word in wordsmith.fill_template(game.dictionary, template):
                move = self.build_move(game, player, position, axis, word)
                # filter out illegal moves
                if move is not None and game.is_legal(move):
                    moves.append(move)

        return moves
    
    def all_valid_moves_at_position(self, game: Game, player: Player, position: Position, axis: Axis) -> List[Move]:
        candidates: List[Move] = []       

        for word_len in range(1, game.variant.n + 1):
            #print("Checking for valid words of length: ", word_len)
            # in order to be able to spell a word here of length `word_len` it can't run into another tile
            end = position.move(axis, word_len)
            if game.board.is_in_bounds(end) and game.board.at(end).tile is not None:
                continue

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
                    if game.board.is_in_bounds(neighbor):
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
            cursor = cursor.next(axis)

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
            cursor = cursor.next(axis)

        return Move(placements)
    
    def select_move(self, game: Game, player: Player) -> Move:
        candidates = self.all_valid_moves(game, player)

        print("Found", len(candidates), 'possible moves')

        # for now, just select a random play
        import random
        return random.choice(candidates)

        # # for now, play all tiles at center, only move we know
        # current = Position(row=7, col=7)

        # placements: List[Placement] = []
        # for tile in player.tiles:
        #     placements.append(Placement(game.board.at(current), tile))
        #     current = current.next(Axis.HORIZONTAL)

        # return Move(placements)
