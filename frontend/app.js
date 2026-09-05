/* ═══════════════════════════════════════════════════════════════
   JARVIS — Frontend Client Logic
   WebSocket communication, audio recording, and UI management
   ═══════════════════════════════════════════════════════════════ */

// ─── DOM Elements ──────────────────────────────────────────────
const chatMessages = document.getElementById('chatMessages');
const textInput = document.getElementById('textInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const micLabel = document.getElementById('micLabel');
const clearBtn = document.getElementById('clearBtn');
const connectionBadge = document.getElementById('connectionBadge');
const orbContainer = document.getElementById('orbContainer');
const orbStatus = document.getElementById('orbStatus');
const stopBtn = document.getElementById('stopBtn');

// ─── State ─────────────────────────────────────────────────────
let ws = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let isProcessing = false;
let audioContext = null;
let reconnectAttempts = 0;
let typingCancelled = false;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_DELAY = 2000;

// ─── WebSocket Connection ──────────────────────────────────────
function connectWebSocket() {
    // Prevent duplicate connections and infinite loops
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        console.log('[WS] WebSocket is already active or connecting. Skipping duplicate.');
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    console.log(`[WS] Connecting to ${wsUrl}...`);
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[WS] Connected!');
        reconnectAttempts = 1; // Mark as "had a successful connection" so auto-reconnect works
        updateConnectionStatus('connected');
        enableInputs(true);
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleServerMessage(message);
        } catch (e) {
            console.error('[WS] Failed to parse message:', e);
        }
    };

    ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        updateConnectionStatus('disconnected');
        enableInputs(false);
        // Always clear thinking state on disconnect
        removeThinkingIndicator();
        hideStopButton();
        isProcessing = false;

        // Only auto-reconnect if we had a successful connection before
        // (prevents greeting loop when first connection fails)
        if (reconnectAttempts > 0 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`[WS] Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
            setTimeout(connectWebSocket, RECONNECT_DELAY);
        }
    };

    ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        removeThinkingIndicator();
        hideStopButton();
        isProcessing = false;
    };
}

// ─── Handle Server Messages ───────────────────────────────────
function handleServerMessage(message) {
    switch (message.type) {
        case 'status':
            updateOrbState(message.content);
            // If status goes idle, ALWAYS clear thinking state
            if (message.content === 'idle') {
                removeThinkingIndicator();
                hideStopButton();
                isProcessing = false;
            }
            break;

        case 'transcription':
            // Show what the user said (from voice) and clear thinking dots
            removeThinkingIndicator();
            addMessage('user', message.content, 'voice');
            // Add a new thinking indicator waiting for JARVIS to reply
            addThinkingIndicator();
            break;

        case 'response':
            // Remove thinking indicator and show JARVIS response
            removeThinkingIndicator();
            addMessage('jarvis', message.content);
            break;

        case 'audio':
            // Play TTS audio response
            playAudioBase64(message.content);
            break;

        case 'error':
            removeThinkingIndicator();
            hideStopButton();
            isProcessing = false;
            addMessage('error', message.content);
            updateOrbState('idle');
            break;

        default:
            console.warn('[WS] Unknown message type:', message.type);
    }
}

// ─── Send Text Message ─────────────────────────────────────────
function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text || isProcessing || !ws || ws.readyState !== WebSocket.OPEN) return;

    typingCancelled = false; // Reset typing cancellation for new command
    isProcessing = true;
    addMessage('user', text, 'text');
    addThinkingIndicator();
    textInput.value = '';

    // Show stop button, hide send button
    showStopButton();

    ws.send(JSON.stringify({
        type: 'text',
        content: text
    }));
}

// ─── Stop Button Logic ─────────────────────────────────────────
function showStopButton() {
    sendBtn.style.display = 'none';
    stopBtn.style.display = 'flex';
}

function hideStopButton() {
    stopBtn.style.display = 'none';
    sendBtn.style.display = 'flex';
}

function sendStop() {
    typingCancelled = true; // Signal all active typing animations to stop
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop' }));
    }
    hideStopButton();
    isProcessing = false;
    updateOrbState('idle');
}

// ─── Audio Recording ───────────────────────────────────────────
async function startRecording() {
    if (isRecording || isProcessing) return;

    typingCancelled = false; // Reset typing cancellation for new command
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Use wav-compatible format
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : 'audio/webm';

        mediaRecorder = new MediaRecorder(stream, { mimeType });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());

            if (audioChunks.length === 0) return;

            const audioBlob = new Blob(audioChunks, { type: mimeType });

            // Convert to WAV using AudioContext
            const wavBlob = await convertToWav(audioBlob);

            if (wavBlob && ws && ws.readyState === WebSocket.OPEN) {
                isProcessing = true;
                addThinkingIndicator();
                showStopButton();

                // Convert to base64 and send
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64 = reader.result.split(',')[1];
                    ws.send(JSON.stringify({
                        type: 'audio',
                        content: base64
                    }));
                };
                reader.readAsDataURL(wavBlob);
            }
        };

        mediaRecorder.start(100); // Collect data every 100ms
        isRecording = true;
        micBtn.classList.add('recording');
        micLabel.textContent = 'RECORDING...';
        updateOrbState('listening');

    } catch (err) {
        console.error('[MIC] Failed to access microphone:', err);
        if (err.name === 'NotAllowedError') {
            addMessage('error', 'Microphone blocked by Brave. Go to brave://settings/content/microphone → Add http://localhost:8000 → Then refresh this page.');
        } else {
            addMessage('error', 'Cannot access microphone. Please allow microphone access in your browser settings.');
        }
    }
}

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;

    mediaRecorder.stop();
    isRecording = false;
    micBtn.classList.remove('recording');
    micLabel.textContent = 'HOLD TO SPEAK';
}

// ─── Convert Audio to WAV ──────────────────────────────────────
async function convertToWav(audioBlob) {
    try {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
        }

        const arrayBuffer = await audioBlob.arrayBuffer();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        // Get mono channel data
        const channelData = audioBuffer.getChannelData(0);
        const sampleRate = audioBuffer.sampleRate;

        // Create WAV file
        const wavBuffer = encodeWav(channelData, sampleRate);
        return new Blob([wavBuffer], { type: 'audio/wav' });

    } catch (err) {
        console.error('[AUDIO] WAV conversion failed:', err);
        return null;
    }
}

function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // WAV header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);           // Subchunk1Size
    view.setUint16(20, 1, true);            // PCM format
    view.setUint16(22, 1, true);            // Mono
    view.setUint32(24, sampleRate, true);    // SampleRate
    view.setUint32(28, sampleRate * 2, true); // ByteRate
    view.setUint16(32, 2, true);            // BlockAlign
    view.setUint16(34, 16, true);           // BitsPerSample
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write audio data
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
    }

    return buffer;
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

// ─── Play Audio Response ───────────────────────────────────────
function playAudioBase64(base64Audio) {
    try {
        const audioBytes = atob(base64Audio);
        const arrayBuffer = new ArrayBuffer(audioBytes.length);
        const view = new Uint8Array(arrayBuffer);
        for (let i = 0; i < audioBytes.length; i++) {
            view[i] = audioBytes.charCodeAt(i);
        }

        const blob = new Blob([arrayBuffer], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);

        audio.onended = () => {
            URL.revokeObjectURL(url);
            updateOrbState('idle');
            isProcessing = false;
        };

        audio.onerror = () => {
            URL.revokeObjectURL(url);
            updateOrbState('idle');
            isProcessing = false;
        };

        audio.play().catch(err => {
            console.error('[AUDIO] Playback failed:', err);
            updateOrbState('idle');
            isProcessing = false;
        });

    } catch (err) {
        console.error('[AUDIO] Failed to play audio:', err);
        updateOrbState('idle');
        isProcessing = false;
    }
}

// ─── UI Helpers ────────────────────────────────────────────────
function addMessage(sender, content, source = '') {
    // Remove welcome message if present
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const avatarLabel = sender === 'user' ? 'YOU' : sender === 'jarvis' ? 'J' : '!';

    let sourceLabel = '';
    if (source === 'voice') sourceLabel = '<span class="message-source">🎤 Voice</span>';
    else if (source === 'text') sourceLabel = '<span class="message-source">⌨️ Typed</span>';

    if (sender === 'jarvis') {
        // Typing effect for JARVIS responses to sync with voice starting
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatarLabel}</div>
            <div class="message-bubble">
                <span class="typing-content"></span>
                ${sourceLabel}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        const bubbleContent = messageDiv.querySelector('.typing-content');
        let index = 0;
        const typingSpeed = 35; // 35ms per character

        function typeChar() {
            if (index < content.length) {
                // If stop button was clicked, halt typing animation immediately
                if (typingCancelled) {
                    return;
                }
                bubbleContent.textContent += content.charAt(index);
                index++;
                scrollToBottom();
                setTimeout(typeChar, typingSpeed);
            }
        }
        typeChar();
    } else {
        // User messages appear instantly
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatarLabel}</div>
            <div class="message-bubble">
                ${escapeHtml(content)}
                ${sourceLabel}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }
}

function addThinkingIndicator() {
    const existingThinking = document.getElementById('thinkingIndicator');
    if (existingThinking) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message jarvis';
    messageDiv.id = 'thinkingIndicator';

    messageDiv.innerHTML = `
        <div class="message-avatar">J</div>
        <div class="message-bubble">
            <div class="thinking-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function removeThinkingIndicator() {
    const thinking = document.getElementById('thinkingIndicator');
    if (thinking) thinking.remove();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateConnectionStatus(status) {
    connectionBadge.className = `status-badge ${status}`;
    const statusText = connectionBadge.querySelector('.status-text');
    statusText.textContent = status === 'connected' ? 'Online' : 'Offline';
    
    if (status === 'connected') {
        checkSystemHealth();
        // Check health every 10 seconds to keep stats updated
        window.healthInterval = setInterval(checkSystemHealth, 10000);
    } else {
        if (window.healthInterval) {
            clearInterval(window.healthInterval);
        }
    }
}

async function checkSystemHealth() {
    try {
        const startTime = Date.now();
        const res = await fetch('/health');
        const data = await res.json();
        
        const latency = Date.now() - startTime;
        const latencyVal = document.getElementById('latencyVal');
        if (latencyVal) latencyVal.textContent = `${latency}ms`;
        
        const llmVal = document.getElementById('llmVal');
        if (llmVal) {
            llmVal.textContent = data.ollama === 'connected' ? 'READY' : 'OFFLINE';
            llmVal.className = data.ollama === 'connected' ? 'stat-value text-glow' : 'stat-value';
        }
        
        const sttVal = document.getElementById('sttVal');
        if (sttVal) {
            sttVal.textContent = data.stt === 'loaded' ? 'READY' : 'OFFLINE';
            sttVal.className = data.stt === 'loaded' ? 'stat-value text-glow' : 'stat-value';
        }
        
        const coreVal = document.getElementById('coreVal');
        if (coreVal) {
            coreVal.textContent = data.status.toUpperCase();
        }
    } catch (e) {
        console.error('[HEALTH] Check failed:', e);
    }
}

function updateOrbState(state) {
    // Apply state class to body for global style/accent colors mapping
    document.body.className = `fullscreen-mode ${state}`;
    
    orbContainer.className = `orb-container ${state}`;
    orbStatus.textContent = state.toUpperCase();

    // Show stop / hide send during thinking & speaking
    if (state === 'thinking' || state === 'speaking') {
        showStopButton();
    }

    // Reset on idle
    if (state === 'idle') {
        isProcessing = false;
        hideStopButton();
    }
}

function enableInputs(enabled) {
    textInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
    micBtn.disabled = !enabled;
}

// ─── Particle Constellation Backdrop ────────────────────────────
let canvas = null;
let ctx = null;
let particles = [];
const numParticles = 65;

class Particle {
    constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.radius = Math.random() * 2 + 1;
    }
    update() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
        if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
    }
    draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        
        // Match primary theme color
        const color = getComputedStyle(document.body).getPropertyValue('--accent-primary').trim() || '#00e5ff';
        ctx.fillStyle = color;
        ctx.fill();
    }
}

