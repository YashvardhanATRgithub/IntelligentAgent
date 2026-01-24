"""
State Manager - Save/Load simulation state like Stanford's replay system

Key features:
1. Save full simulation state to JSON
2. Load/resume from saved state
3. Snapshot system for checkpoints
4. State history for replay
5. Export for analysis
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import time


@dataclass
class SimulationSnapshot:
    """A complete snapshot of simulation state"""
    snapshot_id: str
    timestamp: datetime
    description: str
    
    # Simulation time state
    sim_time: Dict[str, Any]  # week, day, hour, minute
    
    # Agent states
    agents: List[Dict[str, Any]]
    
    # World state
    locations: Dict[str, List[Dict]]
    active_events: List[str]
    
    # Memories (summarized)
    memory_counts: Dict[str, int]
    
    # Relationships
    relationships: Dict[str, Dict[str, Dict]]
    
    # Plans
    plans: Dict[str, Dict]
    
    # Metadata
    step_count: int = 0
    is_running: bool = False


class StateManager:
    """
    Manages simulation state persistence.
    
    Features:
    - Save/load full state
    - Auto-checkpoint system
    - State history for replay
    - Export for analysis
    """
    
    def __init__(self, save_dir: str = "./data/saves"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        
        # Auto-save settings
        self.auto_save_interval = 50  # steps
        self.max_snapshots = 20
        
        # Snapshot history
        self.snapshots: List[str] = []  # List of snapshot IDs
        
        self._load_snapshot_index()
    
    def _load_snapshot_index(self):
        """Load list of existing snapshots"""
        index_path = os.path.join(self.save_dir, "snapshot_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r') as f:
                    self.snapshots = json.load(f)
            except:
                self.snapshots = []
    
    def _save_snapshot_index(self):
        """Save snapshot index"""
        index_path = os.path.join(self.save_dir, "snapshot_index.json")
        with open(index_path, 'w') as f:
            json.dump(self.snapshots, f)
    
    def create_snapshot(
        self,
        simulation,
        description: str = "Manual save"
    ) -> str:
        """
        Create a complete snapshot of the simulation.
        
        Args:
            simulation: SimulationEngine instance
            description: Human-readable description
        
        Returns:
            Snapshot ID
        """
        snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Gather agent states
        agent_states = []
        for agent in simulation.agents:
            agent_states.append({
                "name": agent.name,
                "role": agent.role,
                "location": agent.state.location,
                "activity": agent.state.activity,
                "energy": agent.state.energy,
                "mood": agent.state.mood,
                "personality": {
                    "openness": agent.personality.openness,
                    "conscientiousness": agent.personality.conscientiousness,
                    "extraversion": agent.personality.extraversion,
                    "agreeableness": agent.personality.agreeableness,
                    "neuroticism": agent.personality.neuroticism
                }
            })
        
        # Gather time state
        env = simulation.environment
        sim_time = {
            "week": env.state.week,
            "day": env.state.day,
            "hour": env.state.hour,
            "minute": env.state.minute,
            "accumulated_sim_minutes": env.state.accumulated_sim_minutes,
            "time_multiplier": env.state.time_multiplier
        }
        
        # Gather memory counts
        from ..memory import memory_store
        memory_counts = {
            agent.name: memory_store.get_memory_count(agent.name)
            for agent in simulation.agents
        }
        
        # Gather relationships
        from ..agents.relationships import relationship_manager
        relationships = {}
        for agent in simulation.agents:
            relationships[agent.name] = relationship_manager.to_dict(agent.name)
        
        # Gather plans
        from ..parl.planner import daily_planner
        plans = {}
        for agent in simulation.agents:
            plans[agent.name] = daily_planner.to_dict(agent.name)
        
        # Create snapshot
        snapshot = SimulationSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(),
            description=description,
            sim_time=sim_time,
            agents=agent_states,
            locations=env.to_dict().get("locations", {}),
            active_events=env.state.active_events,
            memory_counts=memory_counts,
            relationships=relationships,
            plans=plans,
            step_count=simulation.step_count,
            is_running=simulation.is_running
        )
        
        # Save to file
        self._save_snapshot(snapshot)
        
        # Update index
        self.snapshots.append(snapshot_id)
        if len(self.snapshots) > self.max_snapshots:
            # Remove oldest
            old_id = self.snapshots.pop(0)
            self._delete_snapshot(old_id)
        
        self._save_snapshot_index()
        
        print(f"[StateManager] Snapshot created: {snapshot_id}")
        return snapshot_id
    
    def _save_snapshot(self, snapshot: SimulationSnapshot):
        """Save snapshot to file"""
        filepath = os.path.join(self.save_dir, f"{snapshot.snapshot_id}.json")
        
        data = {
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "description": snapshot.description,
            "sim_time": snapshot.sim_time,
            "agents": snapshot.agents,
            "locations": snapshot.locations,
            "active_events": snapshot.active_events,
            "memory_counts": snapshot.memory_counts,
            "relationships": snapshot.relationships,
            "plans": snapshot.plans,
            "step_count": snapshot.step_count,
            "is_running": snapshot.is_running
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _delete_snapshot(self, snapshot_id: str):
        """Delete a snapshot file"""
        filepath = os.path.join(self.save_dir, f"{snapshot_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
    
    def load_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Load a snapshot from file"""
        filepath = os.path.join(self.save_dir, f"{snapshot_id}.json")
        
        if not os.path.exists(filepath):
            print(f"[StateManager] Snapshot not found: {snapshot_id}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"[StateManager] Error loading snapshot: {e}")
            return None
    
    def restore_snapshot(self, simulation, snapshot_id: str) -> bool:
        """
        Restore simulation from a snapshot.
        
        Args:
            simulation: SimulationEngine instance
            snapshot_id: ID of snapshot to restore
        
        Returns:
            True if successful
        """
        data = self.load_snapshot(snapshot_id)
        if not data:
            return False
        
        try:
            # Stop simulation first
            simulation.is_running = False
            
            # Restore time state
            sim_time = data.get("sim_time", {})
            simulation.environment.state.accumulated_sim_minutes = sim_time.get("accumulated_sim_minutes", 0)
            simulation.environment.state.time_multiplier = sim_time.get("time_multiplier", 1.0)
            
            # Restore agent states
            for agent_data in data.get("agents", []):
                for agent in simulation.agents:
                    if agent.name == agent_data.get("name"):
                        agent.state.location = agent_data.get("location", "Crew Quarters")
                        agent.state.activity = agent_data.get("activity", "idle")
                        agent.state.energy = agent_data.get("energy", 100)
                        agent.state.mood = agent_data.get("mood", "neutral")
                        break
            
            # Restore step count
            simulation.step_count = data.get("step_count", 0)
            
            print(f"[StateManager] Restored snapshot: {snapshot_id}")
            return True
            
        except Exception as e:
            print(f"[StateManager] Error restoring snapshot: {e}")
            return False
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots"""
        snapshots = []
        
        for snapshot_id in self.snapshots:
            filepath = os.path.join(self.save_dir, f"{snapshot_id}.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    snapshots.append({
                        "id": snapshot_id,
                        "timestamp": data.get("timestamp"),
                        "description": data.get("description"),
                        "step_count": data.get("step_count"),
                        "sim_time": data.get("sim_time", {}).get("hour", 0)
                    })
                except:
                    pass
        
        return snapshots
    
    def export_for_analysis(self, simulation, filepath: str):
        """Export complete simulation data for analysis"""
        from ..memory import memory_store
        from ..agents.relationships import relationship_manager
        
        data = {
            "export_time": datetime.now().isoformat(),
            "simulation_step": simulation.step_count,
            "agents": [],
            "all_memories": {},
            "relationships": {},
            "activity_log": simulation.activity_log[-100:]
        }
        
        for agent in simulation.agents:
            data["agents"].append({
                "name": agent.name,
                "role": agent.role,
                "personality": {
                    "openness": agent.personality.openness,
                    "conscientiousness": agent.personality.conscientiousness,
                    "extraversion": agent.personality.extraversion,
                    "agreeableness": agent.personality.agreeableness,
                    "neuroticism": agent.personality.neuroticism
                }
            })
            data["all_memories"][agent.name] = memory_store.get_recent_memories(agent.name, limit=50)
            data["relationships"][agent.name] = relationship_manager.to_dict(agent.name)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"[StateManager] Exported to: {filepath}")


# Global state manager instance
state_manager = StateManager()
