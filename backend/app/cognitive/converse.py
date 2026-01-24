"""
Conversation Module - Stanford-level multi-agent dialogue generation

Based on Stanford's converse.py (~11KB) from generative_agents.

Key features:
1. Multi-turn dialogue between agents
2. Conversation context tracking
3. Dialogue history per agent pair
4. LLM-based contextual responses
5. Conversation initiation based on relationships and situations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import re


class ConversationType(Enum):
    """Types of conversations"""
    GREETING = "greeting"           # Initial hello
    SMALL_TALK = "small_talk"       # Casual chat
    WORK_RELATED = "work_related"   # Task/job discussion
    EMOTIONAL = "emotional"         # Personal feelings
    INFORMATION = "information"     # Sharing/asking info
    URGENT = "urgent"               # Emergency/important
    FAREWELL = "farewell"           # Ending conversation


@dataclass
class DialogueTurn:
    """A single turn in a conversation"""
    speaker: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    emotion: str = "neutral"        # happy, sad, worried, excited, etc.
    is_question: bool = False
    mentioned_agents: List[str] = field(default_factory=list)


@dataclass
class Conversation:
    """A conversation between two or more agents"""
    id: str
    participants: List[str]
    location: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    turns: List[DialogueTurn] = field(default_factory=list)
    conversation_type: ConversationType = ConversationType.SMALL_TALK
    topic: str = ""
    is_active: bool = True
    
    def add_turn(self, speaker: str, content: str, emotion: str = "neutral"):
        """Add a dialogue turn"""
        is_question = content.strip().endswith("?")
        
        # Extract mentioned agents
        mentioned = []
        for p in self.participants:
            if p != speaker and p.lower() in content.lower():
                mentioned.append(p)
        
        turn = DialogueTurn(
            speaker=speaker,
            content=content,
            emotion=emotion,
            is_question=is_question,
            mentioned_agents=mentioned
        )
        self.turns.append(turn)
        return turn
    
    def end(self):
        """End the conversation"""
        self.is_active = False
        self.end_time = datetime.now()
    
    def get_summary(self) -> str:
        """Get conversation summary for memory"""
        if not self.turns:
            return f"Brief interaction between {' and '.join(self.participants)}"
        
        first_turn = self.turns[0]
        last_turn = self.turns[-1]
        
        return f"{first_turn.speaker} and {', '.join([p for p in self.participants if p != first_turn.speaker])} talked about {self.topic or 'various things'}. {len(self.turns)} exchanges."
    
    def to_prompt_context(self) -> str:
        """Format conversation for LLM prompt"""
        lines = [f"[Conversation at {self.location}]"]
        for turn in self.turns[-5:]:  # Last 5 turns for context
            lines.append(f"{turn.speaker}: {turn.content}")
        return "\n".join(lines)


class ConversationEngine:
    """
    Stanford-level conversation system.
    
    Manages multi-agent dialogues with:
    - Contextual response generation
    - Relationship-aware dialogue
    - Conversation memory
    - Topic tracking
    """
    
    # Conversation starters based on relationship
    GREETING_TEMPLATES = {
        "close": [
            "Hey {name}! How are you doing?",
            "{name}! Great to see you.",
            "Hi {name}, glad I ran into you."
        ],
        "neutral": [
            "Hello {name}.",
            "Hi {name}, how's it going?",
            "Good to see you, {name}."
        ],
        "distant": [
            "Hello, {name}.",
            "{name}.",
            "Good day, {name}."
        ]
    }
    
    # Topic starters based on role
    TOPIC_STARTERS = {
        "Mission Commander": ["mission status", "crew safety", "Earth communications"],
        "Botanist/Life Support": ["plant growth", "oxygen levels", "crop experiments"],
        "AI Assistant": ["system diagnostics", "data analysis", "efficiency metrics"],
        "Crew Welfare Officer": ["crew morale", "mental health", "team dynamics"],
        "Systems Engineer": ["equipment status", "maintenance", "power systems"],
        "Flight Surgeon": ["health checkups", "medical supplies", "crew fitness"],
        "Geologist/Mining Lead": ["mining progress", "sample analysis", "geological findings"],
        "Communications Officer": ["Earth messages", "signal quality", "family updates"]
    }
    
    def __init__(self):
        # Active conversations
        self.active_conversations: Dict[str, Conversation] = {}
        
        # Conversation history (last N per agent pair)
        self.conversation_history: Dict[str, List[Conversation]] = {}
        
        # Last conversation time between pairs
        self.last_interaction: Dict[str, datetime] = {}
    
    def _get_pair_key(self, agent_a: str, agent_b: str) -> str:
        """Get consistent key for agent pair"""
        return "_".join(sorted([agent_a, agent_b]))
    
    def should_start_conversation(
        self,
        agent_a: str,
        agent_b: str,
        relationship_strength: float,
        agent_a_extraversion: float,
        same_location: bool
    ) -> Tuple[bool, str]:
        """
        Determine if agent_a should start a conversation with agent_b.
        
        Returns:
            (should_start, reason)
        """
        if not same_location:
            return False, "not same location"
        
        pair_key = self._get_pair_key(agent_a, agent_b)
        
        # Check if already in conversation
        if pair_key in self.active_conversations:
            return False, "already in conversation"
        
        # Check cooldown - don't chat too frequently
        if pair_key in self.last_interaction:
            time_since = (datetime.now() - self.last_interaction[pair_key]).total_seconds()
            if time_since < 300:  # 5 minute cooldown (in sim time)
                return False, "talked recently"
        
        # Probability based on personality and relationship
        import random
        base_prob = 0.3
        
        # Extraverts more likely to initiate
        prob = base_prob + (agent_a_extraversion * 0.3)
        
        # Stronger relationships more likely
        prob += (relationship_strength / 100) * 0.2
        
        if random.random() < prob:
            return True, "natural conversation"
        
        return False, "not in mood"
    
    def start_conversation(
        self,
        initiator: str,
        target: str,
        location: str,
        relationship_strength: float,
        topic: str = None
    ) -> Conversation:
        """Start a new conversation between two agents"""
        pair_key = self._get_pair_key(initiator, target)
        conv_id = f"{pair_key}_{datetime.now().timestamp()}"
        
        # Determine relationship tier
        if relationship_strength >= 70:
            tier = "close"
        elif relationship_strength >= 40:
            tier = "neutral"
        else:
            tier = "distant"
        
        # Create conversation
        conversation = Conversation(
            id=conv_id,
            participants=[initiator, target],
            location=location,
            topic=topic or "general",
            conversation_type=ConversationType.GREETING
        )
        
        # Generate opening line
        import random
        greeting = random.choice(self.GREETING_TEMPLATES[tier])
        opening = greeting.format(name=target.split()[0])  # First name
        
        conversation.add_turn(initiator, opening)
        
        self.active_conversations[pair_key] = conversation
        self.last_interaction[pair_key] = datetime.now()
        
        return conversation
    
    async def generate_response(
        self,
        conversation: Conversation,
        responder: str,
        responder_role: str,
        responder_personality: Dict[str, float],
        responder_mood: str,
        llm_client: Any = None
    ) -> str:
        """Generate contextual response using LLM"""
        if not llm_client:
            return self._generate_fallback_response(conversation, responder)
        
        # Build prompt
        context = conversation.to_prompt_context()
        last_speaker = conversation.turns[-1].speaker if conversation.turns else "Unknown"
        last_content = conversation.turns[-1].content if conversation.turns else ""
        
        prompt = f"""You are {responder}, a {responder_role} at ISRO's Aryabhata Station on the Moon.

