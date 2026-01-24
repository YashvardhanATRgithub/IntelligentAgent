import { useRef, useState, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Billboard, Stars } from '@react-three/drei';
import * as THREE from 'three';
import './LunarBase.css';
import {
    SciFiHabitat,
    SciFiCommandCenter,
    SciFiCommsTower,
    SciFiMiningFacility
} from './FuturisticBuildings';

// Scattered layout: Mission Control at center, 7 locations spread FAR apart
// MUCH BIGGER SCALE for realistic industrial feel  
const SPOKE_DISTANCE = 150; // Buildings spread very far from center
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

    const AGENT_SCALE = 3.5;

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

    // Initial position - only compute once on mount to prevent teleporting
    const initialPos = useMemo(() => {
        const pos = getBasePosition(currentLocation, agent.name);
        return [pos.x, pos.y, pos.z];
    }, []); // Empty deps - only set initial position on mount

    return (
        <group ref={groupRef} position={initialPos} scale={AGENT_SCALE}>
            {/* ============ HELMET - Round with gold visor ============ */}
            <group ref={headRef} position={[0, 2.1, 0]}>
                {/* Helmet shell - white */}
                <mesh>
                    <sphereGeometry args={[0.42, 24, 24]} />
                    <meshStandardMaterial color="#F5F5F5" metalness={0.15} roughness={0.4} />
                </mesh>
                {/* Gold reflective visor */}
                <mesh position={[0, 0, 0.2]} rotation={[0.1, 0, 0]}>
                    <sphereGeometry args={[0.38, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
                    <meshStandardMaterial
                        color="#FFD700"
                        metalness={0.95}
                        roughness={0.05}
                        emissive="#805000"
                        emissiveIntensity={0.15}
                    />
                </mesh>
                {/* Helmet rim */}
                <mesh position={[0, -0.15, 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[0.35, 0.06, 8, 24]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.5} roughness={0.3} />
                </mesh>
                {/* Comm light - blinks when talking */}
                <mesh position={[0.38, 0.15, 0.15]}>
                    <boxGeometry args={[0.08, 0.04, 0.04]} />
                    <meshBasicMaterial color={isTalking || speechBubble ? '#00FF00' : '#333333'} />
                </mesh>
                {/* Helmet camera */}
                <mesh position={[-0.35, 0.2, 0.2]}>
                    <boxGeometry args={[0.08, 0.06, 0.1]} />
                    <meshStandardMaterial color="#222222" metalness={0.8} roughness={0.2} />
                </mesh>
            </group>

            {/* ============ TORSO - Bulky spacesuit ============ */}
            <group position={[0, 1.3, 0]}>
                {/* Main torso */}
                <mesh>
                    <capsuleGeometry args={[0.42, 0.65, 8, 16]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Chest plate with controls */}
                <mesh position={[0, 0.15, 0.38]}>
                    <boxGeometry args={[0.5, 0.4, 0.12]} />
                    <meshStandardMaterial color="#E0E0E0" metalness={0.3} roughness={0.4} />
                </mesh>
                {/* Chest display */}
                <mesh position={[0, 0.18, 0.45]}>
                    <planeGeometry args={[0.35, 0.22]} />
                    <meshStandardMaterial color="#1a1a2e" emissive={roleColor} emissiveIntensity={0.3} />
                </mesh>
                {/* Role color stripe on chest */}
                <mesh position={[0, -0.05, 0.44]}>
                    <boxGeometry args={[0.4, 0.08, 0.02]} />
                    <meshBasicMaterial color={roleColor} />
                </mesh>
                {/* Shoulder joints */}
                <mesh position={[-0.48, 0.25, 0]}>
                    <sphereGeometry args={[0.12, 16, 16]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
                <mesh position={[0.48, 0.25, 0]}>
                    <sphereGeometry args={[0.12, 16, 16]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
            </group>

            {/* ============ LIFE SUPPORT BACKPACK ============ */}
            <group position={[0, 1.4, -0.48]}>
                {/* Main pack */}
                <mesh>
                    <boxGeometry args={[0.6, 0.8, 0.4]} />
                    <meshStandardMaterial color="#E8E8E8" metalness={0.2} roughness={0.5} />
                </mesh>
                {/* Oxygen tanks */}
                <mesh position={[-0.18, 0, -0.15]} rotation={[0, 0, 0]}>
                    <cylinderGeometry args={[0.08, 0.08, 0.65, 12]} />
                    <meshStandardMaterial color="#FFFFFF" metalness={0.5} roughness={0.3} />
                </mesh>
                <mesh position={[0.18, 0, -0.15]} rotation={[0, 0, 0]}>
                    <cylinderGeometry args={[0.08, 0.08, 0.65, 12]} />
                    <meshStandardMaterial color="#FFFFFF" metalness={0.5} roughness={0.3} />
                </mesh>
                {/* Status light */}
                <mesh position={[0, 0.35, 0.21]}>
                    <sphereGeometry args={[0.04]} />
                    <meshBasicMaterial color="#00FF00" />
                </mesh>
                {/* Vents */}
                <mesh position={[0, -0.3, 0.21]}>
                    <boxGeometry args={[0.3, 0.12, 0.02]} />
                    <meshStandardMaterial color="#555555" metalness={0.7} roughness={0.3} />
                </mesh>
            </group>

            {/* ============ LEFT ARM ============ */}
            <group ref={leftArmRef} position={[-0.58, 1.55, 0]}>
                {/* Upper arm */}
                <mesh position={[0, -0.22, 0]}>
                    <capsuleGeometry args={[0.13, 0.35, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Elbow joint */}
                <mesh position={[0, -0.45, 0]}>
                    <sphereGeometry args={[0.1, 12, 12]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
                {/* Lower arm */}
                <mesh position={[0, -0.65, 0]}>
                    <capsuleGeometry args={[0.11, 0.3, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Glove */}
                <mesh position={[0, -0.88, 0]}>
                    <sphereGeometry args={[0.12, 12, 12]} />
                    <meshStandardMaterial color="#D0D0D0" metalness={0.2} roughness={0.6} />
                </mesh>
            </group>

            {/* ============ RIGHT ARM ============ */}
            <group ref={rightArmRef} position={[0.58, 1.55, 0]}>
                {/* Upper arm */}
                <mesh position={[0, -0.22, 0]}>
                    <capsuleGeometry args={[0.13, 0.35, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Elbow joint */}
                <mesh position={[0, -0.45, 0]}>
                    <sphereGeometry args={[0.1, 12, 12]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
                {/* Lower arm */}
                <mesh position={[0, -0.65, 0]}>
                    <capsuleGeometry args={[0.11, 0.3, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Glove */}
                <mesh position={[0, -0.88, 0]}>
                    <sphereGeometry args={[0.12, 12, 12]} />
                    <meshStandardMaterial color="#D0D0D0" metalness={0.2} roughness={0.6} />
                </mesh>
            </group>

            {/* ============ LEFT LEG ============ */}
            <group ref={leftLegRef} position={[-0.22, 0.7, 0]}>
                {/* Upper leg */}
                <mesh position={[0, -0.28, 0]}>
                    <capsuleGeometry args={[0.15, 0.45, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Knee joint */}
                <mesh position={[0, -0.55, 0]}>
                    <sphereGeometry args={[0.12, 12, 12]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
                {/* Lower leg */}
                <mesh position={[0, -0.78, 0]}>
                    <capsuleGeometry args={[0.13, 0.35, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Boot */}
                <mesh position={[0, -1.05, 0.08]}>
                    <boxGeometry args={[0.22, 0.18, 0.35]} />
                    <meshStandardMaterial color="#4a4a4a" metalness={0.3} roughness={0.6} />
                </mesh>
            </group>

            {/* ============ RIGHT LEG ============ */}
            <group ref={rightLegRef} position={[0.22, 0.7, 0]}>
                {/* Upper leg */}
                <mesh position={[0, -0.28, 0]}>
                    <capsuleGeometry args={[0.15, 0.45, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Knee joint */}
                <mesh position={[0, -0.55, 0]}>
                    <sphereGeometry args={[0.12, 12, 12]} />
                    <meshStandardMaterial color="#CCCCCC" metalness={0.4} roughness={0.4} />
                </mesh>
                {/* Lower leg */}
                <mesh position={[0, -0.78, 0]}>
                    <capsuleGeometry args={[0.13, 0.35, 6, 12]} />
                    <meshStandardMaterial color="#F0F0F0" metalness={0.1} roughness={0.5} />
                </mesh>
                {/* Boot */}
                <mesh position={[0, -1.05, 0.08]}>
                    <boxGeometry args={[0.22, 0.18, 0.35]} />
                    <meshStandardMaterial color="#4a4a4a" metalness={0.3} roughness={0.6} />
                </mesh>
            </group>

            {/* Role color stripes on arms */}
            <mesh position={[-0.58, 1.35, 0.12]} rotation={[0, 0, 0]}>
                <boxGeometry args={[0.22, 0.06, 0.02]} />
                <meshBasicMaterial color={roleColor} />
            </mesh>
            <mesh position={[0.58, 1.35, 0.12]} rotation={[0, 0, 0]}>
                <boxGeometry args={[0.22, 0.06, 0.02]} />
                <meshBasicMaterial color={roleColor} />
            </mesh>

            {/* ============ NAME TAG ============ */}
            <Billboard position={[0, 3.0, 0]}>
                <Text fontSize={0.35} color="white" anchorX="center" outlineWidth={0.03} outlineColor="#000" fontWeight="bold">
                    {agent.name.split(' ').pop()}
                </Text>
                <Text fontSize={0.18} color={roleColor} position={[0, -0.4, 0]} anchorX="center">
                    {agent.role}
                </Text>
                <Text fontSize={0.16} color="#88FF88" position={[0, -0.6, 0]} anchorX="center">
                    {executeCount.current > 0 ? '🚀 Moving...' : (isTalking || speechBubble) ? '💬 Talking' : ''}
                </Text>
            </Billboard>


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

// Earth - Realistic with visible blue ocean and green/brown continents
function Earth() {
    const earthRef = useRef();

    useFrame(() => {
        if (earthRef.current) earthRef.current.rotation.y += 0.0003;
    });

    return (
        <group ref={earthRef} position={[-180, 120, -250]}>
            {/* Main Earth sphere - PURE BLUE OCEAN */}
            <mesh>
                <sphereGeometry args={[35, 64, 64]} />
                <meshStandardMaterial color="#1565C0" metalness={0.3} roughness={0.6} />
            </mesh>

            {/* CONTINENTS - Green/brown landmasses as separate patches */}
            {/* North America */}
            <mesh position={[20, 18, 22]} rotation={[0.2, 0.5, 0.1]}>
                <sphereGeometry args={[12, 32, 32, 0, Math.PI, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#228B22" metalness={0} roughness={0.9} />
            </mesh>

            {/* South America */}
            <mesh position={[18, -8, 25]} rotation={[-0.3, 0.3, 0]}>
                <sphereGeometry args={[8, 32, 32, 0, Math.PI * 0.7, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#2E8B57" metalness={0} roughness={0.9} />
            </mesh>

            {/* Europe/Africa */}
            <mesh position={[-5, 10, 32]} rotation={[0.1, -0.2, 0]}>
                <sphereGeometry args={[10, 32, 32, 0, Math.PI * 0.8, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#228B22" metalness={0} roughness={0.9} />
            </mesh>

            {/* Africa */}
            <mesh position={[-2, -5, 33]} rotation={[-0.2, 0, 0.1]}>
                <sphereGeometry args={[11, 32, 32, 0, Math.PI * 0.9, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#8B4513" metalness={0} roughness={0.85} />
            </mesh>

            {/* Asia */}
            <mesh position={[-25, 15, 18]} rotation={[0.3, -0.8, 0.2]}>
                <sphereGeometry args={[14, 32, 32, 0, Math.PI, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#228B22" metalness={0} roughness={0.9} />
            </mesh>

            {/* Australia */}
            <mesh position={[-28, -15, 12]} rotation={[-0.5, -1, 0]}>
                <sphereGeometry args={[6, 32, 32, 0, Math.PI * 0.8, 0, Math.PI / 2]} />
                <meshStandardMaterial color="#D2691E" metalness={0} roughness={0.85} />
            </mesh>

            {/* White polar ice caps */}
            <mesh position={[0, 33, 0]}>
                <sphereGeometry args={[10, 32, 16, 0, Math.PI * 2, 0, Math.PI / 4]} />
                <meshStandardMaterial color="#FFFFFF" metalness={0.1} roughness={0.3} />
            </mesh>
            <mesh position={[0, -33, 0]} rotation={[Math.PI, 0, 0]}>
                <sphereGeometry args={[12, 32, 16, 0, Math.PI * 2, 0, Math.PI / 4]} />
                <meshStandardMaterial color="#FFFFFF" metalness={0.1} roughness={0.3} />
            </mesh>

            {/* Thin clouds layer */}
            <mesh>
                <sphereGeometry args={[36, 32, 32]} />
                <meshStandardMaterial color="#FFFFFF" transparent opacity={0.15} metalness={0} roughness={1} />
            </mesh>

            {/* Atmosphere glow */}
            <mesh>
                <sphereGeometry args={[38, 32, 32]} />
                <meshBasicMaterial color="#4FC3F7" transparent opacity={0.12} side={THREE.BackSide} />
            </mesh>
        </group>
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
function Scene({ agents, activities, selectedLocation, setSelectedLocation, previousLocations, isPaused, onAgentClick }) {
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

            {/* Sci-Fi Buildings */}
            {LOCATIONS.map((loc) => {
                const count = getAgentsAtLocation(loc.name).length;
                const props = { location: loc, agentCount: count, isSelected: selectedLocation === loc.name, onClick: () => setSelectedLocation(selectedLocation === loc.name ? null : loc.name) };
                switch (loc.name) {
                    case 'Mission Control': return <SciFiCommandCenter key={loc.name} {...props} />;
                    case 'Comms Tower': return <SciFiCommsTower key={loc.name} {...props} />;
                    case 'Mining Tunnel': return <SciFiMiningFacility key={loc.name} {...props} />;
                    default: return <SciFiHabitat key={loc.name} {...props} />;
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

            <OrbitControls makeDefault enablePan enableZoom enableRotate minDistance={80} maxDistance={600} maxPolarAngle={Math.PI / 2.1} target={[0, 50, 0]} />
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
    // Local state for location selection (restored from old implementation)
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
            <Canvas camera={{ position: [200, 180, 250], fov: 50 }} shadows style={{ background: '#000000' }}>
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

            {/* Inline location panel - shows agents at selected location */}
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
