"""
API Routes for Bulls or Cows Game - Vercel Entry Point
"""
import os
import random
from flask import Flask, render_template, request, session, jsonify, redirect, url_for

from game_logic import validate_number, calculate_bulls_and_cows, is_winner
from ai_solver import AIBrainHard, generate_all_combinations, filter_candidates

# Set up Flask with correct paths for Vercel
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static")
)

app.secret_key = os.environ.get('SECRET_KEY', 'bulls-cows-hard-mode-secret-2024')


def pick_ai_secret():
    """Randomly choose a valid 4-digit unique-digit number for the AI's secret."""
    all_combos = generate_all_combinations()
    return random.choice(all_combos)


def error_response(message, status=400):
    return jsonify({'success': False, 'error': message}), status


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game')
def game():
    if 'ai_secret' not in session:
        return redirect(url_for('index'))
    return render_template('game.html')


@app.route('/start', methods=['POST'])
def start():
    """
    Initialize a new game.
    The human THINKS of a secret — never stored server-side.
    AI uses only the feedback the human gives to narrow candidates.
    """
    session.clear()
    session['ai_secret'] = pick_ai_secret()
    session['ai_state'] = AIBrainHard.initial_state()
    session['human_guesses'] = []
    session['ai_guesses'] = []
    session['game_over'] = False
    session['winner'] = None
    session['turn'] = 'human'
    return jsonify({'success': True, 'redirect': '/game'})


@app.route('/human-turn', methods=['POST'])
def human_turn():
    """Human guesses the AI's secret."""
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

    guesses = session.get('human_guesses', [])
    guesses.append({'guess': guess, 'bulls': bulls, 'cows': cows})
    session['human_guesses'] = guesses

    if won:
        session['game_over'] = True
        session['winner'] = 'human'
        return jsonify({
            'success': True, 'bulls': bulls, 'cows': cows,
            'won': True, 'winner': 'human', 'ai_secret': ai_secret,
        })

    session['turn'] = 'ai'
    return jsonify({'success': True, 'bulls': bulls, 'cows': cows, 'won': False})


@app.route('/ai-turn', methods=['GET'])
def ai_turn():
    """AI picks next guess from remaining candidates."""
    if 'ai_state' not in session:
        return error_response('No active game.', 403)
    if session.get('game_over'):
        return error_response('Game is already over.')
    if session.get('turn') != 'ai':
        return error_response("It is not the AI's turn.")

    ai_state = session.get('ai_state')
    guess, ai_state = AIBrainHard.make_guess(ai_state)
    session['ai_state'] = ai_state

    return jsonify({'success': True, 'ai_guess': guess})


@app.route('/ai-feedback', methods=['POST'])
def ai_feedback():
    """
    Human provides honest bulls/cows feedback for AI's guess.
    AI narrows its candidate pool. No server secret for human's number.
    """
    if 'ai_state' not in session:
        return error_response('No active game.', 403)
    if session.get('game_over'):
        return error_response('Game is already over.')
    if session.get('turn') != 'ai':
        return error_response("It is not the AI's turn.")

    data = request.get_json()
    if not data:
        return error_response('No data provided.')

    try:
        bulls = int(data.get('bulls', -1))
        cows  = int(data.get('cows',  -1))
    except (TypeError, ValueError):
        return error_response('Bulls and cows must be integers.')

    if not (0 <= bulls <= 4 and 0 <= cows <= 4 and bulls + cows <= 4):
        return error_response('Invalid bulls/cows values (must be 0–4, sum ≤ 4).')

    ai_state = session['ai_state']
    real_guess = ai_state.get('current_guess')
    won = is_winner(bulls)

    # Apply feedback — AI eliminates impossible candidates
    ai_state = AIBrainHard.apply_feedback(ai_state, bulls, cows)
    session['ai_state'] = ai_state

    ai_guesses = session.get('ai_guesses', [])
    ai_guesses.append({'guess': real_guess or '????', 'bulls': bulls, 'cows': cows})
    session['ai_guesses'] = ai_guesses

    if won:
        session['game_over'] = True
        session['winner'] = 'ai'
        return jsonify({
            'success': True, 'won': True, 'winner': 'ai',
            'ai_guess': real_guess,
        })

    # Check remaining candidates — detect contradictory feedback
    candidates = generate_all_combinations()
    for entry in ai_state.get('guessed', []):
        candidates = filter_candidates(candidates, entry['guess'], entry['bulls'], entry['cows'])

    if len(candidates) == 0:
        return error_response(
            'No valid numbers remain! Your feedback may be inconsistent. '
            'Please verify your answers or start a new game.'
        )

    session['turn'] = 'human'
    return jsonify({'success': True, 'won': False})


@app.route('/result', methods=['GET'])
def result():
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
    session.clear()
    return jsonify({'success': True, 'redirect': '/'})


@app.route("/favicon.ico")
def favicon():
    return "", 204