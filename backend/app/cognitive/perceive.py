"""
Perceive Module - Stanford-level observation processing

This module formalizes what agents "notice" in their environment.
Based on Stanford's perceive.py (~8KB) from generative_agents.

Key concepts:
1. Agents have limited attention - can only perceive 3-7 things per step
2. Observations are filtered by relevance to agent's goals/role
3. Spatial awareness - what's in their current location
4. Social awareness - other agents present and their activities
5. Event detection - important events get priority attention
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum


class ObservationType(Enum):
    """Types of observations an agent can make"""
    AGENT_PRESENCE = "agent_presence"       # Another agent entered/left
    AGENT_ACTIVITY = "agent_activity"       # What another agent is doing
    AGENT_DIALOGUE = "agent_dialogue"       # Something someone said
    LOCATION_STATE = "location_state"       # State of current location
    ENVIRONMENT = "environment"             # Environmental info (time, alerts)
    EVENT = "event"                         # Special events (emergencies, etc.)
    OBJECT = "object"                       # Objects/equipment in location


@dataclass
class Observation:
    """
    A single observation made by an agent.
    Includes attention score for prioritization.
    """
    content: str                            # Human-readable observation
    observation_type: ObservationType       # Category of observation
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Relevance scoring (Stanford-style)
    attention_score: float = 5.0            # 1-10 how much this grabs attention
    importance: float = 5.0                 # 1-10 long-term importance
    
    # Context
    location: str = ""                      # Where this was observed
    subject: Optional[str] = None           # Who/what this is about
    
    # For dialogue observations
    speaker: Optional[str] = None
    dialogue_content: Optional[str] = None
    
    def __repr__(self):
        return f"Observation({self.observation_type.value}: {self.content[:50]}...)"


@dataclass
class PerceivedEnvironment:
    """
    Complete perceptual state for an agent at a moment.
    Filtered and prioritized observations.
    """
    agent_name: str
    location: str
    simulation_time: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Categorized observations
    observations: List[Observation] = field(default_factory=list)
    
    # Quick access to key info
    present_agents: List[str] = field(default_factory=list)
    recent_dialogues: List[Dict] = field(default_factory=list)
    location_state: Dict[str, Any] = field(default_factory=dict)
    
    def get_top_observations(self, limit: int = 5) -> List[Observation]:
        """Return highest attention-score observations"""
        sorted_obs = sorted(
            self.observations, 
            key=lambda o: o.attention_score, 
            reverse=True
        )
        return sorted_obs[:limit]
    
    def to_prompt_text(self) -> str:
        """Convert to text for LLM prompting"""
        lines = [f"[{self.simulation_time}] At {self.location}:"]
        
        if self.present_agents:
            lines.append(f"Present: {', '.join(self.present_agents)}")
        
        for obs in self.get_top_observations(5):
            lines.append(f"- {obs.content}")
        
        return "\n".join(lines)


class PerceptionEngine:
    """
    Stanford-level perception system.
    
    Filters raw world state into what an agent actually "notices",
    based on:
    - Agent's current focus/goals
    - Agent's role and interests
    - Attention limits (bounded rationality)
    - Spatial proximity
    - Social relationships
    """
    
    # Attention constants (Stanford-style)
    MAX_ATTENTION_ITEMS = 7      # Cognitive limit on simultaneous attention
    MIN_ATTENTION_ITEMS = 3      # Always notice at least this many
    DIALOGUE_ATTENTION_BOOST = 3.0   # Boost for speech directed at agent
    EVENT_ATTENTION_BOOST = 4.0      # Boost for important events
    RELATIONSHIP_BOOST = 1.5         # Boost for known agents
    
    def __init__(self):
        # Role-based interest keywords
        self.role_interests = {
            "Mission Commander": ["safety", "mission", "crew", "emergency", "status", "report"],
            "Botanist": ["plants", "growth", "water", "oxygen", "agriculture", "harvest"],
            "AI Assistant": ["system", "data", "analysis", "efficiency", "monitoring"],
            "Crew Welfare Officer": ["morale", "stress", "mental", "team", "conflict", "support"],
            "Systems Engineer": ["power", "system", "repair", "maintenance", "malfunction"],
            "Flight Surgeon": ["health", "medical", "injury", "vital", "sick", "checkup"],
            "Geologist": ["rock", "sample", "mineral", "mining", "excavation", "discovery"],
            "Communications Officer": ["signal", "transmission", "Earth", "message", "communication"]
        }
    
    def perceive(
        self,
        agent_name: str,
        agent_role: str,
        current_location: str,
        simulation_time: str,
        world_state: Dict[str, Any],
        relationship_scores: Dict[str, float] = None
    ) -> PerceivedEnvironment:
        """
        Main perception function - filters world state into agent's perception.
        
        Args:
            agent_name: Name of the perceiving agent
            agent_role: Role of the agent (affects attention priorities)
            current_location: Agent's current location
            simulation_time: Current simulation time string
            world_state: Raw world state from environment
            relationship_scores: Dict of agent_name -> relationship score
        
        Returns:
            PerceivedEnvironment with filtered, prioritized observations
        """
        observations = []
        relationship_scores = relationship_scores or {}
        
        # 1. Perceive other agents at same location
        agents_at_location = world_state.get("agents_at_location", {}).get(current_location, [])
        present_agents = []
        
        for agent_data in agents_at_location:
            other_name = agent_data.get("name", "")
            if other_name == agent_name:
                continue  # Skip self
            
            present_agents.append(other_name)
            
            # Agent presence observation
            activity = agent_data.get("activity", "idle")
            obs = Observation(
                content=f"{other_name} is here, {activity}",
                observation_type=ObservationType.AGENT_PRESENCE,
                location=current_location,
                subject=other_name,
                attention_score=self._calculate_agent_attention(
                    other_name, activity, agent_role, relationship_scores
                ),
                importance=5.0
            )
            observations.append(obs)
            
            # If they're doing something interesting, add activity observation
            if activity not in ["idle", "resting", "sleeping"]:
                activity_obs = Observation(
                    content=f"{other_name} is {activity}",
                    observation_type=ObservationType.AGENT_ACTIVITY,
                    location=current_location,
                    subject=other_name,
                    attention_score=self._calculate_activity_attention(
                        activity, agent_role
                    ),
                    importance=4.0
                )
                observations.append(activity_obs)
        
        # 2. Perceive recent dialogues
        recent_dialogues = world_state.get("recent_dialogues", [])
        dialogue_list = []
        
        for dialogue in recent_dialogues[-5:]:  # Last 5 dialogues
            speaker = dialogue.get("speaker", "")
            content = dialogue.get("content", "")
            target = dialogue.get("target", "")
            location = dialogue.get("location", "")
            
            # Only perceive dialogues in same location or directed at agent
            if location != current_location and target != agent_name:
                continue
            
            dialogue_list.append(dialogue)
            
            attention = 5.0
            if target == agent_name:
                attention += self.DIALOGUE_ATTENTION_BOOST  # Spoken to directly
            if speaker in relationship_scores:
                attention += relationship_scores[speaker] * 0.5
            
            obs = Observation(
                content=f'{speaker} said: "{content}"',
                observation_type=ObservationType.AGENT_DIALOGUE,
                location=location,
                subject=speaker,
                speaker=speaker,
                dialogue_content=content,
                attention_score=min(10.0, attention),
                importance=self._calculate_dialogue_importance(content, agent_role)
            )
            observations.append(obs)
        
        # 3. Perceive location state
        location_states = world_state.get("locations", {})
        if current_location in location_states:
            loc_state = location_states[current_location]
            
            if loc_state.get("alert"):
                obs = Observation(
                    content=f"Alert at {current_location}: {loc_state['alert']}",
                    observation_type=ObservationType.EVENT,
                    location=current_location,
                    attention_score=9.0 + self.EVENT_ATTENTION_BOOST,
                    importance=9.0
                )
                observations.append(obs)
            
            # Location-specific observations
            if loc_state.get("status"):
                obs = Observation(
                    content=f"{current_location} status: {loc_state['status']}",
                    observation_type=ObservationType.LOCATION_STATE,
                    location=current_location,
                    attention_score=4.0,
                    importance=3.0
                )
                observations.append(obs)
        
        # 4. Perceive events
        active_events = world_state.get("events", [])
        for event in active_events:
            obs = Observation(
                content=event.get("description", "Unknown event"),
                observation_type=ObservationType.EVENT,
                location=event.get("location", ""),
                attention_score=8.0 + self.EVENT_ATTENTION_BOOST,
                importance=event.get("importance", 8.0)
            )
            observations.append(obs)
        
        # 5. Perceive time-based info
        obs = Observation(
            content=f"The time is {simulation_time}",
            observation_type=ObservationType.ENVIRONMENT,
            attention_score=2.0,
            importance=2.0
        )
        observations.append(obs)
        
        # Sort by attention and limit
        observations.sort(key=lambda o: o.attention_score, reverse=True)
        filtered_observations = observations[:self.MAX_ATTENTION_ITEMS]
        
        # Ensure minimum observations
        if len(filtered_observations) < self.MIN_ATTENTION_ITEMS:
            filtered_observations = observations[:self.MIN_ATTENTION_ITEMS]
        
        return PerceivedEnvironment(
            agent_name=agent_name,
            location=current_location,
            simulation_time=simulation_time,
            observations=filtered_observations,
            present_agents=present_agents,
            recent_dialogues=dialogue_list,
            location_state=location_states.get(current_location, {})
        )
    
    def _calculate_agent_attention(
        self, 
        other_name: str, 
        activity: str, 
        agent_role: str,
        relationship_scores: Dict[str, float]
    ) -> float:
        """Calculate attention score for another agent"""
        base = 5.0
        
        # Relationship boost
        if other_name in relationship_scores:
            rel_score = relationship_scores[other_name]
            base += rel_score * self.RELATIONSHIP_BOOST
        
        # Activity relevance to role
        role_keywords = self.role_interests.get(agent_role, [])
        for keyword in role_keywords:
            if keyword.lower() in activity.lower():
                base += 2.0
                break
        
        return min(10.0, base)
    
    def _calculate_activity_attention(self, activity: str, agent_role: str) -> float:
        """Calculate attention score based on activity relevance"""
        base = 4.0
        
        role_keywords = self.role_interests.get(agent_role, [])
        for keyword in role_keywords:
            if keyword.lower() in activity.lower():
                base += 2.5
                break
        
        # Emergency activities always grab attention
        if any(word in activity.lower() for word in ["emergency", "alert", "danger", "help"]):
            base += 4.0
        
        return min(10.0, base)
    
    def _calculate_dialogue_importance(self, content: str, agent_role: str) -> float:
        """Calculate importance of dialogue based on content"""
        base = 5.0
        
        # Role-relevant keywords
        role_keywords = self.role_interests.get(agent_role, [])
        for keyword in role_keywords:
            if keyword.lower() in content.lower():
                base += 1.5
        
        # Important keywords
        if any(word in content.lower() for word in ["urgent", "emergency", "important", "critical"]):
            base += 3.0
        
        return min(10.0, base)


# Global perception engine instance
perception_engine = PerceptionEngine()
