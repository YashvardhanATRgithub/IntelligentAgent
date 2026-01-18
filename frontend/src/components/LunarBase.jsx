import { useRef, useState, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Billboard, Html, Stars } from '@react-three/drei';
import * as THREE from 'three';
import './LunarBase.css';

// Hub-spoke layout: Mission Control at center, 7 locations at equal angles
// BIGGER SCALE for better visibility
const SPOKE_DISTANCE = 40; // Increased from 25
const NUM_SPOKES = 7;
const ANGLE_STEP = (Math.PI * 2) / NUM_SPOKES;

// Calculate positions in a circle around center
const LOCATIONS = [
    { name: 'Mission Control', position: [0, 0, 0], type: 'dome', color: '#FF6B35', angle: null },
    { name: 'Mess Hall', position: [Math.cos(ANGLE_STEP * 0) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 0) * SPOKE_DISTANCE], type: 'cylinder', color: '#F5F5F5', angle: ANGLE_STEP * 0 },
    { name: 'Agri Lab', position: [Math.cos(ANGLE_STEP * 1) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 1) * SPOKE_DISTANCE], type: 'cylinder', color: '#4CAF50', angle: ANGLE_STEP * 1 },
    { name: 'Crew Quarters', position: [Math.cos(ANGLE_STEP * 2) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 2) * SPOKE_DISTANCE], type: 'cylinder', color: '#2196F3', angle: ANGLE_STEP * 2 },
    { name: 'Medical Bay', position: [Math.cos(ANGLE_STEP * 3) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 3) * SPOKE_DISTANCE], type: 'cylinder', color: '#E91E63', angle: ANGLE_STEP * 3 },
    { name: 'Comms Tower', position: [Math.cos(ANGLE_STEP * 4) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 4) * SPOKE_DISTANCE], type: 'dish', color: '#00BCD4', angle: ANGLE_STEP * 4 },
    { name: 'Mining Tunnel', position: [Math.cos(ANGLE_STEP * 5) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 5) * SPOKE_DISTANCE], type: 'tunnel', color: '#795548', angle: ANGLE_STEP * 5 },
    { name: 'Rec Room', position: [Math.cos(ANGLE_STEP * 6) * SPOKE_DISTANCE, 0, Math.sin(ANGLE_STEP * 6) * SPOKE_DISTANCE], type: 'cylinder', color: '#9C27B0', angle: ANGLE_STEP * 6 },
];

// Get path between locations (through Mission Control hub)
function getPathBetweenLocations(fromLoc, toLoc) {
    const from = LOCATIONS.find(l => l.name === fromLoc);
    const to = LOCATIONS.find(l => l.name === toLoc);
    if (!from || !to) return [];

    if (fromLoc === 'Mission Control' || toLoc === 'Mission Control') {
        return [from.position, to.position];
    }
    return [from.position, LOCATIONS[0].position, to.position];
}

// Stanford-style frame-counter based movement
// Movement is synchronized: move fixed distance per frame, snap at end
const MOVE_SPEED = 0.8; // Units per frame (tuned for smooth movement)
const FRAMES_PER_MOVE = 60; // Frames to complete one location move

