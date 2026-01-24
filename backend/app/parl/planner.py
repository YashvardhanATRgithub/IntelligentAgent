"""
Daily Planner - Stanford-level hourly plan decomposition

Based on Stanford's plan.py (~42KB) from generative_agents.

Key improvements over basic planning:
1. Hourly decomposition: Break major activities into 5-15 minute tasks
2. Reactive re-planning: Adjust plans when events occur
3. LLM-based dynamic planning: Generate personalized plans
4. Priority management: Handle interrupts gracefully
5. Plan tracking: Record deviations and completions
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class TaskStatus(Enum):
    """Status of a planned task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    INTERRUPTED = "interrupted"


@dataclass
class HourlyTask:
    """
    Fine-grained task within an hourly block.
    Stanford-style decomposition into 5-15 minute chunks.
    """
    start_time: str          # "08:00"
    duration_minutes: int    # 5-60 minutes
    task: str               # What to do
    location: str           # Where
    priority: int = 5       # 1-10
    status: TaskStatus = TaskStatus.PENDING
    
    # Tracking
    actual_start: Optional[str] = None
    actual_end: Optional[str] = None
    deviation_reason: Optional[str] = None
    
    def end_time(self) -> str:
        """Calculate expected end time"""
        h, m = map(int, self.start_time.split(":"))
        total_mins = h * 60 + m + self.duration_minutes
        return f"{total_mins // 60:02d}:{total_mins % 60:02d}"


@dataclass
class PlannedActivity:
    """A major activity block in an agent's schedule"""
    time_slot: str              # e.g., "08:00"
    activity: str               # e.g., "work", "talk", "move"
    location: str               # e.g., "Agri Lab"
    description: str            # e.g., "Morning plant checks"
    priority: int = 5           # 1-10, higher = more important
    completed: bool = False
    
    # Hourly decomposition (Stanford-style)
    subtasks: List[HourlyTask] = field(default_factory=list)
    
    # Tracking
    time_spent_minutes: int = 0
    interruptions: int = 0


@dataclass
class DailyPlan:
    """An agent's complete plan for the day"""
    agent_name: str
    date: str
    activities: List[PlannedActivity] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    # Metadata
    personality_note: str = ""       # How personality affects plan
    current_goals: List[str] = field(default_factory=list)
    
    # Re-planning tracking
    replan_count: int = 0
    last_replan_reason: str = ""


