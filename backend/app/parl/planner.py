"""
Daily Planner - Generates and manages agent daily schedules
Based on Stanford Generative Agents planning system
"""
from typing import Dict, List, Optional
from datetime import datetime, time
from dataclasses import dataclass, field


@dataclass
class PlannedActivity:
    """A single planned activity in an agent's schedule"""
    time_slot: str  # e.g., "08:00"
    activity: str  # e.g., "work"
    location: str  # e.g., "Agri Lab"
    description: str  # e.g., "Check plant growth experiments"
    priority: int = 5  # 1-10, higher = more important
    completed: bool = False


@dataclass
class DailyPlan:
    """An agent's plan for the day"""
    agent_name: str
    date: str  # e.g., "2035-06-15"
    activities: List[PlannedActivity] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class DailyPlanner:
    """
    Manages agent schedules and daily planning.
    Generates plans at start of each day based on role and personality.
    """
    
    def __init__(self):
        # Store daily plans per agent
        self.plans: Dict[str, DailyPlan] = {}
        
        # Default schedules by role
        self.role_schedules = {
            "Mission Commander": [
                ("06:00", "rest", "Crew Quarters", "Wake up and prepare"),
                ("07:00", "move", "Mess Hall", "Breakfast with crew"),
                ("08:00", "work", "Mission Control", "Morning briefing and status check"),
                ("10:00", "move", "Various", "Station inspection rounds"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Mission Control", "Communications with Earth"),
                ("15:00", "talk", "Various", "Check on crew members"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Crew meeting or relaxation"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "Botanist/Life Support": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast"),
                ("08:00", "work", "Agri Lab", "Morning plant checks"),
                ("10:00", "work", "Agri Lab", "Experiment maintenance"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Agri Lab", "Afternoon experiments"),
                ("15:00", "work", "Agri Lab", "Data recording"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Relaxation"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "AI Assistant": [
                ("00:00", "work", "Mission Control", "Systems monitoring"),
                ("06:00", "work", "Mission Control", "Morning diagnostics"),
                ("08:00", "work", "Mission Control", "Assist crew with tasks"),
                ("12:00", "work", "Mission Control", "Midday status report"),
                ("18:00", "work", "Mission Control", "Evening systems check"),
            ],
            "Crew Welfare Officer": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast - observe crew mood"),
                ("08:00", "talk", "Various", "Individual check-ins"),
                ("10:00", "work", "Medical Bay", "Mental health documentation"),
                ("12:00", "move", "Mess Hall", "Lunch with crew"),
                ("14:00", "talk", "Various", "Counseling sessions"),
                ("16:00", "work", "Rec Room", "Organize activity"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Group activity"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "Systems Engineer": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast"),
                ("08:00", "work", "Mission Control", "Systems check"),
                ("10:00", "work", "Various", "Maintenance rounds"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Crew Quarters", "Life support maintenance"),
                ("15:00", "work", "Mission Control", "Repairs and updates"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Relaxation"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "Flight Surgeon": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast"),
                ("08:00", "work", "Medical Bay", "Medical supplies inventory"),
                ("09:00", "talk", "Medical Bay", "Crew health check-ups"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Medical Bay", "Medical records update"),
                ("15:00", "work", "Medical Bay", "Research and monitoring"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Relaxation"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "Geologist/Mining Lead": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast"),
                ("08:00", "work", "Mining Tunnel", "Mining operations"),
                ("10:00", "work", "Mining Tunnel", "Sample collection"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Mining Tunnel", "Afternoon mining"),
                ("16:00", "work", "Agri Lab", "Sample analysis"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Relaxation"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
            "Communications Officer": [
                ("06:00", "rest", "Crew Quarters", "Wake up"),
                ("07:00", "move", "Mess Hall", "Breakfast"),
                ("08:00", "work", "Comms Tower", "Morning Earth transmission"),
                ("10:00", "work", "Comms Tower", "Equipment maintenance"),
                ("12:00", "move", "Mess Hall", "Lunch"),
                ("13:00", "work", "Comms Tower", "Afternoon communications"),
                ("15:00", "talk", "Various", "Relay messages to crew"),
                ("18:00", "move", "Mess Hall", "Dinner"),
                ("19:00", "move", "Rec Room", "Social time"),
                ("22:00", "rest", "Crew Quarters", "Sleep"),
            ],
        }
    
    def create_plan_for_agent(self, agent_name: str, role: str, date: str = None) -> DailyPlan:
        """Create a daily plan based on agent's role"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        activities = []
        schedule = self.role_schedules.get(role, self.role_schedules["Systems Engineer"])
        
        for time_slot, activity, location, description in schedule:
            activities.append(PlannedActivity(
                time_slot=time_slot,
                activity=activity,
                location=location,
                description=description
            ))
        
        plan = DailyPlan(
            agent_name=agent_name,
            date=date,
            activities=activities
        )
        
        self.plans[agent_name] = plan
        return plan
    
    def get_current_planned_activity(self, agent_name: str, current_time: str) -> Optional[PlannedActivity]:
        """Get what the agent should be doing at the current time"""
        if agent_name not in self.plans:
            return None
        
        plan = self.plans[agent_name]
        current_minutes = self._time_to_minutes(current_time)
        
        # Find the activity for current time
        best_activity = None
        best_time = -1
        
        for activity in plan.activities:
            activity_minutes = self._time_to_minutes(activity.time_slot)
            if activity_minutes <= current_minutes and activity_minutes > best_time:
                best_time = activity_minutes
                best_activity = activity
        
        return best_activity
    
    def _time_to_minutes(self, time_str: str) -> int:
        """Convert time string (HH:MM) to minutes since midnight"""
        try:
            h, m = time_str.split(":")
            return int(h) * 60 + int(m)
        except:
            return 0
    
    def get_plan_summary(self, agent_name: str) -> str:
        """Get a text summary of agent's plan for prompts"""
        if agent_name not in self.plans:
            return "No plan for today."
        
        plan = self.plans[agent_name]
        summary = f"Today's plan ({plan.date}):\n"
        for activity in plan.activities[:5]:  # First 5 activities
            summary += f"- {activity.time_slot}: {activity.description} at {activity.location}\n"
        
        return summary
    
    def to_dict(self, agent_name: str) -> Dict:
        """Export plan as dictionary for API"""
        if agent_name not in self.plans:
            return {}
        
        plan = self.plans[agent_name]
        return {
            "date": plan.date,
            "activities": [
                {
                    "time": a.time_slot,
                    "activity": a.activity,
                    "location": a.location,
                    "description": a.description,
                    "completed": a.completed
                }
                for a in plan.activities
            ]
        }


# Global planner instance
daily_planner = DailyPlanner()
