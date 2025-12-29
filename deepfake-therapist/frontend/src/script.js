/**
 * MindfulAI - AI Therapist Application
 * 
 * A comprehensive mental wellness chatbot with:
 * - Speech Recognition (STT) via Web Speech API
 * - Speech Synthesis (TTS) 
 * - Real-time chat with Gemini AI
 * - Animated avatar responses
 * - Session management
 */

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
    API_BASE: '',
    DIALOGUE_ENDPOINT: '/api/dialogue/',
    HEALTH_ENDPOINT: '/api/health/',
    WS_ENDPOINT: `ws://${window.location.host}/ws/stream/`,
    A2F_ENDPOINT: '/api/a2f/latest/',
    COOLDOWN_MS: 3000,
};

// =============================================================================
// State
// =============================================================================

const state = {
    isRecording: false,
    isProcessing: false,
    isSpeaking: false,
    isCooldown: false,
    cooldownTimer: null,
    recognition: null,
    websocket: null,
    currentTranscript: '',
    voices: [],
    selectedVoice: null,
    ttsEnabled: true,
    apiKey: '',
    messageHistory: [],
    sessionId: Date.now().toString(36),
    provider: 'gemini',
    speechRate: 0.95,
    speechPitch: 1.0,
    streamingId: 0,
    a2f: {
        runId: '',
        frames: [],
        emotions: [],
        audioUrl: '',
        audio: null,
        playing: false,
        loaded: false,
        lastFrameIndex: 0,
        lastEmotionIndex: 0,
    },
};

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {};

function initElements() {
    elements.micButton = document.getElementById('mic-button');
    elements.micIcon = document.getElementById('mic-icon');
    elements.stopIcon = document.getElementById('stop-icon');
    elements.sendButton = document.getElementById('send-button');
    elements.textInput = document.getElementById('text-input');
    elements.chatContainer = document.getElementById('chat-container');
    elements.statusDot = document.getElementById('status-dot');
    elements.statusText = document.getElementById('status-text');
    elements.aiState = document.getElementById('ai-state');
    elements.avatarRing = document.getElementById('avatar-ring');
    elements.avatarContainer = document.getElementById('avatar-container');
    elements.voiceViz = document.getElementById('voice-viz');
    elements.themeToggle = document.getElementById('theme-toggle');
    elements.sunIcon = document.getElementById('sun-icon');
    elements.moonIcon = document.getElementById('moon-icon');
    elements.settingsToggle = document.getElementById('settings-toggle');
    elements.settingsPanel = document.getElementById('settings-panel');
    elements.voiceSelect = document.getElementById('voice-select');
    elements.ttsToggle = document.getElementById('tts-toggle');
    elements.apiKeyInput = document.getElementById('api-key-input');
    elements.providerSelect = document.getElementById('provider-select');
    elements.rateSlider = document.getElementById('rate-slider');
    elements.pitchSlider = document.getElementById('pitch-slider');
    elements.cooldownBar = document.getElementById('cooldown-bar');
    elements.cooldownProgress = document.getElementById('cooldown-progress');
    elements.connectionStatus = document.getElementById('connection-status');
    elements.quickPrompts = document.querySelectorAll('.quick-prompt');
    elements.a2fLoad = document.getElementById('a2f-load');
    elements.a2fPlay = document.getElementById('a2f-play');
    elements.a2fStop = document.getElementById('a2f-stop');
    elements.a2fStatus = document.getElementById('a2f-status');
}

// =============================================================================
// Initialization
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🧠 MindfulAI initialized');
    
    initElements();
    initTheme();
    initVoices();
    initSpeechRecognition();
    initWebSocket();
    initEventListeners();
    loadSavedSettings();
    checkServerHealth();
    initAvatar();
});

/**
 * Initialize dark/light theme
 */
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
        updateThemeIcons(true);
    }
}

function updateThemeIcons(isDark) {
    if (isDark) {
        elements.sunIcon.classList.remove('hidden');
        elements.moonIcon.classList.add('hidden');
    } else {
        elements.sunIcon.classList.add('hidden');
        elements.moonIcon.classList.remove('hidden');
    }
}

