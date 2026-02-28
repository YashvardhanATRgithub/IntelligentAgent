"""
Cognitive State - Working Memory for Generative Agents

This module implements the working/scratch memory for agents at Aryabhata Station.
It stores the transient cognitive state that agents use for decision-making,
planning, and interaction tracking.

Key Components:
- Identity Stable Set (ISS): Core identity traits that rarely change
- Attention & Perception: What the agent can see/focus on
- Planning State: Daily schedules and decomposed tasks
- Action State: Current activity and its metadata
- Conversation State: Active dialogues and buffers
- Path Planning: Movement routes through the station
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import json
from pathlib import Path


class ActionStatus(Enum):
    """Status of current action"""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    WAITING = "waiting"


@dataclass
class CognitiveState:
    """
    Working memory for an agent at Aryabhata Station.
    
    This is the agent's "mental scratchpad" - storing everything they're
    currently thinking about, planning, and doing. Unlike long-term memory
    (FAISS), this is fast-access, transient state.
    
    Inspired by human working memory with ~7±2 item capacity.
    """
    
    # ========== PERCEPTION PARAMETERS ==========
    # How far the agent can perceive (in terms of adjacent locations)
    perception_radius: int = 2
    # How many things agent can focus on simultaneously
    attention_bandwidth: int = 5
    # Short-term memory retention (number of recent items)
    retention_capacity: int = 7
    
    # ========== WORLD STATE ==========
    # Current simulation time as perceived by agent
    current_time: Optional[datetime] = None
    # Current location in the station
    world_location: str = "Crew Quarters" # Renamed from current_location to match engine usage better, but let's stick to world_location for clarity
    # What the agent perceives they need to do today (high-level)
    daily_requirement: str = ""
    # Current energy level (0-100)
    energy: float = 100.0
    # Current mood (happy, neutral, anxious, sad, etc.)
    mood: str = "neutral"
    
    # ========== IDENTITY STABLE SET (ISS) ==========
    # These rarely change - core identity
    name: str = ""
    first_name: str = ""
    last_name: str = ""
    age: int = 35
    role: str = ""
    
    # L0 - Innate traits (permanent, personality-based)
    innate_traits: str = ""
    # L1 - Learned traits (stable, experience-based)
    learned_traits: str = ""
    # L2 - Current focus (changes based on situation)
    current_focus: str = ""
    # Lifestyle patterns
    lifestyle: str = ""
    # Primary workspace
    primary_workspace: str = ""
    
    # ========== REFLECTION PARAMETERS ==========
    # Weights for memory retrieval scoring
    recency_weight: float = 1.0
    relevance_weight: float = 1.0
    importance_weight: float = 1.0
    # Decay rate for recency
    recency_decay: float = 0.995
    # Threshold for triggering reflection
    importance_trigger_max: int = 150
    importance_trigger_current: int = 150
    # Count of importance accumulated
    importance_accumulated: int = 0
    # Number of thoughts to generate in reflection
    thought_count: int = 5
    
    # ========== PLANNING STATE ==========
    # High-level daily goals
    daily_goals: List[str] = field(default_factory=list)
    
    # Full daily schedule with decomposition
    # Format: [["activity description", duration_minutes], ...]
    # e.g., [["sleeping", 360], ["morning routine", 60], ...]
    daily_schedule: List[List] = field(default_factory=list)
    
    # Original hourly schedule (before decomposition)
    # Kept for reference when re-planning
    daily_schedule_original: List[List] = field(default_factory=list)
    
    # ========== CURRENT ACTION STATE ==========
    # Full address of action location
    # Format: "Station:Module:Area:Object"
    # e.g., "Aryabhata:Agri Lab:Hydroponics Bay:Nutrient Monitor"
    action_address: Optional[str] = None
    # When the current action started
    action_start_time: Optional[datetime] = None
    # How long the action should take (minutes)
    action_duration: int = 0
    # Human-readable description
    act_description: str = "" # Renamed from action_description for brevity/clarity
    # Emoji representation (for UI/display)
    act_emoji: str = "🙂" # Renamed
    # Event triple: (subject, predicate, object)
    # e.g., ("Dr. Ananya", "is checking", "plant samples")
    action_event: Tuple[str, str, str] = ("", "", "")
    # Status of current action
    action_status: ActionStatus = ActionStatus.IDLE
    
    # Object interaction state
    object_description: str = ""
    object_emoji: str = ""
    object_event: Tuple[str, str, str] = ("", "", "")
    
    # ========== CONVERSATION STATE ==========
    # Who the agent is currently talking to (None if not in conversation)
    chatting_with: Optional[str] = None
    # Current conversation history
    # Format: [["Speaker Name", "utterance"], ...]
    conversation: List[List[str]] = field(default_factory=list)
    # Cooldown buffer - recent conversation partners
    # Format: {"Agent Name": remaining_cooldown_steps}
    conversation_cooldown: Dict[str, int] = field(default_factory=dict)
    # When current conversation should end
    conversation_end_time: Optional[datetime] = None
    
    # ========== PATH PLANNING STATE ==========
    # Whether we've computed the path for current action
    path_computed: bool = False
    # Planned path through locations
    # Format: ["Crew Quarters", "Mess Hall", "Agri Lab"]
    planned_path: List[str] = field(default_factory=list)
    # Current position in path (index)
    path_position: int = 0
    
    # ========== METHODS ==========
    
    def get_identity_summary(self) -> str:
        """
        Get the Identity Stable Set (ISS) - core identity summary.
        Used in most prompts to establish who the agent is.
        """
        date_str = self.current_time.strftime("%A %B %d, %Y") if self.current_time else "Unknown date"
        
        summary = f"""Name: {self.name}
