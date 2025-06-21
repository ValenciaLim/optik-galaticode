import React, { useState, useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Line } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import './App.css';

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
    return <Line points={points} color="gray" lineWidth={0.5} dashed dashSize={0.4} gapSize={0.2} />;
}

function TraceNode({ variant, radius, theme, setSelectedObject }) {
    const meshRef = useRef();

    useFrame(({ clock }) => {
        const angle = clock.getElapsedTime() * 0.5 + radius;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        if (meshRef.current) {
            meshRef.current.position.set(x, 0, z);
        }
    });

    const color = useMemo(() => {
        const baseHue = theme?.hue || 0.6;
        const lightness = 0.4 + (variant.evaluationScore * 0.4); 
        return new THREE.Color().setHSL(baseHue, 0.7, lightness);
    }, [variant.evaluationScore, theme]);

    return (
        <mesh 
            ref={meshRef}
            onPointerOver={(e) => { e.stopPropagation(); setSelectedObject(variant); }}
            onPointerOut={(e) => { e.stopPropagation(); setSelectedObject(null); }}
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

function Planet({ planet, theme, setSelectedObject }) {
    const { deployedVersion, traceHistory, name, status } = planet;

    const isDeployed = status === 'deployed';

    return (
        <group position={planet.position}>
            <mesh
                onPointerOver={(e) => { e.stopPropagation(); setSelectedObject({ ...deployedVersion, isDeployed, planetName: name }); }}
                onPointerOut={(e) => { e.stopPropagation(); setSelectedObject(null); }}
            >
                <sphereGeometry args={[0.8 + deployedVersion.evaluationScore * 1.2, 32, 32]} />
                 <meshStandardMaterial 
                    color={new THREE.Color().setHSL(theme?.hue || 0.6, 0.8, 0.5 + deployedVersion.evaluationScore * 0.2)}
                    metalness={0.5}
                    roughness={0.2}
                    emissive={new THREE.Color().setHSL(theme?.hue || 0.6, 0.8, 0.5 + deployedVersion.evaluationScore * 0.2)}
                    emissiveIntensity={isDeployed ? 1 : 0}
                    toneMapped={false}
                />
            </mesh>
            
            {traceHistory.map((variant, index) => (
                <TraceNode 
                    key={variant.id}
                    variant={variant}
                    radius={2.5 + index * 0.6}
                    theme={theme}
                    setSelectedObject={setSelectedObject}
                />
            ))}
        </group>
    );
}

function Galaxy({ galaxy, setSelectedObject, onStationClick }) {
    return (
        <group position={galaxy.position}>
            <pointLight position={[0, 0, 0]} intensity={1.5} distance={150} />
            <SpaceStation 
                health={1}
                onClick={() => onStationClick(galaxy)} 
            />

            {galaxy.planets && galaxy.planets.map(planet => (
                <OrbitLine key={`orbit-${planet.id}`} radius={planet.orbitRadius} />
            ))}
            
            {galaxy.planets && galaxy.planets.map(planet => (
                <Planet key={planet.id} planet={planet} theme={galaxy.theme} setSelectedObject={setSelectedObject} />
            ))}
        </group>
    );
}

function App() {
  const [galaxies, setGalaxies] = useState({});
  const [selectedObject, setSelectedObject] = useState(null);
  const [statusMessage, setStatusMessage] = useState("Connecting to AI agent...");
  const [controlHubGalaxy, setControlHubGalaxy] = useState(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765');
    ws.onopen = () => setStatusMessage("Connection established. Waiting for agent...");
    ws.onclose = () => setStatusMessage("Connection lost. Please restart the backend and refresh.");
    ws.onerror = () => setStatusMessage("Connection error. Is the backend running?");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'init' || data.type === 'update') {
          setGalaxies(data.payload);
      } else if (data.type === 'status') {
          setStatusMessage(data.message);
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="app-container">
      <ControlHub galaxy={controlHubGalaxy} onClose={() => setControlHubGalaxy(null)} />
      <StatusBar message={statusMessage} />
      <Canvas camera={{ position: [0, 40, 100], fov: 50 }}>
        <ambientLight intensity={0.1} />
        <Stars />
        {Object.values(galaxies).map(galaxy => (
            <Galaxy 
              key={galaxy.id}
              galaxy={galaxy} 
              setSelectedObject={setSelectedObject}
              onStationClick={setControlHubGalaxy}
            />
        ))}
        <EffectComposer>
            <Bloom luminanceThreshold={0.6} luminanceSmoothing={0.9} height={300} intensity={1.2} />
        </EffectComposer>
        <OrbitControls
          enablePan={true}
          minDistance={10}
          maxDistance={250}
        />
      </Canvas>
      <StatsBox selectedObject={selectedObject} />
    </div>
  );
}

function Stars() {
  const count = 5000;
  const positions = useMemo(() => {
    let positions = [];
    for (let i = 0; i < count; i++) {
      positions.push((Math.random() - 0.5) * 300, (Math.random() - 0.5) * 300, (Math.random() - 0.5) * 300);
    }
    return new Float32Array(positions);
  }, []);
  return <points><bufferGeometry><bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} /></bufferGeometry><pointsMaterial attach="material" size={0.15} color="white" /></points>;
}

function StatsBox({ selectedObject }) {
    if (!selectedObject) return null;
    return (
      <div className="stats-box">
        <h3>{selectedObject.isDeployed ? `${selectedObject.planetName} (Deployed)` : 'Trace Variant'}</h3>
        <p><strong>Evaluation Score:</strong> {selectedObject.evaluationScore}</p>
        <div className="telemetry-section">
          <h4>Telemetry</h4>
          <p>Latency: {selectedObject.telemetry?.latency}</p>
          <p>Cost: {selectedObject.telemetry?.cost}</p>
        </div>
         <div className="history-section">
            <h4>Full Text</h4>
            <div className="history-log"><p>{selectedObject.text}</p></div>
        </div>
      </div>
    );
}

function StatusBar({ message }) {
    if(!message) return null;
    return <div className="status-bar"><p>{message}</p></div>;
}

function SpaceStation({ health, onClick }) {
    const stationRef = useRef();
    const [isHovered, setIsHovered] = useState(false);
    useFrame((state, delta) => { if (stationRef.current) stationRef.current.rotation.y += 0.1 * delta; });
    const stationColor = new THREE.Color().setHSL(health * 0.33, 0.8, 0.5);
    useEffect(() => { document.body.style.cursor = isHovered ? 'pointer' : 'auto'; }, [isHovered]);
    return (
        <group ref={stationRef} scale={isHovered ? [0.6, 0.6, 0.6] : [0.5, 0.5, 0.5]} rotation-x={-Math.PI / 12} onClick={(e) => { e.stopPropagation(); onClick(); }} onPointerOver={(e) => { e.stopPropagation(); setIsHovered(true); }} onPointerOut={(e) => { e.stopPropagation(); setIsHovered(false); }}>
            <mesh><sphereGeometry args={[1.5, 16, 16]} /><meshBasicMaterial color={stationColor} /></mesh>
            <mesh rotation-x={Math.PI / 2}><torusGeometry args={[4, 0.3, 8, 48]} /><meshBasicMaterial color="darkgrey" /></mesh>
            <mesh position={[2.75, 0, 0]} rotation-y={Math.PI / 2}><boxGeometry args={[0.2, 0.2, 3]} /><meshBasicMaterial color="grey" /></mesh>
            <mesh position={[-2.75, 0, 0]} rotation-y={Math.PI / 2}><boxGeometry args={[0.2, 0.2, 3]} /><meshBasicMaterial color="grey" /></mesh>
            <mesh position={[0, 0, 2.75]}><boxGeometry args={[0.2, 0.2, 3]} /><meshBasicMaterial color="grey" /></mesh>
            <mesh position={[0, 0, -2.75]}><boxGeometry args={[0.2, 0.2, 3]} /><meshBasicMaterial color="grey" /></mesh>
        </group>
    );
}

function ControlHub({ galaxy, onClose }) {
    if (!galaxy) return null;
    return (
        <div className="control-hub">
            <button className="control-hub-close-btn" onClick={onClose}></button>
            <h3>{galaxy.name} Control Hub</h3>
            <div className="hub-section">
                <h4>Alerts</h4>
                {galaxy.alerts && galaxy.alerts.length > 0 ? (
                    <ul className="alerts-list">
                        {galaxy.alerts.map((alert, i) => <li key={i}>{alert}</li>)}
                    </ul>
                ) : <p>No active alerts.</p>}
            </div>
            <div className="hub-section">
                <h4>Optimizer Configuration</h4>
                <p><strong>Active Optimizer:</strong> {galaxy.config.activeOptimizer}</p>
                <label>Select Metric:</label>
                <select>{galaxy.config.evaluationMetrics.map(m => <option key={m}>{m}</option>)}</select>
            </div>
            <div className="hub-section"><h4>Reports & Logs</h4><button>View Full Report</button></div>
        </div>
    );
}
export default App;
