"""
Simulation Engine - Runs the PARL loop for all agents
Stanford-level cognitive architecture with:
- Perceive: Filter observations with attention scoring
- Retrieve: Semantic memory search
- Plan: Hourly decomposed scheduling (Stanford-level multi-call)
- Reflect: LLM-generated insights
- Act: Execute decisions
- Learn: Store experiences
- Converse: Multi-turn dialogue (Stanford-level)
"""
import asyncio
from typing import List, Dict, Any, Callable
from datetime import datetime
from ..agents.generative_agent import GenerativeAgent, create_all_agents
from ..agents.relationships import relationship_manager
from ..world.environment import Environment
from ..parl import parl_engine
from ..parl.planner import daily_planner, LongTermGoalTracker
from ..parl.stanford_planning import stanford_planner
from ..memory import memory_store
from .analytics import propagation_tracker
from ..config import settings

# Stanford-level cognitive modules
from ..cognitive.perceive import perception_engine, PerceivedEnvironment
from ..cognitive.reflect import reflection_engine
from ..cognitive.conversation import conversation_manager


class SimulationEngine:
    """
    Main simulation engine that orchestrates all agents
    Now powered by PARL with Ollama LLM
    """
    
    def __init__(self, on_update: Callable[[Dict[str, Any]], Any] = None):
        self.environment = Environment()
        self.agents: List[GenerativeAgent] = []
        self.is_running = False
        self.simulation_speed = settings.SIMULATION_SPEED  # Use config (default 5.0s)
        self.on_update = on_update
        self.step_count = 0
        self.activity_log: List[Dict[str, Any]] = []
        self.use_llm = True  # Toggle for LLM reasoning
        self.reflection_interval = 5  # Generate reflections every N steps
        
        # Stanford-surpassing: Decision caching to reduce LLM calls
        self.decision_cache: Dict[str, tuple] = {}  # agent_name -> (decision, step_made)
        self.cache_duration = 3  # Keep decisions for 3 steps
        
        # Stanford-surpassing: Agent staggering for rate limit management
        self.agents_per_step = 2  # Process 2 agents per step (round-robin)
        
    def initialize(self):
        """Initialize all agents and place them in the world"""
        self.agents = create_all_agents()
        
        # Initialize long-term goal tracker for multi-day continuity
        self.goal_tracker = LongTermGoalTracker()
        
        # Place agents in their starting locations (15 agents)
        starting_locations = {
            # Original 8
            "Cdr. Vikram Sharma": "Mission Control",
            "Dr. Ananya Iyer": "Agri Lab",
            "TARA": "Mission Control",
            "Priya Nair": "Mess Hall",
            "Aditya Reddy": "Crew Quarters",
            "Dr. Arjun Menon": "Medical Bay",
            "Kabir Saxena": "Mining Tunnel",
            "Rohan Pillai": "Comms Tower",
            # New 7
            "Lt. Meera Chandra": "Crew Quarters",  # Shuttle Pilot
            "Dr. Dev Malhotra": "Mining Tunnel",  # Research Scientist
            "Lakshmi Venkat": "Mission Control",  # Resource Manager
            "Sanjay Kumar": "Crew Quarters",  # EVA Specialist
            "Neha Gupta": "Mission Control",  # Power Systems
            "Ravi Singh": "Mining Tunnel",  # Robotics Tech
            "Dr. Sunita Rao": "Comms Tower",  # Astrophysicist (observatory)
        }
        
        for agent in self.agents:
            location = starting_locations.get(agent.name, "Crew Quarters")
            agent.state.location = location
            self.environment.move_agent(agent.id, agent.name, "", location)
        
        # Initialize relationships between all agents
        agent_names = [a.name for a in self.agents]
        relationship_manager.initialize_relationships(agent_names)
        
        # Create daily plans for each agent (basic planner)
        for agent in self.agents:
            daily_planner.create_plan_for_agent(agent.name, agent.role)
        
        # Log provider info
        provider = settings.LLM_PROVIDER.upper()
        print(f"✅ Initialized {len(self.agents)} agents | Provider: {provider}")
        print(f"   Stanford modules: planning ✓, reflection ✓, conversation ✓")
        
        return self.get_state()
    
    async def start(self):
        """Start the simulation loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self.initialize()
        
        # Stanford-level: Generate daily plans for agents using LLM (async)
        # Only generate for a few agents to avoid rate limits
        await self._generate_stanford_plans()
        
        # Start environment time
        self.environment.start()
        
        # Send initial state
        await self._broadcast_update({
            "type": "simulation_started",
            "message": "Simulation started with Stanford-level LLM planning",
            "state": self.get_state()
        })
    
    async def _generate_stanford_plans(self):
        """Generate Stanford-level daily plans for agents via multi-call LLM"""
        print("🗓️ [Stanford] Generating daily plans for agents...")
        
        # Only generate plans for 2 agents to avoid rate limits on Groq
        # More will be generated as simulation progresses
        agents_to_plan = self.agents[:2]
        
        for agent in agents_to_plan:
            try:
                agent_dict = {
                    "name": agent.name,
                    "role": agent.role,
                    "location": agent.state.location
                }
                plan = await stanford_planner.create_full_plan(agent_dict)
                if plan:
                    print(f"   ✅ {agent.name}: {len(plan.activities)} activities planned")
            except Exception as e:
                print(f"   ⚠️ {agent.name}: Plan generation skipped ({e})")
        
        print("🗓️ [Stanford] Planning complete!")

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
        # Stop environment time
        self.environment.stop()
        await self._broadcast_update({
            "type": "simulation_stopped",
            "message": "Simulation paused"
        })
    
    async def _simulation_loop(self):
        """Main simulation loop - runs PARL for each agent (Stanford-surpassing with staggering)"""
        while self.is_running:
            self.step_count += 1
            
            # Advance world time
            self.environment.step()
            
            # Stanford-surpassing: Round-robin agent processing (reduces API calls)
            # Only process a subset of agents each step
            start_idx = ((self.step_count - 1) * self.agents_per_step) % len(self.agents)
            agents_to_process = []
            for i in range(self.agents_per_step):
                idx = (start_idx + i) % len(self.agents)
                agents_to_process.append(self.agents[idx])
            
            for agent in agents_to_process:
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
                    
                    # Stanford-surpassing: Check decision cache first
                    cached = self.decision_cache.get(agent.name)
                    if cached and (self.step_count - cached[1]) < self.cache_duration:
                        # Use cached decision (no LLM call needed)
                        result = cached[0]
                        print(f"📋 [Cache] {agent.name} using cached decision: {result.get('action')}")
                    else:
                        # Run PARL step (LLM call)
                        result = await self._run_parl_step(agent, env_state)
                        # Cache the decision
                        self.decision_cache[agent.name] = (result, self.step_count)
                    
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
                    
                    # Stanford-surpassing: Check for edge cases
                    await self._check_and_handle_edge_cases(agent, env_state, result)
                    
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
        """
        Run one PARL step for an agent using Stanford-level cognitive modules.
        
        Flow: Perceive → Retrieve → Plan → Reason → Act → Learn
        """
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
        
        # Get relationship scores for attention prioritization
        relationship_scores = relationship_manager.get_relationship_scores(agent.name)
        
        # Build world state for perception
        world_state = {
            "agents_at_location": {
                agent.state.location: [
                    {"name": a.name, "role": a.role, "activity": a.state.activity}
                    for a in self.agents
                    if a.state.location == agent.state.location and a.id != agent.id
                ]
            },
            "recent_dialogues": self.activity_log[-10:] if self.activity_log else [],
            "locations": env_state.get("locations", {}),
            "events": env_state.get("events", [])
        }
        
        # P - PERCEIVE (Stanford-level: attention filtering)
        perceived_env = perception_engine.perceive(
            agent_name=agent.name,
            agent_role=agent.role,
            current_location=agent.state.location,
            simulation_time=env_state.get("time", "Unknown"),
            world_state=world_state,
            relationship_scores=relationship_scores
        )
        
        # Add perception importance to reflection engine
        total_attention = sum(obs.attention_score for obs in perceived_env.observations)
        reflection_engine.add_importance(agent.name, total_attention / 10.0)
        
        # Build context with filtered observations
        context = {
            "time": env_state.get("time", "Unknown"),
            "agents_at_location": env_state.get("agents_at_location", []),
            "all_agent_names": [a.name for a in self.agents],
            "events": env_state.get("events", []),
            "current_situation": f"At {agent.state.location}",
            # Add perceived observations (Stanford-style)
            "observations": perceived_env.to_prompt_text(),
            "present_agents": perceived_env.present_agents
        }
        
        # Stanford-level: Add current plan/schedule to guide decisions
        agent_plan = stanford_planner.get_plan(agent.name)
        if agent_plan:
            current_hour = self.environment.state.hour
            current_minute = self.environment.state.minute
            current_task = agent_plan.get_current_activity(current_hour, current_minute)
            if current_task:
                context["scheduled_activity"] = current_task.activity
                context["scheduled_location"] = current_task.location
                context["subtasks"] = current_task.subtasks[:3] if current_task.subtasks else []
        
        # R - REASON (LLM call with enriched context)
        decision = await parl_engine.reason(agent_dict, context)
        
        # A - ACT
        result = self._execute_action(agent, decision)
        
        # L - LEARN (store in memory with proper source tracking)
        parl_engine.learn(agent_dict, {
            **result,
            "related_agents": perceived_env.present_agents,
            "observations_count": len(perceived_env.observations)
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
            target = target.strip() # Sanitize input
            
            if target == agent.state.location:
                result["details"] = f"Already at {target}"
            else:
                old_location = agent.state.location
                # Try to move - environment handles hierarchy validation
                success = self.environment.move_agent(agent.id, agent.name, old_location, target)
                
                if success:
                    # Update agent state
                    agent.state.location = self.environment.state.agent_locations[agent.id] # Get normalized path
                    agent.state.activity = f"moving to {target}"
                    result["details"] = f"Moved from {old_location} to {agent.state.location}"
                else:
                    result["details"] = f"Could not move to invalid location: {target}"
                
        elif action == "talk":
            # Check if target agent is present
            # Use environment to find agents at current location (handles sub-areas)
            current_loc_agents = self.environment.get_agents_at_location(agent.state.location)
            others = [
                a for a in self.agents 
                if a.id != agent.id and any(la['id'] == a.id for la in current_loc_agents)
            ]
            
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
                    
                    # Stanford-level: Track conversation with conversation_manager
                    convo = conversation_manager.get_or_create_conversation(
                        agent.name, target_agent.name, agent.state.location
                    )
                    convo.add_turn(agent.name, dialogue)
                    
                    # BIDIRECTIONAL MEMORY: Store for BOTH agents
                    # 1. Target remembers what speaker said
                    memory_store.add_memory(
                        agent_name=target_agent.name,
                        content=f"{agent.name} told me: \"{dialogue}\"",
                        memory_type="dialogue",
                        importance=7.0,  # Increased for conversation awareness
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
        """
        Stanford-level reflection generation.
        Uses importance threshold to trigger reflections.
        """
        for agent in self.agents:
            # Get recent memories for this agent
            recent_memories = memory_store.get_recent_memories(agent.name, limit=15)
            
            # Check if should reflect (importance threshold)
            if reflection_engine.should_reflect(agent.name, self.step_count, recent_memories):
                print(f"[Reflect] {agent.name} is reflecting...")
                
                # Build personality summary
                personality_summary = f"""Personality: Openness={agent.personality.openness:.1f}, 
