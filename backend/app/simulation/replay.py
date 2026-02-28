"""
Simulation Replay System

This module enables recording and playback of simulations at Aryabhata Station.

Features:
1. Frame-by-frame recording of simulation state
2. Compressed storage for efficient persistence
3. Playback with arbitrary speed control
4. Jump to any point in the simulation
5. Export/import for sharing simulations
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import gzip
import shutil
from enum import Enum


class RecordingFormat(Enum):
    """Available recording formats"""
    JSON = "json"           # Human-readable, larger
    JSON_GZ = "json.gz"     # Compressed JSON
    BINARY = "bin"          # Binary format (fastest)


@dataclass
class AgentFrame:
    """Snapshot of an agent's state at a moment in time"""
    name: str
    location: str
    action: str
    action_emoji: str
    current_plan: str
    relationships: Dict[str, int]
    # Emotional/mental state
    mood: str = "neutral"
    energy: float = 1.0
    # Movement
    is_moving: bool = False
    movement_path: List[str] = field(default_factory=list)
    path_progress: float = 0.0


@dataclass
class ConversationFrame:
    """Snapshot of an active conversation"""
    participants: List[str]
    location: str
    topic: str
    current_speaker: str
    utterances: List[Dict[str, str]]
    turn_count: int


@dataclass
class EventFrame:
    """A notable event that occurred"""
    event_type: str         # "action", "conversation", "emergency", "arrival", etc.
    description: str
    agents_involved: List[str]
    location: str
    importance: int = 5


@dataclass
class SimulationFrame:
    """Complete snapshot of simulation state at one moment"""
    step: int                           # Simulation step number
    simulation_time: str                # In-simulation time (e.g., "14:30")
    real_timestamp: str                 # When this was recorded (ISO format)
    
    # State snapshots
    agents: List[AgentFrame]
    conversations: List[ConversationFrame]
    events: List[EventFrame]
    
    # Global state
    active_emergencies: List[str] = field(default_factory=list)
    blocked_paths: List[List[str]] = field(default_factory=list)
    
    # Statistics
    total_conversations: int = 0
    total_reflections: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "step": self.step,
            "simulation_time": self.simulation_time,
            "real_timestamp": self.real_timestamp,
            "agents": [asdict(a) for a in self.agents],
            "conversations": [asdict(c) for c in self.conversations],
            "events": [asdict(e) for e in self.events],
            "active_emergencies": self.active_emergencies,
            "blocked_paths": self.blocked_paths,
            "total_conversations": self.total_conversations,
            "total_reflections": self.total_reflections
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SimulationFrame":
        """Create from dictionary"""
        agents = [AgentFrame(**a) for a in data.get("agents", [])]
        conversations = [ConversationFrame(**c) for c in data.get("conversations", [])]
        events = [EventFrame(**e) for e in data.get("events", [])]
        
        return cls(
            step=data.get("step", 0),
            simulation_time=data.get("simulation_time", "00:00"),
            real_timestamp=data.get("real_timestamp", ""),
            agents=agents,
            conversations=conversations,
            events=events,
            active_emergencies=data.get("active_emergencies", []),
            blocked_paths=data.get("blocked_paths", []),
            total_conversations=data.get("total_conversations", 0),
            total_reflections=data.get("total_reflections", 0)
        )


@dataclass
class RecordingMetadata:
    """Metadata about a recorded simulation"""
    name: str
    description: str = ""
    created_at: str = ""
    
    # Simulation info
    total_frames: int = 0
    first_sim_time: str = ""
    last_sim_time: str = ""
    
    # Agent info
    agent_names: List[str] = field(default_factory=list)
    agent_count: int = 0
    
    # Statistics
    total_conversations: int = 0
    total_events: int = 0
    total_emergencies: int = 0
    
    # Technical
    format: str = "json.gz"
    version: str = "1.0"


