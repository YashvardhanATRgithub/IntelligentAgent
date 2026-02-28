"""
Base Agent class implementing PARL framework
PARL = Perception, Action, Reasoning, Learning
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Import the new CognitiveState module
from ..memory.scratch import CognitiveState, create_cognitive_state_for_agent


@dataclass
class Memory:
    """A single memory in the agent's memory stream"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 5.0  # 1-10 scale
    memory_type: str = "observation"  # observation, reflection, plan
    related_agents: List[str] = field(default_factory=list)
    location: str = ""
    
    def relevance_score(self, query: str, current_time: datetime) -> float:
        """Calculate relevance based on recency, importance, and query match"""
        # Recency decay (more recent = higher score)
        hours_ago = (current_time - self.timestamp).total_seconds() / 3600
        recency_score = 1.0 / (1.0 + hours_ago * 0.1)
        
        # Simple keyword matching for relevance
        query_words = set(query.lower().split())
        content_words = set(self.content.lower().split())
        relevance = len(query_words & content_words) / max(len(query_words), 1)
        
        # Combined score
        return (recency_score + self.importance / 10.0 + relevance) / 3.0


@dataclass
class Personality:
    """Agent personality traits (Big Five)"""
    openness: float = 0.5        # 0-1: curious vs cautious
    conscientiousness: float = 0.5  # 0-1: organized vs flexible
    extraversion: float = 0.5    # 0-1: social vs reserved
    agreeableness: float = 0.5   # 0-1: cooperative vs competitive
    neuroticism: float = 0.5     # 0-1: sensitive vs resilient


