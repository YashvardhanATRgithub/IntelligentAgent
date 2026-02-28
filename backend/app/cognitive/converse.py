"""
Conversation Choreographer - Turn-based dialogue for Generative Agents

This module implements realistic multi-turn conversations between agents
at Aryabhata Station. It handles:

1. Turn-taking: Natural back-and-forth dialogue
2. Topic management: Staying on topic while allowing natural drift
3. Memory integration: Using past memories to inform dialogue
4. Conversation endings: Detecting natural conclusion points
5. Summary generation: Creating memorable summaries for reflection
"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import re


@dataclass
class ConversationContext:
    """Context for an ongoing conversation"""
    initiator: str              # Who started the conversation
    target: str                 # Who they're talking to
    topic: str                  # What they're talking about
    location: str               # Where the conversation is happening
    start_time: datetime        # When it started
    
    # Conversation history: [(speaker, utterance), ...]
    turns: List[Tuple[str, str]] = field(default_factory=list)
    
    # Emotional state tracking
    initiator_emotion: str = "neutral"
    target_emotion: str = "neutral"
    
    # Topic tracking
    topics_discussed: List[str] = field(default_factory=list)
    
    # Conversation metadata
    max_turns: int = 8
    minimum_turns: int = 2
    should_end: bool = False
    end_reason: str = ""


@dataclass 
class ConversationResult:
    """Result of a completed conversation"""
    participants: List[str]
    turns: List[Tuple[str, str]]
    duration_minutes: int
    topics: List[str]
    summary: str
    memories_for_initiator: List[str]
    memories_for_target: List[str]


class ConversationChoreographer:
    """
    Manages multi-turn conversations between agents.
    
    Uses LLM to generate natural dialogue with proper turn-taking,
    topic management, and conversation flow.
    """
    
    def __init__(self, llm_client: Any = None):
        """
        Initialize the choreographer.
        
        Args:
            llm_client: LLM client for generating dialogue
        """
        self.llm_client = llm_client
        self.active_conversations: Dict[str, ConversationContext] = {}
        
        # Conversation templates for when LLM is unavailable
        self.greeting_templates = [
            "Hello {target}, how are you today?",
            "Hey {target}, got a minute to talk?",
            "{target}! Good to see you.",
            "Hi {target}, I was hoping to run into you.",
        ]
        
        self.response_templates = [
            "I'm doing well, thanks for asking.",
            "Things are going okay. What's on your mind?",
            "I've been busy but managing. You?",
            "Could be better, honestly. But I'm hanging in there.",
        ]
        
        self.ending_templates = [
            "Well, I should get back to work. Good talking to you.",
            "Thanks for the chat. See you around.",
            "I need to head out, but let's talk more later.",
            "Duty calls. Take care!",
        ]
    
    async def should_initiate_conversation(
        self,
        initiator_name: str,
        initiator_role: str,
        target_name: str,
        target_role: str,
        context: str,
        relevant_memories: List[str] = None
    ) -> Tuple[bool, str]:
        """
        Decide if an agent should initiate a conversation.
        
        Args:
            initiator_name: Name of potential initiator
            initiator_role: Their role
            target_name: Name of potential conversation partner
            target_role: Their role
            context: Current situation/location
            relevant_memories: Recent memories about the target
            
        Returns:
            (should_talk, topic) - Whether to talk and suggested topic
        """
        if not self.llm_client:
            # Default behavior: 50% chance if in same location
            import random
            should_talk = random.random() > 0.5
            topic = "general check-in"
            return (should_talk, topic)
        
        memories_context = ""
        if relevant_memories:
            memories_context = "\n".join(f"- {m}" for m in relevant_memories[-5:])
        
        prompt = f"""You are {initiator_name}, a {initiator_role} at Aryabhata Station on the Moon.

You just noticed {target_name} ({target_role}) nearby.

Current situation: {context}

Your recent memories about {target_name}:
{memories_context if memories_context else "- No recent memories about this person"}

Should you initiate a conversation? Consider:
1. Do you have something to discuss with them?
2. Is now an appropriate time?
3. What topic would be natural to bring up?

