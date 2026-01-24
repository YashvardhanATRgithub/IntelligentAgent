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



class RateLimiter:
    """
    Token-aware rate limiter for Groq API.
    Tracks both RPM (Requests Per Minute) and TPM (Tokens Per Minute).
    """
    def __init__(self, rpm_limit: int = 30, tpm_limit: int = 6000):
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_timestamps = []
        self.token_timestamps = []
        self.lock = asyncio.Lock()
        
    async def wait_for_capacity(self, estimated_tokens: int = 500):
        """Wait until we have capacity for a new request"""
        async with self.lock:
            while True:
                now = datetime.now().timestamp()
                
                # 1. Clean up old timestamps (older than 60s)
                self.request_timestamps = [t for t in self.request_timestamps if now - t < 60]
                self.token_timestamps = [t for t in self.token_timestamps if now - t[1] < 60]
                
                # 2. Check RPM
                if len(self.request_timestamps) >= self.rpm_limit:
                    wait_time = 60 - (now - self.request_timestamps[0]) + 0.1
                    if wait_time > 0:
                        print(f"⏳ [RateLimit] RPM hit ({len(self.request_timestamps)} reqs). Waiting {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                        continue
                        
                
                
                # 3. Check TPM
                current_tokens = sum(t[0] for t in self.token_timestamps)
                if current_tokens + estimated_tokens > self.tpm_limit:
                    # Find how many tokens we need to free up
                    needed = (current_tokens + estimated_tokens) - self.tpm_limit
                    # Find strictly enough expired usage to proceed
                    # Simpler: just wait for the oldest token release
                    if self.token_timestamps:
                         wait_time = 60 - (now - self.token_timestamps[0][1]) + 0.1
                         if wait_time > 0:
                            print(f"⏳ [RateLimit] TPM hit ({current_tokens} tokens). Waiting {wait_time:.1f}s...")
                            await asyncio.sleep(wait_time)
                            continue
                
                # If we got here, we are good!
                self.request_timestamps.append(now)
                # We proactively reserve tokens (timestamp added at start)
                # Actual adjustment happens after request if needed, but reservation prevents spikes
                self.token_timestamps.append((estimated_tokens, now))
                break

    async def update_actual_usage(self, estimated: int, actual: int):
        """Correct the token usage after the API call finishes"""
        async with self.lock:
            # Find the reservation (simplistic matching by approx time if needed, 
            # but for now we just append the difference or trust the flow)
            # Actually, to be accurate, we should remove the estimation and add actual.
            # But simpler: just add the diff if positive.
            # Let's simple remove the last matching estimation? No, concurrency makes that hard.
            # Better strategy: The reservation stays. We won't 'refund' unused tokens to be safe,
            # but we WILL add extra if we went over.
            if actual > estimated:
                 self.token_timestamps.append((actual - estimated, datetime.now().timestamp()))


class PARLEngine:
    """
    PARL (Perception, Action, Reasoning, Learning) Engine
    Provides LLM-powered decision making for agents.
    Supports dual providers: Groq (cloud) and Ollama (local).
    """
    
    def __init__(self):
        self.llm_provider = settings.LLM_PROVIDER.lower()
        
        # Setup based on provider
        if self.llm_provider == "ollama":
            self.ollama_host = settings.OLLAMA_HOST
            self.ollama_model = settings.OLLAMA_MODEL
            print(f"🦙 PARL Engine initialized with Ollama ({self.ollama_model})")
            print(f"   Host: {self.ollama_host}")
            print(f"   ⚡ NO RATE LIMITS - Unlimited local inference!")
            # No rate limiter needed for local
            self.rate_limiter = None
        else:
            # Groq mode
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is required. Set LLM_PROVIDER=ollama for local mode.")
            
            self.groq_api_key = settings.GROQ_API_KEY.strip()
            self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
            self.groq_model = settings.GROQ_MODEL
            print(f"☁️ PARL Engine initialized with Groq API ({self.groq_model})")
            
            if "8b" in self.groq_model:
                self.rate_limiter = RateLimiter(rpm_limit=20, tpm_limit=25000)
                print(f"   Limits: 20 RPM, 25k TPM (free tier)")
            else:
                self.rate_limiter = RateLimiter(rpm_limit=5, tpm_limit=4000)
                print(f"   Limits: 5 RPM, 4k TPM (70b model)")
        
        # Async Lock for FCFS Queue
        self.lock = asyncio.Lock()
        
        # Action history tracking for anti-repetition
        self.action_history: Dict[str, List[Dict[str, str]]] = {}


    async def reason(self, agent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """R - REASONING: Use LLM to decide agent's next action"""
        prompt = self._build_agent_prompt(agent, context)
        
        # ACQUIRE LOCK (FCFS Queue)
        async with self.lock:
            for attempt in range(3):
                try:
                    # Rate limit only for Groq
                    if self.llm_provider != "ollama" and self.rate_limiter:
                        estimated_usage = 600
                        await self.rate_limiter.wait_for_capacity(estimated_usage)
                        await asyncio.sleep(random.uniform(0.5, 1.5))  # Jitter
                    
                    # Route to appropriate LLM provider
                    if self.llm_provider == "ollama":
                        result = await self._call_ollama(prompt)
                    else:
                        result = await self._call_groq(agent, prompt)
                    
                    if result:
                        result = self._sanitize_response(result, agent, context)
                        print(f"✅ [PARL] {agent['name']} decided: {result.get('action')} ({result.get('target')})")
                        return result
                            
                except Exception as e:
                    print(f"❌ [PARL] {agent['name']} Error: {type(e).__name__}: {e}")
                    if "429" in str(e) or "Rate Limit" in str(e):
                        await asyncio.sleep(5.0 * (attempt + 1))
                    else:
                        traceback.print_exc()
                        await asyncio.sleep(1)

        return self._fallback_decision(agent)
    
    async def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call local Ollama API - NO RATE LIMITS!"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 150
                        }
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("response", "")
                    return self._parse_response(text)
                else:
                    print(f"Ollama Error {response.status_code}: {response.text}")
            except httpx.ConnectError:
                print("❌ Cannot connect to Ollama. Is it running? Try: ollama serve")
            except Exception as e:
                print(f"Ollama Error: {e}")
        return None

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
                
                # Track Usage
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 600)
                # Update limiter with actuals (if we implement that fine-grained logic, for now simple is ok)
                # await self.rate_limiter.update_actual_usage(600, total_tokens) 
                
                return self._parse_response(text)
            elif response.status_code == 429:
                print(f"⚠️ Groq Rate Limit 429 Hit! Backing off...")
                raise Exception("Rate Limit Exceeded")
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
                if "thought" in result:
                    result["thought"] += " (Breaking conversation loop - time to work)"
                else:
                    result["thought"] = "Breaking conversation loop - time to work"
                print(f"🔄 [PARL] {agent_name} breaking talk loop with {target}")
        
        # 5. ANTI-REPETITION: Force diversity if stuck (same action 4+ times)
        if len(history) >= 4:
            recent_actions = [h.get('action') for h in history[-4:]]
            if all(a == action for a in recent_actions):
                alternative_actions = [a for a in valid_actions if a != action]
                new_action = random.choice(alternative_actions)
                result["action"] = new_action
                if "thought" in result:
                    result["thought"] += f" (Diversified from {action} pattern)"
                else:
                    result["thought"] = f"Diversified from {action} pattern"
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
            priority_instruction = f"URGENT: {recent_incoming[0]}. REPLY TO THIS!"
        
        # Social encouragement when others are present
        social_instruction = ""
        if agents_here and len([a for a in agents_here if a['name'] != agent['name']]) > 0:
            other_names = [a['name'] for a in agents_here if a['name'] != agent['name']]
            social_instruction = f"\n💬 SOCIAL: {', '.join(other_names)} are here with you! Consider talking to them about work, the mission, or just to chat."

        # Stanford-level: Include scheduled activity if available
        schedule_instruction = ""
        if context.get("scheduled_activity"):
            schedule_instruction = f"\n📋 SCHEDULE: You're supposed to be doing '{context['scheduled_activity']}' at {context.get('scheduled_location', 'your location')}."
            if context.get("subtasks"):
                subtasks_text = ", ".join(context["subtasks"][:2])
                schedule_instruction += f"\n   Subtasks: {subtasks_text}"

        return f"""You are {agent['name']}, a {agent.get('role', 'crew member')} at Aryabhata Station on the Moon.
CREW: Cdr. Vikram Sharma, Dr. Ananya Iyer, TARA, Priya Nair, Aditya Reddy, Dr. Arjun Menon, Kabir Saxena, Rohan Pillai.
LOCATION: {agent.get('location', 'Unknown')}
PEOPLE HERE: {agents_text}
MEMORIES: {memories_text}

{priority_instruction}
{social_instruction}
{schedule_instruction}

RULES:
1. Follow your SCHEDULE if you have one - go to the right location and do the task
2. If someone is with you, consider TALKING to them (30% of the time)
3. VARY your actions - don't repeat the same action twice in a row
4. Move to different locations to meet other crew members

LOCATIONS: Mission Control, Agri Lab, Mess Hall, Rec Room, Crew Quarters, Medical Bay, Comms Tower, Mining Tunnel
ACTIONS: move, talk, work, rest

Respond in JSON ONLY:
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

    async def generate_reflection(self, agent: Dict[str, Any], memories: List[str] = None) -> Optional[str]:
        """
        Stanford-level reflection: Generate high-level insights from recent memories.
        
        This is called periodically to help agents form beliefs and recognize patterns.
        """
        if not memories:
            return None
        
        # Build memories text
        memories_text = "\n".join([f"- {m}" for m in memories[:10]])
        
        prompt = f"""You are {agent['name']}, a {agent.get('role', 'crew member')} at a lunar station.

Recent memories and observations:
{memories_text}

Based on these experiences, generate 2-3 high-level insights or reflections.
Focus on:
- Patterns you notice in your interactions
- Things you've learned about your colleagues
- Realizations about your work or situation
- Questions or concerns that arise

Format: One insight per line, in first person ("I notice...", "I realize...", "I wonder...").
Keep each insight brief (1-2 sentences)."""

        response = await self._call_llm(prompt) if self.llm_provider == "ollama" else None
        
        # For Groq, skip reflection to save rate limit
        if self.llm_provider != "ollama" and not response:
            # Generate simple fallback reflection
            return f"I've been busy with my duties. I should stay focused on the mission."
        
        return response
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Generic LLM call for reflections and other uses"""
        if self.llm_provider == "ollama":
            result = await self._call_ollama_raw(prompt)
            return result
        return None
    
    async def _call_ollama_raw(self, prompt: str) -> Optional[str]:
        """Call Ollama and return raw text response"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 200}
                    }
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
            except:
                pass
        return None

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