Conscientiousness={agent.personality.conscientiousness:.1f}, 
Extraversion={agent.personality.extraversion:.1f}"""
                
                # Generate reflections using LLM
                reflections = await reflection_engine.generate_reflection(
                    agent_name=agent.name,
                    agent_role=agent.role,
                    personality_summary=personality_summary,
                    recent_memories=recent_memories,
                    llm_client=parl_engine.llm_client if hasattr(parl_engine, 'llm_client') else None,
                    current_step=self.step_count
                )
                
                # Store reflections as high-importance memories
                for reflection in reflections:
                    memory_store.add_reflection(
                        agent_name=agent.name,
                        reflection=reflection.content,
                        importance=reflection.importance
                    )
                    print(f"  → [{reflection.reflection_type.value}] {reflection.content[:80]}...")
    
    # ==================== STANFORD-SURPASSING EDGE CASE HANDLERS ====================
    
    async def _check_and_handle_edge_cases(self, agent, env_state: Dict, result: Dict):
        """
        Stanford-surpassing: Handle edge cases dynamically during simulation.
        Called after each agent action to detect special situations.
        """
        current_time = env_state.get("time", "")
        try:
            if ":" in current_time:
                 # Standard HH:MM format
                hour = int(current_time.split(":")[0])
            elif "," in current_time:
                 # "Week 1, Day 1, 06" format
                hour = int(current_time.split(",")[-1].strip())
            else:
                 # Fallback or simple "06" string
                hour = int(current_time.strip())
        except Exception:
            hour = 12 # Default safe fallback
        
        # Check for sleep interruption (6am-7am or action during 22:00-06:00)
        if 22 <= hour or hour < 6:
            if result.get("action") != "rest" and agent.state.energy < 30:
                await self._handle_sleep_interruption(agent, env_state)
        
        # Check for failed tasks (agent keeps failing same task)
        if result.get("action") == "work" and "failed" in result.get("details", "").lower():
            await self._handle_failed_task(agent, result.get("target", ""))
        
        # Regenerate daily plan at 6am (new day)
        if hour == 6 and self.step_count % 60 == 0:  # ~hourly check
            await self._regenerate_daily_plans()
    
    async def _handle_sleep_interruption(self, agent, env_state: Dict):
        """Handle wake-up during scheduled sleep - recalculate plan"""
        print(f"[EdgeCase] Sleep interruption for {agent.name} - handling...")
        
        # Call planner's sleep interruption handler
        new_tasks = daily_planner.handle_sleep_interruption(
            agent_name=agent.name,
            current_time=env_state.get("time", "06:00"),
            wake_reason="low_energy_urgent_task",
            current_energy=agent.state.energy,
            llm_client=parl_engine.llm_client if hasattr(parl_engine, 'llm_client') else None
        )
        
        if new_tasks:
            print(f"  → New recovery tasks: {[t.activity for t in new_tasks[:3]]}")
    
    async def _handle_failed_task(self, agent, failed_task: str):
        """Retry failed task with exponential backoff"""
        print(f"[EdgeCase] Failed task retry for {agent.name}: {failed_task}")
        
        retry_result = await daily_planner.retry_failed_task(
            agent_name=agent.name,
            failed_task=failed_task,
            failure_count=1,  # Would track this persistently
            max_retries=3,
            alternative_strategies=[
                f"Ask colleague for help with {failed_task}",
                f"Simplify {failed_task}",
                f"Postpone {failed_task} to tomorrow"
            ]
        )
        
        if retry_result and retry_result.get("should_retry"):
            print(f"  → Will retry in {retry_result.get('backoff_minutes')} minutes")
    
    async def trigger_emergency_evacuation(self, emergency_type: str, affected_locations: List[str]):
        """
        Stanford-surpassing: Multi-agent emergency coordination.
        Call this to trigger an emergency that affects multiple agents.
        """
        print(f"[EMERGENCY] {emergency_type} affecting {affected_locations}")
        
        affected_agents = [
            a for a in self.agents 
            if a.state.location in affected_locations
        ]
        
        agent_names = [a.name for a in affected_agents]
        
        # Use planner's emergency handler
        evacuation_plan = await daily_planner.handle_emergency_evacuation(
            affected_agents=agent_names,
            emergency_type=emergency_type,
            current_time=self.environment.state.time_string,
            safe_locations=["Mission Control", "Medical Bay"],
            llm_client=parl_engine.llm_client if hasattr(parl_engine, 'llm_client') else None
        )
        
        # Execute evacuation for all affected agents
        for agent in affected_agents:
            safe_loc = evacuation_plan.get(agent.name, {}).get("safe_location", "Mission Control")
            old_location = agent.state.location
            agent.state.location = safe_loc
            agent.state.activity = f"evacuating due to {emergency_type}"
            self.environment.move_agent(agent.id, agent.name, old_location, safe_loc)
            
            # Store emergency memory
            memory_store.add_memory(
                agent_name=agent.name,
                content=f"Emergency evacuation from {old_location} to {safe_loc} due to {emergency_type}",
                memory_type="event",
                importance=9.0
            )
        
        # Broadcast emergency
        await self._broadcast_update({
            "type": "emergency_event",
            "emergency_type": emergency_type,
            "affected_locations": affected_locations,
            "affected_agents": agent_names,
            "evacuation_plan": evacuation_plan
        })
        
        return evacuation_plan
    
    async def coordinate_multi_agent_task(self, task_name: str, required_roles: List[str], location: str):
        """
        Stanford-surpassing: Coordinate multiple agents for a joint task.
        """
        print(f"[Coordination] Starting multi-agent task: {task_name}")
        
        # Find agents matching required roles
        agent_names = []
        for role in required_roles:
            for agent in self.agents:
                if role.lower() in agent.role.lower():
                    agent_names.append(agent.name)
                    break
        
        if len(agent_names) < len(required_roles):
            print(f"  → Warning: Could only find {len(agent_names)}/{len(required_roles)} required roles")
        
        # Use planner's coordination
        coordination_result = await daily_planner.coordinate_multi_agent_task(
            task_name=task_name,
            participant_agents=agent_names,
            target_location=location,
            required_roles=required_roles,
            coordination_time=self.environment.state.time_string,
            llm_client=parl_engine.llm_client if hasattr(parl_engine, 'llm_client') else None
        )
        
        # Move agents to coordination location
        for agent_name in agent_names:
            agent = next((a for a in self.agents if a.name == agent_name), None)
            if agent and agent.state.location != location:
                old_loc = agent.state.location
                agent.state.location = location
                agent.state.activity = f"coordinating: {task_name}"
                self.environment.move_agent(agent.id, agent.name, old_loc, location)
        
        return coordination_result
    
    async def _regenerate_daily_plans(self):
        """
        Stanford-surpassing: Regenerate all agent plans for new day.
        Incorporates incomplete tasks and long-term goals.
        """
        print("[DailyRegen] Regenerating plans for new simulation day...")
        
        for agent in self.agents:
            # Get prior day's incomplete tasks
            incomplete_tasks = []  # Would track from previous day
            
            # Get long-term goals from tracker
            agent_goals = self.goal_tracker.get_goals(agent.name)
            
            # Use planner's regeneration
            new_plan = await daily_planner.regenerate_daily_plan(
                agent_name=agent.name,
                agent_role=agent.role,
                current_date=self.environment.state.time_string,
                incomplete_tasks=incomplete_tasks,
                long_term_goals=[g.get("description", "") for g in agent_goals],
                llm_client=parl_engine.llm_client if hasattr(parl_engine, 'llm_client') else None
            )
            
            if new_plan:
                daily_planner.create_plan_for_agent(agent.name, agent.role)
                print(f"  → {agent.name}: New plan generated with {len(new_plan.activities)} activities")
    
    async def _broadcast_update(self, data: Dict):
        """Send update to frontend via callback"""
        if self.on_update:
            await self.on_update(data)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        # Build agents list
        agents_list = [
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
        ]
        
        # Get world state (includes full hierarchical locations)
        world = self.environment.to_dict()
        
        return {
            "time": self.environment.state.time_string,
            "step": self.step_count,
            "is_running": self.is_running,
            "llm_enabled": self.use_llm,
            "agents": agents_list,
            "world": world,
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