Respond in JSON format:
{{"should_talk": true/false, "topic": "topic if should_talk is true", "reason": "brief internal thought"}}"""

        try:
            response = await self.llm_client.generate_content_async(prompt)
            
            # Parse response
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return (data.get("should_talk", False), data.get("topic", "general conversation"))
        except Exception as e:
            print(f"Error in conversation decision: {e}")
        
        return (False, "")
    
    async def start_conversation(
        self,
        initiator_name: str,
        initiator_role: str,
        initiator_personality: str,
        target_name: str,
        target_role: str,
        target_personality: str,
        topic: str,
        location: str,
        initiator_memories: List[str] = None,
        target_memories: List[str] = None
    ) -> ConversationContext:
        """
        Start a new conversation between two agents.
        
        Args:
            initiator_name: Who's starting the conversation
            initiator_role: Their role
            initiator_personality: Their personality traits
            target_name: Who they're talking to
            target_role: Their role
            target_personality: Their personality traits
            topic: What to talk about
            location: Where the conversation is happening
            initiator_memories: Initiator's relevant memories
            target_memories: Target's relevant memories
            
        Returns:
            ConversationContext with first utterance
        """
        context = ConversationContext(
            initiator=initiator_name,
            target=target_name,
            topic=topic,
            location=location,
            start_time=datetime.now(),
            topics_discussed=[topic]
        )
        
        # Generate first utterance
        first_utterance = await self.generate_utterance(
            speaker_name=initiator_name,
            speaker_role=initiator_role,
            speaker_personality=initiator_personality,
            listener_name=target_name,
            listener_role=target_role,
            topic=topic,
            conversation_history=[],
            relevant_memories=initiator_memories or [],
            is_opening=True
        )
        
        context.turns.append((initiator_name, first_utterance))
        
        # Store active conversation
        conv_key = self._get_conversation_key(initiator_name, target_name)
        self.active_conversations[conv_key] = context
        
        return context
    
    async def generate_utterance(
        self,
        speaker_name: str,
        speaker_role: str,
        speaker_personality: str,
        listener_name: str,
        listener_role: str,
        topic: str,
        conversation_history: List[Tuple[str, str]],
        relevant_memories: List[str],
        is_opening: bool = False,
        is_closing: bool = False
    ) -> str:
        """
        Generate a single utterance in a conversation.
        
        Args:
            speaker_name: Who is speaking
            speaker_role: Their role
            speaker_personality: Their personality traits
            listener_name: Who they're speaking to
            listener_role: Their role
            topic: Current topic
            conversation_history: Previous turns
            relevant_memories: Speaker's relevant memories
            is_opening: Is this the first utterance?
            is_closing: Should this end the conversation?
            
        Returns:
            The generated utterance
        """
        if not self.llm_client:
            # Use templates if no LLM
            import random
            if is_opening:
                template = random.choice(self.greeting_templates)
                return template.format(target=listener_name.split()[0])
            elif is_closing:
                return random.choice(self.ending_templates)
            else:
                return random.choice(self.response_templates)
        
        # Build conversation history string
        history_str = ""
        if conversation_history:
            history_lines = []
            for speaker, text in conversation_history[-6:]:  # Last 6 turns
                history_lines.append(f"{speaker}: {text}")
            history_str = "\n".join(history_lines)
        
        # Build memories string
        memories_str = ""
        if relevant_memories:
            memories_str = "\n".join(f"- {m}" for m in relevant_memories[-5:])
        
        context_note = ""
        if is_opening:
            context_note = "This is the START of the conversation. Greet them and bring up the topic naturally."
        elif is_closing:
            context_note = "This is the END of the conversation. Wrap up naturally and say goodbye."
        else:
            context_note = "Continue the conversation naturally. Stay on topic but allow for natural flow."
        
        prompt = f"""You are {speaker_name}, a {speaker_role} at ISRO's Aryabhata Station on the Moon.

Personality: {speaker_personality}

You're talking to {listener_name} ({listener_role}) about: {topic}

Your relevant memories:
{memories_str if memories_str else "- No specific memories about this topic"}

Conversation so far:
{history_str if history_str else "(Just starting)"}

{context_note}