function Astronaut({ agent, currentLocation, previousLocation, speechBubble, isTalking, allAgents, isPaused }) {
    const groupRef = useRef();
    const leftArmRef = useRef();
    const rightArmRef = useRef();
    const leftLegRef = useRef();
    const rightLegRef = useRef();
    const headRef = useRef();

    const walkPhase = useRef(0);
    const talkPhase = useRef(0);

    // Stanford-style frame counter
    const executeCount = useRef(0);
    const moveTarget = useRef(null);
    const moveStart = useRef(null);
    const queuedMove = useRef(null); // Queue next move if one is in progress

    const AGENT_SCALE = 1.8;

    const getBasePosition = (locationName, agentName) => {
        const location = LOCATIONS.find(l => l.name === locationName);
        if (!location) return new THREE.Vector3(0, 0, 0);

        const agentsAtLoc = allAgents.filter(a => a.location === locationName);
        const idx = agentsAtLoc.findIndex(a => a.name === agentName);
        const angle = (idx / Math.max(agentsAtLoc.length, 1)) * Math.PI * 2;
        const radius = 6;

        return new THREE.Vector3(
            location.position[0] + Math.cos(angle) * radius,
            0,
            location.position[2] + Math.sin(angle) * radius
        );
    };

    // When location changes, queue the move
    useEffect(() => {
        if (currentLocation !== previousLocation && previousLocation) {
            const target = getBasePosition(currentLocation, agent.name);

            if (executeCount.current > 0) {
                // Movement in progress - queue this move
                queuedMove.current = target;
            } else {
                // Start new move
                const current = groupRef.current?.position || new THREE.Vector3();
                moveStart.current = current.clone();
                moveTarget.current = target;
                executeCount.current = FRAMES_PER_MOVE;
            }
        }
    }, [currentLocation, previousLocation, agent.name]);

    useFrame((state, delta) => {
        if (!groupRef.current) return;
        if (isPaused) return; // Pause support

        const current = groupRef.current.position;

        // TALKING STATE - highest priority
        if (isTalking || speechBubble) {
            talkPhase.current += delta * 4;
            if (headRef.current) {
                headRef.current.rotation.x = Math.sin(talkPhase.current) * 0.15;
                headRef.current.rotation.z = Math.sin(talkPhase.current * 0.6) * 0.08;
            }
            if (rightArmRef.current) {
                rightArmRef.current.rotation.x = -0.6 + Math.sin(talkPhase.current) * 0.3;
                rightArmRef.current.rotation.z = -0.35 + Math.sin(talkPhase.current * 1.2) * 0.2;
            }
            // Reset legs
            if (leftLegRef.current) leftLegRef.current.rotation.x *= 0.9;
            if (rightLegRef.current) rightLegRef.current.rotation.x *= 0.9;
            if (leftArmRef.current) leftArmRef.current.rotation.x *= 0.9;

            // Still move to target if needed (smooth slide while talking)
            if (moveTarget.current) {
                current.lerp(moveTarget.current, 0.05);
            }
            return;
        }

        // MOVING STATE - Stanford frame counter approach
        if (executeCount.current > 0 && moveTarget.current && moveStart.current) {
            executeCount.current--;

            // Calculate progress (0 to 1)
            const progress = 1 - (executeCount.current / FRAMES_PER_MOVE);

            // Linear interpolation from start to target
            current.lerpVectors(moveStart.current, moveTarget.current, progress);
            current.y = Math.abs(Math.sin(walkPhase.current * 2)) * 0.1; // Bounce

            // Face movement direction
            const direction = new THREE.Vector3().subVectors(moveTarget.current, moveStart.current);
            if (direction.length() > 0.1) {
                const targetAngle = Math.atan2(direction.x, direction.z);
                groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, targetAngle, 0.15);
            }

            // Walking animation
            walkPhase.current += delta * 6;
            const walkAngle = Math.sin(walkPhase.current);
            if (leftLegRef.current) leftLegRef.current.rotation.x = walkAngle * 0.5;
            if (rightLegRef.current) rightLegRef.current.rotation.x = -walkAngle * 0.5;
            if (leftArmRef.current) leftArmRef.current.rotation.x = -walkAngle * 0.3;
            if (rightArmRef.current) rightArmRef.current.rotation.x = walkAngle * 0.3;

            // At end of move, snap to exact position
            if (executeCount.current === 0) {
                current.copy(moveTarget.current);
                current.y = 0;
                moveStart.current = null;
                moveTarget.current = null;

                // Check for queued move
                if (queuedMove.current) {
                    moveStart.current = current.clone();
                    moveTarget.current = queuedMove.current;
                    queuedMove.current = null;
                    executeCount.current = FRAMES_PER_MOVE;
                }
            }

            // Reset head
            if (headRef.current) {
                headRef.current.rotation.x *= 0.9;
                headRef.current.rotation.z *= 0.9;
            }
            return;
        }

        // IDLE STATE - breathing animation
        if (leftLegRef.current) leftLegRef.current.rotation.x *= 0.92;
        if (rightLegRef.current) rightLegRef.current.rotation.x *= 0.92;
        if (leftArmRef.current) leftArmRef.current.rotation.x *= 0.92;
        if (rightArmRef.current) rightArmRef.current.rotation.x *= 0.92;
        if (headRef.current) {
            headRef.current.rotation.x *= 0.9;
            headRef.current.rotation.z *= 0.9;
        }

        const breathe = Math.sin(state.clock.elapsedTime * 1.2) * 0.02;
        groupRef.current.scale.setScalar(AGENT_SCALE * (1 + breathe));
    });

    const getRoleColor = () => {
        const colors = {
            'Commander': '#FF6B35', 'Botanist': '#4CAF50', 'AI Assistant': '#00BCD4',
            'Engineer': '#FF9800', 'Surgeon': '#E91E63', 'Geologist': '#795548',
            'Communications Officer': '#2196F3', 'Crew Welfare Officer': '#9C27B0'
        };
        return colors[agent.role] || '#FFFFFF';
    };

    const roleColor = getRoleColor();
    const initialPos = getBasePosition(currentLocation, agent.name);

    return (
        <group ref={groupRef} position={initialPos} scale={AGENT_SCALE}>
            {/* Head/Helmet - BIGGER */}
            <group ref={headRef} position={[0, 1.9, 0]}>
                <mesh>
                    <sphereGeometry args={[0.35, 16, 16]} />
                    <meshStandardMaterial color="#FFFFFF" metalness={0.3} roughness={0.4} />
                </mesh>
                <mesh position={[0, 0, 0.25]}>
                    <sphereGeometry args={[0.26, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
                    <meshStandardMaterial color="#1a1a2e" metalness={0.9} roughness={0.1} />
                </mesh>
                <mesh position={[0.26, 0.2, 0.15]}>
                    <boxGeometry args={[0.12, 0.06, 0.06]} />
                    <meshBasicMaterial color={isTalking || speechBubble ? '#00FF00' : '#333333'} />
                </mesh>
            </group>

            {/* Body - BIGGER */}
            <mesh position={[0, 1.2, 0]}>
                <capsuleGeometry args={[0.38, 0.7, 8, 16]} />
                <meshStandardMaterial color="#EEEEEE" metalness={0.1} roughness={0.6} />
            </mesh>

            {/* Backpack */}
            <mesh position={[0, 1.3, -0.45]}>
                <boxGeometry args={[0.55, 0.7, 0.38]} />
                <meshStandardMaterial color="#CCCCCC" metalness={0.2} roughness={0.5} />
            </mesh>

            {/* Arms - BIGGER */}
            <group ref={leftArmRef} position={[-0.55, 1.45, 0]}>
                <mesh position={[0, -0.32, 0]}>
                    <capsuleGeometry args={[0.12, 0.58, 4, 8]} />
                    <meshStandardMaterial color="#EEEEEE" />
                </mesh>
                <mesh position={[0, -0.7, 0]}>
                    <sphereGeometry args={[0.14, 8, 8]} />
                    <meshStandardMaterial color="#CCCCCC" />
                </mesh>
            </group>
            <group ref={rightArmRef} position={[0.55, 1.45, 0]}>
                <mesh position={[0, -0.32, 0]}>
                    <capsuleGeometry args={[0.12, 0.58, 4, 8]} />
                    <meshStandardMaterial color="#EEEEEE" />
                </mesh>
                <mesh position={[0, -0.7, 0]}>
                    <sphereGeometry args={[0.14, 8, 8]} />
                    <meshStandardMaterial color="#CCCCCC" />
                </mesh>
            </group>

            {/* Legs - BIGGER */}
            <group ref={leftLegRef} position={[-0.2, 0.6, 0]}>
                <mesh position={[0, -0.38, 0]}>
                    <capsuleGeometry args={[0.15, 0.7, 4, 8]} />
                    <meshStandardMaterial color="#EEEEEE" />
                </mesh>
                <mesh position={[0, -0.85, 0.08]}>
                    <boxGeometry args={[0.22, 0.22, 0.32]} />
                    <meshStandardMaterial color="#666666" />
                </mesh>
            </group>
            <group ref={rightLegRef} position={[0.2, 0.6, 0]}>
                <mesh position={[0, -0.38, 0]}>
                    <capsuleGeometry args={[0.15, 0.7, 4, 8]} />
                    <meshStandardMaterial color="#EEEEEE" />
                </mesh>
                <mesh position={[0, -0.85, 0.08]}>
                    <boxGeometry args={[0.22, 0.22, 0.32]} />
                    <meshStandardMaterial color="#666666" />
                </mesh>
            </group>

            {/* Role badge */}
            <mesh position={[0, 1.5, 0.39]}>
                <circleGeometry args={[0.16, 16]} />
                <meshBasicMaterial color={roleColor} />
            </mesh>

            {/* Name tag - BIGGER text */}
            <Billboard position={[0, 2.8, 0]}>
                <Text fontSize={0.35} color="white" anchorX="center" outlineWidth={0.025} outlineColor="#000">
                    {agent.name.split(' ').pop()}
                </Text>
                <Text fontSize={0.22} color={roleColor} position={[0, -0.42, 0]} anchorX="center">
                    {executeCount.current > 0 ? '🚶 Walking...' : (isTalking || speechBubble) ? '💬 Talking' : ''}
                </Text>
            </Billboard>

            {/* Speech bubble - Shows thought and dialogue */}
            {speechBubble && (
                <Html position={[3, 2.5, 0]} center className="speech-bubble-3d" distanceFactor={25}>
                    <div className="bubble-content side-bubble">
                        <span className="bubble-arrow">◀</span>
                        {speechBubble.thought && (
                            <div className="bubble-thought">💭 {speechBubble.thought}</div>
                        )}
                        <div className="bubble-dialogue">"{speechBubble.dialogue}"</div>
                    </div>
                </Html>
            )}
        </group>
    );
}

// BIGGER Transparent Cylindrical Module
function CylinderModule({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const SCALE = 1.5; // Bigger scale

    return (
        <group position={location.position} scale={SCALE}>
            <mesh onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)} rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[2.5, 2.5, 8, 32]} />
                <meshStandardMaterial color={location.color} metalness={0.2} roughness={0.3} transparent opacity={0.3} emissive={isSelected ? location.color : hovered ? '#555' : '#000'} emissiveIntensity={isSelected ? 0.4 : hovered ? 0.2 : 0} />
            </mesh>
            <mesh rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[2.55, 2.55, 8.05, 16]} />
                <meshBasicMaterial color={location.color} wireframe />
            </mesh>
            {[-4.2, 4.2].map((x, i) => (
                <mesh key={i} position={[x, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
                    <cylinderGeometry args={[2.5, 2.2, 0.5, 32]} />
                    <meshStandardMaterial color="#AAAAAA" metalness={0.5} transparent opacity={0.5} />
                </mesh>
            ))}
            {[-2.8, 2.8].map((x, i) => (
                <mesh key={i} position={[x, -2, 0]}>
                    <cylinderGeometry args={[0.25, 0.35, 2]} />
                    <meshStandardMaterial color="#888888" metalness={0.6} />
                </mesh>
            ))}
            <Billboard position={[0, 4.5, 0]}>
                <Text fontSize={0.8} color={location.color} anchorX="center" outlineWidth={0.04} outlineColor="#000" fontWeight="bold">
                    {location.name}
                </Text>
                {agentCount > 0 && (
                    <Text fontSize={0.5} color="white" position={[0, -0.9, 0]} anchorX="center">
                        {agentCount} crew
                    </Text>
                )}
            </Billboard>
        </group>
    );
}

