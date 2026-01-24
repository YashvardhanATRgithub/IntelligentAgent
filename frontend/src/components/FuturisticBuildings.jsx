// FuturisticBuildings.jsx - Glass dome habitats + UFO-saucer Mission Control
import { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text, Billboard } from '@react-three/drei';
import * as THREE from 'three';

// Grey concrete/metal palette (matching reference)
const MATERIALS = {
    concrete: '#8B8B8B',        // Grey concrete
    concreteDark: '#6B6B6B',    // Darker grey
    concreteLight: '#A0A0A0',   // Lighter grey
    metal: '#707070',           // Metal grey
    window: '#1a2a3a',          // Window dark blue
    windowGlow: '#4A90A0',      // Window glow
    glass: '#87CEEB',           // Light blue glass
    accent: '#00BFFF',          // Cyan accent
};

// ============================================================================
// MISSION CONTROL - Fully transparent: two discs with glass pillar between
// ============================================================================
export function SciFiCommandCenter({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const tint = { color: '#87CEEB', glow: '#00BFFF' }; // Sky blue glass

    return (
        <group position={[location.position[0], 0, location.position[2]]}>
            {/* Selection indicator */}
            {isSelected && (
                <>
                    <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[55, 60, 64]} />
                        <meshBasicMaterial color="#00FFFF" transparent opacity={0.8} />
                    </mesh>
                    <pointLight position={[0, 30, 0]} color="#00FFFF" intensity={5} distance={100} />
                </>
            )}

            {/* ============ BASE PLATFORM ============ */}
            <mesh position={[0, 1, 0]}>
                <cylinderGeometry args={[50, 55, 2, 48]} />
                <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.3} roughness={0.7} />
            </mesh>

            {/* Platform glow ring */}
            <mesh position={[0, 2, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[52, 0.3, 8, 64]} />
                <meshBasicMaterial color={MATERIALS.accent} transparent opacity={0.7} />
            </mesh>

            {/* ============ BOTTOM DISC - Transparent glass ============ */}
            <mesh
                onClick={onClick}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
                position={[0, 6, 0]}
            >
                <cylinderGeometry args={[48, 48, 4, 48]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.5 : 0.35}
                    emissive={isSelected ? tint.glow : hovered ? tint.glow : '#000'}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Bottom disc frame ring */}
            <mesh position={[0, 6, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[48, 0.5, 8, 64]} />
                <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
            </mesh>

            {/* ============ CENTRAL GLASS PILLAR - Fully transparent ============ */}
            <mesh position={[0, 22, 0]}>
                <cylinderGeometry args={[18, 22, 28, 48]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.02}
                    transparent
                    opacity={isSelected ? 0.45 : 0.3}
                    emissive={isSelected ? tint.glow : '#1a3a5a'}
                    emissiveIntensity={isSelected ? 0.25 : 0.1}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Pillar frame rings */}
            {[10, 22, 34].map((y, i) => (
                <mesh key={i} position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[20 - i * 0.5, 0.3, 8, 48]} />
                    <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                </mesh>
            ))}

            {/* ============ TOP DISC - Transparent glass ============ */}
            <mesh position={[0, 40, 0]}>
                <cylinderGeometry args={[45, 48, 4, 48]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.5 : 0.35}
                    emissive={isSelected ? tint.glow : hovered ? tint.glow : '#000'}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Top disc frame ring */}
            <mesh position={[0, 40, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[46, 0.5, 8, 64]} />
                <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
            </mesh>

            {/* ============ DOME ON TOP - Transparent ============ */}
            <mesh position={[0, 42, 0]}>
                <sphereGeometry args={[18, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.45 : 0.3}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Dome frame */}
            {[0, 45, 90, 135].map((deg, i) => {
                const rad = (deg * Math.PI) / 180;
                return (
                    <mesh key={i} position={[0, 42, 0]} rotation={[0, rad, 0]}>
                        <torusGeometry args={[18, 0.25, 8, 32, Math.PI]} />
                        <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                    </mesh>
                );
            })}

            {/* Interior warm lighting */}
            <pointLight position={[0, 22, 0]} color="#FFA500" intensity={2} distance={60} />

            {/* Entry */}
            <group position={[0, 2, 52]}>
                <mesh><boxGeometry args={[14, 8, 6]} /><meshStandardMaterial color={MATERIALS.concrete} metalness={0.3} roughness={0.6} /></mesh>
                <mesh position={[0, 0, 3.1]}><planeGeometry args={[10, 6]} /><meshStandardMaterial color={MATERIALS.window} emissive={tint.glow} emissiveIntensity={0.4} /></mesh>
            </group>

            <Billboard position={[0, 75, 0]}>
                <Text fontSize={4} color="#00BFFF" anchorX="center" outlineWidth={0.2} outlineColor="#000" fontWeight="bold">
                    MISSION CONTROL
                </Text>
                {agentCount > 0 && <Text fontSize={2.2} color="#00FF00" position={[0, -5, 0]} anchorX="center">{agentCount} CREW</Text>}
            </Billboard>
        </group>
    );
}

