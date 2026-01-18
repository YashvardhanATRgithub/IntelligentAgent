import { useState, useEffect, useRef, useCallback } from 'react';
import LunarBase from './components/LunarBase';
import AgentPanel from './components/AgentPanel';
import { api } from './services/api';
import './App.css';

function App() {
  const [agents, setAgents] = useState([]);
  const [isSimulationRunning, setIsSimulationRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulationTime, setSimulationTime] = useState('');
  const [activities, setActivities] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isCleaningUp = useRef(false);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      if (isCleaningUp.current) return;

      // Prevent multiple connections
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        return;
      }

      wsRef.current = new WebSocket('ws://localhost:8000/ws');

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      wsRef.current.onclose = () => {
        if (isCleaningUp.current) return;
        console.log('WebSocket disconnected');
        setWsConnected(false);
        // Only reconnect if not cleaning up
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    };

    connectWebSocket();

    return () => {
      isCleaningUp.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleWebSocketMessage = useCallback((data) => {
    switch (data.type) {
      case 'connected':
      case 'state_update':
        if (data.state) {
          updateFromState(data.state);
        }
        break;

      case 'simulation_started':
        setIsSimulationRunning(true);
        if (data.state) {
          updateFromState(data.state);
        }
        break;

      case 'simulation_stopped':
        setIsSimulationRunning(false);
        break;

      case 'agent_action':
        if (data.activity) {
          setActivities(prev => [data.activity, ...prev].slice(0, 50));
        }
        if (data.agent_state) {
          setAgents(prev => prev.map(a =>
            a.name === data.agent_state.name
              ? { ...a, ...data.agent_state }
              : a
          ));
        }
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }, []);

  const updateFromState = (state) => {
    if (state.agents) {
      setAgents(state.agents);
    }
    if (state.time) {
      setSimulationTime(state.time);
    }
    if (state.is_running !== undefined) {
      setIsSimulationRunning(state.is_running);
    }
    if (state.recent_activities) {
      setActivities(state.recent_activities.reverse());
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const data = await api.getAgents();
      setAgents(data.agents);
      setError(null);
    } catch (err) {
      setError('Failed to connect to server');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSimulation = async () => {
    try {
      await api.startSimulation();
      setIsSimulationRunning(true);
    } catch (err) {
      console.error('Failed to start simulation:', err);
    }
  };

  const handlePauseSimulation = async () => {
    try {
      await api.pauseSimulation();
      setIsSimulationRunning(false);
    } catch (err) {
      console.error('Failed to pause simulation:', err);
    }
  };

  return (
    <div className="app">
      {/* Floating Header */}
      <header className="floating-header">
        <div className="header-brand">
          <div className="brand-logo">🚀</div>
          <div>
            <h1>ISRO Chandrayaan-5</h1>
            <span className="tagline">Aryabhatta Station • Moon South Pole</span>
          </div>
        </div>

        <div className="header-center">
          {simulationTime && <span className="sim-time">🕐 {simulationTime}</span>}
          <div className={`connection-status ${wsConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {wsConnected ? 'Live' : 'Offline'}
          </div>
        </div>

        <div className="header-controls">
          <button
            className={`sim-button ${isSimulationRunning ? 'running' : ''}`}
            onClick={isSimulationRunning ? handlePauseSimulation : handleStartSimulation}
            disabled={!!error}
          >
            {isSimulationRunning ? (
              <>
                <span className="btn-icon">⏸️</span>
                <span>Pause</span>
              </>
            ) : (
              <>
                <span className="btn-icon">▶️</span>
                <span>Start</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Full Screen 3D View */}
      <main className="main-fullscreen">
        {loading ? (
          <div className="loading-screen">
            <div className="loader"></div>
            <p>Connecting to Aryabhatta Station...</p>
          </div>
        ) : error ? (
          <div className="error-screen">
            <span className="error-icon">⚠️</span>
            <h2>Connection Error</h2>
            <p>{error}</p>
            <button onClick={loadAgents}>Retry Connection</button>
          </div>
        ) : (
          <>
            <LunarBase
              agents={agents}
              activities={activities}
              onAgentClick={(agentName) => setSelectedAgent(agentName)}
              isPaused={!isSimulationRunning}
            />
            {selectedAgent && (
              <AgentPanel
                agentName={selectedAgent}
                onClose={() => setSelectedAgent(null)}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
