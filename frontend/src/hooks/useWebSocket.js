import { useState, useEffect, useRef } from 'react';

export const useWebSocket = (url) => {
    const [isConnected, setIsConnected] = useState(false);
    const [lastMessage, setLastMessage] = useState(null);
    const wsRef = useRef(null);

    useEffect(() => {
        const connect = () => {
            wsRef.current = new WebSocket(url);

            wsRef.current.onopen = () => {
                setIsConnected(true);
                console.log('WebSocket connected');
            };

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setLastMessage(data);
            };

            wsRef.current.onclose = () => {
                setIsConnected(false);
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connect, 3000);
            };

            wsRef.current.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        };

        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [url]);

    const sendMessage = (message) => {
        if (wsRef.current && isConnected) {
            wsRef.current.send(JSON.stringify(message));
        }
    };

    return { isConnected, lastMessage, sendMessage };
};