class SimulationRecorder:
    """
    Records simulation state for later playback.
    
    Usage:
        recorder = SimulationRecorder("my_simulation")
        
        # Each simulation step:
        recorder.record_frame(current_state)
        
        # When done:
        recorder.save()
    """
    
    def __init__(
        self,
        name: str,
        storage_dir: str = None,
        description: str = ""
    ):
        """
        Initialize a new recorder.
        
        Args:
            name: Name for this recording
            storage_dir: Where to store recordings (default: simulations/)
            description: Human-readable description
        """
        self.name = name
        self.description = description
        
        if storage_dir is None:
            # Default to simulations directory relative to backend
            self.storage_dir = Path(__file__).parent.parent.parent / "simulations"
        else:
            self.storage_dir = Path(storage_dir)
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.frames: List[SimulationFrame] = []
        self.metadata = RecordingMetadata(
            name=name,
            description=description,
            created_at=datetime.now().isoformat()
        )
        
        # Tracking for incremental stats
        self._total_conversations = 0
        self._total_events = 0
        self._total_emergencies = 0
    
    def record_frame(
        self,
        step: int,
        simulation_time: str,
        agents: List[Dict[str, Any]],
        conversations: List[Dict[str, Any]] = None,
        events: List[Dict[str, Any]] = None,
        active_emergencies: List[str] = None,
        blocked_paths: List[List[str]] = None
    ):
        """
        Record a single frame of simulation state.
        
        Args:
            step: Current simulation step
            simulation_time: In-simulation time (HH:MM format)
            agents: List of agent state dictionaries
            conversations: Active conversations
            events: Events that occurred this step
            active_emergencies: Current emergencies
            blocked_paths: Currently blocked paths
        """
        # Convert agent dicts to AgentFrame objects
        agent_frames = []
        for agent in agents:
            frame = AgentFrame(
                name=agent.get("name", "Unknown"),
                location=agent.get("location", "Unknown"),
                action=agent.get("action", agent.get("current_action", "idle")),
                action_emoji=agent.get("emoji", agent.get("action_emoji", "🙂")),
                current_plan=agent.get("plan", agent.get("daily_plan", "")),
                relationships=agent.get("relationships", {}),
                mood=agent.get("mood", "neutral"),
                energy=agent.get("energy", 1.0),
                is_moving=agent.get("is_moving", False),
                movement_path=agent.get("movement_path", []),
                path_progress=agent.get("path_progress", 0.0)
            )
            agent_frames.append(frame)
        
        # Convert conversation dicts
        conv_frames = []
        if conversations:
            for conv in conversations:
                frame = ConversationFrame(
                    participants=conv.get("participants", []),
                    location=conv.get("location", "Unknown"),
                    topic=conv.get("topic", "general"),
                    current_speaker=conv.get("current_speaker", ""),
                    utterances=conv.get("utterances", []),
                    turn_count=conv.get("turn_count", 0)
                )
                conv_frames.append(frame)
            self._total_conversations += len(conv_frames)
        
        # Convert event dicts
        event_frames = []
        if events:
            for event in events:
                frame = EventFrame(
                    event_type=event.get("type", event.get("event_type", "action")),
                    description=event.get("description", ""),
                    agents_involved=event.get("agents", event.get("agents_involved", [])),
                    location=event.get("location", "Unknown"),
                    importance=event.get("importance", 5)
                )
                event_frames.append(frame)
            self._total_events += len(event_frames)
        
        # Track emergencies
        if active_emergencies:
            self._total_emergencies = max(
                self._total_emergencies, 
                len(active_emergencies)
            )
        
        # Create frame
        frame = SimulationFrame(
            step=step,
            simulation_time=simulation_time,
            real_timestamp=datetime.now().isoformat(),
            agents=agent_frames,
            conversations=conv_frames,
            events=event_frames,
            active_emergencies=active_emergencies or [],
            blocked_paths=blocked_paths or [],
            total_conversations=self._total_conversations,
            total_reflections=0  # TODO: track reflections
        )
        
        self.frames.append(frame)
        
        # Update metadata
        self.metadata.total_frames = len(self.frames)
        if len(self.frames) == 1:
            self.metadata.first_sim_time = simulation_time
            self.metadata.agent_names = [a.name for a in agent_frames]
            self.metadata.agent_count = len(agent_frames)
        self.metadata.last_sim_time = simulation_time
    
    def save(self, format: RecordingFormat = RecordingFormat.JSON_GZ) -> str:
        """
        Save the recording to disk.
        
        Args:
            format: Storage format to use
            
        Returns:
            Path to the saved recording
        """
        # Update final metadata
        self.metadata.total_conversations = self._total_conversations
        self.metadata.total_events = self._total_events
        self.metadata.total_emergencies = self._total_emergencies
        self.metadata.format = format.value
        
        # Create recording directory
        recording_dir = self.storage_dir / self.name
        recording_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_path = recording_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(self.metadata), f, indent=2)
        
        # Save frames
        frames_data = [f.to_dict() for f in self.frames]
        
        if format == RecordingFormat.JSON:
            frames_path = recording_dir / "frames.json"
            with open(frames_path, 'w') as f:
                json.dump(frames_data, f)
        
        elif format == RecordingFormat.JSON_GZ:
            frames_path = recording_dir / "frames.json.gz"
            with gzip.open(frames_path, 'wt', encoding='utf-8') as f:
                json.dump(frames_data, f)
        
        else:
            # Binary format (for future optimization)
            frames_path = recording_dir / "frames.json.gz"
            with gzip.open(frames_path, 'wt', encoding='utf-8') as f:
                json.dump(frames_data, f)
        
        return str(recording_dir)
    
    def get_current_frame_count(self) -> int:
        """Get number of frames recorded so far"""
        return len(self.frames)


