import React, { useState, useRef, useMemo, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree, useLoader } from '@react-three/fiber';
import { OrbitControls, Line, Text, Trail, Html, Stars, Sparkles } from '@react-three/drei';
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing';
import * as THREE from 'three';
import { useDrag } from '@use-gesture/react';
import './App.css';
import OnboardingForm from './OnboardingForm';
import MetricConfig from './MetricConfig';


// --- 3D Components ---

function Comet({ comet, onSelect }) {
    const meshRef = useRef();
    const [isHovered, setIsHovered] = useState(false);

    useFrame(() => {
        if (meshRef.current) {
            const progress = comet.progress || 0;
            const start = new THREE.Vector3(...comet.position);
            const trajectory = new THREE.Vector3(...comet.trajectory);
            meshRef.current.position.copy(start).addScaledVector(trajectory, progress * 60);
        }
    });

    return (
        <group>
            <Trail width={2} length={8} color={'#F0F0FF'} attenuation={(t) => t * t}>
                <mesh ref={meshRef} onPointerOver={(e) => { e.stopPropagation(); onSelect({...comet, isComet: true}); setIsHovered(true); }} onPointerOut={() => { onSelect(null); setIsHovered(false); }}>
                    <sphereGeometry args={[isHovered ? 1.2 : 0.8, 16, 16]} />
                    <meshStandardMaterial color="white" emissive="lightblue" emissiveIntensity={2} />
                </mesh>
            </Trail>
        </group>
    );
}

function OrbitLine({ radius }) {
    const points = useMemo(() => {
        const p = [];
        const numPoints = 128;
        for (let i = 0; i <= numPoints; i++) {
            const angle = (i / numPoints) * Math.PI * 2;
            p.push(new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius));
        }
        return p;
    }, [radius]);
    return <Line points={points} color="gray" lineWidth={0.7} dashed dashSize={0.4} gapSize={0.2} />;
}