function initParticles() {
    canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    
    ctx = canvas.getContext('2d');
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    
    particles = [];
    for (let i = 0; i < numParticles; i++) {
        particles.push(new Particle());
    }
    
    requestAnimationFrame(animateParticles);
}

function resizeCanvas() {
    if (canvas) {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
}

function animateParticles() {
    if (!canvas || !ctx) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const colorStr = getComputedStyle(document.body).getPropertyValue('--accent-primary').trim() || '#00e5ff';
    
    for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();
        
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            
            if (dist < 120) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.lineWidth = (1 - dist / 120) * 0.4;
                
                // Add opacity in hex based on distance
                const alphaHex = Math.floor((1 - dist / 120) * 120).toString(16).padStart(2, '0');
                ctx.strokeStyle = colorStr + alphaHex;
                ctx.stroke();
            }
        }
    }
    requestAnimationFrame(animateParticles);
}

// ─── Event Listeners ───────────────────────────────────────────
sendBtn.addEventListener('click', sendTextMessage);

textInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage();
    }
});

micBtn.addEventListener('mousedown', (e) => {
    e.preventDefault();
    startRecording();
});

micBtn.addEventListener('mouseup', (e) => {
    e.preventDefault();
    stopRecording();
});

micBtn.addEventListener('mouseleave', () => {
    if (isRecording) stopRecording();
});

micBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    startRecording();
});

micBtn.addEventListener('touchend', (e) => {
    e.preventDefault();
    stopRecording();
});

clearBtn.addEventListener('click', () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'clear_history' }));
    }
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <p class="welcome-greeting">Memory cleared.</p>
            <p class="welcome-sub">Starting a fresh conversation, Sahil sir.</p>
        </div>
    `;
});

stopBtn.addEventListener('click', sendStop);

// ─── JARVIS Launch (called by auth.js after hand authentication) ───
window.initJarvis = function() {
    connectWebSocket();
    enableInputs(false);
    initParticles();
    hideStopButton();
};

// ─── Initialize (only particles for lock screen background) ────
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    hideStopButton();
});
