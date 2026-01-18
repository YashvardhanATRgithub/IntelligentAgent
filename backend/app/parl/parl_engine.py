"""
PARL Engine - Orchestrates the Perception, Action, Reasoning, Learning loop
Uses Groq API for LLM reasoning
"""
import httpx
import json
import re
import random
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

from ..config import settings
from ..memory import memory_store


class PARLEngine:
    """
    PARL (Perception, Action, Reasoning, Learning) Engine
    Provides LLM-powered decision making for agents using Groq API
    """
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required. Please set it in your .env file.")
        
        self.groq_api_key = settings.GROQ_API_KEY.strip()
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.groq_model = settings.GROQ_MODEL
        print(f"ℹ️ PARL Engine initialized with Groq API ({self.groq_model})")
        
        # Async Lock for FCFS Queue (Strict Sequential Processing)
        self.lock = asyncio.Lock()
        
        # Action history tracking for anti-repetition
        self.action_history: Dict[str, List[Dict[str, str]]] = {}


    async def reason(self, agent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """R - REASONING: Use LLM to decide agent's next action"""
        prompt = self._build_agent_prompt(agent, context)
        
        # ACQUIRE LOCK (FCFS Queue)
        async with self.lock:
            for attempt in range(2):
                try:
                    result = await self._call_groq(agent, prompt)
                    # Rate limit: Groq free tier = 6000 TPM, add delay between calls
                    await asyncio.sleep(4.0)
                    
                    if result:
                        # SANITIZE: Prevent hallucinations
                        result = self._sanitize_response(result, agent, context)
                        print(f"✅ [PARL] {agent['name']} decided: {result.get('action')} ({result.get('target')})")
                        return result
                            
                except Exception as e:
                    print(f"❌ [PARL] {agent['name']} Error: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    await asyncio.sleep(1.0)

        # Fallback if both retries fail
        return self._fallback_decision(agent)

    async def _call_groq(self, agent: Dict[str, Any], prompt: str) -> Optional[Dict[str, Any]]:
        """Call Groq API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.groq_url,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 150
                }
            )
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                return self._parse_response(text)
            else:
                print(f"Groq Error {response.status_code}: {response.text}")
        return None

    def _fallback_decision(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback behavior when Groq API fails (rare)"""
        actions = ["work", "rest", "move"]
        action = random.choice(actions)
        targets = {
            "work": ["station systems", "research", "maintenance"],
            "rest": ["self"],
            "move": ["Mess Hall", "Crew Quarters", "Rec Room", "Medical Bay"]
        }
        return {
            "thought": "I should continue my routine.",
            "action": action,
            "target": random.choice(targets.get(action, ["self"])),
            "dialogue": None
        }

    def _sanitize_response(self, result: Dict[str, Any], agent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Fix hallucinations, invalid actions, and prevent repetitive loops"""
        agent_name = agent['name']
        action = result.get("action", "rest").lower()
        target = result.get("target", "") or ""
        
        # Initialize action history for this agent if needed
        if agent_name not in self.action_history:
            self.action_history[agent_name] = []
        
        history = self.action_history[agent_name]
        valid_actions = ["move", "talk", "work", "rest"]
        
        # 1. Validate Action
        if action not in valid_actions:
            if action == "check":
                result["action"] = "work"
                action = "work"
                result["thought"] += " (Corrected from check)"
            else:
                result["action"] = "rest"
                action = "rest"
                result["thought"] += f" (Invalid action '{action}' corrected)"
        
        # 2. Prevent Ghost Talking (Rohan, Kabir, etc.)
        if action == "talk":
            valid_names = context.get("all_agent_names", [])
            is_valid = False
            for name in valid_names:
                if target.lower() in name.lower() or name.lower() in target.lower():
                    is_valid = True
                    break
            
            if not is_valid:
                result["action"] = "work"
                action = "work"
                result["target"] = "station duties"
                result["thought"] += f" (Target '{target}' not found, working instead)"
        
        # 3. Fix 'Work on Person'
        if action == "work" and any(x in target.lower() for x in ["vikram", "ananya", "tara", "priya", "dr.", "cdr."]):
            result["action"] = "talk"
            action = "talk"
            result["thought"] += " (Changed work-on-person to talk)"
        
        # 4. ANTI-REPETITION: Check for talk loops (same target 2+ times recently)
        if action == "talk":
            recent_talk_targets = [h.get('target', '').lower() for h in history[-3:] if h.get('action') == 'talk']
            target_lower = target.lower() if target else ""
            
            matching_talks = sum(1 for t in recent_talk_targets if t and target_lower and (t in target_lower or target_lower in t))
            if matching_talks >= 2:
                result["action"] = "work"
                action = "work"
                result["target"] = "regular duties"
                result["thought"] += " (Breaking conversation loop - time to work)"
                print(f"🔄 [PARL] {agent_name} breaking talk loop with {target}")
        
        # 5. ANTI-REPETITION: Force diversity if stuck (same action 4+ times)
        if len(history) >= 4:
            recent_actions = [h.get('action') for h in history[-4:]]
            if all(a == action for a in recent_actions):
                alternative_actions = [a for a in valid_actions if a != action]
                new_action = random.choice(alternative_actions)
                result["action"] = new_action
                result["thought"] += f" (Diversified from {action} pattern)"
                print(f"🎲 [PARL] {agent_name} forced diversity: {action} → {new_action}")
                action = new_action
                
                if new_action == "move":
                    locations = ["Mess Hall", "Rec Room", "Medical Bay", "Crew Quarters"]
                    result["target"] = random.choice(locations)
                elif new_action == "work":
                    result["target"] = "station systems"
                elif new_action == "rest":
                    result["target"] = "self"
        
        # 6. Record this action in history (keep last 10)
        self.action_history[agent_name].append({
            "action": action,
            "target": target
        })
        self.action_history[agent_name] = self.action_history[agent_name][-10:]
        
        return result

    def _build_agent_prompt(self, agent: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Get agent's recent memories
        memories = memory_store.retrieve_memories(
            agent_name=agent['name'],
            query=context.get('current_situation', 'current events'),
            limit=3
        )
        memories_text = "\n".join([f"- {m.get('content', '')}" for m in memories]) if memories else "None"
        
        # Get other agents at location
        agents_here = context.get('agents_at_location', [])
        agents_text = ", ".join([f"{a['name']} ({a.get('role', 'crew')})" for a in agents_here if a['name'] != agent['name']]) or "None"
        
        # Check for immediate recent messages
        recent_incoming = []
        for m in memories:
            if "said:" in m.get('content', '').lower() and "You said" not in m.get('content', ''):
                 recent_incoming.append(m.get('content'))

        priority_instruction = ""
        if recent_incoming:
            priority_instruction = f"URGENT: YOU WERE JUST TOLD: '{recent_incoming[0]}'. REPLY TO THIS."
        elif memories and "Said:" in memories[0].get('content', ''):
             priority_instruction = "NOTE: You just spoke. Wait for them to reply, or do some work. DO NOT talk again immediately."

        return f"""You are {agent['name']}, a {agent.get('role', 'crew member')} at Aryabhata Station.
CREW: Cdr. Vikram Sharma, Dr. Ananya Iyer, TARA, Priya Nair, Aditya Reddy, Dr. Arjun Menon, Kabir Saxena, Rohan Pillai.
LOCATION: {agent.get('location', 'Unknown')}
PEOPLE HERE: {agents_text}
MEMORIES: {memories_text}

{priority_instruction}

IMPORTANT RULES:
- VARY your actions! Don't do the same thing repeatedly.
- If you just talked, do work or move next.
- Reply to someone ONCE, then move on to other activities.
- Explore different locations: Mission Control, Agri Lab, Mess Hall, Rec Room, Crew Quarters, Medical Bay.

ACTIONS: move/talk/work/rest

JSON ONLY:
{{"thought": "why", "action": "move|talk|work|rest", "target": "name/place/task", "dialogue": "if talking"}}"""
    

    def _parse_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into action dict (Strict JSON)"""
        try:
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
                
        except Exception:
            pass
        return None

    async def generate_reflection(self, agent: Dict[str, Any]) -> Optional[str]:
        return None  # Disabled for now

    def perceive(self, agent: Dict[str, Any], environment: Dict[str, Any]) -> List[str]:
        """P - PERCEPTION: Create observations"""
        observations = []
        for other in environment.get('agents_at_location', []):
            if other['name'] != agent['name']:
                observations.append(f"Saw {other['name']}")
        return observations
    
    def learn(self, agent: Dict[str, Any], action_result: Dict[str, Any]) -> None:
        """L - LEARNING: Store outcome"""
        if action_result.get('action') == 'talk':
             memory_store.add_memory(
                agent_name=agent['name'],
                content=f"Said: {action_result.get('dialogue')}",
                memory_type="action",
                importance=5.0
            )


# Global PARL engine instance
parl_engine = PARLEngine()
