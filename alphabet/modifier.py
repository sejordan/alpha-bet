from enum import StrEnum

class Scope(StrEnum):
    LETTER = 'L'
    WORD = 'W'

class Modifier(StrEnum):
    TRIPLE_WORD = '3W'
    DOUBLE_WORD = '2W'
    TRIPLE_LETTER = '3L'
    DOUBLE_LETTER = '2L'
    NONE = '1L'

    def scope(self) -> Scope:
        return Scope(self.value[1])