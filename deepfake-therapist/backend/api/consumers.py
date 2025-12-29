"""
WebSocket Consumers

Handles WebSocket connections for real-time token streaming.
"""

import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.conf import settings
import os
import uuid
from .utils import get_llm_streaming_response, normalize_provider
from .session_store import conversation_store

logger = logging.getLogger(__name__)


class StreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming LLM responses.
    
    Client connects to ws://localhost:8000/ws/stream/
    Sends: {"text": "user message", "api_key": "optional"}
    Receives: {"type": "token", "content": "..."} or {"type": "done"} or {"type": "error", "message": "..."}
    """
    
    async def connect(self):
        """Accept WebSocket connection."""
        await self.accept()
        logger.info("WebSocket connection established")
        
        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'message': 'Connected to AI Therapist stream'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket client.
        Expected format: {"text": "user message", "api_key": "optional"}
        """
        try:
            data = json.loads(text_data)
            user_text = data.get('text', '').strip()
            user_api_key = data.get('api_key', '')
            provider = data.get('provider', getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini'))
            session_id = data.get('session_id') or uuid.uuid4().hex
            
            if not user_text:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Text field is required'
                }))
                return
            
            # Stream response
            await self.stream_response(user_text, provider, user_api_key, session_id)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def stream_response(self, user_text: str, provider: str = '', user_api_key: str = '', session_id: str = ''):
        """
        Stream LLM response token by token.
        Falls back to template response if Gemini unavailable.
        """
        provider = normalize_provider(provider)
        # Get API key
        api_key = user_api_key or getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        
        try:
            await self.stream_llm_response(user_text, provider, api_key, session_id)
            return
        except Exception as e:
            logger.warning(f"Primary provider streaming failed, using fallback: {e}")
        
        # Fallback: stream template response
        await self.stream_fallback_response(user_text, session_id)
    
    async def stream_llm_response(self, user_text: str, provider: str, api_key: str, session_id: str):
        """Stream response from configured LLM provider."""
        try:
            # Signal start of streaming
            await self.send(text_data=json.dumps({
                'type': 'start',
                'source': provider
            }))

            # Run token generation in a worker thread and push chunks into an asyncio queue
            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()
            collected = []

            def produce():
                try:
                    for chunk in get_llm_streaming_response(user_text, provider, api_key):
                        asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            producer_task = loop.run_in_executor(None, produce)

            # Stream chunks as they arrive
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                collected.append(chunk)
                await self.send(text_data=json.dumps({
                    'type': 'token',
                    'content': chunk
                }))
                await asyncio.sleep(0.01)  # tiny delay for smoother UI

            # Ensure producer finished
            await asyncio.wrap_future(producer_task)

            await self.send(text_data=json.dumps({
                'type': 'done',
                'source': provider
            }))
            # Persist history
            full_response = ''.join(collected)
            if session_id:
                conversation_store.add(session_id, 'user', user_text)
                conversation_store.add(session_id, 'assistant', full_response)

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            raise
    
    async def stream_fallback_response(self, user_text: str, session_id: str):
        """Stream fallback template response."""
        from .utils import get_fallback_response
        
        response = await sync_to_async(get_fallback_response)(user_text)
        
        # Signal start
        await self.send(text_data=json.dumps({
            'type': 'start',
            'source': 'fallback'
        }))
        
        # Simulate token streaming for consistent UX
        words = response.split(' ')
        for i, word in enumerate(words):
            token = word + (' ' if i < len(words) - 1 else '')
            await self.send(text_data=json.dumps({
                'type': 'token',
                'content': token
            }))
            await asyncio.sleep(0.05)  # Simulate typing delay
        
        # Signal end
        await self.send(text_data=json.dumps({
            'type': 'done',
            'source': 'fallback'
        }))
        if session_id:
            conversation_store.add(session_id, 'user', user_text)
            conversation_store.add(session_id, 'assistant', response)