/**
 * Initialize Speech Recognition
 */
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        console.warn('Speech Recognition not supported');
        if (elements.micButton) {
            elements.micButton.disabled = true;
            elements.micButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
        return;
    }
    
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = false;
    state.recognition.interimResults = true;
    state.recognition.lang = 'en-US';
    
    state.recognition.onstart = () => {
        state.isRecording = true;
        updateMicButton(true);
        setAIState('Listening...', 'listening');
        showVoiceVisualization(true);
    };
    
    state.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        state.currentTranscript = finalTranscript || interimTranscript;
        
        // Show live transcript in input
        if (elements.textInput) {
            elements.textInput.value = state.currentTranscript;
        }
    };
    
    state.recognition.onend = () => {
        state.isRecording = false;
        updateMicButton(false);
        showVoiceVisualization(false);
        
        if (state.currentTranscript.trim()) {
            processUserInput(state.currentTranscript.trim());
        } else {
            setAIState('Ready to help', 'ready');
        }
    };
    
    state.recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        state.isRecording = false;
        updateMicButton(false);
        showVoiceVisualization(false);
        
        if (event.error === 'not-allowed') {
            setAIState('Microphone access denied', 'error');
        } else if (event.error !== 'no-speech') {
            setAIState('Error: ' + event.error, 'error');
        }
    };
}

/**
 * Initialize TTS voices
 */
function initVoices() {
    function loadVoices() {
        state.voices = speechSynthesis.getVoices();
        
        if (!elements.voiceSelect) return;
        elements.voiceSelect.innerHTML = '';
        
        // Filter for good quality voices
        const englishVoices = state.voices.filter(v => v.lang.startsWith('en'));
        
        // Prioritize high quality voices
        const prioritizedVoices = englishVoices.sort((a, b) => {
            const aScore = getVoiceQualityScore(a);
            const bScore = getVoiceQualityScore(b);
            return bScore - aScore;
        });
        
        prioritizedVoices.forEach((voice, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = `${voice.name}`;
            if (index === 0) {
                option.selected = true;
                state.selectedVoice = voice;
            }
            elements.voiceSelect.appendChild(option);
        });
        
        state.englishVoices = prioritizedVoices;
    }
    
    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = loadVoices;
    }
}

function getVoiceQualityScore(voice) {
    let score = 0;
    const name = voice.name.toLowerCase();
    
    if (name.includes('google')) score += 10;
    if (name.includes('microsoft')) score += 8;
    if (name.includes('natural')) score += 5;
    if (name.includes('neural')) score += 5;
    if (name.includes('samantha')) score += 3;
    if (voice.localService === false) score += 2; // Cloud voices are usually better
    
    return score;
}

/**
 * Initialize WebSocket
 */
function initWebSocket() {
    try {
        state.websocket = new WebSocket(CONFIG.WS_ENDPOINT);
        
        state.websocket.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
        };
        
        state.websocket.onmessage = (event) => {
            handleWebSocketMessage(JSON.parse(event.data));
        };
        
        state.websocket.onerror = (error) => {
            console.warn('WebSocket error:', error);
        };
        
        state.websocket.onclose = () => {
            console.log('WebSocket closed');
            updateConnectionStatus(false);
            setTimeout(initWebSocket, 3000);
        };
    } catch (error) {
        console.warn('WebSocket not available');
    }
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'connected':
            console.log('WebSocket ready');
            break;
            
        case 'start':
            setAIState('Thinking...', 'processing');
            state.currentResponse = '';
            ensureStreamingPlaceholder();
            break;
            
        case 'token':
            state.currentResponse = (state.currentResponse || '') + message.content;
            updateLastAIMessage(state.currentResponse);
            break;
            
        case 'done':
            state.isProcessing = false;
            setAIState('Ready to help', 'ready');
            
            if (state.ttsEnabled && state.currentResponse) {
                speakText(state.currentResponse);
            }
            
            finalizeStreamingMessage();
            startCooldown();
            break;
            
        case 'error':
            state.isProcessing = false;
            setAIState('Error occurred', 'error');
            finalizeStreamingMessage();
            break;
    }
}

/**
 * Initialize event listeners
 */
