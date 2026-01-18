from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from typing import List, Dict, Any
import asyncio

from .simulation.engine import SimulationEngine

app = FastAPI(
    title="ISRO Chandrayaan-5 Simulation",
    description="Generative Agents at Aryabhata Station",
    version="1.0.0"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")


manager = ConnectionManager()

# Simulation engine with broadcast callback
async def broadcast_update(data: Dict[str, Any]):
    await manager.broadcast(data)

simulation = SimulationEngine(on_update=broadcast_update)


@app.get("/")
async def root():
    return {"message": "ISRO Chandrayaan-5 Simulation API", "status": "online"}


@app.get("/api/agents")
async def get_agents():
    """Get all agents and their current states"""
    agents = simulation.get_agents()
    return {"agents": agents}


@app.get("/api/state")
async def get_state():
    """Get full simulation state"""
    return simulation.get_state()


@app.post("/api/simulation/start")
async def start_simulation():
    """Start the simulation"""
    await simulation.start()
    return {"status": "started", "message": "Simulation started"}


@app.post("/api/simulation/stop")
async def stop_simulation():
    """Stop/pause the simulation"""
    await simulation.stop()
    return {"status": "stopped", "message": "Simulation paused"}


@app.post("/api/simulation/pause")
async def pause_simulation():
    """Pause the simulation (alias for stop)"""
    await simulation.stop()
    return {"status": "paused"}


@app.post("/api/simulation/speed")
async def set_speed(speed: float = 1.0):
    """Set simulation speed (1.0 = normal, 2.0 = 2x, etc.)"""
    simulation.simulation_speed = max(0.25, min(5.0, speed))
    return {"status": "ok", "speed": simulation.simulation_speed}


@app.get("/api/agents/{agent_name}/memories")
async def get_agent_memories(agent_name: str, limit: int = 20):
    """Get an agent's memory stream"""
    from .memory import memory_store
    memories = memory_store.get_recent_memories(agent_name, limit=limit)
    return {"agent": agent_name, "memories": memories}


@app.get("/api/agents/{agent_name}/relationships")
async def get_agent_relationships(agent_name: str):
    """Get an agent's relationships with other agents"""
    from .agents.relationships import relationship_manager
    relationships = relationship_manager.to_dict(agent_name)
    return {"agent": agent_name, "relationships": relationships}


@app.get("/api/agents/{agent_name}/plan")
async def get_agent_plan(agent_name: str):
    """Get an agent's daily plan"""
    from .parl.planner import daily_planner
    plan = daily_planner.to_dict(agent_name)
    return {"agent": agent_name, "plan": plan}


@app.get("/api/agents/{agent_name}/full")
async def get_agent_full(agent_name: str):
    """Get complete agent info: state, memories, relationships, plan"""
    from .memory import memory_store
    from .agents.relationships import relationship_manager
    from .parl.planner import daily_planner
    
    # Find agent state
    agent_state = None
    for agent in simulation.agents:
        if agent.name == agent_name:
            agent_state = {
                "name": agent.name,
                "role": agent.role,
                "location": agent.state.location,
                "activity": agent.state.activity,
                "mood": agent.state.mood,
                "energy": agent.state.energy
            }
            break
    
    return {
        "agent": agent_name,
        "state": agent_state,
        "memories": memory_store.get_recent_memories(agent_name, limit=10),
        "relationships": relationship_manager.to_dict(agent_name),
        "plan": daily_planner.to_dict(agent_name)
    }


# ===== EVENTS & ANALYTICS =====

@app.get("/api/events")
async def get_events():
    """Get list of available demo events"""
    from .simulation.events import event_manager
    return {"events": event_manager.get_available_events()}


@app.post("/api/events/{event_id}/trigger")
async def trigger_event(event_id: str):
    """Trigger a demo event - injects information into target agent's memory"""
    from .simulation.events import event_manager
    from .simulation.analytics import propagation_tracker
    from .memory import memory_store
    
    result = event_manager.trigger_event(event_id)
    if not result or "error" in result:
        return {"error": result.get("error", "Event not found")}
    
    # Inject memory into target agent
    memory_store.add_memory(
        agent_name=result["agent"],
        content=result["content"],
        memory_type="event",
        importance=result["importance"],
        source="SYSTEM_EVENT"
    )
    
    # Record initial knowledge
    propagation_tracker.record_initial_knowledge(
        event_id=event_id,
        agent_name=result["agent"],
        content=result["content"]
    )
    
    return {
        "status": "triggered",
        "event": event_id,
        "target_agent": result["agent"],
        "message": f"Event '{result['event_name']}' triggered for {result['agent']}"
    }


@app.get("/api/analytics")
async def get_analytics():
    """Get information propagation analytics"""
    from .simulation.analytics import propagation_tracker
    return propagation_tracker.get_summary()


@app.get("/api/analytics/event/{event_id}")
async def get_event_analytics(event_id: str):
    """Get detailed propagation analysis for a specific event"""
    from .simulation.analytics import propagation_tracker
    return propagation_tracker.get_event_spread(event_id)


@app.post("/api/events/reset")
async def reset_events():
    """Reset all events to untriggered state"""
    from .simulation.events import event_manager
    from .simulation.analytics import propagation_tracker
    event_manager.reset_events()
    propagation_tracker.clear()
    return {"status": "reset", "message": "All events and analytics cleared"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time simulation updates"""
    await manager.connect(websocket)
    
    # Send initial state
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to simulation",
            "state": simulation.get_state()
        })
    except Exception as e:
        print(f"Error sending initial state: {e}")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle incoming commands
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "get_state":
                await websocket.send_json({
                    "type": "state_update",
                    "state": simulation.get_state()
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
