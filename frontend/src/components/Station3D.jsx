import { useState, useMemo } from 'react';
import './Station3D.css';

// Agent images mapping
const AGENT_IMAGES = {
    'Cdr. Vikram Sharma': '/agents/vikram.png',
    'Dr. Ananya Iyer': '/agents/ananya.png',
    'TARA': '/agents/tara.png',
    'Aditya Reddy': '/agents/aditya.png',
    'Dr. Arjun Menon': '/agents/arjun.png',
    'Kabir Saxena': '/agents/kabir.png',
    'Rohan Pillai': '/agents/rohan.png',
    'Priya Nair': '/agents/priya.png',
};

// Location images mapping
const LOCATION_IMAGES = {
    'Mission Control': '/locations/mission_control.png',
    'Agri Lab': '/locations/agri_lab.png',
    'Mess Hall': '/locations/mess_hall.png',
    'Rec Room': '/locations/rec_room.png',
    'Crew Quarters': '/locations/crew_quarters.png',
    'Medical Bay': '/locations/medical_bay.png',
    'Comms Tower': '/locations/comms_tower.png',
    'Mining Tunnel': '/locations/mining_tunnel.png',
};

const LOCATIONS = [
    { name: 'Mission Control', icon: '🎛️' },
    { name: 'Agri Lab', icon: '🌱' },
    { name: 'Mess Hall', icon: '🍽️' },
    { name: 'Rec Room', icon: '🎮' },
    { name: 'Crew Quarters', icon: '🛏️' },
    { name: 'Medical Bay', icon: '🏥' },
    { name: 'Comms Tower', icon: '📡' },
    { name: 'Mining Tunnel', icon: '⛏️' },
];

const Station3D = ({ agents, activities }) => {
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [hoveredAgent, setHoveredAgent] = useState(null);

    // Get speech bubbles from recent activities
    const speechBubbles = useMemo(() => {
        const bubbles = {};
        activities
            .filter(a => a.action === 'talk' && a.details?.includes('Said to'))
            .slice(0, 5)
            .forEach((activity) => {
                const match = activity.details.match(/Said to .+?: "(.+)"/);
                if (match) {
                    bubbles[activity.agent] = match[1];
                }
            });
        return bubbles;
    }, [activities]);

    const getAgentsAtLocation = (locationName) => {
        return agents.filter(agent => agent.location === locationName);
    };

    return (
        <div className="station-3d">
            {/* Background */}
            <div className="station-background">
                <img src="/locations/lunar_base.png" alt="Aryabhata Station" className="bg-image" />
                <div className="bg-overlay"></div>
            </div>

            {/* Header */}
            <div className="station-header">
                <h1>🌙 Aryabhata Station</h1>
                <p>ISRO Lunar Base • South Pole</p>
            </div>

            {/* Location Cards Grid */}
            <div className="locations-grid">
                {LOCATIONS.map((location) => {
                    const agentsHere = getAgentsAtLocation(location.name);
                    const isSelected = selectedLocation === location.name;

                    return (
                        <div
                            key={location.name}
                            className={`location-card ${isSelected ? 'selected' : ''} ${agentsHere.length > 0 ? 'occupied' : ''}`}
                            onClick={() => setSelectedLocation(isSelected ? null : location.name)}
                        >
                            <div className="location-image">
                                <img src={LOCATION_IMAGES[location.name]} alt={location.name} />
                                <div className="location-gradient"></div>
                            </div>

                            <div className="location-info">
                                <span className="location-icon">{location.icon}</span>
                                <span className="location-name">{location.name}</span>
                                {agentsHere.length > 0 && (
                                    <span className="agent-count">{agentsHere.length} 👤</span>
                                )}
                            </div>

                            {/* Agents at this location */}
                            <div className="agents-row">
                                {agentsHere.map((agent) => (
                                    <div
                                        key={agent.name}
                                        className={`agent-avatar ${hoveredAgent === agent.name ? 'hovered' : ''}`}
                                        onMouseEnter={() => setHoveredAgent(agent.name)}
                                        onMouseLeave={() => setHoveredAgent(null)}
                                    >
                                        <img src={AGENT_IMAGES[agent.name]} alt={agent.name} />

                                        {/* Speech bubble */}
                                        {speechBubbles[agent.name] && (
                                            <div className="speech-bubble">
                                                <span>"{speechBubbles[agent.name]}"</span>
                                            </div>
                                        )}

                                        {/* Tooltip */}
                                        {hoveredAgent === agent.name && (
                                            <div className="agent-tooltip">
                                                <strong>{agent.name}</strong>
                                                <span>{agent.role}</span>
                                                <span className="activity">{agent.activity || 'idle'}</span>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Selected Location Detail */}
            {selectedLocation && (
                <div className="location-detail">
                    <button className="close-detail" onClick={() => setSelectedLocation(null)}>✕</button>
                    <img src={LOCATION_IMAGES[selectedLocation]} alt={selectedLocation} />
                    <div className="detail-content">
                        <h2>{selectedLocation}</h2>
                        <div className="detail-agents">
                            {getAgentsAtLocation(selectedLocation).map((agent) => (
                                <div key={agent.name} className="detail-agent">
                                    <img src={AGENT_IMAGES[agent.name]} alt={agent.name} />
                                    <div className="detail-agent-info">
                                        <strong>{agent.name}</strong>
                                        <span>{agent.role}</span>
                                        <span className="status">{agent.activity}</span>
                                    </div>
                                </div>
                            ))}
                            {getAgentsAtLocation(selectedLocation).length === 0 && (
                                <p className="empty-room">No one is here currently</p>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Station3D;
