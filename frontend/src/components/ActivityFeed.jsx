import './ActivityFeed.css';

const ActivityFeed = ({ activities }) => {
    return (
        <div className="activity-feed">
            <div className="feed-header">
                <h3>📡 Live Feed</h3>
                <span className="live-indicator">● LIVE</span>
            </div>

            <div className="feed-scroll">
                {activities.length === 0 ? (
                    <div className="feed-empty">
                        <div className="empty-icon">🛸</div>
                        <p>Awaiting transmission...</p>
                        <span>Start simulation to begin</span>
                    </div>
                ) : (
                    activities.map((activity, index) => (
                        <div
                            key={index}
                            className={`feed-item ${activity.action}`}
                            style={{ animationDelay: `${index * 0.05}s` }}
                        >
                            <div className="feed-icon">{getIcon(activity.action)}</div>
                            <div className="feed-content">
                                <div className="feed-main">
                                    <strong>{activity.agent}</strong>
                                    <span className="feed-text">{formatActivity(activity)}</span>
                                </div>
                                <div className="feed-meta">
                                    <span className="feed-location">📍 {activity.location}</span>
                                    <span className="feed-time">{activity.time}</span>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

const getIcon = (action) => {
    const icons = {
        move: '🚶',
        talk: '💬',
        work: '⚙️',
        rest: '😴',
        idle: '🧍',
    };
    return icons[action] || '•';
};

const formatActivity = (activity) => {
    if (activity.action === 'talk' && activity.details?.includes('Said to')) {
        const match = activity.details.match(/Said to (.+?): "(.+)"/);
        if (match) {
            return (
                <>
                    said to <strong>{match[1]}</strong>: "{match[2]}"
                </>
            );
        }
    }
    if (activity.action === 'move' && activity.details?.includes('Moved from')) {
        const match = activity.details.match(/Moved from (.+) to (.+)/);
        if (match) {
            return (
                <>
                    moved to <strong>{match[2]}</strong>
                </>
            );
        }
    }
    return activity.details || activity.action;
};

export default ActivityFeed;