function initEventListeners() {
    // Mic button
    elements.micButton?.addEventListener('click', toggleRecording);
    
    // Send button
    elements.sendButton?.addEventListener('click', () => {
        const text = elements.textInput.value.trim();
        if (text) {
            processUserInput(text);
            elements.textInput.value = '';
        }
    });
    
    // Enter key
    elements.textInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            elements.sendButton.click();
        }
    });
    
    // Theme toggle
    elements.themeToggle?.addEventListener('click', toggleTheme);
    
    // Settings toggle
    elements.settingsToggle?.addEventListener('click', () => {
        elements.settingsPanel.classList.toggle('hidden');
    });
    
    // Close settings when clicking outside
    document.addEventListener('click', (e) => {
        if (!elements.settingsPanel?.contains(e.target) && 
            !elements.settingsToggle?.contains(e.target)) {
            elements.settingsPanel?.classList.add('hidden');
        }
    });
    
    // Voice selection
    elements.voiceSelect?.addEventListener('change', (e) => {
        const index = parseInt(e.target.value);
        state.selectedVoice = state.englishVoices[index];
        localStorage.setItem('voiceIndex', index);
    });

    // Provider selection
    elements.providerSelect?.addEventListener('change', (e) => {
        state.provider = e.target.value;
        localStorage.setItem('llmProvider', state.provider);
    });
    
    // TTS toggle
    elements.ttsToggle?.addEventListener('change', (e) => {
        state.ttsEnabled = e.target.checked;
        localStorage.setItem('ttsEnabled', state.ttsEnabled);
    });

    // Speech controls
    elements.rateSlider?.addEventListener('input', (e) => {
        state.speechRate = parseFloat(e.target.value);
        localStorage.setItem('speechRate', state.speechRate);
    });
    elements.pitchSlider?.addEventListener('input', (e) => {
        state.speechPitch = parseFloat(e.target.value);
        localStorage.setItem('speechPitch', state.speechPitch);
    });

    // API key input
    elements.apiKeyInput?.addEventListener('change', (e) => {
        state.apiKey = e.target.value.trim();
        if (state.apiKey) {
            localStorage.setItem('geminiApiKey', state.apiKey);
        } else {
            localStorage.removeItem('geminiApiKey');
        }
    });

    // Audio2Face controls
    elements.a2fLoad?.addEventListener('click', loadA2FRun);
    elements.a2fPlay?.addEventListener('click', playA2F);
    elements.a2fStop?.addEventListener('click', stopA2F);
    
    // Quick prompts
    elements.quickPrompts?.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.textContent.replace(/[^\w\s]/g, '').trim();
            processUserInput(text);
        });
    });
}

/**
 * Load saved settings
 */
function loadSavedSettings() {
    const savedApiKey = localStorage.getItem('geminiApiKey');
    if (savedApiKey && elements.apiKeyInput) {
        state.apiKey = savedApiKey;
        elements.apiKeyInput.value = savedApiKey;
    }

    const savedRate = localStorage.getItem('speechRate');
    if (savedRate && elements.rateSlider) {
        state.speechRate = parseFloat(savedRate);
        elements.rateSlider.value = state.speechRate;
    }
    const savedPitch = localStorage.getItem('speechPitch');
    if (savedPitch && elements.pitchSlider) {
        state.speechPitch = parseFloat(savedPitch);
        elements.pitchSlider.value = state.speechPitch;
    }

    const savedProvider = localStorage.getItem('llmProvider');
    if (savedProvider && elements.providerSelect) {
        state.provider = savedProvider;
        elements.providerSelect.value = savedProvider;
    }
    
    const savedTts = localStorage.getItem('ttsEnabled');
    if (savedTts !== null && elements.ttsToggle) {
        state.ttsEnabled = savedTts === 'true';
        elements.ttsToggle.checked = state.ttsEnabled;
    }
    
    setTimeout(() => {
        const savedVoiceIndex = localStorage.getItem('voiceIndex');
        if (savedVoiceIndex !== null && state.englishVoices && elements.voiceSelect) {
            const index = parseInt(savedVoiceIndex);
            if (index < state.englishVoices.length) {
                state.selectedVoice = state.englishVoices[index];
                elements.voiceSelect.value = index;
            }
        }
    }, 500);
}

/**
 * Initialize avatar
 */
function initAvatar() {
    if (window.avatarModule?.init) {
        window.avatarModule.init('avatar-container');
    }
}

// =============================================================================
// Audio2Face Integration
// =============================================================================

function setA2FStatus(text) {
    if (elements.a2fStatus) {
        elements.a2fStatus.textContent = text;
    }
}

