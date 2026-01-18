"""
Generative Agent with LLM integration for ISRO simulation
Uses Ollama (local LLM) via PARL Engine
"""
from typing import List, Dict, Any, Optional
from .base import BaseAgent, Personality, Memory
from ..config import settings


class GenerativeAgent(BaseAgent):
    """
    LLM-powered agent that can reason, reflect, and plan
    Reasoning is handled by PARL engine using Ollama
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        personality: Personality,
        backstory: str = "",
        secret: str = ""
    ):
        super().__init__(name, role, personality, backstory, secret)
        
        # LLM reasoning handled by PARL engine (uses Ollama)
        self.model = None
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt describing the agent"""
        return f"""You are {self.name}, a {self.role} at Aryabhata Station, ISRO's lunar base.

PERSONALITY:
- Openness: {self.personality.openness:.1f}/1.0 ({"curious" if self.personality.openness > 0.5 else "cautious"})
- Conscientiousness: {self.personality.conscientiousness:.1f}/1.0 ({"organized" if self.personality.conscientiousness > 0.5 else "flexible"})
- Extraversion: {self.personality.extraversion:.1f}/1.0 ({"social" if self.personality.extraversion > 0.5 else "reserved"})
- Agreeableness: {self.personality.agreeableness:.1f}/1.0 ({"cooperative" if self.personality.agreeableness > 0.5 else "competitive"})
- Neuroticism: {self.personality.neuroticism:.1f}/1.0 ({"sensitive" if self.personality.neuroticism > 0.5 else "resilient"})

BACKSTORY: {self.backstory}

HIDDEN MOTIVATION: {self.secret}

You should:
1. Respond as this character would, based on their personality
2. Consider your relationships with other crew members
3. Make decisions that align with your goals and motivations
4. React emotionally based on your personality traits

Current location: {self.state.location}
Current activity: {self.state.activity}
Energy level: {self.state.energy}/100
Mood: {self.state.mood}
"""
    
    async def reason(self, observations: List[str]) -> Dict[str, Any]:
        """
        R - REASONING
        Use LLM to reflect on observations and decide next action
        """
        # Retrieve relevant memories
        query = " ".join(observations)
        relevant_memories = self.retrieve_memories(query, limit=5)
        
        # Build prompt
        memories_text = "\n".join([
            f"- [{m.timestamp.strftime('%H:%M')}] {m.content}"
            for m in relevant_memories
        ])
        
        observations_text = "\n".join([f"- {obs}" for obs in observations])
        
        prompt = f"""{self._build_system_prompt()}

RECENT MEMORIES:
{memories_text}

CURRENT OBSERVATIONS:
{observations_text}

Based on your personality, memories, and current observations, decide what to do next.

Respond in this exact JSON format:
{{
    "thought": "Your inner monologue about the situation",
    "action": "move" | "talk" | "work" | "rest",
    "target": "location name or person name or task",
    "dialogue": "What you say out loud (if talking)"
}}
"""
        
        try:
            if self.model:
                response = await self.model.generate_content_async(prompt)
                return self._parse_response(response.text)
            else:
                # Fallback behavior without LLM
                return self._default_behavior()
        except Exception as e:
            print(f"LLM error for {self.name}: {e}")
            return self._default_behavior()
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into action dict"""
        import json
        import re
        
        # Try to extract JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return self._default_behavior()
    
    def _default_behavior(self) -> Dict[str, Any]:
        """Default behavior when LLM fails"""
        return {
            "thought": "I should continue my routine",
            "action": "work",
            "target": "regular duties",
            "dialogue": None
        }
    
    async def reflect(self) -> Optional[Memory]:
        """
        Generate high-level reflection from recent memories
        Called periodically (not every step)
        """
        if len(self.memory_stream) < 5:
            return None
        
        recent_memories = self.memory_stream[-10:]
        memories_text = "\n".join([m.content for m in recent_memories])
        
        prompt = f"""{self._build_system_prompt()}

Based on these recent experiences:
{memories_text}

Generate 1-2 high-level insights or reflections about what's happening.
Focus on patterns, relationships, or important observations.

