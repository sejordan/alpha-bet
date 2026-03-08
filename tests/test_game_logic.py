from typing import Iterable

from alphabet.bag import Tile
from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.move import Move, Placement, ExchangeMove, PassMove
from alphabet.position import Position
from alphabet.wordsmith import Dictionary


def _make_game(words: Iterable[str]) -> Game:
    return Game(Dictionary(list(words)))


def _tile(game: Game, letter: str) -> Tile:
    return game.bag.build_tile(letter)


def _placement(game: Game, row: int, col: int, letter: str) -> Placement:
    return Placement(game.board.at(Position(row, col)), _tile(game, letter))


def _set_player_tiles(game: Game, letters: Iterable[str]):
    game.players.a.tiles = []
    game.players.b.tiles = []
    game.active_player.tiles = [_tile(game, letter) for letter in letters]


def _place_existing(game: Game, row: int, col: int, letter: str):
    game.board.place_tile(_tile(game, letter), Position(row, col))


def test_opening_move_must_cross_center():
    game = _make_game(["cat"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["c", "a", "t"])

    legal_opening = Move([
        _placement(game, 7, 7, "c"),
        _placement(game, 7, 8, "a"),
        _placement(game, 7, 9, "t"),
    ])
    assert game.is_legal(legal_opening)

    illegal_opening = Move([
        _placement(game, 0, 0, "c"),
        _placement(game, 0, 1, "a"),
        _placement(game, 0, 2, "t"),
    ])
    assert not game.is_legal(illegal_opening)


def test_move_must_be_contiguous():
    game = _make_game(["cat"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["c", "a", "t"])

    gapped = Move([
        _placement(game, 7, 7, "c"),
        _placement(game, 7, 9, "t"),
    ])
    assert not game.is_legal(gapped)


def test_non_opening_move_must_touch_existing_graph():
    game = _make_game(["cat", "dog"])
    game.round = 1
    game.turn = 2

    _place_existing(game, 7, 7, "c")
    _place_existing(game, 7, 8, "a")
    _place_existing(game, 7, 9, "t")

    _set_player_tiles(game, ["d", "o", "g"])
    detached = Move([
        _placement(game, 0, 0, "d"),
        _placement(game, 0, 1, "o"),
        _placement(game, 0, 2, "g"),
    ])
    assert not game.is_legal(detached)


def test_non_opening_legal_extension():
    game = _make_game(["cat", "at"])
    game.round = 1
    game.turn = 2

    _place_existing(game, 7, 7, "a")
    _place_existing(game, 7, 8, "t")

    _set_player_tiles(game, ["c"])
    extension = Move([_placement(game, 7, 6, "c")])
    assert game.is_legal(extension)


def test_invalid_cross_word_makes_move_illegal():
    game = _make_game(["cat", "at", "za"])
    game.round = 1
    game.turn = 2

    _place_existing(game, 7, 8, "a")
    _place_existing(game, 6, 9, "z")

    _set_player_tiles(game, ["c", "t"])
    move = Move([
        _placement(game, 7, 7, "c"),
        _placement(game, 7, 9, "t"),
    ])
    # Main word is CAT, but cross at (7,9) forms ZT which is not in dictionary.
    assert not game.is_legal(move)


def test_move_using_unowned_tiles_is_illegal():
    game = _make_game(["cat"])
    game.round = 1
    game.turn = 1

    _set_player_tiles(game, ["c", "a"])
    move = Move([
        _placement(game, 7, 7, "c"),
        _placement(game, 7, 8, "a"),
        _placement(game, 7, 9, "t"),
    ])
    assert not game.is_legal(move)


def test_score_word_and_valid_word():
    game = _make_game(["cat"])
    assert game.valid_word("cat")
    assert not game.valid_word("zzz")
    assert game.score_word("cat") > 0
    assert game.score_word("zzz") == 0


def test_all_valid_moves_codex_produces_legal_moves_on_opening():
    game = _make_game(["at", "cat", "act", "tac", "dog", "go", "do"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["c", "a", "t", "d", "o", "g"])

    engine = GameEngine()
    moves = engine.all_valid_moves_codex(game, game.active_player)

    assert len(moves) > 0
    assert all(game.is_legal(move) for move in moves)


def test_select_move_returns_none_when_no_candidates():
    game = _make_game(["cat", "dog"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, [])

    engine = GameEngine()
    assert engine.select_move(game, game.active_player) is None


def test_select_action_returns_exchange_when_no_word_move_exists():
    game = _make_game(["at"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["z"])

    engine = GameEngine()
    action = engine.select_action(game, game.active_player)
    assert isinstance(action, ExchangeMove)
    assert len(action.tiles) == 1


def test_select_action_returns_pass_when_no_move_and_no_exchange():
    game = _make_game(["at"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, [])
    game.bag.total_tiles = 0

    engine = GameEngine()
    action = engine.select_action(game, game.active_player)
    assert isinstance(action, PassMove)


def test_play_scores_opening_with_center_double_word():
    game = _make_game(["cat"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["c", "a", "t"])

    move = Move([
        _placement(game, 7, 7, "c"),
        _placement(game, 7, 8, "a"),
        _placement(game, 7, 9, "t"),
    ])
    assert game.is_legal(move)
    game.play(move)
    assert game.players.a.score == 10  # (3 + 1 + 1) * 2W


def test_play_scores_letter_modifier_for_new_tile_only():
    game = _make_game(["cat", "at"])
    game.round = 1
    game.turn = 2

    # Existing "AT" so player extends to "CAT" by placing C on (7,3) which is 2L.
    _place_existing(game, 7, 4, "a")
    _place_existing(game, 7, 5, "t")
    _set_player_tiles(game, ["c"])

    move = Move([_placement(game, 7, 3, "c")])
    assert game.is_legal(move)
    game.play(move)
    assert game.players.b.score == 8  # C(3*2L) + A(1) + T(1)


def test_play_scores_cross_word_and_wildcard_as_zero():
    game = _make_game(["ate", "he", "at"])
    game.round = 1
    game.turn = 2

    _place_existing(game, 7, 7, "a")
    _place_existing(game, 7, 8, "t")
    _place_existing(game, 6, 9, "h")

    wildcard = _tile(game, "?")
    wildcard.set_letter("e")
    game.players.a.tiles = []
    game.players.b.tiles = [wildcard]

    move = Move([Placement(game.board.at(Position(7, 9)), wildcard)])
    assert game.is_legal(move)
    game.play(move)
    # Main word ATE = 1 + 1 + 0(wildcard), cross HE = 4 + 0(wildcard)
    assert game.players.b.score == 6


def test_two_consecutive_passes_end_game():
    game = _make_game(["cat"])
    game.start()

    assert game.next()  # round 1, player A
    game.pass_turn()
    assert game.next()  # round 1, player B
    game.pass_turn()
    assert not game.next()


def test_tile_out_endgame_adjustment_with_empty_bag():
    game = _make_game(["at"])
    game.round = 1
    game.turn = 2  # Player B turn

    _place_existing(game, 7, 7, "a")
    game.players.a.tiles = [_tile(game, "z")]
    game.players.b.tiles = [_tile(game, "t")]

    # Empty the bag
    for letter in game.bag.counts:
        game.bag.counts[letter] = 0
    game.bag.total_tiles = 0

    move = Move([_placement(game, 7, 8, "t")])
    assert game.is_legal(move)
    game.play(move)

    # Endgame adjustments are applied when advancing to next turn.
    assert not game.next()
    assert game.players.b.score == 12  # 2 for "AT" + 10 opponent rack bonus
    assert game.players.a.score == -10


def test_bingo_adds_50_points():
    game = _make_game(["aaaaaaa"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["a", "a", "a", "a", "a", "a", "a"])

    move = Move([
        _placement(game, 7, 1, "a"),
        _placement(game, 7, 2, "a"),
        _placement(game, 7, 3, "a"),
        _placement(game, 7, 4, "a"),
        _placement(game, 7, 5, "a"),
        _placement(game, 7, 6, "a"),
        _placement(game, 7, 7, "a"),
    ])
    assert game.is_legal(move)
    # Base: seven 1-point letters, with 2xL at (7,3) => +1, and 2xW at (7,7): (7+1)*2 = 16.
    # Bingo bonus +50 => 66 total.
    assert game.score_move(move) == 66


def test_all_valid_moves_codex_has_no_duplicates():
    game = _make_game(["at", "ate", "tea", "eat", "eta", "to", "toe", "ten", "net"])
    game.round = 1
    game.turn = 1
    _set_player_tiles(game, ["a", "t", "e", "n", "o", "r", "s"])

    engine = GameEngine()
    moves = engine.all_valid_moves_codex(game, game.active_player)

    sigs = []
    for move in moves:
        sig = tuple(sorted(
            (p.location.position.row, p.location.position.col, p.tile.letter, p.tile.wildcard)
            for p in move.placements
        ))
        sigs.append(sig)

    assert len(sigs) == len(set(sigs))


def test_engine_selected_moves_stay_legal_across_multiple_turns():
    import numpy as np

    np.random.seed(7)
    words = [line.strip() for line in open("dictionary/classic.txt")]
    game = _make_game(words)
    engine = GameEngine()
    game.start()

    completed_turns = 0
    while completed_turns < 12 and game.next():
        action = engine.select_action(game, game.active_player)
        if isinstance(action, PassMove):
            game.apply_action(action)
            completed_turns += 1
            continue

        if isinstance(action, ExchangeMove):
            game.apply_action(action)
            completed_turns += 1
            continue

        move = action
        assert game.is_legal(move)
        predicted = game.score_move(move)
        score_before = game.active_player.score
        game.play(move)
        assert game.active_player.score == score_before + predicted
        completed_turns += 1

    assert completed_turns == 12


def test_exchange_action_replaces_tiles_and_keeps_bag_total_constant():
    game = _make_game(["at"])
    game.start()
    game.round = 1
    game.turn = 1

    before_bag = game.bag.total_tiles
    before_tiles = list(game.active_player.tiles)

    action = ExchangeMove(before_tiles[:2])
    assert game.can_exchange(action)
    game.apply_action(action)

    assert game.consecutive_passes == 1
    assert game.bag.total_tiles == before_bag
    assert len(game.active_player.tiles) == game.variant.starting_tiles


def test_select_action_prefers_higher_scoring_move():
    game = _make_game(["za", "at"])
    game.round = 1
    game.turn = 2
    _place_existing(game, 7, 7, "a")
    _set_player_tiles(game, ["z", "t"])

    engine = GameEngine()
    action = engine.select_action(game, game.active_player, verbose=False)
    assert isinstance(action, Move)
    played_letters = {placement.tile.letter for placement in action.placements}
    assert "z" in played_letters
