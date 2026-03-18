const API = {
    sessionStart: "/api/session/start/",
    sessionEnd: "/api/session/end/",
    transcribe: "/api/transcribe/",
    respond: "/api/respond/",
    tts: "/api/tts/",
    health: "/api/health/",
};

const state = {
    sessionId: null,
    mediaStream: null,
    recorder: null,
    recordingStream: null,
    recordingOwnsStream: false,
    recordingStartedAtMs: 0,
    audioChunks: [],
    isRecording: false,
    ws: null,
    hasVideo: false,
};

const dom = {
    startSessionBtn: document.getElementById("startSessionBtn"),
    endSessionBtn: document.getElementById("endSessionBtn"),
    micBtn: document.getElementById("micBtn"),
    webcamPreview: document.getElementById("webcamPreview"),
    transcriptLog: document.getElementById("transcriptLog"),
    assistantResponseField: document.getElementById("assistantResponseField"),
    assistantText: document.getElementById("assistantText"),
    assistantAudio: document.getElementById("assistantAudio"),
    sessionStatus: document.getElementById("sessionStatus"),
    aiDot: document.getElementById("aiDot"),
    aiIndicatorWrap: document.getElementById("aiIndicatorWrap"),
    aiIndicatorText: document.getElementById("aiIndicatorText"),
    visualSignals: document.getElementById("visualSignals"),
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
    if (!dom.errorLog) {
        return;
    }
    dom.errorLog.innerHTML = '<div class="error-empty">No errors yet.</div>';
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
        setAIState("", "AI reply ready");
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

    let stream;

    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
        state.hasVideo = true;
    } catch (_videoError) {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            state.hasVideo = false;
            appendLine("system", "Camera unavailable. Continuing with audio only.");
        } catch (audioError) {
            throw new Error(describeMediaError(audioError));
        }
    }

    state.mediaStream = stream;
    if (dom.webcamPreview) {
        dom.webcamPreview.srcObject = stream;
    }
    return stream;
}

function stopMedia() {
    if (!state.mediaStream) {
        return;
    }

    state.mediaStream.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
    state.hasVideo = false;

    if (dom.webcamPreview) {
        dom.webcamPreview.srcObject = null;
    }

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
    if (dom.micBtn) {
        dom.micBtn.disabled = !activeSession;
        dom.micBtn.textContent = "Start Talking";
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
                    vision_stub_enabled: true,
                },
            }),
        });

        state.sessionId = payload.session_id;
        connectSessionSocket(state.sessionId);

        setControlState(true);
        setStatus(`Session active: ${state.sessionId}`, "active");
        setAssistantReply("Session started. Press Start Talking to begin.");
        setAIState("", "AI idle");
        appendLine("system", "Session started.");
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

    // Empty mimeType option lets browser pick a default, often the most stable path.
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
            addError("Fresh audio stream opened but contains no live audio track.");
        }
    } catch (error) {
        const message = error && error.message ? error.message : "Unknown mic capture error.";
        addError(`Fresh audio capture unavailable, using fallback stream. ${message}`);
    }

    return options.concat(recordingStreamCandidates(baseStream));
}

