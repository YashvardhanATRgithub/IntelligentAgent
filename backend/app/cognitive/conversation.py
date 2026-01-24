"""
Stanford-Level Conversation Module
Multi-turn dialogue system with context and memory integration.

Inspired by Stanford's generative_agents/converse.py but adapted for our architecture.
Features:
- Multi-turn conversation tracking
- Memory-informed dialogue
- Relationship-aware responses
- Conversation summarization
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import httpx
import re

from ..config import settings
from ..memory import memory_store


@dataclass
class ConversationTurn:
    """A single turn in a conversation"""
    speaker: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ActiveConversation:
    """An ongoing conversation between agents"""
    participants: List[str]
    turns: List[ConversationTurn] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    location: str = ""
    topic: str = ""
    
    def add_turn(self, speaker: str, content: str):
        self.turns.append(ConversationTurn(speaker=speaker, content=content))
    
    def get_history_text(self, max_turns: int = 5) -> str:
        """Get formatted conversation history"""
        recent = self.turns[-max_turns:]
        return "\n".join([f"{t.speaker}: {t.content}" for t in recent])
    
    def is_stale(self, max_age_seconds: int = 120) -> bool:
        """Check if conversation has gone stale"""
        if not self.turns:
            return True
        last_turn = self.turns[-1].timestamp
        return (datetime.now() - last_turn).total_seconds() > max_age_seconds


class ConversationManager:
    """
    Stanford-level conversation system with multi-turn context.
    
    Key features:
    - Tracks active conversations between agent pairs
    - Generates contextual responses using conversation history
    - Integrates memories and relationship scores
    - Summarizes conversations for memory storage
    """
    
    def __init__(self):
        self.active_conversations: Dict[str, ActiveConversation] = {}
        self.llm_provider = settings.LLM_PROVIDER.lower()
    
    def _get_conversation_key(self, agent1: str, agent2: str) -> str:
        """Generate consistent key for agent pair"""
        return "-".join(sorted([agent1, agent2]))
    
    def get_or_create_conversation(
        self, 
        speaker: str, 
        listener: str, 
        location: str = ""
    ) -> ActiveConversation:
        """Get existing conversation or create new one"""
        key = self._get_conversation_key(speaker, listener)
        
        if key in self.active_conversations:
            convo = self.active_conversations[key]
            if not convo.is_stale():
                return convo
        
        # Create new conversation
        convo = ActiveConversation(
            participants=[speaker, listener],
            location=location
        )
        self.active_conversations[key] = convo
        return convo
    
    async def generate_utterance(
        self,
        speaker: Dict[str, Any],
        listener: Dict[str, Any],
        initial_message: str = None,
        context: str = ""
    ) -> str:
        """
        Stanford-level: Generate contextual conversation response.
        
        Uses conversation history, memories, and relationship to craft response.
        """
        speaker_name = speaker['name']
        listener_name = listener['name']
        
        # Get or create conversation
        convo = self.get_or_create_conversation(
            speaker_name, 
            listener_name,
            speaker.get('location', '')
        )
        
        # Get relevant memories about the listener
        memories = memory_store.retrieve_memories(
            agent_name=speaker_name,
            query=f"conversations with {listener_name}",
            limit=5
        )
        memories_text = "\n".join([f"- {m.get('content', '')}" for m in memories]) if memories else "No specific memories"
        
        # Build prompt
        history_text = convo.get_history_text()
        
        if initial_message:
            # This is a new conversation
            prompt = f"""You are {speaker_name}, a {speaker.get('role', 'crew member')} at a lunar station.
You want to talk to {listener_name}, a {listener.get('role', 'crew member')}.

Your memories about them:
{memories_text}

{f"Context: {context}" if context else ""}

Start a natural conversation. What do you say?
Keep it brief (1-2 sentences). Be natural and in-character."""

        else:
            # Continuing conversation
            prompt = f"""You are {speaker_name}, a {speaker.get('role', 'crew member')} at a lunar station.
You're talking to {listener_name}, a {listener.get('role', 'crew member')}.

Conversation so far:
{history_text}

Your memories about them:
{memories_text}

What do you say next?
Keep it brief (1-2 sentences). Be natural and in-character. Respond to what they said."""

        response = await self._call_llm(prompt)
        
        if response:
            # Clean up response
            response = response.strip()
            # Remove any "Speaker:" prefix if present
            response = re.sub(r'^[A-Za-z\s]+:\s*', '', response)
            # Take first sentence or two
            sentences = response.split('.')[:2]
            response = '. '.join(sentences).strip()
            if response and not response.endswith(('.', '!', '?')):
                response += '.'
        else:
            # Fallback responses
            fallbacks = [
                f"Hello {listener_name}, how are you doing?",
                f"Hey {listener_name}, got a moment?",
                f"Good to see you, {listener_name}.",
                f"Hi there! How's your shift going?"
            ]
            import random
            response = random.choice(fallbacks)
        
        # Add turn to conversation
        convo.add_turn(speaker_name, response)
        
        return response
    
    async def generate_reply(
        self,
        speaker: Dict[str, Any],
        listener: Dict[str, Any],
        incoming_message: str
    ) -> str:
        """Generate a reply to an incoming message"""
        speaker_name = speaker['name']
        listener_name = listener['name']
        
        # Get conversation
        convo = self.get_or_create_conversation(speaker_name, listener_name)
        
        # Add the incoming message to history
        convo.add_turn(listener_name, incoming_message)
        
        # Generate response
        return await self.generate_utterance(speaker, listener)
    
    async def summarize_conversation(self, agent1: str, agent2: str) -> Optional[str]:
        """
        Stanford-level: Summarize conversation for memory storage.
        
        Called when conversation ends to create a memory of what was discussed.
        """
        key = self._get_conversation_key(agent1, agent2)
        convo = self.active_conversations.get(key)
        
        if not convo or not convo.turns:
            return None
        
        history_text = "\n".join([f"{t.speaker}: {t.content}" for t in convo.turns])
        
        prompt = f"""Summarize this conversation in 1-2 sentences:

{history_text}

Summary (from a third-person perspective):"""

        summary = await self._call_llm(prompt)
        
        if summary:
            summary = summary.strip()
            # Store as memory for both agents
            memory_store.add_memory(
                agent_name=agent1,
                content=f"Conversation with {agent2}: {summary}",
                memory_type="conversation",
                importance=6.0,
                related_agents=[agent2]
            )
            memory_store.add_memory(
                agent_name=agent2,
                content=f"Conversation with {agent1}: {summary}",
                memory_type="conversation",
                importance=6.0,
                related_agents=[agent1]
            )
        
        # Clear the conversation
        del self.active_conversations[key]
        
        return summary
    
    def end_conversation(self, agent1: str, agent2: str):
        """End a conversation (without summarization)"""
        key = self._get_conversation_key(agent1, agent2)
        if key in self.active_conversations:
            del self.active_conversations[key]
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Route to appropriate LLM provider"""
        if self.llm_provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            return await self._call_groq(prompt)
    
    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call local Ollama"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{settings.OLLAMA_HOST}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.8, "num_predict": 100}
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
            except Exception as e:
                print(f"Ollama conversation error: {e}")
        return None
    
    async def _call_groq(self, prompt: str) -> Optional[str]:
        """Call Groq API for conversation"""
        if not settings.GROQ_API_KEY:
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.GROQ_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.8,
                        "max_tokens": 100
                    }
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"Groq conversation error: {e}")
        return None


# Global conversation manager instance
conversation_manager = ConversationManager()
