"""
Station Navigator - Pathfinding for Aryabhata Station

This module implements A* pathfinding between locations in the lunar base.
Agents use this to navigate realistically through the station rather than
teleporting between locations.

Features:
- A* algorithm for optimal path finding
- Travel time estimation based on distance
- Path description generation for memory/display
- Support for blocked/restricted paths (emergencies)
"""
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from heapq import heappush, heappop
import math


@dataclass
class PathResult:
    """Result of a pathfinding operation"""
    path: List[str]           # Sequence of locations
    total_distance: int       # Abstract distance units
    travel_time_minutes: int  # Estimated travel time
    description: str          # Natural language description
    
    def __bool__(self) -> bool:
        """True if path was found"""
        return len(self.path) > 0


class StationNavigator:
    """
    A* Pathfinding for Aryabhata Station.
    
    The station is modeled as a graph where:
    - Nodes are locations (modules)
    - Edges represent corridors/connections
    - Edge weights represent distance/travel time
    
    Layout of Aryabhata Station:
    
           Comms Tower
               |
         Mission Control
           /         \\
    Crew Quarters    Medical Bay
       |    |            |
    Mess Hall         Agri Lab
       |                 |
    Rec Room       Mining Tunnel
    """
    
    def __init__(self):
        # Define the station layout as an adjacency graph
        # Format: location -> [(connected_location, distance), ...]
        self.graph: Dict[str, List[Tuple[str, int]]] = {
            "Mission Control": [
                ("Crew Quarters", 2),
                ("Medical Bay", 2),
                ("Comms Tower", 1),
            ],
            "Crew Quarters": [
                ("Mission Control", 2),
                ("Mess Hall", 1),
                ("Rec Room", 1),
            ],
            "Medical Bay": [
                ("Mission Control", 2),
                ("Agri Lab", 2),
            ],
            "Agri Lab": [
                ("Medical Bay", 2),
                ("Mining Tunnel", 3),
            ],
            "Mess Hall": [
                ("Crew Quarters", 1),
                ("Rec Room", 1),
            ],
            "Comms Tower": [
                ("Mission Control", 1),
            ],
            "Mining Tunnel": [
                ("Agri Lab", 3),
            ],
            "Rec Room": [
                ("Crew Quarters", 1),
                ("Mess Hall", 1),
            ],
        }
        
        # Minutes per distance unit (lunar gravity affects walking speed)
        self.minutes_per_unit = 2
        
        # Blocked paths (e.g., during emergencies)
        self.blocked_paths: Set[Tuple[str, str]] = set()
        
        # Location coordinates for heuristic (x, y in abstract units)
        # Used for A* heuristic estimation
        self.coordinates: Dict[str, Tuple[int, int]] = {
            "Comms Tower": (5, 0),
            "Mission Control": (5, 2),
            "Crew Quarters": (2, 4),
            "Medical Bay": (8, 4),
            "Mess Hall": (1, 6),
            "Rec Room": (3, 6),
            "Agri Lab": (8, 6),
            "Mining Tunnel": (8, 9),
        }
    
    def _heuristic(self, loc1: str, loc2: str) -> float:
        """
        A* heuristic: Euclidean distance between locations.
        """
        if loc1 not in self.coordinates or loc2 not in self.coordinates:
            return 0
        
        x1, y1 = self.coordinates[loc1]
        x2, y2 = self.coordinates[loc2]
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _is_path_blocked(self, loc1: str, loc2: str) -> bool:
        """Check if path between two locations is blocked"""
        return (loc1, loc2) in self.blocked_paths or (loc2, loc1) in self.blocked_paths
    
    def find_path(self, start: str, end: str) -> PathResult:
        """
        Find the optimal path between two locations using A*.
        
        Args:
            start: Starting location
            end: Destination location
            
        Returns:
            PathResult with path details, or empty path if no route exists
        """
        if start == end:
            return PathResult(
                path=[start],
                total_distance=0,
                travel_time_minutes=0,
                description=f"Already at {start}"
            )
        
        if start not in self.graph:
            return PathResult(
                path=[],
                total_distance=0,
                travel_time_minutes=0,
                description=f"Unknown location: {start}"
            )
        
        if end not in self.graph:
            return PathResult(
                path=[],
                total_distance=0,
                travel_time_minutes=0,
                description=f"Unknown location: {end}"
            )
        
        # A* algorithm
        # Priority queue: (f_score, g_score, current_node, path)
        open_set = [(self._heuristic(start, end), 0, start, [start])]
        visited: Set[str] = set()
        
        while open_set:
            _, g_score, current, path = heappop(open_set)
            
            if current == end:
                return PathResult(
                    path=path,
                    total_distance=g_score,
                    travel_time_minutes=g_score * self.minutes_per_unit,
                    description=self._generate_path_description(path)
                )
            
            if current in visited:
                continue
            visited.add(current)
            
            for neighbor, distance in self.graph.get(current, []):
                if neighbor in visited:
                    continue
                
                if self._is_path_blocked(current, neighbor):
                    continue
                
                new_g = g_score + distance
                new_f = new_g + self._heuristic(neighbor, end)
                new_path = path + [neighbor]
                
                heappush(open_set, (new_f, new_g, neighbor, new_path))
        
        # No path found
        return PathResult(
            path=[],
            total_distance=0,
            travel_time_minutes=0,
            description=f"No path available from {start} to {end}"
        )
    
    def get_travel_time(self, start: str, end: str) -> int:
        """
        Get travel time in minutes between two locations.
        
        Args:
            start: Starting location
            end: Destination
            
        Returns:
            Travel time in minutes, or -1 if no path exists
        """
        result = self.find_path(start, end)
        return result.travel_time_minutes if result else -1
    
    def get_adjacent_locations(self, location: str) -> List[str]:
        """
        Get all locations directly connected to the given location.
        
        Args:
            location: Current location
            
        Returns:
            List of adjacent location names
        """
        if location not in self.graph:
            return []
        
        adjacent = []
        for neighbor, _ in self.graph[location]:
            if not self._is_path_blocked(location, neighbor):
                adjacent.append(neighbor)
        
        return adjacent
    
    def get_locations_within_radius(
        self,
        location: str,
        radius: int = 2
    ) -> List[Tuple[str, int]]:
        """
        Get all locations within a certain distance.
        
        Used for perception radius - what locations can an agent see/sense.
        
        Args:
            location: Center location
            radius: Maximum distance in graph edges
            
        Returns:
            List of (location, distance) tuples
        """
        if location not in self.graph:
            return []
        
        result = []
        visited = {location: 0}
        queue = [(location, 0)]
        
        while queue:
            current, dist = queue.pop(0)
            
            if dist > 0:
                result.append((current, dist))
            
            if dist < radius:
                for neighbor, _ in self.graph.get(current, []):
                    if neighbor not in visited:
                        visited[neighbor] = dist + 1
                        queue.append((neighbor, dist + 1))
        
        return sorted(result, key=lambda x: x[1])
    
    def block_path(self, loc1: str, loc2: str):
        """
        Block the path between two locations (e.g., emergency, damage).
        """
        self.blocked_paths.add((loc1, loc2))
    
    def unblock_path(self, loc1: str, loc2: str):
        """
        Unblock a previously blocked path.
        """
        self.blocked_paths.discard((loc1, loc2))
        self.blocked_paths.discard((loc2, loc1))
    
    def unblock_all(self):
        """Clear all blocked paths"""
        self.blocked_paths.clear()
    
    def _generate_path_description(self, path: List[str]) -> str:
        """
        Generate natural language description of a path.
        
        Args:
            path: List of locations in order
            
        Returns:
            Human-readable path description
        """
        if not path:
            return "No path"
        
        if len(path) == 1:
            return f"Staying at {path[0]}"
        
        if len(path) == 2:
            return f"Walking from {path[0]} to {path[1]}"
        
        # Multi-step path
        via_locations = path[1:-1]
        via_str = ", ".join(via_locations)
        return f"Walking from {path[0]} to {path[-1]} via {via_str}"
    
    def get_path_for_animation(
        self,
        start: str,
        end: str,
        steps_per_segment: int = 5
    ) -> List[Dict]:
        """
        Generate animation-friendly path data.
        
        Args:
            start: Starting location
            end: Destination
            steps_per_segment: Animation steps between each location pair
            
        Returns:
            List of animation frames with position data
        """
        result = self.find_path(start, end)
        if not result.path:
            return []
        
        frames = []
        path = result.path
        
        for i in range(len(path) - 1):
            from_loc = path[i]
            to_loc = path[i + 1]
            
            from_coord = self.coordinates.get(from_loc, (0, 0))
            to_coord = self.coordinates.get(to_loc, (0, 0))
            
            for step in range(steps_per_segment):
                progress = step / steps_per_segment
                x = from_coord[0] + (to_coord[0] - from_coord[0]) * progress
                y = from_coord[1] + (to_coord[1] - from_coord[1]) * progress
                
                frames.append({
                    "x": x,
                    "y": y,
                    "from": from_loc,
                    "to": to_loc,
                    "progress": progress,
                    "segment": i,
                    "moving": True
                })
        
        # Final frame at destination
        end_coord = self.coordinates.get(end, (0, 0))
        frames.append({
            "x": end_coord[0],
            "y": end_coord[1],
            "from": end,
            "to": end,
            "progress": 1.0,
            "segment": len(path) - 1,
            "moving": False
        })
        
        return frames
    
    def get_all_locations(self) -> List[str]:
        """Get list of all locations in the station"""
        return list(self.graph.keys())
    
    def get_location_info(self, location: str) -> Dict:
        """Get information about a location"""
        if location not in self.graph:
            return {}
        
        coord = self.coordinates.get(location, (0, 0))
        neighbors = self.get_adjacent_locations(location)
        
        return {
            "name": location,
            "x": coord[0],
            "y": coord[1],
            "neighbors": neighbors,
            "num_connections": len(neighbors)
        }
    
    def calculate_station_layout(self) -> Dict:
        """
        Get complete station layout data for visualization.
        
        Returns dict with locations and connections.
        """
        locations = []
        connections = []
        seen_connections = set()
        
        for loc in self.graph:
            coord = self.coordinates.get(loc, (0, 0))
            locations.append({
                "id": loc,
                "name": loc,
                "x": coord[0],
                "y": coord[1]
            })
            
            for neighbor, distance in self.graph[loc]:
                # Avoid duplicate connections
                conn_key = tuple(sorted([loc, neighbor]))
                if conn_key not in seen_connections:
                    seen_connections.add(conn_key)
                    blocked = self._is_path_blocked(loc, neighbor)
                    connections.append({
                        "from": loc,
                        "to": neighbor,
                        "distance": distance,
                        "blocked": blocked
                    })
        
        return {
            "locations": locations,
            "connections": connections,
            "blocked_count": len(self.blocked_paths)
        }


# Singleton instance for shared use
_navigator_instance: Optional[StationNavigator] = None


def get_navigator() -> StationNavigator:
    """Get the shared navigator instance"""
    global _navigator_instance
    if _navigator_instance is None:
        _navigator_instance = StationNavigator()
    return _navigator_instance
