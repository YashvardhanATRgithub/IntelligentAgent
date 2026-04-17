# ISRO Chandrayaan-5 — Project Architecture & Flow Diagrams

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph Frontend["🖥️ Frontend (React + Three.js)"]
        UI["App.jsx — Main UI"]
        LB["LunarBase.jsx — 3D Scene"]
        FB["FuturisticBuildings.jsx — 3D Buildings"]
        AP["AgentPanel.jsx — Agent Sidebar"]
        LI["LocationInterior.jsx — Location Panel"]
        WS_HOOK["useWebSocket.js — WebSocket Hook"]
        API_SVC["api.js — REST Client"]
    end

    subgraph Backend["⚙️ Backend (Python FastAPI)"]
        MAIN["main.py — FastAPI App + Endpoints"]
        CONFIG["config.py — Settings + Env Vars"]

        subgraph SimLayer["Simulation Layer"]
            ENGINE["engine.py — Simulation Loop"]
            EVENTS["events.py — Event Injector"]
            ANALYTICS["analytics.py — Info Propagation"]
            REPLAY["replay.py — Record/Playback"]
            STATE_MGR["state_manager.py — Save/Load"]
        end

        subgraph AgentLayer["Agent Layer"]
            GEN_AGENT["generative_agent.py — Agent Class"]
            BASE["base.py — BaseAgent + Memory"]
            HISTORY["history_loader.py — CSV Loader"]
            RELS["relationships.py — Social Graph"]
        end

        subgraph CogLayer["Cognitive Layer"]
            PERCEIVE["perceive.py — Perception Engine"]
            CONVERSE["converse.py — Conversation Choreographer"]
            CONV_MGR["conversation.py — Conversation Manager"]
            REFLECT["reflect.py — Reflection Engine"]
        end

        subgraph PARLLayer["PARL Engine"]
            PARL["parl_engine.py — LLM Decision Making"]
            PLANNER["planner.py — Daily Planner"]
            STAN_PLAN["stanford_planning.py — Stanford Planner"]
        end

        subgraph MemLayer["Memory Layer"]
            MEM_STORE["memory_store.py — FAISS + Embeddings"]
            SCRATCH["scratch.py — CognitiveState"]
            SPATIAL["spatial_memory.py — Mental Map"]
        end

        subgraph WorldLayer["World Layer"]
            ENV["environment.py — Station + Time"]
            PATHFIND["pathfinder.py — A* Navigation"]
        end
    end

    subgraph External["☁️ External Services"]
        GROQ["Groq Cloud API"]
        CEREBRAS["Cerebras Cloud API"]
        OLLAMA["Ollama (Local LLM)"]
        FAISS_LIB["FAISS Library"]
        SENT_TRANS["sentence-transformers"]
    end

    subgraph Data["📁 Data Files"]
        DEF_CSV["agent_definitions.csv"]
        HIST_CSV["agent_history.csv"]
        MEM_DIR["memories/ (FAISS indices)"]
        SAVE_DIR["saves/ (snapshots)"]
        REC_DIR["simulations/ (recordings)"]
    end

    UI --> LB
    UI --> AP
    UI --> LI
    LB --> FB
    UI --> WS_HOOK
    UI --> API_SVC

    API_SVC -- "REST HTTP" --> MAIN
    WS_HOOK -- "WebSocket" --> MAIN

    MAIN --> ENGINE
    MAIN --> CONFIG
    ENGINE --> PARL
    ENGINE --> ENV
    ENGINE --> PATHFIND
    ENGINE --> GEN_AGENT
    ENGINE --> CONVERSE
    ENGINE --> REPLAY
    ENGINE --> STATE_MGR

    PARL --> PERCEIVE
    PARL --> MEM_STORE
    PARL --> RELS
    PARL --> PLANNER
    PARL -- "LLM Calls" --> GROQ
    PARL -- "LLM Calls" --> CEREBRAS
    PARL -- "LLM Calls" --> OLLAMA

    GEN_AGENT --> BASE
    GEN_AGENT --> HISTORY
    BASE --> SCRATCH

    HISTORY --> DEF_CSV
    HISTORY --> HIST_CSV
    MEM_STORE --> FAISS_LIB
    MEM_STORE --> SENT_TRANS
    MEM_STORE --> MEM_DIR
    STATE_MGR --> SAVE_DIR
    REPLAY --> REC_DIR

    CONVERSE --> MEM_STORE
    CONVERSE --> RELS
    REFLECT --> MEM_STORE
    PERCEIVE --> RELS

    style Frontend fill:#1a1a2e,stroke:#e94560,color:#fff
    style Backend fill:#0f3460,stroke:#e94560,color:#fff
    style External fill:#533483,stroke:#e94560,color:#fff
    style Data fill:#2b2b2b,stroke:#e94560,color:#fff
