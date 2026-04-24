/* register.js — multi-step student registration */

const video     = document.getElementById('reg-video');
const canvas    = document.getElementById('reg-canvas');
const ctx       = canvas ? canvas.getContext('2d') : null;
const capBtn    = document.getElementById('cap-btn');
const submitBtn = document.getElementById('submit-btn');
const progBar   = document.getElementById('prog-bar');
const progLabel = document.getElementById('prog-label');
const progCount = document.getElementById('prog-count');
const faceBox   = document.getElementById('face-detect-box');

const TOTAL   = 30;
const CAPTURE_W = 640;
const CAPTURE_H = 480;

let stream       = null;
let loopTimer    = null;
let capturing    = false;
let studentId    = null;
let sampleCount  = 0;
let step         = 1;       // 1 = form, 2 = capture, 3 = done

// ── Step navigation ───────────────────────────────────────────────
function goStep(n) {
  step = n;
  document.querySelectorAll('.step-panel').forEach(p => {
    p.style.display = p.dataset.step == n ? 'block' : 'none';
  });
  document.querySelectorAll('.step').forEach(s => {
    const sn = parseInt(s.dataset.step, 10);
    s.classList.toggle('active', sn === n);
    s.classList.toggle('done',   sn < n);
  });
}

// ── Start capture ─────────────────────────────────────────────────
document.getElementById('start-cap-btn')?.addEventListener('click', async () => {
  const name = document.getElementById('name-input').value.trim();
  const roll = document.getElementById('roll-input').value.trim();

  if (!name || !roll) { toast('Please fill in all fields.', 'warn'); return; }

  // Get student_id from server
  const res = await postJSON('/api/registration/start', {});
  studentId   = res.student_id;
  sampleCount = 0;

  goStep(2);
  await openCamera();
});

async function openCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: CAPTURE_W, height: CAPTURE_H }, audio: false
    });
    video.srcObject = stream;
    await video.play();
    document.querySelector('.cam-wrapper').classList.add('live');
    updateProgress(0);
  } catch (err) {
    toast('Camera error: ' + err.message, 'error');
  }
}

// ── Toggle capture ────────────────────────────────────────────────
capBtn?.addEventListener('click', () => {
  if (capturing) {
    stopCapture();
  } else {
    startCapture();
  }
});

function startCapture() {
  capturing = true;
  capBtn.textContent  = '⏹  Stop Capture';
  capBtn.className    = 'btn btn-danger w-100';
  loopTimer = setInterval(captureLoop, 180);
}

function stopCapture() {
  capturing = false;
  clearInterval(loopTimer);
  capBtn.textContent = '▶  Start Capture';
  capBtn.className   = 'btn btn-primary w-100';
}

// ── Capture loop ──────────────────────────────────────────────────
async function captureLoop() {
  if (!capturing || sampleCount >= TOTAL || !video.videoWidth) return;

  const tmp = document.createElement('canvas');
  tmp.width  = CAPTURE_W;
  tmp.height = CAPTURE_H;
  tmp.getContext('2d').drawImage(video, 0, 0, CAPTURE_W, CAPTURE_H);
  const b64 = tmp.toDataURL('image/jpeg', 0.85);

  // Show face detection box on overlay canvas
  drawDetecting();

  try {
    const data = await postJSON('/api/registration/sample', {
      student_id: studentId,
      image: b64
    });

    if (data.saved) {
      sampleCount = data.count;
      updateProgress(sampleCount);
      drawSuccess();
    }

    if (data.done || sampleCount >= TOTAL) {
      stopCapture();
      finishCapture();
    }
  } catch (e) {}
}

function drawDetecting() {
  if (!ctx || !video.videoWidth) return;
  canvas.width  = video.offsetWidth;
  canvas.height = video.offsetHeight;
  const cx = canvas.width / 2, cy = canvas.height / 2;
  const bw = 200, bh = 240;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = 'rgba(96,239,255,.5)';
  ctx.lineWidth   = 1.5;
  ctx.setLineDash([8, 6]);
  ctx.strokeRect(cx - bw/2, cy - bh/2, bw, bh);
  ctx.setLineDash([]);
}

function drawSuccess() {
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const cx = canvas.width / 2, cy = canvas.height / 2;
  const bw = 200, bh = 240;
  ctx.strokeStyle = '#00ffaa';
  ctx.lineWidth   = 2;
  ctx.strokeRect(cx - bw/2, cy - bh/2, bw, bh);
}

function updateProgress(count) {
  const pct = Math.min((count / TOTAL) * 100, 100);
  if (progBar)   progBar.style.width = pct + '%';
  if (progLabel) progLabel.textContent = `${count} / ${TOTAL} samples`;
  if (progCount) progCount.textContent = count;
}

function finishCapture() {
  setTimeout(() => {
    document.querySelector('.cam-wrapper').classList.remove('live');
    goStep(3);
    submitBtn.disabled = false;
  }, 500);
}

// ── Submit registration ───────────────────────────────────────────
submitBtn?.addEventListener('click', async () => {
  const name = document.getElementById('name-input').value.trim();
  const roll = document.getElementById('roll-input').value.trim();

  submitBtn.disabled  = true;
  submitBtn.textContent = '⏳  Training model…';

  const data = await postJSON('/api/registration/finish', {
    student_id: studentId, name, roll
  });

  if (data.success) {
    toast(`🎉  ${data.name} registered successfully!`, 'success', 4000);
    document.getElementById('success-name').textContent = data.name;
    goStep(4);
    stopStream();
  } else {
    toast(data.error || 'Registration failed.', 'error');
    submitBtn.disabled  = false;
    submitBtn.textContent = '✅  Complete Registration';
  }
});

// ── Register another ──────────────────────────────────────────────
document.getElementById('reg-another-btn')?.addEventListener('click', () => {
  document.getElementById('name-input').value = '';
  document.getElementById('roll-input').value = '';
  sampleCount = 0; studentId = null;
  updateProgress(0);
  goStep(1);
});

function stopStream() {
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  clearInterval(loopTimer);
}

// ── Init ──────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => goStep(1));
