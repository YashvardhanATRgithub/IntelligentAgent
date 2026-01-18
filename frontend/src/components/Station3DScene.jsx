import { useRef, useState, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree, useLoader } from '@react-three/fiber';
import { OrbitControls, Text, Billboard, Html, useTexture, Stars, Float } from '@react-three/drei';
import * as THREE from 'three';
import './Station3DScene.css';

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

// Location configuration with 3D positions in a circular layout
const LOCATIONS = [
    { name: 'Mission Control', icon: '🎛️', position: [0, 0, 0], color: '#FF6B35' },
    { name: 'Agri Lab', icon: '🌱', position: [4, 0, 2], color: '#4CAF50' },
    { name: 'Mess Hall', icon: '🍽️', position: [4, 0, -2], color: '#FF9800' },
    { name: 'Rec Room', icon: '🎮', position: [-4, 0, 2], color: '#9C27B0' },
    { name: 'Crew Quarters', icon: '🛏️', position: [-4, 0, -2], color: '#2196F3' },
    { name: 'Medical Bay', icon: '🏥', position: [0, 0, 4], color: '#E91E63' },
    { name: 'Comms Tower', icon: '📡', position: [0, 0, -4], color: '#00BCD4' },
    { name: 'Mining Tunnel', icon: '⛏️', position: [-6, -0.5, 0], color: '#795548' },
];

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

// 3D Room Component
function Room({ location, agents, isSelected, onClick, speechBubbles }) {
    const meshRef = useRef();
    const [hovered, setHovered] = useState(false);

    // Load texture for the room
    const texture = useTexture(LOCATION_IMAGES[location.name]);

    useFrame((state) => {
        if (meshRef.current) {
            // Subtle floating animation
            meshRef.current.position.y = location.position[1] + Math.sin(state.clock.elapsedTime * 0.5 + location.position[0]) * 0.05;

            // Glow effect when hovered or selected
            if (isSelected || hovered) {
                meshRef.current.scale.lerp(new THREE.Vector3(1.1, 1.1, 1.1), 0.1);
            } else {
                meshRef.current.scale.lerp(new THREE.Vector3(1, 1, 1), 0.1);
            }
        }
    });

    // Calculate agent positions in a semi-circle around the room
    const agentPositions = useMemo(() => {
        return agents.map((_, index) => {
            const angle = (index / Math.max(agents.length, 1)) * Math.PI - Math.PI / 2;
            const radius = 1.2;
            return [
                Math.cos(angle) * radius,
                0.3,
                Math.sin(angle) * radius
            ];
        });
    }, [agents]);

    return (
        <group position={location.position}>
            {/* Room Base */}
            <mesh
                ref={meshRef}
                onClick={onClick}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
            >
                <boxGeometry args={[2, 1.5, 2]} />
                <meshStandardMaterial
                    map={texture}
                    transparent
                    opacity={0.95}
                    emissive={new THREE.Color(location.color)}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0.05}
                />
            </mesh>

            {/* Room Label */}
            <Billboard position={[0, 1.2, 0]}>
                <Text
                    fontSize={0.25}
                    color="white"
                    anchorX="center"
                    anchorY="middle"
                    outlineWidth={0.02}
                    outlineColor="#000"
                >
                    {location.icon} {location.name}
                </Text>
            </Billboard>

            {/* Agent Count Badge */}
            {agents.length > 0 && (
                <Billboard position={[0.9, 0.9, 0]}>
                    <mesh>
                        <circleGeometry args={[0.2, 32]} />
                        <meshBasicMaterial color="#FF6B35" />
                    </mesh>
                    <Text
                        fontSize={0.15}
                        color="white"
                        position={[0, 0, 0.01]}
                        anchorX="center"
                        anchorY="middle"
                    >
                        {agents.length}
                    </Text>
                </Billboard>
            )}

            {/* Agents at this location */}
            {agents.map((agent, index) => (
                <Agent
                    key={agent.name}
                    agent={agent}
                    position={agentPositions[index]}
                    speechBubble={speechBubbles[agent.name]}
                />
            ))}

            {/* Connection lines to center */}
            {location.name !== 'Mission Control' && (
                <ConnectionLine
                    start={[0, -0.5, 0]}
                    end={[-location.position[0], -0.5 - location.position[1], -location.position[2]]}
                    color={location.color}
                />
            )}
        </group>
    );
}

// Agent Component
function Agent({ agent, position, speechBubble }) {
    const meshRef = useRef();
    const [hovered, setHovered] = useState(false);

    // Load agent texture
    const texture = useTexture(AGENT_IMAGES[agent.name] || '/agents/vikram.png');

    useFrame((state) => {
        if (meshRef.current) {
            // Bobbing animation
            meshRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.02;
            // Always face camera
            meshRef.current.rotation.y = state.camera.rotation.y;
        }
    });

    return (
        <group position={position}>
            <mesh
                ref={meshRef}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
            >
                <planeGeometry args={[0.4, 0.4]} />
                <meshBasicMaterial map={texture} transparent alphaTest={0.5} />
            </mesh>

            {/* Agent Name Label (Always Visible) */}
            <Html
                position={[0, 0.45, 0]}
                center
                className="agent-label-3d"
                distanceFactor={10}
            >
                <div className="name-tag">
                    {agent.name.split(' ')[0]}
                </div>
            </Html>

            {/* Speech bubble - Only if NOT moving */}
            {speechBubble && !agent.activity?.toLowerCase().includes('moving') && (
                <Html
                    position={[0, 0.9, 0]}
                    center
                    className="speech-bubble-3d"
                    distanceFactor={10}
                >
                    <div className="bubble-content">
                        "{speechBubble}"
                    </div>
                </Html>
            )}

            {/* Activity indicator ring */}
            <mesh position={[0, -0.1, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <ringGeometry args={[0.2, 0.25, 32]} />
                <meshBasicMaterial
                    color={agent.activity === 'working' ? '#4CAF50' : agent.activity === 'resting' ? '#2196F3' : '#FF9800'}
                    transparent
                    opacity={0.7}
                />
            </mesh>
        </group>
    );
}

// Connection Line Component
function ConnectionLine({ start, end, color }) {
    const points = useMemo(() => {
        return [
            new THREE.Vector3(...start),
            new THREE.Vector3(...end)
        ];
    }, [start, end]);

    const lineGeometry = useMemo(() => {
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        return geometry;
    }, [points]);

    return (
        <line geometry={lineGeometry}>
            <lineBasicMaterial color={color} transparent opacity={0.3} />
        </line>
    );
}

// Lunar Surface Component
function LunarSurface() {
    return (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1, 0]} receiveShadow>
            <planeGeometry args={[30, 30, 32, 32]} />
            <meshStandardMaterial
                color="#1a1a2e"
                roughness={0.9}
                metalness={0.1}
            />
        </mesh>
    );
}

