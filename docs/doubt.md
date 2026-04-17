# Project Doubts — Q&A

---

### 1. What is FastAPI and why is it used here?

**FastAPI** is a modern Python web framework for building APIs. Think of it as the "server" that listens for requests from the frontend (or any client) and responds with data.

**Why here?** Our simulation runs in Python. The React frontend (running in a browser) needs to communicate with it. FastAPI acts as the bridge — it exposes URLs (endpoints) that the frontend can call to get agent data, start/stop the simulation, etc. It was chosen over alternatives like Flask because:
- It's **async** — can handle multiple agents making LLM calls simultaneously without blocking.
- It has built-in **WebSocket** support — needed for real-time updates to the frontend.
- It auto generates API documentation at `/docs`.

---

### 2. What is a REST endpoint?

A **REST endpoint** is just a URL on the server that does something when you visit it.

For example:
- `GET http://localhost:8000/api/agents` → Returns all 8 agents' data as JSON.
- `POST http://localhost:8000/api/simulation/start` → Starts the simulation.
- `GET http://localhost:8000/api/agents/TARA/memories` → Returns TARA's memory stream.

**REST** is a convention: you use `GET` to read data, `POST` to create/trigger actions, `PUT` to update, `DELETE` to remove. Each URL is called an "endpoint" because it's the end point of a communication channel between the frontend and backend.

---

### 3. Why use `config.py` if `.env` file is already there?

They serve different purposes:

- **`.env` file** — Stores raw key-value pairs like `GROQ_API_KEY=gsk_abc123`. It's a flat text file. Python code can't directly use it as variables.
- **`config.py`** — Reads those raw values from `.env` and converts them into a proper Python `Settings` object with type validation, defaults, and structure.

For example, `.env` has `NUM_AGENTS=8` as a string. `config.py` reads it, converts it to an integer, and makes it accessible as `settings.NUM_AGENTS` (an actual `int`). It also sets sensible defaults — if you forget to set `LLM_PROVIDER` in `.env`, `config.py` defaults it to `"groq"`.

**In short:** `.env` = raw storage, `config.py` = structured access with validation.

---

### 4. What does "Agents have bounded attention (3–7 items max)" mean?

In real life, you can't pay attention to everything around you at once. If you're in a crowded room, you might notice 5–6 things (a friend waving, loud music, someone spilling a drink) but ignore the rest.

Our agents work the same way. When the `PerceptionEngine` runs, it might detect 15+ things happening (other agents present, their activities, dialogues, events, time of day). But instead of feeding ALL of that to the LLM (which would be expensive and unrealistic), it **ranks** them by attention score and only keeps the **top 3–7 most relevant** observations.

So if Cdr. Vikram is in Mission Control:
- He'll **notice** an emergency alert (attention score = 9) ✅
- He'll **notice** Dr. Priya talking to him directly (score = 8) ✅
- He'll **ignore** that it's 14:30 (score = 2) ❌

This makes the agents behave more realistically — they have cognitive limits, just like humans.

---

### 5. What is a multi-turn dialogue system?

A **single-turn** dialogue is: Agent A says something → done.

A **multi-turn** dialogue is a back-and-forth conversation:
1. **TARA:** "Good afternoon, Commander. How are systems looking?"
2. **Vikram:** "All nominal, TARA. Any updates from Earth?"
3. **TARA:** "Received a status check from ISRO. All clear."
4. **Vikram:** "Good. Carry on."

The system tracks the conversation **history** (what was said before), so each new reply is **contextual** — TARA's line 3 makes sense because she "remembers" Vikram asked about Earth in line 2. When the conversation ends, it generates a **summary** and stores it as a memory for both agents.

---

### 6. How to play files saved using `replay.py`?

The recordings in `backend/simulations/` are **not video files** — they're JSON data snapshots of every simulation step (agent positions, actions, dialogues, etc.).

To replay them, you use the **API endpoint**:
1. Start the backend server (`cd backend && bash run.sh`).
2. Call `GET http://localhost:8000/api/replays` to list available recordings.
3. Call `POST http://localhost:8000/api/replays/{recording_id}/play` to start playback.
4. The frontend will show the agents moving and acting exactly as they did during the original simulation, at whatever speed you set.

