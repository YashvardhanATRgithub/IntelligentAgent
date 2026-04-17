# Diagram Explanations — What to Say to the Professor

---

## Diagram 1: High-Level System Architecture

**What to say:**

"Sir, this is the overall architecture of our project. It has 4 main parts:

1. **Frontend** — Built with React and Three.js. It renders a 3D lunar base in the browser where you can see all 8 agents moving around. The main file is `App.jsx` which manages the UI, and `LunarBase.jsx` which renders the 3D scene with animated astronauts.

2. **Backend** — Built with Python FastAPI. It has 6 layers:
   - **Agent Layer** — Defines who the agents are (8 lunar station crew members with unique personalities and backstories)
   - **Cognitive Layer** — How they think — perception, conversation, and reflection engines inspired by Stanford's generative agents paper
   - **PARL Engine** — The brain. It calls the LLM (Groq/Cerebras) to make decisions using the Perceive-Act-Reason-Learn loop
   - **Memory Layer** — Uses FAISS vector database with sentence-transformers to store and retrieve memories semantically
   - **World Layer** — The physical station with 10 locations and A* pathfinding for navigation
   - **Simulation Layer** — Controls the main loop, events, save/load, and replay

3. **External Services** — We use cloud LLM APIs (Groq or Cerebras) for agent reasoning, FAISS for vector search, and sentence-transformers for generating embeddings.

4. **Data Files** — Agent profiles stored in CSV, memories persisted as JSON + FAISS indices, simulation snapshots for checkpointing.

The frontend communicates with the backend via REST API for commands and WebSocket for real-time state updates."

---

## Diagram 2: Startup Flow

**What to say:**

"This diagram shows what happens step-by-step when we start the project:

1. We run `bash run.sh` in the backend folder. This starts the FastAPI server using uvicorn on port 8000.

2. On startup, the server:
   - Loads configuration from `.env` file (API keys, LLM provider, model name)
   - Reads `agent_definitions.csv` to load all 8 agent profiles — their names, roles, personality traits, backstories, and secrets
   - Creates all 8 GenerativeAgent instances
   - Seeds initial memories into the FAISS memory store using sentence-transformers embeddings
   - Initializes 56 pairwise relationships (8 agents × 7 others)
   - Creates the world environment with 10 station locations
   - Places agents at their primary workspaces

3. Then we run `bash run.sh` in the frontend folder. This starts Vite dev server on port 5173.

4. The browser connects via WebSocket, fetches all agent data through REST API, and renders the 3D lunar base with all agents visible.

5. When the user clicks 'Start Simulation', the frontend sends a POST request, and the simulation loop begins."

---

## Diagram 3: Simulation Loop (Every Step)

**What to say:**

"This is the core of the project — what happens every simulation step:

1. The engine advances simulation time and iterates through each agent.

2. For each agent, it first checks: is the current action finished? If not, the agent continues (e.g., keeps walking along the A* path).

3. If the action is done, the **PARL loop** kicks in:
   - **P (Perceive)** — The perception engine scans the environment and filters it into 3-7 prioritized observations based on relationship strength, role relevance, and spatial proximity. Agents can't see everything — they have bounded attention, just like humans.
   - **R (Reason)** — The PARL engine builds a rich prompt with the agent's identity, location, nearby agents, recent memories, schedule, and anti-repetition rules. This prompt is sent to the LLM (Groq/Cerebras), which returns a JSON decision: action type, target, thought, and optional dialogue.
   - **A (Act)** — The decision is executed: move (A* pathfinding), talk (multi-turn conversation), work (timed role-based task), or rest.
   - **L (Learn)** — New memories are embedded using sentence-transformers and indexed in FAISS. If accumulated memory importance exceeds 50, the reflection engine generates 2-3 high-level insights.

4. After processing, the updated state is broadcast to the frontend via WebSocket for real-time visualization."

---

## Diagram 4: File Call Graph

**What to say:**

"This diagram shows which file depends on which other file — the complete dependency chain:

- Everything starts from `main.py` — it initializes the simulation engine, creates agents, and sets up the PARL engine.
- The **engine** calls the PARL engine for decisions, the environment for world state, the pathfinder for A* navigation, and the choreographer for conversations.
- The **PARL engine** uses the perception engine to filter observations, the memory store for context retrieval, and relationships for social awareness.
- **Agents** are created by `generative_agent.py` which reads definitions from `history_loader.py`, creates base agents using `base.py`, and seeds memories into the memory store.

This modular design means each component can be tested and modified independently."

---

## Diagram 5: Frontend ↔ Backend Communication

**What to say:**

"This shows exactly how the frontend and backend talk to each other:

- **REST API** (HTTP) is used for one-time requests:
  - `GET /api/agents` — Fetch all 8 agents' current state
  - `GET /api/state` — Get simulation status and time
  - `POST /api/simulation/start` — Start the simulation
  - `GET /api/agents/TARA/memories` — Get a specific agent's memory stream *(when user clicks an agent)*

- **WebSocket** is used for continuous real-time updates:
  - Every simulation step, the backend broadcasts the full state (agent positions, activities, time) to all connected frontends
  - This is why the 3D scene updates live without the user refreshing the page

- When the user clicks an agent in the 3D scene, the frontend makes additional REST calls to fetch that agent's memories and relationships, then displays them in the sidebar panel."

---

## Diagram 6: Agent Decision Flow

**What to say:**

"This is a linear view of how a single agent makes one decision:

1. Agent finishes its current task and becomes idle.
2. The perception engine scans everything happening around the agent.
3. It builds observations: which agents are nearby, what dialogues are happening, any events, time of day.
4. These are ranked by attention score (1-10) based on relationship strength, role-relevant keywords, and whether someone is speaking directly to this agent.
5. Only the top 3-7 observations pass through — this simulates human cognitive limits.
6. The PARL engine builds a detailed prompt with the agent's full identity, location, observations, recent memories, daily schedule, and anti-repetition rules.
7. This prompt goes to the LLM, which returns a JSON with: what action to take, who/what to target, an inner thought, and optional dialogue.
8. The response is sanitized — we fix hallucinated locations, validate that target agents actually exist, and break repetitive action loops.
9. The action is executed: movement via A* pathfinding, multi-turn conversation, timed work task, or rest.
10. Finally, the outcome is stored as a new memory in the FAISS vector store."

---

## Quick Tips for the Demo

- **Start backend first**, then frontend
- **Click agents** in the 3D scene to show the professor their personality traits, memories, and relationships
- **Trigger an event** via the API to show emergent behavior (e.g., how information spreads from one agent to others)
- **Point out conversations** — agents autonomously decide to talk to each other based on proximity and relationship strength
- **Show the terminal** — the backend prints live decision logs like `✅ [PARL] TARA decided: move (Agri Lab)` which demonstrates the PARL loop in action