// Scene Setup Component
function Scene({ agents, activities, selectedLocation, setSelectedLocation }) {
    // Calculate speech bubbles from activities
    const speechBubbles = useMemo(() => {
        const bubbles = {};
        activities
            .filter(a => a.action === 'talk' && a.details?.includes('Said to'))
            .slice(0, 5)
            .forEach((activity) => {
                const match = activity.details.match(/Said to .+?: "(.+)"/);
                if (match) {
                    bubbles[activity.agent] = match[1].slice(0, 50) + (match[1].length > 50 ? '...' : '');
                }
            });
        return bubbles;
    }, [activities]);

    const getAgentsAtLocation = (locationName) => {
        return agents.filter(agent => agent.location === locationName);
    };

    return (
        <>
            {/* Environment */}
            <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />
            <ambientLight intensity={0.4} />
            <directionalLight position={[10, 10, 5]} intensity={0.8} castShadow />
            <pointLight position={[0, 5, 0]} intensity={0.5} color="#FF6B35" />

            {/* Lunar Surface */}
            <LunarSurface />

            {/* Rooms */}
            {LOCATIONS.map((location) => (
                <Room
                    key={location.name}
                    location={location}
                    agents={getAgentsAtLocation(location.name)}
                    isSelected={selectedLocation === location.name}
                    onClick={() => setSelectedLocation(selectedLocation === location.name ? null : location.name)}
                    speechBubbles={speechBubbles}
                />
            ))}

            {/* Camera Controls */}
            <OrbitControls
                makeDefault
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minDistance={5}
                maxDistance={20}
                maxPolarAngle={Math.PI / 2.2}
                target={[0, 0, 0]}
            />
        </>
    );
}

// Location Detail Modal
function LocationDetailModal({ location, agents, onClose }) {
    const locationData = LOCATIONS.find(l => l.name === location);

    return (
        <div className="location-modal-overlay" onClick={onClose}>
            <div className="location-modal" onClick={(e) => e.stopPropagation()}>
                <button className="close-btn" onClick={onClose}>✕</button>
                <div
                    className="modal-header"
                    style={{
                        backgroundImage: `url(${LOCATION_IMAGES[location]})`,
                        borderColor: locationData?.color
                    }}
                >
                    <h2>{locationData?.icon} {location}</h2>
                </div>
                <div className="modal-content">
                    <h3>Crew Members Present ({agents.length})</h3>
                    {agents.length > 0 ? (
                        <div className="agents-list">
                            {agents.map(agent => (
                                <div key={agent.name} className="agent-item">
                                    <img src={AGENT_IMAGES[agent.name]} alt={agent.name} />
                                    <div className="agent-info">
                                        <strong>{agent.name}</strong>
                                        <span>{agent.role}</span>
                                        <span className="status">{agent.activity || 'Idle'}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="empty-message">No crew members in this location</p>
                    )}
                </div>
            </div>
        </div>
    );
}

// Main Component
export default function Station3DScene({ agents, activities }) {
    const [selectedLocation, setSelectedLocation] = useState(null);

    const getAgentsAtLocation = (locationName) => {
        return agents.filter(agent => agent.location === locationName);
    };

    return (
        <div className="station-3d-scene">
            {/* 3D Canvas */}
            <Canvas
                camera={{ position: [8, 6, 8], fov: 50 }}
                shadows
                style={{ background: 'linear-gradient(to bottom, #0a0a1a 0%, #1a1a2e 100%)' }}
            >
                <Scene
                    agents={agents}
                    activities={activities}
                    selectedLocation={selectedLocation}
                    setSelectedLocation={setSelectedLocation}
                />
            </Canvas>

            {/* Overlay UI */}
            <div className="scene-overlay">
                <div className="scene-header">
                    <h1>🌙 Aryabhata Station</h1>
                    <p>ISRO Lunar Base • South Pole</p>
                </div>

                <div className="legend">
                    {LOCATIONS.map(loc => (
                        <button
                            key={loc.name}
                            className={`legend-item ${selectedLocation === loc.name ? 'active' : ''}`}
                            onClick={() => setSelectedLocation(selectedLocation === loc.name ? null : loc.name)}
                            style={{ '--accent-color': loc.color }}
                        >
                            <span className="legend-icon">{loc.icon}</span>
                            <span className="legend-name">{loc.name}</span>
                            <span className="legend-count">{getAgentsAtLocation(loc.name).length}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Location Detail Modal */}
            {selectedLocation && (
                <LocationDetailModal
                    location={selectedLocation}
                    agents={getAgentsAtLocation(selectedLocation)}
                    onClose={() => setSelectedLocation(null)}
                />
            )}
        </div>
    );
}
