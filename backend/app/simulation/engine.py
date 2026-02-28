"""
Simulation Engine - Runs the PARL loop for all agents
Orchestrates:
- Cognitive Agents (Memory, Identity, Planning)
- Environment (Locations, Time)
- Conversation Choreography (Multi-turn dialogue)
- Pathfinding (Movement)
- Recording (Replay system)
"""
import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import traceback

from ..agents.generative_agent import GenerativeAgent, create_all_agents
from ..agents.history_loader import HistoryLoader
from ..agents.relationships import relationship_manager
from ..world.environment import Environment
from ..parl import parl_engine
from ..memory import memory_store
from ..config import settings

# Integration of new modules
from ..cognitive.converse import ConversationChoreographer, create_choreographer_with_llm
from ..world.pathfinder import StationNavigator, get_navigator
from ..simulation.replay import SimulationRecorder, get_recorder
from ..memory.scratch import ActionStatus

class SimulationEngine:
    """
    Main simulation engine that orchestrates all agents
    """
    
    def __init__(self, on_update: Callable[[Dict[str, Any]], Any] = None):
        self.environment = Environment()
        self.agents: List[GenerativeAgent] = []
        self.is_running = False
        self.simulation_speed = settings.SIMULATION_SPEED
        self.on_update = on_update
        self.step_count = 0
        self.activity_log: List[Dict[str, Any]] = []
        
        # New modules
        self.choreographer = create_choreographer_with_llm()
        self.recorder = get_recorder()
        self.navigator = get_navigator()
        
        # Agent processing
        self.agents_per_step = 2  # Process 2 agents per step for rate limits
        
    def initialize(self):
        """Initialize all agents and place them in the world"""
        # Load agents from history/CSV
        self.agents = create_all_agents()
        
        # Initialize relationships
        agent_names = [a.name for a in self.agents]
        relationship_manager.initialize_relationships(agent_names)
        
        # Place agents in their primary workspaces
        for agent in self.agents:
            location = agent.cognitive_state.primary_workspace
            agent.cognitive_state.world_location = location
            # Explicitly register agent in environment hierarchy
            # Use 'None' or empty string as from_loc since they are new
            self.environment.move_agent(agent.id, agent.name, None, location)
            
            # Record initial state
            memory_store.add_memory(
                agent_name=agent.name,
                content=f"Simulation started. I am at {location}.",
                memory_type="observation",
                importance=5.0
            )
        
        print(f"✅ Initialized {len(self.agents)} agents with Cognitive State")
        return self.get_state()
    
    async def start(self):
        """Start the simulation loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.initialize()
        self.environment.start()
        
        # Broadcast start
        await self._broadcast_update({
            "type": "simulation_started",
            "message": "Simulation started",
            "state": self.get_state()
        })
        
        # Start loop
        asyncio.create_task(self._simulation_loop())
    
    async def stop(self):
        """Stop the simulation"""
        self.is_running = False
        self.environment.stop()
        
        # Save recording
        saved_path = self.recorder.save()
        filename = saved_path.split("/")[-1] # Extract name for display
        
        await self._broadcast_update({
            "type": "simulation_stopped",
            "message": "Simulation paused",
            "recording": filename
        })
    
    async def _simulation_loop(self):
        """Main simulation loop"""
        while self.is_running:
            self.step_count += 1
            self.environment.step() # Clear events
            
            # Sync simulation time to all agents using the CANONICAL time source
            # This is the single source of truth — perceive() no longer overrides it
            sim_datetime = self.environment.state.get_current_datetime()
            for agent in self.agents:
                agent.cognitive_state.current_time = sim_datetime
                agent.cognitive_state.update_cooldowns()
            
            # Process agents (round-robin)
            start_idx = ((self.step_count - 1) * self.agents_per_step) % len(self.agents)
            agents_to_process = []
            for i in range(self.agents_per_step):
                idx = (start_idx + i) % len(self.agents)
                agents_to_process.append(self.agents[idx])
            
            for agent in agents_to_process:
                if not self.is_running: break
                
                try:
                    await self._process_agent(agent)
                except Exception as e:
                    print(f"Error processing agent {agent.name}: {e}")
                    traceback.print_exc()
            
            # Record frame (full state)
            state = self.get_state()
            self.recorder.record_frame(
                step=self.step_count,
                simulation_time=state["time"],
                agents=state["agents"],
                conversations=None, # TODO: Track active conversations in state
                events=state["world"].get("events", [])
            )
            
            # Broadcast update
            await self._broadcast_update({
                "type": "state_update",
                "state": state
            })
            
            await asyncio.sleep(self.simulation_speed)
    
    async def _process_agent(self, agent: GenerativeAgent):
        """Process a single agent step.
        
        Follows Stanford generative agents pattern:
        1. Check if current action/conversation is finished → end it
        2. If action still in progress → continue (let time tick)
        3. If idle → reason for next action
        """
        env_state = self.environment.get_environment_for_agent(agent.cognitive_state.world_location)
        
        # Enrich agent info with roles
        for other in env_state.get("agents_at_location", []):
            full_agent = next((a for a in self.agents if a.name == other["name"]), None)
            if full_agent:
                other["role"] = full_agent.role
            else:
                other["role"] = "Crew"
        
        # --- Step 1: If action is in progress, check if it's finished ---
        if agent.cognitive_state.action_status == ActionStatus.IN_PROGRESS:
            if agent.cognitive_state.is_action_finished():
                # Handle conversation ending
                if agent.cognitive_state.chatting_with:
                    partner_name = agent.cognitive_state.chatting_with
                    agent.add_memory(
                        f"Finished chatting with {partner_name}",
                        "conversation", 5.0
                    )
                    # Also end the partner's conversation if they're still chatting with us
                    partner = next((a for a in self.agents if a.name == partner_name), None)
                    if partner and partner.cognitive_state.chatting_with == agent.name:
                        partner.cognitive_state.end_conversation()
                        partner.add_memory(
                            f"Finished chatting with {agent.name}",
                            "conversation", 5.0
                        )
                    agent.cognitive_state.end_conversation()
                    print(f"💬 [Conv] {agent.name} ended conversation with {partner_name}")
                else:
                    # Regular action finished
                    desc = agent.cognitive_state.act_description or "an action"
                    
                    # If this was a movement action, teleport to final destination
                    if agent.cognitive_state.path_computed and agent.cognitive_state.planned_path:
                        old_loc = agent.cognitive_state.world_location
                        final_dest = agent.cognitive_state.planned_path[-1]
                        if old_loc != final_dest:
                            agent.cognitive_state.world_location = final_dest
                            self.environment.move_agent(
                                agent.id, agent.name, old_loc, final_dest
                            )
                            print(f"📍 [Arrive] {agent.name} arrived at {final_dest} (from {old_loc})")
                        agent.add_memory(f"Arrived at {final_dest}", "observation", 3.0)
                    else:
                        print(f"✔️  [Action] {agent.name} finished: {desc}")
                        agent.add_memory(
                            content=f"Finished {desc}",
                            memory_type="observation",
                            importance=3.0
                        )
                    agent.cognitive_state.end_action()
                # Fall through to reasoning below
            else:
                # Action still in progress — handle movement or let time tick
                if agent.cognitive_state.path_computed:
                    await self._handle_movement_step(agent)
                # For conversations and timed actions, just let time tick
                return
        
        # --- Step 2: Agent is idle — reason for next action ---
        observations = agent.perceive(env_state)
        decision = await agent.reason(observations, env_state)
        await self._execute_decision(agent, decision)
        
    async def _handle_movement_step(self, agent: GenerativeAgent):
        """Advance agent along planned path"""
        old_loc = agent.cognitive_state.world_location
        new_loc = agent.cognitive_state.advance_path()
        
        if new_loc:
            success = self.environment.move_agent(
                agent.id, agent.name, old_loc, new_loc
            )
            if success:
                agent.cognitive_state.act_description = f"moving to {agent.cognitive_state.planned_path[-1]}"
            else:
                agent.cognitive_state.end_action() # Stop if failed
        else:
            # Reached destination
            agent.cognitive_state.end_action()
            agent.add_memory(f"Arrived at {agent.cognitive_state.world_location}", "observation", 3.0)

    async def _execute_decision(self, agent: GenerativeAgent, decision: Dict):
        """Execute the action decided by the agent"""
        action = decision.get("action")
        target = decision.get("target")
        dialogue = decision.get("dialogue")
        thought = decision.get("thought")
        
        # Log thought
        if thought:
             # Add strictly as thought memory
            agent.add_memory(thought, "thought", 2.0)
            
        if action == "move":
            # Use Navigator to plan path
            path_result = self.navigator.find_path(agent.cognitive_state.world_location, target)
            if path_result.path:
                agent.cognitive_state.start_action(
                    address=target,
                    duration=path_result.travel_time_minutes,
                    description=f"moving to {target}",
                    emoji="🚶"
                )
                agent.cognitive_state.set_path(path_result.path)
                print(f"🚶 [Move] {agent.name}: {agent.cognitive_state.world_location} → {target} (path: {path_result.path}, {path_result.travel_time_minutes}min)")
                agent.add_memory(f"Started walking to {target}", "observation", 3.0)
            else:
                print(f"⚠️ [Move] {agent.name}: No path found from '{agent.cognitive_state.world_location}' to '{target}' — {path_result.description}")
                agent.add_memory(f"Could not find path to {target}", "observation", 4.0)
                
        elif action == "talk":
            # Attempt to start conversation
            if agent.cognitive_state.can_talk_to(target):
                # Find target agent object
                target_agent = next((a for a in self.agents if a.name == target), None)
                if target_agent:
                    # CHECK: Is the target already in a conversation?
                    # Stanford pattern: don't overwrite an ongoing conversation
                    if target_agent.cognitive_state.chatting_with:
                        agent.add_memory(
                            f"{target} was busy talking to {target_agent.cognitive_state.chatting_with}, couldn't chat.",
                            "observation", 3.0
                        )
                        # Fallback: do a short work action instead of staying idle
                        agent.cognitive_state.start_action(
                            address=agent.cognitive_state.world_location,
                            duration=2, description="waiting / working briefly", emoji="⏳"
                        )
                        print(f"⏭️  [Conv] {agent.name} wanted to talk to {target} but they're busy → working briefly")
                    else:
                        # Calculate conversation end time (2 sim-minutes from now)
                        conv_duration = 2  # minutes in sim time
                        conv_end_time = agent.cognitive_state.current_time + timedelta(minutes=conv_duration)
                        
                        # Start via Choreographer (fire-and-forget, don't depend on it for lifecycle)
                        try:
                            await self.choreographer.start_conversation(
                                initiator_name=agent.name,
                                initiator_role=agent.role,
                                initiator_personality=str(agent.personality),
                                target_name=target_agent.name,
                                target_role=target_agent.role,
                                target_personality=str(target_agent.personality),
                                topic="Check-in",
                                location=agent.cognitive_state.world_location
                            )
                        except Exception as e:
                            print(f"⚠️ Choreographer error (non-fatal): {e}")
                        
                        # Set states for both agents with a fixed end_time
                        # Following Stanford pattern: conversations are timed, not turn-managed
                        agent.cognitive_state.start_conversation(target, end_time=conv_end_time)
                        agent.cognitive_state.act_description = f"chatting with {target}"
                        agent.cognitive_state.action_duration = conv_duration
                        agent.cognitive_state.action_start_time = agent.cognitive_state.current_time
                        
                        target_agent.cognitive_state.start_conversation(agent.name, end_time=conv_end_time)
                        target_agent.cognitive_state.act_description = f"chatting with {agent.name}"
                        target_agent.cognitive_state.action_duration = conv_duration
                        target_agent.cognitive_state.action_start_time = target_agent.cognitive_state.current_time
                        
                        print(f"💬 [Conv] {agent.name} started conversation with {target} (ends at {conv_end_time.strftime('%H:%M')})")
                else:
                    agent.add_memory(f"Wanted to talk to {target} but couldn't find them.", "observation", 3.0)
                    agent.cognitive_state.start_action(
                        address=agent.cognitive_state.world_location,
                        duration=2, description="looking around", emoji="👀"
                    )
            else:
                print(f"⏭️  [Conv] {agent.name} can't talk to {target} (cooldown or already chatting) → working briefly")
                agent.cognitive_state.start_action(
                    address=agent.cognitive_state.world_location,
                    duration=2, description="waiting / working briefly", emoji="⏳"
                )

        elif action == "work":
            agent.cognitive_state.start_action(
                address=agent.cognitive_state.world_location,
                duration=10,
                description=f"working on {target}",
                emoji="💻"
            )
            
        elif action == "rest":
            agent.cognitive_state.start_action(
                address=agent.cognitive_state.world_location,
                duration=5,
                description="resting",
                emoji="😴"
            )

        # Log activity for frontend display
        activity_entry = {
            "agent": agent.name,
            "action": action or "idle",
            "details": f"{action} → {target}" if target else action,
            "thought": thought or "",
            "location": agent.cognitive_state.world_location,
            "time": str(agent.cognitive_state.current_time.strftime("%H:%M")) if agent.cognitive_state.current_time else ""
        }
        # For talk actions, add dialogue for speech bubbles
        if action == "talk" and dialogue and agent.cognitive_state.chatting_with:
            activity_entry["details"] = f'Said to {target}: "{dialogue}"'
        
        self.activity_log.append(activity_entry)
        # Keep only last 50 entries
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]

    async def _broadcast_update(self, data: Dict):
        """Send update to frontend via callback"""
        if self.on_update:
            await self.on_update(data)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        agents_list = [agent.to_dict() for agent in self.agents]
        world = self.environment.to_dict()
        
        return {
            "time": self.environment.state.time_string,
            "step": self.step_count,
            "is_running": self.is_running,
            "agents": agents_list,
            "world": world,
            "recent_activities": self.activity_log[-10:]
        }
