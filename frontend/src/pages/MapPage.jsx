import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet';
import L from 'leaflet';
import { StatusBadge } from '../components/StatusBadge';
import { Layers, MapPin, Filter, Eye, Cpu, Radio, ShieldAlert } from 'lucide-react';

// Create SVG-based custom Leaflet icons for each status to avoid missing png icon asset issues
const createMarkerIcon = (color) => {
  return L.divIcon({
    className: 'custom-mineguard-pin',
    html: `
      <div style="
        background-color: ${color};
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid #ffffff;
        box-shadow: 0 0 10px ${color};
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="width: 6px; height: 6px; background-color: #ffffff; border-radius: 50%;"></div>
      </div>
    `,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -11],
  });
};

const ICONS = {
  CRITICAL: createMarkerIcon('#ef4444'),
  WARNING: createMarkerIcon('#f59e0b'),
  WATCH: createMarkerIcon('#38bdf8'),
  NORMAL: createMarkerIcon('#10b981'),
  OFFLINE: createMarkerIcon('#64748b'),
  STALE: createMarkerIcon('#d97706'),
};

export function MapPage({ latestTelemetry }) {
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeTelemetry, setNodeTelemetry] = useState([]);
  const [filterType, setFilterType] = useState('ALL');
  const [isSchematicMode, setIsSchematicMode] = useState(false);
  const [loading, setLoading] = useState(true);

  // Default center around Jharia demonstration pit
  const defaultCenter = [23.7541, 86.4215];

  useEffect(() => {
    loadNodes();
  }, []);

  const loadNodes = async () => {
    try {
      const data = await api.getNodes();
      setNodes(data.items || []);
      if (data.items?.length > 0 && !selectedNode) {
        setSelectedNode(data.items[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedNode) {
      api.getNodeTelemetry(selectedNode.node_id, { limit: 10 }).then(setNodeTelemetry).catch(console.error);
    }
  }, [selectedNode]);

  const filteredNodes = nodes.filter((node) => {
    if (filterType === 'ALL') return true;
    if (filterType === 'ONLINE') return node.connectivity_status === 'ONLINE';
    if (filterType === 'OFFLINE') return node.connectivity_status === 'OFFLINE';
    return node.node_type === filterType;
  });

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'calc(100vh - 80px)' }}>
      {/* Top Header & View Modes */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Geotechnical GIS Surface Viewer
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Spatial Distribution of Deformation Nodes | SIH26025
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={() => setIsSchematicMode(!isSchematicMode)}
            className={`btn ${isSchematicMode ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          >
            <Layers size={14} />
            {isSchematicMode ? 'Switch to Map Tiles' : 'Local Schematic Mode (Offline)'}
          </button>

          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#f8fafc',
              border: '1px solid var(--border-color)',
              padding: '0.35rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Nodes ({nodes.length})</option>
            <option value="ONLINE">Online Only</option>
            <option value="OFFLINE">Offline / Stale</option>
          </select>
        </div>
      </div>

      {/* Main Map + Inspector Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '1rem', flex: 1, minHeight: 0 }}>
        {/* Map View Container */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
          {isSchematicMode ? (
            /* Local-First High-Contrast 2D Schematic Grid */
            <div style={{
              width: '100%',
              height: '100%',
              backgroundColor: '#070b14',
              backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)',
              backgroundSize: '24px 24px',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              overflow: 'hidden'
            }}>
              <div style={{ padding: '0.75rem 1rem', backgroundColor: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8' }}>
                <span>DEMONSTRATION PIT SCHEMATIC GRID (NORTH 0°, EAST 90°)</span>
                <span style={{ color: '#38bdf8' }}>NO EXTERNAL TILES REQUIRED</span>
              </div>

              {/* Render Nodes relative to coordinates in SVG */}
              <svg style={{ width: '100%', height: 'calc(100% - 40px)' }} viewBox="0 0 800 500">
                {/* Pit Benches Schematic Contours */}
                <ellipse cx="400" cy="250" rx="350" ry="200" fill="none" stroke="#1e293b" strokeWidth="2" strokeDasharray="4" />
                <ellipse cx="400" cy="250" rx="260" ry="145" fill="none" stroke="#1e293b" strokeWidth="2" strokeDasharray="4" />
                <ellipse cx="400" cy="250" rx="160" ry="90" fill="none" stroke="#334155" strokeWidth="2" />
                <text x="360" y="255" fill="#475569" fontSize="12" fontWeight="600">PIT BOTTOM</text>

                {filteredNodes.map((n, i) => {
                  // Normalize coordinates to SVG canvas
                  const cx = 150 + (i % 3) * 220 + ((i * 35) % 60);
                  const cy = 100 + Math.floor(i / 3) * 160 + ((i * 25) % 50);
                  const isSel = selectedNode?.node_id === n.node_id;

                  return (
                    <g
                      key={n.node_id}
                      onClick={() => setSelectedNode(n)}
                      style={{ cursor: 'pointer' }}
                    >
                      {isSel && (
                        <circle cx={cx} cy={cy} r="18" fill="none" stroke="#38bdf8" strokeWidth="2" className="animate-ping" opacity="0.4" />
                      )}
                      <circle
                        cx={cx}
                        cy={cy}
                        r="10"
                        fill={n.connectivity_status === 'ONLINE' ? '#10b981' : '#64748b'}
                        stroke="#ffffff"
                        strokeWidth="2"
                      />
                      <text x={cx + 14} y={cy + 4} fill="#f8fafc" fontSize="11" fontWeight="600">
                        {n.node_id}
                      </text>
                      <text x={cx + 14} y={cy + 18} fill="#94a3b8" fontSize="9">
                        {n.elevation_m ? `${n.elevation_m}m` : ''} • {n.connectivity_status}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
          ) : (
            /* Standard Leaflet GIS Map */
            <MapContainer
              center={defaultCenter}
              zoom={15}
              style={{ width: '100%', height: '100%' }}
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Visual Pit Boundary Zone */}
              <Circle
                center={defaultCenter}
                radius={450}
                pathOptions={{ color: '#0284c7', fillColor: '#0284c7', fillOpacity: 0.08, dashArray: '5, 5' }}
              />

              {filteredNodes.map((node) => {
                const icon = node.connectivity_status === 'ONLINE' ? ICONS.NORMAL : ICONS.OFFLINE;
                return (
                  <Marker
                    key={node.node_id}
                    position={[node.latitude, node.longitude]}
                    icon={icon}
                    eventHandlers={{
                      click: () => setSelectedNode(node),
                    }}
                  >
                    <Popup>
                      <div style={{ minWidth: '180px' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>{node.node_id}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{node.name}</div>
                        <div style={{ marginTop: '0.4rem' }}>
                          <StatusBadge status={node.connectivity_status} type="connectivity" />
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '0.3rem' }}>
                          Elev: {node.elevation_m || 'N/A'} m • Type: {node.node_type}
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          )}
        </div>

        {/* Selected Node Details Inspector */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflowY: 'auto' }}>
          <div style={{ borderBottom: '1px solid #334155', paddingBottom: '0.75rem' }}>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
              Node Telemetry Inspector
            </h2>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Detailed field geotechnical telemetry
            </div>
          </div>

          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>IDENTIFIER</div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#38bdf8' }}>{selectedNode.node_id}</div>
                <div style={{ fontSize: '0.8rem', color: '#e2e8f0' }}>{selectedNode.name}</div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>STATUS & POWER</div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.2rem', alignItems: 'center' }}>
                  <StatusBadge status={selectedNode.connectivity_status} type="connectivity" />
                  <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    Battery: {selectedNode.battery_pct ? `${selectedNode.battery_pct.toFixed(0)}%` : 'N/A'}
                  </span>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>GEOGRAPHIC LOCATION</div>
                <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                  Lat: {selectedNode.latitude.toFixed(5)}°<br />
                  Lon: {selectedNode.longitude.toFixed(5)}°<br />
                  Elev: {selectedNode.elevation_m ? `${selectedNode.elevation_m.toFixed(1)} m` : 'N/A'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>RECENT TELEMETRY SAMPLES</div>
                {nodeTelemetry.length === 0 ? (
                  <div style={{ fontSize: '0.75rem', color: '#64748b', fontStyle: 'italic', marginTop: '0.3rem' }}>
                    No records received yet.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.4rem' }}>
                    {nodeTelemetry.slice(0, 4).map((r) => (
                      <div key={r.id} style={{ backgroundColor: '#1e293b', padding: '0.4rem 0.6rem', borderRadius: '4px', fontSize: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                          <span>{new Date(r.timestamp).toLocaleTimeString()}</span>
                          <span style={{ color: '#38bdf8' }}>{r.displacement_mm !== null ? `${r.displacement_mm.toFixed(3)} mm` : '0 mm'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.7rem' }}>
                          <span>Tilt: {r.vector_tilt_deg !== null ? `${r.vector_tilt_deg.toFixed(2)}°` : 'N/A'}</span>
                          <span>Vib: {r.vibration_rms_ms2 !== null ? `${r.vibration_rms_ms2.toFixed(2)} m/s²` : 'N/A'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.85rem' }}>
              Select a node marker on the map to inspect live geotechnical parameters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
