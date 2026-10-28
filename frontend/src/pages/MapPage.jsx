import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polygon } from 'react-leaflet';
import L from 'leaflet';
import { StatusBadge } from '../components/StatusBadge';
import { Layers, MapPin, Filter, Eye, Cpu, Radio, ShieldAlert, ArrowRight, Info, AlertTriangle } from 'lucide-react';

// Create SVG-based custom Leaflet icons for each status
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

// Defined Mine Panels with realistic excavation footprints
const MINE_PANELS = [
  {
    id: 'Panel-North-01',
    name: 'North Longwall Active Seam (Panel-North-01)',
    method: 'Longwall',
    depth: '120 - 150m',
    color: '#38bdf8',
    coordinates: [
      [23.7548, 86.4205],
      [23.7565, 86.4215],
      [23.7558, 86.4248],
      [23.7538, 86.4235],
    ],
  },
  {
    id: 'Panel-West-03',
    name: 'West Bord & Pillar Extraction (Panel-West-03)',
    method: 'Bord and Pillar',
    depth: '80 - 100m',
    color: '#a855f7',
    coordinates: [
      [23.7510, 86.4168],
      [23.7530, 86.4170],
      [23.7525, 86.4210],
      [23.7505, 86.4205],
    ],
  },
  {
    id: 'Panel-East-02',
    name: 'East Open-Cast Waste Bench (Panel-East-02)',
    method: 'Open Cast Dump',
    depth: '40 - 65m',
    color: '#f59e0b',
    coordinates: [
      [23.7525, 86.4250],
      [23.7545, 86.4255],
      [23.7540, 86.4285],
      [23.7518, 86.4278],
    ],
  },
];