class DailyPlanner:
    """
    Stanford-level planning with hourly decomposition.
    
    Features:
    - Decompose activities into 5-15 minute subtasks
    - Dynamic LLM-based plan generation
    - Reactive re-planning on interrupts
    - Track plan adherence and deviations
    """
    
    def __init__(self):
        self.plans: Dict[str, DailyPlan] = {}
        
        # Role-based schedule templates
        self.role_schedules = {
            "Mission Commander": [
                ("06:00", "rest", "Crew Quarters", "Wake up and prepare", 3),
                ("07:00", "move", "Mess Hall", "Breakfast with crew", 5),
                ("08:00", "work", "Mission Control", "Morning briefing and status", 9),
                ("10:00", "move", "Various", "Station inspection rounds", 7),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Mission Control", "Communications with Earth", 9),
                ("15:00", "talk", "Various", "Check on crew members", 7),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Crew meeting or relaxation", 4),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "Botanist/Life Support": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast", 5),
                ("08:00", "work", "Agri Lab", "Morning plant checks", 8),
                ("10:00", "work", "Agri Lab", "Experiment maintenance", 8),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Agri Lab", "Afternoon experiments", 8),
                ("15:00", "work", "Agri Lab", "Data recording and analysis", 7),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Relaxation", 4),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "AI Assistant": [
                ("00:00", "work", "Mission Control", "Night systems monitoring", 6),
                ("06:00", "work", "Mission Control", "Morning diagnostics", 8),
                ("08:00", "work", "Mission Control", "Assist crew with tasks", 7),
                ("12:00", "work", "Mission Control", "Midday status report", 7),
                ("15:00", "work", "Various", "Mobile assistance", 6),
                ("18:00", "work", "Mission Control", "Evening systems check", 8),
            ],
            "Crew Welfare Officer": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast - observe crew mood", 6),
                ("08:00", "talk", "Various", "Individual check-ins", 9),
                ("10:00", "work", "Medical Bay", "Mental health documentation", 7),
                ("12:00", "move", "Mess Hall", "Lunch with crew", 6),
                ("14:00", "talk", "Various", "Counseling sessions", 9),
                ("16:00", "work", "Rec Room", "Organize group activity", 7),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Facilitate group bonding", 7),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "Systems Engineer": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast", 5),
                ("08:00", "work", "Mission Control", "Systems diagnostics", 8),
                ("10:00", "work", "Various", "Maintenance rounds", 8),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Crew Quarters", "Life support maintenance", 9),
                ("15:00", "work", "Mission Control", "Repairs and updates", 8),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Relaxation", 4),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "Flight Surgeon": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast", 5),
                ("08:00", "work", "Medical Bay", "Medical supplies check", 7),
                ("09:00", "talk", "Medical Bay", "Crew health check-ups", 9),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Medical Bay", "Medical records update", 7),
                ("15:00", "work", "Medical Bay", "Health monitoring", 8),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Relaxation", 4),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "Geologist/Mining Lead": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast", 5),
                ("08:00", "work", "Mining Tunnel", "Mining operations start", 8),
                ("10:00", "work", "Mining Tunnel", "Sample collection", 8),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Mining Tunnel", "Afternoon mining", 8),
                ("16:00", "work", "Agri Lab", "Sample analysis", 7),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Relaxation", 4),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
            "Communications Officer": [
                ("06:00", "rest", "Crew Quarters", "Wake up", 3),
                ("07:00", "move", "Mess Hall", "Breakfast", 5),
                ("08:00", "work", "Comms Tower", "Morning Earth transmission", 9),
                ("10:00", "work", "Comms Tower", "Equipment maintenance", 7),
                ("12:00", "move", "Mess Hall", "Lunch", 5),
                ("13:00", "work", "Comms Tower", "Afternoon communications", 8),
                ("15:00", "talk", "Various", "Relay messages to crew", 8),
                ("18:00", "move", "Mess Hall", "Dinner", 5),
                ("19:00", "move", "Rec Room", "Social time", 5),
                ("22:00", "rest", "Crew Quarters", "Sleep", 8),
            ],
        }
        
        # Subtask templates for decomposition
        self.subtask_templates = {
            "work": [
                ("Review today's objectives", 5),
                ("Main task execution", 30),
                ("Documentation/logging", 10),
                ("Break/transition", 5),
            ],
            "talk": [
                ("Find the person", 5),
                ("Conversation", 20),
                ("Follow-up notes", 5),
            ],
            "move": [
                ("Travel to location", 5),
                ("Arrive and settle", 5),
            ],
            "rest": [
                ("Personal time", 30),
            ],
        }
    
    def create_plan_for_agent(
        self, 
        agent_name: str, 
        role: str, 
        date: str = None,
        personality_traits: Dict[str, float] = None,
        current_goals: List[str] = None
    ) -> DailyPlan:
        """
        Create a daily plan with hourly decomposition.
        
        Args:
            agent_name: Agent's name
            role: Agent's role
            date: Plan date (defaults to today)
            personality_traits: Optional personality for customization
            current_goals: Optional goals to prioritize
        
        Returns:
            DailyPlan with decomposed hourly tasks
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        activities = []
        schedule = self.role_schedules.get(role, self.role_schedules["Systems Engineer"])
        
        for time_slot, activity, location, description, priority in schedule:
            planned = PlannedActivity(
                time_slot=time_slot,
                activity=activity,
                location=location,
                description=description,
                priority=priority
            )
            
            # Decompose into hourly subtasks (Stanford-style)
            planned.subtasks = self._decompose_activity(
                time_slot, activity, location, description, priority
            )
            
            activities.append(planned)
        
        # Create personality note
        personality_note = ""
        if personality_traits:
            if personality_traits.get("conscientiousness", 0.5) > 0.7:
                personality_note = "Very organized - follows schedule strictly"
            elif personality_traits.get("openness", 0.5) > 0.7:
                personality_note = "Flexible - may deviate for interesting opportunities"
        
        plan = DailyPlan(
            agent_name=agent_name,
            date=date,
            activities=activities,
            personality_note=personality_note,
            current_goals=current_goals or []
        )
        
        self.plans[agent_name] = plan
        return plan
    
    def _decompose_activity(
        self,
        start_time: str,
        activity_type: str,
        location: str,
        description: str,
        priority: int
    ) -> List[HourlyTask]:
        """
        Decompose major activity into 5-15 minute subtasks.
        This is the key Stanford-style feature.
        """
        subtasks = []
        template = self.subtask_templates.get(activity_type, self.subtask_templates["work"])
        
        current_h, current_m = map(int, start_time.split(":"))
        current_minutes = current_h * 60 + current_m
        
        for task_desc, duration in template:
            # Format time
            h = current_minutes // 60
            m = current_minutes % 60
            time_str = f"{h:02d}:{m:02d}"
            
            # Contextualize task description
            if "{location}" in task_desc or "Main task" in task_desc:
                task_desc = task_desc.replace("Main task execution", description)
            
            subtask = HourlyTask(
                start_time=time_str,
                duration_minutes=duration,
                task=f"{task_desc} ({description})" if "Main task" not in task_desc else description,
                location=location,
                priority=priority
            )
            subtasks.append(subtask)
            
            current_minutes += duration
        
        return subtasks
    
    def get_current_planned_activity(
        self, 
        agent_name: str, 
        current_time: str
    ) -> Optional[PlannedActivity]:
        """Get what the agent should be doing at the current time"""
        if agent_name not in self.plans:
            return None
        
        plan = self.plans[agent_name]
        current_minutes = self._time_to_minutes(current_time)
        
        best_activity = None
        best_time = -1
        
        for activity in plan.activities:
            activity_minutes = self._time_to_minutes(activity.time_slot)
            if activity_minutes <= current_minutes and activity_minutes > best_time:
                best_time = activity_minutes
                best_activity = activity
        
        return best_activity
    
    def get_current_subtask(
        self,
        agent_name: str,
        current_time: str
    ) -> Optional[HourlyTask]:
        """
        Get the specific subtask the agent should be doing now.
        This provides 5-15 minute granularity.
        """
        activity = self.get_current_planned_activity(agent_name, current_time)
        if not activity or not activity.subtasks:
            return None
        
        current_minutes = self._time_to_minutes(current_time)
        
        for subtask in activity.subtasks:
            start_mins = self._time_to_minutes(subtask.start_time)
            end_mins = start_mins + subtask.duration_minutes
            
            if start_mins <= current_minutes < end_mins:
                return subtask
        
        return activity.subtasks[-1] if activity.subtasks else None
    
    def replan_from_event(
        self,
        agent_name: str,
        event_description: str,
        current_time: str,
        event_priority: int = 8
    ) -> bool:
        """
        Reactive re-planning when an important event occurs.
        
        Args:
            agent_name: Agent to replan for
            event_description: What happened
            current_time: Current simulation time
            event_priority: How important is this event
        
        Returns:
            True if plan was modified
        """
        if agent_name not in self.plans:
            return False
        
        plan = self.plans[agent_name]
        current_activity = self.get_current_planned_activity(agent_name, current_time)
        
        if not current_activity:
            return False
        
        # Only interrupt if event is higher priority
        if event_priority <= current_activity.priority:
            return False
        
        # Mark current activity as interrupted
        current_activity.interruptions += 1
        
        # Mark current subtask as interrupted
        subtask = self.get_current_subtask(agent_name, current_time)
        if subtask:
            subtask.status = TaskStatus.INTERRUPTED
            subtask.deviation_reason = event_description
        
        # Record replan
        plan.replan_count += 1
        plan.last_replan_reason = event_description
        
        return True
    
    async def generate_dynamic_plan(
        self,
        agent_name: str,
        agent_role: str,
        personality: Dict[str, float],
        recent_events: List[str],
        llm_client: Any
    ) -> Optional[DailyPlan]:
        """
        Use LLM to generate a personalized plan (Stanford-style).
        
        This generates a truly dynamic plan based on personality,
        recent events, and goals.
        """
        if not llm_client:
            return self.create_plan_for_agent(agent_name, agent_role)
        
        prompt = f"""You are {agent_name}, a {agent_role} at ISRO's Aryabhata Station on the Moon.

