/* ═══════════════════════════════════════════════════════════════
   JARVIS — Hand Authentication System
   Camera opens → show hand → Access Granted → JARVIS launches
   ═══════════════════════════════════════════════════════════════ */

let handDetectedCount = 0;
const REQUIRED_FRAMES = 10;
let isAuthenticated = false;
let authHands = null;

function initAuthentication() {
    const statusEl = document.getElementById('authStatus');
    const cameraBox = document.querySelector('.camera-box');

    // Show a "Start Camera" button — Brave trusts user-gesture permission requests
    statusEl.innerHTML = '';

    const startBtn = document.createElement('button');
    startBtn.textContent = '📷 START CAMERA SCAN';
    startBtn.id = 'startCameraBtn';
    startBtn.style.cssText = `
        background: rgba(0,229,255,0.12);
        border: 1px solid rgba(0,229,255,0.5);
        color: #00e5ff;
        padding: 14px 36px;
        border-radius: 8px;
        cursor: pointer;
        font-family: Consolas, monospace;
        font-size: 1rem;
        letter-spacing: 3px;
        transition: all 0.3s;
        margin-bottom: 10px;
    `;
    startBtn.onmouseenter = () => { startBtn.style.background = 'rgba(0,229,255,0.25)'; };
    startBtn.onmouseleave = () => { startBtn.style.background = 'rgba(0,229,255,0.12)'; };
    startBtn.onclick = () => requestCameraAccess();
    statusEl.appendChild(startBtn);

    // Add a small skip link below
    const skipLink = document.createElement('p');
    skipLink.innerHTML = '<a href="#" id="skipAuthLink" style="color: rgba(0,229,255,0.4); font-size: 0.75rem; text-decoration: none; letter-spacing: 2px;">SKIP AUTHENTICATION →</a>';
    skipLink.querySelector('a').onclick = (e) => { e.preventDefault(); grantAccess(); };
    statusEl.appendChild(skipLink);
}

function requestCameraAccess() {
    const statusEl = document.getElementById('authStatus');
    statusEl.innerHTML = '<p style="color: rgba(0,229,255,0.7); font-size: 0.9rem;">Requesting camera access...</p>';

    navigator.mediaDevices.getUserMedia({ video: true })
    .then((stream) => {
        const videoEl = document.getElementById('authVideo');
        videoEl.srcObject = stream;
        videoEl.play();

        // Remove button, show scanning status
        statusEl.innerHTML = '';
        const scanText = document.createElement('p');
        scanText.id = 'scanStatus';
        scanText.style.cssText = 'color: rgba(0,229,255,0.8); font-family: Consolas, monospace; font-size: 0.95rem; letter-spacing: 1px;';
        scanText.textContent = '🖐️ Show your hand to authenticate';
        statusEl.appendChild(scanText);

        // Try MediaPipe, fall back to motion detection
        if (typeof Hands !== 'undefined') {
            initMediaPipeAuth(videoEl);
        } else {
            initMotionAuth(videoEl);
        }
    })
    .catch((err) => {
        console.error('[AUTH] Camera error:', err);
        statusEl.innerHTML = '';

        const errMsg = document.createElement('p');
        errMsg.style.cssText = 'color: rgba(255,100,100,0.9); font-size: 0.85rem; margin-bottom: 8px;';

        if (err.name === 'NotAllowedError') {
            errMsg.textContent = '⚠️ Camera blocked by browser.';
            const helpMsg = document.createElement('p');
            helpMsg.style.cssText = 'color: rgba(255,255,255,0.5); font-size: 0.75rem; margin-bottom: 15px; max-width: 320px; line-height: 1.5;';
            helpMsg.textContent = 'Go to brave://settings/content/camera → Add http://localhost:8000 → Refresh page';
            statusEl.appendChild(errMsg);
            statusEl.appendChild(helpMsg);
        } else if (err.name === 'NotFoundError') {
            errMsg.textContent = '⚠️ No camera detected on this device.';
            statusEl.appendChild(errMsg);
        } else {
            errMsg.textContent = `⚠️ Camera error: ${err.message}`;
            statusEl.appendChild(errMsg);
        }

        // Show unlock button
        const unlockBtn = document.createElement('button');
        unlockBtn.textContent = '🔓 UNLOCK MANUALLY';
        unlockBtn.style.cssText = `
            background: rgba(0,255,100,0.12);
            border: 1px solid rgba(0,255,100,0.5);
            color: #00ff66;
            padding: 14px 36px;
            border-radius: 8px;
            cursor: pointer;
            font-family: Consolas, monospace;
            font-size: 1rem;
            letter-spacing: 3px;
            transition: all 0.3s;
        `;
        unlockBtn.onmouseenter = () => { unlockBtn.style.background = 'rgba(0,255,100,0.25)'; };
        unlockBtn.onmouseleave = () => { unlockBtn.style.background = 'rgba(0,255,100,0.12)'; };
        unlockBtn.onclick = () => grantAccess();
        statusEl.appendChild(unlockBtn);
    });
}

