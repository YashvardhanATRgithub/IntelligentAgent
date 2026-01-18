"""
World Environment for Aryabhata Station
Manages locations, time, and simulation state
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class Location(Enum):
    """All locations at Aryabhata Station"""
    MISSION_CONTROL = "Mission Control"
    AGRI_LAB = "Agri Lab"
    MESS_HALL = "Mess Hall"
    REC_ROOM = "Rec Room"
    CREW_QUARTERS = "Crew Quarters"
    MEDICAL_BAY = "Medical Bay"
    COMMS_TOWER = "Comms Tower"
    MINING_TUNNEL = "Mining Tunnel"


# Adjacent locations (for movement)
LOCATION_CONNECTIONS = {
    Location.MISSION_CONTROL: [Location.CREW_QUARTERS, Location.COMMS_TOWER, Location.MEDICAL_BAY],
    Location.AGRI_LAB: [Location.MESS_HALL, Location.CREW_QUARTERS],
    Location.MESS_HALL: [Location.AGRI_LAB, Location.REC_ROOM, Location.CREW_QUARTERS],
    Location.REC_ROOM: [Location.MESS_HALL, Location.CREW_QUARTERS],
    Location.CREW_QUARTERS: [Location.MISSION_CONTROL, Location.AGRI_LAB, Location.MESS_HALL, Location.REC_ROOM, Location.MEDICAL_BAY],
    Location.MEDICAL_BAY: [Location.MISSION_CONTROL, Location.CREW_QUARTERS],
    Location.COMMS_TOWER: [Location.MISSION_CONTROL, Location.MINING_TUNNEL],
    Location.MINING_TUNNEL: [Location.COMMS_TOWER],
}


@dataclass
class WorldState:
    """Current state of the simulation world - synced to real-time"""
    # No stored time - uses system time dynamically
    
    # Events happening now
    active_events: List[str] = field(default_factory=list)
    
    # Agent locations
    agent_locations: Dict[str, str] = field(default_factory=dict)
    
    @property
    def time_string(self) -> str:
        """Get current real-world time string"""
        now = datetime.now()
        return f"Week {now.isocalendar()[1]}, Day {now.isoweekday()}, {now.strftime('%H:%M')}"
    
    @property
    def is_night(self) -> bool:
        """Check if it is night based on real time"""
        hour = datetime.now().hour
        return hour < 6 or hour >= 22

    @property
    def hour(self) -> int:
        return datetime.now().hour

    @property
    def minute(self) -> int:
        return datetime.now().minute
    
    @property
    def day(self) -> int:
        return datetime.now().isoweekday()
    
    @property
    def week(self) -> int:
        return datetime.now().isocalendar()[1]
    
    @property
    def time_string(self) -> str:
        return f"Week {self.week}, Day {self.day}, {self.hour:02d}:{self.minute:02d}"
    
    @property
    def is_night(self) -> bool:
        return self.hour < 6 or self.hour >= 22


class Environment:
    """
    Manages the simulation environment
    """
    
    def __init__(self):
        self.state = WorldState()
        self.locations = {loc.value: [] for loc in Location}
    
    def get_agents_at_location(self, location: str) -> List[Dict[str, Any]]:
        """Get all agents at a location"""
        return self.locations.get(location, [])
    
    def move_agent(self, agent_id: str, agent_name: str, from_loc: str, to_loc: str) -> bool:
        """Move an agent between locations"""
        # Remove from old location
        if from_loc in self.locations:
            self.locations[from_loc] = [
                a for a in self.locations[from_loc] 
                if a.get("id") != agent_id
            ]
        
        # Add to new location
        if to_loc in self.locations:
            self.locations[to_loc].append({
                "id": agent_id,
                "name": agent_name
            })
            self.state.agent_locations[agent_id] = to_loc
            return True
        
        return False
    
    def get_environment_for_agent(self, agent_location: str) -> Dict[str, Any]:
        """Get environment state from an agent's perspective"""
        return {
            "time": self.state.time_string,
            "is_night": self.state.is_night,
            "agents_at_location": self.get_agents_at_location(agent_location),
            "events": self.state.active_events,
            "location": agent_location
        }
    
    def add_event(self, event: str):
        """Add a global event"""
        self.state.active_events.append(event)
    
    def clear_events(self):
        """Clear processed events"""
        self.state.active_events = []
    
    def step(self):
        """Advance the world (events only, time is real-time)"""
        self.clear_events()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize world state"""
        return {
            "time": self.state.time_string,
            "week": self.state.week,
            "day": self.state.day,
            "hour": self.state.hour,
            "is_night": self.state.is_night,
            "locations": {
                loc: agents for loc, agents in self.locations.items()
            },
            "active_events": self.state.active_events
        }
