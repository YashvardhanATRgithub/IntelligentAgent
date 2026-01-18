"""
Analytics - Tracks information propagation for emergent behavior analysis
"""
from typing import Dict, List, Set
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class PropagationRecord:
    """Records how information spreads between agents"""
    source_agent: str
    target_agent: str
    content_snippet: str
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = ""


class PropagationTracker:
    """Tracks how information spreads through the agent network"""
    
    def __init__(self):
        # Track who knows about each piece of information
        self.knowledge_map: Dict[str, Set[str]] = defaultdict(set)
        
        # Track propagation chain
        self.propagation_log: List[PropagationRecord] = []
        
        # Track events
        self.event_knowledge: Dict[str, Set[str]] = defaultdict(set)
    
    def record_initial_knowledge(self, event_id: str, agent_name: str, content: str):
        """Record that an agent first received information"""
        self.event_knowledge[event_id].add(agent_name)
        self.propagation_log.append(PropagationRecord(
            source_agent="SYSTEM",
            target_agent=agent_name,
            content_snippet=content[:100],
            event_id=event_id
        ))
    
    def record_propagation(self, from_agent: str, to_agent: str, content: str, event_id: str = ""):
        """Record information being passed from one agent to another"""
        # Check if this looks like it's related to a tracked event
        for eid, agents in self.event_knowledge.items():
            if from_agent in agents:
                self.event_knowledge[eid].add(to_agent)
                event_id = eid
                break
        
        self.propagation_log.append(PropagationRecord(
            source_agent=from_agent,
            target_agent=to_agent,
            content_snippet=content[:100] if content else "",
            event_id=event_id
        ))
    
    def get_event_spread(self, event_id: str) -> Dict:
        """Get analysis of how an event's information spread"""
        if event_id not in self.event_knowledge:
            return {"error": "Event not tracked"}
        
        agents_who_know = self.event_knowledge[event_id]
        
        # Build propagation chain
        chain = []
        for record in self.propagation_log:
            if record.event_id == event_id:
                chain.append({
                    "from": record.source_agent,
                    "to": record.target_agent,
                    "time": record.timestamp.isoformat(),
                    "snippet": record.content_snippet
                })
        
        return {
            "event_id": event_id,
            "total_agents_informed": len(agents_who_know),
            "agents_who_know": list(agents_who_know),
            "propagation_chain": chain
        }
    
    def get_summary(self) -> Dict:
        """Get overall propagation summary"""
        return {
            "total_propagations": len(self.propagation_log),
            "events_tracked": list(self.event_knowledge.keys()),
            "event_summaries": {
                eid: len(agents) for eid, agents in self.event_knowledge.items()
            }
        }
    
    def clear(self):
        """Clear all tracking data"""
        self.knowledge_map.clear()
        self.propagation_log.clear()
        self.event_knowledge.clear()


# Global tracker instance
propagation_tracker = PropagationTracker()
