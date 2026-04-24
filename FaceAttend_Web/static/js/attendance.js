/* attendance.js — webcam capture + face recognition loop */

const video    = document.getElementById('att-video');
const canvas   = document.getElementById('att-canvas');
const ctx      = canvas ? canvas.getContext('2d') : null;
const startBtn = document.getElementById('start-btn');
const stopBtn  = document.getElementById('stop-btn');
const liveDot  = document.getElementById('live-dot');
const markedList = document.getElementById('marked-list');
const markedCount = document.getElementById('marked-count');

let stream      = null;
let loopTimer   = null;
let isRunning   = false;
let markedToday = new Set();

const CAPTURE_W = 640;
const CAPTURE_H = 480;
const MODE      = document.body.dataset.camMode || 'webcam'; // 'webcam' or 'cctv'

// ── Start ─────────────────────────────────────────────────────────
async function startAttendance() {
  if (MODE === 'cctv') {
    startCCTV(); return;
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: CAPTURE_W, height: CAPTURE_H, facingMode: 'user' },
      audio: false
    });
    video.srcObject = stream;
    await video.play();

    // Resize canvas to match video display size
    const rect = video.getBoundingClientRect();
    canvas.width  = video.offsetWidth  || CAPTURE_W;
    canvas.height = video.offsetHeight || CAPTURE_H;

    document.querySelector('.cam-wrapper').classList.add('live');
    setLive(true);
    startBtn.disabled = true;
    stopBtn.disabled  = false;
    isRunning = true;

    // Load today's already-marked students
    loadToday();

    // Start recognition loop
    loopTimer = setInterval(recognizeLoop, 900);
  } catch (err) {
    toast('Camera access denied: ' + err.message, 'error');
  }
}

function startCCTV() {
  // For CCTV: server handles recognition, stream shown via <img>
  const img = document.getElementById('cctv-img');
  if (img) {
    img.src = '/api/stream/cctv?t=' + Date.now();
    document.querySelector('.cam-wrapper').classList.add('live');
    setLive(true);
    startBtn.disabled = true;
    stopBtn.disabled  = false;
    // Poll attendance list every 2s
    loopTimer = setInterval(loadToday, 2000);
  }
}

// ── Stop ──────────────────────────────────────────────────────────
function stopAttendance() {
  isRunning = false;
  clearInterval(loopTimer);

  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (MODE === 'cctv') {
    const img = document.getElementById('cctv-img');
    if (img) img.src = '';
  }

  document.querySelector('.cam-wrapper').classList.remove('live');
  setLive(false);
  startBtn.disabled = false;
  stopBtn.disabled  = true;
}

// ── Recognition loop ──────────────────────────────────────────────
async function recognizeLoop() {
  if (!isRunning || !video.videoWidth) return;

  // Capture current frame to temp canvas
  const tmp = document.createElement('canvas');
  tmp.width  = CAPTURE_W;
  tmp.height = CAPTURE_H;
  tmp.getContext('2d').drawImage(video, 0, 0, CAPTURE_W, CAPTURE_H);
  const b64 = tmp.toDataURL('image/jpeg', 0.8);

  try {
    const data = await postJSON('/api/recognize', { image: b64 });
    drawBoxes(data.results || []);
    handleResults(data.results || []);
  } catch (e) {
    // Silently ignore network errors in loop
  }
}

// ── Draw face boxes on overlay canvas ────────────────────────────
function drawBoxes(results) {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const scaleX = canvas.width  / CAPTURE_W;
  const scaleY = canvas.height / CAPTURE_H;

  results.forEach(r => {
    const [x, y, w, h] = r.bbox;
    const sx = x * scaleX, sy = y * scaleY;
    const sw = w * scaleX, sh = h * scaleY;

    const color = r.known ? '#00ffaa' : '#ff3d6b';

    // Box
    ctx.strokeStyle = color;
    ctx.lineWidth   = 2;
    ctx.strokeRect(sx, sy, sw, sh);

    // Corner accents
    const cs = 12;
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    // TL
    ctx.beginPath(); ctx.moveTo(sx, sy+cs); ctx.lineTo(sx, sy); ctx.lineTo(sx+cs, sy); ctx.stroke();
    // TR
    ctx.beginPath(); ctx.moveTo(sx+sw-cs, sy); ctx.lineTo(sx+sw, sy); ctx.lineTo(sx+sw, sy+cs); ctx.stroke();
    // BL
    ctx.beginPath(); ctx.moveTo(sx, sy+sh-cs); ctx.lineTo(sx, sy+sh); ctx.lineTo(sx+cs, sy+sh); ctx.stroke();
    // BR
    ctx.beginPath(); ctx.moveTo(sx+sw-cs, sy+sh); ctx.lineTo(sx+sw, sy+sh); ctx.lineTo(sx+sw, sy+sh-cs); ctx.stroke();

    // Label background
    const label    = r.known ? r.name : 'Unknown';
    const subLabel = r.known ? (r.already_present ? '• Present' : `${r.confidence}`) : `${r.confidence}`;
    ctx.font       = 'bold 13px DM Sans';
    const tw       = ctx.measureText(label).width;
    ctx.fillStyle  = r.known ? 'rgba(0,255,170,.85)' : 'rgba(255,61,107,.85)';
    ctx.fillRect(sx, sy - 34, tw + 18, 28);

    // Label text
    ctx.fillStyle = '#000';
    ctx.fillText(label, sx + 9, sy - 14);
    ctx.font      = '11px DM Sans';
    ctx.fillStyle = r.known ? '#000' : '#fff';
    ctx.fillText(subLabel, sx + 9, sy - 2);
  });
}

// ── Handle results (mark attendance etc.) ─────────────────────────
function handleResults(results) {
  results.forEach(r => {
    if (r.known && r.marked && !markedToday.has(r.name)) {
      markedToday.add(r.name);
      addToMarkedList(r.name);
      toast(`✅  ${r.name} marked present!`, 'success', 3000);
    }
  });
}

// ── Load today's attendance list ──────────────────────────────────
async function loadToday() {
  try {
    const data = await getJSON('/api/attendance/today');
    markedList.innerHTML = '';
    markedToday.clear();
    (data.records || []).forEach(row => {
      if (row[1]) {
        markedToday.add(row[1]);
        appendMarkedItem(row[1], row[2]);
      }
    });
    if (markedCount) markedCount.textContent = markedToday.size;
  } catch (e) {}
}

function addToMarkedList(name) {
  const now = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  appendMarkedItem(name, now);
  if (markedCount) markedCount.textContent = markedToday.size;
}

function appendMarkedItem(name, time) {
  const div = document.createElement('div');
  div.className = 'marked-item';
  div.innerHTML = `
    <span class="mi-icon">✓</span>
    <span class="mi-name">${name}</span>
    <span class="mi-time">${time}</span>`;
  markedList.prepend(div);
}

// ── Live dot helper ───────────────────────────────────────────────
function setLive(on) {
  if (!liveDot) return;
  liveDot.className = 'live-dot ' + (on ? 'on' : 'off');
  liveDot.querySelector('.dot-text').textContent = on ? 'LIVE' : 'IDLE';
}

// ── Event listeners ───────────────────────────────────────────────
startBtn?.addEventListener('click', startAttendance);
stopBtn?.addEventListener('click', stopAttendance);

// Load already-marked list on page load
document.addEventListener('DOMContentLoaded', loadToday);