// BIGGER Transparent Dome (Mission Control)
function DomeModule({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const SCALE = 1.6;

    return (
        <group position={location.position} scale={SCALE}>
            <mesh onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
                <sphereGeometry args={[5, 32, 32, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshStandardMaterial color={location.color} metalness={0.2} roughness={0.3} transparent opacity={0.3} emissive={isSelected ? location.color : hovered ? '#555' : '#000'} emissiveIntensity={isSelected ? 0.5 : hovered ? 0.2 : 0} />
            </mesh>
            <mesh>
                <sphereGeometry args={[5.1, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshBasicMaterial color={location.color} wireframe />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[5, 0.5, 8, 32]} />
                <meshStandardMaterial color="#AAAAAA" metalness={0.5} />
            </mesh>
            <mesh position={[0, 5.5, 0]}>
                <cylinderGeometry args={[0.12, 0.12, 2.5]} />
                <meshStandardMaterial color="#888888" />
            </mesh>
            <mesh position={[0, 7, 0]}>
                <sphereGeometry args={[0.25, 8, 8]} />
                <meshBasicMaterial color="#FF0000" />
            </mesh>
            <Billboard position={[0, 9, 0]}>
                <Text fontSize={1} color="#FF6B35" anchorX="center" outlineWidth={0.05} outlineColor="#000" fontWeight="bold">
                    MISSION CONTROL
                </Text>
                {agentCount > 0 && (
                    <Text fontSize={0.6} color="white" position={[0, -1.2, 0]} anchorX="center">{agentCount} crew</Text>
                )}
            </Billboard>
        </group>
    );
}

// BIGGER Comms Tower
function CommsDish({ location, agentCount, isSelected, onClick }) {
    const dishRef = useRef();
    const [hovered, setHovered] = useState(false);
    const SCALE = 1.5;

    useFrame((state) => {
        if (dishRef.current) dishRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.12) * 0.5;
    });

    return (
        <group position={location.position} scale={SCALE}>
            <mesh onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
                <cylinderGeometry args={[4, 4, 1.2, 32]} />
                <meshStandardMaterial color={location.color} transparent opacity={0.3} emissive={isSelected || hovered ? location.color : '#000'} emissiveIntensity={0.3} />
            </mesh>
            <mesh><cylinderGeometry args={[4.05, 4.05, 1.25, 16]} /><meshBasicMaterial color={location.color} wireframe /></mesh>
            <mesh position={[0, 5, 0]}><cylinderGeometry args={[0.5, 0.6, 10]} /><meshStandardMaterial color="#888888" metalness={0.6} /></mesh>
            <group ref={dishRef} position={[0, 10, 0]}>
                <mesh rotation={[Math.PI / 4, 0, 0]}><sphereGeometry args={[3, 32, 32, 0, Math.PI * 2, 0, Math.PI / 2]} /><meshStandardMaterial color="#EEEEEE" metalness={0.8} roughness={0.2} side={THREE.DoubleSide} /></mesh>
                <mesh position={[0, 1.2, -2.4]} rotation={[Math.PI / 4, 0, 0]}><cylinderGeometry args={[0.25, 0.3, 1.2]} /><meshStandardMaterial color="#666666" /></mesh>
            </group>
            <Billboard position={[0, 14, 0]}><Text fontSize={0.8} color={location.color} anchorX="center" outlineWidth={0.04} outlineColor="#000">Comms Tower</Text></Billboard>
        </group>
    );
}

// BIGGER Mining Tunnel
function MiningTunnel({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const SCALE = 1.5;

    return (
        <group position={location.position} scale={SCALE}>
            <mesh rotation={[Math.PI / 2, 0, Math.PI / 4]} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
                <cylinderGeometry args={[3, 3, 10, 16, 1, true]} />
                <meshStandardMaterial color={location.color} transparent opacity={0.3} side={THREE.DoubleSide} emissive={isSelected || hovered ? location.color : '#000'} emissiveIntensity={0.3} />
            </mesh>
            <mesh rotation={[Math.PI / 2, 0, Math.PI / 4]}><cylinderGeometry args={[3.1, 3.1, 10.1, 12, 1, true]} /><meshBasicMaterial color={location.color} wireframe /></mesh>
            <mesh position={[0, 1.2, 0]} rotation={[0, Math.PI / 4, 0]}><boxGeometry args={[7, 6, 0.6]} /><meshStandardMaterial color="#FF6B35" metalness={0.5} /></mesh>
            {[-0.6, 0.6].map((offset, i) => (
                <mesh key={i} position={[4 + offset, -0.5, 4 + offset]} rotation={[0, Math.PI / 4, 0]}><boxGeometry args={[0.22, 0.22, 18]} /><meshStandardMaterial color="#444444" metalness={0.7} /></mesh>
            ))}
            <Billboard position={[0, 6, 0]}><Text fontSize={0.8} color={location.color} anchorX="center" outlineWidth={0.04} outlineColor="#000">Mining Tunnel</Text></Billboard>
        </group>
    );
}

// BIGGER Spoke paths
function SpokePaths() {
    return (
        <group>
            {LOCATIONS.slice(1).map((location, i) => {
                const center = [0, 0.2, 0];
                const end = [...location.position]; end[1] = 0.2;
                const startVec = new THREE.Vector3(...center);
                const endVec = new THREE.Vector3(...end);
                const length = startVec.distanceTo(endVec);
                const midpoint = startVec.clone().add(endVec).multiplyScalar(0.5);
                const angle = Math.atan2(endVec.x - startVec.x, endVec.z - startVec.z);

                return (
                    <group key={location.name}>
                        <mesh position={[midpoint.x, 0.15, midpoint.z]} rotation={[0, angle, 0]}>
                            <boxGeometry args={[2.2, 0.2, length]} />
                            <meshStandardMaterial color="#555555" metalness={0.3} roughness={0.7} />
                        </mesh>
                        {[-0.9, 0.9].map((offset, j) => (
                            <mesh key={j} position={[midpoint.x + Math.cos(angle + Math.PI / 2) * offset, 0.3, midpoint.z + Math.sin(angle + Math.PI / 2) * offset]} rotation={[0, angle, 0]}>
                                <boxGeometry args={[0.15, 0.2, length]} />
                                <meshStandardMaterial color={location.color} metalness={0.4} />
                            </mesh>
                        ))}
                        {Array.from({ length: Math.floor(length / 6) }).map((_, k) => {
                            const t = (k + 1) / (Math.floor(length / 6) + 1);
                            const markerPos = startVec.clone().lerp(endVec, t);
                            return (
                                <mesh key={k} position={[markerPos.x, 0.35, markerPos.z]} rotation={[-Math.PI / 2, 0, angle]}>
                                    <coneGeometry args={[0.4, 0.8, 4]} />
                                    <meshBasicMaterial color={location.color} transparent opacity={0.8} />
                                </mesh>
                            );
                        })}
                    </group>
                );
            })}
        </group>
    );
}

// ULTRA-REALISTIC Lunar Surface with rocks, craters, and terrain detail
function LunarSurface() {
    const rocksRef = useRef();

    // Generate random rocks
    const rocks = useMemo(() => {
        const r = [];
        for (let i = 0; i < 80; i++) {
            const angle = Math.random() * Math.PI * 2;
            const dist = 15 + Math.random() * 100;
            const size = 0.3 + Math.random() * 1.5;
            r.push({ x: Math.cos(angle) * dist, z: Math.sin(angle) * dist, size, rotY: Math.random() * Math.PI * 2 });
        }
        return r;
    }, []);

    // Generate craters
    const craters = useMemo(() => {
        const c = [];
        for (let i = 0; i < 25; i++) {
            const angle = Math.random() * Math.PI * 2;
            const dist = 50 + Math.random() * 80;
            const size = 3 + Math.random() * 8;
            c.push({ x: Math.cos(angle) * dist, z: Math.sin(angle) * dist, size });
        }
        return c;
    }, []);

    return (
        <group>
            {/* Main ground - darker gray with subtle variation */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.6, 0]} receiveShadow>
                <circleGeometry args={[150, 64]} />
                <meshStandardMaterial color="#3a3a3a" roughness={0.98} metalness={0.02} />
            </mesh>

            {/* Inner lighter area where station is */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.55, 0]}>
                <circleGeometry args={[55, 48]} />
                <meshStandardMaterial color="#4a4a4a" roughness={0.95} />
            </mesh>

            {/* Regolith layer - fine dust */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
                <ringGeometry args={[55, 150, 64]} />
                <meshStandardMaterial color="#2d2d2d" roughness={1} transparent opacity={0.7} />
            </mesh>

            {/* Craters */}
            {craters.map((crater, i) => (
                <group key={i} position={[crater.x, -0.5, crater.z]}>
                    {/* Crater rim */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[crater.size * 0.7, crater.size, 32]} />
                        <meshStandardMaterial color="#4a4a4a" roughness={0.9} />
                    </mesh>
                    {/* Crater inner */}
                    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
                        <circleGeometry args={[crater.size * 0.6, 24]} />
                        <meshStandardMaterial color="#252525" roughness={1} />
                    </mesh>
                </group>
            ))}

            {/* Rocks scattered across surface */}
            {rocks.map((rock, i) => (
                <mesh key={i} position={[rock.x, -0.3 + rock.size * 0.3, rock.z]} rotation={[Math.random() * 0.3, rock.rotY, Math.random() * 0.3]}>
                    <dodecahedronGeometry args={[rock.size, 0]} />
                    <meshStandardMaterial color={`hsl(0, 0%, ${25 + Math.random() * 15}%)`} roughness={0.95} />
                </mesh>
            ))}

            {/* Dust patches */}
            {Array.from({ length: 30 }).map((_, i) => {
                const angle = Math.random() * Math.PI * 2;
                const dist = 20 + Math.random() * 100;
                return (
                    <mesh key={i} rotation={[-Math.PI / 2, 0, 0]} position={[Math.cos(angle) * dist, -0.48, Math.sin(angle) * dist]}>
                        <circleGeometry args={[2 + Math.random() * 4, 16]} />
                        <meshStandardMaterial color="#363636" roughness={1} transparent opacity={0.5} />
                    </mesh>
                );
            })}
        </group>
    );
}

// Earth - BIGGER
function Earth() {
    const earthRef = useRef();
    useFrame(() => { if (earthRef.current) earthRef.current.rotation.y += 0.00015; });
    return (
        <mesh ref={earthRef} position={[-100, 65, -150]}>
            <sphereGeometry args={[20, 32, 32]} />
            <meshStandardMaterial color="#4169E1" emissive="#4169E1" emissiveIntensity={0.4} />
        </mesh>
    );
}

// Station sign - BIGGER
function StationSign() {
    return (
        <group position={[0, 0, 15]}>
            <mesh position={[0, 1.5, 0]}><cylinderGeometry args={[0.25, 0.25, 3]} /><meshStandardMaterial color="#888888" metalness={0.5} /></mesh>
            <mesh position={[0, 3.5, 0]}><boxGeometry args={[12, 1.5, 0.25]} /><meshStandardMaterial color="#FFFFFF" /></mesh>
            <Billboard position={[0, 3.5, 0.2]}><Text fontSize={0.8} color="#1a1a2e" anchorX="center" fontWeight="bold">ARYABHATTA STATION</Text></Billboard>
        </group>
    );
}

// BIGGER Lunar rover
function LunarRover({ position }) {
    const roverRef = useRef();
    useFrame((state) => { if (roverRef.current) roverRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.35) * 0.05; });
    return (
        <group ref={roverRef} position={position} scale={1.4}>
            <mesh position={[0, 0.8, 0]}><boxGeometry args={[2.5, 1, 3.2]} /><meshStandardMaterial color="#DDDDDD" metalness={0.3} /></mesh>
            <mesh position={[0, 1.4, 0]}><boxGeometry args={[1.8, 0.5, 1.8]} /><meshStandardMaterial color="#888888" metalness={0.5} /></mesh>
            {[[-1.3, -1.6], [1.3, -1.6], [-1.3, 1.6], [1.3, 1.6]].map(([x, z], i) => (
                <mesh key={i} position={[x, 0.45, z]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.5, 0.5, 0.4, 16]} /><meshStandardMaterial color="#333333" /></mesh>
            ))}
            <mesh position={[0, 2, 0]} rotation={[0.3, 0, 0]}><boxGeometry args={[2.2, 0.05, 1.4]} /><meshStandardMaterial color="#1a237e" metalness={0.8} /></mesh>
        </group>
    );
}

// Main Scene
function Scene({ agents, activities, selectedLocation, setSelectedLocation, previousLocations, isPaused }) {
    const talkingAgents = useMemo(() => {
        const talking = new Set();
        activities.filter(a => a.action === 'talk' && a.details?.includes('Said to')).slice(0, 5).forEach(a => talking.add(a.agent));
        return talking;
    }, [activities]);

    const speechBubbles = useMemo(() => {
        const bubbles = {};
        activities.filter(a => a.action === 'talk' && a.details?.includes('Said to')).slice(0, 3).forEach(a => {
            const match = a.details.match(/Said to .+?: "(.+)"/);
            if (match) {
                bubbles[a.agent] = {
                    dialogue: match[1].slice(0, 100) + (match[1].length > 100 ? '...' : ''),
                    thought: a.thought?.slice(0, 60) || null
                };
            }
        });
        return bubbles;
    }, [activities]);

    const getAgentsAtLocation = (locName) => agents.filter(a => a.location === locName);

    return (
        <>
            <ambientLight intensity={0.45} />
            <directionalLight position={[50, 60, 40]} intensity={1.3} castShadow />
            <pointLight position={[0, 25, 0]} intensity={0.9} color="#FFF5E1" />

            <Stars radius={400} depth={250} count={12000} factor={12} saturation={0} fade speed={0.15} />
            <Earth />
            <LunarSurface />
            <SpokePaths />

            {LOCATIONS.map((loc) => {
                const count = getAgentsAtLocation(loc.name).length;
                const props = { location: loc, agentCount: count, isSelected: selectedLocation === loc.name, onClick: () => setSelectedLocation(selectedLocation === loc.name ? null : loc.name) };
                switch (loc.type) {
                    case 'dome': return <DomeModule key={loc.name} {...props} />;
                    case 'dish': return <CommsDish key={loc.name} {...props} />;
                    case 'tunnel': return <MiningTunnel key={loc.name} {...props} />;
                    default: return <CylinderModule key={loc.name} {...props} />;
                }
            })}

            <LunarRover position={[45, 0, 40]} />

            {agents.map(agent => (
                <Astronaut
                    key={agent.name}
                    agent={agent}
                    currentLocation={agent.location}
                    previousLocation={previousLocations[agent.name]}
                    speechBubble={speechBubbles[agent.name]}
                    isTalking={talkingAgents.has(agent.name)}
                    allAgents={agents}
                    isPaused={isPaused}
                />
            ))}

            <OrbitControls makeDefault enablePan enableZoom enableRotate minDistance={30} maxDistance={180} maxPolarAngle={Math.PI / 2.1} target={[0, 0, 0]} />
        </>
    );
}

// Agent Status Bar (Stanford-style)
function AgentStatusBar({ agents, activities, onAgentClick }) {
    const getEmoji = (agent) => {
        const activity = activities.find(a => a.agent === agent.name);
        if (!activity) return '😐';
        switch (activity.action) {
            case 'talk': return '💬';
            case 'move': return '🚶';
            case 'work': return '⚙️';
            case 'rest': return '😴';
            default: return '🤔';
        }
    };

    return (
        <div className="agent-status-bar">
            {agents.map(agent => (
                <div
                    key={agent.name}
                    className="agent-status-item"
                    onClick={() => onAgentClick && onAgentClick(agent.name)}
                    title={agent.name}
                >
                    <div className="agent-initials" style={{ background: getRoleColor(agent.role) }}>
                        {agent.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <span className="agent-emoji">{getEmoji(agent)}</span>
                </div>
            ))}
        </div>
    );
}

// Main Component
export default function LunarBase({ agents, activities, onAgentClick, isPaused = false }) {
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [previousLocations, setPreviousLocations] = useState({});

    useEffect(() => {
        const newPrev = {};
        agents.forEach(agent => {
            const prev = previousLocations[agent.name];
            if (prev !== agent.location) newPrev[agent.name] = prev || agent.location;
            else newPrev[agent.name] = prev;
        });
        setPreviousLocations(newPrev);
    }, [agents]);

    return (
        <div className="lunar-base-container">
            <Canvas camera={{ position: [70, 55, 85], fov: 50 }} shadows style={{ background: '#000000' }}>
                <Suspense fallback={null}>
                    <Scene
                        agents={agents}
                        activities={activities}
                        selectedLocation={selectedLocation}
                        setSelectedLocation={setSelectedLocation}
                        previousLocations={previousLocations}
                        isPaused={isPaused}
                    />
                </Suspense>
            </Canvas>

            {/* Agent Status Bar (Stanford-style) */}
            <AgentStatusBar agents={agents} activities={activities} onAgentClick={onAgentClick} />

            <div className="base-overlay">
                <div className="controls-hint"><span>🖱️ Drag to rotate</span><span>🔍 Scroll to zoom</span><span>👆 Click location to see crew</span></div>
            </div>

            {selectedLocation && (
                <div className="location-info-panel">
                    <button className="close-btn" onClick={() => setSelectedLocation(null)}>✕</button>
                    <h2>{selectedLocation}</h2>
                    <div className="crew-list">
                        {agents.filter(a => a.location === selectedLocation).map(agent => (
                            <div
                                key={agent.name}
                                className="crew-member clickable"
                                onClick={() => onAgentClick && onAgentClick(agent.name)}
                            >
                                <div className="crew-badge" style={{ background: getRoleColor(agent.role) }} />
                                <div>
                                    <strong>{agent.name}</strong>
                                    <span>{agent.role}</span>
                                </div>
                            </div>
                        ))}
                        {agents.filter(a => a.location === selectedLocation).length === 0 && <p className="empty">No crew present</p>}
                    </div>
                </div>
            )}
        </div>
    );
}

function getRoleColor(role) {
    return { 'Commander': '#FF6B35', 'Botanist': '#4CAF50', 'AI Assistant': '#00BCD4', 'Engineer': '#FF9800', 'Surgeon': '#E91E63', 'Geologist': '#795548', 'Communications Officer': '#2196F3', 'Crew Welfare Officer': '#9C27B0' }[role] || '#FFFFFF';
}
