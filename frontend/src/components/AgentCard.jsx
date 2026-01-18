import './AgentCard.css';

const ROLE_COLORS = {
    'Commander': '#e74c3c',
    'Botanist': '#27ae60',
    'AI Assistant': '#9b59b6',
    'Engineer': '#f39c12',
    'Surgeon': '#3498db',
    'Geologist': '#e67e22',
    'Comms Officer': '#1abc9c',
    'Welfare Officer': '#e91e63',
};

const AgentCard = ({ agent, isSelected, onClick }) => {
    const roleColor = ROLE_COLORS[agent.role] || '#95a5a6';

    return (
        <div
            className={`agent-card ${isSelected ? 'selected' : ''}`}
            onClick={() => onClick(agent)}
            style={{ '--role-color': roleColor }}
        >
            <div className="agent-avatar">
                {agent.name === 'TARA' ? '🤖' : '👨‍🚀'}
            </div>
            <div className="agent-info">
                <h3 className="agent-name">{agent.name}</h3>
                <span className="agent-role" style={{ backgroundColor: roleColor }}>
                    {agent.role}
                </span>
                <p className="agent-location">📍 {agent.location}</p>
            </div>
            <div className="agent-status">
                <span className="status-dot online"></span>
                Active
            </div>
        </div>
    );
};

export default AgentCard;
