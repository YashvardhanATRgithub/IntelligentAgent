import './ActivityLog.css';

const ActivityLog = ({ activities }) => {
    return (
        <div className="activity-log">
            <h2>📋 Activity Log</h2>
            <div className="log-container">
                {activities.length === 0 ? (
                    <div className="no-activity">
                        <p>No activity yet.</p>
                        <p className="hint">Click "Start Simulation" to begin!</p>
                    </div>
                ) : (
                    activities.map((activity, index) => (
                        <div key={index} className={`log-entry ${activity.action}`}>
                            <div className="log-time">{activity.time}</div>
                            <div className="log-content">
                                <span className="log-agent">{activity.agent}</span>
                                <span className="log-action">{getActionEmoji(activity.action)}</span>
                                <span className="log-details">{activity.details}</span>
                            </div>
                            <div className="log-location">📍 {activity.location}</div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

const getActionEmoji = (action) => {
    switch (action) {
        case 'move': return '🚶';
        case 'talk': return '💬';
        case 'work': return '⚙️';
        case 'rest': return '😴';
        default: return '•';
    }
};

export default ActivityLog;
