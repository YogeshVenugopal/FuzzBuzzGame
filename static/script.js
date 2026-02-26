/**
 * script.js — Bulls or Cows Frontend Logic
 * Handles: OTP inputs, API calls, turn transitions, confetti win animation
 */

'use strict';

// ─────────────────────────────────────────────
// OTP-BOX KEYBOARD NAVIGATION
// ─────────────────────────────────────────────

/**
 * Wires up OTP-style digit boxes inside a given container ID.
 * - Auto-advances on valid digit entry
 * - Backspace moves to previous box
 * - Arrow keys navigate
 * - Paste handles 4-digit strings
 */
function initOtpBoxes(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const boxes = Array.from(container.querySelectorAll('.otp-box'));

  boxes.forEach((box, idx) => {
    // Input event — handle digit entry
    box.addEventListener('input', (e) => {
      const val = e.target.value;

      // Keep only the last digit typed (handles auto-fill edge cases)
      const digit = val.replace(/[^0-9]/g, '').slice(-1);
      box.value = digit;

      if (digit) {
        box.classList.add('filled');
        // Advance to next
        if (idx < boxes.length - 1) boxes[idx + 1].focus();
      } else {
        box.classList.remove('filled');
      }
    });

    // Keydown — backspace, arrows
    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace') {
        if (box.value === '' && idx > 0) {
          boxes[idx - 1].value = '';
          boxes[idx - 1].classList.remove('filled');
          boxes[idx - 1].focus();
        } else {
          box.value = '';
          box.classList.remove('filled');
        }
        e.preventDefault();
      }

      if (e.key === 'ArrowLeft'  && idx > 0)              boxes[idx - 1].focus();
      if (e.key === 'ArrowRight' && idx < boxes.length - 1) boxes[idx + 1].focus();

      // Enter submits from last box
      if (e.key === 'Enter' && idx === boxes.length - 1) {
        const submitBtn = document.getElementById('btnHumanSubmit') ||
                          document.getElementById('btnStart');
        if (submitBtn && !submitBtn.disabled) submitBtn.click();
      }
    });

    // Prevent non-numeric
    box.addEventListener('keypress', (e) => {
      if (!/[0-9]/.test(e.key)) e.preventDefault();
    });

    // Paste — fill all boxes from clipboard
    box.addEventListener('paste', (e) => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData)
        .getData('text')
        .replace(/[^0-9]/g, '')
        .slice(0, 4);

      pasted.split('').forEach((ch, i) => {
        if (boxes[i]) {
          boxes[i].value = ch;
          boxes[i].classList.add('filled');
        }
      });

      const nextEmpty = boxes.find(b => b.value === '');
      if (nextEmpty) nextEmpty.focus();
      else boxes[boxes.length - 1].focus();
    });

    // Clicking an already-filled box selects it for replacement
    box.addEventListener('click', () => box.select());
  });
}

// ─────────────────────────────────────────────
// READ OTP VALUE
// ─────────────────────────────────────────────

function getOtpValue(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return '';
  return Array.from(container.querySelectorAll('.otp-box'))
    .map(b => b.value)
    .join('');
}

function clearOtpBoxes(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.otp-box').forEach(b => {
    b.value = '';
    b.classList.remove('filled');
  });
  const first = container.querySelector('.otp-box');
  if (first) first.focus();
}

// ─────────────────────────────────────────────
// SHOW / HIDE HELPERS
// ─────────────────────────────────────────────

function show(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = '';
}

function hide(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

function showError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.style.display = '';
  // Re-trigger shake
  el.style.animation = 'none';
  el.offsetHeight; // reflow
  el.style.animation = '';
}

function clearError(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = 'none';
}

// ─────────────────────────────────────────────
// START GAME
// ─────────────────────────────────────────────

/**
 * Start the game immediately with pre-set secret
 */
