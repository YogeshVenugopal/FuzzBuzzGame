"""
game_logic.py - Core game logic for Bulls or Cows
"""


def validate_number(number_str):
    """
    Validate that the input is a 4-digit number with all unique digits.
    Returns (is_valid: bool, error_message: str)
    """
    if not number_str or not isinstance(number_str, str):
        return False, "Input must be a string."

    number_str = number_str.strip()

    if len(number_str) != 4:
        return False, "Number must be exactly 4 digits."

    if not number_str.isdigit():
        return False, "Number must contain digits only."

    if len(set(number_str)) != 4:
        return False, "All digits must be unique (no repeating digits)."

    return True, ""


def calculate_bulls_and_cows(secret, guess):
    """
    Calculate Bulls and Cows for a given guess against the secret number.
    
    Bull  = correct digit in correct position
    Cow   = correct digit in wrong position
    
    Returns (bulls: int, cows: int)
    """
    bulls = 0
    cows = 0

    for i in range(4):
        if guess[i] == secret[i]:
            bulls += 1
        elif guess[i] in secret:
            cows += 1

    return bulls, cows


def is_winner(bulls):
    """Check if the player has won (4 bulls = all digits correct)."""
    return bulls == 4