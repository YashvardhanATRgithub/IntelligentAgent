import { useState, useEffect } from 'react';
import './IsometricStation.css';
import './CommsFeed.css';

// Agent colors for avatars
const AGENT_COLORS = {
    'Cdr. Vikram Sharma': '#e74c3c',
    'Dr. Ananya Iyer': '#27ae60',
    'TARA': '#9b59b6',
    'Aditya Reddy': '#f39c12',
    'Dr. Arjun Menon': '#3498db',
    'Kabir Saxena': '#e67e22',
    'Rohan Pillai': '#1abc9c',
    'Priya Nair': '#e91e63',
};

// Location positions in isometric grid
const LOCATIONS = {
    'Mission Control': { x: 0, y: 0, icon: '🎛️', color: '#2c3e50' },
    'Agri Lab': { x: 1, y: 0, icon: '🌱', color: '#27ae60' },
    'Mess Hall': { x: 2, y: 0, icon: '🍽️', color: '#e67e22' },
    'Rec Room': { x: 3, y: 0, icon: '🎮', color: '#9b59b6' },
    'Crew Quarters': { x: 0, y: 1, icon: '🛏️', color: '#34495e' },
    'Medical Bay': { x: 1, y: 1, icon: '🏥', color: '#e74c3c' },
    'Comms Tower': { x: 2, y: 1, icon: '📡', color: '#3498db' },
    'Mining Tunnel': { x: 3, y: 1, icon: '⛏️', color: '#95a5a6' },
};

const IsometricStation = ({ agents, activities }) => {
    // Comms feed logic now handled directly in render

    return (
        <div className="isometric-container">
            <h2 className="station-title">🌙 Aryabhata Station</h2>
            <div className="isometric-grid">
                {Object.entries(LOCATIONS).map(([name, loc]) => {
                    const agentsHere = getAgentsAtLocation(name);
                    return (
                        <div
                            key={name}
                            className="isometric-room"
                            style={{
                                '--room-color': loc.color,
                                '--grid-x': loc.x,
                                '--grid-y': loc.y,
                            }}
                        >
                            <div className="room-floor">
                                <div className="room-walls">
                                    <div className="wall-left"></div>
                                    <div className="wall-right"></div>
                                </div>
                                <div className="room-content">
                                    <div className="room-icon">{loc.icon}</div>
                                    <div className="room-name">{name}</div>

                                    <div className="agents-in-room">
                                        {agentsHere.map((agent, idx) => (
                                            <div
                                                key={agent.name}
                                                className={`agent-sprite ${agent.name === 'TARA' ? 'robot' : ''}`}
                                                style={{
                                                    '--agent-color': AGENT_COLORS[agent.name],
                                                    '--agent-index': idx,
                                                }}
                                                title={`${agent.name} - ${agent.activity || 'idle'}`}
                                            >
                                                <div className="agent-body">
                                                    <div className="agent-head">
                                                        {agent.name === 'TARA' ? '🤖' : '👤'}
                                                    </div>
                                                    <div className="agent-torso"></div>
                                                </div>
                                                <div className="agent-name-tag">
                                                    {agent.name.split(' ')[0]}
                                                </div>

                                                {/* Speech bubble removed */}

                                                {/* Activity indicator */}
                                                {agent.activity && agent.activity !== 'idle' && (
                                                    <div className="activity-indicator">
                                                        {getActivityIcon(agent.activity)}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Comms Feed Overlay */}
            <div className="comms-feed">
                <h3>📡 Live Comms</h3>
                <div className="comms-list">
                    {activities
                        .filter(a => a.action === 'talk' && a.details?.includes('Said to'))
                        .slice(0, 10)
                        .map((activity, idx) => (
                            <div key={idx} className="comms-item">
                                <div className="comms-header">
                                    <span className="comms-agent" style={{ color: AGENT_COLORS[activity.agent] }}>
                                        {activity.agent.split(' ')[0]}
                                    </span>
                                    <span className="comms-arrow">▶</span>
                                    <span className="comms-target">
                                        {activity.details.match(/Said to (.+):/)?.[1]?.split(' ')[0] || 'All'}
                                    </span>
                                </div>
                                <div className="comms-message">
                                    "{activity.details.match(/"(.+)"/)?.[1]}"
                                </div>
                            </div>
                        ))}
                    {activities.filter(a => a.action === 'talk').length === 0 && (
                        <div className="comms-empty">No active channels</div>
                    )}
                </div>
            </div>

            {/* Legend */}
            <div className="station-legend">
                {agents.map(agent => (
                    <div key={agent.name} className="legend-item">
                        <div
                            className="legend-color"
                            style={{ backgroundColor: AGENT_COLORS[agent.name] }}
                        ></div>
                        <span>{agent.name.split(' ').pop()}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const getActivityIcon = (activity) => {
    if (activity.includes('moving')) return '🚶';
    if (activity.includes('talking')) return '💬';
    if (activity.includes('resting')) return '😴';
    if (activity.includes('working') || activity.includes('checking') || activity.includes('analyzing')) return '⚙️';
    return '•';
};

export default IsometricStation;
