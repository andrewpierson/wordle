import copy
import pickle
import sys
import string
import time
from typing import Tuple
from multiprocessing.pool import ThreadPool


class Word:
    def __init__(self, word):
        self.letter_count = {}
        self.word = word
        self.is_permanently_included = True
        self.is_temporarily_included = True
        self.is_included_derived_cache = self.is_permanently_included and self.is_temporarily_included
        for l in word:
            if l in self.letter_count:
                self.letter_count[l] += 1
            else:
                self.letter_count[l] = 1

    def add_keys(self, keys):
        for k in keys:
            if not k in self.letter_count:
                self.letter_count[k] = 0

    def is_included(self):
        return self.is_included_derived_cache

    def letter_at_position(self, position):
        return self.word[position]

    def has_letter(self, letter):
        return letter in self.letter_count and self.letter_count[letter] > 0

    def has_letter_at_position(self, letter, position):
        return self.word[position] == letter

    def exclude_word(self, is_permanent):
        if is_permanent:
            self.is_permanently_included = False
        else:
            self.is_temporarily_included = False
        self.is_included_derived_cache = self.is_permanently_included and self.is_temporarily_included

    def reset_memo(self):
        self.is_temporarily_included = True
        self.is_included_derived_cache = self.is_permanently_included and self.is_temporarily_included

    def exclude_if_has_letter(self, letter, exists, is_permanent):
        if self.is_included():
            # XOR logic.
            if exists == (self.letter_count[letter] > 0):
                self.exclude_word(is_permanent)
                return True
        return False

    def exclude_if_letter_at_position(self, letter, position, exists, is_permanent):
        if self.is_included():
            # XOR logic.
            if exists == (self.word[position] == letter):
                self.exclude_word(is_permanent)
                return True
        return False


# Each guess is 5 letters, preceeded by:
# . for an incorrect guess (character is ignored)
# - for a letter in the wrong location
# = for a letter in the right location


def score_guess(guess, answer) -> Tuple[int, int, int, int, int]:
    # iterating through guess
    rv = [0,0,0,0,0]
    for i in range(5):
        if answer.has_letter_at_position(guess.letter_at_position(i), i):
            rv[i] = 1
        elif answer.has_letter(guess.letter_at_position(i)):
            rv[i] = 2
        else:
            rv[i] = 3
    return rv[0], rv[1], rv[2], rv[3], rv[4]




def main():
    lookup = {}
    with open('wordle-allowed-guesses.txt') as guesses_file:
        for guess_str in guesses_file:
            print(guess_str)
            lookup[guess_str] = {}
            guess = Word(guess_str.rstrip())
            with open('wordle-answers-alphabetical.txt') as answers_file:
                for answer_str in answers_file:
                    answer = Word(answer_str.rstrip())
                    lookup[guess_str][answer_str] = score_guess(guess, answer)
    with open('lookup.pickle', 'wb') as pickle_file:
        pickle.dump(lookup, pickle_file)


if __name__ == "__main__":
    main()
