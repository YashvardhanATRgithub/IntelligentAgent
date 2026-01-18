import { useState, useEffect } from 'react';
import './AgentPanel.css';

/**
 * Agent Details Panel - Shows when an agent is clicked
 * Displays: state, memories, relationships, daily plan
 */
export default function AgentPanel({ agentName, onClose }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('state');

    useEffect(() => {
        if (agentName) {
            fetchAgentData();
        }
    }, [agentName]);

    const fetchAgentData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/api/agents/${encodeURIComponent(agentName)}/full`);
            const json = await res.json();
            setData(json);
        } catch (err) {
            console.error('Error fetching agent data:', err);
        }
        setLoading(false);
    };

    if (!agentName) return null;

    return (
        <div className="agent-panel">
            <div className="panel-header">
                <h2>{agentName}</h2>
                <button className="close-btn" onClick={onClose}>✕</button>
            </div>

            {loading ? (
                <div className="loading">Loading...</div>
            ) : (
                <>
                    <div className="panel-tabs">
                        <button
                            className={activeTab === 'state' ? 'active' : ''}
                            onClick={() => setActiveTab('state')}
                        >
                            Status
                        </button>
                        <button
                            className={activeTab === 'memories' ? 'active' : ''}
                            onClick={() => setActiveTab('memories')}
                        >
                            Memories
                        </button>
                        <button
                            className={activeTab === 'relationships' ? 'active' : ''}
                            onClick={() => setActiveTab('relationships')}
                        >
                            Relations
                        </button>
                        <button
                            className={activeTab === 'plan' ? 'active' : ''}
                            onClick={() => setActiveTab('plan')}
                        >
                            Schedule
                        </button>
                    </div>

                    <div className="panel-content">
                        {activeTab === 'state' && data?.state && (
                            <div className="state-tab">
                                <div className="stat-row">
                                    <span className="label">Role</span>
                                    <span className="value">{data.state.role}</span>
                                </div>
                                <div className="stat-row">
                                    <span className="label">Location</span>
                                    <span className="value">{data.state.location}</span>
                                </div>
                                <div className="stat-row">
                                    <span className="label">Activity</span>
                                    <span className="value">{data.state.activity || 'Idle'}</span>
                                </div>
                                <div className="stat-row">
                                    <span className="label">Mood</span>
                                    <span className="value">{data.state.mood}</span>
                                </div>
                                <div className="stat-row">
                                    <span className="label">Energy</span>
                                    <div className="energy-bar">
                                        <div
                                            className="energy-fill"
                                            style={{ width: `${data.state.energy}%` }}
                                        />
                                        <span>{data.state.energy}%</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'memories' && (
                            <div className="memories-tab">
                                {data?.memories?.length > 0 ? (
                                    data.memories.map((mem, idx) => (
                                        <div key={idx} className={`memory-item ${mem.memory_type}`}>
                                            <div className="memory-meta">
                                                <span className="memory-type">{mem.memory_type}</span>
                                                <span className="memory-importance">⭐ {mem.importance.toFixed(1)}</span>
                                            </div>
                                            <p className="memory-content">{mem.content}</p>
                                            {mem.source && (
                                                <span className="memory-source">Source: {mem.source}</span>
                                            )}
                                        </div>
                                    ))
                                ) : (
                                    <p className="empty">No memories yet</p>
                                )}
                            </div>
                        )}

                        {activeTab === 'relationships' && (
                            <div className="relationships-tab">
                                {data?.relationships && Object.keys(data.relationships).length > 0 ? (
                                    Object.entries(data.relationships).map(([name, rel]) => (
                                        <div key={name} className="relationship-item">
                                            <div className="rel-name">{name}</div>
                                            <div className="rel-bar">
                                                <div
                                                    className={`rel-fill ${rel.sentiment}`}
                                                    style={{ width: `${rel.strength}%` }}
                                                />
                                            </div>
                                            <div className="rel-stats">
                                                <span>{rel.strength}%</span>
                                                <span className={`sentiment ${rel.sentiment}`}>
                                                    {rel.sentiment}
                                                </span>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="empty">No relationships tracked yet</p>
                                )}
                            </div>
                        )}

                        {activeTab === 'plan' && (
                            <div className="plan-tab">
                                {data?.plan?.activities?.length > 0 ? (
                                    data.plan.activities.map((activity, idx) => (
                                        <div key={idx} className={`plan-item ${activity.completed ? 'completed' : ''}`}>
                                            <span className="plan-time">{activity.time}</span>
                                            <span className="plan-activity">{activity.description}</span>
                                            <span className="plan-location">📍 {activity.location}</span>
                                        </div>
                                    ))
                                ) : (
                                    <p className="empty">No plan generated</p>
                                )}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
