import copy
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

import numpy as np
from flask import Flask, make_response, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from alphabet.engine import GameEngine
from alphabet.game import Game
from alphabet.move import ExchangeMove, Move, PassMove, Placement
from alphabet.position import Axis, Position
from alphabet.strategy_factory import build_strategy
from alphabet.wordsmith import Dictionary


def _load_dictionary() -> Dictionary:
    words: List[str] = []
    dictionary_path = os.path.join(REPO_ROOT, "dictionary", "classic.txt")
    with open(dictionary_path, "r") as fh:
        for line in fh:
            words.append(line.strip())
    return Dictionary(words)


DICTIONARY = _load_dictionary()


def _default_ai_epsilon() -> float:
    value = os.environ.get("ALPHABET_AI_EPSILON", "0.0").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


DEFAULT_AI_STRATEGY = os.environ.get("ALPHABET_AI_STRATEGY", "greedy").strip().lower()
DEFAULT_AI_MODEL = os.environ.get("ALPHABET_AI_MODEL", "").strip()
DEFAULT_AI_EPSILON = _default_ai_epsilon()
DEFAULT_AI_TOPK = int(os.environ.get("ALPHABET_AI_TOPK", "5"))


def _build_engine(
    strategy_name: str,
    model_path: str = "",
    epsilon: float = 0.0,
    seed: int | None = None,
) -> tuple[GameEngine, str]:
    result = build_strategy(
        strategy_name,
        model_path=model_path,
        epsilon=epsilon,
        seed=seed,
        strict_model_load=False,
    )
    return GameEngine(strategy=result.strategy), result.warning


UTILITY_ENGINE = GameEngine()

app = Flask(__name__)
app.secret_key = os.environ.get("ALPHABET_SECRET_KEY", "dev-secret-key")


def create_app() -> Flask:
    return app


@dataclass
class PlayState:
    game: Game
    suggestions: List[Move]
    engine: GameEngine
    ai_strategy: str
    ai_model_path: str
    ai_epsilon: float
    ai_reasoning: List[Dict[str, Any]] = field(default_factory=list)
    human_analysis: List[Dict[str, Any]] = field(default_factory=list)
    message: str = ""


@dataclass
class CompanionState:
    board: List[List[str]] = field(default_factory=lambda: [["" for _ in range(15)] for _ in range(15)])
    my_rack: str = ""
    my_score: int = 0
    opp_score: int = 0
    turn: str = "me"
    lexicon: str = "classic"
    seen_letters: str = ""
    history: List[Dict[str, Any]] = field(default_factory=list)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "board": copy.deepcopy(self.board),
            "my_rack": self.my_rack,
            "my_score": self.my_score,
            "opp_score": self.opp_score,
            "turn": self.turn,
            "lexicon": self.lexicon,
            "seen_letters": self.seen_letters,
        }

    def restore(self, snapshot: Dict[str, Any]) -> None:
        self.board = copy.deepcopy(snapshot["board"])
        self.my_rack = snapshot["my_rack"]
        self.my_score = snapshot["my_score"]
        self.opp_score = snapshot["opp_score"]
        self.turn = snapshot["turn"]
        self.lexicon = snapshot.get("lexicon", "classic")
        self.seen_letters = snapshot.get("seen_letters", "")

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": 2,
                "board": self.board,
                "my_rack": self.my_rack,
                "my_score": self.my_score,
                "opp_score": self.opp_score,
                "turn": self.turn,
                "lexicon": self.lexicon,
                "seen_letters": self.seen_letters,
                "history": self.history,
            },
            indent=2,
        )


PLAY_STATE: PlayState | None = None
COMPANION_STATE = CompanionState()


def _blank_grid(n: int) -> List[List[str]]:
    return [["" for _ in range(n)] for _ in range(n)]


def _grid_from_request(n: int) -> List[List[str]]:
    grid = _blank_grid(n)
    for row in range(n):
        for col in range(n):
            raw = request.form.get(f"cell_{row}_{col}", "")
            grid[row][col] = _normalize_board_cell(raw)
    return grid


