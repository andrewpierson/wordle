import copy
import sys
import string
import time
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


class WordSetMetaIterator:
    def __init__(self, wsm):
        self.wsm = wsm
        self.next_index = 0

    def __next__(self):
        while self.next_index < len(self.wsm.words):
            self.next_index += 1
            if self.wsm.words[self.next_index - 1].is_included():
                return self.wsm.words[self.next_index - 1]
        raise StopIteration


class WordSetMeta:
    def __init__(self):
        self.letter_count = {}
        self.words = []
        self.memo_pad = {}

    def __len__(self):
        # return len(self.words)
        count = 0
        for word in self.words:
            if word.is_included():
                count += 1
        return count

    def __iter__(self):
        return WordSetMetaIterator(self)

    def add_word(self, word):
        self.words.append(Word(word))
        # Despite initialization, there are weird characters
        for l in word:
            if l in self.letter_count:
                self.letter_count[l] += 1
            else:
                self.letter_count[l] = 1

    def update_keys(self):
        for word in self.words:
            word.add_keys(self.letter_count.keys())

    def reset_memos(self):
        for word in self.words:
            word.reset_memo()

    def remove_words_if_letter_at_position(self, letter, position, exists, is_permanent):
        for word in self.words:
            if word.exclude_if_letter_at_position(
                    letter, position, exists, is_permanent) and is_permanent:
                # Optimization to reduce future search space by culling the list at the start.
                self.words.remove(word)

    def remove_words_if_has_letter(self, letter, exists, is_permanent):
        for word in self.words:
            if word.exclude_if_has_letter(letter, exists, is_permanent) and is_permanent:
                # Optimization to reduce future search space by culling the list at the start.
                self.words.remove(word)


# Each guess is 5 letters, preceeded by:
# . for an incorrect guess (character is ignored)
# - for a letter in the wrong location
# = for a letter in the right location

def handle_perfect_match(words, letter, index, is_permanent):
    words.remove_words_if_letter_at_position(
        letter, index, False, is_permanent)


def handle_partial_match(words, letter, index, is_permanent):
    words.remove_words_if_letter_at_position(
        letter, index, True, is_permanent)
    words.remove_words_if_has_letter(letter, False, is_permanent)


def handle_negative_match(words, letter, index, is_permanent):
    words.remove_words_if_has_letter(letter, True, is_permanent)


def eliminate_impossible_words(prior_guesses, words, is_permanent):
    if prior_guesses == None:
        return
    # print("    Eliminating words.  Starting count=" + str(len(words)), end='')
    for guess in prior_guesses:
        action = 0
        index = 0
        next_char_is_action = True
        for l in guess:
            if next_char_is_action:
                if l == '=':
                    action = 1
                elif l == '-':
                    action = 2
                elif l == '.':
                    action = 3
                else:
                    print("Invalid action: " + l)
                    sys.exit(l)
                next_char_is_action = False
            else:
                # print(l)
                if action == 1:
                    handle_perfect_match(words, l, index, is_permanent)
                elif action == 2:
                    handle_partial_match(words, l, index, is_permanent)
                elif action == 3:
                    handle_negative_match(words, l, index, is_permanent)
                action = 0
                index += 1
                next_char_is_action = True
    # print(" Ending count=" + str(len(words)))


def make_guess(words, guess, answer):
    # iterating through guess
    for i in range(5):
        if answer.has_letter_at_position(guess.letter_at_position(i), i):
            handle_perfect_match(words, guess.letter_at_position(i), i, False)
        elif answer.has_letter(guess.letter_at_position(i)):
            handle_partial_match(words, guess.letter_at_position(i), i, False)
        else:
            handle_negative_match(words, guess.letter_at_position(i), i, False)
    return len(words)


def get_best_gueess(words):
    # initialize with worst case
    best_guess = ''
    work_done = 0
    work_to_do = len(words)
    score = work_to_do * work_to_do
    if work_to_do == 1:
        # Use the iterator to get the only valid one
        for word in words:
            return word
    #pool = ThreadPool(processes=32)
    for possible_next_guess in words:
        sys.stdout.write('\r' + str(work_done) + "/" + str(work_to_do))
        sys.stdout.flush()
        work_done += 1
        start_time = time.perf_counter()
        sum_score = 0
        async_results = []
        for possible_answer in words:
            #words_copy = copy.deepcopy(words)
            # async_results.append(pool.apply_async(
            # make_guess, (words_copy, possible_next_guess, possible_answer)))
            sum_score += make_guess(words,
                                    possible_next_guess, possible_answer)
            words.reset_memos()
        # for r in async_results:
            #sum_score += r.get()
        if sum_score < score:
            # print("  best score!=" + str(sum_score))
            score = sum_score
            best_guess = possible_next_guess
        work_duration = time.perf_counter() - start_time
        # if work_duration > 1.0:
        # print(" ! " + possible_next_guess.word + " took " +
        # str(work_duration) + " seconds!")
    return best_guess


def main():
    print("Processing inputs...")
    prior_guesses = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if len(arg) < 10:
                print("Invalid argument of length != 10")
                sys.exit(arg)
            guess = []
            for l in arg:
                guess.append(l)
            prior_guesses.append(guess)
    words = WordSetMeta()
    # with open('test.words') as f:
    with open('five.letter.words') as f:
        for line in f:
            words.add_word(line.rstrip())
    words.update_keys()
    print("Found " + str(len(words)) + " words, and " +
          str(len(prior_guesses)) + " guesses.")
    print("Eliminating impossible words...")
    eliminate_impossible_words(prior_guesses, words, True)
    print("Finding best guess of " + str(len(words)) + " remaining words...")
    for word in words:
        print(word.word)
    best_guess = get_best_gueess(words).word
    print("\nbest guess = " + best_guess)


if __name__ == "__main__":
    main()
