from alphabet.encoding import ActionEncoder, ENCODER_SCHEMA_VERSION, StateEncoder
from alphabet.game import Game
from alphabet.move import Move, Placement
from alphabet.position import Position
from alphabet.wordsmith import Dictionary


def _game(words: list[str]) -> Game:
    return Game(Dictionary(words))


def _tile(game: Game, letter: str):
    return game.bag.build_tile(letter)


def _place_existing(game: Game, row: int, col: int, letter: str) -> None:
    game.board.place_tile(_tile(game, letter), Position(row, col))


def test_state_encoder_captures_board_rack_bag_and_turn_context() -> None:
    game = _game(["cat", "at"])
    game.start()
    assert game.next()

    game.active_player.tiles = [_tile(game, "c"), _tile(game, "a"), _tile(game, "t")]
    _place_existing(game, 7, 7, "a")

    encoded = StateEncoder().encode(game, game.active_player)

    assert encoded.schema_version == ENCODER_SCHEMA_VERSION
    assert encoded.board_size == 15
    assert encoded.rack_size == 3
    assert encoded.bag_total == game.bag.total_tiles
    assert encoded.round == game.round
    assert encoded.turn == game.turn
    assert encoded.board_letters[(7 * 15) + 7] == "a"


def test_action_encoder_captures_cross_word_impact() -> None:
    game = _game(["ate", "he", "at"])
    game.round = 1
    game.turn = 2

    _place_existing(game, 7, 7, "a")
    _place_existing(game, 7, 8, "t")
    _place_existing(game, 6, 9, "h")

    wildcard = _tile(game, "?")
    wildcard.set_letter("e")
    game.players.b.tiles = [wildcard]
    game.players.a.tiles = []

    move = Move([Placement(game.board.at(Position(7, 9)), wildcard)])
    encoded = ActionEncoder().encode(game, game.active_player, move)

    assert encoded.schema_version == ENCODER_SCHEMA_VERSION
    assert encoded.immediate_score == 6
    assert encoded.cross_word_count == 1
    assert encoded.cross_score == 4
    assert any(word["text"] == "ate" for word in encoded.formed_words)
    assert any(word["text"] == "he" for word in encoded.formed_words)
