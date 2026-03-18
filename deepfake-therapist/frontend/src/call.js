const API = {
    sessionStart: "/api/session/start/",
    sessionEnd: "/api/session/end/",
    transcribe: "/api/transcribe/",
    respond: "/api/respond/",
    tts: "/api/tts/",
    health: "/api/health/",
};

const THEME_STORAGE_KEY = "voice-therapist-theme";

const VAD = {
    pollMs: 120,
    startRms: 0.022,
    stopRms: 0.014,
    speechConfirmMs: 220,
    silenceStopMs: 950,
    minUtteranceMs: 700,
    maxUtteranceMs: 15000,
};

const state = {
    sessionId: null,
    mediaStream: null,
    recorder: null,
    recordingStream: null,
    recordingOwnsStream: false,
    recordingStartedAtMs: 0,
    isRecording: false,
    recordingStarting: false,
    ws: null,
    pipelineBusy: false,
    assistantSpeaking: false,
    continuousListening: false,
    blob: {
        audioContext: null,
        analyser: null,
        sourceNode: null,
        rafId: null,
        simulatedAtMs: 0,
    },
    vad: {
        audioContext: null,
        analyser: null,
        sourceNode: null,
        intervalId: null,
        speechMs: 0,
        silenceMs: 0,
        lastTs: 0,
    },
};

const dom = {
    startSessionBtn: document.getElementById("startSessionBtn"),
    endSessionBtn: document.getElementById("endSessionBtn"),
    themeToggleBtn: document.getElementById("themeToggleBtn"),
    autoListenHint: document.getElementById("autoListenHint"),
    transcriptLog: document.getElementById("transcriptLog"),
    assistantResponseField: document.getElementById("assistantResponseField"),
    assistantText: document.getElementById("assistantText"),
    assistantAudio: document.getElementById("assistantAudio"),
    avatarRing: document.getElementById("avatarRing"),
    voiceBlob: document.getElementById("voiceBlob"),
    sessionStatus: document.getElementById("sessionStatus"),
    aiDot: document.getElementById("aiDot"),
    aiIndicatorWrap: document.getElementById("aiIndicatorWrap"),
    aiIndicatorText: document.getElementById("aiIndicatorText"),
    errorPanel: document.getElementById("errorPanel"),
    errorLog: document.getElementById("errorLog"),
    clearErrorsBtn: document.getElementById("clearErrorsBtn"),
};

function nowLabel() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function addError(message) {
    const text = String(message || "Unknown UI error");
    console.error(text);

    if (!dom.errorLog) {
        return;
    }

    if (dom.errorPanel) {
        dom.errorPanel.hidden = false;
    }

    const empty = dom.errorLog.querySelector(".error-empty");
    if (empty) {
        empty.remove();
    }

    const row = document.createElement("div");
    row.className = "error-item";
    row.textContent = `[${nowLabel()}] ${text}`;
    dom.errorLog.appendChild(row);
    dom.errorLog.scrollTop = dom.errorLog.scrollHeight;
}

function clearErrors() {
    if (dom.errorPanel) {
        dom.errorPanel.hidden = true;
    }
    if (!dom.errorLog) {
        return;
    }
    dom.errorLog.innerHTML = '<div class="error-empty">No errors yet.</div>';
}

function applyTheme(theme) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = nextTheme;
    if (dom.themeToggleBtn) {
        dom.themeToggleBtn.textContent = nextTheme === "dark" ? "Light Mode" : "Dark Mode";
    }
}

function initializeTheme() {
    let saved = null;
    try {
        saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    } catch (_error) {
        saved = null;
    }

    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(saved || (prefersDark ? "dark" : "light"));
}

