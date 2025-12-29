# Viva Questions & Answers - MindfulAI Project

## Project Overview Questions

### Q1: What is the main objective of your project?

**Answer:** MindfulAI is an AI-powered mental wellness companion that provides accessible, always-available support through conversation. It uses Google's Gemini AI to generate empathetic, therapeutic responses, and features voice input/output for natural interaction.

### Q2: What problem does this project solve?

**Answer:** Mental health support is often inaccessible due to:

- High cost of therapy sessions
- Long waiting times for appointments
- Social stigma around seeking help
- Lack of 24/7 availability

MindfulAI provides an initial layer of support that's free, private, and always available.

### Q3: Who is the target audience?

**Answer:**

- People experiencing mild stress or anxiety
- Those who want a safe space to express feelings
- Users who prefer voice interaction over typing
- Anyone seeking initial mental wellness support before professional help

---

## Technical Architecture Questions

### Q4: Explain the system architecture.

**Answer:** The system uses a client-server architecture:

**Frontend (Client):**

- HTML/CSS/JavaScript
- Web Speech API for STT/TTS
- WebSocket client for real-time streaming
- Animated avatar for visual feedback

**Backend (Server):**

- Django with Django REST Framework
- Django Channels for WebSocket support
- Integration with Google Gemini AI
- Rate limiting and caching systems

**External Services:**

- Google Gemini AI (LLM for responses)

### Q5: Why did you choose Django for the backend?

**Answer:**

1. **Rapid Development** - Django's batteries-included approach speeds up development
2. **REST Framework** - Built-in support for building APIs
3. **Channels** - Native WebSocket support for real-time streaming
4. **Security** - Built-in CSRF, XSS protection
5. **Scalability** - Can easily scale with ASGI servers

### Q6: How does the WebSocket streaming work?

**Answer:**

1. Client opens WebSocket connection to `/ws/stream/`
2. Client sends user message as JSON
3. Server receives message via `StreamConsumer`
4. Server calls Gemini API with streaming enabled
5. As tokens arrive, server sends them to client via WebSocket
6. Client updates UI progressively
7. When complete, server sends "done" message

### Q7: What is the fallback mechanism?

**Answer:** If the Gemini API is unavailable (no key, rate limited, network error), the system uses a template-based empathetic responder. It analyzes the user's message for keywords (stress, anxiety, sad, etc.) and returns pre-written therapeutic responses. This ensures the user always gets a response.

---

## AI & NLP Questions

### Q8: How does the AI generate therapeutic responses?

**Answer:** We use Google's Gemini AI with a carefully crafted system prompt that instructs the model to:

- Act as an empathetic therapist
- Use active listening techniques
- Ask open-ended questions
- Provide coping strategies
- Never give medical advice
- Suggest professional help when appropriate

### Q9: Why Gemini instead of GPT/ChatGPT?

**Answer:**

1. **Free Tier** - Gemini offers 1 million tokens/day free
2. **Quality** - Competitive with GPT-4
3. **Speed** - Fast response times
4. **Streaming** - Native streaming support
5. **No credit card** - Easy to get started

### Q10: What is the system prompt? Why is it important?

**Answer:** The system prompt defines the AI's persona:

```
You are a compassionate AI therapist. Your role is to provide
emotional support, practice active listening, and suggest
helpful coping strategies. Be warm, non-judgmental, and
empathetic. Never diagnose or prescribe. If someone expresses
severe distress, encourage them to seek professional help.
```

It's crucial because:

- Sets boundaries for AI behavior
- Ensures consistent therapeutic tone
- Prevents harmful or inappropriate responses
- Maintains ethical guidelines

---

## Frontend Questions

### Q11: How does Speech Recognition work in browsers?

**Answer:** We use the Web Speech API:

1. `SpeechRecognition` object listens to microphone
2. Audio is sent to browser's cloud service (Google for Chrome)
3. Returns text transcription in real-time
4. We capture final transcript and send to backend