```

---

## 2. Project Startup Flow (What Happens When You Run the Project)

```mermaid
sequenceDiagram
    participant User
    participant Terminal
    participant FastAPI as main.py (FastAPI)
    participant Config as config.py
    participant History as history_loader.py
    participant CSV as agent_definitions.csv
    participant GenAgent as generative_agent.py
    participant MemStore as memory_store.py
    participant RelMgr as relationships.py
    participant Env as environment.py
    participant Engine as engine.py
    participant PARL as parl_engine.py
    participant Browser as React Frontend

    User->>Terminal: bash run.sh (backend)
    Terminal->>FastAPI: uvicorn app.main:app --port 8000

    Note over FastAPI: @app.on_event("startup")

    FastAPI->>Config: Load settings from .env
    Config-->>FastAPI: LLM_PROVIDER, API keys, model names

    FastAPI->>History: HistoryLoader()
    History->>CSV: Read agent_definitions.csv
    CSV-->>History: 8 agent profiles (name, role, personality, backstory)
    History->>CSV: Read agent_history.csv
    CSV-->>History: Pre-seeded memories

    FastAPI->>GenAgent: create_all_agents()
    loop For each of 8 agents
        GenAgent->>GenAgent: Create GenerativeAgent instance
        GenAgent->>MemStore: Seed initial memories
        MemStore->>MemStore: Embed with sentence-transformers
        MemStore->>MemStore: Index in FAISS
    end
    GenAgent->>RelMgr: initialize_relationships(all_agent_names)
    RelMgr->>RelMgr: Create 56 pairwise relationships (8×7)

    FastAPI->>Env: Create WorldEnvironment
    Env->>Env: Define 10 station locations
    Env->>Env: Place agents at starting locations

    FastAPI->>Engine: Create SimulationEngine
    FastAPI->>PARL: Create PARLEngine + RateLimiter

    Note over FastAPI: Server is ready on port 8000 ✅

    User->>Terminal: bash run.sh (frontend)
    Terminal->>Browser: npm run dev → Vite → port 5173

    Browser->>FastAPI: WebSocket connect to ws://localhost:8000/ws
    FastAPI-->>Browser: Connection established ✅
    Browser->>FastAPI: GET /api/agents
    FastAPI-->>Browser: JSON with all 8 agents' states

    Note over Browser: 3D Lunar Base rendered with agents ✅

    User->>Browser: Clicks "Start Simulation"
    Browser->>FastAPI: POST /api/simulation/start
    FastAPI->>Engine: simulation.start()

    Note over Engine: Simulation loop begins...