export function MapPage({ latestTelemetry, latestNodeStatus }) {
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeTelemetry, setNodeTelemetry] = useState([]);
  const [filterPanel, setFilterPanel] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');
  const [isSchematicMode, setIsSchematicMode] = useState(false);
  const [showDeformationSurface, setShowDeformationSurface] = useState(true);
  const [loading, setLoading] = useState(true);

  // Default center around Jharia demonstration pit
  const defaultCenter = [23.7541, 86.4215];

  useEffect(() => {
    loadNodes();
    const interval = setInterval(loadNodes, 6000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (latestNodeStatus) {
      setNodes((prevNodes) =>
        prevNodes.map((n) =>
          n.node_id === latestNodeStatus.node_id
            ? { ...n, ...latestNodeStatus }
            : n
        )
      );
    }
  }, [latestNodeStatus]);

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
    if (filterPanel !== 'ALL' && node.mine_panel !== filterPanel) return false;
    if (filterType === 'ALL') return true;
    if (filterType === 'ONLINE') return node.connectivity_status === 'ONLINE';
    if (filterType === 'OFFLINE') return node.connectivity_status === 'OFFLINE';
    return node.node_type === filterType;
  });

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'calc(100vh - 80px)' }}>
      {/* Top Header & View Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Geotechnical GIS Surface & Mine Panel Viewer
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Multi-Panel Polygon Spatial Monitoring with IDW Interpolation | SIH26025
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {/* Panel Filter */}
          <select
            value={filterPanel}
            onChange={(e) => setFilterPanel(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#f8fafc',
              border: '1px solid var(--border-color)',
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Panels (3)</option>
            <option value="Panel-North-01">Panel-North-01 (Longwall)</option>
            <option value="Panel-West-03">Panel-West-03 (Bord & Pillar)</option>
            <option value="Panel-East-02">Panel-East-02 (Open Cast)</option>
          </select>

          {/* Node Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#f8fafc',
              border: '1px solid var(--border-color)',
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Nodes ({nodes.length})</option>
            <option value="ONLINE">Online Only</option>
            <option value="OFFLINE">Offline / Stale</option>
          </select>

          {/* Deformation Surface Layer Toggle */}
          <button
            onClick={() => setShowDeformationSurface(!showDeformationSurface)}
            className={`btn ${showDeformationSurface ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            title="Toggle IDW Interpolated Surface"
          >
            <Eye size={13} />
            {showDeformationSurface ? 'IDW Surface: ON' : 'IDW Surface: OFF'}
          </button>

          {/* Schematic Mode Toggle */}
          <button
            onClick={() => setIsSchematicMode(!isSchematicMode)}
            className={`btn ${isSchematicMode ? 'btn-primary' : 'btn-secondary'} btn-sm`}
          >
            <Layers size={13} />
            {isSchematicMode ? 'Switch to GIS Map' : 'Local Schematic (Offline)'}
          </button>
        </div>
      </div>

      {/* Explicit IDW Surface Disclosure Alert Banner */}
      {showDeformationSurface && (
        <div style={{
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid #0284c7',
          borderRadius: '6px',
          padding: '0.5rem 0.85rem',
          fontSize: '0.75rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          color: '#cbd5e1'
        }}>
          <Info size={16} color="#38bdf8" style={{ flexShrink: 0 }} />
          <div>
            <strong style={{ color: '#38bdf8' }}>IDW Surface Interpolation Disclosure:</strong> Radial inverse distance weighting ($p=2$, max valid influence radius $350\text{m}$).
            Areas outside the 350m radius of active sensors are unmeasured void space and must <span style={{ color: '#f87171' }}>never be interpreted as physically stable or safe</span>.
          </div>
        </div>
      )}

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
                <span>DEMONSTRATION PIT SCHEMATIC GRID (PANELS OVERLAY)</span>
                <span style={{ color: '#38bdf8' }}>OFFLINE LOCAL CANVAS</span>
              </div>

              {/* Render Nodes & Panels relative to coordinates in SVG */}
              <svg style={{ width: '100%', height: 'calc(100% - 40px)' }} viewBox="0 0 800 500">
                {/* Pit Benches Schematic Contours */}
                <ellipse cx="400" cy="250" rx="360" ry="210" fill="none" stroke="#1e293b" strokeWidth="2" strokeDasharray="4" />
                <ellipse cx="400" cy="250" rx="270" ry="155" fill="none" stroke="#1e293b" strokeWidth="2" strokeDasharray="4" />
                <ellipse cx="400" cy="250" rx="170" ry="95" fill="none" stroke="#334155" strokeWidth="2" />
                <text x="360" y="255" fill="#475569" fontSize="12" fontWeight="600">PIT BOTTOM</text>

                {/* Panel schematic boundary blocks */}
                <rect x="360" y="70" width="220" height="90" fill="rgba(56, 189, 248, 0.08)" stroke="#38bdf8" strokeWidth="1" strokeDasharray="3" rx="4" />
                <text x="370" y="90" fill="#38bdf8" fontSize="10" fontWeight="600">PANEL-NORTH-01 (Longwall)</text>

                <rect x="140" y="260" width="180" height="100" fill="rgba(168, 85, 247, 0.08)" stroke="#a855f7" strokeWidth="1" strokeDasharray="3" rx="4" />
                <text x="150" y="280" fill="#a855f7" fontSize="10" fontWeight="600">PANEL-WEST-03 (Bord & Pillar)</text>

                <rect x="520" y="270" width="180" height="90" fill="rgba(245, 158, 11, 0.08)" stroke="#f59e0b" strokeWidth="1" strokeDasharray="3" rx="4" />
                <text x="530" y="290" fill="#f59e0b" fontSize="10" fontWeight="600">PANEL-EAST-02 (Waste Dump)</text>

                {filteredNodes.map((n, i) => {
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
                        <circle cx={cx} cy={cy} r="18" fill="none" stroke="#38bdf8" strokeWidth="2" opacity="0.4" />
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
                        {n.mine_panel || 'No Panel'} • {n.connectivity_status}
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

              {/* Mine Panels Polygons */}
              {MINE_PANELS.map((panel) => {
                const isMatchingFilter = filterPanel === 'ALL' || filterPanel === panel.id;
                return (
                  <Polygon
                    key={panel.id}
                    positions={panel.coordinates}
                    pathOptions={{
                      color: panel.color,
                      fillColor: panel.color,
                      fillOpacity: isMatchingFilter ? 0.15 : 0.03,
                      weight: isMatchingFilter ? 2 : 1,
                      dashArray: '4, 4'
                    }}
                  >
                    <Popup>
                      <div style={{ minWidth: '180px' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: panel.color }}>{panel.name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '0.3rem' }}>
                          Method: {panel.method}<br />
                          Depth: {panel.depth}
                        </div>
                      </div>
                    </Popup>
                  </Polygon>
                );
              })}

              {/* IDW Interpolation Influence Discs */}
              {showDeformationSurface && filteredNodes.map((node) => (
                <Circle
                  key={`idw-${node.node_id}`}
                  center={[node.latitude, node.longitude]}
                  radius={350}
                  pathOptions={{
                    color: node.connectivity_status === 'ONLINE' ? '#0284c7' : '#64748b',
                    fillColor: node.connectivity_status === 'ONLINE' ? '#38bdf8' : '#475569',
                    fillOpacity: 0.06,
                    weight: 1,
                    dashArray: '3, 6'
                  }}
                />
              ))}

              {/* Sensor Nodes Markers */}
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
                      <div style={{ minWidth: '190px' }}>
                        <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>{node.node_id}</div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{node.name}</div>
                        <div style={{ marginTop: '0.4rem', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                          <StatusBadge status={node.connectivity_status} type="connectivity" />
                          <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 600 }}>{node.mine_panel || 'Pit Zone'}</span>
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '0.3rem' }}>
                          Depth: {node.depth_m ? `${node.depth_m}m` : 'Surface'} • Calib: {node.calibration_status || 'nominal'}
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
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', overflowY: 'auto' }}>
          <div style={{ borderBottom: '1px solid #334155', paddingBottom: '0.65rem' }}>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
              Geotechnical Node Inspector
            </h2>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Field calibration & subsidence telemetry
            </div>
          </div>

          {selectedNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>IDENTIFIER & PANEL</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8' }}>{selectedNode.node_id}</div>
                <div style={{ fontSize: '0.78rem', color: '#e2e8f0' }}>{selectedNode.name}</div>
                <div style={{ display: 'inline-block', marginTop: '0.2rem', padding: '0.15rem 0.45rem', backgroundColor: '#0369a1', color: '#f0f9ff', borderRadius: '4px', fontSize: '0.68rem', fontWeight: 600 }}>
                  {selectedNode.mine_panel || 'Unassigned Panel'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>MINING CONTEXT & DEPTH</div>
                <div style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                  Method: <strong>{selectedNode.extraction_method || 'Open Cut'}</strong><br />
                  Depth: <strong>{selectedNode.depth_m ? `${selectedNode.depth_m} m` : 'Surface'}</strong><br />
                  Context: <span style={{ color: '#94a3b8' }}>{selectedNode.geological_context || 'Standard overburden'}</span>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>CALIBRATION & HEALTH</div>
                <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.2rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <StatusBadge status={selectedNode.connectivity_status} type="connectivity" />
                  <span style={{ fontSize: '0.72rem', color: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                    Cal: {selectedNode.calibration_status || 'nominal'}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
                    Batt: {selectedNode.battery_pct ? `${selectedNode.battery_pct.toFixed(0)}%` : 'N/A'}
                  </span>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>COORDINATES</div>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  {selectedNode.latitude.toFixed(5)}°N, {selectedNode.longitude.toFixed(5)}°E ({selectedNode.elevation_m || 0}m)
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>RECENT TELEMETRY SAMPLES</div>
                {nodeTelemetry.length === 0 ? (
                  <div style={{ fontSize: '0.72rem', color: '#64748b', fontStyle: 'italic', marginTop: '0.3rem' }}>
                    No records received yet.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', marginTop: '0.3rem' }}>
                    {nodeTelemetry.slice(0, 4).map((r) => (
                      <div key={r.id} style={{ backgroundColor: '#1e293b', padding: '0.35rem 0.5rem', borderRadius: '4px', fontSize: '0.72rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8' }}>
                          <span>{new Date(r.timestamp).toLocaleTimeString()}</span>
                          <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                            {r.displacement_mm !== null ? `${r.displacement_mm.toFixed(3)} mm` : '0 mm'}
                          </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', fontSize: '0.68rem', marginTop: '0.1rem' }}>
                          <span>Tilt: {r.vector_tilt_deg !== null ? `${r.vector_tilt_deg.toFixed(2)}°` : 'N/A'}</span>
                          <span style={{ color: r.sensor_quality_state === 'valid' ? '#10b981' : '#f59e0b' }}>
                            {r.sensor_quality_state || 'valid'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Link
                to={`/telemetry?node_id=${encodeURIComponent(selectedNode.node_id)}`}
                className="btn btn-primary btn-sm"
                style={{ marginTop: '0.3rem', width: '100%' }}
              >
                Inspect Telemetry & Baseline <ArrowRight size={13} />
              </Link>
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
