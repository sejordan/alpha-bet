from typing import List, NamedTuple

import enum
from alphabet.game import Game
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


class GameDisplay:
    @staticmethod
    def present(game: Game) -> None:
        BoardDisplay.present(game.board)