```

---

## 3. Simulation Loop — What Happens Every Step

```mermaid
flowchart TD
    START["⏱️ Engine.step()"] --> ADVANCE["Advance simulation time<br/>(environment.py)"]
    ADVANCE --> LOOP["For each of 8 agents"]

    LOOP --> CHECK{"Is current<br/>action finished?"}
    CHECK -- "No, still moving/talking/working" --> CONTINUE["Continue current action<br/>(move along A* path, etc.)"]
    CONTINUE --> BROADCAST

    CHECK -- "Yes, action done" --> STORE_MEM["Store completion memory<br/>(memory_store.py)"]
    STORE_MEM --> PERCEIVE_STEP

    subgraph PARL["🧠 PARL Loop"]
        PERCEIVE_STEP["1. PERCEIVE<br/>perceive.py filters world state<br/>into 3-7 observations"]
        PERCEIVE_STEP --> REASON["2. REASON<br/>parl_engine.py builds prompt<br/>+ calls LLM (Groq/Cerebras/Ollama)"]
        REASON --> LLM_RESP["LLM returns JSON:<br/>{action, target, thought, dialogue}"]
        LLM_RESP --> SANITIZE["Sanitize response<br/>(fix hallucinations, validate targets)"]
        SANITIZE --> ACT["3. ACT<br/>Execute decision"]
    end

    ACT --> MOVE_CHECK{"What action?"}

    MOVE_CHECK -- "move" --> PATHFIND["pathfinder.py<br/>A* finds shortest path"]
    PATHFIND --> SET_PATH["Set planned_path on CognitiveState<br/>(scratch.py)"]

    MOVE_CHECK -- "talk" --> VALIDATE["Validate target agent<br/>is at same location"]
    VALIDATE --> CONVO["converse.py<br/>Multi-turn dialogue"]
    CONVO --> DIALOGUE_MEM["Store conversation<br/>as memory for both agents"]
    CONVO --> REL_UPDATE["Update relationship<br/>(relationships.py)"]

    MOVE_CHECK -- "work" --> WORK["Set timed work action<br/>at current location"]

    MOVE_CHECK -- "rest" --> REST["Set short rest duration"]

    SET_PATH --> LEARN
    DIALOGUE_MEM --> LEARN
    REL_UPDATE --> LEARN
    WORK --> LEARN
    REST --> LEARN

    LEARN["4. LEARN<br/>memory_store.py embeds<br/>+ indexes new memories"]
    LEARN --> REFLECT_CHECK{"Accumulated<br/>importance > 50?"}
    REFLECT_CHECK -- "Yes" --> DO_REFLECT["reflect.py generates<br/>2-3 high-level insights"]
    DO_REFLECT --> BROADCAST
    REFLECT_CHECK -- "No" --> BROADCAST

    BROADCAST["📡 Broadcast updated state<br/>via WebSocket to frontend"]
    BROADCAST --> NEXT["Next agent / Next step"]

    style PARL fill:#1a1a2e,stroke:#e94560,color:#fff
    style START fill:#e94560,stroke:#fff,color:#fff
    style BROADCAST fill:#0f3460,stroke:#e94560,color:#fff
```

---

## 4. File Call Graph — Which File Calls Which

```mermaid
graph LR
    subgraph Entry["Entry Points"]
        MAIN["main.py"]
        RUN["run.sh"]
    end

    subgraph Core["Core Engine"]
        ENGINE["engine.py"]
        PARL["parl_engine.py"]
    end

    subgraph Agents["Agent System"]
        GEN["generative_agent.py"]
        BASE["base.py"]
        HIST["history_loader.py"]
        REL["relationships.py"]
    end

    subgraph Cognitive["Cognitive System"]
        PERC["perceive.py"]
        CONV["conversation.py"]
        CHOREO["converse.py"]
        REFL["reflect.py"]
    end

    subgraph Memory["Memory System"]
        MSTORE["memory_store.py"]
        SCRATCH["scratch.py"]
        SPATIAL["spatial_memory.py"]
    end

    subgraph World["World System"]
        ENV["environment.py"]
        PATH["pathfinder.py"]
    end

    subgraph Sim["Simulation Mgmt"]
        EVENTS["events.py"]
        ANALYTICS["analytics.py"]
        REPLAY["replay.py"]
        STATE["state_manager.py"]
    end

    RUN --> MAIN
    MAIN --> ENGINE
    MAIN --> GEN
    MAIN --> PARL
    MAIN --> MSTORE
    MAIN --> REL
    MAIN --> ENV
    MAIN --> EVENTS
    MAIN --> REPLAY

    ENGINE --> PARL
    ENGINE --> ENV
    ENGINE --> PATH
    ENGINE --> CHOREO
    ENGINE --> MSTORE
    ENGINE --> REL
    ENGINE --> ANALYTICS
    ENGINE --> REPLAY
    ENGINE --> STATE

    PARL --> PERC
    PARL --> MSTORE
    PARL --> REL
    PARL --> SCRATCH

    GEN --> BASE
    GEN --> HIST
    GEN --> MSTORE
    GEN --> REL

    BASE --> SCRATCH

    CHOREO --> MSTORE
    CHOREO --> REL
    CONV --> MSTORE
    REFL --> MSTORE

    PERC --> REL

    STATE --> MSTORE
    STATE --> REL

    style Entry fill:#e94560,stroke:#fff,color:#fff
    style Core fill:#0f3460,stroke:#e94560,color:#fff
    style Agents fill:#533483,stroke:#e94560,color:#fff
    style Cognitive fill:#1a1a2e,stroke:#e94560,color:#fff
    style Memory fill:#2b2b2b,stroke:#e94560,color:#fff
    style World fill:#16213e,stroke:#e94560,color:#fff
    style Sim fill:#1a1a2e,stroke:#e94560,color:#fff
