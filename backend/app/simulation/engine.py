"""
Simulation Engine - Runs the PARL loop for all agents
Uses Groq/Ollama for agent reasoning with Stanford-style features
"""
import asyncio
from typing import List, Dict, Any, Callable
from datetime import datetime
from ..agents.generative_agent import GenerativeAgent, create_all_agents
from ..agents.relationships import relationship_manager
from ..world.environment import Environment
from ..parl import parl_engine
from ..parl.planner import daily_planner
from ..memory import memory_store
from .analytics import propagation_tracker


class SimulationEngine:
    """
    Main simulation engine that orchestrates all agents
    Now powered by PARL with Ollama LLM
    """
    
    def __init__(self, on_update: Callable[[Dict[str, Any]], Any] = None):
        self.environment = Environment()
        self.agents: List[GenerativeAgent] = []
        self.is_running = False
        self.simulation_speed = 1.0  # Real-time speed (Colab is fast)
        self.on_update = on_update
        self.step_count = 0
        self.activity_log: List[Dict[str, Any]] = []
        self.use_llm = True  # Toggle for LLM reasoning
        self.reflection_interval = 5  # Generate reflections every N steps
        
    def initialize(self):
        """Initialize all agents and place them in the world"""
        self.agents = create_all_agents()
        
        # Place agents in their starting locations (8 agents)
        starting_locations = {
            "Cdr. Vikram Sharma": "Mission Control",
            "Dr. Ananya Iyer": "Agri Lab",
            "TARA": "Mission Control",
            "Priya Nair": "Mess Hall",
            "Aditya Reddy": "Crew Quarters",
            "Dr. Arjun Menon": "Medical Bay",
            "Kabir Saxena": "Mining Tunnel",
            "Rohan Pillai": "Comms Tower",
        }
        
        for agent in self.agents:
            location = starting_locations.get(agent.name, "Crew Quarters")
            agent.state.location = location
            self.environment.move_agent(agent.id, agent.name, "", location)
        
        # Initialize relationships between all agents
        agent_names = [a.name for a in self.agents]
        relationship_manager.initialize_relationships(agent_names)
        
        # Create daily plans for each agent
        for agent in self.agents:
            daily_planner.create_plan_for_agent(agent.name, agent.role)
        
        print(f"ℹ️ Initialized {len(self.agents)} agents with relationships and daily plans")
        
        return self.get_state()
    
    async def start(self):
        """Start the simulation loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.initialize()
        
        # Send initial state
        await self._broadcast_update({
            "type": "simulation_started",
            "message": "Simulation started with LLM-powered agents",
            "state": self.get_state()
        })

        # CRITICAL: Send immediate state update so UI is live while LLM loads
        await self._broadcast_update({
            "type": "state_update",
            "state": self.get_state()
        })
        
        # WARMUP: Brief pause to ensure WebSocket connections are established
        # Reduced from 2.0s to 0.3s for faster startup
        await asyncio.sleep(0.3)
        await self._broadcast_update({
            "type": "state_update",
            "state": self.get_state()
        })
        
        # Start the simulation loop
        asyncio.create_task(self._simulation_loop())
    
    async def stop(self):
        """Stop the simulation"""
        self.is_running = False
        await self._broadcast_update({
            "type": "simulation_stopped",
            "message": "Simulation paused"
        })
    
    async def _simulation_loop(self):
        """Main simulation loop - runs PARL for each agent"""
        while self.is_running:
            self.step_count += 1
            
            # Advance world time
            self.environment.step()
            
            # Process each agent - Fast & Parallel-ish (No artificial delay)
            for agent in self.agents:
                if not self.is_running:
                    break
                
                try:
                    # Get environment from agent's perspective
                    env_state = self.environment.get_environment_for_agent(agent.state.location)
                    
                    # Add other agents at this location
                    env_state["agents_at_location"] = [
                        {"name": a.name, "role": a.role}
                        for a in self.agents
                        if a.state.location == agent.state.location and a.id != agent.id
                    ]
                    
                    # Run PARL step (Pure LLM - No Fallback)
                    result = await self._run_parl_step(agent, env_state)
                    
                    # Log activity
                    activity = {
                        "time": self.environment.state.time_string,
                        "agent": agent.name,
                        "action": result.get("action", "rest"),
                        "details": result.get("details", ""),
                        "thought": result.get("thought", ""),
                        "location": agent.state.location
                    }
                    self.activity_log.append(activity)
                    
                    # Broadcast update
                    await self._broadcast_update({
                        "type": "agent_action",
                        "activity": activity,
                        "agent_state": {
                            "id": agent.id,
                            "name": agent.name,
                            "location": agent.state.location,
                            "activity": agent.state.activity,
                            "mood": agent.state.mood
                        }
                    })
                    
                except Exception as e:
                    print(f"Error processing agent {agent.name}: {e}")
                
                # Lock handles timing now. No sleep needed.
            
            # Send full state update
            await self._broadcast_update({
                "type": "state_update",
                "state": self.get_state()
            })
            
            # Wait before next step
            await asyncio.sleep(self.simulation_speed)
    
    async def _run_parl_step(self, agent: GenerativeAgent, env_state: Dict) -> Dict:
        """Run one PARL step for an agent using LLM"""
        # Build agent dict for PARL engine
        agent_dict = {
            "name": agent.name,
            "role": agent.role,
            "location": agent.state.location,
            "energy": agent.state.energy,
            "mood": agent.state.mood,
            "backstory": agent.backstory,
            "secret": agent.secret,
            "personality": {
                "openness": agent.personality.openness,
                "conscientiousness": agent.personality.conscientiousness,
                "extraversion": agent.personality.extraversion,
                "agreeableness": agent.personality.agreeableness,
                "neuroticism": agent.personality.neuroticism
            }
        }
        
        # Build context
        context = {
            "time": env_state.get("time", "Unknown"),
            "agents_at_location": env_state.get("agents_at_location", []),
            "all_agent_names": [a.name for a in self.agents],  # For hallucination check
            "events": env_state.get("events", []),
            "current_situation": f"At {agent.state.location}"
        }
        
        # P - Perceive
        observations = parl_engine.perceive(agent_dict, env_state)
        
        # R - Reason (LLM call)
        decision = await parl_engine.reason(agent_dict, context)
        
        # A - Act
        result = self._execute_action(agent, decision)
        
        # L - Learn
        parl_engine.learn(agent_dict, {
            **result,
            "related_agents": [a["name"] for a in context.get("agents_at_location", [])]
        })
        
        return result
    
    def _execute_action(self, agent: GenerativeAgent, decision: Dict) -> Dict:
        """Execute the decided action"""
        action = decision.get("action", "rest")
        target = decision.get("target", "")
        dialogue = decision.get("dialogue")
        thought = decision.get("thought", "")
        
        result = {
            "action": action,
            "details": "",
            "thought": thought,
            "dialogue": dialogue
        }
        
        if action == "move":
            # Validate location
            valid_locations = ["Mission Control", "Agri Lab", "Mess Hall", "Rec Room", 
                              "Crew Quarters", "Medical Bay", "Comms Tower", "Mining Tunnel"]
            
            target = target.strip() # Sanitize input
            
            if target in valid_locations and target != agent.state.location:
                old_location = agent.state.location
                agent.state.location = target
                agent.state.activity = f"moving to {target}"
                self.environment.move_agent(agent.id, agent.name, old_location, target)
                result["details"] = f"Moved from {old_location} to {target}"
            else:
                result["details"] = f"Staying at {agent.state.location}"
                
        elif action == "talk":
            # Check if target agent is present
            others = [a for a in self.agents 
                     if a.state.location == agent.state.location and a.id != agent.id]
            
            if others and dialogue:
                # Find target
                target_agent = None
                for o in others:
                    if target and target.lower() in o.name.lower():
                        target_agent = o
                        break
                
                if target_agent:
                    # Valid conversation
                    agent.state.activity = f"talking to {target_agent.name}"
                    result["details"] = f"Said to {target_agent.name}: \"{dialogue}\""
                    result["target_agent"] = target_agent.name
                    
                    # BIDIRECTIONAL MEMORY: Store for BOTH agents
                    # 1. Target remembers what speaker said
                    memory_store.add_memory(
                        agent_name=target_agent.name,
                        content=f"{agent.name} told me: \"{dialogue}\"",
                        memory_type="dialogue",
                        importance=6.0,
                        related_agents=[agent.name],
                        source=agent.name,
                        propagation_chain=[agent.name]
                    )
                    
                    # 2. Speaker remembers what they said
                    memory_store.add_memory(
                        agent_name=agent.name,
                        content=f"I told {target_agent.name}: \"{dialogue}\"",
                        memory_type="dialogue",
                        importance=5.0,
                        related_agents=[target_agent.name],
                        source="self"
                    )
                    
                    # Update relationship between agents
                    relationship_manager.update_after_interaction(
                        agent.name,
                        target_agent.name,
                        "talk",
                        "positive"  # Assume conversations are positive
                    )
                    
                    # Track information propagation for analytics
                    propagation_tracker.record_propagation(
                        from_agent=agent.name,
                        to_agent=target_agent.name,
                        content=dialogue
                    )
                else:
                    # Targeted person not here - Search for them
                    real_target_agent = None
                    for a in self.agents:
                        if target and target.lower() in a.name.lower():
                            real_target_agent = a
                            break
                    
                    if real_target_agent:
                        # Found them elsewhere - Move there
                        target_loc = real_target_agent.state.location
                        result["action"] = "move"
                        result["target"] = target_loc
                        result["thought"] = f"I need to tell {real_target_agent.name} \"{dialogue}\", but they are at {target_loc}. I'll go there."
                        result["details"] = f"Moving to {target_loc} to find {real_target_agent.name}"
                        
                        # Execute move immediately
                        old_location = agent.state.location
                        agent.state.location = target_loc
                        agent.state.activity = f"moving to {target_loc}"
                        self.environment.move_agent(agent.id, agent.name, old_location, target_loc)
                    else:
                        result["action"] = "rest"
                        failure_msg = f"I wanted to talk to {target}, but I can't find them anywhere."
                        result["thought"] = failure_msg
                        result["details"] = "Confused - Target not found"
                        
                        # CRITICAL: Add memory of failure so they don't loop
                        memory_store.add_memory(
                            agent_name=agent.name,
                            content=failure_msg,
                            memory_type="observation",
                            importance=5.0
                        )
            else:
                result["details"] = "No one to talk to"
                result["action"] = "idle"
                
        elif action == "work":
            agent.state.activity = f"working on {target or 'duties'}"
            agent.state.energy = max(0, agent.state.energy - 5)
            result["details"] = f"Working: {target or 'regular duties'}"
            
        elif action == "rest":
            agent.state.activity = "resting"
            agent.state.energy = min(100, agent.state.energy + 15)
            result["details"] = "Taking a rest"
        
        return result
    
    async def _generate_reflections(self):
        """Generate reflections for agents periodically"""
        import random
        
        # Pick 1-2 random agents to reflect
        reflecting_agents = random.sample(self.agents, min(2, len(self.agents)))
        
        for agent in reflecting_agents:
            agent_dict = {
                "name": agent.name,
                "role": agent.role
            }
            reflection = await parl_engine.generate_reflection(agent_dict)
            if reflection:
                print(f"[Reflection] {agent.name}: {reflection}")
    
    async def _broadcast_update(self, data: Dict):
        """Send update to frontend via callback"""
        if self.on_update:
            await self.on_update(data)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        return {
            "time": self.environment.state.time_string,
            "step": self.step_count,
            "is_running": self.is_running,
            "llm_enabled": self.use_llm,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "role": agent.role,
                    "location": agent.state.location,
                    "activity": agent.state.activity,
                    "mood": agent.state.mood,
                    "energy": agent.state.energy
                }
                for agent in self.agents
            ],
            "world": self.environment.to_dict(),
            "recent_activities": self.activity_log[-10:]
        }
    
    def get_agents(self) -> List[Dict]:
        """Get all agents as dict"""
        if not self.agents:
            self.initialize()
        return [
            {
                "id": i + 1,
                "name": agent.name,
                "role": agent.role,
                "location": agent.state.location
            }
            for i, agent in enumerate(self.agents)
        ]
