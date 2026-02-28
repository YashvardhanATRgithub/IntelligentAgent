"""
World Environment for Aryabhata Station
Manages hierarchical locations (Buildings -> Sub-areas), time, and simulation state.
Integrated with StationNavigator for valid movement paths.

Uses ACCELERATED simulation time:
- 1 real second = 1 simulation minute
- Full day cycles in ~24 real minutes
- Time ONLY advances when simulation is running
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import time

from .pathfinder import get_navigator, StationNavigator

class Location(Enum):
    """Main buildings at Aryabhata Station"""
    MISSION_CONTROL = "Mission Control"
    AGRI_LAB = "Agri Lab"
    MESS_HALL = "Mess Hall"
    REC_ROOM = "Rec Room"
    CREW_QUARTERS = "Crew Quarters"
    MEDICAL_BAY = "Medical Bay"
    COMMS_TOWER = "Comms Tower"
    MINING_TUNNEL = "Mining Tunnel"


@dataclass
class LocationNode:
    """Node in the location hierarchy tree"""
    name: str
    type: str  # "building" or "room"
    parent: Optional['LocationNode'] = None
    children: Dict[str, 'LocationNode'] = field(default_factory=dict)
    agents: List[str] = field(default_factory=list)  # List of agent IDs
    
    def add_child(self, child_name: str, child_type: str = "room") -> 'LocationNode':
        child = LocationNode(name=child_name, type=child_type, parent=self)
        self.children[child_name] = child
        return child
    
    def get_full_path(self) -> str:
        if self.parent:
            return f"{self.parent.get_full_path()}/{self.name}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "agents": self.agents,
            "children": {k: v.to_dict() for k, v in self.children.items()}
        }

@dataclass
class WorldState:
    """Accelerated simulation time"""
    accumulated_sim_minutes: int = 0
    last_update_time: float = field(default_factory=time.time)
    is_running: bool = False
    start_sim_hour: int = 6
    start_sim_minute: int = 0
    start_sim_day: int = 1
    start_sim_week: int = 1
    time_multiplier: float = 1.0
    active_events: List[str] = field(default_factory=list)
    agent_locations: Dict[str, str] = field(default_factory=dict) # agent_id -> full_path
    
    def update_time(self):
        if self.is_running:
            now = time.time()
            delta = now - self.last_update_time
            self.accumulated_sim_minutes += int(delta * self.time_multiplier)
            self.last_update_time = now
        else:
            self.last_update_time = time.time()
    
    def start(self):
        self.is_running = True
        self.last_update_time = time.time()
    
    def stop(self):
        self.update_time()
        self.is_running = False
    
    def _get_current_sim_time(self) -> tuple:
        self.update_time()
        start_total = self.start_sim_hour * 60 + self.start_sim_minute
        current_total = start_total + self.accumulated_sim_minutes
        days_elapsed = current_total // (24 * 60)
        remaining_mins = current_total % (24 * 60)
        hour = remaining_mins // 60
        minute = remaining_mins % 60
        total_days = self.start_sim_day + days_elapsed - 1
        week = self.start_sim_week + (total_days // 7)
        day = (total_days % 7) + 1
        return week, day, hour, minute
    
    def get_current_datetime(self) -> datetime:
        """Single canonical source of simulation datetime.
        Used by sim loop, perceive(), and get_environment_for_agent()."""
        from datetime import timedelta
        self.update_time()
        base_date = datetime(2030, 1, 1, self.start_sim_hour, self.start_sim_minute)
        return base_date + timedelta(minutes=self.accumulated_sim_minutes)
    
    @property
    def week(self) -> int: return self._get_current_sim_time()[0]
    @property
    def day(self) -> int: return self._get_current_sim_time()[1]
    @property
    def hour(self) -> int: return self._get_current_sim_time()[2]
    @property
    def minute(self) -> int: return self._get_current_sim_time()[3]
    @property
    def time_string(self) -> str:
        w, d, h, m = self._get_current_sim_time()
        return f"Week {w}, Day {d}, {h:02d}:{m:02d}"
    @property
    def is_night(self) -> bool: return self.hour < 6 or self.hour >= 22

class Environment:
    """Manages hierarchical simulation environment"""
    
    def __init__(self):
        self.state = WorldState()
        self.root = LocationNode(name="Aryabhata Station", type="station")
        self._build_hierarchy()
        self.navigator: StationNavigator = get_navigator()
    
    def _build_hierarchy(self):
        """Initialize all 8 buildings at Aryabhata Station"""
        self.root.add_child(Location.MISSION_CONTROL.value, "building")
        self.root.add_child(Location.CREW_QUARTERS.value, "building")
        self.root.add_child(Location.MEDICAL_BAY.value, "building")
        self.root.add_child(Location.AGRI_LAB.value, "building")
        self.root.add_child(Location.MESS_HALL.value, "building")
        self.root.add_child(Location.COMMS_TOWER.value, "building")
        self.root.add_child(Location.MINING_TUNNEL.value, "building")
        self.root.add_child(Location.REC_ROOM.value, "building")

    
    def _find_node(self, full_path: str) -> Optional[LocationNode]:
        """Find a node by its full path (e.g. 'Mission Control/Command Deck')"""
        if not full_path:
            return None
            
        parts = full_path.split("/")
        current = self.root
        
        # Handle cases where path includes "Aryabhata Station" or not
        if parts[0] == "Aryabhata Station":
            parts = parts[1:]
            
        for part in parts:
            if part in current.children:
                current = current.children[part]
            else:
                # Fallback: check if 'part' matches a building name directly
                return None
        return current

    def start(self): self.state.start()
    def stop(self): self.state.stop()
    
    def get_agents_at_location(self, location: str) -> List[Dict[str, Any]]:
        """
        Get all agents at a location (including sub-areas).
        location can be a building name ("Mission Control") or full path.
        """
        node = self._find_node(location)
        if not node:
            # Fallback for just building name lookup at root level
            if location in self.root.children:
                node = self.root.children[location]
            else:
                return []
        
        agents = []
        # Collect agents recursively
        def collect_agents(n: LocationNode):
            for agent_id in n.agents:
                agents.append({"id": agent_id, "name": agent_id.split("_")[0]})
            for child in n.children.values():
                collect_agents(child)
        
        collect_agents(node)
        return agents
    
    def move_agent(self, agent_id: str, agent_name: str, from_loc: str, to_loc: str) -> bool:
        """
        Move agent between locations.
        Supports full paths: "Mission Control/Command Deck"
        """
        # Remove from old
        if from_loc:
            old_node = self._find_node(from_loc)
            if old_node and agent_id in old_node.agents:
                old_node.agents.remove(agent_id)
        
        # Find new node
        new_node = self._find_node(to_loc)
        
        # If not found, try robust search
        if not new_node:
            # Try case-insensitive match for building name
            to_loc_lower = to_loc.lower().strip()
            for building_name, building_node in self.root.children.items():
                if building_name.lower() == to_loc_lower:
                    new_node = building_node
                    break
            
            # Still not found? Try partial match
            if not new_node:
                for building_name, building_node in self.root.children.items():
                    if to_loc_lower in building_name.lower() or building_name.lower() in to_loc_lower:
                        new_node = building_node
                        break
        
        if new_node:
            new_node.agents.append(agent_id)
            self.state.agent_locations[agent_id] = new_node.get_full_path()
            return True
        else:
            print(f"⚠️ Could not find location node: {to_loc}")
            return False

    def get_environment_for_agent(self, agent_location: str) -> Dict[str, Any]:
        """Get the current environment state for a specific agent"""
        # Use the single canonical datetime source
        current_dt = self.state.get_current_datetime()
        
        return {
            "time": current_dt, # Return datetime object
            "time_string": self.state.time_string, # Keep string for display if needed
            "hour": self.state.hour,
            "is_night": self.state.is_night,
            "agents_at_location": self.get_agents_at_location(agent_location),
            "valid_moves": self.navigator.get_adjacent_locations(agent_location),
            "events": self.state.active_events,
            "location": agent_location
        }
    
    def step(self): self.state.active_events = [] # Clear events
    def set_time_speed(self, multiplier: float): self.state.time_multiplier = max(0.1, min(60.0, multiplier))
    
    def to_dict(self) -> Dict[str, Any]:
        """Return full state including hierarchical locations and blocked paths"""
        return {
            "time": self.state.time_string,
            "week": self.state.week,
            "day": self.state.day,
            "hour": self.state.hour,
            "minute": self.state.minute,
            "is_running": self.state.is_running,
            "is_night": self.state.is_night,
            "locations": self.root.to_dict()["children"], # Send children of root (Buildings)
            "active_events": self.state.active_events,
            "blocked_connections": list(self.navigator.blocked_paths) if self.navigator else []
        }
