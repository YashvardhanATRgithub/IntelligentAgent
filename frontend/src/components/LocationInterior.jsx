import React from 'react';
import './LocationInterior.css';

const LocationInterior = ({ locationNode, agents, onClose, onAgentClick }) => {
    if (!locationNode) return null;

    // Flatten agents for easy lookup
    // locationNode structure: { name, type, children: { name: node }, agents: [ids] }

    // Helper to get agents for a specific sub-area node
    const getAgentsInArea = (node) => {
        // node.agents is list of IDs. We need full agent objects.
        if (!node || !node.agents) return [];
        return agents.filter(a => node.agents.includes(a.id) || node.agents.includes(a.name));
        // Backend might send "Vikram" (name) or "Vikram_1" (id). Handling both.
    };

    const buildingAgents = getAgentsInArea(locationNode);
    const subAreas = Object.values(locationNode.children || {});

    // Calculate total agents in building (including sub-areas)
    const getAllAgentsCount = (node) => {
        let count = (node.agents || []).length;
        if (node.children) {
            Object.values(node.children).forEach(child => {
                count += getAllAgentsCount(child);
            });
        }
        return count;
    };

    return (
        <div className="interior-modal-overlay">
            <div className="interior-modal">
                <div className="interior-header">
                    <div className="header-title">
                        <h2>{locationNode.name.toUpperCase()}</h2>
                        <span className="location-type">{locationNode.type}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <div className="interior-content">
                    {/* Main Building Lobby / General Area */}
                    <div className="sub-area lobby">
                        <h3>Main Entrance / Lobby</h3>
                        <div className="area-agents">
                            {buildingAgents.length > 0 ? (
                                buildingAgents.map(agent => (
                                    <AgentCard key={agent.id || agent.name} agent={agent} onClick={onAgentClick} />
                                ))
                            ) : (
                                <span className="empty-msg">Empty</span>
                            )}
                        </div>
                    </div>

                    {/* Grid of Sub-Areas */}
                    <div className="sub-areas-grid">
                        {subAreas.map(area => {
                            const areaAgents = getAgentsInArea(area);
                            return (
                                <div key={area.name} className="sub-area-card">
                                    <div className="area-header">
                                        <h4>{area.name}</h4>
                                        <span className="agent-count-badge">{areaAgents.length}</span>
                                    </div>
                                    <div className="area-agents">
                                        {areaAgents.length > 0 ? (
                                            areaAgents.map(agent => (
                                                <AgentCard key={agent.id || agent.name} agent={agent} onClick={onAgentClick} />
                                            ))
                                        ) : (
                                            <span className="empty-msg">No Crew</span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

const AgentCard = ({ agent, onClick }) => {
    // Helper for role color (duplicated from LunarBase, ideally shared)
    const getRoleColor = (role) => {
        const colors = {
            'Commander': '#FF6B35', 'Botanist': '#4CAF50', 'AI Assistant': '#00BCD4',
            'Engineer': '#FF9800', 'Surgeon': '#E91E63', 'Geologist': '#795548',
            'Communications Officer': '#2196F3', 'Crew Welfare Officer': '#9C27B0'
        };
        return colors[role] || '#FFFFFF'; // Default
    };

    return (
        <div className="interior-agent-card" onClick={() => onClick && onClick(agent.name)}>
            <div className="agent-avatar" style={{ background: getRoleColor(agent.role) }}>
                {agent.name.charAt(0)}
            </div>
            <div className="agent-briefer">
                <span className="agent-name">{agent.name.split(" ").slice(-1)[0]}</span>
                {/* <span className="agent-role">{agent.role}</span> */}
            </div>
        </div>
    );
};

export default LocationInterior;