The replay system loads the saved frames and feeds them to the frontend via WebSocket, just like a live simulation would — but from recorded data instead of real-time LLM decisions.

---

### 7. What is FAISS and why is it used here?

**FAISS** (Facebook AI Similarity Search) is a library by Meta for efficiently searching through large collections of vectors (arrays of numbers).

**Why here?** Each agent's memory (e.g., "I talked to Vikram about the mission") is converted into a **384-dimensional vector** (a list of 384 numbers) using a sentence-transformer model. This vector numerically represents the *meaning* of that sentence.

When an agent needs to recall relevant memories (e.g., "What do I know about Vikram?"), FAISS instantly finds the memories whose vectors are most **similar** to the query — even if the exact words don't match. For example, "I had a conversation with Commander Sharma about supplies" would match the query "Vikram" because the sentence-transformer understands they refer to the same person contextually.

**Without FAISS:** You'd have to compare every memory one by one (slow for hundreds of memories).
**With FAISS:** It uses optimized indexing to find the top matches almost instantly.

---

### 8. Why 13 recording directories? Is it fixed or does it change?

**It is NOT fixed.** The number changes every time you run and record a simulation.

Each time you start a simulation with recording enabled, a new directory is created with a timestamp name like `recording_20260210_225819` (meaning: recorded on 2026-02-10 at 22:58:19). The 13 you see now are just from past simulation runs during development. If you run the simulation 5 more times, there would be 18 directories. If you delete some, the count goes down.

There is no limit hardcoded — they'll keep accumulating until you manually clean them up.

---

### 9. What is Vite?

**Vite** (pronounced "veet", French for "fast") is a **build tool** for frontend projects. It does two things:

1. **Development server** — When you run `npm run dev`, Vite serves your React files to the browser with **hot reload** (you edit code → the browser updates instantly without refreshing).
2. **Production bundler** — When you run `npm run build`, it compresses and optimizes all your JS/CSS files into a small `dist/` folder ready for deployment.

**Why Vite over alternatives?** It's significantly faster than older tools like Webpack because it uses native ES modules and only compiles what's needed.

---

### 10. What is ESLint?

**ESLint** is a **code quality checker** for JavaScript/JSX. It scans your code and flags:
- Potential bugs (e.g., using an undefined variable)
- Style violations (e.g., missing semicolons, inconsistent quotes)
- Bad practices (e.g., unused imports)

The `eslint.config.js` file defines the rules for this project. It doesn't change how the app works — it just helps catch mistakes during development. Think of it as a spell-checker, but for code.

---

### 11. What is a Hook and what are React Hooks?

In React, a **component** is a function that returns some UI (HTML). But sometimes that component needs to do extra things like:
- Store data that changes over time (state)
- Connect to a server (side effects)
- Share logic between components

**React Hooks** are special functions (starting with `use`) that let you "hook into" React features inside your components:

| Hook | What It Does |
|------|-------------|
| `useState()` | Creates a variable that, when changed, re-renders the component. E.g., `const [agents, setAgents] = useState([])` |
| `useEffect()` | Runs code when the component loads or when something changes. E.g., "fetch agents from API when page loads" |
| `useRef()` | Stores a value that persists across renders without causing re-renders. E.g., storing the WebSocket connection object |

**Custom hooks** (like our `useWebSocket.js`) combine multiple built-in hooks into a reusable package. Instead of writing WebSocket connection logic in every component, you just call `const { lastMessage } = useWebSocket(url)`.

---

### 12. What is message parsing?

**Message parsing** means taking raw incoming data and converting it into a usable format.

When the WebSocket receives a message from the backend, it arrives as a **raw text string** like this:
```
'{"type":"state_update","agents":[{"name":"TARA","location":"Mission Control"}]}'
```

That's just text — JavaScript can't access `agents[0].name` from a string. **Parsing** converts it into a JavaScript object:
```javascript
const data = JSON.parse(event.data);
// Now data.agents[0].name === "TARA" ✅
```

In our `useWebSocket.js`, line 18–19 does exactly this:
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);  // parsing
    setLastMessage(data);                 // now it's usable
};
```

Without parsing, the data would be an unusable blob of text.
