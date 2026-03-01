from typing import List, Tuple
import enum
from alphabet.modifier import Modifier
from alphabet.bag import LetterBag, LetterConfig
from abc import ABC, abstractmethod


class GameVariant(ABC):
    Type = enum.Enum('Type', ['CLASSIC'])

    @property
    @abstractmethod
    def name(self) -> Type:
        raise NotImplementedError("Method not implemented!")

    @property
    @abstractmethod
    def n(self) -> int:
        raise NotImplementedError("Method not implemented!")
    
    @property
    @abstractmethod
    def starting_tiles(self) -> int:
        raise NotImplementedError("Method not implemented!")
    
    @property
    @abstractmethod
    def modifiers(self) -> List[List[Tuple[int, Modifier]]]:
        raise NotImplementedError("Method not implemented!")

    @abstractmethod
    def create_bag(self) -> LetterBag:
        raise NotImplementedError("Method not implemented!")


class Classic(GameVariant):
    
    @property
    def name(self) -> GameVariant.Type:
        return GameVariant.Type.CLASSIC

    @property
    def starting_tiles(self) -> int:
        return 7
    
    @property
    def n(self) -> int:
        return 15

    @property
    def modifiers(self) -> List[List[Tuple[int, Modifier]]]:
        return [
            [ # Row=0
                ( 0, Modifier.TRIPLE_WORD),
                ( 3, Modifier.DOUBLE_LETTER),
                ( 7, Modifier.TRIPLE_WORD),
                (11, Modifier.DOUBLE_LETTER),
                (14, Modifier.TRIPLE_WORD),
            ],
            [ # Row=1
                ( 1, Modifier.DOUBLE_WORD),
                ( 5, Modifier.TRIPLE_LETTER),
                ( 9, Modifier.TRIPLE_LETTER),
                (13, Modifier.DOUBLE_WORD),
            ],
            [ # Row=2
                ( 2, Modifier.DOUBLE_WORD),
                ( 6, Modifier.DOUBLE_LETTER),
                ( 8, Modifier.DOUBLE_LETTER),
                (12, Modifier.DOUBLE_WORD),
            ],
            [ # Row=3
                ( 0, Modifier.DOUBLE_LETTER),
                ( 3, Modifier.DOUBLE_WORD),
                ( 7, Modifier.DOUBLE_LETTER),
                (11, Modifier.DOUBLE_WORD),
                (14, Modifier.DOUBLE_LETTER),
            ],
            [ # Row=4
                ( 4, Modifier.DOUBLE_WORD),
                (10, Modifier.DOUBLE_WORD),
            ],
            [ # Row=5
                ( 1, Modifier.TRIPLE_LETTER),
                ( 5, Modifier.TRIPLE_LETTER),
                ( 9, Modifier.TRIPLE_LETTER),
                (13, Modifier.TRIPLE_LETTER),
            ],
            [ # Row=6
                ( 2, Modifier.DOUBLE_LETTER),
                ( 6, Modifier.DOUBLE_LETTER),
                ( 8, Modifier.DOUBLE_LETTER),
                (12, Modifier.DOUBLE_LETTER),
            ],
            [ # Row=7
                ( 0, Modifier.TRIPLE_WORD),
                ( 3, Modifier.DOUBLE_LETTER),
                ( 7, Modifier.DOUBLE_WORD),
                (11, Modifier.DOUBLE_LETTER),
                (14, Modifier.TRIPLE_WORD),
            ],
            [ # Row=8
                ( 2, Modifier.DOUBLE_LETTER),
                ( 6, Modifier.DOUBLE_LETTER),
                ( 8, Modifier.DOUBLE_LETTER),
                (12, Modifier.DOUBLE_LETTER),
            ],
            [ # Row=9
                ( 1, Modifier.TRIPLE_LETTER),
                ( 5, Modifier.TRIPLE_LETTER),
                ( 9, Modifier.TRIPLE_LETTER),
                (13, Modifier.TRIPLE_LETTER),
            ],
            [ # Row=10
                ( 4, Modifier.DOUBLE_WORD),
                (10, Modifier.DOUBLE_WORD),
            ],
            [ # Row=11
                ( 0, Modifier.DOUBLE_LETTER),
                ( 3, Modifier.DOUBLE_WORD),
                ( 7, Modifier.DOUBLE_LETTER),
                (11, Modifier.DOUBLE_WORD),
                (14, Modifier.DOUBLE_LETTER),
            ],
            [ # Row=12
                ( 2, Modifier.DOUBLE_WORD),
                ( 6, Modifier.DOUBLE_LETTER),
                ( 8, Modifier.DOUBLE_LETTER),
                (12, Modifier.DOUBLE_WORD),
            ],
            [ # Row=13
                ( 1, Modifier.DOUBLE_WORD),
                ( 5, Modifier.TRIPLE_LETTER),
                ( 9, Modifier.TRIPLE_LETTER),
                (13, Modifier.DOUBLE_WORD),
            ],
            [ # Row=14
                ( 0, Modifier.TRIPLE_WORD),
                ( 3, Modifier.DOUBLE_LETTER),
                ( 7, Modifier.TRIPLE_WORD),
                (11, Modifier.DOUBLE_LETTER),
                (14, Modifier.TRIPLE_WORD),
            ],
        ]
    
    def create_bag(self) -> LetterBag:
        letters = 'abcdefghijklmnopqrstuvwxyz?'
        distribution = [9, 2, 2, 4, 12, 2, 3, 2, 9, 1, 1, 4, 2, 6, 8, 2, 1, 6, 4, 6, 4, 2, 2, 1, 2, 1, 2]
        values = [1, 3, 3, 2, 1, 4, 2, 4, 1, 8, 5, 1, 3, 1, 0, 1, 10, 1, 1, 1, 1, 4, 4, 8, 4, 10, 0]

        config = { letter: LetterConfig(quantity=distribution[i], value=values[i]) for i, letter in enumerate(letters) }
        return LetterBag(config)

class VariantFactory():

    @staticmethod
    def build(variant_type: GameVariant.Type) -> GameVariant:
        match variant_type:
            case GameVariant.Type.CLASSIC:
                return Classic()
        raise RuntimeError("Unsupported game variant")