function toggleTheme() {
    const current = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    try {
        window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch (_error) {
        // Ignore storage write failures.
    }
}

function setAssistantReply(text) {
    const value = String(text || "");
    if (dom.assistantResponseField) {
        dom.assistantResponseField.value = value;
    }
    if (dom.assistantText) {
        dom.assistantText.textContent = value;
    }
}

function setStatus(text, tone) {
    if (!dom.sessionStatus) {
        return;
    }
    dom.sessionStatus.textContent = String(text || "");
    dom.sessionStatus.dataset.tone = tone || "idle";
    dom.sessionStatus.title = String(text || "");
}

function setAIState(type, text) {
    if (dom.aiDot) {
        dom.aiDot.className = "dot";
        if (type) {
            dom.aiDot.classList.add(type);
        }
    }

    if (dom.aiIndicatorWrap) {
        dom.aiIndicatorWrap.dataset.state = type || "idle";
    }

    if (dom.aiIndicatorText) {
        dom.aiIndicatorText.textContent = String(text || "");
    }
}

function setAvatarSpeaking(isSpeaking) {
    if (!dom.avatarRing) {
        return;
    }
    dom.avatarRing.classList.toggle("speaking", Boolean(isSpeaking));
    if (isSpeaking) {
        startBlobPulse();
    } else {
        stopBlobPulse();
    }
}

function setAvatarMouth(openness) {
    const level = Math.max(0, Math.min(1, Number(openness) || 0));
    applyBlobIntensity(level);
}

function applyBlobIntensity(level) {
    if (!dom.voiceBlob) {
        return;
    }
    const scale = 0.9 + level * 0.42;
    const glow = 0.18 + level * 0.82;
    dom.voiceBlob.style.setProperty("--blob-scale", scale.toFixed(3));
    dom.voiceBlob.style.setProperty("--blob-glow", glow.toFixed(3));
}

function ensureBlobAudioAnalyser() {
    if (state.blob.analyser || !dom.assistantAudio) {
        return true;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
        return false;
    }

    try {
        state.blob.audioContext = state.blob.audioContext || new AudioCtx();
        if (state.blob.audioContext.state === "suspended") {
            state.blob.audioContext.resume().catch(() => {});
        }

        state.blob.sourceNode = state.blob.audioContext.createMediaElementSource(dom.assistantAudio);
        state.blob.analyser = state.blob.audioContext.createAnalyser();
        state.blob.analyser.fftSize = 1024;
        state.blob.analyser.smoothingTimeConstant = 0.82;
        state.blob.sourceNode.connect(state.blob.analyser);
        state.blob.analyser.connect(state.blob.audioContext.destination);
        return true;
    } catch (_error) {
        state.blob.analyser = null;
        return false;
    }
}

function readBlobAudioLevel() {
    if (!state.blob.analyser) {
        return 0;
    }
    const analyser = state.blob.analyser;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i += 1) {
        const centered = (data[i] - 128) / 128;
        sum += centered * centered;
    }
    return Math.sqrt(sum / data.length);
}

function blobTick() {
    if (!state.assistantSpeaking) {
        return;
    }
    let level = 0.18;
    const hasAnalyser = ensureBlobAudioAnalyser();
    if (hasAnalyser && state.blob.analyser) {
        level = Math.min(1, Math.max(0.08, readBlobAudioLevel() * 5.0));
    } else {
        const t = Date.now() / 1000;
        level = 0.22 + Math.abs(Math.sin(t * 9.0)) * 0.45;
    }
    applyBlobIntensity(level);
    state.blob.rafId = window.requestAnimationFrame(blobTick);
}

function startBlobPulse() {
    if (state.blob.rafId) {
        return;
    }
    state.blob.simulatedAtMs = Date.now();
    state.blob.rafId = window.requestAnimationFrame(blobTick);
}

function stopBlobPulse() {
    if (state.blob.rafId) {
        window.cancelAnimationFrame(state.blob.rafId);
        state.blob.rafId = null;
    }
    applyBlobIntensity(0.04);
}

function stopAvatarAnimation() {
    stopBlobPulse();
    setAvatarMouth(0);
}

function stepAvatarAnimation() {
    startBlobPulse();
}

function startAvatarAnimation(_payload) {
    stopAvatarAnimation();
    startBlobPulse();
}

function appendLine(role, text) {
    if (!dom.transcriptLog) {
        return;
    }

    const item = document.createElement("div");
    item.className = `line ${role}`;
    item.textContent = `${role}: ${text}`;
    dom.transcriptLog.appendChild(item);
    dom.transcriptLog.scrollTop = dom.transcriptLog.scrollHeight;
}

function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute("content") && meta.getAttribute("content") !== "NOTPROVIDED") {
        return meta.getAttribute("content");
    }

    const cookie = document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith("csrftoken="));

    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

