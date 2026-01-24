import sys
import os
sys.path.append(os.getcwd())

from app.world.environment import Environment, Location
from app.simulation.engine import SimulationEngine

def verify_hierarchy():
    print("🌍 Initializing Environment...")
    env = Environment()
    
    # 1. Check Hierarchy
    print("\n🔍 Checking Hierarchy Structure:")
    mc = env._find_node("Mission Control")
    if mc and "Command Deck" in mc.children:
        print("  ✅ Mission Control has Command Deck")
    else:
        print("  ❌ Missing hierarchy")
        
    # 2. Check Movement to Sub-area
    print("\n🏃 Checking Movement:")
    agent_id = "Vikram_1"
    success = env.move_agent(agent_id, "Vikram", "Crew Quarters", "Mission Control/Command Deck")
    if success:
        print(f"  ✅ Moved to Mission Control/Command Deck")
        print(f"  Current loc: {env.state.agent_locations[agent_id]}")
    else:
        print("  ❌ Movement failed")

    # 3. Check Recursive Agent Retrieval
    print("\n👥 Checking Agent Retrieval:")
    agents = env.get_agents_at_location("Mission Control")
    names = [a['name'] for a in agents]
    if "Vikram" in names:
        print(f"  ✅ Found Vikram in Mission Control (inherited from Command Deck)")
    else:
        print(f"  ❌ Vikram missing from Mission Control retrieval. Found: {names}")
        
    # 4. Check Engine State
    print("\n📦 Checking Engine State Serialization:")
    engine = SimulationEngine()
    engine.environment = env # Inject our env
    # Mock agent
    from app.agents.generative_agent import create_vikram
    vikram = create_vikram()
    vikram.state.location = "Mission Control/Command Deck"
    engine.agents = [vikram]
    
    state = engine.get_state()
    locs = state["world"]["locations"]
    if "Mission Control" in locs and "children" in locs["Mission Control"]:
        print("  ✅ State contains hierarchical locations")
    else:
        print("  ❌ State missing hierarchy")

if __name__ == "__main__":
    verify_hierarchy()
