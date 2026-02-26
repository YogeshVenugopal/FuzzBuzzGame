"""
ai_solver.py - Hard-mode AI solver for Bulls or Cows using elimination strategy.

The AI maintains a list of all possible 4-digit combinations with unique digits.
After each guess + feedback, it filters out any combination that would NOT
produce the same bulls/cows result — drastically narrowing the search space.
This is similar to Knuth's algorithm for Mastermind.

Key design:
- The human THINKS of a number; it is NEVER stored on the server.
- The AI learns purely from the honest feedback the human provides.
- No cheating: the AI cannot verify feedback against any stored secret.
"""

from itertools import permutations
from game_logic import calculate_bulls_and_cows


def generate_all_combinations():
    """
    Generate all valid 4-digit numbers with unique digits (0-9, no repeats).
    Leading zeros are allowed (e.g., '0123' is valid).
    Returns a list of strings.
    """
    return [''.join(p) for p in permutations('0123456789', 4)]


def filter_candidates(candidates, guess, bulls, cows):
    """
    Keep only candidates that would produce the same (bulls, cows) result
    if 'guess' were applied to them as the secret.
    """
    filtered = []
    for candidate in candidates:
        b, c = calculate_bulls_and_cows(candidate, guess)
        if b == bulls and c == cows:
            filtered.append(candidate)
    return filtered


def get_candidates_from_history(history):
    """Rebuild the candidate list by replaying all prior guesses + feedback."""
    candidates = generate_all_combinations()
    for entry in history:
        candidates = filter_candidates(candidates, entry['guess'], entry['bulls'], entry['cows'])
    return candidates


def get_next_guess(candidates, guessed_set):
    """
    Choose the next best guess.

    Strategy:
    - First guess: '0123' — a strong opener that probes 4 distinct digits.
    - Subsequent guesses: use a minimax-style pick.
      For each possible guess (from the full set), compute the worst-case
      partition size. Pick the guess that minimises the worst-case remaining
      candidates. Prefer guesses that are still in the candidate pool (they
      could be the answer).

    Falls back to first unguessed candidate if pool is small enough.
    """
    OPENER = '0123'

    if not guessed_set:
        return OPENER

    # If only 1 or 2 candidates left, just guess them directly
    unguessed_candidates = [c for c in candidates if c not in guessed_set]
    if len(candidates) <= 2:
        return unguessed_candidates[0] if unguessed_candidates else candidates[0]

    # Minimax: evaluate every possible guess from the full pool
    # but cap at a reasonable subset to keep it fast for a web game
    all_combos = generate_all_combinations()

    best_guess = None
    best_score = float('inf')
    # prefer guesses still in candidates (they might be the answer)
    candidate_set = set(candidates)

    # To keep response time reasonable, evaluate candidates first,
    # then all_combos if needed. With 5040 total this is fast enough.
    eval_pool = list(candidates) + [c for c in all_combos if c not in candidate_set]

    for guess in eval_pool:
        if guess in guessed_set:
            continue

        # Partition remaining candidates by (bulls, cows) outcome
        partitions = {}
        for secret in candidates:
            result = calculate_bulls_and_cows(secret, guess)
            partitions[result] = partitions.get(result, 0) + 1

        # Worst-case partition size (minimax criterion)
        worst = max(partitions.values())

        # Prefer smaller worst-case; break ties by preferring in-candidate guesses
        in_candidates = guess in candidate_set
        score = (worst, 0 if in_candidates else 1)

        if score < (best_score, 0 if (best_guess in candidate_set if best_guess else False) else 1):
            best_score = worst
            best_guess = guess

    return best_guess if best_guess else (unguessed_candidates[0] if unguessed_candidates else candidates[0])


class AIBrainHard:
    """
    Stateful AI solver for hard-mode Bulls or Cows.
    State stored as plain dicts/lists for Flask session serialization.
    The AI never knows the human's secret — it only uses feedback.
    """

    @staticmethod
    def initial_state():
        """Return a fresh solver state dict."""
        return {
            'guessed': [],          # list of {guess, bulls, cows}
            'current_guess': None,  # pending guess awaiting feedback
        }

    @staticmethod
    def make_guess(state):
        """
        Choose next guess using minimax elimination, record it, return it.
        Returns (guess_string, updated_state).
        """
        guessed_list = state.get('guessed', [])
        candidates = get_candidates_from_history(guessed_list)
        guessed_set = {g['guess'] for g in guessed_list}

        guess = get_next_guess(candidates, guessed_set)
        state['current_guess'] = guess
        return guess, state

    @staticmethod
    def apply_feedback(state, bulls, cows):
        """
        Record the human's feedback for the current pending guess.
        This narrows the candidate pool for the next guess.
        Returns updated_state.
        """
        guess = state.get('current_guess')
        if guess is None:
            return state

        guessed_list = state.get('guessed', [])
        guessed_list.append({'guess': guess, 'bulls': bulls, 'cows': cows})
        state['guessed'] = guessed_list
        state['current_guess'] = None
        return state