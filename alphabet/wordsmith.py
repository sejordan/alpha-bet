from typing import Dict, List, Set


class Dictionary:
    def __init__(self, words: List[str]):
        self.words = list(words)
        self.word_set = set(words)
        self.words_by_length = self._build_words_by_length()
        self.position_index = self._build_position_index()
        self.template_cache: Dict[str, List[str]] = {}

    def is_valid(self, word: str) -> bool:
        return word in self.word_set

    def get_words_by_length(self, length: int) -> List[str]:
        if length not in self.words_by_length:
            return []
        return list(self.words_by_length[length])

    def _build_words_by_length(self) -> Dict[int, tuple[str, ...]]:
        grouped: Dict[int, List[str]] = {}
        for word in self.words:
            if len(word) not in grouped:
                grouped[len(word)] = []
            grouped[len(word)].append(word)
        return {length: tuple(values) for length, values in grouped.items()}

    def _build_position_index(self) -> Dict[int, List[Dict[str, Set[int]]]]:
        index: Dict[int, List[Dict[str, Set[int]]]] = {}

        for length, words in self.words_by_length.items():
            slots: List[Dict[str, Set[int]]] = [{} for _ in range(length)]
            for word_id, word in enumerate(words):
                for pos, letter in enumerate(word):
                    slot = slots[pos]
                    if letter not in slot:
                        slot[letter] = set()
                    slot[letter].add(word_id)
            index[length] = slots

        return index


def make_cache_key(template: List[None | str]) -> str:
    return "".join(["?" if x is None else x for x in template])


def fill_template(dictionary: Dictionary, template: List[None | str]) -> List[str]:
    """
    Return all words matching an exact-length positional template.
    Example: [None, "a", None] => words of len 3 with "a" at index 1.
    """
    cache_key = make_cache_key(template)
    if cache_key in dictionary.template_cache:
        return dictionary.template_cache[cache_key]

    length = len(template)
    if length not in dictionary.words_by_length:
        dictionary.template_cache[cache_key] = []
        return []

    base_words = dictionary.words_by_length[length]
    requirements: List[tuple[int, str]] = [
        (index, slot) for index, slot in enumerate(template) if slot is not None
    ]

    if len(requirements) == 0:
        result = list(base_words)
        dictionary.template_cache[cache_key] = result
        return result

    candidate_sets: List[Set[int]] = []
    slots = dictionary.position_index[length]
    for pos, letter in requirements:
        matches = slots[pos].get(letter)
        if not matches:
            dictionary.template_cache[cache_key] = []
            return []
        candidate_sets.append(matches)

    candidate_sets.sort(key=len)
    surviving_ids = set(candidate_sets[0])
    for candidates in candidate_sets[1:]:
        surviving_ids &= candidates
        if len(surviving_ids) == 0:
            dictionary.template_cache[cache_key] = []
            return []

    result = [base_words[word_id] for word_id in sorted(surviving_ids)]
    dictionary.template_cache[cache_key] = result
    return result