Age: {self.age}
Role: {self.role}
Innate traits: {self.innate_traits}
Learned traits: {self.learned_traits}
Current focus: {self.current_focus}
Lifestyle: {self.lifestyle}
Daily requirement: {self.daily_requirement}
Current mood: {self.mood}
Current date: {date_str}"""
        return summary
    
    def get_action_summary(self) -> str:
        """Get a human-readable summary of current action"""
        if not self.action_address and not self.act_description:
            return f"{self.name} is idle"
        
        time_str = self.action_start_time.strftime("%H:%M") if self.action_start_time else "unknown time"
        return f"[{time_str}] {self.name} is {self.act_description} at {self.world_location} ({self.action_duration} min)"
    
    def get_schedule_summary(self) -> str:
        """Get formatted daily schedule"""
        if not self.daily_schedule:
            return "No schedule planned"
        
        lines = []
        cumulative_minutes = 0
        
        for activity, duration in self.daily_schedule:
            hours = cumulative_minutes // 60
            minutes = cumulative_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            lines.append(f"{time_str} - {activity} ({duration} min)")
            cumulative_minutes += duration
        
        return "\n".join(lines)
    
    def get_current_schedule_index(self, advance_minutes: int = 0) -> int:
        """
        Get the index of current activity in daily_schedule.
        """
        if not self.daily_schedule or not self.current_time:
            return -1
        
        # Calculate minutes elapsed today
        today_minutes = self.current_time.hour * 60 + self.current_time.minute + advance_minutes
        
        # Find which activity we're in
        cumulative = 0
        for idx, (activity, duration) in enumerate(self.daily_schedule):
            cumulative += duration
            if cumulative > today_minutes:
                return idx
        
        return len(self.daily_schedule) - 1
    
    def is_action_finished(self) -> bool:
        """Check if current action has completed"""
        if not self.action_start_time or not self.action_duration:
            return True
        
        if self.chatting_with and self.conversation_end_time:
            end_time = self.conversation_end_time
        else:
            end_time = self.action_start_time + timedelta(minutes=self.action_duration)
        
        if self.current_time:
            return self.current_time >= end_time
        return False
    
    def start_action(
        self,
        address: str,
        duration: int,
        description: str,
        emoji: str = "🙂",
        event: Tuple[str, str, str] = None
    ):
        """Begin a new action"""
        self.action_address = address
        self.action_duration = duration
        self.act_description = description
        self.act_emoji = emoji
        self.action_event = event or (self.name, "is doing", description)
        self.action_start_time = self.current_time
        self.action_status = ActionStatus.IN_PROGRESS
        self.path_computed = False
    
    def end_action(self):
        """Complete current action"""
        self.action_status = ActionStatus.COMPLETED
        self.action_address = None
        self.act_description = ""
        self.act_emoji = "🙂"
        self.action_event = ("", "", "")
        self.action_duration = 0
        # Clear path state so next action doesn't think we're still moving
        self.path_computed = False
        self.planned_path = []
        self.path_position = 0
    
    def start_conversation(self, partner: str, end_time: datetime = None):
        """Begin conversation with another agent"""
        self.chatting_with = partner
        self.conversation = []
        self.conversation_end_time = end_time
        self.action_status = ActionStatus.IN_PROGRESS
    
    def add_utterance(self, speaker: str, text: str):
        """Add utterance to current conversation"""
        self.conversation.append([speaker, text])
    
    def end_conversation(self, cooldown_steps: int = 10):
        """End current conversation and set cooldown"""
        if self.chatting_with:
            self.conversation_cooldown[self.chatting_with] = cooldown_steps
        
        self.chatting_with = None
        self.conversation = []
        self.conversation_end_time = None
        # Reset action state so agent becomes idle (same as end_action)
        self.action_status = ActionStatus.COMPLETED
        self.action_address = None
        self.act_description = ""
        self.act_emoji = "🙂"
        self.action_event = ("", "", "")
        self.action_duration = 0
        self.action_start_time = None
    
    def update_cooldowns(self):
        """Decrement conversation cooldowns each step"""
        expired = []
        for partner, remaining in self.conversation_cooldown.items():
            if remaining <= 1:
                expired.append(partner)
            else:
                self.conversation_cooldown[partner] = remaining - 1
        
        for partner in expired:
            del self.conversation_cooldown[partner]
    
    def can_talk_to(self, agent_name: str) -> bool:
        """Check if we can initiate conversation with agent"""
        if self.chatting_with:
            return False
        if agent_name in self.conversation_cooldown:
            return False
        return True
    
    def set_path(self, path: List[str]):
        """Set planned movement path"""
        self.planned_path = path
        self.path_position = 0
        self.path_computed = True
    
    def advance_path(self) -> Optional[str]:
        """Move to next location in path, return new location or None if done"""
        if self.path_position >= len(self.planned_path) - 1:
            return None
        
        self.path_position += 1
        self.world_location = self.planned_path[self.path_position]
        return self.world_location
    
    def trigger_reflection_check(self, importance: int) -> bool:
        """
        Check if accumulated importance triggers reflection.
        RETURNS True if reflection should occur.
        """
        self.importance_accumulated += importance
        
        if self.importance_accumulated >= self.importance_trigger_current:
            self.importance_accumulated = 0
            # Increase threshold slightly for next time
            self.importance_trigger_current = min(
                self.importance_trigger_max,
                self.importance_trigger_current + 10
            )
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Export state as dictionary for persistence/API"""
        return {
            # Perception
            "perception_radius": self.perception_radius,
            "attention_bandwidth": self.attention_bandwidth,
            "retention_capacity": self.retention_capacity,
            
            # World
            "current_time": self.current_time.isoformat() if isinstance(self.current_time, datetime) else str(self.current_time),
            "world_location": self.world_location,
            "daily_requirement": self.daily_requirement,
            "energy": self.energy,
            "mood": self.mood,
            
            # Identity
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "age": self.age,
            "role": self.role,
            "innate_traits": self.innate_traits,
            "learned_traits": self.learned_traits,
            "current_focus": self.current_focus,
            "lifestyle": self.lifestyle,
            "primary_workspace": self.primary_workspace,
            
            # Reflection
            "recency_weight": self.recency_weight,
            "relevance_weight": self.relevance_weight,
            "importance_weight": self.importance_weight,
            "recency_decay": self.recency_decay,
            "importance_trigger_current": self.importance_trigger_current,
            "importance_accumulated": self.importance_accumulated,
            
            # Planning
            "daily_goals": self.daily_goals,
            "daily_schedule": self.daily_schedule,
            "daily_schedule_original": self.daily_schedule_original,
            
            # Action
            "action_address": self.action_address,
            "action_start_time": self.action_start_time.isoformat() if isinstance(self.action_start_time, datetime) else str(self.action_start_time),
            "action_duration": self.action_duration,
            "act_description": self.act_description,
            "act_emoji": self.act_emoji,
            "action_event": list(self.action_event),
            "action_status": self.action_status.value,
            
            # Conversation
            "chatting_with": self.chatting_with,
            "conversation": self.conversation,
            "conversation_cooldown": self.conversation_cooldown,
            "conversation_end_time": self.conversation_end_time.isoformat() if self.conversation_end_time else None,
            
            # Path
            "path_computed": self.path_computed,
            "planned_path": self.planned_path,
            "path_position": self.path_position,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveState":
        """Load state from dictionary"""
        state = cls()
        
        # Perception
        state.perception_radius = data.get("perception_radius", 2)
        state.attention_bandwidth = data.get("attention_bandwidth", 5)
        state.retention_capacity = data.get("retention_capacity", 7)
        
        # World
        if data.get("current_time"):
            state.current_time = datetime.fromisoformat(data["current_time"])
        state.world_location = data.get("world_location", "Crew Quarters")
        state.daily_requirement = data.get("daily_requirement", "")
        state.energy = data.get("energy", 100.0)
        state.mood = data.get("mood", "neutral")
        
        # Identity
        state.name = data.get("name", "")
        state.first_name = data.get("first_name", "")
        state.last_name = data.get("last_name", "")
        state.age = data.get("age", 35)
        state.role = data.get("role", "")
        state.innate_traits = data.get("innate_traits", "")
        state.learned_traits = data.get("learned_traits", "")
        state.current_focus = data.get("current_focus", "")
        state.lifestyle = data.get("lifestyle", "")
        state.primary_workspace = data.get("primary_workspace", "")
        
        # Reflection
        state.recency_weight = data.get("recency_weight", 1.0)
        state.relevance_weight = data.get("relevance_weight", 1.0)
        state.importance_weight = data.get("importance_weight", 1.0)
        state.recency_decay = data.get("recency_decay", 0.995)
        state.importance_trigger_current = data.get("importance_trigger_current", 150)
        state.importance_accumulated = data.get("importance_accumulated", 0)
        
        # Planning
        state.daily_goals = data.get("daily_goals", [])
        state.daily_schedule = data.get("daily_schedule", [])
        state.daily_schedule_original = data.get("daily_schedule_original", [])
        
        # Action
        state.action_address = data.get("action_address")
        if data.get("action_start_time"):
            state.action_start_time = datetime.fromisoformat(data["action_start_time"])
        state.action_duration = data.get("action_duration", 0)
        state.act_description = data.get("act_description", "")
        state.act_emoji = data.get("act_emoji", "🙂")
        event = data.get("action_event", ["", "", ""])
        state.action_event = tuple(event) if event else ("", "", "")
        state.action_status = ActionStatus(data.get("action_status", "idle"))
        
        # Conversation
        state.chatting_with = data.get("chatting_with")
        state.conversation = data.get("conversation", [])
        state.conversation_cooldown = data.get("conversation_cooldown", {})
        if data.get("conversation_end_time"):
            state.conversation_end_time = datetime.fromisoformat(data["conversation_end_time"])
        
        # Path
        state.path_computed = data.get("path_computed", False)
        state.planned_path = data.get("planned_path", [])
        state.path_position = data.get("path_position", 0)
        
        return state
    
    def save(self, filepath: str):
        """Save state to JSON file"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> "CognitiveState":
        """Load state from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


def create_cognitive_state_for_agent(
    name: str,
    role: str,
    backstory: str,
    age: int = 35,
    innate_traits: str = "",
    learned_traits: str = "",
    personality_traits: str = "", # New argument to support BaseAgent init
    lifestyle: str = "",
    primary_workspace: str = "Mission Control"
) -> CognitiveState:
    """
    Factory function to create a CognitiveState for an agent.
    
    Args:
        name: Full name (e.g., "Dr. Ananya Iyer")
        role: Job role (e.g., "Botanist/Life Support")
        backstory: Agent backstory text
        age: Agent age
        innate_traits: Personality traits
        learned_traits: Skills and knowledge
        lifestyle: Daily patterns
        primary_workspace: Main work location
    
    Returns:
        Initialized CognitiveState
    """
    # Parse first/last name
    name_parts = name.replace("Dr. ", "").replace("Cdr. ", "").replace("Lt. ", "").split()
    first_name = name_parts[0] if name_parts else name
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    
    # Use backstory as current focus or learned traits fallback
    focus = backstory[:100] + "..." if len(backstory) > 100 else backstory
    
    # Use personality_traits if innate_traits is empty
    if not innate_traits and personality_traits:
        innate_traits = personality_traits
        
    state = CognitiveState(
        name=name,
        first_name=first_name,
        last_name=last_name,
        age=age,
        role=role,
        innate_traits=innate_traits,
        learned_traits=learned_traits,
        lifestyle=lifestyle,
        current_focus=focus, # Populate focus with backstory summary
        primary_workspace=primary_workspace,
        world_location=primary_workspace # Start at work
    )
    
    return state