async function apiFetch(url, options) {
    const requestOptions = options || {};
    const headers = requestOptions.headers || {};
    const csrf = getCsrfToken();

    if (!(requestOptions.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }
    if (csrf) {
        headers["X-CSRFToken"] = csrf;
    }

    let response;
    try {
        response = await fetch(url, {
            ...requestOptions,
            headers,
        });
    } catch (_error) {
        throw new Error("Cannot reach backend server. Confirm Django is running.");
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : {};

    if (!response.ok) {
        throw new Error(payload.error || `Request failed (${response.status})`);
    }

    return payload;
}

function connectSessionSocket(sessionId) {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socketUrl = `${protocol}://${window.location.host}/ws/session/${sessionId}/`;

    try {
        state.ws = new WebSocket(socketUrl);
    } catch (_error) {
        addError("Could not create websocket connection.");
        return;
    }

    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleSessionEvent(data.event, data.payload || {});
        } catch (_error) {
            addError("WebSocket message parse failed.");
        }
    };

    state.ws.onerror = () => {
        addError("Realtime channel disconnected. Session continues without live events.");
    };

    state.ws.onclose = () => {
        state.ws = null;
    };
}

function handleSessionEvent(event, payload) {
    if (event === "thinking") {
        setAIState("thinking", "AI is thinking");
    } else if (event === "speaking") {
        setAIState("speaking", "AI is speaking");
    } else if (event === "listening") {
        setAIState("listening", "Transcribing audio");
    } else if (event === "error") {
        setAIState("error", payload.detail || "Error");
        addError(payload.detail || "Session event error received.");
    } else if (event === "response_ready") {
        setAIState("listening", "Listening automatically");
    }
}

function describeMediaError(error) {
    const name = error && error.name ? error.name : "";

    if (name === "NotAllowedError") {
        return "Microphone permission denied. Allow mic access and retry.";
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        return "No microphone found on this device.";
    }
    if (name === "NotReadableError") {
        return "Microphone is busy in another app.";
    }
    if (window.isSecureContext === false) {
        return "Mic requires secure context. Use http://localhost:8000.";
    }
    return error && error.message ? error.message : "Unable to access microphone.";
}

async function requestMedia() {
    if (state.mediaStream) {
        return state.mediaStream;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Browser does not support getUserMedia.");
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
            video: false,
        });

        if (!stream.getAudioTracks().length) {
            throw new Error("No microphone audio track is available in the stream.");
        }

        state.mediaStream = stream;
        return stream;
    } catch (error) {
        throw new Error(describeMediaError(error));
    }
}

function stopMedia() {
    if (state.mediaStream) {
        state.mediaStream.getTracks().forEach((track) => track.stop());
    }
    state.mediaStream = null;

    if (state.recordingStream && state.recordingOwnsStream) {
        state.recordingStream.getTracks().forEach((track) => track.stop());
    }
    state.recordingStream = null;
    state.recordingOwnsStream = false;
}

function setControlState(activeSession) {
    if (dom.startSessionBtn) {
        dom.startSessionBtn.disabled = activeSession;
    }
    if (dom.endSessionBtn) {
        dom.endSessionBtn.disabled = !activeSession;
    }
    if (dom.autoListenHint) {
        dom.autoListenHint.textContent = activeSession
            ? "Auto-listening is on. Speak naturally; pauses are detected automatically."
            : "Auto-listening is off.";
    }
}

function cleanupAudioAnalysis() {
    if (state.vad.intervalId) {
        window.clearInterval(state.vad.intervalId);
        state.vad.intervalId = null;
    }

    if (state.vad.sourceNode) {
        try {
            state.vad.sourceNode.disconnect();
        } catch (_error) {
            // Ignore disconnect failures.
        }
        state.vad.sourceNode = null;
    }

    if (state.vad.analyser) {
        try {
            state.vad.analyser.disconnect();
        } catch (_error) {
            // Ignore disconnect failures.
        }
        state.vad.analyser = null;
    }

    if (state.vad.audioContext) {
        state.vad.audioContext.close().catch(() => {
            // Ignore close failures.
        });
        state.vad.audioContext = null;
    }

    state.vad.speechMs = 0;
    state.vad.silenceMs = 0;
    state.vad.lastTs = 0;
}

