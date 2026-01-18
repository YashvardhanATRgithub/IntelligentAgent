import './StationMap.css';

const LOCATIONS = [
    { id: 'mission-control', name: 'Mission Control', emoji: '🎛️', row: 0, col: 0 },
    { id: 'agri-lab', name: 'Agri Lab', emoji: '🌱', row: 0, col: 1 },
    { id: 'mess-hall', name: 'Mess Hall', emoji: '🍽️', row: 0, col: 2 },
    { id: 'rec-room', name: 'Rec Room', emoji: '🎮', row: 0, col: 3 },
    { id: 'crew-quarters', name: 'Crew Quarters', emoji: '🛏️', row: 1, col: 0 },
    { id: 'medical-bay', name: 'Medical Bay', emoji: '🏥', row: 1, col: 1 },
    { id: 'comms-tower', name: 'Comms Tower', emoji: '📡', row: 1, col: 2 },
    { id: 'mining-tunnel', name: 'Mining Tunnel', emoji: '⛏️', row: 1, col: 3 },
];

const StationMap = ({ agents }) => {
    const getAgentsAtLocation = (locationName) => {
        return agents.filter(agent => agent.location === locationName);
    };

    return (
        <div className="station-map">
            <h2 className="map-title">🌙 Aryabhata Station</h2>
            <div className="map-grid">
                {LOCATIONS.map((location) => {
                    const agentsHere = getAgentsAtLocation(location.name);
                    return (
                        <div key={location.id} className="map-cell">
                            <div className="location-header">
                                <span className="location-emoji">{location.emoji}</span>
                                <span className="location-name">{location.name}</span>
                            </div>
                            <div className="location-agents">
                                {agentsHere.map((agent) => (
                                    <div key={agent.id} className="agent-marker" title={agent.name}>
                                        {agent.name === 'TARA' ? '🤖' : '👨‍🚀'}
                                    </div>
                                ))}
                            </div>
                            {agentsHere.length > 0 && (
                                <div className="agent-count">{agentsHere.length} here</div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default StationMap;