def _board_to_grid(game: Game) -> List[List[str]]:
    n = game.variant.n
    grid = _blank_grid(n)
    for row in range(n):
        for col in range(n):
            tile = game.board.at(Position(row, col)).tile
            if tile is not None:
                grid[row][col] = tile.letter
    return grid


def _play_board_view(game: Game) -> List[List[Dict[str, Any]]]:
    view: List[List[Dict[str, Any]]] = []
    for row in range(game.variant.n):
        values: List[Dict[str, Any]] = []
        for col in range(game.variant.n):
            square = game.board.at(Position(row, col))
            tile = square.tile
            values.append(
                {
                    "row": row,
                    "col": col,
                    "letter": tile.letter.upper() if tile is not None else "",
                    "occupied": tile is not None,
                    "wildcard": tile.wildcard if tile is not None else False,
                    "modifier": square.modifier.value,
                }
            )
        view.append(values)
    return view


def _normalized_rack(raw: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyz?")
    return "".join([ch for ch in raw.lower() if ch in allowed])


def _normalize_board_cell(raw: str) -> str:
    value = raw.strip()
    if len(value) == 0 or value == ".":
        return ""
    ch = value[0]
    if ch.isalpha():
        return ch
    return ""


def _cell_letter(cell: str) -> str:
    return cell.lower()


def _cell_is_blank(cell: str) -> bool:
    return len(cell) > 0 and cell.isalpha() and cell.isupper()


def _grid_to_text(grid: List[List[str]]) -> str:
    lines = []
    for row in grid:
        lines.append("".join([cell if cell else "." for cell in row]))
    return "\n".join(lines)


def _text_to_grid(text: str, n: int = 15) -> List[List[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != n:
        raise ValueError(f"Expected {n} board rows, found {len(lines)}.")
    grid = _blank_grid(n)
    for row, line in enumerate(lines):
        if len(line) != n:
            raise ValueError(f"Row {row} must have exactly {n} characters.")
        for col, ch in enumerate(line):
            if ch == ".":
                continue
            if not ch.isalpha():
                raise ValueError("Board text may only contain letters and '.'")
            grid[row][col] = ch
    return grid


def _apply_grid(game: Game, grid: List[List[str]]) -> None:
    for row, values in enumerate(grid):
        for col, cell in enumerate(values):
            if cell:
                letter = _cell_letter(cell)
                tile = game.bag.build_tile("?" if _cell_is_blank(cell) else letter)
                if _cell_is_blank(cell):
                    tile.set_letter(letter)
                game.board.place_tile(tile, Position(row, col))


def _setup_companion_game(state: CompanionState) -> Game:
    game = Game(DICTIONARY)
    game.players.a.tiles = []
    game.players.b.tiles = []
    _apply_grid(game, state.board)
    game.players.a.tiles = [game.bag.build_tile(letter) for letter in state.my_rack]
    game.players.a.score = state.my_score
    game.players.b.score = state.opp_score
    game.round = 2 if any(letter for row in state.board for letter in row) else 1
    game.turn = 1 if state.turn == "me" else 2
    return game


def _leave_for_move(game: Game, move: Move) -> str:
    rack = [tile.letter if not tile.wildcard else "?" for tile in game.active_player.tiles]
    for placement in move.placements:
        if placement.tile.wildcard:
            if "?" in rack:
                rack.remove("?")
        elif placement.tile.letter in rack:
            rack.remove(placement.tile.letter)
        elif "?" in rack:
            rack.remove("?")
    return "".join(sorted(rack))


def _leave_quality(letters: str) -> float:
    vowels = sum(1 for ch in letters if ch in "aeiou")
    consonants = len(letters) - vowels
    balance_penalty = abs(vowels - consonants)
    return -float(balance_penalty)


def _move_summary(game: Game, move: Move) -> Dict[str, Any]:
    analysis = game.analyze_move(move)
    formed_words: List[Dict[str, Any]] = []
    for word in analysis.formed_words:
        formed_words.append({"text": word.text, "score": word.score})
    leave = _leave_for_move(game, move)
    return {
        "score": analysis.total_score,
        "direction": analysis.direction,
        "word": analysis.word,
        "placements": analysis.placements,
        "leave": leave,
        "leave_quality": _leave_quality(leave),
        "formed_words": formed_words,
    }


def _serialize_move(move: Move) -> str:
    parts = []
    for placement in move.placements:
        pos = placement.location.position
        parts.append(
            f"{pos.row}:{pos.col}:{placement.tile.letter}:{'1' if placement.tile.wildcard else '0'}"
        )
    return "|".join(parts)


def _deserialize_move(game: Game, payload: str) -> Move:
    placements: List[Placement] = []
    for chunk in payload.split("|"):
        row_s, col_s, letter, wild_s = chunk.split(":")
        tile = game.bag.build_tile("?" if wild_s == "1" else letter)
        if wild_s == "1":
            tile.set_letter(letter)
        placements.append(Placement(game.board.at(Position(int(row_s), int(col_s))), tile))
    return Move(placements)


def _build_manual_move(game: Game, payload: str) -> Move:
    if not payload:
        raise ValueError("No manual placements provided.")
    data = json.loads(payload)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Manual move payload is empty.")

    placements: List[Placement] = []
    seen: set[Tuple[int, int]] = set()
    for item in data:
        row = int(item["row"])
        col = int(item["col"])
        token = str(item["token"]).lower()
        assigned = str(item.get("assigned", "")).lower()

        if not (0 <= row < game.variant.n and 0 <= col < game.variant.n):
            raise ValueError("Manual placement out of bounds.")
        key = (row, col)
        if key in seen:
            raise ValueError("Duplicate manual placement coordinates.")
        seen.add(key)

        pos = Position(row, col)
        if game.board.at(pos).tile is not None:
            raise ValueError("Manual move places on occupied square.")

        if token == "?":
            if len(assigned) != 1 or assigned not in "abcdefghijklmnopqrstuvwxyz":
                raise ValueError("Wildcard tiles require a single assigned letter.")
            tile = game.bag.build_tile("?")
            tile.set_letter(assigned)
        else:
            if len(token) != 1 or token not in "abcdefghijklmnopqrstuvwxyz":
                raise ValueError("Invalid rack token in manual move.")
            tile = game.bag.build_tile(token)

        placements.append(Placement(game.board.at(pos), tile))

    return Move(placements)


def _sorted_suggestions(game: Game, limit: int = 30, engine: GameEngine | None = None) -> List[Move]:
    move_engine = engine if engine is not None else UTILITY_ENGINE
    candidates = move_engine.all_valid_moves_codex(game, game.active_player)
    return sorted(candidates, key=lambda move: game.score_move(move), reverse=True)[:limit]


def _available_model_paths() -> List[str]:
    model_dir = os.path.join(REPO_ROOT, "models")
    if not os.path.isdir(model_dir):
        return []
    out: List[str] = []
    for value in sorted(os.listdir(model_dir)):
        if value.endswith(".json"):
            out.append(os.path.join("models", value))
    return out


def _ai_reasoning(game: Game, engine: GameEngine, top_k: int = DEFAULT_AI_TOPK) -> List[Dict[str, Any]]:
    candidates = engine.all_valid_moves_codex(game, game.active_player)
    scored: List[tuple[float, Move]] = []
    for candidate in candidates:
        try:
            model_score = float(engine.strategy.model.score(engine.strategy.move_features(game, game.active_player, candidate)))  # type: ignore[attr-defined]
        except Exception:
            model_score = float(game.score_move(candidate))
        scored.append((model_score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for score, move in scored[:top_k]:
        summary = _move_summary(game, move)
        summary["model_score"] = round(score, 4)
        out.append(summary)
    return out


def _build_move_from_word(
    game: Game,
    word: str,
    row: int,
    col: int,
    direction: str,
    actor: str,
) -> Tuple[Move | None, str]:
    if direction not in ("horizontal", "vertical"):
        return None, "Direction must be horizontal or vertical."
    axis = Axis.HORIZONTAL if direction == "horizontal" else Axis.VERTICAL
    word = word.strip().lower()
    if len(word) < 2 or any(ch not in "abcdefghijklmnopqrstuvwxyz" for ch in word):
        return None, "Word must be at least 2 letters and contain only a-z."

    pos = Position(row, col)
    if not game.board.is_in_bounds(pos):
        return None, "Start position is out of bounds."

    if actor == "me":
        move = UTILITY_ENGINE.build_move(game, game.active_player, pos, axis, word)
        if move is None:
            return None, "Your rack cannot build that word at the selected position."
        return move, ""

    placements: List[Placement] = []
    cursor = pos
    for letter in word:
        if not game.board.is_in_bounds(cursor):
            return None, "Word runs off the board."
        existing = game.board.at(cursor).tile
        if existing is not None and existing.letter != letter:
            return None, f"Board mismatch at ({cursor.row}, {cursor.col})."
        if existing is None:
            placements.append(Placement(game.board.at(cursor), game.bag.build_tile(letter)))
        cursor = cursor.next(axis)
    return Move(placements), ""


def _apply_companion_move(
    state: CompanionState,
    actor: str,
    move: Move,
    word: str,
    best_score: int | None = None,
) -> Dict[str, Any]:
    before_snapshot = state.snapshot()
    state.snapshots.append(before_snapshot)
    game = _setup_companion_game(state)
    score = game.score_move(move)
    for placement in move.placements:
        r = placement.location.position.row
        c = placement.location.position.col
        letter = placement.tile.letter
        state.board[r][c] = letter.upper() if placement.tile.wildcard else letter

    if actor == "me":
        rack = list(state.my_rack)
        for placement in move.placements:
            if placement.tile.wildcard and "?" in rack:
                rack.remove("?")
            elif placement.tile.letter in rack:
                rack.remove(placement.tile.letter)
            elif "?" in rack:
                rack.remove("?")
        state.my_rack = "".join(rack)
        state.my_score += score
    else:
        state.opp_score += score

    state.turn = "opponent" if actor == "me" else "me"

    summary = _move_summary(game, move)
    summary["actor"] = actor
    summary["entered_word"] = word
    summary["snapshot_before"] = before_snapshot
    if actor == "me" and best_score is not None:
        summary["best_gap"] = best_score - summary["score"]
    summary["snapshot_after"] = state.snapshot()
    state.history.append(summary)
    return summary


def _apply_raw_board_diff(
    state: CompanionState,
    actor: str,
    changed_tiles: List[Tuple[int, int, str]],
    entered_word: str,
    direction: str,
    score: int,
) -> Dict[str, Any]:
    before_snapshot = state.snapshot()
    state.snapshots.append(before_snapshot)
    for row, col, cell in changed_tiles:
        state.board[row][col] = cell

    if actor == "me":
        state.my_score += score
    else:
        state.opp_score += score
    state.turn = "opponent" if actor == "me" else "me"

    summary: Dict[str, Any] = {
        "actor": actor,
        "word": entered_word,
        "entered_word": entered_word,
        "direction": direction,
        "score": score,
        "leave": state.my_rack,
        "leave_quality": _leave_quality(state.my_rack),
        "placements": [(r, c, _cell_letter(cell), _cell_is_blank(cell)) for r, c, cell in changed_tiles],
        "formed_words": [],
        "forced": True,
        "snapshot_before": before_snapshot,
    }
    summary["snapshot_after"] = state.snapshot()
    state.history.append(summary)
    return summary


def _infer_move_from_diff(
    old_grid: List[List[str]],
    new_grid: List[List[str]],
) -> Tuple[List[Tuple[int, int, str]], str, int, int, str, str]:
    added: List[Tuple[int, int, str]] = []
    for row in range(15):
        for col in range(15):
            old_cell = old_grid[row][col]
            new_cell = new_grid[row][col]
            if old_cell == new_cell:
                continue
            if old_cell:
                return [], "", -1, -1, "", "Board diff cannot remove or alter existing tiles."
            if not new_cell:
                continue
            added.append((row, col, new_cell))

    if not added:
        return [], "", -1, -1, "", "No new tiles detected."

    rows = {r for r, _, _ in added}
    cols = {c for _, c, _ in added}
    direction = "horizontal" if len(rows) == 1 else "vertical" if len(cols) == 1 else ""
    if not direction:
        return [], "", -1, -1, "", "Added tiles must be in one row or one column."

    axis = Axis.HORIZONTAL if direction == "horizontal" else Axis.VERTICAL
    first = min(added, key=lambda item: item[1] if direction == "horizontal" else item[0])
    start = Position(first[0], first[1])

    # Expand to whole formed word using the NEW board.
    cursor = start
    while True:
        prev = cursor.prev(axis)
        if prev.row < 0 or prev.col < 0 or prev.row >= 15 or prev.col >= 15:
            break
        if not new_grid[prev.row][prev.col]:
            break
        cursor = prev

    letters: List[str] = []
    begin = cursor
    while True:
        if cursor.row < 0 or cursor.col < 0 or cursor.row >= 15 or cursor.col >= 15:
            break
        cell = new_grid[cursor.row][cursor.col]
        if not cell:
            break
        letters.append(_cell_letter(cell))
        cursor = cursor.next(axis)

    if len(letters) <= 1:
        return [], "", -1, -1, "", "Diff does not form a valid word run."

    return added, "".join(letters), begin.row, begin.col, direction, ""


def _parse_shorthand_move(raw: str) -> Tuple[str, int, int, str, str]:
    """
    Parse shorthand like:
      H8 H WORD
      7 7 v word
    Returns actor, row, col, direction, word
    """
    text = raw.strip()
    if not text:
        raise ValueError("Shorthand input is empty.")
    tokens = text.split()
    if len(tokens) < 3:
        raise ValueError("Shorthand requires at least 3 tokens.")

    actor = "me"
    if tokens[0].lower() in ("me", "opp", "opponent"):
        actor = "opponent" if tokens[0].lower() in ("opp", "opponent") else "me"
        tokens = tokens[1:]

    if len(tokens) < 3:
        raise ValueError("Shorthand requires position, direction, and word.")

    coord = tokens[0].upper()
    direction_token = tokens[1].lower()
    word = tokens[2].lower()

    if coord[0].isalpha() and coord[1:].isdigit():
        row = ord(coord[0]) - ord("A")
        col = int(coord[1:]) - 1
    elif len(tokens) >= 4 and tokens[0].isdigit() and tokens[1].isdigit():
        row = int(tokens[0])
        col = int(tokens[1])
        direction_token = tokens[2].lower()
        word = tokens[3].lower()
    else:
        raise ValueError("Unsupported coordinate format.")

    if not (0 <= row < 15 and 0 <= col < 15):
        raise ValueError("Coordinates out of bounds.")

    if direction_token in ("h", "horizontal"):
        direction = "horizontal"
    elif direction_token in ("v", "vertical"):
        direction = "vertical"
    else:
        raise ValueError("Direction must be H/V or horizontal/vertical.")

    return actor, row, col, direction, word


def _unseen_pool_counts(state: CompanionState) -> Dict[str, int]:
    game = Game(DICTIONARY)
    counts = dict(game.bag.counts)

    for row in state.board:
        for cell in row:
            if cell:
                letter = _cell_letter(cell)
                counts[letter] = max(0, counts.get(letter, 0) - 1)

    for letter in state.my_rack:
        counts[letter] = max(0, counts.get(letter, 0) - 1)

    for letter in state.seen_letters:
        counts[letter] = max(0, counts.get(letter, 0) - 1)

    return counts


@app.route("/")
def index() -> ResponseReturnValue:
    return render_template("index.html")


@app.route("/companion", methods=["GET", "POST"])
def companion() -> ResponseReturnValue:
    state = COMPANION_STATE
    error = ""
    preview: Dict[str, Any] | None = None
    suggestions: List[Dict[str, Any]] = []

    if request.method == "POST":
        action = request.form.get("action", "suggest")
        try:
            if action == "set_rack":
                state.my_rack = _normalized_rack(request.form.get("rack", ""))
            elif action == "set_lexicon":
                lexicon = request.form.get("lexicon", "classic")
                if lexicon != "classic":
                    raise ValueError("Only 'classic' lexicon is available in this build.")
                state.lexicon = lexicon
            elif action == "mark_seen":
                state.seen_letters = _normalized_rack(request.form.get("seen_letters", ""))
            elif action == "clear_board":
                state.restore(
                    {
                        "board": _blank_grid(15),
                        "my_rack": state.my_rack,
                        "my_score": 0,
                        "opp_score": 0,
                        "turn": "me",
                        "lexicon": "classic",
                        "seen_letters": state.seen_letters,
                        "history": [],
                    }
                )
                state.snapshots = []
            elif action == "undo":
                if state.snapshots:
                    state.restore(state.snapshots.pop())
                    if state.history:
                        state.history.pop()
            elif action == "jump_turn":
                turn_index = int(request.form.get("turn_index", "-1"))
                if turn_index < 0:
                    if state.history and state.history[0].get("snapshot_before"):
                        state.restore(state.history[0]["snapshot_before"])
                    else:
                        state.restore(
                            {
                                "board": _blank_grid(15),
                                "my_rack": state.my_rack,
                                "my_score": 0,
                                "opp_score": 0,
                                "turn": "me",
                                "lexicon": state.lexicon,
                                "seen_letters": state.seen_letters,
                            }
                        )
                    state.history = []
                    state.snapshots = []
                elif 0 <= turn_index < len(state.history):
                    snapshot = state.history[turn_index].get("snapshot_after")
                    if snapshot:
                        state.restore(snapshot)
                        state.history = state.history[: turn_index + 1]
                        state.snapshots = state.snapshots[: turn_index + 1]
            elif action == "import_board":
                board_text = request.form.get("board_text", "")
                state.board = _text_to_grid(board_text)
            elif action == "import_state":
                payload = request.form.get("state_payload", "").strip()
                parsed = json.loads(payload)
                state.board = parsed["board"]
                state.my_rack = parsed.get("my_rack", "")
                state.my_score = int(parsed.get("my_score", 0))
                state.opp_score = int(parsed.get("opp_score", 0))
                state.turn = parsed.get("turn", "me")
                state.lexicon = parsed.get("lexicon", "classic")
                state.seen_letters = parsed.get("seen_letters", "")
                state.history = parsed.get("history", [])
                state.snapshots = []
            elif action == "set_grid":
                state.board = _grid_from_request(15)
            elif action == "infer_diff":
                new_grid = _grid_from_request(15)
                actor = request.form.get("actor", "opponent")
                added, word, row, col, direction, err = _infer_move_from_diff(state.board, new_grid)
                if err:
                    raise ValueError(err)
                game = _setup_companion_game(state)
                if actor != "me":
                    game.turn = 2
                move, build_err = _build_move_from_word(game, word, row, col, direction, actor)
                if move is None:
                    raise ValueError(build_err)
                if not game.is_legal(move):
                    raise ValueError(game.explain_illegal_move(move))
                preview = _apply_companion_move(state, actor, move, word)
            elif action == "shorthand":
                actor, row, col, direction, word = _parse_shorthand_move(request.form.get("shorthand", ""))
                game = _setup_companion_game(state)
                if actor != "me":
                    game.turn = 2
                move, build_error = _build_move_from_word(game, word, row, col, direction, actor)
                if move is None:
                    raise ValueError(build_error)
                if not game.is_legal(move):
                    raise ValueError(game.explain_illegal_move(move))
                preview = _apply_companion_move(state, actor, move, word)
            elif action in ("preview_move", "apply_move"):
                actor = request.form.get("actor", state.turn)
                row = int(request.form.get("start_row", "-1"))
                col = int(request.form.get("start_col", "-1"))
                direction = request.form.get("direction", "horizontal")
                word = request.form.get("word", "")
                allow_illegal = request.form.get("allow_illegal", "") == "on"
                manual_score = int(request.form.get("manual_score", "0") or "0")
                game = _setup_companion_game(state)
                if actor != "me":
                    game.turn = 2
                move, build_error = _build_move_from_word(game, word, row, col, direction, actor)
                if move is None:
                    raise ValueError(build_error)
                legal = game.is_legal(move)
                if (not legal) and (not allow_illegal):
                    raise ValueError(game.explain_illegal_move(move))
                if action == "preview_move":
                    preview = _move_summary(game, move)
                    preview["actor"] = actor
                    preview["legal"] = legal
                else:
                    if legal:
                        best_score = None
                        if actor == "me":
                            top_moves = _sorted_suggestions(game, limit=1)
                            if top_moves:
                                best_score = game.score_move(top_moves[0])
                        summary = _apply_companion_move(state, actor, move, word, best_score=best_score)
                    else:
                        changed = [
                            (
                                placement.location.position.row,
                                placement.location.position.col,
                                placement.tile.letter.upper() if placement.tile.wildcard else placement.tile.letter,
                            )
                            for placement in move.placements
                        ]
                        summary = _apply_raw_board_diff(
                            state=state,
                            actor=actor,
                            changed_tiles=changed,
                            entered_word=word,
                            direction=direction,
                            score=manual_score,
                        )
                        summary["legal"] = False
                    preview = summary
            elif action == "suggest":
                pass
        except Exception as exc:  # pragma: no cover
            error = str(exc)

    try:
        game = _setup_companion_game(state)
        limit = int(request.values.get("limit", "30"))
        min_score = int(request.values.get("min_score", "0"))
        sort_by = request.values.get("sort_by", "score")
        raw = _sorted_suggestions(game, limit=200)
        summaries = [_move_summary(game, move) for move in raw]
        summaries = [summary for summary in summaries if summary["score"] >= min_score]
        if sort_by == "leave":
            summaries.sort(key=lambda item: (item["leave_quality"], item["score"]), reverse=True)
        else:
            summaries.sort(key=lambda item: (item["score"], -item["leave_quality"]), reverse=True)
        suggestions = summaries[:limit]
    except Exception as exc:  # pragma: no cover
        error = str(exc)

    return render_template(
        "companion.html",
        state=state,
        suggestions=suggestions,
        preview=preview,
        error=error,
        board_text=_grid_to_text(state.board),
        state_payload=state.to_json(),
        unseen_counts=_unseen_pool_counts(state),
        best_gap=(
            round(
                sum(entry.get("best_gap", 0) for entry in state.history if entry.get("actor") == "me")
                / max(1, len([h for h in state.history if h.get("actor") == "me"])),
                2,
            )
        ),
    )


@app.route("/companion/export")
def companion_export() -> ResponseReturnValue:
    payload = COMPANION_STATE.to_json()
    response = make_response(payload)
    response.headers["Content-Type"] = "application/json"
    response.headers["Content-Disposition"] = "attachment; filename=companion_state.json"
    return response


@app.route("/play/new", methods=["POST"])
def play_new() -> ResponseReturnValue:
    global PLAY_STATE
    seed = request.form.get("seed", "").strip()
    if seed:
        np.random.seed(int(seed))

    ai_strategy = request.form.get("ai_strategy", DEFAULT_AI_STRATEGY).strip().lower()
    ai_model_choice = request.form.get("ai_model_choice", "").strip()
    ai_model_path = request.form.get("ai_model_path", "").strip()
    if ai_model_choice:
        ai_model_path = ai_model_choice
    if not ai_model_path:
        ai_model_path = DEFAULT_AI_MODEL
    ai_epsilon_raw = request.form.get("ai_epsilon", str(DEFAULT_AI_EPSILON)).strip()
    try:
        ai_epsilon = float(ai_epsilon_raw)
    except ValueError:
        ai_epsilon = DEFAULT_AI_EPSILON

    game_seed = int(seed) if seed else None
    ai_engine, warning = _build_engine(
        strategy_name=ai_strategy,
        model_path=ai_model_path,
        epsilon=ai_epsilon,
        seed=game_seed,
    )

    game = Game(DICTIONARY)
    game.start()
    game.next()
    suggestions = _sorted_suggestions(game, engine=ai_engine)
    ai_reasoning = _ai_reasoning(game, ai_engine)
    PLAY_STATE = PlayState(
        game=game,
        suggestions=suggestions,
        engine=ai_engine,
        ai_strategy=ai_strategy,
        ai_model_path=ai_model_path,
        ai_epsilon=ai_epsilon,
        ai_reasoning=ai_reasoning,
        human_analysis=[],
        message=warning,
    )
    return redirect(url_for("play"))


@app.route("/play", methods=["GET"])
def play() -> ResponseReturnValue:
    if PLAY_STATE is None:
        return render_template("play.html", ready=False, model_paths=_available_model_paths())

    game = PLAY_STATE.game
    suggestion_summaries = [_move_summary(game, move) for move in PLAY_STATE.suggestions]
    payloads = [_serialize_move(move) for move in PLAY_STATE.suggestions]
    rack = [
        {
            "id": i,
            "token": "?" if tile.wildcard else tile.letter,
            "label": tile.letter.upper() if not tile.wildcard else "?",
            "wildcard": tile.wildcard,
        }
        for i, tile in enumerate(game.players.a.tiles)
    ]
    return render_template(
        "play.html",
        ready=True,
        board_view=_play_board_view(game),
        game=game,
        rack=rack,
        suggestions=suggestion_summaries,
        payloads=payloads,
        message=PLAY_STATE.message,
        ai_strategy=PLAY_STATE.ai_strategy,
        ai_model_path=PLAY_STATE.ai_model_path,
        ai_epsilon=PLAY_STATE.ai_epsilon,
        ai_reasoning=PLAY_STATE.ai_reasoning,
        human_analysis=PLAY_STATE.human_analysis,
        model_paths=_available_model_paths(),
    )


@app.route("/play/action", methods=["POST"])
def play_action() -> ResponseReturnValue:
    global PLAY_STATE
    if PLAY_STATE is None:
        return redirect(url_for("play"))

    game = PLAY_STATE.game
    payload = request.form.get("move_payload", "")
    manual_payload = request.form.get("manual_payload", "")
    action: Move | ExchangeMove | PassMove
    try:
        if manual_payload:
            action = _build_manual_move(game, manual_payload)
        elif payload:
            action = _deserialize_move(game, payload)
        else:
            action = PassMove()

        if isinstance(action, Move) and not game.is_legal(action):
            raise ValueError(game.explain_illegal_move(action))

        if isinstance(action, Move):
            top_moves = _sorted_suggestions(game, limit=5, engine=PLAY_STATE.engine)
            chosen_score = game.score_move(action)
            top_score = game.score_move(top_moves[0]) if top_moves else chosen_score
            PLAY_STATE.human_analysis.append(
                {
                    "round": game.round,
                    "turn": game.turn,
                    "chosen_score": chosen_score,
                    "top_score": top_score,
                    "gap": top_score - chosen_score,
                    "chosen": _move_summary(game, action),
                }
            )

        game.apply_action(action)
        if game.next():
            PLAY_STATE.ai_reasoning = _ai_reasoning(game, PLAY_STATE.engine)
            ai_action = PLAY_STATE.engine.select_action(game, game.active_player, verbose=False)
            game.apply_action(ai_action)
        if game.next():
            PLAY_STATE.suggestions = _sorted_suggestions(game, engine=PLAY_STATE.engine)
            PLAY_STATE.ai_reasoning = _ai_reasoning(game, PLAY_STATE.engine)
        else:
            PLAY_STATE.suggestions = []
            PLAY_STATE.ai_reasoning = []
        PLAY_STATE.message = ""
    except Exception as exc:  # pragma: no cover
        PLAY_STATE.message = str(exc)
    return redirect(url_for("play"))


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