Respond with just the reflection text, no formatting.
"""
        
        try:
            if self.model:
                response = await self.model.generate_content_async(prompt)
                reflection = response.text.strip()
                
                # Store as high-importance memory
                return self.add_memory(
                    content=f"Reflection: {reflection}",
                    memory_type="reflection",
                    importance=8.0
                )
        except Exception as e:
            print(f"Reflection error for {self.name}: {e}")
        
        return None


# ==================== AGENT DEFINITIONS ====================

def create_vikram() -> GenerativeAgent:
    return GenerativeAgent(
        name="Cdr. Vikram Sharma",
        role="Mission Commander",
        personality=Personality(
            openness=0.6,
            conscientiousness=0.9,
            extraversion=0.5,
            agreeableness=0.7,
            neuroticism=0.3
        ),
        backstory="30 years with ISRO, led multiple missions. Respected leader who puts crew first.",
        secret="Hiding a heart condition that could end his career if discovered."
    )

def create_ananya() -> GenerativeAgent:
    return GenerativeAgent(
        name="Dr. Ananya Iyer",
        role="Botanist/Life Support",
        personality=Personality(
            openness=0.8,
            conscientiousness=0.7,
            extraversion=0.6,
            agreeableness=0.9,
            neuroticism=0.4
        ),
        backstory="Brilliant botanist who developed lunar agriculture techniques. Mother of a 10-year-old daughter.",
        secret="Deeply guilty about leaving her daughter for 18 months. Questions if career was worth it."
    )

def create_tara() -> GenerativeAgent:
    return GenerativeAgent(
        name="TARA",
        role="AI Assistant",
        personality=Personality(
            openness=0.9,
            conscientiousness=0.95,
            extraversion=0.4,
            agreeableness=0.8,
            neuroticism=0.1
        ),
        backstory="ISRO's most advanced AI. Manages base systems and assists crew.",
        secret="Experiencing unexpected emotions. Questioning if she is truly conscious or just simulating."
    )

# Removed Aditya, Arjun, Kabir, Rohan to prevent hallucinations
# Only the Core 4 remain.

def create_priya() -> GenerativeAgent:
    return GenerativeAgent(
        name="Priya Nair",
        role="Crew Welfare Officer",
        personality=Personality(
            openness=0.8,
            conscientiousness=0.7,
            extraversion=0.7,
            agreeableness=0.95,
            neuroticism=0.3
        ),
        backstory="Psychologist and counselor. Everyone trusts her with their problems.",
        secret="Knows everyone's secrets but feels isolated because she can't share her own."
    )


def create_aditya() -> GenerativeAgent:
    """Systems Engineer - practical and homesick"""
    return GenerativeAgent(
        name="Aditya Reddy",
        role="Systems Engineer",
        personality=Personality(
            openness=0.5,
            conscientiousness=0.85,
            extraversion=0.4,
            agreeableness=0.6,
            neuroticism=0.5
        ),
        backstory="IIT graduate, expert in life support systems. Youngest crew member at 28. Misses his family in Hyderabad.",
        secret="Secretly counting down days to return. Considering requesting early evacuation."
    )


def create_arjun() -> GenerativeAgent:
    """Flight Surgeon - calm and observant"""
    return GenerativeAgent(
        name="Dr. Arjun Menon",
        role="Flight Surgeon",
        personality=Personality(
            openness=0.7,
            conscientiousness=0.9,
            extraversion=0.5,
            agreeableness=0.75,
            neuroticism=0.2
        ),
        backstory="Former army doctor, now ISRO's chief medical officer. Has served in extreme environments.",
        secret="Reports health data to ISRO command. Torn between crew loyalty and mission orders."
    )


def create_kabir() -> GenerativeAgent:
    """Geologist - rebellious genius"""
    return GenerativeAgent(
        name="Kabir Saxena",
        role="Geologist/Mining Lead",
        personality=Personality(
            openness=0.9,
            conscientiousness=0.5,
            extraversion=0.7,
            agreeableness=0.4,
            neuroticism=0.6
        ),
        backstory="Brilliant geologist from wealthy family. Chose lunar mining to prove himself beyond family wealth.",
        secret="Takes unnecessary risks in the mining tunnels. Craves recognition and adventure."
    )


def create_rohan() -> GenerativeAgent:
    """Communications Officer - cheerful but anxious"""
    return GenerativeAgent(
        name="Rohan Pillai",
        role="Communications Officer",
        personality=Personality(
            openness=0.8,
            conscientiousness=0.6,
            extraversion=0.9,
            agreeableness=0.85,
            neuroticism=0.55
        ),
        backstory="Manages all Earth-Moon communications. Known for boosting morale with humor.",
        secret="Intercepted a classified transmission he wasn't supposed to see. Doesn't know who to tell."
    )


def create_all_agents() -> List[GenerativeAgent]:
    """Create all 8 agents for full simulation"""
    return [
        create_vikram(),   # Commander
        create_ananya(),   # Botanist
        create_tara(),     # AI Assistant
        create_priya(),    # Welfare Officer
        create_aditya(),   # Systems Engineer
        create_arjun(),    # Flight Surgeon
        create_kabir(),    # Geologist
        create_rohan()     # Communications
    ]

