# ISRO Chandrayaan-5 — Complete File-by-File Guide

## Root Directory

| File | Purpose |
|------|---------|
| `README.md` | Project overview, setup instructions, architecture diagram |
| `CHANGELOG.md` | Version history and feature changelog |
| `.gitignore` | Git ignore rules |
| `D1_Agent_Design_Document.md` | Deliverable 1 in markdown (agent design doc) |
| `D1_Agent_Design_Document.tex` | Deliverable 1 in LaTeX |
| `deliverable1.tex` | Alternate LaTeX version of D1 |
| `D2_Formal_Report.tex` | Deliverable 2 LaTeX (Tool integration, Traceability, Task completion) |
| `D2_Formal_Report1.tex` | Alternate version of D2 |
| `*.pdf` | Professor's evaluation criteria and project title suggestions |

---

## `backend/` — Python FastAPI Server

### Root Files

| File | Purpose |
|------|---------|
| `.env` / `.env.example` | Environment variables (API keys, LLM provider, model names, sim speed) |
| `requirements.txt` | Python dependencies (fastapi, uvicorn, httpx, faiss-cpu, sentence-transformers, etc.) |
| `run.sh` | Shell script to start the backend server (`uvicorn app.main:app`) |
| `stop.sh` | Shell script to stop the backend server |
| `verify_hierarchy.py` | Verifies agent class hierarchy is set up correctly |
| `verify_integration.py` | Integration test script — checks all modules load and work together |

---

### `backend/app/` — Main Application Package

| File | What It Does |
|------|-------------|
| `config.py` | **Settings class.** Loads env vars for LLM provider selection (`groq`/`cerebras`/`ollama`), API keys, model names, simulation speed, number of agents (8), and FAISS memory persist directory. |
| `main.py` | **FastAPI app entry point.** Defines 15+ REST endpoints (`/api/state`, `/api/agents`, `/api/agents/{name}/memories`, `/api/agents/{name}/relationships`, `/api/simulation/start`, `/api/simulation/stop`, `/api/simulation/speed`, `/api/analytics`, `/api/replays`, etc.) and WebSocket endpoint (`/ws`). Houses the `ConnectionManager` for multi-client WebSocket broadcasting. Initializes simulation engine, PARL engine, agents, and memory store on startup. |

---

### `backend/app/agents/` — Agent Definitions & Creation

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `BaseAgent`, `Memory`, `Personality`, `GenerativeAgent`, `create_all_agents`. |
| `base.py` | **BaseAgent abstract class (316 lines).** Defines the `Memory` dataclass (id, content, timestamp, importance, type, related_agents, location) with a `relevance_score()` method combining recency decay + importance + keyword matching. Defines `Personality` dataclass (Big Five traits: openness, conscientiousness, extraversion, agreeableness, neuroticism). `BaseAgent` holds: name, role, personality, backstory, secret, `CognitiveState`, `memory_stream`, `state` (location/activity/energy/mood). Has `to_dict()` for serializing the full agent state to the frontend. |
| `generative_agent.py` | **GenerativeAgent class (240 lines).** Extends `BaseAgent`. Factory method `create_from_history()` loads agent definitions from CSV via `HistoryLoader`. `create_all_agents()` function creates all 8 agents from `agent_definitions.csv`, loads their history from `agent_history.csv`, seeds initial memories into the global `MemoryStore`, and initializes relationships via `RelationshipManager`. |
| `history_loader.py` | **History & definition loader (600 lines).** Defines `AgentDefinition` dataclass (name, role, age, Big Five traits, backstory, secret, innate/learned traits, lifestyle, internal conflict, primary workspace). Defines `HistoryEvent` dataclass. `HistoryLoader` class reads/writes `agent_definitions.csv` and `agent_history.csv`. `create_default_agent_definitions()` hardcodes all 8 agent profiles (Cdr. Vikram Sharma, Dr. Ananya Iyer, TARA, Dr. Priya Nair, Lt. Aditya Menon, Dr. Arjun Reddy, Kabir Ahmed, Rohan Kapoor) with rich backstories, secrets, and personality traits. `create_default_agent_history()` provides seed memories. `generate_inner_thought()` converts external "whispers" into agent inner thoughts via LLM. |
| `relationships.py` | **RelationshipManager (152 lines).** Tracks bidirectional relationships between all agent pairs. Each `Relationship` has: strength (0–100), sentiment (positive/neutral/negative), interaction count, last interaction time. `update_after_interaction()` adjusts strength (+3 for positive, −5 for negative, +1 for neutral). `describe_relationship()` maps strength to labels (close friend / friendly colleague / acquaintance / distant / strained). `get_relationship_scores()` normalizes scores to 0–1 for the perception engine. Global singleton: `relationship_manager`. |