async function quickStartGame() {
  const btn = document.getElementById('btnStartGame');
  setButtonLoading(btn, true);

  try {
    const res = await fetch('/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    const data = await res.json();

    if (!data.success) {
      alert(data.error || 'Failed to start game.');
      return;
    }

    window.location.href = data.redirect;
  } catch (err) {
    alert('Network error. Please try again.');
  } finally {
    setButtonLoading(btn, false);
  }
}

// ─────────────────────────────────────────────
// GAME PAGE: TURN MANAGEMENT
// ─────────────────────────────────────────────

function showHumanTurn() {
  show('humanCard');
  hide('resultFlash');
  hide('aiCard');
  const first = document.querySelector('#guessInputs .otp-box');
  if (first) first.focus();
}

async function submitHumanGuess() {
  const guess = getOtpValue('guessInputs');
  clearError('humanError');

  if (guess.length !== 4) {
    showError('humanError', 'Fill in all 4 digits.');
    return;
  }

  const btn = document.getElementById('btnHumanSubmit');
  setButtonLoading(btn, true);

  try {
    const res = await fetch('/human-turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guess }),
    });

    const data = await res.json();

    if (!data.success) {
      showError('humanError', data.error || 'Invalid guess.');
      return;
    }

    // Record in history
    addHistoryRow('humanHistory', guess, data.bulls, data.cows);

    // Show result flash
    clearOtpBoxes('guessInputs');
    hide('humanCard');
    showResultFlash(guess, data.bulls, data.cows);

    if (data.won) {
      setTimeout(() => showWinner('human', data.ai_secret), 2000);
      return;
    }

    // After 2.5s switch to AI turn
    setTimeout(() => {
      hide('resultFlash');
      triggerAiTurn();
    }, 2500);

  } catch (err) {
    showError('humanError', 'Network error. Please try again.');
  } finally {
    setButtonLoading(btn, false);
  }
}

// ─────────────────────────────────────────────
// RESULT FLASH
// ─────────────────────────────────────────────

function showResultFlash(guess, bulls, cows) {
  const flashEl = document.getElementById('resultFlash');
  if (!flashEl) return;

  const emoji = bulls === 4 ? '🎉' : bulls >= 2 ? '🔥' : '🎯';
  document.getElementById('resultEmoji').textContent = emoji;
  document.getElementById('resultScore').textContent =
    `🐂 ${bulls} Bulls  ·  🐄 ${cows} Cows`;
  document.getElementById('resultSub').textContent = `Your guess: ${guess.split('').join(' ')}`;

  // Reset animation
  flashEl.style.animation = 'none';
  flashEl.offsetHeight;
  flashEl.style.animation = '';

  show('resultFlash');
}

// ─────────────────────────────────────────────
// AI TURN
// ─────────────────────────────────────────────

async function triggerAiTurn() {
  try {
    const res = await fetch('/ai-turn');
    const data = await res.json();

    if (!data.success) {
      alert('AI error: ' + (data.error || 'Unknown'));
      return;
    }

    displayAiGuess(data.ai_guess);
  } catch (err) {
    alert('Network error during AI turn.');
  }
}

function displayAiGuess(guess) {
  // Animate digits appearing one by one
  const display = document.getElementById('aiGuessDisplay');
  if (!display) return;

  display.textContent = '_ _ _ _';

  const digits = guess.split('');
  let i = 0;

  const interval = setInterval(() => {
    const shown = digits.slice(0, i + 1).join(' ') +
      (i < 3 ? ' ' + '_ '.repeat(3 - i).trim() : '');
    display.textContent = shown;
    i++;
    if (i >= digits.length) clearInterval(interval);
  }, 180);

  // Show AI card after a tiny delay
  show('aiCard');

  // Reset animation
  const card = document.getElementById('aiCard');
  if (card) {
    card.style.animation = 'none';
    card.offsetHeight;
    card.style.animation = '';
  }
}

async function submitAiFeedback() {
  const bulls = parseInt(document.getElementById('aiBulls').value, 10);
  const cows  = parseInt(document.getElementById('aiCows').value,  10);
  clearError('aiError');

  if (bulls + cows > 4) {
    showError('aiError', 'Bulls + Cows cannot exceed 4.');
    return;
  }

  const btn = document.getElementById('btnAiFeedback');
  setButtonLoading(btn, true);

  try {
    const res = await fetch('/ai-feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bulls, cows }),
    });

    const data = await res.json();

    if (!data.success) {
      showError('aiError', data.error || 'Invalid feedback.');
      return;
    }

    // Get guess from display for history
    const aiDisplay = document.getElementById('aiGuessDisplay');
    const guess = (aiDisplay ? aiDisplay.textContent : '????').replace(/\s/g, '');
    addHistoryRow('aiHistory', guess, bulls, cows);

    // Reset selects
    document.getElementById('aiBulls').value = '0';
    document.getElementById('aiCows').value  = '0';

    if (data.won) {
      hide('aiCard');
      setTimeout(() => showWinner('ai', data.human_secret), 400);
      return;
    }

    // Switch back to human turn
    hide('aiCard');
    setTimeout(showHumanTurn, 300);

  } catch (err) {
    showError('aiError', 'Network error. Please try again.');
  } finally {
    setButtonLoading(btn, false);
  }
}

