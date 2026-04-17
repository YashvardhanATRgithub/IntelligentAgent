# Project Changelog

All notable changes, errors, and fixes for the ISRO Chandrayaan-5 project.

---

## [2026-01-17] Project Initialization

### 20:06 - Project Setup Started
- Created project structure with `backend/` and `frontend/` directories
- Initialized FastAPI backend with WebSocket support

### 20:08 - Design Document Created
- Created `D1_Agent_Design_Document.md` with PEAS analysis, environment properties, PARL framework
- Created `D1_Agent_Design_Document.tex` (LaTeX version for PDF submission)

### 20:10 - Backend Development
- Created `backend/app/main.py` - FastAPI entry point
- Created `backend/app/config.py` - Configuration loader
- Created `backend/app/agents/base.py` - Base Agent class with PARL framework
- Created `backend/app/agents/generative_agent.py` - All 8 ISRO crew members defined
- Created `backend/app/world/environment.py` - Aryabhata Station with 8 locations

### 20:12 - Dependency Issues & Fixes

#### Error 1: httpx version conflict
```
ERROR: ollama 0.1.6 depends on httpx<0.26.0 and >=0.25.2
The user requested httpx==0.26.0
```
**Fix:** Changed `httpx==0.26.0` to `httpx>=0.25.2` in requirements.txt

#### Error 2: ChromaDB/onnxruntime compatibility
```
ERROR: chromadb depends on onnxruntime>=1.14.1
No matching distributions available for onnxruntime
```
**Fix:** Removed chromadb from requirements.txt (will add later with compatible version)

### 20:15 - Virtual Environment Created
- Created `isro_env` virtual environment
- Successfully installed all dependencies
- Backend server started on http://localhost:8000

### 20:17 - API Endpoints Tested
- `GET /` - Returns API status ✅
- `GET /api/agents` - Returns all 8 agents with locations ✅

### 20:21 - Frontend Created
- Scaffolded React + Vite project in `frontend/` directory
- Created `src/components/StationMap.jsx` - 8 locations grid with agent markers
- Created `src/components/AgentCard.jsx` - Agent cards with role colors
- Created `src/services/api.js` - API service for backend communication
- Created `src/hooks/useWebSocket.js` - WebSocket hook with auto-reconnect
- Created `src/App.jsx` - Main app with header, map, crew list
- Dark theme with glassmorphism effects

### 20:25 - Frontend Running
- Frontend running on http://localhost:5173
- Backend running on http://localhost:8000
- Frontend successfully connects to backend (shows "Connected")
- All 8 agents displayed on station map

### 20:35 - Full Simulation Implemented
- Created `backend/app/simulation/engine.py` - SimulationEngine with PARL loop
- Updated `backend/app/main.py` - Integrated simulation with WebSocket broadcasting
- Updated `frontend/src/App.jsx` - WebSocket integration for real-time updates
- Created `frontend/src/components/ActivityLog.jsx` - Shows live agent actions

### 20:40 - Simulation Working!
- Click "Start Simulation" → agents start moving, talking, working, resting
- Activity Log shows real-time actions with timestamps
- Simulation time displayed (Week 1, Day 1, 06:00 format)
- Agents interact with each other when in same location
- Station map shows agents moving between locations

### 20:50 - Isometric 2.5D UI Created
- Created `frontend/src/components/IsometricStation.jsx` - 2.5D station view
- Created `frontend/src/components/IsometricStation.css` - 3D room effects
- Added character sprites with color-coded avatars for each agent
- Added activity indicators (⚙️ working, 🚶 moving, 😴 resting)
- Added speech bubbles when agents talk to each other
- Added legend showing agent colors
- Updated layout: Station view on left, Activity Log on right

---

## Template for Future Entries

```
## [YYYY-MM-DD] Description

### HH:MM - What was done
- Details

### Error (if any)
```
Error message
```
**Fix:** How it was fixed
```

---

## Team Members
- [Your Name] - Backend & PARL Engine
- [Friend's Name] - Frontend & Environment
