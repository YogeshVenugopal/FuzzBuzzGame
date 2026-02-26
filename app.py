"""
app.py - Flask application for Bulls or Cows (Hard Mode, AI vs Human)
"""

import os
import random
from flask import Flask, render_template, request, session, jsonify, redirect, url_for

from game_logic import validate_number, calculate_bulls_and_cows, is_winner
from ai_solver import AIBrainHard, generate_all_combinations

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bulls-cows-hard-mode-secret-2024')

# ─────────────────────────────────────────────
# HUMAN'S SECRET — SET BY DEVELOPER
# ─────────────────────────────────────────────
# Change this to the human player's secret number
HUMAN_SECRET = '1234'  # Developer sets this — all 4 unique digits


# ─────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────

def pick_ai_secret():
    """Randomly choose a valid 4-digit unique-digit number for the AI's secret."""
    all_combos = generate_all_combinations()
    return random.choice(all_combos)


def error_response(message, status=400):
    return jsonify({'success': False, 'error': message}), status


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """Landing page — show rules and start button."""
    return render_template('index.html')


@app.route('/game')
def game():
    """Game screen — requires an active session."""
    if 'human_secret' not in session:
        return redirect(url_for('index'))
    return render_template('game.html')


@app.route('/start', methods=['POST'])
def start():
    """
    Initialize a new game.
    Uses the pre-set HUMAN_SECRET (set by developer).
    The AI picks its own secret internally; the human never sees it.
    """
    # Validate that the pre-set human secret is valid
    valid, msg = validate_number(HUMAN_SECRET)
    if not valid:
        return error_response(f'Invalid HUMAN_SECRET configuration: {msg}')

    # Clear any previous session
    session.clear()

    # Store game state
    session['human_secret'] = HUMAN_SECRET
    session['ai_secret'] = pick_ai_secret()
    session['ai_state'] = AIBrainHard.initial_state()
    session['human_guesses'] = []   # list of {guess, bulls, cows}
    session['ai_guesses'] = []      # list of {guess, bulls, cows}
    session['game_over'] = False
    session['winner'] = None        # 'human' | 'ai'
    session['turn'] = 'human'       # whose turn to guess next

    return jsonify({'success': True, 'redirect': '/game'})


@app.route('/human-turn', methods=['POST'])
def human_turn():
    """
    Human submits a guess against the AI's secret number.
    Expects JSON: { "guess": "5678" }
    Returns bulls, cows, and whether the human won.
    """
    if 'ai_secret' not in session:
        return error_response('No active game. Please start a new game.', 403)

    if session.get('game_over'):
        return error_response('Game is already over.')

    if session.get('turn') != 'human':
        return error_response('It is not your turn.')

    data = request.get_json()
    if not data:
        return error_response('No data provided.')

    guess = str(data.get('guess', '')).strip()
    valid, msg = validate_number(guess)
    if not valid:
        return error_response(msg)

    ai_secret = session['ai_secret']
    bulls, cows = calculate_bulls_and_cows(ai_secret, guess)
    won = is_winner(bulls)

    # Record guess
    entry = {'guess': guess, 'bulls': bulls, 'cows': cows}
    guesses = session.get('human_guesses', [])
    guesses.append(entry)
    session['human_guesses'] = guesses

    if won:
        session['game_over'] = True
        session['winner'] = 'human'
        return jsonify({
            'success': True,
            'bulls': bulls,
            'cows': cows,
            'won': True,
            'winner': 'human',
            'ai_secret': ai_secret,
        })

    # Pass turn to AI
    session['turn'] = 'ai'
    return jsonify({
        'success': True,
        'bulls': bulls,
        'cows': cows,
        'won': False,
    })


@app.route('/ai-turn', methods=['GET'])
def ai_turn():
    """
    AI generates its next guess.
    Returns the AI's guess string so the human can evaluate it.
    """
    if 'human_secret' not in session:
        return error_response('No active game.', 403)

    if session.get('game_over'):
        return error_response('Game is already over.')

    if session.get('turn') != 'ai':
        return error_response('It is not the AI\'s turn.')

    ai_state = session.get('ai_state')
    guess, ai_state = AIBrainHard.make_guess(ai_state)
    session['ai_state'] = ai_state

    return jsonify({'success': True, 'ai_guess': guess})


@app.route('/ai-feedback', methods=['POST'])
def ai_feedback():
    """
    Human provides bulls/cows feedback for the AI's last guess.
    Expects JSON: { "bulls": 1, "cows": 2 }
    AI updates its candidate list; if 4 bulls → AI wins.
    """
    if 'human_secret' not in session:
        return error_response('No active game.', 403)

    if session.get('game_over'):
        return error_response('Game is already over.')

    if session.get('turn') != 'ai':
        return error_response('It is not the AI\'s turn.')

    data = request.get_json()
    if not data:
        return error_response('No data provided.')

    try:
        bulls = int(data.get('bulls', -1))
        cows = int(data.get('cows', -1))
    except (TypeError, ValueError):
        return error_response('Bulls and cows must be integers.')

    if not (0 <= bulls <= 4 and 0 <= cows <= 4 and bulls + cows <= 4):
        return error_response('Invalid bulls/cows values (must be 0–4, sum ≤ 4).')

    # Verify honesty: check feedback against the real human secret
    ai_state = session['ai_state']
    
    # Get the current guess that the AI just made
    human_secret = session['human_secret']
    real_guess = ai_state.get('current_guess')
    if real_guess:
        real_bulls, real_cows = calculate_bulls_and_cows(human_secret, real_guess)
        if bulls != real_bulls or cows != real_cows:
            return error_response(
                f'Incorrect feedback! The real result is {real_bulls} Bulls, {real_cows} Cows. '
                'No cheating allowed! 🕵️'
            )

    won = is_winner(bulls)

    # Apply feedback to AI solver
    ai_state = AIBrainHard.apply_feedback(ai_state, bulls, cows)
    session['ai_state'] = ai_state

    # Record AI guess
    ai_guesses = session.get('ai_guesses', [])
    ai_guesses.append({'guess': real_guess or '????', 'bulls': bulls, 'cows': cows})
    session['ai_guesses'] = ai_guesses

    if won:
        session['game_over'] = True
        session['winner'] = 'ai'
        return jsonify({
            'success': True,
            'won': True,
            'winner': 'ai',
            'human_secret': human_secret,
        })

    # Pass turn back to human
    session['turn'] = 'human'
    return jsonify({'success': True, 'won': False})


@app.route('/result', methods=['GET'])
def result():
    """Return current game state summary."""
    return jsonify({
        'success': True,
        'game_over': session.get('game_over', False),
        'winner': session.get('winner'),
        'human_guesses': session.get('human_guesses', []),
        'ai_guesses': session.get('ai_guesses', []),
        'turn': session.get('turn'),
    })


@app.route('/reset', methods=['POST'])
def reset():
    """Clear session and restart."""
    session.clear()
    return jsonify({'success': True, 'redirect': '/'})


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)