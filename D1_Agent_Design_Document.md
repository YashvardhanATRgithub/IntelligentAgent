# Agent Design Document
## ISRO Chandrayaan-5: Generative Agents for Emergent Social Simulation
### Capstone Project 2025-2026

**Team Members:** [Your Name], [Friend's Name]  
**Submission Date:** January 28, 2026

---

## 1. PEAS Analysis

### 1.1 Performance Measures
The agent's performance is evaluated on:

| Metric | Description | Measurement |
|--------|-------------|-------------|
| **Goal Completion** | Successfully completing daily tasks and objectives | % of planned tasks completed |
| **Social Engagement** | Quality and frequency of interactions with other agents | Number of meaningful conversations per day |
| **Emotional Stability** | Maintaining balanced emotional state over time | Variance in mood scores |
| **Relationship Building** | Forming and maintaining social connections | Relationship strength scores (0-100) |
| **Survival Contribution** | Contributing to base operations and crew welfare | Task contribution score |

### 1.2 Environment Description

**Setting:** Aryabhata Station - ISRO's first permanent lunar base at Moon's South Pole (Year 2035)

**Physical Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│                      ARYABHATA STATION                           │
├─────────────────────────────────────────────────────────────────┤
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │  Mission  │  │   Agri    │  │   Mess    │  │    Rec    │   │
│   │  Control  │  │   Lab     │  │   Hall    │  │   Room    │   │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│   │   Crew    │  │  Medical  │  │   Comms   │  │  Mining   │   │
│   │ Quarters  │  │    Bay    │  │   Tower   │  │  Tunnel   │   │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Actuators (Actions)

| Actuator | Function | Parameters |
|----------|----------|------------|
| `move(location)` | Navigate to a location | Target location ID |
| `talk(agent, message)` | Communicate with another agent | Target agent, message content |
| `work(task)` | Perform a work activity | Task type and duration |
| `rest()` | Take rest/sleep | Duration |
| `observe()` | Actively scan environment | Observation radius |
| `interact(object)` | Use equipment/objects | Object ID |

### 1.4 Sensors (Perceptions)

| Sensor | Input Type | Range |
|--------|-----------|-------|
| `see_agents()` | Detect nearby agents | Current location |
| `hear_conversations()` | Overhear nearby dialogue | Adjacent locations |
| `check_time()` | Current simulation time | Global |
| `observe_events()` | Detect environmental events | Current location |
| `check_status()` | Self-status (energy, mood) | Internal |
| `read_messages()` | Check received communications | Personal queue |

---

## 2. Environment Properties

| Property | Classification | Justification |
|----------|---------------|---------------|
| **Observable** | Partially Observable | Agents can only perceive their current location and adjacent areas; they cannot see the entire base simultaneously |
| **Determinism** | Stochastic | Other agents' responses and decisions are unpredictable; random events (equipment failures, emergencies) can occur |
| **Episodic vs Sequential** | Sequential | Past interactions influence future relationships and behaviors; memories persist and affect decisions |
| **Static vs Dynamic** | Dynamic | The environment changes continuously as agents act; time progresses, events occur |
| **Discrete vs Continuous** | Discrete | Time advances in fixed steps (simulation ticks); locations are discrete nodes |
| **Single vs Multi-agent** | Multi-agent (Cooperative + Competitive) | 4 agents interact socially; cooperation for survival, competition for resources/attention |

---

## 3. Architecture Choice

### 3.1 Selected Architecture: Hybrid Goal-Based + Utility-Based Agent

**Justification:**

| Component | Architecture Type | Reason |
|-----------|------------------|--------|
| Daily Planning | Goal-Based | Agents have explicit objectives (work shifts, social goals) |
| Action Selection | Utility-Based | Agents weigh importance of competing goals using utility functions |
| Memory Retrieval | Utility-Based | Memories scored by recency, importance, relevance |
| Social Behavior | Goal-Based | Relationship maintenance as explicit goals |

### 3.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐   │
│  │   SENSORS   │──────▶│   MEMORY    │──────▶│  REASONING  │   │
│  │(Perception) │       │   STREAM    │       │(Reflection) │   │
│  └─────────────┘       └─────────────┘       └──────┬──────┘   │
│                                                      │          │
│                                                      ▼          │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐   │
│  │  ACTUATORS  │◀──────│   ACTION    │◀──────│   PLANNING  │   │
│  │  (Actions)  │       │  SELECTION  │       │   (Goals)   │   │
│  └─────────────┘       └─────────────┘       └─────────────┘   │
│                                                      │          │
│                              ┌────────────────────────┘          │
│                              ▼                                   │
│                       ┌─────────────┐                           │
│                       │   LEARNING  │                           │
│                       │  (Updates)  │                           │
│                       └─────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Characteristics

### 4.1 Internal Characteristics (Mental State)

| Characteristic | Type | Description |
|----------------|------|-------------|
| **Personality Traits** | Static | Big Five traits: Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism |
| **Current Emotion** | Dynamic | Mood state (happy, anxious, sad, neutral) updated by events |
| **Goals** | Dynamic | Short-term and long-term objectives |
| **Memory Stream** | Persistent | Time-stamped observations with importance scores |
| **Relationships** | Dynamic | Map of relationship strengths with other agents |
| **Energy Level** | Dynamic | Physical/mental fatigue (0-100) |

### 4.2 External Characteristics (Observable)

| Characteristic | Description |
|----------------|-------------|
| **Location** | Current position in the base |
| **Activity** | Current action being performed |
| **Expression** | Visible emotional state |
| **Interactions** | Ongoing conversations or collaborations |

### 4.3 The 4 Agents

| Agent | Role | Key Traits | Internal Conflict |
|-------|------|------------|-------------------|
| Cdr. Vikram Sharma | Mission Commander | Disciplined, decisive, responsible | Hiding health condition |
| Dr. Ananya Iyer | Botanist/Life Support | Nurturing, optimistic, dedicated | Guilt over leaving family |
| TARA | AI Assistant | Curious, logical, evolving | Questioning own consciousness |
| Priya Nair | Crew Welfare Officer | Empathetic, perceptive, trusted | Burden of everyone's secrets |

---

## 5. PARL Framework Implementation

### 5.1 Perception Module
```
Input: Environment state
Output: Observations list

Process:
1. Scan current location for agents, objects, events
2. Check personal status (energy, mood, messages)
3. Note current time and scheduled activities
4. Create timestamped observation records
```

### 5.2 Action Module
```
Input: Selected action from planning
Output: Environment modification

Available Actions:
- Movement: Navigate between locations
- Communication: Talk, listen, broadcast
- Work: Perform role-specific tasks
- Social: Build relationships, resolve conflicts
- Self-care: Rest, eat, recreation
```

### 5.3 Reasoning Module
```
Input: Current observations + Retrieved memories
Output: Insights and plans

Process:
1. Retrieve relevant memories (by recency, importance, relevance)
2. Generate reflections (high-level insights)
3. Evaluate current goals
4. Create/update action plans
```

### 5.4 Learning Module
```
Input: Action outcomes
Output: Updated memory weights

Process:
1. Store new experiences in memory stream
2. Calculate importance scores for memories
3. Update relationship strengths based on interactions
4. Consolidate old memories (compression)
```

---

## 6. Frontend and Backend Architecture

### 6.1 System Architecture

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│                 │◀──────────────────────────▶│                 │
│  React Frontend │                            │ FastAPI Backend │
│                 │         REST API           │                 │
│  • Village Map  │◀──────────────────────────▶│ • Agent Manager │
│  • Agent Cards  │                            │ • PARL Engine   │
│  • Activity Log │                            │ • World State   │
│  • Time Control │                            │ • LLM Interface │
│                 │                            │                 │
└─────────────────┘                            └────────┬────────┘
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                            │ Gemini Pro  │     │   Ollama    │     │  ChromaDB   │
                            │  (Primary)  │     │ (Fallback)  │     │  (Memory)   │
                            └─────────────┘     └─────────────┘     └─────────────┘
```

### 6.2 Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite |
| Backend | Python + FastAPI |
| Real-time | WebSocket |
| Primary LLM | Groq API (llama-3.1-8b-instant) |
| Fallback LLM | Ollama (local) |
| Memory Store | FAISS (vector DB) |

### 6.3 Data Flow

1. **User Input** → Start simulation with parameters
2. **Backend** → Initialize agents with personalities
3. **Simulation Loop**:
   - Each agent: Perceive → Reason → Act → Learn
   - Update world state
   - Emit events via WebSocket
4. **Frontend** → Render agent positions, activities, conversations
5. **Logging** → Store interactions for analysis

---

## References

1. Park, J.S., et al. (2023). "Generative Agents: Interactive Simulacra of Human Behavior." arXiv:2304.03442
2. Russell, S., & Norvig, P. (2020). "Artificial Intelligence: A Modern Approach." 4th Edition
3. ISRO. (2023). "Chandrayaan-3 Mission Overview." Indian Space Research Organisation

---

*Document Version: 1.0 | Last Updated: January 2026*