async function startContinuousListening() {
    if (state.continuousListening || !state.sessionId || !state.mediaStream) {
        return;
    }

    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) {
        addError("Web Audio API is not available in this browser. Auto-listening cannot start.");
        return;
    }

    cleanupAudioAnalysis();

    state.vad.audioContext = new AudioCtx();
    if (state.vad.audioContext.state === "suspended") {
        await state.vad.audioContext.resume().catch(() => {
            // Some browsers may auto-resume on first speech.
        });
    }

    state.vad.sourceNode = state.vad.audioContext.createMediaStreamSource(state.mediaStream);
    state.vad.analyser = state.vad.audioContext.createAnalyser();
    state.vad.analyser.fftSize = 1024;
    state.vad.analyser.smoothingTimeConstant = 0.85;
    state.vad.sourceNode.connect(state.vad.analyser);

    state.continuousListening = true;
    state.vad.lastTs = performance.now();
    state.vad.intervalId = window.setInterval(runVadTick, VAD.pollMs);
    setAIState("listening", "Listening automatically");
}

function stopContinuousListening() {
    state.continuousListening = false;
    cleanupAudioAnalysis();
}

function sampleRms(analyser) {
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);

    let sum = 0;
    for (let i = 0; i < data.length; i += 1) {
        const centered = (data[i] - 128) / 128;
        sum += centered * centered;
    }

    return Math.sqrt(sum / data.length);
}

function runVadTick() {
    if (!state.continuousListening || !state.sessionId || !state.vad.analyser) {
        return;
    }

    const now = performance.now();
    const deltaMs = Math.max(1, now - (state.vad.lastTs || now));
    state.vad.lastTs = now;

    if (state.pipelineBusy || state.assistantSpeaking) {
        state.vad.speechMs = 0;
        state.vad.silenceMs = 0;
        return;
    }

    const rms = sampleRms(state.vad.analyser);

    if (state.isRecording) {
        const durationMs = Date.now() - state.recordingStartedAtMs;

        if (rms <= VAD.stopRms) {
            state.vad.silenceMs += deltaMs;
        } else {
            state.vad.silenceMs = 0;
        }

        if (
            (state.vad.silenceMs >= VAD.silenceStopMs && durationMs >= VAD.minUtteranceMs) ||
            durationMs >= VAD.maxUtteranceMs
        ) {
            stopRecording();
            state.vad.silenceMs = 0;
        }

        return;
    }

    if (rms >= VAD.startRms) {
        state.vad.speechMs += deltaMs;
    } else {
        state.vad.speechMs = Math.max(0, state.vad.speechMs - deltaMs * 0.7);
    }

    if (state.vad.speechMs >= VAD.speechConfirmMs) {
        state.vad.speechMs = 0;
        state.vad.silenceMs = 0;
        startRecording().catch((error) => {
            const message = error && error.message ? error.message : "Recording setup failed.";
            addError(`Recording setup failed: ${message}`);
            setAIState("error", "Recording failed");
        });
    }
}

async function startSession() {
    try {
        setStatus("Starting session...", "idle");
        await requestMedia();

        const payload = await apiFetch(API.sessionStart, {
            method: "POST",
            body: JSON.stringify({
                metadata: {
                    client: "web-call-ui",
                    vision_stub_enabled: false,
                },
            }),
        });

        state.sessionId = payload.session_id;
        connectSessionSocket(state.sessionId);
        setControlState(true);

        await startContinuousListening();

        setStatus(`Session active: ${state.sessionId}`, "active");
        setAssistantReply("Session started. Speak naturally; I will auto-detect when you start and stop talking.");
        setAIState("listening", "Listening automatically");
        appendLine("system", "Session started. Auto-listening is enabled.");
    } catch (error) {
        const message = error && error.message ? error.message : "Start failed.";
        setStatus(`Failed to start session: ${message}`, "error");
        setAIState("error", "Unable to start");
        addError(`Start failed: ${message}`);
        appendLine("system", `Start failed: ${message}`);
    }
}

async function endSession() {
    try {
        stopContinuousListening();

        if (state.isRecording) {
            stopRecording();
        }

        if (state.sessionId) {
            await apiFetch(API.sessionEnd, {
                method: "POST",
                body: JSON.stringify({ session_id: state.sessionId }),
            });
        }

        if (state.ws) {
            state.ws.close();
            state.ws = null;
        }

        stopMedia();
        state.sessionId = null;
        state.pipelineBusy = false;
        state.assistantSpeaking = false;
        setAvatarSpeaking(false);
        stopAvatarAnimation();

        setControlState(false);
        setStatus("Session ended", "ended");
        setAIState("", "AI idle");
        setAssistantReply("Session ended.");
        appendLine("system", "Session ended.");
    } catch (error) {
        const message = error && error.message ? error.message : "End failed.";
        setStatus(`Failed to end session: ${message}`, "error");
        setAIState("error", "End failed");
        addError(`End failed: ${message}`);
        appendLine("system", `End failed: ${message}`);
    }
}