Personality traits:
- Openness: {personality.get('openness', 0.5):.1f}/1.0
- Conscientiousness: {personality.get('conscientiousness', 0.5):.1f}/1.0
- Extraversion: {personality.get('extraversion', 0.5):.1f}/1.0
- Agreeableness: {personality.get('agreeableness', 0.5):.1f}/1.0
- Neuroticism: {personality.get('neuroticism', 0.5):.1f}/1.0

Recent events:
{chr(10).join('- ' + e for e in recent_events[-5:])}

Create a detailed daily schedule with 8-12 activities. Consider your personality when planning.
For each activity, provide:
- Time slot (HH:MM format)
- Activity type (work, talk, move, rest)
- Location
- Description
- Priority (1-10)

Respond in JSON format:
{{
    "activities": [
        {{"time": "06:00", "type": "rest", "location": "Crew Quarters", "description": "Wake up", "priority": 3}},
        ...
    ]
}}
"""
        
        try:
            response = await llm_client.generate_content_async(prompt)
            return self._parse_llm_plan(agent_name, response.text, personality)
        except Exception as e:
            print(f"LLM planning error for {agent_name}: {e}")
            return self.create_plan_for_agent(agent_name, agent_role)
    
    def _parse_llm_plan(
        self,
        agent_name: str,
        response_text: str,
        personality: Dict[str, float]
    ) -> DailyPlan:
        """Parse LLM response into DailyPlan"""
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                activities = []
                for act in data.get("activities", []):
                    planned = PlannedActivity(
                        time_slot=act.get("time", "08:00"),
                        activity=act.get("type", "work"),
                        location=act.get("location", "Mission Control"),
                        description=act.get("description", "Work"),
                        priority=int(act.get("priority", 5))
                    )
                    
                    # Decompose into subtasks
                    planned.subtasks = self._decompose_activity(
                        planned.time_slot,
                        planned.activity,
                        planned.location,
                        planned.description,
                        planned.priority
                    )
                    
                    activities.append(planned)
                
                plan = DailyPlan(
                    agent_name=agent_name,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    activities=activities
                )
                
                self.plans[agent_name] = plan
                return plan
                
        except Exception as e:
            print(f"Plan parse error: {e}")
        
        return None
    
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
        lines = [f"Today's plan ({plan.date}):"]
        
        for activity in plan.activities[:6]:
            status = "✓" if activity.completed else "○"
            lines.append(f"  {status} {activity.time_slot}: {activity.description} @ {activity.location}")
            
            # Include subtasks for current/next activity
            if not activity.completed and activity.subtasks:
                for subtask in activity.subtasks[:2]:
                    st_status = "→" if subtask.status == TaskStatus.IN_PROGRESS else "  "
                    lines.append(f"    {st_status} {subtask.start_time}: {subtask.task}")
        
        return "\n".join(lines)
    
    def to_dict(self, agent_name: str) -> Dict:
        """Export plan as dictionary for API"""
        if agent_name not in self.plans:
            return {}
        
        plan = self.plans[agent_name]
        return {
            "date": plan.date,
            "personality_note": plan.personality_note,
            "replan_count": plan.replan_count,
            "activities": [
                {
                    "time": a.time_slot,
                    "activity": a.activity,
                    "location": a.location,
                    "description": a.description,
                    "priority": a.priority,
                    "completed": a.completed,
                    "interruptions": a.interruptions,
                    "subtasks": [
                        {
                            "time": st.start_time,
                            "duration": st.duration_minutes,
                            "task": st.task,
                            "status": st.status.value
                        }
                        for st in a.subtasks
                    ]
                }
                for a in plan.activities
            ]
        }
    
    def get_plan_adherence(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics on how well agent follows their plan"""
        if agent_name not in self.plans:
            return {}
        
        plan = self.plans[agent_name]
        total_activities = len(plan.activities)
        completed = sum(1 for a in plan.activities if a.completed)
        interrupted = sum(a.interruptions for a in plan.activities)
        
        return {
            "total_activities": total_activities,
            "completed": completed,
            "adherence_rate": completed / total_activities if total_activities > 0 else 0,
            "total_interruptions": interrupted,
            "replan_count": plan.replan_count
        }
    
    # ========== ADVANCED EDGE CASES (Stanford-surpassing) ==========
    
    def handle_sleep_interruption(
        self,
        agent_name: str,
        current_time: str,
        interruption_reason: str,
        interruption_priority: int = 8
    ) -> Dict[str, Any]:
        """
        Handle sleep being interrupted (emergency, medical issue, etc.)
        
        Creates recovery plan:
        1. Handle the emergency
        2. Return to sleep if possible
        3. Adjust next day's start time for recovery
        """
        if agent_name not in self.plans:
            return {"status": "no_plan"}
        
        plan = self.plans[agent_name]
        current_hour = self._time_to_minutes(current_time) // 60
        
        # Check if actually in sleep period (22:00 - 06:00)
        is_sleep_time = current_hour >= 22 or current_hour < 6
        
        if not is_sleep_time:
            return {"status": "not_sleeping", "hour": current_hour}
        
        # Record the interruption
        plan.replan_count += 1
        plan.last_replan_reason = f"Sleep interrupted: {interruption_reason}"
        
        # Calculate recovery needs
        hours_of_sleep_lost = 0
        if current_hour >= 22:
            hours_of_sleep_lost = 24 - current_hour + 6
        else:
            hours_of_sleep_lost = 6 - current_hour
        
        # Create emergency handling activity
        emergency_activity = PlannedActivity(
            time_slot=current_time,
            activity="emergency",
            location="Various",
            description=f"Responding to: {interruption_reason}",
            priority=interruption_priority
        )
        emergency_activity.subtasks = [
            HourlyTask(
                start_time=current_time,
                duration_minutes=30,
                task="Assess situation",
                location="Various",
                priority=interruption_priority
            ),
            HourlyTask(
                start_time=self._add_minutes(current_time, 30),
                duration_minutes=30,
                task="Take action",
                location="Various",
                priority=interruption_priority
            )
        ]
        
        # Insert at current position
        plan.activities.append(emergency_activity)
        
        # If less than 4 hours until wake time, skip return to sleep
        return_to_sleep = hours_of_sleep_lost > 4
        
        return {
            "status": "handled",
            "sleep_interrupted": True,
            "hours_lost": hours_of_sleep_lost,
            "return_to_sleep": return_to_sleep,
            "recovery_needed": hours_of_sleep_lost > 2
        }
    
    def handle_emergency_evacuation(
        self,
        agent_names: List[str],
        emergency_type: str,
        safe_location: str = "Mission Control"
    ) -> Dict[str, Any]:
        """
        Coordinate emergency evacuation for multiple agents.
        
        1. All agents drop current tasks
        2. Move to safe location
        3. Report to commander
        """
        results = {}
        
        for agent_name in agent_names:
            if agent_name not in self.plans:
                continue
            
            plan = self.plans[agent_name]
            
            # Mark all current activities as interrupted
            for activity in plan.activities:
                if not activity.completed:
                    activity.interruptions += 1
                    for subtask in activity.subtasks:
                        if subtask.status != TaskStatus.COMPLETED:
                            subtask.status = TaskStatus.INTERRUPTED
                            subtask.deviation_reason = f"EMERGENCY: {emergency_type}"
            
            # Create emergency evacuation activity with HIGH priority
            evac_activity = PlannedActivity(
                time_slot=datetime.now().strftime("%H:%M"),
                activity="emergency",
                location=safe_location,
                description=f"EMERGENCY EVACUATION: {emergency_type}",
                priority=10  # Maximum priority
            )
            evac_activity.subtasks = [
                HourlyTask(
                    start_time=datetime.now().strftime("%H:%M"),
                    duration_minutes=5,
                    task="Immediate evacuation",
                    location=safe_location,
                    priority=10
                ),
                HourlyTask(
                    start_time=self._add_minutes(datetime.now().strftime("%H:%M"), 5),
                    duration_minutes=15,
                    task="Report status to commander",
                    location=safe_location,
                    priority=10
                ),
                HourlyTask(
                    start_time=self._add_minutes(datetime.now().strftime("%H:%M"), 20),
                    duration_minutes=30,
                    task="Await further instructions",
                    location=safe_location,
                    priority=9
                )
            ]
            
            plan.activities.append(evac_activity)
            plan.replan_count += 1
            plan.last_replan_reason = f"EMERGENCY: {emergency_type}"
            
            results[agent_name] = {
                "status": "evacuating",
                "destination": safe_location
            }
        
        return {
            "emergency_type": emergency_type,
            "agents_affected": len(results),
            "safe_location": safe_location,
            "agent_status": results
        }
    
    def retry_failed_task(
        self,
        agent_name: str,
        task_description: str,
        failure_reason: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Handle task failure with retry logic.
        
        1. Log the failure
        2. Determine if retry is possible
        3. Schedule retry with appropriate delay
        """
        if agent_name not in self.plans:
            return {"status": "no_plan"}
        
        plan = self.plans[agent_name]
        
        # Track retries per task (simple in-memory tracking)
        if not hasattr(self, '_retry_counts'):
            self._retry_counts = {}
        
        task_key = f"{agent_name}:{task_description}"
        current_retries = self._retry_counts.get(task_key, 0)
        
        if current_retries >= max_retries:
            return {
                "status": "max_retries_exceeded",
                "retries": current_retries,
                "action": "escalate_to_commander"
            }
        
        # Increment retry count
        self._retry_counts[task_key] = current_retries + 1
        
        # Schedule retry with exponential backoff (5, 15, 45 minutes)
        delay_minutes = 5 * (3 ** current_retries)
        retry_time = self._add_minutes(datetime.now().strftime("%H:%M"), delay_minutes)
        
        # Create retry activity
        retry_activity = PlannedActivity(
            time_slot=retry_time,
            activity="work",
            location="Various",
            description=f"RETRY ({current_retries + 1}/{max_retries}): {task_description}",
            priority=7
        )
        
        plan.activities.append(retry_activity)
        
        return {
            "status": "retry_scheduled",
            "retry_number": current_retries + 1,
            "max_retries": max_retries,
            "scheduled_time": retry_time,
            "delay_minutes": delay_minutes
        }
    
    def coordinate_multi_agent_task(
        self,
        task_name: str,
        participating_agents: List[str],
        coordinator: str,
        location: str,
        scheduled_time: str,
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Coordinate a task requiring multiple agents.
        
        1. Check all agents' availability
        2. Reserve time slots for all
        3. Handle conflicts
        """
        conflicts = []
        available_agents = []
        
        for agent_name in participating_agents:
            if agent_name not in self.plans:
                continue
            
            # Check for conflicts
            scheduled_mins = self._time_to_minutes(scheduled_time)
            current_activity = self.get_current_planned_activity(agent_name, scheduled_time)
            
            if current_activity and current_activity.priority >= 8:
                conflicts.append({
                    "agent": agent_name,
                    "conflict": current_activity.description,
                    "priority": current_activity.priority
                })
            else:
                available_agents.append(agent_name)
        
        if len(conflicts) > 0:
            # Try to find alternative time (within next 2 hours)
            for offset in [30, 60, 90, 120]:
                alt_time = self._add_minutes(scheduled_time, offset)
                new_conflicts = []
                for agent_name in participating_agents:
                    activity = self.get_current_planned_activity(agent_name, alt_time)
                    if activity and activity.priority >= 8:
                        new_conflicts.append(agent_name)
                
                if len(new_conflicts) == 0:
                    scheduled_time = alt_time
                    conflicts = []
                    available_agents = participating_agents
                    break
        
        # Schedule for all available agents
        for agent_name in available_agents:
            if agent_name not in self.plans:
                continue
            
            role = "coordinator" if agent_name == coordinator else "participant"
            
            activity = PlannedActivity(
                time_slot=scheduled_time,
                activity="coordinate",
                location=location,
                description=f"[{role.upper()}] {task_name}",
                priority=8
            )
            activity.subtasks = [
                HourlyTask(
                    start_time=scheduled_time,
                    duration_minutes=duration_minutes,
                    task=f"{task_name} ({role})",
                    location=location,
                    priority=8
                )
            ]
            
            self.plans[agent_name].activities.append(activity)
        
        return {
            "task": task_name,
            "scheduled_time": scheduled_time,
            "location": location,
            "coordinator": coordinator,
            "participants": available_agents,
            "conflicts": conflicts,
            "status": "scheduled" if len(conflicts) == 0 else "partial"
        }
    
    def regenerate_daily_plan(
        self,
        agent_name: str,
        agent_role: str,
        long_term_goals: List[str] = None
    ) -> DailyPlan:
        """
        Regenerate plan for new day, incorporating:
        1. Previous day's incomplete tasks
        2. Long-term goals
        3. Accumulated fatigue/mood
        """
        old_plan = self.plans.get(agent_name)
        
        # Gather incomplete tasks from previous day
        incomplete_tasks = []
        if old_plan:
            for activity in old_plan.activities:
                if not activity.completed and activity.priority >= 6:
                    incomplete_tasks.append({
                        "description": activity.description,
                        "priority": activity.priority
                    })
        
        # Create new plan
        new_plan = self.create_plan_for_agent(
            agent_name=agent_name,
            role=agent_role,
            current_goals=long_term_goals or []
        )
        
        # Insert high-priority incomplete tasks
        for task in incomplete_tasks[:3]:  # Max 3 carryover tasks
            carryover = PlannedActivity(
                time_slot="09:00",  # Late morning for carryover
                activity="work",
                location="Various",
                description=f"[CARRYOVER] {task['description']}",
                priority=task['priority']
            )
            new_plan.activities.insert(2, carryover)  # After wake up & breakfast
        
        # Add long-term goal progress if any
        if long_term_goals:
            goal_activity = PlannedActivity(
                time_slot="14:00",
                activity="work",
                location="Various",
                description=f"Progress on goal: {long_term_goals[0]}",
                priority=6
            )
            new_plan.activities.append(goal_activity)
        
        return new_plan
    
    def _add_minutes(self, time_str: str, minutes: int) -> str:
        """Add minutes to a time string"""
        h, m = map(int, time_str.split(":"))
        total = h * 60 + m + minutes
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"


# ========== LONG-TERM GOALS TRACKER ==========

class LongTermGoalTracker:
    """
    Track agent goals over multiple days.
    Stanford's project tracks this implicitly; we do it explicitly.
    """
    
    def __init__(self):
        self.goals: Dict[str, List[Dict]] = {}  # agent -> list of goals
        self.progress: Dict[str, Dict[str, float]] = {}  # agent -> goal -> progress
    
    def add_goal(
        self,
        agent_name: str,
        goal: str,
        deadline_days: int = 7,
        priority: int = 5
    ):
        """Add a long-term goal for an agent"""
        if agent_name not in self.goals:
            self.goals[agent_name] = []
            self.progress[agent_name] = {}
        
        goal_id = f"{agent_name}_{len(self.goals[agent_name])}"
        
        self.goals[agent_name].append({
            "id": goal_id,
            "goal": goal,
            "deadline_days": deadline_days,
            "priority": priority,
            "created": datetime.now().isoformat(),
            "status": "active"
        })
        self.progress[agent_name][goal_id] = 0.0
    
    def update_progress(self, agent_name: str, goal_id: str, progress: float):
        """Update progress (0.0 - 1.0)"""
        if agent_name in self.progress and goal_id in self.progress[agent_name]:
            self.progress[agent_name][goal_id] = min(1.0, max(0.0, progress))
            
            # Mark complete if 100%
            if self.progress[agent_name][goal_id] >= 1.0:
                for goal in self.goals.get(agent_name, []):
                    if goal["id"] == goal_id:
                        goal["status"] = "completed"
    
    def get_active_goals(self, agent_name: str) -> List[Dict]:
        """Get active goals for an agent"""
        return [
            {**g, "progress": self.progress.get(agent_name, {}).get(g["id"], 0)}
            for g in self.goals.get(agent_name, [])
            if g["status"] == "active"
        ]


# Global instances
daily_planner = DailyPlanner()
goal_tracker = LongTermGoalTracker()

