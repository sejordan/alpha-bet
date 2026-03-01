from typing import List, Dict


def can_spell(word: str, letters: Dict[str, int], max_length: int, wildcard_count: int) -> bool:
    # make a clone of letter dict
    local_letters = dict(letters)

    if len(word) == 1 or len(word) > max_length:
        return False

    for letter in word:
        if letter not in local_letters:
            return False
        if local_letters[letter] > 0:
            local_letters[letter] -= 1
        elif wildcard_count > 0:
            wildcard_count -= 1
        else:
            return False
    
    return True


dictionary: List[str] = []
with open('/usr/share/dict/words', 'r') as fh:
    for line in fh:
        dictionary.append(line.strip())


# classic
letters = 'abcdefghijklmnopqrstuvwxyz'
distribution = [9, 2, 2, 4, 12, 2, 3, 2, 9, 1, 1, 4, 2, 6, 8, 2, 1, 6, 4, 6, 4, 2, 2, 1, 2, 1]

letter_distribution = dict(zip(letters, distribution))

for word in dictionary:
    if can_spell(word, letter_distribution, max_length=15, wildcard_count=2):
        print(word)