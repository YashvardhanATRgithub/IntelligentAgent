# ISRO Chandrayaan-5: Generative Agents Simulation

A multi-agent simulation of ISRO's first permanent lunar base, implementing **Stanford's Generative Agents** architecture (2023) with 8 AI agents that develop emergent social behaviors.

## 🚀 Project Overview

**Setting:** Aryabhata Station - ISRO's lunar base at Moon's South Pole (Year 2035)

**Architecture:** PARL Framework (Perception, Action, Reasoning, Learning) with Stanford-style features.

## 👨‍🚀 The Crew (8 Agents)

| Agent | Role | Key Traits |
|-------|------|------------|
| Cdr. Vikram Sharma | Mission Commander | Disciplined, decisive |
| Dr. Ananya Iyer | Botanist/Life Support | Nurturing, optimistic |
| TARA | AI Assistant | Curious, logical, evolving |
| Priya Nair | Crew Welfare Officer | Empathetic, perceptive |
| Aditya Reddy | Systems Engineer | Practical, homesick |
| Dr. Arjun Menon | Flight Surgeon | Calm, analytical |
| Kabir Saxena | Geologist/Mining Lead | Rebellious, brilliant |
| Rohan Pillai | Communications Officer | Cheerful, anxious |

## 🧠 Stanford Features Implemented

| Feature | Description |
|---------|-------------|
| **Memory Stream** | FAISS-based with importance scoring and decay |
| **Bidirectional Memory** | Both speaker AND listener remember conversations |
| **Information Propagation** | Track who told whom what |
| **Relationship Tracking** | 0-100 strength with sentiment |
| **Daily Planning** | Role-based schedules |
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
| Memory Store | FAISS (vector DB) |

## 🚀 Quick Start

### Backend
```bash
cd backend
python -m venv isro_env
source isro_env/bin/activate
pip install -r requirements.txt
# Add GROQ_API_KEY to .env
./run.sh
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and click "Start Simulation"!

## 📡 API Endpoints

### Agent Details
- `GET /api/agents/{name}/memories` - Memory stream
- `GET /api/agents/{name}/relationships` - Relationship data
- `GET /api/agents/{name}/plan` - Daily schedule
- `GET /api/agents/{name}/full` - Complete info

### Events & Analytics
- `GET /api/events` - List available demo events
- `POST /api/events/{id}/trigger` - Trigger an event
- `GET /api/analytics` - Propagation summary
- `GET /api/analytics/event/{id}` - Event spread analysis

## 🎯 Demo: Emergent Behavior

1. Start simulation with 8 agents
2. Trigger an event:
   ```bash
   curl -X POST http://localhost:8000/api/events/crew_meeting/trigger
   ```
3. Watch agents spread information through conversations
4. Check who knows about the meeting:
   ```bash
   curl http://localhost:8000/api/analytics/event/crew_meeting
   ```

## 📁 Project Structure

```
IntelligentAgent/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── generative_agent.py  # 8 agent definitions
│   │   │   └── relationships.py     # Relationship tracking
│   │   ├── parl/
│   │   │   ├── parl_engine.py       # LLM reasoning
│   │   │   └── planner.py           # Daily schedules
│   │   ├── simulation/
│   │   │   ├── engine.py            # Main loop
│   │   │   ├── events.py            # Demo events
│   │   │   └── analytics.py         # Propagation tracking
│   │   └── memory/
│   │       └── memory_store.py      # FAISS memory
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       └── components/
│           ├── LunarBase.jsx        # 3D visualization
│           └── AgentPanel.jsx       # Agent details panel
│
├── README.md
└── D1_Agent_Design_Document.md
```

## 📄 Reference

Based on: Park, J.S., et al. (2023). "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442
