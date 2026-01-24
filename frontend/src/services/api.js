const API_BASE = 'http://localhost:8000';

export const api = {
    // Get all agents
    getAgents: async () => {
        const response = await fetch(`${API_BASE}/api/agents`);
        return response.json();
    },

    // Get simulation state (for time updates)
    getState: async () => {
        const response = await fetch(`${API_BASE}/api/state`);
        return response.json();
    },

    // Start simulation
    startSimulation: async () => {
        const response = await fetch(`${API_BASE}/api/simulation/start`, {
            method: 'POST',
        });
        return response.json();
    },

    // Pause simulation
    pauseSimulation: async () => {
        const response = await fetch(`${API_BASE}/api/simulation/pause`, {
            method: 'POST',
        });
        return response.json();
    },
};

// WebSocket connection
export const createWebSocket = (onMessage) => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        onMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };

    return ws;
};