function TraceNode({ variant, radius, onSelect, theme = {} }) {
    const nodeRef = useRef();

    useFrame(({ clock }) => {
        const angle = clock.getElapsedTime() * 0.5 + radius;
        if (nodeRef.current) {
            nodeRef.current.position.set(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
        }
    });
    
    const score = variant?.evaluation?.score ?? 0;
    const color = useMemo(() => new THREE.Color().setHSL(theme.hue || 0.6, 0.7, 0.4 + (score * 0.4)), [score, theme]);

    return (
        <mesh
            ref={nodeRef}
            onPointerOver={(e) => {
                e.stopPropagation();
                onSelect(variant);
                document.body.style.cursor = 'pointer';
            }}
            onPointerOut={() => {
                onSelect(null);
                document.body.style.cursor = 'auto';
            }}
        >
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshStandardMaterial
                color={color}
                metalness={0.3}
                roughness={0.4}
                emissive={color}
                emissiveIntensity={0.3}
            />
        </mesh>
    );
}

function PlanetMesh({ planet, texture, onSelect, onDoubleClick, theme, galaxyConfig }) {
    const { deployedVersion, traceHistory, status, orbitRadius } = planet;
    const isDeployed = status === 'deployed';

    const planetRef = useRef();
    const materialRef = useRef();
    
    // Get metric mappings from galaxy config
    const metricMapping = galaxyConfig?.metricMapping || {
        planetSize: "score",
        planetPosition: "score"
    };
    
    console.log('PlanetMesh metricMapping:', metricMapping);
    
    // Calculate dynamic properties based on metric mappings
    const getMetricValue = (metricName) => {
        // If the metric is not mapped (was set to empty), return null
        if (!metricMapping[metricName]) {
            return null;
        }
        const evaluation = deployedVersion?.evaluation || {};
        return evaluation[metricName] || null;
    };
    
    const sizeMetric = getMetricValue('planetSize');
    const positionMetric = getMetricValue('planetPosition');
    const speedMetric = getMetricValue('planetSpeed');
    
    // Debug logging for each planet
    console.log(`Planet ${planet.id}:`, {
        sizeMetric,
        positionMetric,
        speedMetric,
        score: deployedVersion?.evaluation?.score,
        metricMapping,
        orbitRadius: planet.orbitRadius
    });
    
    // Normalize metrics to 0-1 range (assuming most metrics are already in this range)
    // Use default values when metric is null (empty)
    const normalizedSizeMetric = sizeMetric !== null ? Math.max(0, Math.min(1, sizeMetric || 0)) : 0.5;
    const normalizedPositionMetric = positionMetric !== null ? Math.max(0, Math.min(1, positionMetric || 0)) : 0.5;
    const normalizedSpeedMetric = speedMetric !== null ? Math.max(0, Math.min(1, speedMetric || 0)) : 0; // Default to 0 (no movement)
    
    // Use individual planet orbit radius if no position metric is mapped
    const planetOrbitRadius = positionMetric !== null ? (10 + 30 * (1 - normalizedPositionMetric)) : (planet.orbitRadius || 15);
    const planetSize = sizeMetric !== null ? (0.5 + 2.5 * normalizedSizeMetric) : (0.5 + 2.5 * (deployedVersion?.evaluation?.score || 0.5));
    
    const planetColor = isDeployed ? new THREE.Color(0x44ff44) : new THREE.Color(0xaaaaaa);
    
    // Check if planet should pulse red (score < 0.5)
    const score = deployedVersion?.evaluation?.score ?? 0;
    const isCritical = score < 0.5;
    
    // Use speed metric for orbital movement speed - only move if speed metric is assigned
    const orbitalSpeed = metricMapping.planetSpeed ? (normalizedSpeedMetric * 0.5 + 0.1) : 0; // 0 speed when no metric assigned

    useFrame(({ clock }) => {
        if (planetRef.current) {
            // Position the planet on its orbit
            const time = clock.getElapsedTime();
            const angle = (orbitRadius || 0) + (metricMapping.planetSpeed ? time * orbitalSpeed : 0);
            const x = Math.cos(angle) * planetOrbitRadius;
            const z = Math.sin(angle) * planetOrbitRadius;
            planetRef.current.position.set(x, 0, z);
        }
        
        // Pulse red effect for critical planets
        if (materialRef.current && isCritical) {
            materialRef.current.emissiveIntensity = 0.6 + Math.sin(clock.getElapsedTime() * 4) * 0.4;
        }
    });

    const handleHover = (e, isHovering) => {
        e.stopPropagation();
        document.body.style.cursor = isHovering ? 'pointer' : 'auto';
        onSelect(isHovering ? { type: 'planet', ...planet } : null);
    };

    const handleDoubleClick = (e) => {
        e.stopPropagation();
        onDoubleClick(planet.id);
    };

    return (
        <group>
            <mesh
                ref={planetRef}
                onPointerOver={(e) => handleHover(e, true)}
                onPointerOut={(e) => handleHover(e, false)}
                onDoubleClick={handleDoubleClick}
            >
                <sphereGeometry args={[planetSize, 64, 64]} />
                {texture && isDeployed ? (
                    <meshStandardMaterial
                        ref={materialRef}
                        map={texture}
                        color={isCritical ? 0xff4444 : 0xffffff} // Red tint if critical
                        emissive={isCritical ? new THREE.Color(0xff4444) : new THREE.Color('#111111')} // Red emissive if critical
                        emissiveIntensity={isDeployed ? 0.7 : 0}
                        metalness={0}
                        roughness={0}
                        toneMapped={false}
                    />
                    ) : (
                    <meshStandardMaterial
                        ref={materialRef}
                        color={isCritical ? 0xff4444 : planetColor}
                        emissive={isCritical ? new THREE.Color(0xff4444) : planetColor}
                        emissiveIntensity={isDeployed ? 0.7 : 0}
                        metalness={0}
                        roughness={0}
                        toneMapped={false}
                    />
                )}
            </mesh>
            {/* {traceHistory?.map((variant, index) => (
                <TraceNode key={variant.id} variant={variant} radius={planetSize + 1.5 + index * 0.6} onSelect={onSelect} theme={theme} />
            ))} */}
        </group>
    );
}

function PlanetWithTextureLoader({ planet, textureUrl, onSelect, onDoubleClick, theme, galaxyConfig }) {
    const texture = useLoader(THREE.TextureLoader, textureUrl);
    return <PlanetMesh planet={planet} texture={texture} onSelect={onSelect} onDoubleClick={onDoubleClick} theme={theme} galaxyConfig={galaxyConfig} />;
}

function Planet({ planet, onSelect, onDoubleClick, textureTheme, theme, galaxyConfig }) {
    let textureUrl = null;
    if (textureTheme && textureTheme !== 'default') {
        const theme_generators = {
            'cats': `http://localhost:8080/api/texture?theme=cats&id=${planet.id}`,
            'pokemon': `http://localhost:8080/api/texture?theme=pokemon&id=${planet.id}`,
        };
        textureUrl = theme_generators[textureTheme];
    }
    
    if (!textureUrl) {
        return <PlanetMesh planet={planet} texture={null} onSelect={onSelect} onDoubleClick={onDoubleClick} theme={theme} galaxyConfig={galaxyConfig} />;
    }

    return <PlanetWithTextureLoader planet={planet} textureUrl={textureUrl} onSelect={onSelect} onDoubleClick={onDoubleClick} theme={theme} galaxyConfig={galaxyConfig} />;
}

function SpaceStation({ color, onDoubleClick, isCritical, status, statusMessage, onHover }) {
    const stationRef = useRef();
    const ringsRef = useRef();
    const [isHovered, setIsHovered] = useState(false);
    const materialRef = useRef();

    useFrame(( { clock }, delta) => {
        if (stationRef.current) stationRef.current.rotation.y += 0.1 * delta;
        if (ringsRef.current) {
            ringsRef.current.rotation.x = Math.PI / 2;
            ringsRef.current.rotation.y += 0.05 * delta;
            ringsRef.current.rotation.z -= 0.02 * delta;
        }
        if (isCritical && materialRef.current) {
            materialRef.current.emissiveIntensity = 0.6 + Math.sin(clock.getElapsedTime() * 4) * 0.4;
        }
    });

    useEffect(() => {
        document.body.style.cursor = isHovered ? 'pointer' : 'auto';
    }, [isHovered]);

    return (
        <group
            ref={stationRef}
            scale={isHovered ? 1.1 : 1}
            onPointerOver={(e) => {
                e.stopPropagation();
                setIsHovered(true);
                if (onHover) onHover(statusMessage || `Status: ${status}`);
            }}
            onPointerOut={() => {
                setIsHovered(false);
                if (onHover) onHover(null);
            }}
        >
            <mesh onDoubleClick={(e) => { e.stopPropagation(); onDoubleClick(); }}>
                <icosahedronGeometry args={[2.8, 1]} />
                <meshStandardMaterial ref={materialRef} color={color} emissive={color} emissiveIntensity={isCritical ? 1.0 : 0.6} metalness={0.8} roughness={0.2} />
            </mesh>
            <group ref={ringsRef}>
                <mesh>
                    <torusGeometry args={[4, 0.2, 8, 48]} />
                    <meshBasicMaterial color="white" />
                </mesh>
                <mesh rotation-x={Math.PI / 2} rotation-y={Math.PI / 3}>
                    <torusGeometry args={[5.5, 0.15, 8, 48]} />
                    <meshBasicMaterial color="white" />
                </mesh>
            </group>
        </group>
    );
}

function Galaxy({ galaxy, onSelect, onPlanetSelect, onGalaxyDoubleClick, onPlanetDoubleClick, onStationHover, textureTheme, onGalaxyMove, setOrbitControlsEnabled }) {
    const groupRef = useRef();
    const [position, setPosition] = useState(galaxy.position);
    const pointLightRef = useRef();
    const isOptimizing = galaxy.status === 'optimizing' || (galaxy.comets && galaxy.comets.length > 0);
    const isCritical = galaxy.status === 'critical';
    const hasPlanets = galaxy.planets && galaxy.planets.length > 0;

    // Check if any planet has a score below 0.5
    const hasCriticalPlanet = galaxy.planets?.some(planet => {
        const score = planet.deployedVersion?.evaluation?.score ?? 0;
        return score < 0.5;
    });

    const statusColor = useMemo(() => {
        if (!hasPlanets) return new THREE.Color("#aaaaaa");
        if (isCritical || hasCriticalPlanet) return new THREE.Color("#ff4d4d");
        if (isOptimizing) return new THREE.Color("#ffd700");
        return new THREE.Color("#4dff4d");
    }, [isCritical, isOptimizing, hasPlanets, hasCriticalPlanet]);

    useFrame(({ clock }) => {
        if (pointLightRef.current && (isCritical || hasCriticalPlanet)) {
            pointLightRef.current.intensity = 2.5 + Math.sin(clock.getElapsedTime() * 4) * 0.8;
        }
    });

    useEffect(() => {
        setPosition(galaxy.position);
    }, [galaxy.position]);

    const bind = useDrag(({ offset: [x, z], down, event }) => {
        event.stopPropagation();
        const newPosition = [x / 10, 0, z / 10]; // Scale down the movement
        setPosition(newPosition);
        if (!down) {
            onGalaxyMove(galaxy.id, newPosition);
        }
        setOrbitControlsEnabled(!down);
    }, {
        // Correctly transform screen-space drag into 3D-space movement on the XZ plane
        transform: ([x, y]) => [x, y],
        from: () => [position[0] * 10, position[2] * 10], // Scale up for mapping
    });

    return (
        <group
            {...bind()}
            ref={groupRef}
            position={position}
            onClick={(e) => { e.stopPropagation(); onSelect({ ...galaxy, isGalaxy: true, position }); }}
        >
            <group ref={pointLightRef}>
                <pointLight color={galaxy.theme?.hue ? new THREE.Color().setHSL(galaxy.theme.hue, 1, 0.6) : "white"} distance={100} intensity={isOptimizing ? 4 : 2} decay={2} />
            </group>
            <SpaceStation
                color={statusColor}
                onDoubleClick={() => onGalaxyDoubleClick(galaxy.id)}
                isCritical={isCritical || hasCriticalPlanet}
                status={galaxy.status}
                statusMessage={galaxy.status_message}
                onHover={onStationHover}
            />
            {galaxy.planets?.map(p => {
                // Use the same metric mapping logic as planets
                const metricMapping = galaxy.config?.metricMapping || {
                    planetSize: "score",
                    planetPosition: "score"
                };
                
                const getMetricValue = (metricName) => {
                    // If the metric is not mapped (was set to empty), return null
                    if (!metricMapping[metricName]) {
                        return null;
                    }
                    const evaluation = p.deployedVersion?.evaluation || {};
                    return evaluation[metricName] || null;
                };
                
                const positionMetric = getMetricValue('planetPosition');
                const normalizedPositionMetric = positionMetric !== null ? Math.max(0, Math.min(1, positionMetric || 0)) : 0.5;
                const orbitRadius = positionMetric !== null ? (10 + 30 * (1 - normalizedPositionMetric)) : (p.orbitRadius || 15);
                
                return <OrbitLine key={`orbit-${p.id}`} radius={orbitRadius} />;
            })}
            {galaxy.planets?.map(p => (
                <Planet key={p.id} planet={p} onSelect={onSelect} onDoubleClick={onPlanetDoubleClick} textureTheme={textureTheme} theme={galaxy.theme} galaxyConfig={galaxy.config} />
            ))}
            <Text
                position={[0, 8, 0]}
                fontSize={3}
                color="white"
                anchorX="center"
                font="https://fonts.gstatic.com/s/roboto/v18/KFOmCnqEu92Fr1Mu4mxM.woff"
            >
                {galaxy.name}
            </Text>
        </group>
    );
}


// --- Camera & Scene Logic ---

function MainScene({ galaxies, onGalaxyDoubleClick, onPlanetDoubleClick, onSelect, orbitControlsRef, onStationHover, textureTheme, onGalaxyMove, setOrbitControlsEnabled }) {
    return (
        <Suspense fallback={<Html center>Loading...</Html>}>
            <ambientLight intensity={2} />
            <pointLight position={[100, 100, 100]} intensity={2} />
            <directionalLight position={[-100, 50, -200]} intensity={1.5} />
            
            <Stars radius={200} depth={50} count={10000} factor={4} saturation={0} fade speed={1} />
            <Sparkles count={200} scale={150} size={2} speed={0.5} color="lightblue" />
            {galaxies.length === 0 ? (
                <Text>Loading galaxies...</Text>
                ) : (
                    galaxies.map(galaxy => (
                    <Galaxy
                        key={galaxy.id}
                        galaxy={galaxy}
                        onSelect={onSelect}
                        onGalaxyDoubleClick={() => onGalaxyDoubleClick(galaxy.id)}
                        onPlanetDoubleClick={(planetId) => onPlanetDoubleClick(planetId, galaxy.id)}
                        onStationHover={onStationHover}
                        textureTheme={textureTheme}
                        onGalaxyMove={onGalaxyMove}
                        setOrbitControlsEnabled={setOrbitControlsEnabled}
                    />
                ))
            )}
            <EffectComposer>
                <Bloom luminanceThreshold={0.8} luminanceSmoothing={0.9} height={300} />
                <Vignette eskil={false} offset={0.1} darkness={0.5} />
            </EffectComposer>
        </Suspense>
    );
}

function CameraController({ view, orbitControlsRef, galaxies, enabled }) {
    const { camera } = useThree();
    const lastFocusedView = useRef(null);
  
    useEffect(() => {
      if (!orbitControlsRef.current) return;
      const controls = orbitControlsRef.current;
      const cam = controls.object;
  
      // Only zoom in/out automatically if view type is galaxy or universe (breadcrumb)
      if (
        (view.type === 'galaxy' && view.id) ||
        view.type === 'universe'
      ) {
        // Prevent reapplying if same view:
        if (JSON.stringify(view) === JSON.stringify(lastFocusedView.current)) return;
  
        let targetPosition, targetLookAt;
  
        if (view.type === 'galaxy' && view.id) {
          const targetGalaxy = galaxies[view.id];
          if (targetGalaxy) {
            const galaxyCenter = new THREE.Vector3(...targetGalaxy.position);
            const radius = targetGalaxy.radius || 50;
  
            const fov = THREE.MathUtils.degToRad(cam.fov);
            const distance = radius / Math.sin(fov / 2);
            const tiltHeight = 20;
  
            targetPosition = new THREE.Vector3(
              galaxyCenter.x,
              galaxyCenter.y + tiltHeight,
              galaxyCenter.z + distance
            );
            targetLookAt = galaxyCenter;
          } else {
            console.error(`Galaxy not found for id: ${view.id}, defaulting.`);
            targetPosition = new THREE.Vector3(0, 80, 150);
            targetLookAt = new THREE.Vector3(0, 0, 0);
          }
        } else if (view.type === 'universe') {
          // Zoom out to show entire universe
          targetPosition = new THREE.Vector3(0, 150, 300);
          targetLookAt = new THREE.Vector3(0, 0, 0);
        }
  
        cam.position.copy(targetPosition);
        controls.target.copy(targetLookAt);
        controls.update();
        controls.saveState();
  
        lastFocusedView.current = JSON.parse(JSON.stringify(view)); // save current view
      } else {
        // For other view types or no special zoom, reset lastFocusedView so next galaxy/universe can trigger zoom
        lastFocusedView.current = null;
      }
    }, [view, galaxies, orbitControlsRef]);
  
    return (
      <OrbitControls
        ref={orbitControlsRef}
        enabled={enabled}
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={5}
        maxDistance={300}
      />
    );
  }

// --- UI Components ---

function Breadcrumb({ view, galaxies, onNavigate }) {
    const galaxy = view.type === 'galaxy'
        ? galaxies[view.id]
        : view.type === 'planet'
        ? galaxies[view.galaxyId]
        : null;

    const planet = view.type === 'planet' && galaxy
        ? galaxy.planets.find(p => p.id === view.id)
        : null;

    return (
        <div className="breadcrumb">
            <span className="breadcrumb-link" onClick={() => onNavigate({ type: 'universe', id: '' })}>Universe</span>
            {galaxy && (
                <>
                    <span> &gt; </span>
                    {view.type === 'planet' ? (
                        <span className="breadcrumb-link" onClick={() => onNavigate({ type: 'galaxy', id: galaxy.id })}>
                            {galaxy.name}
                        </span>
                    ) : (
                        <span>{galaxy.name}</span>
                    )}
                </>
            )}
            {planet && (
                <>
                    <span> &gt; </span>
                    <span>{planet.name}</span>
                </>
            )}
        </div>
    );
}

function StatsBox({ selectedObject, onDeleteAgent, onClose, onUpdateMetricMapping }) {
    if (!selectedObject) return null;

    if (selectedObject.isGalaxy) {
        return (
            <div className="stats-box">
                <div className="stats-header">
                    <h3>{selectedObject.name}</h3>
                    <button onClick={onClose} className="close-btn-stats">×</button>
                </div>
                {selectedObject.status_message && <p>{selectedObject.status_message}</p>}
                <MetricConfig 
                    galaxy={selectedObject} 
                    onUpdateMapping={onUpdateMetricMapping}
                />
                <button 
                    onClick={() => onDeleteAgent(selectedObject.id)}
                    className="delete-btn"
                >
                    Delete Agent
                </button>
            </div>
        );
    }

    if (selectedObject.isComet) {
        return (
            <div className="stats-box">
                <p><strong>ID:</strong> {selectedObject.id}</p>
                <p><strong>Target:</strong> Planet {selectedObject.targetPlanetId}</p>
                <p><strong>Progress:</strong> {Math.round(selectedObject.progress * 100)}%</p>
            </div>
        );
    }

    const evalData = selectedObject.evaluation;

    return (
      <div className="stats-box">
        <h3>{selectedObject.isDeployed ? `${selectedObject.planetName} (Deployed)` : `Variant ${selectedObject.id}`}</h3>
        <p><strong>Score:</strong> {evalData?.score.toFixed(2)}</p>
        <div className="telemetry-section">
          <h4>Opik Evaluation</h4>
          <p><strong>Factuality:</strong> {evalData?.factuality}</p>
          <p><strong>Hallucination:</strong> {evalData?.hallucination}</p>
          <p><strong>Speed (ms):</strong> {evalData?.speed}</p>
        </div>
         <div className="history-section">
            <h4>Full Text</h4>
            <div className="history-log"><p>{selectedObject.text}</p></div>
        </div>
      </div>
    );
}

function StatusBar({ message }) {
    if (!message) return null;
    return <div className="status-bar"><p>{message}</p></div>;
}

function ControlPanel({ onFilterChange, onSearchChange, searchQuery, healthFilter, onThemeChange, textureTheme, onOnboardClick }) {
    return (
        <div className="control-panel">
            <input
                type="text"
                placeholder="Search agents..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="search-input"
            />
            <div className="controls-row">
                <select value={healthFilter} onChange={(e) => onFilterChange(e.target.value)} className="filter-select">
                    <option value="all">All Health Statuses</option>
                    <option value="good">Good (0.8+)</option>
                    <option value="medium">Medium (0.6-0.8)</option>
                    <option value="poor">Poor (&lt;0.6)</option>
                </select>
                <select value={textureTheme} onChange={(e) => onThemeChange(e.target.value)} className="filter-select">
                    <option value="default">Default Planets</option>
                    <option value="cats">Cats</option>
                    <option value="pokemon">Pokemon</option>
                </select>
            </div>
            <button onClick={onOnboardClick} className="onboard-btn">Onboard New Agent</button>
        </div>
    );
}

function App() {
  const [galaxies, setGalaxies] = useState({});
  const [selectedObject, setSelectedObject] = useState(null);
  const [view, setView] = useState({ type: 'universe', id: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const [healthFilter, setHealthFilter] = useState('all');
  const [statusMessage, setStatusMessage] = useState("MCP ready. Awaiting instructions.");
  const [hoverMessage, setHoverMessage] = useState("");
  const orbitControlsRef = useRef();
  const [textureTheme, setTextureTheme] = useState('default');
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [orbitControlsEnabled, setOrbitControlsEnabled] = useState(true);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8765");

    ws.onopen = () => setStatusMessage("MCP connection established. Systems online.");
    ws.onclose = () => setStatusMessage("MCP connection lost. Attempting to reconnect...");
    ws.onerror = () => setStatusMessage("MCP connection error.");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'error') {
            console.error("MCP Error:", data.message);
            setStatusMessage(`Error: ${data.message}`);
        } else {
            // Merge updates instead of completely replacing state to preserve local changes
            setGalaxies(prev => {
                const updated = { ...prev };
                if (data.galaxies) {
                    Object.keys(data.galaxies).forEach(galaxyId => {
                        if (updated[galaxyId]) {
                            // Preserve local position changes
                            const currentPosition = updated[galaxyId].position;
                            updated[galaxyId] = { ...data.galaxies[galaxyId] };
                            if (currentPosition) {
                                updated[galaxyId].position = currentPosition;
                            }
                        } else {
                            updated[galaxyId] = data.galaxies[galaxyId];
                        }
                    });
                }
                return updated;
            });
        }
    };
    
    return () => {
        ws.close();
    };
  }, []);

  const handleGalaxyMove = async (galaxyId, newPosition) => {
    // Update local state immediately for responsive UI
    setGalaxies(prev => ({
        ...prev,
        [galaxyId]: {
            ...prev[galaxyId],
            position: newPosition,
        }
    }));

    // Persist the change to the backend
    try {
        const response = await fetch(`http://localhost:8080/api/agent/${galaxyId}/position`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ position: newPosition })
        });

        if (!response.ok) {
            console.error('Failed to update galaxy position on server');
        }
    } catch (error) {
        console.error('Error updating galaxy position:', error);
    }
  };

  const handleOnboard = (newAgent) => {
    setStatusMessage(`Agent "${newAgent.name}" successfully onboarded. Awaiting telemetry...`);
  };

  const handleDeleteAgent = async (agentId) => {
      if (!window.confirm(`Are you sure you want to delete agent "${galaxies[agentId].name}"?`)) {
          return;
      }

      try {
          const response = await fetch(`http://localhost:8080/api/agent/${agentId}`, {
              method: 'DELETE',
          });

          if (response.ok) {
              setStatusMessage(`Agent "${galaxies[agentId].name}" deleted.`);
              setSelectedObject(null);
          } else {
              const errorText = await response.text();
              alert(`Failed to delete agent: ${errorText}`);
          }
      } catch (error) {
          console.error("Delete agent API error:", error);
          alert("Failed to delete agent due to a network or server error.");
      }
  };

  const handleUpdateMetricMapping = (newMapping) => {
      setStatusMessage(`Metric mapping updated for ${selectedObject.name}`);
  };

  const handleThemeChange = (theme) => {
      setTextureTheme(theme);
      setStatusMessage(`Theme "${theme}" selected.`);
  };

  const handleGalaxyDoubleClick = (galaxyId) => {
    setView({ type: 'galaxy', id: galaxyId });
    setStatusMessage(`Focusing on ${galaxies[galaxyId].name} system.`);
  };

  const handlePlanetDoubleClick = (planetId, galaxyId) => {
      const galaxy = galaxies[galaxyId];
      const planet = galaxy?.planets.find(p => p.id === planetId);
      if (galaxy && planet) {
          setView({ type: 'planet', id: planetId, galaxyId: galaxyId });
          setStatusMessage(`Focusing on planet ${planet.name} in ${galaxy.name} system.`);
      }
  };

  const filteredGalaxies = Object.values(galaxies).filter(g => {
    if (!g) return false;
    const passesHealth = healthFilter === 'all' || (g.planets?.some(p => p.status === healthFilter));
    const passesSearch = searchQuery === '' || g.name?.toLowerCase().includes(searchQuery.toLowerCase()) || (g.planets?.some(p => p.name.toLowerCase().includes(searchQuery.toLowerCase())));
    return passesHealth && passesSearch;
  });

  const galaxiesForScene = view.type === 'galaxy' && view.id
    ? filteredGalaxies.filter(g => g.id === view.id)
    : filteredGalaxies;

    return (
      <div className="App">
        <div className="canvas-container">
          <Canvas camera={{ position: [0, 80, 150], fov: 50 }}>
              <MainScene
                  galaxies={galaxiesForScene}
                  onGalaxyDoubleClick={handleGalaxyDoubleClick}
                  onPlanetDoubleClick={handlePlanetDoubleClick}
                  onSelect={setSelectedObject}
                  orbitControlsRef={orbitControlsRef}
                  onStationHover={setHoverMessage}
                  textureTheme={textureTheme}
                  onGalaxyMove={handleGalaxyMove}
                  setOrbitControlsEnabled={setOrbitControlsEnabled}
              />
              <CameraController
                  view={view}
                  orbitControlsRef={orbitControlsRef}
                  galaxies={galaxies}
                  enabled={orbitControlsEnabled}
              />
          </Canvas>
        </div>
        <div className="ui-container">
          <Breadcrumb view={view} galaxies={galaxies} onNavigate={setView} />
          <ControlPanel
              onFilterChange={setHealthFilter}
              onSearchChange={setSearchQuery}
              searchQuery={searchQuery}
              healthFilter={healthFilter}
              onThemeChange={handleThemeChange}
              textureTheme={textureTheme}
              onOnboardClick={() => setIsOnboarding(true)}
          />
          <StatsBox 
            selectedObject={selectedObject} 
            onDeleteAgent={handleDeleteAgent}
            onClose={() => setSelectedObject(null)}
            onUpdateMetricMapping={handleUpdateMetricMapping}
          />
          <StatusBar message={statusMessage} hoverMessage={hoverMessage} />
          {isOnboarding && (
            <OnboardingForm 
              onOnboard={handleOnboard}
              onClose={() => setIsOnboarding(false)} 
            />
          )}
        </div>
      </div>
    );
}

export default App;