class SimulationPlayer:
    """
    Plays back recorded simulations.
    
    Usage:
        player = SimulationPlayer()
        player.load("my_simulation")
        
        # Get frames
        frame = player.get_frame(step=100)
        
        # Or iterate
        for frame in player.get_range(0, 100):
            process(frame)
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize the player.
        
        Args:
            storage_dir: Where recordings are stored
        """
        if storage_dir is None:
            self.storage_dir = Path(__file__).parent.parent.parent / "simulations"
        else:
            self.storage_dir = Path(storage_dir)
        
        self.current_recording: Optional[str] = None
        self.metadata: Optional[RecordingMetadata] = None
        self.frames: List[SimulationFrame] = []
        self._frame_index: Dict[int, int] = {}  # step -> index
    
    def list_recordings(self) -> List[RecordingMetadata]:
        """List all available recordings"""
        recordings = []
        
        if not self.storage_dir.exists():
            return recordings
        
        for recording_dir in self.storage_dir.iterdir():
            if recording_dir.is_dir():
                metadata_path = recording_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        data = json.load(f)
                        recordings.append(RecordingMetadata(**data))
        
        return recordings
    
    def load(self, name: str) -> bool:
        """
        Load a recording for playback.
        
        Args:
            name: Name of the recording to load
            
        Returns:
            True if loaded successfully
        """
        recording_dir = self.storage_dir / name
        
        if not recording_dir.exists():
            print(f"Recording not found: {name}")
            return False
        
        # Load metadata
        metadata_path = recording_dir / "metadata.json"
        if not metadata_path.exists():
            print(f"Invalid recording (no metadata): {name}")
            return False
        
        with open(metadata_path, 'r') as f:
            self.metadata = RecordingMetadata(**json.load(f))
        
        # Load frames based on format
        frames_data = None
        
        # Try compressed first
        gz_path = recording_dir / "frames.json.gz"
        if gz_path.exists():
            with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
                frames_data = json.load(f)
        else:
            # Try uncompressed
            json_path = recording_dir / "frames.json"
            if json_path.exists():
                with open(json_path, 'r') as f:
                    frames_data = json.load(f)
        
        if frames_data is None:
            print(f"No frame data found for: {name}")
            return False
        
        # Parse frames
        self.frames = [SimulationFrame.from_dict(f) for f in frames_data]
        
        # Build index
        self._frame_index = {f.step: i for i, f in enumerate(self.frames)}
        
        self.current_recording = name
        return True
    
    def get_frame(self, step: int) -> Optional[SimulationFrame]:
        """
        Get a specific frame by step number.
        
        Args:
            step: Simulation step to retrieve
            
        Returns:
            SimulationFrame or None if not found
        """
        if step in self._frame_index:
            return self.frames[self._frame_index[step]]
        
        # If exact step not found, find nearest
        if not self.frames:
            return None
        
        for frame in self.frames:
            if frame.step >= step:
                return frame
        
        return self.frames[-1]
    
    def get_frame_by_time(self, sim_time: str) -> Optional[SimulationFrame]:
        """
        Get the frame closest to a simulation time.
        
        Args:
            sim_time: Simulation time (HH:MM format)
            
        Returns:
            Closest SimulationFrame
        """
        if not self.frames:
            return None
        
        for frame in self.frames:
            if frame.simulation_time >= sim_time:
                return frame
        
        return self.frames[-1]
    
    def get_range(
        self,
        start_step: int,
        end_step: int
    ) -> List[SimulationFrame]:
        """
        Get a range of frames.
        
        Args:
            start_step: First step (inclusive)
            end_step: Last step (inclusive)
            
        Returns:
            List of frames in range
        """
        return [
            f for f in self.frames 
            if start_step <= f.step <= end_step
        ]
    
    def get_agent_timeline(
        self,
        agent_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of a specific agent's activities.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of agent states over time
        """
        timeline = []
        
        for frame in self.frames:
            for agent in frame.agents:
                if agent.name == agent_name:
                    timeline.append({
                        "step": frame.step,
                        "time": frame.simulation_time,
                        "location": agent.location,
                        "action": agent.action,
                        "emoji": agent.action_emoji,
                        "mood": agent.mood
                    })
                    break
        
        return timeline
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get all conversations that occurred during the simulation"""
        conversations = []
        
        for frame in self.frames:
            for conv in frame.conversations:
                conversations.append({
                    "step": frame.step,
                    "time": frame.simulation_time,
                    "participants": conv.participants,
                    "topic": conv.topic,
                    "utterances": conv.utterances,
                    "turns": conv.turn_count
                })
        
        return conversations
    
    def get_events(self, importance_min: int = 0) -> List[Dict[str, Any]]:
        """Get all events, optionally filtered by importance"""
        events = []
        
        for frame in self.frames:
            for event in frame.events:
                if event.importance >= importance_min:
                    events.append({
                        "step": frame.step,
                        "time": frame.simulation_time,
                        "type": event.event_type,
                        "description": event.description,
                        "agents": event.agents_involved,
                        "location": event.location,
                        "importance": event.importance
                    })
        
        return events
    
    def get_playback_info(self) -> Dict[str, Any]:
        """Get information about the loaded recording"""
        if not self.metadata:
            return {"loaded": False}
        
        return {
            "loaded": True,
            "name": self.metadata.name,
            "description": self.metadata.description,
            "total_frames": self.metadata.total_frames,
            "agent_count": self.metadata.agent_count,
            "agent_names": self.metadata.agent_names,
            "first_time": self.metadata.first_sim_time,
            "last_time": self.metadata.last_sim_time,
            "created_at": self.metadata.created_at,
            "stats": {
                "total_conversations": self.metadata.total_conversations,
                "total_events": self.metadata.total_events,
                "total_emergencies": self.metadata.total_emergencies
            }
        }
    
    def delete_recording(self, name: str) -> bool:
        """
        Delete a recording from disk.
        
        Args:
            name: Recording name to delete
            
        Returns:
            True if deleted successfully
        """
        recording_dir = self.storage_dir / name
        
        if not recording_dir.exists():
            return False
        
        try:
            shutil.rmtree(recording_dir)
            
            # Clear if this was loaded
            if self.current_recording == name:
                self.current_recording = None
                self.metadata = None
                self.frames = []
                self._frame_index = {}
            
            return True
        except Exception as e:
            print(f"Error deleting recording {name}: {e}")
            return False


# Singleton instances for shared use
_recorder_instance: Optional[SimulationRecorder] = None
_player_instance: Optional[SimulationPlayer] = None


def get_recorder(name: str = None) -> SimulationRecorder:
    """Get or create the shared recorder instance"""
    global _recorder_instance
    if _recorder_instance is None or (name and _recorder_instance.name != name):
        recording_name = name or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        _recorder_instance = SimulationRecorder(recording_name)
    return _recorder_instance


def get_player() -> SimulationPlayer:
    """Get the shared player instance"""
    global _player_instance
    if _player_instance is None:
        _player_instance = SimulationPlayer()
    return _player_instance
