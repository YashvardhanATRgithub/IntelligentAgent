# ISRO Chandrayaan-5: Generative Agents Simulation

A multi-agent simulation of ISRO's first permanent lunar base, implementing **Stanford's Generative Agents** architecture (2023) with 8 AI agents that develop emergent social behaviors.

## 🚀 Project Overview

**Setting:** Aryabhata Station - ISRO's lunar base at Moon's South Pole (Year 2035)

**Architecture:** Hybrid Goal-Based + Utility-Based Agent using the PARL Framework (Perception, Action, Reasoning, Learning)

## 🏠 Aryabhata Station (8 Modules)

| Module | Description |
|--------|-------------|
| Mission Control | Central command hub, system monitoring |
| Crew Quarters | Living spaces, personal quarters |
| Medical Bay | Health monitoring, treatment facility |
| Agri Lab | Lunar agriculture, life support systems |
| Mess Hall | Dining area, social gathering spot |
| Comms Tower | Earth communications, data relay |
| Mining Tunnel | Resource extraction operations |
| Rec Room | Recreation, relaxation area |

## 👨‍🚀 The Crew (8 Agents)

| Agent | Role | Key Traits | Internal Conflict |
|-------|------|------------|-------------------|
| Cdr. Vikram Sharma | Mission Commander | Disciplined, decisive | Hiding health condition |
| Dr. Ananya Iyer | Botanist/Life Support | Nurturing, optimistic | Guilt over leaving family |
| TARA | AI Assistant | Curious, logical | Questioning consciousness |
| Priya Nair | Crew Welfare Officer | Empathetic, perceptive | Burden of secrets |
| Aditya Reddy | Systems Engineer | Practical, methodical | Homesickness |
| Dr. Arjun Menon | Flight Surgeon | Calm, analytical | Medical confidentiality |
| Kabir Saxena | Geologist/Mining Lead | Rebellious, brilliant | Authority disagreements |
| Rohan Pillai | Communications Officer | Cheerful, anxious | Fear of isolation |

Each agent has a **Big Five personality profile** (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism), backstory, and hidden motivation that influences their behavior.

## 🧠 Features Implemented

| Feature | Description |
|---------|-------------|
| **Memory Stream** | FAISS-based vector storage with importance scoring and recency decay |
| **Bidirectional Memory** | Both speaker AND listener remember conversations |
| **Information Propagation** | Track who told whom what |
| **Relationship Tracking** | 0-100 strength scores between agents |
| **Daily Planning** | Role-based schedules that adapt dynamically |
| **Reflection Generation** | Agents form high-level insights from experiences |
| **Triggerable Events** | Inject information and watch it spread |
| **Analytics** | Track emergent behavior propagation |

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite + Three.js |
| Backend | Python + FastAPI |
| Real-time | WebSocket |
| Primary LLM | Groq API (llama-3.1-8b-instant) |
| Fallback LLM | Ollama (local) |
| Memory Store | FAISS with sentence-transformers |

## 🚀 Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv isro_env
source isro_env/bin/activate  # On Windows: isro_env\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create `backend/.env`:
```
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
NUM_AGENTS=8
```

### 3. Start Backend
```bash
cd backend
./run.sh  # Or: python -m uvicorn app.main:app --reload
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Open the Simulation
Go to http://localhost:5173 and click **Start Simulation**!

## 📡 API Endpoints

### Simulation Control
- `POST /api/simulation/start` - Start the simulation
- `POST /api/simulation/pause` - Pause the simulation
- `GET /api/state` - Get current simulation state
- `GET /api/agents` - Get all agent details

### Agent Details
- `GET /api/agents/{name}/memories` - Memory stream
- `GET /api/agents/{name}/relationships` - Relationship data
- `GET /api/agents/{name}/plan` - Daily schedule
- `GET /api/agents/{name}/full` - Complete agent info

### Events & Analytics
- `GET /api/events` - List available events
- `POST /api/events/{id}/trigger` - Trigger an event
- `GET /api/analytics` - Propagation summary

## 🎯 Demo: Emergent Behavior

1. Start the simulation with 8 agents
2. Trigger an event:
   ```bash
   curl -X POST http://localhost:8000/api/events/crew_meeting/trigger
   ```
3. Watch agents spread information through conversations
4. Check who knows about it:
   ```bash
   curl http://localhost:8000/api/analytics
   ```

## 📁 Project Structure

```
IntelligentAgent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── base.py               # Base agent class with PARL
│   │   │   ├── generative_agent.py   # 8 agent definitions
│   │   │   └── relationships.py      # Relationship tracking
│   │   ├── cognitive/
│   │   │   ├── perceive.py           # Perception module
│   │   │   └── reflect.py            # Reflection generation
│   │   ├── memory/
│   │   │   └── memory_store.py       # FAISS vector memory
│   │   ├── parl/
│   │   │   ├── parl_engine.py        # LLM reasoning (Groq/Ollama)
│   │   │   ├── planner.py            # Daily schedules
│   │   │   └── stanford_planning.py  # Long-term goal tracking
│   │   ├── simulation/
│   │   │   ├── engine.py             # Main simulation loop
│   │   │   ├── events.py             # Triggerable events
│   │   │   └── analytics.py          # Propagation tracking
│   │   ├── world/
│   │   │   └── environment.py        # 8 location modules
│   │   ├── config.py                 # Settings (LLM, agents)
│   │   └── main.py                   # FastAPI app, WebSocket
│   ├── .env                          # API keys
│   ├── requirements.txt
│   └── run.sh
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LunarBase.jsx         # 3D lunar base view
│   │   │   ├── AgentPanel.jsx        # Agent details panel
│   │   │   └── FuturisticBuildings.jsx
│   │   ├── services/
│   │   │   └── api.js                # API client
│   │   └── App.jsx                   # Main React app
│   └── package.json
│
├── deliverable1.tex                  # Design document (LaTeX)
├── D1_Agent_Design_Document.md       # Design document (Markdown)
└── README.md
```

## 🔧 Configuration

Environment variables in `backend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key | Required |
| `LLM_PROVIDER` | "groq" or "ollama" | groq |
| `NUM_AGENTS` | Number of agents (1-8) | 8 |
| `SIMULATION_SPEED` | Seconds per step | 5.0 |

## 📄 Reference

Based on: Park, J.S., et al. (2023). "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442

---

**Authors:** Yashvardhan (M250570CS), Prakash Kumar Sarangi (M251250CS)  
**Course:** CS6312E: Intelligent Agents - Capstone Project 2025-2026
