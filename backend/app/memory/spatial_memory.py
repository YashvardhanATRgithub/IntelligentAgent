"""
Spatial Memory - Stanford-level location knowledge and navigation

Based on Stanford's spatial_memory.py (~3KB) but expanded.

Key features:
1. Location knowledge (what's at each location)
2. Path finding between locations
3. Agent location tracking history
4. Navigation preferences per agent
5. Location familiarity scoring
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from collections import defaultdict
import heapq


class LocationType(Enum):
    """Types of locations at the station"""
    COMMAND = "command"         # Mission Control
    HABITAT = "habitat"         # Living areas
    WORK = "work"               # Work areas
    SOCIAL = "social"           # Social spaces
    MEDICAL = "medical"         # Medical facilities
    EXTERNAL = "external"       # Mining, Comms


@dataclass
class LocationInfo:
    """Information about a location"""
    name: str
    location_type: LocationType
    description: str
    capacity: int = 10
    objects: List[str] = field(default_factory=list)
    typical_activities: List[str] = field(default_factory=list)
    connected_to: List[str] = field(default_factory=list)


@dataclass
class LocationVisit:
    """Record of an agent visiting a location"""
    agent_name: str
    location: str
    arrival_time: datetime
    departure_time: Optional[datetime] = None
    activity: str = ""


class SpatialMemory:
    """
    Stanford-level spatial memory system.
    
    Tracks:
    - What's at each location
    - How to navigate between locations
    - Agent location history
    - Location familiarity
    """
    
    def __init__(self):
        # Station layout
        self.locations: Dict[str, LocationInfo] = self._initialize_station()
        
        # Agent location history
        self.visit_history: Dict[str, List[LocationVisit]] = defaultdict(list)
        
        # Current agent locations
        self.current_locations: Dict[str, str] = {}
        
        # Location familiarity scores per agent (0-1)
        self.familiarity: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Navigation graph (for pathfinding)
        self.graph: Dict[str, List[str]] = self._build_navigation_graph()
    
    def _initialize_station(self) -> Dict[str, LocationInfo]:
        """Initialize Aryabhata Station layout"""
        return {
            "Mission Control": LocationInfo(
                name="Mission Control",
                location_type=LocationType.COMMAND,
                description="Central command hub with Earth communications and station systems",
                capacity=8,
                objects=["main console", "communication terminal", "status displays", "TARA interface"],
                typical_activities=["work", "monitor", "communicate", "briefing"],
                connected_to=["Crew Quarters", "Comms Tower", "Medical Bay"]
            ),
            "Agri Lab": LocationInfo(
                name="Agri Lab",
                location_type=LocationType.WORK,
                description="Hydroponic agriculture laboratory for food production",
                capacity=4,
                objects=["hydroponic beds", "growth lights", "water recycler", "seed storage"],
                typical_activities=["work", "experiment", "harvest", "maintain"],
                connected_to=["Mess Hall", "Crew Quarters"]
            ),
            "Mess Hall": LocationInfo(
                name="Mess Hall",
                location_type=LocationType.SOCIAL,
                description="Communal dining and gathering area",
                capacity=15,
                objects=["dining tables", "food synthesizer", "coffee maker", "notice board"],
                typical_activities=["eat", "talk", "relax", "meeting"],
                connected_to=["Agri Lab", "Rec Room", "Crew Quarters"]
            ),
            "Rec Room": LocationInfo(
                name="Rec Room",
                location_type=LocationType.SOCIAL,
                description="Recreation and relaxation area",
                capacity=8,
                objects=["exercise equipment", "movie screen", "games", "lounge chairs"],
                typical_activities=["exercise", "relax", "socialize", "play"],
                connected_to=["Mess Hall", "Crew Quarters"]
            ),
            "Crew Quarters": LocationInfo(
                name="Crew Quarters",
                location_type=LocationType.HABITAT,
                description="Private sleeping and personal space for crew",
                capacity=8,
                objects=["bunks", "personal lockers", "private terminals", "life support"],
                typical_activities=["sleep", "rest", "personal time", "call home"],
                connected_to=["Mission Control", "Agri Lab", "Mess Hall", "Rec Room", "Medical Bay"]
            ),
            "Medical Bay": LocationInfo(
                name="Medical Bay",
                location_type=LocationType.MEDICAL,
                description="Medical facility and health monitoring center",
                capacity=4,
                objects=["medical beds", "diagnostic equipment", "pharmacy", "surgery suite"],
                typical_activities=["checkup", "treatment", "rest", "counseling"],
                connected_to=["Mission Control", "Crew Quarters"]
            ),
            "Comms Tower": LocationInfo(
                name="Comms Tower",
                location_type=LocationType.WORK,
                description="Communications array for Earth-Moon transmissions",
                capacity=3,
                objects=["antenna controls", "signal processor", "backup systems", "recording equipment"],
                typical_activities=["communicate", "maintain", "monitor", "record"],
                connected_to=["Mission Control", "Mining Tunnel"]
            ),
            "Mining Tunnel": LocationInfo(
                name="Mining Tunnel",
                location_type=LocationType.EXTERNAL,
                description="Helium-3 mining operations in lunar regolith",
                capacity=4,
                objects=["mining equipment", "sample containers", "safety gear", "transport rover"],
                typical_activities=["mine", "explore", "analyze", "maintain"],
                connected_to=["Comms Tower"]
            )
        }
    
    def _build_navigation_graph(self) -> Dict[str, List[str]]:
        """Build graph for pathfinding"""
        graph = {}
        for loc_name, loc_info in self.locations.items():
            graph[loc_name] = loc_info.connected_to
        return graph
    
    def find_path(self, from_loc: str, to_loc: str) -> List[str]:
        """
        Find shortest path between two locations using BFS.
        
        Returns:
            List of locations to traverse (including start and end)
        """
        if from_loc == to_loc:
            return [from_loc]
        
        if from_loc not in self.graph or to_loc not in self.graph:
            return []
        
        # BFS
        queue = [(from_loc, [from_loc])]
        visited = {from_loc}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in self.graph.get(current, []):
                if neighbor == to_loc:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # No path found
    
    def get_distance(self, from_loc: str, to_loc: str) -> int:
        """Get number of steps between locations"""
        path = self.find_path(from_loc, to_loc)
        return len(path) - 1 if path else -1
    
    def get_adjacent_locations(self, location: str) -> List[str]:
        """Get locations directly connected to this one"""
        return self.graph.get(location, [])
    
    def record_visit(
        self,
        agent_name: str,
        location: str,
        activity: str = ""
    ):
        """Record an agent arriving at a location"""
        # End previous visit if any
        if agent_name in self.current_locations:
            prev_loc = self.current_locations[agent_name]
            if self.visit_history[agent_name]:
                last_visit = self.visit_history[agent_name][-1]
                if last_visit.departure_time is None:
                    last_visit.departure_time = datetime.now()
        
        # Record new visit
        visit = LocationVisit(
            agent_name=agent_name,
            location=location,
            arrival_time=datetime.now(),
            activity=activity
        )
        self.visit_history[agent_name].append(visit)
        self.current_locations[agent_name] = location
        
        # Increase familiarity
        self.familiarity[agent_name][location] = min(
            1.0,
            self.familiarity[agent_name][location] + 0.02
        )
        
        # Keep history limited
        if len(self.visit_history[agent_name]) > 100:
            self.visit_history[agent_name] = self.visit_history[agent_name][-100:]
    
    def get_agent_location(self, agent_name: str) -> Optional[str]:
        """Get current location of an agent"""
        return self.current_locations.get(agent_name)
    
    def get_agents_at_location(self, location: str) -> List[str]:
        """Get all agents currently at a location"""
        return [
            agent for agent, loc in self.current_locations.items()
            if loc == location
        ]
    
    def get_location_info(self, location: str) -> Optional[LocationInfo]:
        """Get detailed info about a location"""
        return self.locations.get(location)
    
    def get_familiarity(self, agent_name: str, location: str) -> float:
        """Get how familiar an agent is with a location (0-1)"""
        return self.familiarity[agent_name][location]
    
    def get_most_visited(self, agent_name: str, limit: int = 3) -> List[Tuple[str, int]]:
        """Get agent's most visited locations"""
        visit_counts = defaultdict(int)
        for visit in self.visit_history[agent_name]:
            visit_counts[visit.location] += 1
        
        sorted_locs = sorted(visit_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_locs[:limit]
    
    def get_location_for_activity(self, activity: str) -> List[str]:
        """Find locations suitable for an activity"""
        suitable = []
        activity_lower = activity.lower()
        
        for loc_name, loc_info in self.locations.items():
            for typical in loc_info.typical_activities:
                if typical in activity_lower or activity_lower in typical:
                    suitable.append(loc_name)
                    break
        
        return suitable
    
    def describe_location(self, location: str) -> str:
        """Get natural language description of a location"""
        info = self.locations.get(location)
        if not info:
            return f"Unknown location: {location}"
        
        agents = self.get_agents_at_location(location)
        agent_str = f"Present: {', '.join(agents)}" if agents else "Currently empty"
        
        return f"{info.name}: {info.description}. Objects: {', '.join(info.objects[:3])}. {agent_str}"
    
    def to_dict(self, agent_name: str = None) -> Dict[str, Any]:
        """Export spatial memory as dictionary"""
        base = {
            "locations": {
                name: {
                    "type": info.location_type.value,
                    "description": info.description,
                    "connected_to": info.connected_to,
                    "current_agents": self.get_agents_at_location(name)
                }
                for name, info in self.locations.items()
            }
        }
        
        if agent_name:
            base["agent_location"] = self.current_locations.get(agent_name)
            base["familiarity"] = dict(self.familiarity[agent_name])
            base["most_visited"] = self.get_most_visited(agent_name)
        
        return base


# Global spatial memory instance
spatial_memory = SpatialMemory()