function recorderCandidates() {
    if (!window.MediaRecorder) {
        return [];
    }

    const preferred = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
    const supported = preferred.filter((value) => {
        if (!MediaRecorder.isTypeSupported) {
            return false;
        }
        return MediaRecorder.isTypeSupported(value);
    });

    supported.push("");
    return [...new Set(supported)];
}

function recordingStreamCandidates(baseStream) {
    const tracks = baseStream.getAudioTracks().filter((track) => track.readyState === "live");
    if (!tracks.length) {
        return [];
    }

    const source = tracks[0];
    const candidates = [];

    if (typeof source.clone === "function") {
        candidates.push({
            stream: new MediaStream([source.clone()]),
            ownsTracks: true,
            label: "cloned-audio-track",
        });
    }

    candidates.push({
        stream: new MediaStream([source]),
        ownsTracks: false,
        label: "original-audio-track",
    });

    return candidates;
}

async function buildRecordingStreamOptions(baseStream) {
    const options = [];

    try {
        const freshAudio = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
            },
            video: false,
        });
        const freshTracks = freshAudio.getAudioTracks().filter((track) => track.readyState === "live");
        if (freshTracks.length > 0) {
            options.push({
                stream: freshAudio,
                ownsTracks: true,
                label: "fresh-audio-stream",
            });
        } else {
            freshAudio.getTracks().forEach((track) => track.stop());
        }
    } catch (_error) {
        // Fallback candidates below handle this path.
    }

    return options.concat(recordingStreamCandidates(baseStream));
}