---

### `backend/app/cognitive/` — Higher-Level Cognitive Functions

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `ConversationChoreographer`, `ConversationContext`, `ConversationResult`. |
| `perceive.py` | **PerceptionEngine (355 lines).** Stanford-style attention system. Agents have bounded attention (3–7 items max). Filters raw world state into prioritized `Observation` objects. Each observation has an `attention_score` (1–10) calculated from: relationship strength boost, role-relevant keyword matching, dialogue directed at agent, emergency event boost. Outputs a `PerceivedEnvironment` with categorized observations (agent presence, agent activity, dialogue, location state, events, environment). Role-interest keywords map each role to relevant topics (e.g., Botanist → plants, growth, oxygen). Global singleton: `perception_engine`. |
| `conversation.py` | **ConversationManager (309 lines).** Multi-turn dialogue system. Tracks `ActiveConversation` objects (participants, turns, staleness check). `generate_utterance()` builds a memory-informed LLM prompt and generates dialogue (supports Groq and Ollama). `generate_reply()` adds incoming message to history, then generates response. `summarize_conversation()` uses LLM to create a 1–2 sentence summary stored as a memory for both agents. Includes fallback responses when LLM fails. Global singleton: `conversation_manager`. |
| `converse.py` | **ConversationChoreographer (669 lines).** Advanced turn-based dialogue system. `ConversationContext` tracks initiator, target, topic, location, turns, max turns, whether conversation should end. `ConversationResult` holds all turns + summary. `ConversationChoreographer` orchestrates full multi-turn conversations: generates opening line, manages turn-taking, detects natural endings, generates summaries, and stores conversation memories. Has per-provider LLM call routing (Groq, Cerebras, Ollama). |
| `reflect.py` | **ReflectionEngine (314 lines).** Stanford-style insight generation. Triggered when accumulated memory importance exceeds threshold (50.0). Generates 2–3 high-level reflections via LLM in categories: SELF, SOCIAL, SITUATIONAL, GOAL, INSIGHT. Each reflection is stored as a high-importance (8–9) memory. Has configurable thresholds: min 5 memories to reflect, cooldown of 10 steps between reflections, max 20 memories considered per reflection. Has fallback reflection generation without LLM. Global singleton: `reflection_engine`. |

---

### `backend/app/memory/` — Memory & State Systems

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `memory_store` (global MemoryStore instance). |
| `memory_store.py` | **MemoryStore (18KB).** FAISS + sentence-transformers memory system. Uses `all-MiniLM-L6-v2` (384-dim embeddings). Per-agent FAISS `IndexFlatIP` indices with cosine similarity. `add_memory()` embeds and indexes memories. `retrieve_memories()` uses Stanford-style scoring: α·recency + β·relevance + γ·importance (α=0.3, β=0.4, γ=0.3). Persists memories to JSON on disk every 5 entries. Supports memory count, recent memory retrieval, and bulk loading. Global singleton: `memory_store`. |
| `scratch.py` | **CognitiveState (21KB).** The agent's "scratch pad" — full mental state. Identity Stable Set (name, role, age, personality traits, backstory). Spatial state (`world_location`). Action state (`action_status`, `act_description`, `act_emoji`, `action_duration`, `action_start_time`). Path state (`planned_path[]`, `path_position`, `path_computed`). Conversation state (`chatting_with`, `conversation_end_time`, `talk_cooldowns{}`). Schedule and planning state. Methods: `start_action()`, `end_action()` (clears path state), `is_action_finished()` (checks elapsed sim-time), `to_dict()` / `from_dict()` for serialization. `create_cognitive_state_for_agent()` factory function. |
| `spatial_memory.py` | **SpatialMemory (12KB).** Agent's mental map of the station. Tracks known locations, visited locations, objects seen at locations, other agents' last known positions. Allows querying "where did I last see X?" and "what's at location Y?". Used by the PARL engine to inform navigation decisions. |

---

