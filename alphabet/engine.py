from typing import List, Dict

from alphabet.game import Game, Tile, Player
from alphabet.move import Move, Placement, ExchangeMove, PassMove
from alphabet.position import Position, Axis
from alphabet.strategy import ActionStrategy, GreedyImmediateScoreStrategy
from alphabet import wordsmith


class GameEngine:
    def __init__(self, strategy: ActionStrategy | None = None) -> None:
        self.strategy = strategy if strategy is not None else GreedyImmediateScoreStrategy()

    def all_valid_moves_codex(self, game: Game, player: Player) -> List[Move]:
        """
        Alternative move generator optimized to reduce repeated board scans and
        repeated player-rack cloning.
        """
        # Opening move logic is already bounded and comparatively cheap.
        if game.round == 1 and game.turn == 1:
            return self.all_valid_opening_moves(game, player)

        anchors = self._anchors_codex(game)
        if len(anchors) == 0:
            return []

        rack_tiles, wildcard_tiles = self._index_player_tiles_codex(player)
        candidates: List[Move] = []
        horizontal_starts = self._candidate_starts_codex(game, player, anchors, Axis.HORIZONTAL)
        vertical_starts = self._candidate_starts_codex(game, player, anchors, Axis.VERTICAL)

        for start in horizontal_starts:
            candidates += self._all_valid_moves_at_position_codex(
                game=game,
                player=player,
                start=start,
                axis=Axis.HORIZONTAL,
                rack_tiles=rack_tiles,
                wildcard_tiles=wildcard_tiles,
            )

        for start in vertical_starts:
            candidates += self._all_valid_moves_at_position_codex(
                game=game,
                player=player,
                start=start,
                axis=Axis.VERTICAL,
                rack_tiles=rack_tiles,
                wildcard_tiles=wildcard_tiles,
            )

        deduped: List[Move] = []
        seen: set[tuple] = set()
        for move in candidates:
            sig = self._move_signature_codex(move)
            if sig in seen:
                continue
            seen.add(sig)
            deduped.append(move)

        return deduped

    def _anchors_codex(self, game: Game) -> List[Position]:
        anchors: List[Position] = []
        for row in range(game.variant.n):
            for col in range(game.variant.n):
                position = Position(row, col)
                if game.board.at(position).tile is not None:
                    continue

                connected = False
                for neighbor in position.neighbors():
                    if game.board.is_in_bounds(neighbor) and game.board.at(neighbor).tile is not None:
                        connected = True
                        break

                if connected:
                    anchors.append(position)

        return anchors

    def _candidate_starts_codex(
        self,
        game: Game,
        player: Player,
        anchors: List[Position],
        axis: Axis,
    ) -> List[Position]:
        rack_size = len(player.tiles)
        if rack_size == 0:
            return []

        selected: Dict[tuple[int, int], Position] = {}

        for anchor in anchors:
            cursor = anchor
            empty_slots = 1  # anchor itself is empty and requires one placed tile

            while game.board.is_in_bounds(cursor) and empty_slots <= rack_size:
                # canonical full-word start: preceding square cannot be occupied
                previous = cursor.prev(axis)
                if (not game.board.is_in_bounds(previous)) or game.board.at(previous).tile is None:
                    selected[(cursor.row, cursor.col)] = Position(cursor.row, cursor.col)

                cursor = cursor.prev(axis)
                if not game.board.is_in_bounds(cursor):
                    break

                if game.board.at(cursor).tile is None:
                    empty_slots += 1

        return list(selected.values())

    def _index_player_tiles_codex(self, player: Player) -> tuple[Dict[str, List[Tile]], List[Tile]]:
        rack_tiles: Dict[str, List[Tile]] = {}
        wildcard_tiles: List[Tile] = []
        for tile in player.tiles:
            if tile.wildcard:
                wildcard_tiles.append(tile)
            else:
                if tile.letter not in rack_tiles:
                    rack_tiles[tile.letter] = []
                rack_tiles[tile.letter].append(tile)
        return rack_tiles, wildcard_tiles

    def _move_signature_codex(self, move: Move) -> tuple:
        normalized = sorted([
            (
                placement.location.position.row,
                placement.location.position.col,
                placement.tile.letter,
                placement.tile.wildcard,
            )
            for placement in move.placements
        ])
        return tuple(normalized)

    def _all_valid_moves_at_position_codex(
        self,
        game: Game,
        player: Player,
        start: Position,
        axis: Axis,
        rack_tiles: Dict[str, List[Tile]],
        wildcard_tiles: List[Tile],
    ) -> List[Move]:
        min_word_len = self.find_minimum_valid_word_length_at_position(game, player, start, axis)
        if min_word_len == 0:
            return []

        max_word_len = self.find_maximum_valid_word_length_at_position(game, player, start, axis)
        if max_word_len < min_word_len:
            return []

        candidates: List[Move] = []
        template: List[None | str] = []
        path: List[Position] = []
        cursor = start

        for word_len in range(1, max_word_len + 1):
            if not game.board.is_in_bounds(cursor):
                break

            square = game.board.at(cursor)
            path.append(cursor)
            template.append(square.tile.letter if square.tile is not None else None)

            if word_len >= min_word_len:
                # Words cannot terminate immediately before an occupied square.
                end_next = cursor.next(axis)
                if (not game.board.is_in_bounds(end_next)) or game.board.at(end_next).tile is None:
                    candidate_words = wordsmith.fill_template(game.dictionary, template)
                    for word in candidate_words:
                        move = self._build_move_codex(
                            game=game,
                            path=path,
                            template=template,
                            rack_tiles=rack_tiles,
                            wildcard_tiles=wildcard_tiles,
                            word=word,
                        )
                        if move is not None and game.is_legal(move):
                            candidates.append(move)

            cursor = cursor.next(axis)

        return candidates

    def _build_move_codex(
        self,
        game: Game,
        path: List[Position],
        template: List[None | str],
        rack_tiles: Dict[str, List[Tile]],
        wildcard_tiles: List[Tile],
        word: str,
    ) -> Move | None:
        placements: List[Placement] = []
        consumed_by_letter: Dict[str, int] = {}
        consumed_wildcards = 0

        for index, required_letter in enumerate(template):
            # Board already contains this tile; no placement required.
            if required_letter is not None:
                continue

            letter = word[index]
            used_letter_count = consumed_by_letter.get(letter, 0)
            available_tiles = rack_tiles.get(letter, [])

            if used_letter_count < len(available_tiles):
                source_tile = available_tiles[used_letter_count]
                consumed_by_letter[letter] = used_letter_count + 1
                tile = Tile(source_tile.letter, source_tile.value)
            elif consumed_wildcards < len(wildcard_tiles):
                source_tile = wildcard_tiles[consumed_wildcards]
                consumed_wildcards += 1
                tile = Tile(source_tile.letter, source_tile.value)
                tile.set_letter(letter)
            else:
                return None

            placements.append(Placement(game.board.at(path[index]), tile))

        return Move(placements)
         
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
    
    def select_action(self, game: Game, player: Player, verbose: bool = True) -> Move | ExchangeMove | PassMove:
        candidates = self.all_valid_moves_codex(game, player)

        if verbose:
            print("Found", len(candidates), 'possible moves')

        return self.strategy.select_action(
            engine=self,
            game=game,
            player=player,
            candidates=candidates,
        )

    def select_move(self, game: Game, player: Player) -> Move | None:
        action = self.select_action(game, player)
        if isinstance(action, Move):
            return action
        return None

        # # for now, play all tiles at center, only move we know
        # current = Position(row=7, col=7)

        # placements: List[Placement] = []
        # for tile in player.tiles:
        #     placements.append(Placement(game.board.at(current), tile))
        #     current = current.next(Axis.HORIZONTAL)

        # return Move(placements)