class BaseAgent(ABC):
    """
    Base class for all agents implementing PARL framework
    
    PARL Components:
    - Perception: Observe environment and other agents
    - Action: Execute behaviors in the world
    - Reasoning: Reflect on memories and plan actions
    - Learning: Update memory importance and learn patterns
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        personality: Personality,
        backstory: str = "",
        secret: str = ""
    ):
        self.id = f"{name}_{str(uuid.uuid4())[:8]}" # Name + Short UUID
        self.name = name
        self.role = role
        self.personality = personality
        self.backstory = backstory
        self.secret = secret  # Hidden motivation
        
        # Initialize Cognitive State (Working Memory)
        self.cognitive_state = create_cognitive_state_for_agent(
            name=name,
            role=role,
            backstory=backstory,
            personality_traits=f"O={personality.openness:.1f}, C={personality.conscientiousness:.1f}, E={personality.extraversion:.1f}, A={personality.agreeableness:.1f}, N={personality.neuroticism:.1f}"
        )
        
        # Memory stream (Long-term memory)
        self.memory_stream: List[Memory] = []
        
        # Relationships with other agents (name -> strength 0-100)
        self.relationships: Dict[str, float] = {}
        
        # LLM interface (set by subclass)
        self.llm = None
    
    # ==================== PERCEPTION ====================
    
    def perceive(self, environment: Dict[str, Any]) -> List[str]:
        """
        P - PERCEPTION
        Observe the environment and create observations
        """
        observations = []
        current_location = self.cognitive_state.world_location
        # Use the agent's already-synced current_time (set by sim loop) for observations
        # Do NOT override current_time here — it's synced by _simulation_loop using
        # the canonical WorldState.get_current_datetime() to avoid time mismatches.
        current_time = self.cognitive_state.current_time or environment.get("time", "unknown")
        
        # See agents in same location
        agents_here = environment.get("agents_at_location", [])
        for agent in agents_here:
            if agent["name"] != self.name:
                observations.append(
                    f"Saw {agent['name']} ({agent['role']}) at {current_location}"
                )
        
        # Observe events
        events = environment.get("events", [])
        for event in events:
            observations.append(f"Noticed: {event}")
        
        # Check time
        observations.append(f"Current time: {current_time}")
        
        # Store observations as memories if significant
        for obs in observations:
            self.add_memory(obs, memory_type="observation", importance=3.0)
        
        return observations
    
    # ==================== ACTION ====================
    
    def act(self, action: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        A - ACTION
        Execute an action in the environment and update cognitive state
        """
        result = {"success": False, "message": ""}
        
        if action == "move":
            # Update cognitive state location
            self.cognitive_state.world_location = target
            self.cognitive_state.start_action(
                address=target,
                duration=10,
                description=f"Moving to {target}",
                emoji="🚶"
            )
            result = {"success": True, "message": f"Moved to {target}"}
            
        elif action == "talk":
            self.cognitive_state.start_action(
                address=self.cognitive_state.world_location,
                duration=5,
                description=f"Talking to {target}",
                emoji="💬"
            )
            self.cognitive_state.chatting_with = target
            result = {"success": True, "message": f"Talking to {target}"}
            
        elif action == "work":
            self.cognitive_state.start_action(
                address=self.cognitive_state.world_location,
                duration=60,
                description=f"Working on {target}",
                emoji="💼"
            )
            result = {"success": True, "message": f"Working on {target}"}
            
        elif action == "rest":
            self.cognitive_state.start_action(
                address=self.cognitive_state.world_location,
                duration=30,
                description="Resting",
                emoji="😴"
            )
            result = {"success": True, "message": "Resting"}
        
        return result
    
    # ==================== REASONING ====================
    
    @abstractmethod
    async def reason(self, observations: List[str]) -> str:
        """
        R - REASONING
        Reflect on observations and memories, decide next action
        Must be implemented by subclass with LLM integration
        """
        pass
    
    def retrieve_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """Retrieve most relevant memories for a query"""
        current_time = datetime.now()
        
        # Score all memories
        scored = [
            (mem, mem.relevance_score(query, current_time))
            for mem in self.memory_stream
        ]
        
        # Sort by score and return top memories
        scored.sort(key=lambda x: x[1], reverse=True)
        return [mem for mem, score in scored[:limit]]
    
    # ==================== LEARNING ====================
    
    def learn(self, outcome: Dict[str, Any]) -> None:
        """
        L - LEARNING
        Update memories and learn from outcomes
        """
        # Store outcome as memory
        if outcome.get("success"):
            importance = 5.0
        else:
            importance = 7.0  # Failures are more memorable
        
        self.add_memory(
            content=f"Action result: {outcome.get('message', 'unknown')}",
            memory_type="observation",
            importance=importance
        )
        
        # Update relationship if interaction with another agent
        if "agent" in outcome:
            agent_name = outcome["agent"]
            delta = 5.0 if outcome.get("positive", True) else -5.0
            current = self.relationships.get(agent_name, 50.0)
            self.relationships[agent_name] = max(0, min(100, current + delta))
            
        # Check for reflection trigger
        self.cognitive_state.trigger_reflection_check(importance)
    
    def add_memory(
        self,
        content: str,
        memory_type: str = "observation",
        importance: float = 5.0,
        related_agents: List[str] = None
    ) -> Memory:
        """Add a new memory to the stream AND the global memory store"""
        memory = Memory(
            content=content,
            timestamp=datetime.now(),
            importance=importance,
            memory_type=memory_type,
            related_agents=related_agents or [],
            location=self.cognitive_state.world_location
        )
        self.memory_stream.append(memory)
        
        # Also persist to global memory store so the API can retrieve it
        try:
            from ..memory import memory_store
            memory_store.add_memory(
                agent_name=self.name,
                content=content,
                memory_type=memory_type,
                importance=importance,
                related_agents=related_agents or [],
                location=self.cognitive_state.world_location
            )
        except Exception as e:
            pass  # Don't crash if memory store unavailable
        
        return memory
    
    # ==================== PARL LOOP ====================
    
    async def step(self, environment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute one PARL cycle
        """
        # P - Perceive
        observations = self.perceive(environment)
        
        # R - Reason (includes planning)
        decision = await self.reason(observations)
        
        # A - Act
        action_result = self.act(decision["action"], decision.get("target"))
        
        # L - Learn
        self.learn(action_result)
        
        return {
            "agent": self.name,
            "observations": observations,
            "decision": decision,
            "result": action_result
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent state for API/frontend"""
        # Mix base identity with dynamic cognitive state
        state_dict = self.cognitive_state.to_dict()
        
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "location": self.cognitive_state.world_location,
            "activity": self.cognitive_state.act_description,
            "emoji": self.cognitive_state.act_emoji,
            "mood": "neutral",  # Could be added to cognitive state
            "personality": {
                "openness": self.personality.openness,
                "conscientiousness": self.personality.conscientiousness,
                "extraversion": self.personality.extraversion,
                "agreeableness": self.personality.agreeableness,
                "neuroticism": self.personality.neuroticism
            },
            # Return full cognitive state for debug/display
            "cognitive_state": state_dict
        }