**Limitations:**

- Requires internet connection
- Works best in Chrome
- User must grant microphone permission

### Q12: How does Text-to-Speech work?

**Answer:** We use the `SpeechSynthesis` API:

1. Create `SpeechSynthesisUtterance` with text
2. Select preferred voice from available voices
3. Call `speechSynthesis.speak(utterance)`
4. Browser synthesizes and plays audio

We prioritize high-quality voices (Google, Microsoft) when available.

### Q13: Why Tailwind CSS instead of Bootstrap?

**Answer:**

1. **Customization** - Easy to create unique designs
2. **No Bloat** - Only use what you need
3. **Modern** - Perfect for glassmorphism effects
4. **Performance** - Smaller bundle size
5. **Developer Experience** - Faster styling with utility classes

---

## Security Questions

### Q14: How do you handle API keys securely?

**Answer:**

1. **Server-side storage** - Primary key in environment variables
2. **Never in code** - Keys not committed to version control
3. **User keys optional** - Users can provide their own keys
4. **Local storage only** - User keys stored in browser localStorage, never sent to our database
5. **HTTPS in production** - All traffic encrypted

### Q15: What security measures are implemented?

**Answer:**

1. **CORS Configuration** - Restricts cross-origin requests
2. **CSRF Protection** - Django's built-in protection
3. **Rate Limiting** - Prevents API abuse
4. **Input Validation** - All inputs validated before processing
5. **No Sensitive Logging** - API keys not logged
6. **XSS Prevention** - HTML escaped in chat messages

---

## Performance Questions

### Q16: How do you optimize response times?

**Answer:**

1. **Streaming** - Show partial responses immediately
2. **Caching** - Cache identical queries
3. **Async Operations** - Non-blocking I/O with ASGI
4. **CDN Assets** - Tailwind loaded from CDN
5. **Efficient Frontend** - Minimal JavaScript, no heavy frameworks

### Q17: What is the rate limiting strategy?

**Answer:**

- 10 requests per minute per IP address
- Sliding window algorithm
- Returns 429 status when exceeded
- 3-second cooldown between messages on frontend
- Protects both our server and Gemini API quota

---

## Ethics & Limitations

### Q18: What are the ethical considerations?

**Answer:**

1. **Not a replacement** - Clear disclaimer that it's not professional therapy
2. **Crisis handling** - Encourages professional help for severe cases
3. **No diagnosis** - AI doesn't diagnose conditions
4. **Privacy** - Conversations not stored permanently
5. **Transparency** - Clear AI labeling

### Q19: What are the limitations of this system?

**Answer:**

1. **Not professional help** - Cannot replace human therapists
2. **No memory** - Each conversation starts fresh
3. **Internet required** - Needs connection for AI and STT
4. **Browser support** - Speech API best in Chrome
5. **AI limitations** - May sometimes give generic responses

---

## Future Enhancements

### Q20: How would you improve this project?

**Answer:**

1. **Session Memory** - Remember conversation history
2. **User Accounts** - Track progress over time
3. **Mood Analytics** - Visualize emotional patterns
4. **Video Avatar** - D-ID or similar for realistic avatar
5. **Multi-language** - Support for Indian languages
6. **Mobile App** - Native iOS/Android apps
7. **Therapist Dashboard** - For professional oversight
8. **Integration** - Connect with mental health resources

---

## Demo Tips

### Starting the Demo

1. Have the server running before the viva
2. Clear the chat history for a fresh start
3. Test the microphone beforehand

### Key Points to Highlight

1. Show real-time streaming responses
2. Demonstrate voice input/output
3. Show the settings panel
4. Toggle dark mode
5. Show the API health endpoint
6. Explain the architecture diagram

### Handle Failures Gracefully

- If Gemini fails, show the fallback response
- If mic doesn't work, use text input
- If server slow, explain WebSocket vs REST fallback