// ============================================================================
// HABITAT BUILDINGS - All transparent glass domes with colored tint
// ============================================================================
export function SciFiHabitat({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);

    // Different tint colors for each building
    const getTint = () => {
        switch (location.name) {
            case 'Mess Hall': return { color: '#F5DEB3', glow: '#FFD700', size: 22 };      // Warm wheat
            case 'Crew Quarters': return { color: '#87CEEB', glow: '#4FC3F7', size: 24 };  // Sky blue
            case 'Medical Bay': return { color: '#98FB98', glow: '#00FF7F', size: 20 };   // Pale green
            case 'Rec Room': return { color: '#DDA0DD', glow: '#DA70D6', size: 21 };      // Plum
            case 'Agri Lab': return { color: '#90EE90', glow: '#32CD32', size: 26 };      // Light green
            default: return { color: '#B0E0E6', glow: '#87CEEB', size: 20 };              // Powder blue
        }
    };
    const tint = getTint();

    return (
        <group position={[location.position[0], 0, location.position[2]]}>
            {/* Selection indicator */}
            {isSelected && (
                <>
                    <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[tint.size + 5, tint.size + 8, 64]} />
                        <meshBasicMaterial color={tint.glow} transparent opacity={0.8} />
                    </mesh>
                    <pointLight position={[0, tint.size, 0]} color={tint.glow} intensity={3} distance={50} />
                </>
            )}

            {/* ============ BASE PLATFORM - Grey concrete ============ */}
            <mesh position={[0, 1, 0]}>
                <cylinderGeometry args={[tint.size + 3, tint.size + 5, 2, 32]} />
                <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.2} roughness={0.8} />
            </mesh>

            {/* Platform rim glow */}
            <mesh position={[0, 2, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[tint.size + 4, 0.2, 8, 48]} />
                <meshBasicMaterial color={MATERIALS.accent} transparent opacity={0.6} />
            </mesh>

            {/* ============ GLASS DOME - Transparent! ============ */}
            <mesh
                onClick={onClick}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
                position={[0, 2, 0]}
            >
                <sphereGeometry args={[tint.size, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.5 : 0.35}
                    emissive={isSelected ? tint.glow : hovered ? tint.glow : '#000'}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Dome frame - lattice structure */}
            {[0, 45, 90, 135].map((deg, i) => {
                const rad = (deg * Math.PI) / 180;
                return (
                    <mesh key={i} position={[0, 2, 0]} rotation={[0, rad, 0]}>
                        <torusGeometry args={[tint.size, 0.3, 8, 32, Math.PI]} />
                        <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                    </mesh>
                );
            })}

            {/* Horizontal rings on dome */}
            {[0.3, 0.5, 0.7].map((t, i) => (
                <mesh key={i} position={[0, 2 + tint.size * Math.sin(Math.acos(1 - t)), 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[tint.size * Math.sin(Math.acos(t)), 0.2, 8, 32]} />
                    <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                </mesh>
            ))}

            {/* Interior floor */}
            <mesh position={[0, 2.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[tint.size - 1, 32]} />
                <meshStandardMaterial color="#4a4a4a" metalness={0.3} roughness={0.8} />
            </mesh>

            {/* Interior warm lighting (visible through glass) */}
            <pointLight position={[0, tint.size / 2, 0]} color="#FFA500" intensity={1.5} distance={tint.size * 2} />

            {/* Entry door */}
            <group position={[0, 1, tint.size + 2]}>
                <mesh>
                    <boxGeometry args={[8, 6, 4]} />
                    <meshStandardMaterial color={MATERIALS.concrete} metalness={0.3} roughness={0.6} />
                </mesh>
                <mesh position={[0, 0, 2.1]}>
                    <planeGeometry args={[5, 5]} />
                    <meshStandardMaterial color={MATERIALS.window} emissive={tint.glow} emissiveIntensity={0.4} />
                </mesh>
            </group>

            {/* Steps */}
            {[0, 1, 2].map((s, i) => (
                <mesh key={i} position={[0, 0.3 + s * 0.4, tint.size + 5 + s * 1]}>
                    <boxGeometry args={[10, 0.4, 1]} />
                    <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.2} roughness={0.7} />
                </mesh>
            ))}

            <Billboard position={[0, tint.size + 12, 0]}>
                <Text fontSize={2.5} color={tint.glow} anchorX="center" outlineWidth={0.12} outlineColor="#000" fontWeight="bold">
                    {location.name.toUpperCase()}
                </Text>
                {agentCount > 0 && <Text fontSize={1.5} color="#00FF00" position={[0, -3, 0]} anchorX="center">{agentCount} CREW</Text>}
            </Billboard>
        </group>
    );
}

