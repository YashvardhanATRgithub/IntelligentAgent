from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json
from typing import List, Dict, Any
import asyncio
import os

from .simulation.engine import SimulationEngine
from .simulation.replay import get_player

app = FastAPI(
    title="ISRO Chandrayaan-5 Simulation",
    description="Generative Agents at Aryabhata Station",
    version="2.0.0"
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
player = get_player()


@app.get("/")
async def root():
    return {"message": "ISRO Chandrayaan-5 Simulation API", "status": "online", "version": "2.0.0"}


@app.get("/api/agents")
async def get_agents():
    """Get all agents and their current states"""
    # Use simulation state to get agents
    state = simulation.get_state()
    return {"agents": state["agents"]}


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


@app.get("/api/agents/{agent_name}/full")
async def get_agent_full(agent_name: str):
    """Get complete agent info: state, memories, relationships"""
    from .memory import memory_store
    from .agents.relationships import relationship_manager
    
    # Find agent
    agent = next((a for a in simulation.agents if a.name == agent_name), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "agent": agent_name,
        "state": agent.to_dict(),
        "memories": memory_store.get_recent_memories(agent_name, limit=10),
        "relationships": relationship_manager.to_dict(agent_name)
    }


# ===== REPLAY SYSTEM =====

@app.get("/api/replays")
async def list_replays():
    """List all available simulation recordings"""
    recordings = player.list_recordings()
    return {"recordings": recordings}

@app.get("/api/replays/{recording_id}")
async def get_replay_info(recording_id: str):
    """Get metadata for a specific recording"""
    # This might load the file to get metadata
    success = player.load(recording_id)
    if not success:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    return {
        "id": recording_id,
        "metadata": player.metadata,
        "duration": len(player.frames) if player.frames else 0
    }

@app.delete("/api/replays/{recording_id}")
async def delete_replay(recording_id: str):
    """Delete a recording"""
    success = player.delete_recording(recording_id)
    if success:
        return {"status": "deleted", "id": recording_id}
    raise HTTPException(status_code=404, detail="Recording not found")


# ===== EVENTS & ANALYTICS =====

@app.get("/api/events")
async def get_events():
    """Get list of available demo events"""
    # Simplified interaction event system
    return {"events": []} 


@app.get("/api/analytics")
async def get_analytics():
    """Get information propagation analytics"""
    # Placeholder for analytics
    return {"message": "Analytics module upgrading"}


# ===== WEBSOCKET =====

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
            elif message.get("type") == "start":
                await simulation.start()
            elif message.get("type") == "stop":
                await simulation.stop()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