async function startRecording() {
    if (!state.mediaStream || state.isRecording || !state.sessionId) {
        return;
    }

    const candidates = recorderCandidates();
    if (!candidates.length) {
        const message = "MediaRecorder is not available in this browser.";
        setStatus(message, "error");
        setAIState("error", "Recording unavailable");
        addError(message);
        return;
    }

    const streamOptions = await buildRecordingStreamOptions(state.mediaStream);
    if (!streamOptions.length) {
        const previewTracks = state.mediaStream.getAudioTracks().length;
        const message = "Could not prepare an audio recording stream. Verify microphone permission/device.";
        setStatus(message, "error");
        setAIState("error", "Recording unavailable");
        addError(`${message} preview_audio_tracks=${previewTracks}`);
        return;
    }

    state.audioChunks = [];
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
                    setStatus(`Recorder error: ${detail}`, "error");
                    setAIState("error", "Recorder error");
                    addError(`Recorder runtime error: ${detail}`);
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
        const message = `MediaRecorder could not start on this browser. ${startErrorMessage}`;
        setStatus(message, "error");
        setAIState("error", "Recording unavailable");
        addError(message);
        return;
    }
    state.recorder = recorder;
    state.recordingStream = activeStream;
    state.recordingOwnsStream = activeOwnsTracks;
    state.audioChunks = recordingChunks;

    state.recorder.onstop = async () => {
        const usedStream = state.recordingStream;
        const usedOwnsTracks = state.recordingOwnsStream;
        const usedTrackCount = usedStream ? usedStream.getTracks().length : 0;
        const usedAudioTrack = usedStream ? usedStream.getAudioTracks()[0] : null;
        const trackDetail = usedAudioTrack
            ? `track_label=${usedAudioTrack.label || "unknown"} muted=${usedAudioTrack.muted} enabled=${usedAudioTrack.enabled} ready=${usedAudioTrack.readyState}`
            : "track_label=none";
        const durationMs = Math.max(0, Date.now() - state.recordingStartedAtMs);

        state.isRecording = false;
        if (dom.micBtn) {
            dom.micBtn.textContent = "Start Talking";
        }

        // Give the browser a brief moment for final dataavailable events.
        window.setTimeout(async () => {
            const totalBytes = recordingChunks.reduce((sum, chunk) => sum + chunk.size, 0);

            if (!state.sessionId || recordingChunks.length === 0 || totalBytes === 0) {
                addError(
                    `Recorder stopped but no audio chunks were captured. duration_ms=${durationMs} stream_tracks=${usedTrackCount} ${trackDetail}`
                );
                if (usedStream && usedOwnsTracks) {
                    usedStream.getTracks().forEach((track) => track.stop());
                }
                state.recordingStream = null;
                state.recordingOwnsStream = false;
                state.recorder = null;
                return;
            }

            const blobType = activeMimeType || (recordingChunks[0] ? recordingChunks[0].type : "audio/webm");
            const blob = new Blob(recordingChunks, { type: blobType });

            if (durationMs < 350) {
                const message = "Recording too short. Hold the mic for at least 1 second.";
                setStatus(message, "error");
                setAIState("error", "Recording too short");
                addError(`${message} (bytes=${blob.size}, duration_ms=${durationMs}, mime=${blobType || "unknown"})`);
                if (usedStream && usedOwnsTracks) {
                    usedStream.getTracks().forEach((track) => track.stop());
                }
                state.recordingStream = null;
                state.recordingOwnsStream = false;
                state.recorder = null;
                return;
            }

            if (blob.size < 1024 && durationMs >= 1500) {
                const message = "Microphone captured near-zero audio data. Check OS input device/mute settings.";
                setStatus(message, "error");
                setAIState("error", "No mic signal");
                addError(`${message} (bytes=${blob.size}, duration_ms=${durationMs}, mime=${blobType || "unknown"}, ${trackDetail})`);
                if (usedStream && usedOwnsTracks) {
                    usedStream.getTracks().forEach((track) => track.stop());
                }
                state.recordingStream = null;
                state.recordingOwnsStream = false;
                state.recorder = null;
                return;
            }

            await processUtterance(blob);

            if (usedStream && usedOwnsTracks) {
                usedStream.getTracks().forEach((track) => track.stop());
            }
            state.recordingStream = null;
            state.recordingOwnsStream = false;
            state.recorder = null;
        }, 220);
    };

    state.isRecording = true;
    state.recordingStartedAtMs = Date.now();
    if (dom.micBtn) {
        dom.micBtn.textContent = "Stop Talking";
    }
    setAIState("listening", "Listening...");
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
            const message = "No speech detected. Try speaking closer to the mic.";
            setStatus(message, "error");
            setAIState("error", "No speech detected");
            addError(message);
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

        const assistantText = respondData.assistant_text || "";
        setAssistantReply(assistantText);
        appendLine("assistant", assistantText);

        setAIState("speaking", "AI is speaking");

        const ttsData = await apiFetch(API.tts, {
            method: "POST",
            body: JSON.stringify({
                session_id: state.sessionId,
                text: assistantText,
            }),
        });

        if (dom.assistantAudio) {
            dom.assistantAudio.src = ttsData.audio_url;
            dom.assistantAudio.onended = () => setAIState("", "AI idle");
            dom.assistantAudio.play().catch(() => {
                setStatus("Audio ready. Press play if autoplay is blocked.", "active");
            });
        }
    } catch (error) {
        const message = error && error.message ? error.message : "Pipeline failed.";
        setStatus(`Pipeline error: ${message}`, "error");
        setAIState("error", "Pipeline error");
        addError(`Pipeline error: ${message}`);
        appendLine("system", `Pipeline error: ${message}`);
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

function toggleRecording() {
    if (!state.sessionId) {
        return;
    }

    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording().catch((error) => {
            const message = error && error.message ? error.message : "Recording setup failed.";
            setStatus(`Recording failed: ${message}`, "error");
            setAIState("error", "Recording failed");
            addError(`Recording setup failed: ${message}`);
        });
    }
}

function initializeVisionHook() {
    setInterval(() => {
        if (!state.sessionId || !state.mediaStream || !dom.visualSignals) {
            return;
        }

        const lines = state.hasVideo
            ? [
                "face_detected: true",
                "looking_away: false",
                "low_light: false",
                "user_present: true",
            ]
            : [
                "face_detected: unavailable",
                "looking_away: unavailable",
                "low_light: unavailable",
                "user_present: true",
            ];

        dom.visualSignals.innerHTML = lines.map((line) => `<span>${line}</span>`).join("");
    }, 8000);
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
        "micBtn",
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
    if (dom.micBtn) {
        dom.micBtn.addEventListener("click", toggleRecording);
    }
    if (dom.clearErrorsBtn) {
        dom.clearErrorsBtn.addEventListener("click", clearErrors);
    }

    window.addEventListener("beforeunload", () => {
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
    clearErrors();
    bindEvents();

    if (!checkRequiredUI()) {
        setStatus("UI initialization failed", "error");
        return;
    }

    setControlState(false);
    setAssistantReply("Waiting for session to start.");
    setAIState("", "AI idle");
    initializeVisionHook();
    verifyBackend();
}

boot();