function setA2FControls(loaded, playing) {
    if (elements.a2fPlay) {
        elements.a2fPlay.disabled = !loaded || playing;
    }
    if (elements.a2fStop) {
        elements.a2fStop.disabled = !playing;
    }
}

async function loadA2FRun() {
    try {
        setA2FStatus('Loading latest output...');
        const response = await fetch(CONFIG.A2F_ENDPOINT);
        if (!response.ok) {
            throw new Error('No Audio2Face output found');
        }
        const data = await response.json();
        state.a2f.runId = data.run_id || '';
        state.a2f.frames = Array.isArray(data.frames) ? data.frames : [];
        state.a2f.emotions = Array.isArray(data.emotions) ? data.emotions : [];
        state.a2f.audioUrl = data.audio_url || '';
        state.a2f.loaded = true;
        state.a2f.lastFrameIndex = 0;
        state.a2f.lastEmotionIndex = 0;
        if (state.a2f.audioUrl) {
            state.a2f.audio = new Audio(`${state.a2f.audioUrl}?v=${Date.now()}`);
            state.a2f.audio.addEventListener('ended', stopA2F);
        }
        setA2FStatus(`Loaded ${state.a2f.runId}`);
        setA2FControls(true, false);
    } catch (error) {
        console.error('A2F load error:', error);
        setA2FStatus('No output found. Run Audio2Face client first.');
        state.a2f.loaded = false;
        setA2FControls(false, false);
    }
}

function playA2F() {
    if (!state.a2f.loaded || !state.a2f.audio) {
        setA2FStatus('Load Audio2Face output first.');
        return;
    }
    state.a2f.playing = true;
    state.a2f.lastFrameIndex = 0;
    state.a2f.lastEmotionIndex = 0;
    elements.avatarRing?.classList.add('speaking');
    setA2FControls(true, true);
    state.a2f.audio.currentTime = 0;
    state.a2f.audio.play().catch((error) => {
        console.error('A2F audio play error:', error);
        setA2FStatus('Audio playback failed.');
        stopA2F();
    });
    requestAnimationFrame(stepA2FAnimation);
}

function stopA2F() {
    if (state.a2f.audio) {
        state.a2f.audio.pause();
        state.a2f.audio.currentTime = 0;
    }
    state.a2f.playing = false;
    elements.avatarRing?.classList.remove('speaking');
    if (window.avatarModule) {
        window.avatarModule.setMouthOpenness(0);
        window.avatarModule.setEmotion('neutral', 0);
    }
    setA2FControls(state.a2f.loaded, false);
}

function stepA2FAnimation() {
    if (!state.a2f.playing || !state.a2f.audio) return;
    const t = state.a2f.audio.currentTime;
    applyA2FMouth(t);
    applyA2FEmotion(t);
    requestAnimationFrame(stepA2FAnimation);
}

function applyA2FMouth(t) {
    const frames = state.a2f.frames;
    if (!frames.length) return;
    let idx = state.a2f.lastFrameIndex;
    while (idx + 1 < frames.length && frames[idx + 1].t <= t) {
        idx += 1;
    }
    state.a2f.lastFrameIndex = idx;
    const frame = frames[idx];
    if (window.avatarModule?.setMouthOpenness) {
        window.avatarModule.setMouthOpenness(frame.mouth ?? 0);
    }
}

function applyA2FEmotion(t) {
    const emotions = state.a2f.emotions;
    if (!emotions.length) return;
    let idx = state.a2f.lastEmotionIndex;
    while (idx + 1 < emotions.length && emotions[idx + 1].t <= t) {
        idx += 1;
    }
    state.a2f.lastEmotionIndex = idx;
    const emotion = emotions[idx];
    if (window.avatarModule?.setEmotion) {
        window.avatarModule.setEmotion(emotion.dominant || 'neutral', emotion.intensity || 0);
    }
}

// =============================================================================
// Core Functions
// =============================================================================

function toggleRecording() {
    if (state.isCooldown || state.isProcessing) return;
    
    if (state.isRecording) {
        state.recognition?.stop();
    } else {
        state.currentTranscript = '';
        elements.textInput.value = '';
        state.recognition?.start();
    }
}