// ============================================================================
// COMMS TOWER - Glass dome base with tower rising from top
// ============================================================================
export function SciFiCommsTower({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const dishRef = useRef();
    const domeSize = 22;
    const tint = { color: '#87CEEB', glow: '#00BFFF' };

    useFrame((state) => {
        if (dishRef.current) dishRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.08) * 0.4;
    });

    return (
        <group position={[location.position[0], 0, location.position[2]]}>
            {/* Selection indicator */}
            {isSelected && (
                <>
                    <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[domeSize + 5, domeSize + 8, 64]} />
                        <meshBasicMaterial color="#00FFFF" transparent opacity={0.8} />
                    </mesh>
                    <pointLight position={[0, 60, 0]} color="#00FFFF" intensity={4} distance={100} />
                </>
            )}

            {/* Base platform - grey concrete */}
            <mesh position={[0, 1, 0]}>
                <cylinderGeometry args={[domeSize + 3, domeSize + 5, 2, 32]} />
                <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.2} roughness={0.8} />
            </mesh>

            {/* Platform rim glow */}
            <mesh position={[0, 2, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[domeSize + 4, 0.2, 8, 48]} />
                <meshBasicMaterial color={MATERIALS.accent} transparent opacity={0.6} />
            </mesh>

            {/* ============ GLASS DOME ============ */}
            <mesh
                onClick={onClick}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
                position={[0, 2, 0]}
            >
                <sphereGeometry args={[domeSize, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.5 : 0.35}
                    emissive={isSelected ? tint.glow : hovered ? tint.glow : '#000'}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Dome frame */}
            {[0, 45, 90, 135].map((deg, i) => {
                const rad = (deg * Math.PI) / 180;
                return (
                    <mesh key={i} position={[0, 2, 0]} rotation={[0, rad, 0]}>
                        <torusGeometry args={[domeSize, 0.3, 8, 32, Math.PI]} />
                        <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                    </mesh>
                );
            })}

            {/* Interior floor */}
            <mesh position={[0, 2.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[domeSize - 1, 32]} />
                <meshStandardMaterial color="#4a4a4a" metalness={0.3} roughness={0.8} />
            </mesh>

            {/* Interior warm lighting */}
            <pointLight position={[0, domeSize / 2, 0]} color="#FFA500" intensity={1.5} distance={domeSize * 2} />

            {/* ============ TOWER RISING FROM DOME TOP ============ */}
            <mesh position={[0, domeSize + 30, 0]}>
                <cylinderGeometry args={[2, 4, 55, 8]} />
                <meshStandardMaterial color={MATERIALS.metal} metalness={0.6} roughness={0.3} />
            </mesh>

            {/* Tower accent rings */}
            {[domeSize + 10, domeSize + 25, domeSize + 40, domeSize + 55].map((y, i) => (
                <mesh key={i} position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[3.5 - i * 0.4, 0.15, 8, 24]} />
                    <meshBasicMaterial color={MATERIALS.accent} transparent opacity={0.7} />
                </mesh>
            ))}

            {/* Main dish */}
            <group ref={dishRef} position={[0, domeSize + 65, 0]}>
                <mesh rotation={[Math.PI / 4, 0, 0]}>
                    <sphereGeometry args={[12, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2.5]} />
                    <meshStandardMaterial color={MATERIALS.concreteLight} metalness={0.5} roughness={0.3} side={THREE.DoubleSide} />
                </mesh>
                <mesh position={[0, 4, -6]} rotation={[Math.PI / 4, 0, 0]}>
                    <coneGeometry args={[1, 5, 8]} />
                    <meshStandardMaterial color={MATERIALS.metal} metalness={0.7} roughness={0.3} />
                </mesh>
            </group>

            {/* Beacon */}
            <mesh position={[0, domeSize + 82, 0]}>
                <sphereGeometry args={[1.5]} />
                <meshBasicMaterial color="#FF0000" />
            </mesh>

            {/* Entry door */}
            <group position={[0, 1, domeSize + 2]}>
                <mesh><boxGeometry args={[8, 6, 4]} /><meshStandardMaterial color={MATERIALS.concrete} metalness={0.3} roughness={0.6} /></mesh>
                <mesh position={[0, 0, 2.1]}><planeGeometry args={[5, 5]} /><meshStandardMaterial color={MATERIALS.window} emissive={tint.glow} emissiveIntensity={0.4} /></mesh>
            </group>

            <Billboard position={[0, domeSize + 95, 0]}>
                <Text fontSize={2.8} color={MATERIALS.accent} anchorX="center" outlineWidth={0.12} outlineColor="#000" fontWeight="bold">
                    COMMS TOWER
                </Text>
                {agentCount > 0 && <Text fontSize={1.6} color="#00FF00" position={[0, -3.5, 0]} anchorX="center">{agentCount} CREW</Text>}
            </Billboard>
        </group>
    );
}

