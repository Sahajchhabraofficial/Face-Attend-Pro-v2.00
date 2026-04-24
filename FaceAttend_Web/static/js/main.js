/* main.js — shared utilities */

// ── Toast notifications ───────────────────────────────────────────
function toast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warn: '⚠️' };
  const container = document.getElementById('toast-container');

  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <span class="toast-msg">${msg}</span>
    <span class="toast-dismiss" onclick="this.parentElement.remove()">✕</span>`;

  container.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .4s';
    setTimeout(() => t.remove(), 400); }, duration);
}

// ── Topbar date ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('topbar-date');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-IN', {
      weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
    });
  }
});

// ── Animated number counter ───────────────────────────────────────
function animateCount(el, target, duration = 800) {
  let start = 0;
  const step = Math.ceil(target / (duration / 16));
  const timer = setInterval(() => {
    start += step;
    if (start >= target) { el.textContent = target; clearInterval(timer); return; }
    el.textContent = start;
  }, 16);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-count]').forEach(el => {
    const val = parseInt(el.dataset.count, 10);
    if (!isNaN(val)) animateCount(el, val);
  });
});

// ── Fetch helpers ─────────────────────────────────────────────────
async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return res.json();
}

async function getJSON(url) {
  const res = await fetch(url);
  return res.json();
}
