/**
 * AI Therapist Avatar - Image-Based Avatar with Animations
 * 
 * This is a simpler, more reliable approach using a high-quality image
 * with CSS animations for a professional look.
 * 
 * Features:
 * - Professional therapist image
 * - Subtle breathing/pulse animation
 * - Glow effect when speaking
 * - Expression overlays for emotions
 */

let avatarContainer = null;
let avatarImage = null;
let mouthOverlay = null;
let isInitialized = false;
let isSpeaking = false;
let mouthOpen = 0;

/**
 * Initialize the avatar
 */
function initAvatar(containerId = 'avatar-container') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn('Avatar container not found');
        return false;
    }

    avatarContainer = container;
    
    // Clear container
    container.innerHTML = '';
    
    // Create avatar wrapper
    const wrapper = document.createElement('div');
    wrapper.id = 'avatar-wrapper';
    wrapper.style.cssText = `
        width: 100%;
        height: 100%;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 50%;
    `;
    
    // Create the image element
    avatarImage = document.createElement('img');
    avatarImage.src = '/static/src/therapist.png';
    avatarImage.alt = 'AI Therapist';
    avatarImage.style.cssText = `
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 50%;
        transition: all 0.3s ease;
    `;

    // Mouth overlay for simple lip-sync
    mouthOverlay = document.createElement('div');
    mouthOverlay.id = 'mouth-overlay';
    mouthOverlay.style.cssText = `
        position: absolute;
        left: 50%;
        bottom: 24%;
        width: 34%;
        height: 8%;
        background: rgba(0, 0, 0, 0.55);
        border-radius: 999px;
        transform: translateX(-50%) scaleY(0.2);
        transform-origin: center;
        opacity: 0;
        transition: transform 0.06s linear, opacity 0.12s ease;
        mix-blend-mode: multiply;
        pointer-events: none;
    `;
    
    // Add animation styles
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        @keyframes avatar-breathe {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        
        @keyframes avatar-speaking {
            0%, 100% { 
                box-shadow: 0 0 20px rgba(34, 197, 94, 0.3);
                transform: scale(1);
            }
            50% { 
                box-shadow: 0 0 40px rgba(34, 197, 94, 0.6);
                transform: scale(1.01);
            }
        }
        
        @keyframes avatar-pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.6; }
        }
        
        .avatar-idle {
            animation: avatar-breathe 4s ease-in-out infinite;
        }
        
        .avatar-speaking {
            animation: avatar-speaking 0.8s ease-in-out infinite;
        }
        
        .speaking-indicator {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 4px;
        }
        
        .speaking-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: avatar-pulse 0.5s ease-in-out infinite;
        }
        
        .speaking-dot:nth-child(2) { animation-delay: 0.15s; }
        .speaking-dot:nth-child(3) { animation-delay: 0.3s; }
    `;
    document.head.appendChild(styleSheet);
    
    // Add idle animation
    avatarImage.classList.add('avatar-idle');
    
    wrapper.appendChild(avatarImage);
    wrapper.appendChild(mouthOverlay);
    
    // Add speaking indicator (hidden by default)
    const speakingIndicator = document.createElement('div');
    speakingIndicator.id = 'speaking-indicator';
    speakingIndicator.className = 'speaking-indicator';
    speakingIndicator.style.display = 'none';
    speakingIndicator.innerHTML = `
        <div class="speaking-dot"></div>
        <div class="speaking-dot"></div>
        <div class="speaking-dot"></div>
    `;
    wrapper.appendChild(speakingIndicator);
    
    container.appendChild(wrapper);
    
    isInitialized = true;
    console.log('Image-based avatar initialized');
    return true;
}

/**
 * Set mouth openness (for animation sync)
 * With image avatar, this controls the speaking animation intensity
 */
function setMouthOpenness(value) {
    if (!isInitialized || !avatarImage) return;
    const clamped = Math.max(0, Math.min(1, value));
    mouthOpen = clamped;

    if (clamped > 0.08 && !isSpeaking) {
        startSpeakingAnimation();
    } else if (clamped < 0.05 && isSpeaking) {
        stopSpeakingAnimation();
    }

    if (mouthOverlay) {
        const scaleY = 0.2 + clamped * 2.0;
        mouthOverlay.style.transform = `translateX(-50%) scaleY(${scaleY.toFixed(2)})`;
        mouthOverlay.style.opacity = clamped > 0.02 ? '0.9' : '0';
    }
}

/**
 * Start speaking animation
 */
function startSpeakingAnimation() {
    if (!avatarImage) return;
    
    isSpeaking = true;
    avatarImage.classList.remove('avatar-idle');
    avatarImage.classList.add('avatar-speaking');
    
    const indicator = document.getElementById('speaking-indicator');
    if (indicator) {
        indicator.style.display = 'flex';
    }
}

/**
 * Stop speaking animation
 */
function stopSpeakingAnimation() {
    if (!avatarImage) return;
    
    isSpeaking = false;
    avatarImage.classList.remove('avatar-speaking');
    avatarImage.classList.add('avatar-idle');
    
    const indicator = document.getElementById('speaking-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Simulate speaking
 */
function simulateSpeaking(text) {
    if (!isInitialized) return;
    
    startSpeakingAnimation();
    
    // Stop after estimated speech duration
    const duration = text.length * 70;
    const jitter = setInterval(() => {
        if (!isSpeaking) {
            clearInterval(jitter);
            return;
        }
        const value = Math.min(1, Math.max(0, Math.random() * 0.6));
        setMouthOpenness(value);
    }, 90);
    setTimeout(() => {
        clearInterval(jitter);
        setMouthOpenness(0);
        stopSpeakingAnimation();
    }, duration);
}

/**
 * Set emotion (for image avatar, we use filter effects)
 */
function setEmotion(emotion, intensity = 0.5) {
    if (!avatarImage) return;
    
    switch (emotion) {
        case 'happy':
            avatarImage.style.filter = `brightness(${1 + intensity * 0.1})`;
            break;
        case 'concerned':
            avatarImage.style.filter = `brightness(${1 - intensity * 0.05})`;
            break;
        case 'thoughtful':
            avatarImage.style.filter = `brightness(1) saturate(${1 - intensity * 0.1})`;
            break;
        default:
            avatarImage.style.filter = 'none';
    }
}

/**
 * Detect and set emotion from text
 */
function detectAndSetEmotion(text) {
    const lowerText = text.toLowerCase();
    
    const happyWords = ['glad', 'happy', 'wonderful', 'great', 'excellent', 'proud', 'good'];
    const concernedWords = ['sorry', 'understand', 'difficult', 'hard', 'tough', 'pain', 'struggle'];
    const thoughtfulWords = ['think', 'consider', 'perhaps', 'maybe', 'interesting', 'reflect'];
    
    if (happyWords.some(word => lowerText.includes(word))) {
        setEmotion('happy', 0.6);
    } else if (concernedWords.some(word => lowerText.includes(word))) {
        setEmotion('concerned', 0.5);
    } else if (thoughtfulWords.some(word => lowerText.includes(word))) {
        setEmotion('thoughtful', 0.5);
    } else {
        setEmotion('neutral', 0);
    }
    
    // Reset after delay
    setTimeout(() => setEmotion('neutral', 0), 5000);
}

/**
 * Update for dark mode
 */
function setDarkMode(isDark) {
    if (avatarContainer) {
        avatarContainer.style.boxShadow = isDark 
            ? '0 4px 20px rgba(0, 0, 0, 0.5)' 
            : '0 4px 20px rgba(0, 0, 0, 0.15)';
    }
}

// Export
window.avatarModule = {
    init: initAvatar,
    setMouthOpenness,
    setEmotion,
    simulateSpeaking,
    stopSpeaking: stopSpeakingAnimation,
    detectAndSetEmotion,
    setDarkMode,
};