async function startRecording() {
    if (!state.mediaStream || state.isRecording || !state.sessionId || state.recordingStarting) {
        return;
    }

    if (state.pipelineBusy || state.assistantSpeaking) {
        return;
    }

    state.recordingStarting = true;

    try {
        const candidates = recorderCandidates();
        if (!candidates.length) {
            throw new Error("MediaRecorder is not available in this browser.");
        }

        const streamOptions = await buildRecordingStreamOptions(state.mediaStream);
        if (!streamOptions.length) {
            throw new Error("Could not prepare an audio recording stream. Verify microphone permission/device.");
        }

        const recordingChunks = [];
        let recorder = null;
        let activeMimeType = "";
        let activeStream = null;
        let activeOwnsTracks = false;
        let startErrorMessage = "";

        for (const streamOption of streamOptions) {
            for (const mimeType of candidates) {
                try {
                    const attemptRecorder = mimeType
                        ? new MediaRecorder(streamOption.stream, { mimeType })
                        : new MediaRecorder(streamOption.stream);

                    attemptRecorder.ondataavailable = (event) => {
                        if (event.data && event.data.size > 0) {
                            recordingChunks.push(event.data);
                        }
                    };

                    attemptRecorder.onerror = (event) => {
                        const detail = event && event.error && event.error.message ? event.error.message : "Recorder runtime error.";
                        addError(`Recorder runtime error: ${detail}`);
                        setAIState("error", "Recorder error");
                    };

                    attemptRecorder.start(1000);

                    recorder = attemptRecorder;
                    activeMimeType = mimeType;
                    activeStream = streamOption.stream;
                    activeOwnsTracks = streamOption.ownsTracks;
                    break;
                } catch (error) {
                    startErrorMessage = error && error.message ? error.message : "MediaRecorder start failed.";
                }
            }

            if (recorder) {
                break;
            }

            if (streamOption.ownsTracks) {
                streamOption.stream.getTracks().forEach((track) => track.stop());
            }
        }

        if (!recorder) {
            throw new Error(`MediaRecorder could not start on this browser. ${startErrorMessage}`);
        }

        state.recorder = recorder;
        state.recordingStream = activeStream;
        state.recordingOwnsStream = activeOwnsTracks;

        state.recorder.onstop = async () => {
            const usedStream = state.recordingStream;
            const usedOwnsTracks = state.recordingOwnsStream;
            const durationMs = Math.max(0, Date.now() - state.recordingStartedAtMs);
            const totalBytes = recordingChunks.reduce((sum, chunk) => sum + chunk.size, 0);

            state.isRecording = false;

            window.setTimeout(async () => {
                if (!state.sessionId || recordingChunks.length === 0 || totalBytes === 0) {
                    if (durationMs > 1200) {
                        addError(`Recorder stopped with empty audio data. duration_ms=${durationMs}`);
                    }
                    if (usedStream && usedOwnsTracks) {
                        usedStream.getTracks().forEach((track) => track.stop());
                    }
                    state.recordingStream = null;
                    state.recordingOwnsStream = false;
                    state.recorder = null;
                    if (state.sessionId) {
                        setAIState("listening", "Listening automatically");
                    }
                    return;
                }

                const blobType = activeMimeType || (recordingChunks[0] ? recordingChunks[0].type : "audio/webm");
                const blob = new Blob(recordingChunks, { type: blobType });

                if (durationMs < 400 || (blob.size < 700 && durationMs < 2000)) {
                    if (usedStream && usedOwnsTracks) {
                        usedStream.getTracks().forEach((track) => track.stop());
                    }
                    state.recordingStream = null;
                    state.recordingOwnsStream = false;
                    state.recorder = null;
                    if (state.sessionId) {
                        setAIState("listening", "Listening automatically");
                    }
                    return;
                }

                if (blob.size < 1024 && durationMs >= 1500) {
                    addError(`Microphone captured near-zero audio data. bytes=${blob.size} duration_ms=${durationMs}`);
                    if (usedStream && usedOwnsTracks) {
                        usedStream.getTracks().forEach((track) => track.stop());
                    }
                    state.recordingStream = null;
                    state.recordingOwnsStream = false;
                    state.recorder = null;
                    if (state.sessionId) {
                        setAIState("listening", "Listening automatically");
                    }
                    return;
                }

                await processUtterance(blob);

                if (usedStream && usedOwnsTracks) {
                    usedStream.getTracks().forEach((track) => track.stop());
                }
                state.recordingStream = null;
                state.recordingOwnsStream = false;
                state.recorder = null;

                if (state.sessionId && !state.assistantSpeaking && !state.pipelineBusy) {
                    setAIState("listening", "Listening automatically");
                }
            }, 220);
        };

        state.isRecording = true;
        state.recordingStartedAtMs = Date.now();
        setAIState("listening", "Listening...");
    } finally {
        state.recordingStarting = false;
    }
}

function stopRecording() {
    if (!state.recorder || !state.isRecording) {
        return;
    }

    try {
        if (state.recorder.state === "recording") {
            state.recorder.stop();
        }
    } catch (_error) {
        addError("Recorder stop failed.");
    }
}

async function processUtterance(audioBlob) {
    if (!state.sessionId) {
        return;
    }

    state.pipelineBusy = true;

    try {
        setAIState("listening", "Transcribing...");

        const formData = new FormData();
        formData.append("session_id", state.sessionId);
        formData.append("audio", audioBlob, buildAudioFilename(audioBlob));

        const transcribeData = await apiFetch(API.transcribe, {
            method: "POST",
            body: formData,
        });

        const transcript = (transcribeData.transcript || "").trim();
        if (!transcript) {
            return;
        }

        appendLine("user", transcript);
        setAIState("thinking", "AI is thinking");

        const respondData = await apiFetch(API.respond, {
            method: "POST",
            body: JSON.stringify({
                session_id: state.sessionId,
                transcript,
            }),
        });

        const assistantText = (respondData.assistant_text || "").trim();
        if (!assistantText) {
            return;
        }

        setAssistantReply(assistantText);
        appendLine("assistant", assistantText);

        const ttsData = await apiFetch(API.tts, {
            method: "POST",
            body: JSON.stringify({
                session_id: state.sessionId,
                text: assistantText,
            }),
        });

        if (dom.assistantAudio) {
            const playbackUrl = ttsData.audio_url;

            const handlePlaybackEnd = () => {
                state.assistantSpeaking = false;
                setAvatarSpeaking(false);
                stopAvatarAnimation();
                if (state.sessionId) {
                    setAIState("listening", "Listening automatically");
                } else {
                    setAIState("", "AI idle");
                }
            };

            dom.assistantAudio.onplay = () => {
                state.assistantSpeaking = true;
                setAvatarSpeaking(true);
                startAvatarAnimation(null);
                setAIState("speaking", "AI is speaking");
            };
            dom.assistantAudio.onended = handlePlaybackEnd;
            dom.assistantAudio.onerror = handlePlaybackEnd;

            dom.assistantAudio.src = playbackUrl;
            await dom.assistantAudio.play().catch(() => {
                handlePlaybackEnd();
                setStatus("Audio ready. Press play if autoplay is blocked.", "active");
            });
        }
    } catch (error) {
        const message = error && error.message ? error.message : "Pipeline failed.";
        setStatus(`Pipeline error: ${message}`, "error");
        setAIState("error", "Pipeline error");
        addError(`Pipeline error: ${message}`);
        appendLine("system", `Pipeline error: ${message}`);
    } finally {
        state.pipelineBusy = false;
        if (state.sessionId && !state.assistantSpeaking && !state.isRecording) {
            setAIState("listening", "Listening automatically");
        }
    }
}

