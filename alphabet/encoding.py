from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from alphabet.game import Game, Player
from alphabet.move import Move, Placement
from alphabet.position import Axis, Position

ENCODER_SCHEMA_VERSION = "state_action_v1"


@dataclass(frozen=True)
class EncodedState:
    schema_version: str
    board_size: int
    board_modifiers: List[str]
    board_occupied: List[int]
    board_letters: List[str]
    rack_letters: List[str]
    rack_size: int
    opponent_rack_size: int
    bag_total: int
    bag_counts: Dict[str, int]
    round: int
    turn: int
    consecutive_passes: int
    max_rounds: int
    opening_move: int
    active_is_player_a: int
    player_score: int
    opponent_score: int
    score_diff: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "board_size": self.board_size,
            "board_modifiers": self.board_modifiers,
            "board_occupied": self.board_occupied,
            "board_letters": self.board_letters,
            "rack_letters": self.rack_letters,
            "rack_size": self.rack_size,
            "opponent_rack_size": self.opponent_rack_size,
            "bag_total": self.bag_total,
            "bag_counts": dict(self.bag_counts),
            "round": self.round,
            "turn": self.turn,
            "consecutive_passes": self.consecutive_passes,
            "max_rounds": self.max_rounds,
            "opening_move": self.opening_move,
            "active_is_player_a": self.active_is_player_a,
            "player_score": self.player_score,
            "opponent_score": self.opponent_score,
            "score_diff": self.score_diff,
        }


@dataclass(frozen=True)
class EncodedAction:
    schema_version: str
    placements: List[tuple[int, int, str, int]]
    axis: str
    tiles_used: int
    immediate_score: int
    leave_letters: List[str]
    leave_size: int
    leave_vowels: int
    leave_consonants: int
    leave_balance: int
    is_bingo: int
    formed_words: List[Dict[str, Any]]
    cross_word_count: int
    cross_score: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "placements": list(self.placements),
            "axis": self.axis,
            "tiles_used": self.tiles_used,
            "immediate_score": self.immediate_score,
            "leave_letters": self.leave_letters,
            "leave_size": self.leave_size,
            "leave_vowels": self.leave_vowels,
            "leave_consonants": self.leave_consonants,
            "leave_balance": self.leave_balance,
            "is_bingo": self.is_bingo,
            "formed_words": self.formed_words,
            "cross_word_count": self.cross_word_count,
            "cross_score": self.cross_score,
        }


class StateEncoder:
    def encode(self, game: Game, player: Player) -> EncodedState:
        other = game.players.b if player == game.players.a else game.players.a

        modifiers: List[str] = []
        occupied: List[int] = []
        letters: List[str] = []
        for row in range(game.variant.n):
            for col in range(game.variant.n):
                square = game.board.at(Position(row=row, col=col))
                modifiers.append(square.modifier.value)
                tile = square.tile
                occupied.append(1 if tile is not None else 0)
                letters.append(tile.letter if tile is not None else ".")

        rack_letters = sorted(["?" if tile.wildcard else tile.letter for tile in player.tiles])

        return EncodedState(
            schema_version=ENCODER_SCHEMA_VERSION,
            board_size=game.variant.n,
            board_modifiers=modifiers,
            board_occupied=occupied,
            board_letters=letters,
            rack_letters=rack_letters,
            rack_size=len(player.tiles),
            opponent_rack_size=len(other.tiles),
            bag_total=game.bag.total_tiles,
            bag_counts=dict(game.bag.counts),
            round=game.round,
            turn=game.turn,
            consecutive_passes=game.consecutive_passes,
            max_rounds=game.max_rounds,
            opening_move=1 if (game.round == 1 and game.turn == 1) else 0,
            active_is_player_a=1 if game.active_player == game.players.a else 0,
            player_score=player.score,
            opponent_score=other.score,
            score_diff=player.score - other.score,
        )


class ActionEncoder:
    VOWELS = {"a", "e", "i", "o", "u"}

    def encode(self, game: Game, player: Player, move: Move) -> EncodedAction:
        placements = sorted(
            [
                (
                    placement.location.position.row,
                    placement.location.position.col,
                    placement.tile.letter,
                    1 if placement.tile.wildcard else 0,
                )
                for placement in move.placements
            ]
        )

        axis = game._infer_move_axis(move.placements)  # pylint: disable=protected-access
        axis_name = axis.value if axis is not None else Axis.HORIZONTAL.value

        placement_by_pos = {
            (placement.location.position.row, placement.location.position.col): placement
            for placement in move.placements
        }

        words = game._words_formed_positions(placement_by_pos, axis) if axis is not None else []  # pylint: disable=protected-access
        formed_words: List[Dict[str, Any]] = []
        cross_score = 0

        for idx, positions in enumerate(words):
            text = "".join(
                [game._tile_letter_at(position, placement_by_pos) or "" for position in positions]  # pylint: disable=protected-access
            )
            score = game._score_word_positions(positions, placement_by_pos)  # pylint: disable=protected-access
            formed_words.append({"text": text, "score": score})
            if idx > 0:
                cross_score += score

        leave_letters = _rack_after_move_letters(player, move)
        leave_vowels = sum(1 for letter in leave_letters if letter in self.VOWELS)
        leave_consonants = len(leave_letters) - leave_vowels

        return EncodedAction(
            schema_version=ENCODER_SCHEMA_VERSION,
            placements=placements,
            axis=axis_name,
            tiles_used=len(move.placements),
            immediate_score=game.score_move(move),
            leave_letters=leave_letters,
            leave_size=len(leave_letters),
            leave_vowels=leave_vowels,
            leave_consonants=leave_consonants,
            leave_balance=abs(leave_vowels - leave_consonants),
            is_bingo=1 if len(move.placements) == game.variant.starting_tiles else 0,
            formed_words=formed_words,
            cross_word_count=max(0, len(formed_words) - 1),
            cross_score=cross_score,
        )


def _rack_after_move_letters(player: Player, move: Move) -> List[str]:
    remaining = list(player.tiles)
    for placement in move.placements:
        _remove_tile_like(remaining, placement)

    letters = ["?" if tile.wildcard else tile.letter for tile in remaining]
    letters.sort()
    return letters


def _remove_tile_like(tiles: List[Any], placement: Placement) -> None:
    target = placement.tile
    for idx, tile in enumerate(tiles):
        if tile is target:
            tiles.pop(idx)
            return

        if tile.wildcard == target.wildcard and tile.letter == target.letter:
            tiles.pop(idx)
            return