async function processUserInput(text) {
    if (state.isProcessing || state.isCooldown || !text.trim()) return;
    
    state.isProcessing = true;
    setAIState('Processing...', 'processing');
    
    // Add user message to chat
    addMessage(text, 'user');
    
    // Store in history
    state.messageHistory.push({ role: 'user', content: text });
    
    // Try WebSocket first
    if (state.websocket?.readyState === WebSocket.OPEN) {
        // Add placeholder for AI response
        addMessage('', 'ai', true);
        
        state.websocket.send(JSON.stringify({
            text: text,
            api_key: state.apiKey,
            provider: state.provider
        }));
        return;
    }
    
    // Fallback to REST API
    try {
        const response = await fetch(CONFIG.DIALOGUE_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                api_key: state.apiKey,
                provider: state.provider
            })
        });
        
        if (!response.ok) {
            throw new Error(response.status === 429 ? 'Please wait before sending another message' : 'Server error');
        }
        
        const data = await response.json();
        
        // Add AI response
        addMessage(data.response, 'ai');
        
        // Store in history
        state.messageHistory.push({ role: 'assistant', content: data.response });
        
        // Speak response
        if (state.ttsEnabled) {
            speakText(data.response);
        }
        
        setAIState('Ready to help', 'ready');
        
    } catch (error) {
        console.error('Error:', error);
        addMessage("I'm having trouble connecting right now. Please try again in a moment.", 'ai');
        setAIState('Connection issue', 'error');
    } finally {
        state.isProcessing = false;
        startCooldown();
    }
}

/**
 * Add message to chat
 */