Generate your next line of dialogue. Be natural and in-character. Keep it 1-3 sentences.
Respond with ONLY the dialogue, no quotes or speaker label."""

        try:
            response = await self.llm_client.generate_content_async(prompt)
            utterance = response.text.strip()
            
            # Clean up response
            utterance = utterance.strip('"\'')
            if utterance.startswith(f"{speaker_name}:"):
                utterance = utterance[len(f"{speaker_name}:"):].strip()
            
            return utterance
        except Exception as e:
            print(f"Error generating utterance: {e}")
            import random
            return random.choice(self.response_templates)
    
    async def should_end_conversation(
        self,
        context: ConversationContext,
        last_utterance: str
    ) -> Tuple[bool, str]:
        """
        Determine if conversation should end naturally.
        
        Args:
            context: Current conversation context
            last_utterance: The most recent thing said
            
        Returns:
            (should_end, reason)
        """
        # Minimum turns not reached
        if len(context.turns) < context.minimum_turns:
            return (False, "")
        
        # Maximum turns reached
        if len(context.turns) >= context.max_turns:
            return (True, "max_turns_reached")
        
        # Check for natural ending phrases
        ending_phrases = [
            "see you", "talk later", "got to go", "i should go",
            "need to get back", "duty calls", "back to work",
            "goodbye", "bye", "take care", "catch you later"
        ]
        
        lower_utterance = last_utterance.lower()
        for phrase in ending_phrases:
            if phrase in lower_utterance:
                return (True, "natural_ending")
        
        if not self.llm_client:
            # Without LLM, use probability based on turn count
            import random
            end_prob = (len(context.turns) - context.minimum_turns) / context.max_turns
            if random.random() < end_prob:
                return (True, "random_ending")
            return (False, "")
        
        # Use LLM to determine if conversation has naturally concluded
        history_str = "\n".join(f"{s}: {t}" for s, t in context.turns[-4:])
        
        prompt = f"""Analyze this conversation snippet:

{history_str}

Has this conversation reached a natural ending point? Consider:
- Have they covered the topic sufficiently?
- Is there an awkward pause or conclusion?
- Did someone signal they need to leave?

Respond with JSON: {{"should_end": true/false, "reason": "brief reason"}}"""

        try:
            response = await self.llm_client.generate_content_async(prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return (data.get("should_end", False), data.get("reason", ""))
        except Exception as e:
            print(f"Error checking conversation end: {e}")
        
        return (False, "")
    
    async def continue_conversation(
        self,
        initiator_name: str,
        initiator_role: str,
        initiator_personality: str,
        target_name: str,
        target_role: str,
        target_personality: str,
        initiator_memories: List[str] = None,
        target_memories: List[str] = None
    ) -> Optional[ConversationContext]:
        """
        Continue an active conversation with the next turn.
        
        Returns the updated context, or None if conversation ended.
        """
        conv_key = self._get_conversation_key(initiator_name, target_name)
        context = self.active_conversations.get(conv_key)
        
        if not context:
            return None
        
        # Determine whose turn it is
        last_speaker = context.turns[-1][0] if context.turns else context.initiator
        if last_speaker == context.initiator:
            current_speaker = context.target
            current_role = target_role
            current_personality = target_personality
            current_memories = target_memories or []
            listener_name = context.initiator
            listener_role = initiator_role
        else:
            current_speaker = context.initiator
            current_role = initiator_role
            current_personality = initiator_personality
            current_memories = initiator_memories or []
            listener_name = context.target
            listener_role = target_role
        
        # Check if we should end
        if context.turns:
            should_end, reason = await self.should_end_conversation(
                context, context.turns[-1][1]
            )
            if should_end:
                context.should_end = True
                context.end_reason = reason
                return context
        
        # Generate next utterance
        is_closing = len(context.turns) >= context.max_turns - 1
        
        utterance = await self.generate_utterance(
            speaker_name=current_speaker,
            speaker_role=current_role,
            speaker_personality=current_personality,
            listener_name=listener_name,
            listener_role=listener_role,
            topic=context.topic,
            conversation_history=context.turns,
            relevant_memories=current_memories,
            is_closing=is_closing
        )
        
        context.turns.append((current_speaker, utterance))
        
        # Check again after adding turn
        if is_closing or len(context.turns) >= context.max_turns:
            context.should_end = True
            context.end_reason = "max_turns_reached"
        
        return context
    
    async def run_full_conversation(
        self,
        initiator_name: str,
        initiator_role: str,
        initiator_personality: str,
        target_name: str,
        target_role: str,
        target_personality: str,
        topic: str,
        location: str,
        initiator_memories: List[str] = None,
        target_memories: List[str] = None,
        max_turns: int = 8
    ) -> ConversationResult:
        """
        Run a complete conversation between two agents.
        
        This executes the full back-and-forth dialogue and returns
        the complete result with summaries.
        
        Args:
            All agent info and context
            max_turns: Maximum number of turns
            
        Returns:
            ConversationResult with full dialogue and summaries
        """
        # Start conversation
        context = await self.start_conversation(
            initiator_name=initiator_name,
            initiator_role=initiator_role,
            initiator_personality=initiator_personality,
            target_name=target_name,
            target_role=target_role,
            target_personality=target_personality,
            topic=topic,
            location=location,
            initiator_memories=initiator_memories,
            target_memories=target_memories
        )
        context.max_turns = max_turns
        
        # Continue until natural end or max turns
        while not context.should_end:
            context = await self.continue_conversation(
                initiator_name=initiator_name,
                initiator_role=initiator_role,
                initiator_personality=initiator_personality,
                target_name=target_name,
                target_role=target_role,
                target_personality=target_personality,
                initiator_memories=initiator_memories,
                target_memories=target_memories
            )
            if context is None:
                break
        
        # Generate summary
        summary = await self.summarize_conversation(context)
        
        # Generate memories for each participant
        initiator_memory = await self.generate_conversation_memory(
            context, initiator_name
        )
        target_memory = await self.generate_conversation_memory(
            context, target_name
        )
        
        # Calculate duration (rough estimate based on turns)
        duration = len(context.turns) * 2  # ~2 min per exchange
        
        # Clean up
        conv_key = self._get_conversation_key(initiator_name, target_name)
        if conv_key in self.active_conversations:
            del self.active_conversations[conv_key]
        
        return ConversationResult(
            participants=[initiator_name, target_name],
            turns=context.turns,
            duration_minutes=duration,
            topics=context.topics_discussed,
            summary=summary,
            memories_for_initiator=[initiator_memory],
            memories_for_target=[target_memory]
        )
    
    async def summarize_conversation(
        self,
        context: ConversationContext
    ) -> str:
        """
        Create a summary of the conversation for logging/display.
        """
        if not context.turns:
            return "No conversation occurred."
        
        if not self.llm_client:
            # Basic summary without LLM
            num_turns = len(context.turns)
            return (f"{context.initiator} and {context.target} had a "
                    f"{num_turns}-turn conversation about {context.topic} "
                    f"at {context.location}.")
        
        history_str = "\n".join(f"{s}: {t}" for s, t in context.turns)
        
        prompt = f"""Summarize this conversation in 1-2 sentences:

