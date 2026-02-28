from typing import List, NamedTuple

import enum
from alphabet.game import Game, Player
from alphabet.board import Board, Square
from alphabet.modifier import Modifier

ANSI_RESET = "\033[0m"
BRIGHT_MODIFIER = 60

class Foreground(enum.IntEnum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    @enum.property
    def bright(self) -> int:
        return self.value + BRIGHT_MODIFIER
    
    @enum.property
    def ansi(self) -> int:
        return self.value

class Background(enum.IntEnum):
    BLACK = 40
    RED = 41
    GREEN = 42
    YELLOW = 43
    BLUE = 44
    MAGENTA = 45
    CYAN = 46
    WHITE = 47

    @enum.property
    def bright(self) -> int:
        return self.value + BRIGHT_MODIFIER
    
    @enum.property
    def ansi(self) -> int:
        return self.value

class ModifierColor(NamedTuple):
    fg: Foreground
    bg: Background

MODIFIER_COLOR_MAP = {
    Modifier.TRIPLE_WORD:   ModifierColor(fg=Foreground.WHITE, bg=Background.BLUE),
    Modifier.DOUBLE_WORD:   ModifierColor(fg=Foreground.WHITE, bg=Background.RED),
    Modifier.TRIPLE_LETTER: ModifierColor(fg=Foreground.WHITE, bg=Background.CYAN),
    Modifier.DOUBLE_LETTER: ModifierColor(fg=Foreground.WHITE, bg=Background.MAGENTA),
    Modifier.NONE:          ModifierColor(fg=Foreground.BLACK, bg=Background.WHITE),
}

class SquareDisplay:

    Section = enum.StrEnum('Section', ['HEAD', 'MID', 'FOOT'])

    @staticmethod
    def present(square: Square, section: Section) -> None:
        color = MODIFIER_COLOR_MAP[square.modifier]

        content = ""
        if section == SquareDisplay.Section.MID:
            if square.tile is not None:
                content = square.tile.letter.upper()
                if square.tile.wildcard:
                    content += "?"
            else:
                if square.modifier == Modifier.NONE:
                    content = ""
                elif square.special_display:
                    content = square.special_display
                else:
                    content = "x".join(list(square.modifier.value))

            border_color = f"{ANSI_RESET}\033[{Foreground.BLACK.ansi};{color.bg.ansi}m"
            content_color = f"{ANSI_RESET}\033[{color.fg.ansi};{color.bg.ansi}m"
            content = f"{border_color}│{content_color}{content.center(5)}{border_color}│{ANSI_RESET}"

        elif section == SquareDisplay.Section.HEAD:
            content = f"\033[{Foreground.BLACK.ansi};{color.bg.ansi}m┌─────┐{ANSI_RESET}"
        else:
            content = f"\033[{Foreground.BLACK.ansi};{color.bg.ansi}m└─────┘{ANSI_RESET}"


        print(f"\033[{color.fg.ansi}m{content}{ANSI_RESET}", end="")

class BoardDisplay:
    @staticmethod
    def present(board: Board) -> None:
        for row in board.get_board():
            BoardDisplay.display_row(row, section=SquareDisplay.Section.HEAD)
            BoardDisplay.display_row(row, section=SquareDisplay.Section.MID)
            BoardDisplay.display_row(row, section=SquareDisplay.Section.FOOT)

    @staticmethod
    def display_row(row: List[Square], section: SquareDisplay.Section) -> None:
        for square in row:
            SquareDisplay.present(square, section)
        print("")

class PlayerDisplay:
    @staticmethod
    def present(player: Player):

        name_display = f" {player.name} "
        tile_display = " ".join(map(lambda x: f"{x.letter.upper()}".center(3), player.tiles))
        tile_display = f" Letter  {tile_display}"
        value_display = " ".join(map(lambda x: f"{x.value}".center(3), player.tiles))
        value_display = f"  Value  {value_display}"
        
        box_width = max(len(name_display), len(tile_display), len(value_display))

        full_bar = "═" * box_width

        name_display = name_display.center(box_width)
        tile_display = tile_display.ljust(box_width)
        value_display = value_display.ljust(box_width)

        print("")
        print(f"╔{full_bar}╗")
        print(f"║{name_display}║")
        print(f"╠{full_bar}╣")
        print(f"║{tile_display}║")
        print(f"║{value_display}║")
        print(f"╚{full_bar}╝")

class ScoreboardDisplay:
    @staticmethod
    def present(game: Game):
        """
        Displays the game's score

        Example
        -------
        ╔══════════════════════════════════╗
        ║           SCOREBOARD             ║
        ╠════════════════╦═════════════════╣
        ║   Player A     ║    Player B     ║
        ╠════════════════╬═════════════════╣
        ║       0        ║        0        ║
        ╚════════════════╩═════════════════╝
        """

        player_title_width = 2 + max(14, len(game.players.a.name), len(game.players.b.name))
        player_a_title = game.players.a.name.center(player_title_width)
        player_b_title = game.players.b.name.center(player_title_width)

        scoreboard_width = 1 + len(player_a_title) + len(player_b_title)

        full_bar = "═" * scoreboard_width
        half_bar = "═" * (scoreboard_width // 2)
        half_bar_thin = "─" * (scoreboard_width // 2)
        scoreboard_title = "SCOREBOARD".center(scoreboard_width)
        player_a_score = f"{game.players.a.score}".center(player_title_width)
        player_b_score = f"{game.players.b.score}".center(player_title_width)

        print(f"╔{full_bar}╗")
        print(f"║{scoreboard_title}║")
        print(f"╠{half_bar}╤{half_bar}╣")
        print(f"║{player_a_title}│{player_b_title}║")
        print(f"╟{half_bar_thin}┼{half_bar_thin}╢")
        print(f"║{player_a_score}│{player_b_score}║")
        print(f"╚{half_bar}╧{half_bar}╝")


class GameDisplay:
    @staticmethod
    def present(game: Game, display_opponent: bool = True) -> None:
        BoardDisplay.present(game.board)
        ScoreboardDisplay.present(game)

        print(f"Remaining Letters: {game.bag.total_tiles}")

        PlayerDisplay.present(game.players.a)

        if display_opponent:
            PlayerDisplay.present(game.players.b)