Your personality:
- Extraversion: {responder_personality.get('extraversion', 0.5):.1f}
- Agreeableness: {responder_personality.get('agreeableness', 0.5):.1f}
- Current mood: {responder_mood}

{context}

{last_speaker} just said: "{last_content}"

Generate a natural, in-character response. Keep it brief (1-2 sentences).
Consider your personality and mood. If appropriate, ask a follow-up question.

Respond with ONLY the dialogue, no quotes or attribution."""

        try:
            response = await llm_client.generate_content_async(prompt)
            text = response.text.strip()
            # Clean up response
            text = text.replace(f"{responder}:", "").strip()
            text = text.strip('"').strip("'")
            return text
        except Exception as e:
            print(f"Conversation LLM error: {e}")
            return self._generate_fallback_response(conversation, responder)
    
    def _generate_fallback_response(self, conversation: Conversation, responder: str) -> str:
        """Generate simple response without LLM"""
        import random
        
        if not conversation.turns:
            return "Hello there."
        
        last_turn = conversation.turns[-1]
        
        # If greeting
        if any(word in last_turn.content.lower() for word in ["hello", "hi", "hey", "good"]):
            responses = [
                "Hello! How are you?",
                "Hi! Good to see you.",
                "Hey, doing well thanks. You?",
                "Greetings! How's everything?"
            ]
            return random.choice(responses)
        
        # If question
        if last_turn.is_question:
            responses = [
                "I think it's going well.",
                "Yes, I believe so.",
                "Everything seems fine from my end.",
                "Let me think about that..."
            ]
            return random.choice(responses)
        
        # General responses
        responses = [
            "I see, that's interesting.",
            "Makes sense to me.",
            "I agree with that.",
            "That's good to know.",
            "Right, I understand."
        ]
        return random.choice(responses)
    
    def continue_conversation(
        self,
        agent_a: str,
        agent_b: str,
        speaker: str,
        content: str,
        emotion: str = "neutral"
    ) -> Optional[DialogueTurn]:
        """Add a turn to an existing conversation"""
        pair_key = self._get_pair_key(agent_a, agent_b)
        
        if pair_key not in self.active_conversations:
            return None
        
        conversation = self.active_conversations[pair_key]
        turn = conversation.add_turn(speaker, content, emotion)
        
        # End conversation after too many turns
        if len(conversation.turns) >= 6:
            self.end_conversation(agent_a, agent_b)
        
        return turn
    
    def end_conversation(self, agent_a: str, agent_b: str) -> Optional[Conversation]:
        """End an active conversation"""
        pair_key = self._get_pair_key(agent_a, agent_b)
        
        if pair_key not in self.active_conversations:
            return None
        
        conversation = self.active_conversations.pop(pair_key)
        conversation.end()
        
        # Store in history
        if pair_key not in self.conversation_history:
            self.conversation_history[pair_key] = []
        
        self.conversation_history[pair_key].append(conversation)
        
        # Keep only last 10 conversations per pair
        self.conversation_history[pair_key] = self.conversation_history[pair_key][-10:]
        
        return conversation
    
    def get_active_conversation(self, agent_a: str, agent_b: str) -> Optional[Conversation]:
        """Get active conversation between two agents"""
        pair_key = self._get_pair_key(agent_a, agent_b)
        return self.active_conversations.get(pair_key)
    
    def get_conversation_history(self, agent_a: str, agent_b: str) -> List[Conversation]:
        """Get conversation history between two agents"""
        pair_key = self._get_pair_key(agent_a, agent_b)
        return self.conversation_history.get(pair_key, [])
    
    def get_conversation_summary_for_memory(
        self,
        agent_a: str,
        agent_b: str
    ) -> Optional[str]:
        """Get summary of last conversation for memory storage"""
        history = self.get_conversation_history(agent_a, agent_b)
        if not history:
            return None
        
        last_conv = history[-1]
        return last_conv.get_summary()


# Global conversation engine instance
conversation_engine = ConversationEngine()
