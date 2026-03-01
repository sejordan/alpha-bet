from typing import List
import pandas as pd

def word_fits_template(word: str, template: List[None | str]) -> bool:
    # if they aren't the same length, then its a definite no...
    if len(word) != len(template):
        return False
        
    # iterate through the template
    for index, slot in enumerate(template):
        # if the slot is a blank, its a free-pass .. any character fits
        # otherwise, the word has to match the template at this slot-index
        if slot is not None and word[index] != slot:
            return False
        
    return True


def fill_template(dictionary: pd.Series, template: List[None | str]) -> List[str]:
    """
    Returns a list of words that complete the provided template
    """
    words: List[str] = []

    # TODO:
    # this algorithm is super brute-force, come up with something faster
    for word in dictionary:
        if word_fits_template(word, template):
            words.append(word)

    return words