### `backend/app/parl/` — PARL Engine (Perception, Action, Reasoning, Learning)

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `PARLEngine`. |
| `parl_engine.py` | **PARLEngine (594 lines, 27KB).** The brain of the system. Supports 3 LLM providers (Groq, Cerebras, Ollama) with a `RateLimiter` class (token-aware, RPM/TPM tracking, FCFS queue via asyncio.Lock). `build_prompt()` constructs detailed context-rich prompts including: agent identity, location, nearby agents, recent memories, role-based workspace hints, schedule, anti-repetition rules, and movement encouragement. `get_decision()` calls the LLM and returns JSON: `{"action":"move/talk/work/rest", "target":"...", "thought":"...", "dialogue":"..."}`. `_sanitize_response()` validates and fixes LLM output (hallucination correction, invalid action fixes, target validation, repetition breaking). Maintains per-agent `action_history` (last 3 actions). |
| `planner.py` | **DailyPlanner (38KB).** Stanford-style daily planning system. Generates hourly schedules for agents based on their role, personality, and current goals. Creates structured plans with time slots, activities, and locations. Supports plan revision when events occur. LLM-powered plan generation with fallback templates. Tracks plan adherence and deviations. Global singleton: `daily_planner`. |
| `stanford_planning.py` | **StanfordPlanner (14KB).** Implements the original Stanford generative agents planning algorithm. Hierarchical planning: broad strokes → hourly plans → 5-minute decomposition. Plan revision system triggered by new observations or events. Integrates with memory retrieval for plan context. |

---

### `backend/app/simulation/` — Simulation Engine & Management

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `SimulationEngine`. |
| `engine.py` | **SimulationEngine (18.5KB).** The main simulation loop. `step()` advances time, calls `_process_agent()` for each agent. `_process_agent()` checks if current action is finished → if so, calls PARL engine for new decision → dispatches to handler. `_execute_decision()` maps action types to handlers: **Move** (A* via `StationNavigator`, sets planned path, teleports on completion), **Talk** (validates target, initiates conversation via `ConversationChoreographer`, sets timed duration), **Work** (timed role-appropriate action), **Rest** (short duration). Maintains `activity_log` for frontend. Handles movement step-by-step along A* path. |
| `events.py` | **EventManager (128 lines).** Inject-able events for emergent behavior demo (inspired by Stanford's Valentine's Day party experiment). 6 pre-defined events: Emergency Crew Meeting, Supply Shortage, Medical Concern, Mining Discovery, Secret Transmission, Surprise Celebration. Each targets a specific agent and injects a memory. Events can be triggered via API and track triggered state. Global singleton: `event_manager`. |
| `analytics.py` | **PropagationTracker (103 lines).** Tracks how information spreads through the agent network. Records initial knowledge sources, tracks propagation chains (who told whom), and provides analysis of event spread (how many agents know, what path the info took). Global singleton: `propagation_tracker`. |
| `replay.py` | **SimulationRecorder & ReplaySystem (657 lines).** Frame-by-frame recording of simulation state. Supports JSON and compressed gzip formats. Playback with arbitrary speed control, jump to any point. Export/import for sharing simulations. Recording metadata includes creation time, duration, frame count. |
| `state_manager.py` | **StateManager (335 lines).** Save/load simulation checkpoints to JSON. Auto-checkpoint system (every 50 steps, max 20 snapshots). `SimulationSnapshot` captures full state: sim time, all agent states, locations, events, memory counts, relationships, plans, step count. `restore_snapshot()` reloads a saved state. `export_for_analysis()` dumps complete simulation data for external analysis. Global singleton: `state_manager`. |

---

### `backend/app/world/` — World Environment & Navigation

| File | What It Does |
|------|-------------|
| `__init__.py` | Exports `WorldEnvironment`, `StationNavigator`. |
| `environment.py` | **WorldEnvironment (10KB).** Manages the physical simulation world. Defines all station locations (Mission Control, Agri Lab, Medical Bay, Mining Tunnel, Comms Tower, Crew Quarters, Mess Hall, Rec Room, Airlock, Observatory). Tracks which agents are at which locations. Manages simulation time (week/day/hour/minute with configurable speed multiplier). `move_agent()` changes an agent's location and returns a success status. `get_agents_at_location()` for spatial queries. `to_dict()` serializes the entire world state for the frontend. |
| `pathfinder.py` | **StationNavigator (14KB).** A* pathfinding for the lunar station. Defines the station layout as a weighted graph (locations are nodes, corridors are edges with travel-time weights). `find_path()` returns the shortest path between two locations. `get_travel_time()` estimates movement duration. Handles edge cases like same-location and unreachable destinations. Used by the simulation engine for agent movement. |

