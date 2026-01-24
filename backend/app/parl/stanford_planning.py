"""
Stanford-Level Planning Module
Multi-call LLM planning for granular agent behavior.

Inspired by Stanford's generative_agents/plan.py but adapted for our architecture.
Features:
- Wake-up hour generation
- Daily plan generation with LLM
- Task decomposition into 5-15 min subtasks
- Hierarchical planning (day -> hour -> task)
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
import httpx
import json
import re

from ..config import settings


@dataclass
class PlannedTask:
    """A single planned task with time and details"""
    start_hour: int
    start_minute: int
    duration_minutes: int
    activity: str
    location: str
    subtasks: List[str] = None
    
    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []


@dataclass 
class DailyAgentPlan:
    """Full day plan for an agent"""
    agent_name: str
    agent_role: str
    wake_hour: int
    sleep_hour: int
    activities: List[PlannedTask]
    generated_at: datetime = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()
    
    def get_current_activity(self, current_hour: int, current_minute: int) -> Optional[PlannedTask]:
        """Get what the agent should be doing right now"""
        current_time_mins = current_hour * 60 + current_minute
        for task in self.activities:
            task_start = task.start_hour * 60 + task.start_minute
            task_end = task_start + task.duration_minutes
            if task_start <= current_time_mins < task_end:
                return task
        return None


class StanfordPlanner:
    """
    Stanford-level planning with multiple LLM calls.
    
    Key difference from basic planning:
    - Generates wake/sleep times dynamically
    - Creates full daily schedule via LLM
    - Decomposes each task into subtasks
    - Adapts plan based on personality/role
    """
    
    def __init__(self):
        self.plans: Dict[str, DailyAgentPlan] = {}
        self.llm_provider = settings.LLM_PROVIDER.lower()
        
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Route to appropriate LLM provider"""
        if self.llm_provider == "ollama":
            return await self._call_ollama(prompt)
        else:
            return await self._call_groq(prompt)
    
    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call local Ollama - no rate limits"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{settings.OLLAMA_HOST}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 500}
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
            except Exception as e:
                print(f"Ollama planning error: {e}")
        return None
    
    async def _call_groq(self, prompt: str) -> Optional[str]:
        """Call Groq API for planning"""
        if not settings.GROQ_API_KEY:
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.GROQ_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"Groq planning error: {e}")
        return None

    async def generate_wake_up_hour(self, agent: Dict[str, Any]) -> int:
        """
        Stanford-level: LLM generates personalized wake time based on role/personality.
        
        Example: A commander wakes at 5am, a scientist at 7am, night shift at 10pm.
        """
        prompt = f"""You are {agent['name']}, a {agent['role']} at a lunar research station.

Based on your role and duties, at what hour do you typically wake up?
Consider:
- Commanders and pilots often wake early (5-6am)
- Scientists may wake later (7-8am)
- Medical staff varies by shift
- Engineers depend on maintenance schedules

Respond with ONLY a number between 0 and 23 (24-hour format).
Example: 6"""

        response = await self._call_llm(prompt)
        if response:
            try:
                # Extract number from response
                numbers = re.findall(r'\d+', response)
                if numbers:
                    hour = int(numbers[0])
                    if 0 <= hour <= 23:
                        print(f"☀️ [Plan] {agent['name']} wakes at {hour}:00")
                        return hour
            except:
                pass
        
        # Fallback based on role
        role = agent.get('role', '').lower()
        if 'commander' in role or 'pilot' in role:
            return 5
        elif 'medical' in role or 'doctor' in role:
            return 6
        else:
            return 7

    async def generate_daily_plan(self, agent: Dict[str, Any], wake_hour: int) -> List[PlannedTask]:
        """
        Stanford-level: LLM generates full day schedule.
        
        This is the key Stanford innovation - the LLM creates the entire day's plan,
        not just responding to immediate situations.
        """
        prompt = f"""You are {agent['name']}, a {agent['role']} at Aryabhata Station on the Moon.

You wake up at {wake_hour}:00. Create your daily schedule.

Available locations:
- Mission Control (command center)
- Agri Lab (food production)
- Medical Bay (health & fitness)
- Crew Quarters (living spaces)
- Mess Hall (dining)
- Rec Room (recreation)
- Mining Tunnel (resource extraction)
- Comms Tower (communications)

Create a realistic schedule with 8-12 activities. Format EXACTLY like this:
7:00 - Wake up, morning hygiene (Crew Quarters) - 30 min
7:30 - Breakfast (Mess Hall) - 30 min
8:00 - Morning briefing (Mission Control) - 60 min
...

Each line MUST have: TIME - ACTIVITY (LOCATION) - DURATION
End day with sleep around 22:00-23:00."""

        response = await self._call_llm(prompt)
        activities = []
        
        if response:
            activities = self._parse_daily_plan(response, agent['name'])
        
        # Fallback if LLM fails or returns empty
        if not activities:
            activities = self._generate_template_plan(agent, wake_hour)
        
        print(f"📋 [Plan] {agent['name']} has {len(activities)} activities planned")
        return activities

    def _parse_daily_plan(self, response: str, agent_name: str) -> List[PlannedTask]:
        """Parse LLM response into PlannedTask objects"""
        activities = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Try to parse: "7:00 - Activity (Location) - 30 min"
            try:
                # Extract time
                time_match = re.match(r'(\d{1,2}):(\d{2})', line)
                if not time_match:
                    continue
                
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                
                # Extract location (in parentheses)
                loc_match = re.search(r'\(([^)]+)\)', line)
                location = loc_match.group(1) if loc_match else "Crew Quarters"
                
                # Extract duration
                dur_match = re.search(r'(\d+)\s*min', line)
                duration = int(dur_match.group(1)) if dur_match else 60
                
                # Extract activity (between - and location)
                parts = line.split('-')
                if len(parts) >= 2:
                    activity = parts[1].strip()
                    # Remove location from activity
                    activity = re.sub(r'\([^)]+\)', '', activity).strip()
                else:
                    activity = "General duties"
                
                activities.append(PlannedTask(
                    start_hour=hour,
                    start_minute=minute,
                    duration_minutes=duration,
                    activity=activity,
                    location=location
                ))
                
            except Exception as e:
                continue
        
        return activities

    def _generate_template_plan(self, agent: Dict[str, Any], wake_hour: int) -> List[PlannedTask]:
        """Fallback template-based plan"""
        role = agent.get('role', '').lower()
        
        # Base schedule
        activities = [
            PlannedTask(wake_hour, 0, 30, "Morning routine", "Crew Quarters"),
            PlannedTask(wake_hour, 30, 30, "Breakfast", "Mess Hall"),
            PlannedTask(wake_hour + 1, 0, 60, "Morning briefing", "Mission Control"),
        ]
        
        # Role-specific work blocks
        if 'commander' in role:
            activities.extend([
                PlannedTask(wake_hour + 2, 0, 120, "Station oversight", "Mission Control"),
                PlannedTask(wake_hour + 4, 0, 60, "Crew coordination", "Mission Control"),
            ])
        elif 'doctor' in role or 'medical' in role:
            activities.extend([
                PlannedTask(wake_hour + 2, 0, 120, "Medical checks", "Medical Bay"),
                PlannedTask(wake_hour + 4, 0, 60, "Health reports", "Medical Bay"),
            ])
        elif 'scientist' in role or 'research' in role:
            activities.extend([
                PlannedTask(wake_hour + 2, 0, 120, "Research experiments", "Agri Lab"),
                PlannedTask(wake_hour + 4, 0, 60, "Data analysis", "Mission Control"),
            ])
        else:
            activities.extend([
                PlannedTask(wake_hour + 2, 0, 120, "Station duties", "Mission Control"),
                PlannedTask(wake_hour + 4, 0, 60, "Maintenance work", "Crew Quarters"),
            ])
        
        # Afternoon/Evening
        activities.extend([
            PlannedTask(12, 0, 60, "Lunch break", "Mess Hall"),
            PlannedTask(13, 0, 180, "Afternoon work", "Mission Control"),
            PlannedTask(17, 0, 60, "Exercise", "Medical Bay"),
            PlannedTask(18, 0, 60, "Dinner", "Mess Hall"),
            PlannedTask(19, 0, 120, "Free time", "Rec Room"),
            PlannedTask(21, 0, 60, "Evening routine", "Crew Quarters"),
            PlannedTask(22, 0, 480, "Sleep", "Crew Quarters"),
        ])
        
        return activities

    async def generate_task_decomp(self, task: PlannedTask, agent: Dict[str, Any]) -> List[str]:
        """
        Stanford-level: Decompose a task into 5-15 minute subtasks.
        
        This adds granularity to agent behavior - instead of "working for 2 hours",
        the agent does specific subtasks.
        """
        if task.duration_minutes < 30:
            return [task.activity]  # No decomposition for short tasks
        
        prompt = f"""You are {agent['name']}, a {agent['role']}.

You need to: {task.activity}
Location: {task.location}
Total time: {task.duration_minutes} minutes

Break this into smaller steps (5-15 minutes each).
Format: One step per line, just the action.

Example for "Morning briefing (60 min)":
- Review overnight status reports
- Check equipment status logs
- Brief team on today's priorities
- Assign daily tasks to crew
- Answer questions from crew

Now break down: {task.activity}"""

        response = await self._call_llm(prompt)
        subtasks = []
        
        if response:
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean up the line
                    line = re.sub(r'^[-*•\d.)\s]+', '', line).strip()
                    if line:
                        subtasks.append(line)
        
        # Fallback: simple subdivision
        if not subtasks:
            num_subtasks = max(2, task.duration_minutes // 20)
            for i in range(num_subtasks):
                subtasks.append(f"{task.activity} - part {i+1}")
        
        task.subtasks = subtasks
        return subtasks

    async def create_full_plan(self, agent: Dict[str, Any]) -> DailyAgentPlan:
        """
        Stanford-level: Generate complete daily plan with all LLM calls.
        
        This is the main entry point that orchestrates:
        1. Wake-up hour generation
        2. Daily schedule generation
        3. Task decomposition for major activities
        """
        print(f"🗓️ [Stanford Plan] Generating full plan for {agent['name']}...")
        
        # 1. Generate wake-up hour
        wake_hour = await self.generate_wake_up_hour(agent)
        
        # 2. Generate daily activities
        activities = await self.generate_daily_plan(agent, wake_hour)
        
        # 3. Decompose major tasks (>= 60 min)
        for task in activities:
            if task.duration_minutes >= 60:
                await self.generate_task_decomp(task, agent)
        
        # Create and store plan
        plan = DailyAgentPlan(
            agent_name=agent['name'],
            agent_role=agent.get('role', 'crew'),
            wake_hour=wake_hour,
            sleep_hour=22,  # Default sleep time
            activities=activities
        )
        
        self.plans[agent['name']] = plan
        return plan

    def get_plan(self, agent_name: str) -> Optional[DailyAgentPlan]:
        """Get cached plan for an agent"""
        return self.plans.get(agent_name)


# Global planner instance
stanford_planner = StanfordPlanner()