```

---

## 5. Frontend ↔ Backend Communication

```mermaid
sequenceDiagram
    participant React as React Frontend (Browser)
    participant WS as WebSocket (ws://localhost:8000/ws)
    participant REST as REST API (http://localhost:8000)
    participant Engine as Simulation Engine

    Note over React,Engine: Initial Page Load

    React->>REST: GET /api/agents
    REST-->>React: [{name:"Vikram", location:"Mission Control", ...}, ...]
    React->>REST: GET /api/state
    REST-->>React: {time:"06:00", is_running:false, ...}
    React->>WS: Connect

    Note over React,Engine: User Starts Simulation

    React->>REST: POST /api/simulation/start
    REST->>Engine: engine.start()
    REST-->>React: {status:"started"}

    loop Every simulation step (~1 second)
        Engine->>Engine: Process all 8 agents (PARL loop)
        Engine->>WS: Broadcast state update
        WS-->>React: {type:"state_update", agents:[...], time:"06:15"}
        React->>React: Update 3D positions + UI
    end

    Note over React,Engine: User Clicks an Agent

    React->>REST: GET /api/agents/TARA/memories
    REST-->>React: [{content:"Talked to Vikram", importance:7}, ...]
    React->>REST: GET /api/agents/TARA/relationships
    REST-->>React: {Vikram:{strength:72}, Ananya:{strength:85}, ...}
    React->>React: Show AgentPanel sidebar

    Note over React,Engine: User Changes Speed

    React->>REST: POST /api/simulation/speed {speed: 2.0}
    REST->>Engine: Set time_multiplier = 2.0
    REST-->>React: {status:"speed_updated"}
```

---

## 6. Agent Decision Flow (Single Agent Per Step)

```mermaid
flowchart LR
    A["Agent is idle"] --> B["perceive.py<br/>Scans environment"]
    B --> C["Builds observations:<br/>• Agents nearby<br/>• Dialogues heard<br/>• Events<br/>• Time of day"]
    C --> D["Ranks by attention<br/>score (1-10)"]
    D --> E["Top 3-7 passed<br/>to PARL Engine"]
    E --> F["parl_engine.py<br/>builds rich prompt"]
    F --> G["Prompt includes:<br/>• Identity/role<br/>• Location<br/>• Nearby agents<br/>• Recent memories<br/>• Schedule<br/>• Anti-repetition rules"]
    G --> H["LLM Call<br/>(Groq/Cerebras/Ollama)"]
    H --> I["JSON Response:<br/>{action, target,<br/>thought, dialogue}"]
    I --> J["Sanitize:<br/>• Fix hallucinations<br/>• Validate targets<br/>• Break loops"]
    J --> K{"Action Type?"}
    K -- "move" --> L["A* pathfinding<br/>→ walk to target"]
    K -- "talk" --> M["Multi-turn<br/>conversation"]
    K -- "work" --> N["Role-based<br/>timed task"]
    K -- "rest" --> O["Short rest"]
    L --> P["Store memory<br/>+ Update state"]
    M --> P
    N --> P
    O --> P

    style A fill:#e94560,color:#fff
    style H fill:#533483,color:#fff
    style P fill:#0f3460,color:#fff
```

---

## Quick Reference: Folder → Responsibility

```
IntelligentAgent/
├── backend/
│   ├── app/
│   │   ├── main.py              ← SERVER: FastAPI + all API endpoints + WebSocket
│   │   ├── config.py            ← SETTINGS: Reads .env, provides settings object
│   │   ├── agents/              ← WHO: Agent creation, profiles, relationships
│   │   ├── cognitive/           ← HOW THEY THINK: Perceive, converse, reflect
│   │   ├── memory/              ← WHAT THEY REMEMBER: FAISS vectors, mental state
│   │   ├── parl/                ← BRAIN: LLM calls, decision-making, planning
│   │   ├── simulation/          ← LOOP: Engine, events, save/load, replay
│   │   └── world/               ← WHERE: Station map, A* pathfinding, time
│   └── data/                    ← FILES: CSVs, saved memories, snapshots
├── frontend/
│   └── src/
│       ├── App.jsx              ← MAIN UI: State management, layout
│       ├── components/          ← VISUALS: 3D scene, agent panel, buildings
│       ├── hooks/               ← REALTIME: WebSocket connection
│       └── services/            ← HTTP: REST API client
└── *.tex / *.md                 ← DOCS: Reports, deliverables, guides
```