---

### `backend/data/` — Data Files

| File | What It Does |
|------|---------|
| `agent_definitions.csv` | CSV with all 8 agents' profiles: name, role, age, Big Five scores, backstory, secret, traits, workspace |
| `agent_history.csv` | Pre-seeded historical memories for agents (events that happened before the simulation starts) |
| `memories/` | Directory where FAISS memory indices and JSON memory files are persisted per-agent |
| `saves/` | Directory for simulation snapshots/checkpoints |

### `backend/simulations/` — Recordings

Contains 13 timestamped recording directories (e.g., `recording_20260131_233004/`), each storing a complete frame-by-frame simulation recording for replay.

---

## `frontend/` — React + Three.js Frontend

### Root Files

| File | Purpose |
|------|---------|
| `index.html` | HTML entry point, loads the React app |
| `package.json` | Node dependencies: react, three, @react-three/fiber, @react-three/drei, etc. |
| `vite.config.js` | Vite build configuration |
| `eslint.config.js` | ESLint rules |
| `run.sh` | Shell script to start the dev server (`npm run dev`) |

---

### `frontend/src/` — Source Code

| File | What It Does |
|------|-------------|
| `main.jsx` | React entry point, renders `<App />` into the DOM. |
| `App.jsx` | **Main application component (7KB).** Manages global state: simulation status, agents data, selected agent, time display. Connects to WebSocket for real-time updates. Renders the 3D lunar base scene, agent panel sidebar, control buttons (Start/Stop/Speed), and time display. Handles agent selection and location panel toggling. |
| `App.css` | Global app styles: layout, header, control buttons, time display, sidebar animations. |
| `index.css` | Base CSS reset and root styles. |

---

### `frontend/src/components/` — React Components

| File | What It Does |
|------|-------------|
| `LunarBase.jsx` | **Main 3D scene (36KB).** The centerpiece of the frontend. Uses `@react-three/fiber` and Three.js. Contains: `Astronaut` component (animated 3D astronaut with smooth position interpolation, name labels, click handlers), `Scene` component (lighting, camera, ground plane, dome, stars), location markers for all station areas. Handles agent click events to show the `AgentPanel`. The `LunarBase` wrapper manages the `Canvas` and passes agents data into the 3D scene. |
| `FuturisticBuildings.jsx` | **3D building models (24KB).** Procedurally generated 3D models for each station location using Three.js primitives. Each building has a unique design: Mission Control (dome with antenna), Agri Lab (greenhouse), Medical Bay (cross symbol), Mining Tunnel (excavation site), Comms Tower (tall antenna array), Crew Quarters (habitat modules), Mess Hall, Rec Room, Airlock (circular door), Observatory (telescope dome). Includes glowing effects, labels, and click handlers. |
| `AgentPanel.jsx` | **Agent info sidebar (8KB).** Displays selected agent's details: name, role, location, current activity, emoji status indicator, personality traits (Big Five as progress bars), memory stream (recent memories with timestamps), relationship scores with other agents. |
| `AgentPanel.css` | Styles for the agent panel: sliding sidebar animation, card layouts, trait bars, memory list styling. |
| `LocationInterior.jsx` | **Location detail panel (5KB).** Shows which agents are currently at a clicked location, what activities are happening there, and location status. |
| `LocationInterior.css` | Styles for the location interior panel. |

---

### `frontend/src/hooks/` — Custom React Hooks

| File | What It Does |
|------|-------------|
| `useWebSocket.js` | **WebSocket hook (50 lines).** Custom React hook for managing WebSocket connection to `ws://localhost:8000/ws`. Handles connection, reconnection (auto-retry every 3 seconds on disconnect), message parsing, and provides `isConnected`, `lastMessage`, and `sendMessage()` to consuming components. |

---

### `frontend/src/services/` — API Client

| File | What It Does |
|------|-------------|
| `api.js` | **REST API client (56 lines).** Wrapper functions for backend endpoints: `getAgents()`, `getState()`, `startSimulation()`, `pauseSimulation()`. Also exports `createWebSocket()` for establishing WebSocket connections with message/error/close handlers. Base URL: `http://localhost:8000`. |
