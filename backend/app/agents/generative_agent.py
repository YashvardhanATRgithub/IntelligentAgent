"""
Generative Agent with LLM integration for ISRO simulation
Uses Ollama (local LLM) via PARL Engine
"""
from typing import List, Dict, Any, Optional
from .base import BaseAgent, Personality, Memory
from .history_loader import HistoryLoader, create_default_agent_definitions
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
    
    @classmethod
    def create_from_history(cls, agent_name: str, loader: Optional[HistoryLoader] = None) -> "GenerativeAgent":
        """
        Create an agent instance from historical data loaded via CSV.
        
        Args:
            agent_name: Name of the agent to create
            loader: Optional HistoryLoader instance (creates new if None)
            
        Returns:
            Initialized GenerativeAgent
        """
        if loader is None:
            loader = HistoryLoader()
            
        # Try to load definitions from CSV, or create defaults if missing
        try:
            definitions = loader.load_agent_definitions()
        except FileNotFoundError:
            definitions = create_default_agent_definitions()
            loader.save_agent_definitions(definitions)
            
        # Find specific agent definition
        definition = next((d for d in definitions if d.name == agent_name), None)
        
        if not definition:
            raise ValueError(f"Agent definition not found for: {agent_name}")
            
        # Create agent
        agent = cls(
            name=definition.name,
            role=definition.role,
            personality=Personality(
                openness=definition.openness,
                conscientiousness=definition.conscientiousness,
                extraversion=definition.extraversion,
                agreeableness=definition.agreeableness,
                neuroticism=definition.neuroticism
            ),
            backstory=definition.backstory,
            secret=definition.secret
        )
        
        # Load historical memories
        try:
            history = loader.load_agent_history()
            agent_events = history.get(agent_name, [])
            
            for event in agent_events:
                agent.add_memory(
                    content=event.memory_text,
                    memory_type=event.memory_type,
                    importance=float(event.importance)
                )
        except Exception as e:
            print(f"Could not load history for {agent_name}: {e}")
            
        return agent

    def _build_system_prompt(self) -> str:
        """Build the system prompt using Cognitive State Identity Summary"""
        # Use the Identity Stable Set (ISS) from Cognitive State
        identity_summary = self.cognitive_state.get_identity_summary()
        
        prompt = f"""You are {self.name}, a {self.role} at Aryabhata Station, ISRO's lunar base.

{identity_summary}

You should:
1. Respond as this character would, based on their personality
2. Consider your relationships with other crew members
3. Make decisions that align with your goals and motivations
4. React emotionally based on your personality traits

CURRENT STATE:
Time: {self.cognitive_state.current_time}
Location: {self.cognitive_state.world_location}
Status: {self.cognitive_state.act_description}
Mood: {self.cognitive_state.mood}

LOCATIONS: You are in a detailed environment. Locations have sub-areas (Format: "Building/Room").
Example: "Mission Control/Command Deck", "Crew Quarters/Gym", "Mess Hall/Kitchen".
Be specific when moving.
"""
        return prompt
    
    async def reason(self, observations: List[str], env_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        R - REASONING
        Use LLM to reflect on observations and decide next action
        """
        # Connect to PARL engine
        from ..parl.parl_engine import parl_engine
        
        # Build context
        context = {
            "current_situation": str(observations[-1]) if observations else "Normal operations",
            "agents_at_location": env_state.get("agents_at_location", []) if env_state else [],
            "scheduled_activity": self.cognitive_state.act_description, # Use current activity as guide
            "all_agent_names": [a["name"] for a in env_state.get("agents_at_location", [])] if env_state else []
        }
        
        try:
            decision = await parl_engine.reason(self.to_dict(), context)
            if decision:
                return decision
            else:
                return self._default_behavior()
        except Exception as e:
            print(f"LLM error for {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return self._default_behavior()
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into action dict"""
        import json
        import re
        
        try:
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


def create_all_agents() -> List[GenerativeAgent]:
    """Create all agents for the simulation using HistoryLoader"""
    loader = HistoryLoader()
    
    # Ensure definitions exist
    try:
        definitions = loader.load_agent_definitions()
    except:
        definitions = create_default_agent_definitions()
        loader.save_agent_definitions(definitions)
    
    all_agents = []
    
    # Map to ensure correct order/priority if needed, or just load all
    priority_names = [
        "Cdr. Vikram Sharma",
        "Dr. Ananya Iyer",
        "TARA",
        "Dr. Priya Nair",
        "Lt. Aditya Menon",
        "Dr. Arjun Reddy",
        "Kabir Ahmed",
        "Rohan Kapoor"
    ]
    
    for name in priority_names:
        try:
            agent = GenerativeAgent.create_from_history(name, loader)
            all_agents.append(agent)
        except ValueError:
            print(f"Skipping agent {name} - definition not found")
            
    # Respect configuration limits
    return all_agents[:settings.NUM_AGENTS]
