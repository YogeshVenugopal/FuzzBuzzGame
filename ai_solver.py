"""
ai_solver.py - Hard-mode AI solver for Bulls or Cows using elimination strategy.

The AI maintains a list of all possible 4-digit combinations with unique digits.
After each guess + feedback, it filters out any combination that would NOT
produce the same bulls/cows result — drastically narrowing the search space.
This is similar to Knuth's algorithm for Mastermind.
"""

from itertools import permutations
from game_logic import calculate_bulls_and_cows


def generate_all_combinations():
    """
    Generate all valid 4-digit numbers with unique digits (0-9, no repeats).
    Leading zeros are allowed (e.g., '0123' is valid).
    Returns a list of strings.
    """
    combos = []
    for perm in permutations('0123456789', 4):
        combos.append(''.join(perm))
    return combos


def filter_candidates(candidates, guess, bulls, cows):
    """
    Filter the candidate list by removing any number that would NOT produce
    the same bulls/cows result if 'guess' were applied to it as the secret.

    This is the core elimination step:
    - For each remaining candidate, simulate: "if THIS were the secret and AI guessed 'guess', would we get (bulls, cows)?"
    - Keep only candidates where the answer is YES.
    """
    filtered = []
    for candidate in candidates:
        b, c = calculate_bulls_and_cows(candidate, guess)
        if b == bulls and c == cows:
            filtered.append(candidate)
    return filtered


def get_next_guess(candidates, guessed_set):
    """
    Choose the next best guess from the remaining candidates.

    Strategy:
    - First guess is always '0123' — a well-spread opener that maximizes information.
    - Subsequent guesses: pick the first candidate not yet guessed.
      (In a full Knuth implementation we'd use minimax; for hard mode this
       greedy "pick first valid candidate" approach solves the puzzle in ≤7 moves
       and is fast enough for a web game.)

    Returns the next guess string.
    """
    # Classic strong opener — covers 4 distinct digits from the low range
    OPENER = '0123'

    if not guessed_set:
        return OPENER

    # Pick first candidate that hasn't been guessed yet
    for candidate in candidates:
        if candidate not in guessed_set:
            return candidate

    # Fallback (should never happen in normal play)
    return candidates[0] if candidates else '0123'


class AIBrainHard:
    """
    Stateful AI solver for hard-mode Bulls or Cows.
    Keeps all state as plain dicts/lists so it can be stored in Flask session.
    """

    @staticmethod
    def initial_state():
        """Return a fresh solver state dict to store in session."""
        return {
            'guessed': [],           # history of AI's own guesses
            'current_guess': None,   # the current pending guess
        }

    @staticmethod
    def make_guess(state):
        """
        Choose next guess, record it, and update state.
        Returns (guess_string, updated_state).
        """
        # Regenerate candidates to filter based on previous feedback
        all_candidates = generate_all_combinations()
        candidates = all_candidates
        
        # Reconstruct the candidate list by replaying history
        # This avoids storing ~5040 numbers in the session
        guessed_list = state.get('guessed', [])
        for i, guess_entry in enumerate(guessed_list):
            guess = guess_entry['guess']
            bulls = guess_entry['bulls']
            cows = guess_entry['cows']
            candidates = filter_candidates(candidates, guess, bulls, cows)
        
        guessed_set = set([g['guess'] for g in guessed_list])
        guess = get_next_guess(candidates, guessed_set)
        state['current_guess'] = guess
        return guess, state

    @staticmethod
    def apply_feedback(state, bulls, cows):
        """
        Apply human-provided feedback (bulls, cows) for the current guess.
        Records the guess with its feedback for future candidate filtering.
        Returns updated_state.
        """
        guess = state['current_guess']
        if guess is None:
            return state

        # Record guess with feedback (we'll use this to filter candidates later)
        guessed_list = state.get('guessed', [])
        guessed_list.append({'guess': guess, 'bulls': bulls, 'cows': cows})
        state['guessed'] = guessed_list
        state['current_guess'] = None

        return state