function buildAudioFilename(audioBlob) {
    const mime = String((audioBlob && audioBlob.type) || "").toLowerCase();
    const extByMime = {
        "audio/webm": "webm",
        "audio/mp4": "mp4",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/ogg": "ogg",
    };

    const exactExt = extByMime[mime];
    if (exactExt) {
        return `utterance.${exactExt}`;
    }

    const wildcard = Object.keys(extByMime).find((key) => mime.startsWith(`${key};`));
    if (wildcard) {
        return `utterance.${extByMime[wildcard]}`;
    }

    return "utterance.webm";
}

async function verifyBackend() {
    try {
        const health = await apiFetch(API.health, { method: "GET" });
        if (health && health.status === "healthy") {
            setStatus("Idle", "idle");
            return;
        }
        throw new Error("Unexpected health response.");
    } catch (error) {
        const message = error && error.message ? error.message : "Backend health check failed.";
        setStatus(`Backend unavailable: ${message}`, "error");
        setAIState("error", "Backend offline");
        addError(`Backend check failed: ${message}`);
    }
}

function checkRequiredUI() {
    const required = [
        "startSessionBtn",
        "endSessionBtn",
        "sessionStatus",
        "aiIndicatorText",
        "transcriptLog",
        "assistantResponseField",
        "assistantAudio",
        "errorLog",
    ];

    const missing = required.filter((key) => !dom[key]);
    if (missing.length > 0) {
        addError(`UI is missing required elements: ${missing.join(", ")}`);
        return false;
    }

    return true;
}

function bindEvents() {
    if (dom.startSessionBtn) {
        dom.startSessionBtn.addEventListener("click", startSession);
    }
    if (dom.endSessionBtn) {
        dom.endSessionBtn.addEventListener("click", endSession);
    }
    if (dom.themeToggleBtn) {
        dom.themeToggleBtn.addEventListener("click", toggleTheme);
    }
    if (dom.clearErrorsBtn) {
        dom.clearErrorsBtn.addEventListener("click", clearErrors);
    }

    window.addEventListener("beforeunload", () => {
        stopContinuousListening();
        setAvatarSpeaking(false);
        stopAvatarAnimation();
        if (state.blob.audioContext) {
            state.blob.audioContext.close().catch(() => {});
            state.blob.audioContext = null;
            state.blob.analyser = null;
            state.blob.sourceNode = null;
        }
        if (state.ws) {
            state.ws.close();
        }
        stopMedia();
    });

    window.addEventListener("error", (event) => {
        addError(`UI error: ${event.message}`);
    });

    window.addEventListener("unhandledrejection", (event) => {
        const reason = event && event.reason ? event.reason : "Unhandled promise rejection.";
        const message = reason && reason.message ? reason.message : String(reason);
        addError(`Unhandled rejection: ${message}`);
    });
}

function boot() {
    initializeTheme();
    clearErrors();
    bindEvents();

    if (!checkRequiredUI()) {
        setStatus("UI initialization failed", "error");
        return;
    }

    setControlState(false);
    setAssistantReply("Waiting for session to start.");
    setAIState("", "AI idle");
    setAvatarSpeaking(false);
    setAvatarMouth(0);
    verifyBackend();
}

boot();
