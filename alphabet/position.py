from __future__ import annotations

from typing import List
import enum

class Axis(enum.StrEnum):
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'

class Position:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    
    def delta(self, axis: Axis, magnitude: int):
        rowmod = 1 if axis == Axis.VERTICAL else 0
        colmod = 1 if rowmod == 0 else 0
        return (rowmod * magnitude, colmod * magnitude)
    
    def move(self, axis: Axis, magnitude: int):
        rowmod, colmod = self.delta(axis, magnitude)
        return Position(
            self.row + rowmod,
            self.col + colmod
        )

    def next(self, axis: Axis) -> Position:
        return self.move(axis, 1)

    def prev(self, axis: Axis) -> Position:
        return self.move(axis, -1)
    
    def neighbors(self) -> List[Position]:
        return [
            self.prev(Axis.VERTICAL),
            self.next(Axis.VERTICAL),
            self.prev(Axis.HORIZONTAL),
            self.next(Axis.HORIZONTAL)
        ]
