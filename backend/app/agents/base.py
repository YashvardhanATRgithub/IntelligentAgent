"""
Base Agent class implementing PARL framework
PARL = Perception, Action, Reasoning, Learning
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


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
class AgentState:
    """Current state of an agent"""
    location: str = "Crew Quarters"
    activity: str = "idle"
    energy: float = 100.0  # 0-100
    mood: str = "neutral"  # happy, neutral, anxious, sad
    current_goal: Optional[str] = None


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
        self.id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.personality = personality
        self.backstory = backstory
        self.secret = secret  # Hidden motivation
        
        # State
        self.state = AgentState()
        
        # Memory stream
        self.memory_stream: List[Memory] = []
        
        # Relationships with other agents (name -> strength 0-100)
        self.relationships: Dict[str, float] = {}
        
        # Current plan
        self.current_plan: List[str] = []
        
        # LLM interface (set by subclass)
        self.llm = None
    
    # ==================== PERCEPTION ====================
    
    def perceive(self, environment: Dict[str, Any]) -> List[str]:
        """
        P - PERCEPTION
        Observe the environment and create observations
        """
        observations = []
        
        # See agents in same location
        agents_here = environment.get("agents_at_location", [])
        for agent in agents_here:
            if agent["name"] != self.name:
                observations.append(
                    f"Saw {agent['name']} ({agent['role']}) at {self.state.location}"
                )
        
        # Observe events
        events = environment.get("events", [])
        for event in events:
            observations.append(f"Noticed: {event}")
        
        # Check time
        current_time = environment.get("time", "unknown")
        observations.append(f"Current time: {current_time}")
        
        # Store observations as memories
        for obs in observations:
            self.add_memory(obs, memory_type="observation", importance=3.0)
        
        return observations
    
    # ==================== ACTION ====================
    
    def act(self, action: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        A - ACTION
        Execute an action in the environment
        """
        result = {"success": False, "message": ""}
        
        if action == "move":
            self.state.location = target
            self.state.activity = "moving"
            result = {"success": True, "message": f"Moved to {target}"}
            
        elif action == "talk":
            self.state.activity = f"talking to {target}"
            result = {"success": True, "message": f"Talking to {target}"}
            
        elif action == "work":
            self.state.activity = f"working on {target}"
            self.state.energy -= 10
            result = {"success": True, "message": f"Working on {target}"}
            
        elif action == "rest":
            self.state.activity = "resting"
            self.state.energy = min(100, self.state.energy + 20)
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
    
    def add_memory(
        self,
        content: str,
        memory_type: str = "observation",
        importance: float = 5.0,
        related_agents: List[str] = None
    ) -> Memory:
        """Add a new memory to the stream"""
        memory = Memory(
            content=content,
            timestamp=datetime.now(),
            importance=importance,
            memory_type=memory_type,
            related_agents=related_agents or [],
            location=self.state.location
        )
        self.memory_stream.append(memory)
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
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "location": self.state.location,
            "activity": self.state.activity,
            "energy": self.state.energy,
            "mood": self.state.mood,
            "personality": {
                "openness": self.personality.openness,
                "conscientiousness": self.personality.conscientiousness,
                "extraversion": self.personality.extraversion,
                "agreeableness": self.personality.agreeableness,
                "neuroticism": self.personality.neuroticism
            }
        }