// ─────────────────────────────────────────────
// GAME HISTORY SIDEBAR
// ─────────────────────────────────────────────

function addHistoryRow(listId, guess, bulls, cows) {
  const list = document.getElementById(listId);
  if (!list) return;

  // Remove empty placeholder
  const empty = list.querySelector('.history-empty');
  if (empty) empty.remove();

  const row = document.createElement('div');
  row.className = 'history-row';
  row.innerHTML = `
    <span class="num">${guess.split('').join(' ')}</span>
    <span class="bc">🐂<span>${bulls}</span> 🐄<span>${cows}</span></span>
  `;
  list.appendChild(row);

  // Scroll to bottom
  list.scrollTop = list.scrollHeight;
}

// ─────────────────────────────────────────────
// WIN OVERLAY + CONFETTI
// ─────────────────────────────────────────────

function showWinner(winner, revealedSecret) {
  const overlay = document.getElementById('winOverlay');
  if (!overlay) return;

  const isHuman = winner === 'human';

  document.getElementById('winEmoji').textContent = isHuman ? '🏆' : '🤖';
  document.getElementById('winTitle').textContent  = isHuman ? 'HUMAN WINS!' : 'AI WINS!';
  document.getElementById('winSub').textContent    = isHuman
    ? `You cracked the AI's secret number!`
    : `The AI cracked your secret number!`;
  document.getElementById('winSecret').textContent = revealedSecret
    ? revealedSecret.split('').join(' ')
    : '';

  overlay.style.display = 'flex';

  if (isHuman) launchConfetti();
}

/**
 * Minimal canvas confetti — no external dependency.
 */
function launchConfetti() {
  const canvas = document.getElementById('confettiCanvas');
  if (!canvas) return;

  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
  const ctx = canvas.getContext('2d');

  const COLORS = ['#ffb41e', '#ff4d4d', '#4daaff', '#39ff88', '#fff', '#ff80d5'];
  const particles = Array.from({ length: 140 }, () => ({
    x: Math.random() * canvas.width,
    y: -20 - Math.random() * 200,
    w: 6 + Math.random() * 8,
    h: 8 + Math.random() * 6,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    vx: (Math.random() - 0.5) * 3,
    vy: 2 + Math.random() * 4,
    angle: Math.random() * Math.PI * 2,
    spin: (Math.random() - 0.5) * 0.15,
    opacity: 0.9 + Math.random() * 0.1,
  }));

  let frame;
  let done = false;

  function loop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = 0;

    particles.forEach(p => {
      if (p.y > canvas.height + 20) return;
      alive++;

      p.x     += p.vx;
      p.y     += p.vy;
      p.angle += p.spin;
      p.vy    += 0.05; // gravity

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.angle);
      ctx.globalAlpha = p.opacity;
      ctx.fillStyle   = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });

    if (alive > 0 && !done) frame = requestAnimationFrame(loop);
  }

  loop();

  // Stop after 5 seconds
  setTimeout(() => {
    done = true;
    cancelAnimationFrame(frame);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, 5000);
}

// ─────────────────────────────────────────────
// RESET
// ─────────────────────────────────────────────

async function resetGame() {
  try {
    await fetch('/reset', { method: 'POST' });
  } catch (_) {/* ignore */}
  window.location.href = '/';
}

// ─────────────────────────────────────────────
// BUTTON LOADING STATE
// ─────────────────────────────────────────────

function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    btn._originalHTML = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Loading…';
  } else {
    if (btn._originalHTML) btn.innerHTML = btn._originalHTML;
  }
}