function addMessage(content, type, isStreaming = false) {
    if (isStreaming) {
        // Only one active streaming placeholder at a time
        finalizeStreamingMessage();
        state.streamingId += 1;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `flex gap-3 animate-fade-in ${type === 'user' ? 'flex-row-reverse' : ''}`;
    
    const avatar = type === 'user' 
        ? '<div class="w-8 h-8 rounded-full bg-gradient-to-br from-accent-400 to-accent-600 flex items-center justify-center flex-shrink-0"><span class="text-white text-sm">👤</span></div>'
        : '<div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center flex-shrink-0"><span class="text-white text-sm">🧠</span></div>';
    
    const bubbleClass = type === 'user'
        ? 'bg-primary-500 text-white rounded-2xl rounded-tr-none'
        : 'bg-gray-100 dark:bg-calm-700 text-gray-800 dark:text-gray-200 rounded-2xl rounded-tl-none';
    
    const messageContent = isStreaming 
        ? '<div class="typing-indicator flex gap-1"><span class="w-2 h-2 bg-gray-400 rounded-full"></span><span class="w-2 h-2 bg-gray-400 rounded-full"></span><span class="w-2 h-2 bg-gray-400 rounded-full"></span></div>'
        : `<p class="text-sm leading-relaxed">${escapeHtml(content)}</p>`;
    
    messageDiv.innerHTML = `
        ${avatar}
        <div class="${bubbleClass} px-4 py-3 max-w-[80%]" ${isStreaming ? `id="streaming-message-${state.streamingId}"` : ''}>
            ${messageContent}
        </div>
    `;
    
    elements.chatContainer.appendChild(messageDiv);
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

/**
 * Update the last AI message (for streaming)
 */
function updateLastAIMessage(content) {
    const streamingMessage = getActiveStreamingMessage();
    if (streamingMessage) {
        streamingMessage.innerHTML = `<p class="text-sm leading-relaxed">${escapeHtml(content)}</p>`;
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    }
}

function finalizeStreamingMessage() {
    const streamingMessage = getActiveStreamingMessage();
    if (streamingMessage) {
        streamingMessage.id = '';
        const indicator = streamingMessage.querySelector('.typing-indicator');
        if (indicator) indicator.remove();
        if (!streamingMessage.textContent.trim()) {
            streamingMessage.innerHTML = `<p class="text-sm leading-relaxed">${escapeHtml(state.currentResponse || '')}</p>`;
        }
    }
}

function getActiveStreamingMessage() {
    return document.getElementById(`streaming-message-${state.streamingId}`) || document.querySelector('[id^="streaming-message"]');
}

function ensureStreamingPlaceholder() {
    if (!getActiveStreamingMessage()) {
        addMessage('', 'ai', true);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Speak text using TTS
 */
function speakText(text) {
    if (!state.ttsEnabled) return;
    
    // Trigger avatar animation
    if (window.avatarModule) {
        window.avatarModule.simulateSpeaking(text);
        window.avatarModule.detectAndSetEmotion(text);
    }
    
    // Start speaking animation
    state.isSpeaking = true;
    elements.avatarRing?.classList.add('speaking');
    setAIState('Speaking...', 'speaking');
    showVoiceVisualization(true);
    
    speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (state.selectedVoice) {
        utterance.voice = state.selectedVoice;
    }
    
    utterance.rate = state.speechRate;
    utterance.pitch = state.speechPitch;
    
    utterance.onend = () => {
        state.isSpeaking = false;
        elements.avatarRing?.classList.remove('speaking');
        setAIState('Ready to help', 'ready');
        showVoiceVisualization(false);
        
        if (window.avatarModule) {
            window.avatarModule.setMouthOpenness(0);
        }
    };
    
    speechSynthesis.speak(utterance);
}

/**
 * Start cooldown
 */
function startCooldown() {
    state.isCooldown = true;
    elements.cooldownBar?.classList.remove('hidden');
    
    let elapsed = 0;
    const interval = 50;
    
    state.cooldownTimer = setInterval(() => {
        elapsed += interval;
        const progress = (elapsed / CONFIG.COOLDOWN_MS) * 100;
        
        if (elements.cooldownProgress) {
            elements.cooldownProgress.style.width = `${100 - progress}%`;
        }
        
        if (elapsed >= CONFIG.COOLDOWN_MS) {
            clearInterval(state.cooldownTimer);
            state.isCooldown = false;
            elements.cooldownBar?.classList.add('hidden');
        }
    }, interval);
}

// =============================================================================
// UI Updates
// =============================================================================

function updateMicButton(isRecording) {
    if (!elements.micButton) return;
    
    if (isRecording) {
        elements.micButton.classList.add('recording-active', 'bg-red-500');
        elements.micButton.classList.remove('bg-gradient-to-br', 'from-primary-500', 'to-primary-600');
        elements.micIcon?.classList.add('hidden');
        elements.stopIcon?.classList.remove('hidden');
    } else {
        elements.micButton.classList.remove('recording-active', 'bg-red-500');
        elements.micButton.classList.add('bg-gradient-to-br', 'from-primary-500', 'to-primary-600');
        elements.micIcon?.classList.remove('hidden');
        elements.stopIcon?.classList.add('hidden');
    }
}

function setAIState(text, state) {
    if (!elements.aiState) return;
    
    elements.aiState.textContent = text;
    
    const stateClasses = {
        ready: 'bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300',
        listening: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
        processing: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
        speaking: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300',
        error: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
    };
    
    elements.aiState.className = `px-2 py-0.5 rounded-full text-xs ${stateClasses[state] || stateClasses.ready}`;
}

function showVoiceVisualization(show) {
    if (!elements.voiceViz) return;
    
    if (show) {
        elements.voiceViz.classList.remove('hidden');
        animateVoiceBars();
    } else {
        elements.voiceViz.classList.add('hidden');
    }
}

function animateVoiceBars() {
    if (elements.voiceViz?.classList.contains('hidden')) return;
    
    const bars = elements.voiceViz.querySelectorAll('.voice-bar');
    bars.forEach(bar => {
        const height = Math.random() * 24 + 8;
        bar.style.height = `${height}px`;
    });
    
    if (state.isRecording || state.isSpeaking) {
        requestAnimationFrame(() => setTimeout(animateVoiceBars, 100));
    }
}

function updateConnectionStatus(connected) {
    if (!elements.statusDot || !elements.statusText) return;
    
    if (connected) {
        elements.statusDot.classList.remove('bg-red-400');
        elements.statusDot.classList.add('bg-green-400');
        elements.statusText.textContent = 'Connected';
    } else {
        elements.statusDot.classList.remove('bg-green-400');
        elements.statusDot.classList.add('bg-red-400');
        elements.statusText.textContent = 'Reconnecting...';
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcons(isDark);
    
    if (window.avatarModule?.setDarkMode) {
        window.avatarModule.setDarkMode(isDark);
    }
}

async function checkServerHealth() {
    try {
        const response = await fetch(CONFIG.HEALTH_ENDPOINT);
        if (response.ok) {
            console.log('✅ Server healthy');
            updateConnectionStatus(true);
        } else {
            throw new Error('Server unhealthy');
        }
    } catch (error) {
        console.warn('Server health check failed');
        updateConnectionStatus(false);
    }
}