{history_str}

Focus on what was discussed and any important outcomes or agreements."""

        try:
            response = await self.llm_client.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error summarizing conversation: {e}")
            return (f"{context.initiator} and {context.target} discussed "
                    f"{context.topic} at {context.location}.")
    
    async def generate_conversation_memory(
        self,
        context: ConversationContext,
        agent_name: str
    ) -> str:
        """
        Generate a memory about the conversation from a specific agent's POV.
        """
        if not context.turns:
            return ""
        
        other_agent = (context.target if agent_name == context.initiator 
                       else context.initiator)
        
        if not self.llm_client:
            return f"I had a conversation with {other_agent} about {context.topic}."
        
        # Get this agent's utterances
        my_utterances = [t for s, t in context.turns if s == agent_name]
        their_utterances = [t for s, t in context.turns if s == other_agent]
        
        prompt = f"""You are {agent_name}. You just finished talking to {other_agent} about {context.topic}.

What they said (highlights):
{chr(10).join('- ' + u for u in their_utterances[-3:])}

What you said (highlights):
{chr(10).join('- ' + u for u in my_utterances[-3:])}

Write a brief (1-2 sentence) memory of this conversation from your perspective.
Start with "I talked with..." or "I had a conversation with..."."""

        try:
            response = await self.llm_client.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating conversation memory: {e}")
            return f"I talked with {other_agent} about {context.topic}."
    
    def _get_conversation_key(self, agent1: str, agent2: str) -> str:
        """Create consistent conversation key for two agents"""
        return "|".join(sorted([agent1, agent2]))
    
    def get_active_conversation(
        self,
        agent_name: str
    ) -> Optional[ConversationContext]:
        """
        Get any active conversation involving an agent.
        """
        for key, context in self.active_conversations.items():
            if agent_name in key:
                return context
        return None
    
    def end_all_conversations(self):
        """Force end all active conversations"""
        self.active_conversations.clear()


# Helper function to create choreographer with project's LLM client
def create_choreographer_with_llm() -> ConversationChoreographer:
    """
    Create a ConversationChoreographer with the project's LLM client.
    
    This integrates with the existing PARL engine.
    """
    try:
        from ..parl.parl_engine import parl_engine
        
        # Create a wrapper that matches what Choreographer expects
        class EngineWrapper:
            def __init__(self, engine):
                self.engine = engine
                
            async def generate_content_async(self, prompt: str):
                # Return an object with .text attribute
                response_text = await self.engine._call_llm(prompt)
                if not response_text:
                    response_text = ""
                
                class Response:
                    def __init__(self, text):
                        self.text = text
                
                return Response(response_text)

        return ConversationChoreographer(EngineWrapper(parl_engine))
    except Exception as e:
        print(f"Could not load LLM client: {e}")
        return ConversationChoreographer()