function initMediaPipeAuth(videoEl) {
    try {
        authHands = new Hands({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`
        });
        authHands.setOptions({
            maxNumHands: 1,
            modelComplexity: 0,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });
        authHands.onResults(onHandResults);
        processFrames(videoEl);
    } catch (e) {
        console.warn('[AUTH] MediaPipe failed, using motion fallback');
        initMotionAuth(videoEl);
    }
}

async function processFrames(videoEl) {
    if (isAuthenticated) return;
    try {
        await authHands.send({ image: videoEl });
    } catch (e) { /* retry */ }
    if (!isAuthenticated) {
        requestAnimationFrame(() => processFrames(videoEl));
    }
}

function onHandResults(results) {
    if (isAuthenticated) return;
    const scanStatus = document.getElementById('scanStatus');
    if (!scanStatus) return;

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        handDetectedCount++;
        const pct = Math.min(Math.round((handDetectedCount / REQUIRED_FRAMES) * 100), 100);
        scanStatus.textContent = `🔍 Scanning biometrics... ${pct}%`;
        if (handDetectedCount >= REQUIRED_FRAMES) {
            grantAccess();
        }
    } else {
        handDetectedCount = Math.max(0, handDetectedCount - 1);
        scanStatus.textContent = '🖐️ Show your hand to authenticate';
    }
}

// Fallback: detect motion (hand waving)
function initMotionAuth(videoEl) {
    const canvas = document.createElement('canvas');
    canvas.width = 160;
    canvas.height = 120;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    let prevData = null;
    let motionCount = 0;

    function detect() {
        if (isAuthenticated) return;
        const scanStatus = document.getElementById('scanStatus');
        if (!scanStatus) return;

        ctx.drawImage(videoEl, 0, 0, 160, 120);
        const imageData = ctx.getImageData(0, 0, 160, 120);
        const data = imageData.data;

        if (prevData) {
            let diff = 0;
            for (let i = 0; i < data.length; i += 16) {
                diff += Math.abs(data[i] - prevData[i]);
            }
            if (diff / (data.length / 16) > 12) {
                motionCount++;
                const pct = Math.min(Math.round((motionCount / 12) * 100), 100);
                scanStatus.textContent = `🔍 Scanning biometrics... ${pct}%`;
                if (motionCount >= 12) {
                    grantAccess();
                    return;
                }
            } else {
                motionCount = Math.max(0, motionCount - 1);
            }
        }
        prevData = new Uint8ClampedArray(data);
        requestAnimationFrame(detect);
    }
    detect();
}

function grantAccess() {
    if (isAuthenticated) return;
    isAuthenticated = true;

    const lockScreen = document.getElementById('lockScreen');
    const grantedEl = document.getElementById('accessGranted');
    const videoEl = document.getElementById('authVideo');
    const scanStatus = document.getElementById('scanStatus');

    // Phase 1: Show "Verifying identity..." for 5 seconds (scanning feel)
    if (scanStatus) {
        scanStatus.textContent = '🔒 Identity detected. Verifying biometrics...';
        scanStatus.style.color = '#ffcc00';
    }

    setTimeout(() => {
        // Phase 2: After 5 sec — show ACCESS GRANTED
        const lockContent = document.querySelector('.lock-content');
        if (lockContent) lockContent.style.display = 'none';
        if (grantedEl) grantedEl.style.display = 'flex';

        // Speak "Access granted"
        try {
            const utterance = new SpeechSynthesisUtterance('Access granted. Launching Jarvis.');
            utterance.rate = 1.0;
            utterance.pitch = 0.8;
            const voices = speechSynthesis.getVoices();
            const voice = voices.find(v => v.name.includes('David') || v.name.includes('Male') || v.name.includes('Mark'));
            if (voice) utterance.voice = voice;
            speechSynthesis.speak(utterance);
        } catch (e) { /* not critical */ }

        // Stop camera
        if (videoEl && videoEl.srcObject) {
            videoEl.srcObject.getTracks().forEach(t => t.stop());
        }

        // Phase 3: After 2.5 more sec — fade out and launch JARVIS
        setTimeout(() => {
            lockScreen.classList.add('fade-out');
            setTimeout(() => {
                lockScreen.style.display = 'none';
                document.getElementById('mainUI').style.display = '';
                if (typeof window.initJarvis === 'function') {
                    window.initJarvis();
                }
            }, 800);
        }, 2500);

    }, 5000);
}

// Preload voices
if (typeof speechSynthesis !== 'undefined') {
    speechSynthesis.onvoiceschanged = () => { speechSynthesis.getVoices(); };
}

// Start on page load
document.addEventListener('DOMContentLoaded', initAuthentication);
