"""
Events System - Triggerable events for emergent behavior demonstration
Based on Stanford's Valentine's Day party experiment
"""
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Event:
    """A triggerable event that can be injected into the simulation"""
    id: str
    name: str
    description: str
    target_agent: str  # Agent who first receives this information
    content: str  # The information to inject into agent's memory
    trigger_time: str = ""  # When to trigger (empty = immediately)
    importance: float = 8.0  # High importance for events
    triggered: bool = False
    triggered_at: datetime = None


# Pre-defined demo events for emergent behavior testing
DEMO_EVENTS = [
    Event(
        id="crew_meeting",
        name="Emergency Crew Meeting",
        description="Commander calls for an emergency crew meeting",
        target_agent="Cdr. Vikram Sharma",
        content="I need to organize an emergency crew meeting at 15:00 in Mission Control. It's important that everyone attends. I should tell the crew members.",
        importance=9.0
    ),
    Event(
        id="supply_shortage",
        name="Supply Shortage Warning",
        description="Engineer discovers potential supply issue",
        target_agent="Aditya Reddy",
        content="I discovered that we have a potential oxygen recycler malfunction. I need to inform Commander Vikram about this urgently.",
        importance=8.5
    ),
    Event(
        id="medical_concern",
        name="Medical Concern",
        description="Doctor has a private health concern about a crew member",
        target_agent="Dr. Arjun Menon",
        content="I've noticed Commander Vikram showing signs of fatigue. I should check on him privately and maybe tell Priya about my concerns.",
        importance=7.0
    ),
    Event(
        id="discovery",
        name="Mining Discovery",
        description="Geologist makes an exciting discovery",
        target_agent="Kabir Saxena",
        content="I found unusual mineral deposits in the mining tunnel! This could be significant. I should share this news with Dr. Ananya for analysis and tell Rohan to inform Earth.",
        importance=8.0
    ),
    Event(
        id="secret_message",
        name="Secret Transmission",
        description="Communications officer receives classified info",
        target_agent="Rohan Pillai",
        content="I intercepted a classified transmission from ISRO about a potential rescue mission. I'm not supposed to share this, but maybe I should tell Commander Vikram?",
        importance=9.0
    ),
    Event(
        id="celebration",
        name="Surprise Celebration",
        description="Welfare officer plans a celebration",
        target_agent="Priya Nair",
        content="I'm planning a surprise celebration for our 100th day on the Moon tomorrow evening at 19:00 in the Rec Room. I need to secretly invite everyone without spoiling the surprise.",
        importance=7.5
    ),
]


class EventManager:
    """Manages triggerable events for the simulation"""
    
    def __init__(self):
        self.events: Dict[str, Event] = {e.id: e for e in DEMO_EVENTS}
        self.active_events: List[str] = []
        self.triggered_events: List[str] = []
    
    def get_available_events(self) -> List[Dict]:
        """Get list of events that can be triggered"""
        return [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "target_agent": e.target_agent,
                "triggered": e.triggered
            }
            for e in self.events.values()
        ]
    
    def trigger_event(self, event_id: str) -> Optional[Dict]:
        """Trigger an event - returns the memory to inject"""
        if event_id not in self.events:
            return None
        
        event = self.events[event_id]
        if event.triggered:
            return {"error": "Event already triggered"}
        
        event.triggered = True
        event.triggered_at = datetime.now()
        self.triggered_events.append(event_id)
        
        return {
            "agent": event.target_agent,
            "content": event.content,
            "importance": event.importance,
            "event_name": event.name
        }
    
    def reset_events(self):
        """Reset all events to untriggered state"""
        for event in self.events.values():
            event.triggered = False
            event.triggered_at = None
        self.triggered_events = []


# Global event manager instance
event_manager = EventManager()