// ============================================================================
// MINING FACILITY - Glass dome like other habitats
// ============================================================================
export function SciFiMiningFacility({ location, agentCount, isSelected, onClick }) {
    const [hovered, setHovered] = useState(false);
    const domeSize = 24;
    const tint = { color: '#DEB887', glow: '#CD853F' }; // Burlywood/Peru for mining


    return (
        <group position={[location.position[0], 0, location.position[2]]}>
            {/* Selection indicator */}
            {isSelected && (
                <>
                    <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <ringGeometry args={[domeSize + 5, domeSize + 8, 64]} />
                        <meshBasicMaterial color={tint.glow} transparent opacity={0.8} />
                    </mesh>
                    <pointLight position={[0, domeSize, 0]} color={tint.glow} intensity={3} distance={50} />
                </>
            )}

            {/* ============ BASE PLATFORM ============ */}
            <mesh position={[0, 1, 0]}>
                <cylinderGeometry args={[domeSize + 3, domeSize + 5, 2, 32]} />
                <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.2} roughness={0.8} />
            </mesh>

            {/* Platform rim glow */}
            <mesh position={[0, 2, 0]} rotation={[Math.PI / 2, 0, 0]}>
                <torusGeometry args={[domeSize + 4, 0.2, 8, 48]} />
                <meshBasicMaterial color={tint.glow} transparent opacity={0.6} />
            </mesh>

            {/* ============ GLASS DOME ============ */}
            <mesh
                onClick={onClick}
                onPointerOver={() => setHovered(true)}
                onPointerOut={() => setHovered(false)}
                position={[0, 2, 0]}
            >
                <sphereGeometry args={[domeSize, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2]} />
                <meshStandardMaterial
                    color={tint.color}
                    metalness={0.1}
                    roughness={0.05}
                    transparent
                    opacity={isSelected ? 0.5 : 0.35}
                    emissive={isSelected ? tint.glow : hovered ? tint.glow : '#000'}
                    emissiveIntensity={isSelected ? 0.3 : hovered ? 0.15 : 0}
                    side={THREE.DoubleSide}
                />
            </mesh>

            {/* Dome frame */}
            {[0, 45, 90, 135].map((deg, i) => {
                const rad = (deg * Math.PI) / 180;
                return (
                    <mesh key={i} position={[0, 2, 0]} rotation={[0, rad, 0]}>
                        <torusGeometry args={[domeSize, 0.3, 8, 32, Math.PI]} />
                        <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                    </mesh>
                );
            })}

            {/* Horizontal rings on dome */}
            {[0.3, 0.5, 0.7].map((t, i) => (
                <mesh key={i} position={[0, 2 + domeSize * Math.sin(Math.acos(1 - t)), 0]} rotation={[Math.PI / 2, 0, 0]}>
                    <torusGeometry args={[domeSize * Math.sin(Math.acos(t)), 0.2, 8, 32]} />
                    <meshStandardMaterial color={MATERIALS.concrete} metalness={0.4} roughness={0.5} />
                </mesh>
            ))}

            {/* Interior floor */}
            <mesh position={[0, 2.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <circleGeometry args={[domeSize - 1, 32]} />
                <meshStandardMaterial color="#4a4a4a" metalness={0.3} roughness={0.8} />
            </mesh>

            {/* Interior warm lighting */}
            <pointLight position={[0, domeSize / 2, 0]} color="#FFA500" intensity={1.5} distance={domeSize * 2} />

            {/* Entry door */}
            <group position={[0, 1, domeSize + 2]}>
                <mesh><boxGeometry args={[8, 6, 4]} /><meshStandardMaterial color={MATERIALS.concrete} metalness={0.3} roughness={0.6} /></mesh>
                <mesh position={[0, 0, 2.1]}><planeGeometry args={[5, 5]} /><meshStandardMaterial color={MATERIALS.window} emissive={tint.glow} emissiveIntensity={0.4} /></mesh>
            </group>

            {/* Steps */}
            {[0, 1, 2].map((s, i) => (
                <mesh key={i} position={[0, 0.3 + s * 0.4, domeSize + 5 + s * 1]}>
                    <boxGeometry args={[10, 0.4, 1]} />
                    <meshStandardMaterial color={MATERIALS.concreteDark} metalness={0.2} roughness={0.7} />
                </mesh>
            ))}

            <Billboard position={[0, domeSize + 12, 0]}>
                <Text fontSize={2.5} color={tint.glow} anchorX="center" outlineWidth={0.12} outlineColor="#000" fontWeight="bold">
                    MINING FACILITY
                </Text>
                {agentCount > 0 && <Text fontSize={1.5} color="#00FF00" position={[0, -3, 0]} anchorX="center">{agentCount} CREW</Text>}
            </Billboard>
        </group>
    );
}

