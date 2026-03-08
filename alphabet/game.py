from typing import List, NamedTuple, Dict

from alphabet.player import Player
from alphabet.move import Move, Placement, PassMove, ExchangeMove
from alphabet.board import Board, Tile
from alphabet.variant import GameVariant, VariantFactory
from alphabet.wordsmith import Dictionary
from alphabet.position import Position, Axis
from alphabet.modifier import Modifier


class Players(NamedTuple):
    a: Player
    b: Player

class Game:
    def __init__(self, dictionary: Dictionary, variant: GameVariant.Type = GameVariant.Type.CLASSIC):
        self.max_rounds = 30
        self.round = 0
        self.turn = 0
        self.consecutive_passes = 0
        self._endgame_scored = False
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

        if self.consecutive_passes >= 2:
            return True

        # Natural tile-out ending requires an empty bag.
        if self.bag.total_tiles == 0 and (len(self.players.a.tiles) == 0 or len(self.players.b.tiles) == 0):
            return True

        # If the bag is empty and neither player can form any legal move, game is over.
        if self.bag.total_tiles == 0 and self._both_players_blocked():
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

        if self.is_over:
            self._apply_endgame_adjustments()
            return False

        return True
    
    def play(self, move: Move):
        assert self.is_legal(move), "Illegal move!"
        self.consecutive_passes = 0
        points = self.score_move(move)

        # apply the move to the board
        move.play(self.active_player, self.board)
        self.active_player.add_points(points)

        # player tops off their tiles
        tiles_to_draw = self.variant.starting_tiles - len(self.active_player.tiles)
        self.active_player.draw(self.bag, n=tiles_to_draw)

    def pass_turn(self):
        self.consecutive_passes += 1

    def exchange(self, move: ExchangeMove):
        assert self.can_exchange(move), "Illegal exchange!"
        self.consecutive_passes += 1

        # Exchange is scoreless, and counts as a pass-like turn.
        for tile in move.tiles:
            self.active_player.play_letter(tile)
            self.bag.add_tile(self.bag.build_tile(Tile.WILDCARD if tile.wildcard else tile.letter))

        self.active_player.draw(self.bag, n=len(move.tiles))

    def can_exchange(self, move: ExchangeMove) -> bool:
        if len(move.tiles) == 0:
            return False

        # Must be able to draw at least the number exchanged from the bag.
        if self.bag.total_tiles < len(move.tiles):
            return False

        remaining: Dict[tuple[str, bool], int] = {}
        for tile in self.active_player.tiles:
            key = (tile.letter, tile.wildcard)
            remaining[key] = remaining.get(key, 0) + 1

        for tile in move.tiles:
            key = (tile.letter, tile.wildcard)
            if remaining.get(key, 0) <= 0:
                return False
            remaining[key] -= 1

        return True

    def apply_action(self, action: Move | ExchangeMove | PassMove):
        if isinstance(action, Move):
            self.play(action)
            return
        if isinstance(action, ExchangeMove):
            self.exchange(action)
            return
        if isinstance(action, PassMove):
            self.pass_turn()
            return
        raise RuntimeError("Unsupported action type")

    def score_move(self, move: Move) -> int:
        placements = move.placements
        if len(placements) == 0:
            return 0

        placement_by_pos = {
            (placement.location.position.row, placement.location.position.col): placement
            for placement in placements
        }
        axis = self._infer_move_axis(placements)
        if axis is None:
            return 0

        words_to_score = self._words_formed_positions(placement_by_pos, axis)

        total = 0
        for positions in words_to_score:
            total += self._score_word_positions(positions, placement_by_pos)

        # Bingo: used all rack tiles this turn.
        if len(placements) == self.variant.starting_tiles:
            total += 50

        return total

    def is_legal(self, move: Move) -> bool:
        placements = move.placements
        if len(placements) == 0:
            return False

        # placement map keyed by coordinates for quick lookups
        placement_by_pos: Dict[tuple[int, int], Placement] = {}
        for placement in placements:
            position = placement.location.position
            key = (position.row, position.col)

            # position must be valid and currently empty
            if not self.board.is_in_bounds(position):
                return False
            if self.board.at(position).tile is not None:
                return False

            # cannot place multiple tiles on the same square
            if key in placement_by_pos:
                return False

            # wildcard must already have a resolved letter
            if placement.tile.wildcard and placement.tile.letter == Tile.WILDCARD:
                return False

            placement_by_pos[key] = placement

        if not self._active_player_has_tiles_for_move(placements):
            return False

        axis = self._infer_move_axis(placements)
        if axis is None:
            return False

        if not self._is_contiguous_on_axis(placement_by_pos, axis):
            return False

        is_opening_move = (self.turn == 1 and self.round == 1)
        if is_opening_move:
            if not self._move_crosses_center(placement_by_pos):
                return False
        else:
            if not self._touches_existing_graph(placement_by_pos):
                return False

        if not self._all_words_valid(placement_by_pos, axis):
            return False

        return True

    def _active_player_has_tiles_for_move(self, placements: List[Placement]) -> bool:
        remaining_letters: Dict[str, int] = {}
        remaining_wildcards = 0

        for tile in self.active_player.tiles:
            if tile.wildcard:
                remaining_wildcards += 1
            else:
                remaining_letters[tile.letter] = remaining_letters.get(tile.letter, 0) + 1

        for placement in placements:
            tile = placement.tile
            if tile.wildcard:
                if remaining_wildcards <= 0:
                    return False
                remaining_wildcards -= 1
            else:
                if remaining_letters.get(tile.letter, 0) <= 0:
                    return False
                remaining_letters[tile.letter] -= 1

        return True

    def _infer_move_axis(self, placements: List[Placement]) -> Axis | None:
        if len(placements) == 1:
            return Axis.HORIZONTAL

        rows = {placement.location.position.row for placement in placements}
        cols = {placement.location.position.col for placement in placements}

        if len(rows) == 1:
            return Axis.HORIZONTAL
        if len(cols) == 1:
            return Axis.VERTICAL

        return None

    def _is_contiguous_on_axis(self, placement_by_pos: Dict[tuple[int, int], Placement], axis: Axis) -> bool:
        positions = [placement.location.position for placement in placement_by_pos.values()]

        if axis == Axis.HORIZONTAL:
            row = positions[0].row
            min_col = min(position.col for position in positions)
            max_col = max(position.col for position in positions)
            for col in range(min_col, max_col + 1):
                position = Position(row=row, col=col)
                if self.board.at(position).tile is None and (row, col) not in placement_by_pos:
                    return False
        else:
            col = positions[0].col
            min_row = min(position.row for position in positions)
            max_row = max(position.row for position in positions)
            for row in range(min_row, max_row + 1):
                position = Position(row=row, col=col)
                if self.board.at(position).tile is None and (row, col) not in placement_by_pos:
                    return False

        return True

    def _move_crosses_center(self, placement_by_pos: Dict[tuple[int, int], Placement]) -> bool:
        center = self.variant.n // 2
        return (center, center) in placement_by_pos

    def _touches_existing_graph(self, placement_by_pos: Dict[tuple[int, int], Placement]) -> bool:
        for placement in placement_by_pos.values():
            position = placement.location.position
            for neighbor in position.neighbors():
                if not self.board.is_in_bounds(neighbor):
                    continue

                if (neighbor.row, neighbor.col) in placement_by_pos:
                    continue

                if self.board.at(neighbor).tile is not None:
                    return True

        return False

    def _all_words_valid(self, placement_by_pos: Dict[tuple[int, int], Placement], axis: Axis) -> bool:
        words = self._words_formed_positions(placement_by_pos, axis)
        if len(words) == 0:
            return False

        for word_positions in words:
            if len(word_positions) <= 1:
                return False
            word = "".join([self._tile_letter_at(position, placement_by_pos) or "" for position in word_positions])
            if not self.valid_word(word):
                return False

        return True

    def _build_word(self, origin: Position, axis: Axis, placement_by_pos: Dict[tuple[int, int], Placement]) -> str:
        cursor = self._find_word_start(origin, axis, placement_by_pos)
        letters: List[str] = []
        while True:
            letter = self._tile_letter_at(cursor, placement_by_pos)
            if letter is None:
                break
            letters.append(letter)
            cursor = cursor.next(axis)

        return "".join(letters)

    def _build_word_positions(self, origin: Position, axis: Axis, placement_by_pos: Dict[tuple[int, int], Placement]) -> List[Position]:
        cursor = self._find_word_start(origin, axis, placement_by_pos)
        positions: List[Position] = []

        while True:
            letter = self._tile_letter_at(cursor, placement_by_pos)
            if letter is None:
                break
            positions.append(cursor)
            cursor = cursor.next(axis)

        return positions

    def _find_word_start(self, origin: Position, axis: Axis, placement_by_pos: Dict[tuple[int, int], Placement]) -> Position:
        cursor = origin
        while True:
            previous = cursor.prev(axis)
            if self._tile_letter_at(previous, placement_by_pos) is None:
                return cursor
            cursor = previous

    def _score_word_positions(self, positions: List[Position], placement_by_pos: Dict[tuple[int, int], Placement]) -> int:
        subtotal = 0
        word_multiplier = 1

        for position in positions:
            key = (position.row, position.col)
            is_new_tile = key in placement_by_pos

            if is_new_tile:
                placement = placement_by_pos[key]
                tile_value = placement.tile.value
                square = self.board.at(position)
                letter_multiplier = self._letter_multiplier_for_modifier(square.modifier)
                word_multiplier *= self._word_multiplier_for_modifier(square.modifier)
                subtotal += tile_value * letter_multiplier
            else:
                existing_tile = self.board.at(position).tile
                assert existing_tile is not None
                subtotal += existing_tile.value

        return subtotal * word_multiplier

    def _words_formed_positions(self, placement_by_pos: Dict[tuple[int, int], Placement], axis: Axis) -> List[List[Position]]:
        positions = [placement.location.position for placement in placement_by_pos.values()]
        if len(positions) == 0:
            return []

        words: List[List[Position]] = []
        seen: set[tuple] = set()

        anchor = positions[0]
        main_positions = self._build_word_positions(anchor, axis, placement_by_pos)
        if len(main_positions) > 1:
            key = tuple((position.row, position.col) for position in main_positions)
            seen.add(key)
            words.append(main_positions)

        cross_axis = Axis.VERTICAL if axis == Axis.HORIZONTAL else Axis.HORIZONTAL
        for position in positions:
            cross_positions = self._build_word_positions(position, cross_axis, placement_by_pos)
            if len(cross_positions) <= 1:
                continue
            key = tuple((pos.row, pos.col) for pos in cross_positions)
            if key in seen:
                continue
            seen.add(key)
            words.append(cross_positions)

        return words

    def _letter_multiplier_for_modifier(self, modifier: Modifier) -> int:
        if modifier == Modifier.DOUBLE_LETTER:
            return 2
        if modifier == Modifier.TRIPLE_LETTER:
            return 3
        return 1

    def _word_multiplier_for_modifier(self, modifier: Modifier) -> int:
        if modifier == Modifier.DOUBLE_WORD:
            return 2
        if modifier == Modifier.TRIPLE_WORD:
            return 3
        return 1

    def _tile_letter_at(self, position: Position, placement_by_pos: Dict[tuple[int, int], Placement]) -> str | None:
        if not self.board.is_in_bounds(position):
            return None

        key = (position.row, position.col)
        if key in placement_by_pos:
            return placement_by_pos[key].tile.letter

        tile = self.board.at(position).tile
        if tile is None:
            return None

        return tile.letter

    def _both_players_blocked(self) -> bool:
        return (not self._player_has_legal_word_move(self.players.a)) and (
            not self._player_has_legal_word_move(self.players.b)
        )

    def _player_has_legal_word_move(self, player: Player) -> bool:
        """
        Check if the provided player has at least one legal word move in the current
        board state. This temporarily flips active-player parity because legality
        validation is tied to `self.active_player`.
        """
        from alphabet.engine import GameEngine  # local import to avoid circular import

        previous_turn = self.turn
        try:
            # Active player is A on odd turns and B on even turns.
            self.turn = 1 if player == self.players.a else 2
            engine = GameEngine()
            return len(engine.all_valid_moves_codex(self, player)) > 0
        finally:
            self.turn = previous_turn

    def score(self, tiles: List[Tile]) -> int:
        return self.score_word("".join([Tile.WILDCARD if tile.wildcard else tile.letter for tile in tiles]))

    def score_word(self, word: str) -> int:
        """
        Returns the point value of the word, based on the game's bag
        """
        if not self.valid_word(word):
            return 0
        
        return sum([self.bag.get_letter_value(letter) for letter in word])

    def _apply_endgame_adjustments(self):
        if self._endgame_scored:
            return

        a_remaining = sum(tile.value for tile in self.players.a.tiles)
        b_remaining = sum(tile.value for tile in self.players.b.tiles)

        # Player went out with an empty bag.
        if self.bag.total_tiles == 0 and (len(self.players.a.tiles) == 0 or len(self.players.b.tiles) == 0):
            if len(self.players.a.tiles) == 0:
                self.players.a.add_points(b_remaining)
                self.players.b.add_points(-b_remaining)
            elif len(self.players.b.tiles) == 0:
                self.players.b.add_points(a_remaining)
                self.players.a.add_points(-a_remaining)
        else:
            # Pass/round-limit ending: each player loses the value of unplayed tiles.
            self.players.a.add_points(-a_remaining)
            self.players.b.add_points(-b_remaining)

        self._endgame_scored = True
    
    # todo: this is super inefficient, find a better algorithm/data structure
    def valid_word(self, word: str) -> bool:
        return self.dictionary.is_valid(word)
