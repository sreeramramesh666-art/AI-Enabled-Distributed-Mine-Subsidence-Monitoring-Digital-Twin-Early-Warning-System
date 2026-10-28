import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import {
  Download,
  Calendar,
  Activity,
  AlertTriangle,
  Layers,
  RotateCcw,
  Sparkles,
  Cpu,
  Clock,
  Compass,
  Thermometer,
  Zap,
  CheckCircle,
  RefreshCw
} from 'lucide-react';

export function TelemetryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryNodeId = searchParams.get('node_id') || '';

  const [nodes, setNodes] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState(queryNodeId);
  const [currentNode, setCurrentNode] = useState(null);
  const [timeWindow, setTimeWindow] = useState(24);
  const [dataPoints, setDataPoints] = useState([]);
  const [rawRecords, setRawRecords] = useState([]);
  const [baseline, setBaseline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [recalcNotice, setRecalcNotice] = useState('');
  const [activeChannel, setActiveChannel] = useState('displacement');

  // Load registered nodes
  useEffect(() => {
    api.getNodes().then((data) => {
      const items = data.items || [];
      setNodes(items);
      if (items.length > 0) {
        if (queryNodeId && items.some((n) => n.node_id === queryNodeId)) {
          setSelectedNodeId(queryNodeId);
        } else {
          setSelectedNodeId(items[0].node_id);
        }
      }
    }).catch(console.error);
  }, [queryNodeId]);

  // Keep search params in sync with selection
  const handleSelectNode = (nodeId) => {
    setSelectedNodeId(nodeId);
    setSearchParams({ node_id: nodeId });
  };

  useEffect(() => {
    if (selectedNodeId) {
      const found = nodes.find((n) => n.node_id === selectedNodeId);
      setCurrentNode(found || null);
      loadNodeData();
    }
  }, [selectedNodeId, timeWindow, nodes]);

  const loadNodeData = async () => {
    if (!selectedNodeId) return;
    setLoading(true);
    try {
      const [trendRes, rawRes, baselineRes] = await Promise.all([
        api.getTrends(selectedNodeId, timeWindow).catch(() => ({ series: [] })),
        api.getNodeTelemetry(selectedNodeId, { limit: 25 }).catch(() => []),
        api.getNodeBaseline(selectedNodeId).catch(() => null),
      ]);

      const formatted = (trendRes.series || []).map((pt) => ({
        ...pt,
        formattedTime: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }));

      setDataPoints(formatted);
      setRawRecords(rawRes || []);
      setBaseline(baselineRes);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculateBaseline = async () => {
    if (!selectedNodeId) return;
    setRecalculating(true);
    setRecalcNotice('');
    try {
      const updated = await api.recalculateBaseline(selectedNodeId, 72.0);
      setBaseline(updated);
      setRecalcNotice('Baseline statistics successfully recalculated over 72-hour historical window.');
      setTimeout(() => setRecalcNotice(''), 4000);
    } catch (e) {
      setRecalcNotice(`Recalculation error: ${e.message}`);
    } finally {
      setRecalculating(false);
    }
  };

  const handleExportCsv = () => {
    if (!selectedNodeId) return;
    window.open(`/api/v1/reports/export?format=csv&node_id=${encodeURIComponent(selectedNodeId)}`, '_blank');
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Node Details & Telemetry History
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Multi-Channel Kinematic Verification, Baseline Geotechnical Calibration & Observation Logs
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Node Selector */}
          <select
            value={selectedNodeId}
            onChange={(e) => handleSelectNode(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.45rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.85rem'
            }}
          >
            {nodes.map((n) => (
              <option key={n.node_id} value={n.node_id}>
                {n.node_id} ({n.name.slice(0, 24)})
              </option>
            ))}
          </select>

          {/* Time Window Buttons */}
          <div style={{ display: 'flex', backgroundColor: '#1e293b', borderRadius: '6px', padding: '2px', border: '1px solid var(--border-color)' }}>
            {[1, 6, 24, 72].map((hrs) => (
              <button
                key={hrs}
                onClick={() => setTimeWindow(hrs)}
                style={{
                  background: timeWindow === hrs ? '#0284c7' : 'none',
                  color: timeWindow === hrs ? '#ffffff' : '#94a3b8',
                  border: 'none',
                  padding: '0.3rem 0.65rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                {hrs === 72 ? '3d' : `${hrs}h`}
              </button>
            ))}
          </div>

          <button onClick={loadNodeData} className="btn btn-secondary btn-sm" title="Refresh Telemetry">
            <RefreshCw size={13} /> Refresh
          </button>

          <button onClick={handleExportCsv} className="btn btn-secondary btn-sm">
            <Download size={13} /> Export CSV
          </button>
        </div>
      </div>

      {/* Node Hardware & Baseline Calibration Summary Card */}
      {currentNode && (
        <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', backgroundColor: '#0f172a', border: '1px solid #1e293b' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>NODE IDENTIFIER</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8' }}>{currentNode.node_id}</div>
            <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{currentNode.name}</div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>STATUS & POWER</div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.2rem', alignItems: 'center' }}>
              <StatusBadge status={currentNode.connectivity_status} type="connectivity" />
              <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                Battery: {currentNode.battery_pct !== null && currentNode.battery_pct !== undefined ? `${currentNode.battery_pct.toFixed(0)}%` : 'N/A'}
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.2rem' }}>
              Type: {currentNode.node_type} • Fw: {currentNode.firmware_version || 'v1.0.0'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>GEOTECHNICAL BASELINE REFERENCE</div>
            <div style={{ fontSize: '0.85rem', color: '#f8fafc', fontWeight: 600, marginTop: '0.1rem' }}>
              Disp Ref: {baseline?.reference_displacement_mm !== undefined && baseline.reference_displacement_mm !== null ? `${baseline.reference_displacement_mm.toFixed(3)} mm` : '0.000 mm'}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Tilt &sigma;: {baseline?.tilt_x_std_deg !== undefined ? `${baseline.tilt_x_std_deg.toFixed(3)}°` : '0.000°'}
            </div>
            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
              Window: {baseline?.baseline_period_hours || 72}h
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <button
              onClick={handleRecalculateBaseline}
              disabled={recalculating}
              className="btn btn-secondary btn-sm"
              style={{ width: 'fit-content' }}
            >
              <RotateCcw size={13} className={recalculating ? 'animate-spin' : ''} />
              {recalculating ? 'Recalculating...' : 'Recalculate Baseline'}
            </button>
            {recalcNotice && (
              <span style={{ fontSize: '0.75rem', color: '#4ade80', marginTop: '0.35rem' }}>
                {recalcNotice}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Channel Switcher Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem', flexWrap: 'wrap' }}>
        {[
          { key: 'displacement', label: 'Cumulative Displacement (mm)', color: '#38bdf8' },
          { key: 'velocity', label: 'Rate / Velocity (mm/hr)', color: '#f59e0b' },
          { key: 'acceleration', label: 'Acceleration (mm/hr²)', color: '#ec4899' },
          { key: 'tilt', label: 'Resultant Vector Tilt (°)', color: '#a855f7' },
          { key: 'vibration', label: 'Vibration RMS (m/s²)', color: '#ef4444' },
          { key: 'temperature', label: 'Temperature (°C)', color: '#10b981' },
        ].map((ch) => (
          <button
            key={ch.key}
            onClick={() => setActiveChannel(ch.key)}
            style={{
              background: activeChannel === ch.key ? 'rgba(56, 189, 248, 0.15)' : 'none',
              color: activeChannel === ch.key ? ch.color : '#94a3b8',
              border: activeChannel === ch.key ? `1px solid ${ch.color}` : '1px solid transparent',
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {ch.label}
          </button>
        ))}
      </div>

      {/* Chart Canvas Card */}
      <div className="card" style={{ height: '440px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
            {selectedNodeId} — Kinematic Time-Series ({timeWindow}h Historical Window)
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            [Integrity Rule]: connectNulls=false prevents false linear interpolation across sensor dropouts
          </div>
        </div>

        {loading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
            Loading telemetry observations...
          </div>
        ) : dataPoints.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.875rem' }}>
            No measurements recorded for node {selectedNodeId} in the selected time window.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dataPoints} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="formattedTime" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '6px', fontSize: '12px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Legend verticalAlign="top" height={36} />

              {activeChannel === 'displacement' && (
                <Line
                  type="monotone"
                  dataKey="displacement_mm"
                  name="Displacement (mm)"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}

              {activeChannel === 'velocity' && (
                <Line
                  type="monotone"
                  dataKey="velocity_mm_hr"
                  name="Velocity (mm/hr)"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}

              {activeChannel === 'acceleration' && (
                <Line
                  type="monotone"
                  dataKey="acceleration_mm_hr2"
                  name="Acceleration (mm/hr²)"
                  stroke="#ec4899"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}

              {activeChannel === 'tilt' && (
                <Line
                  type="monotone"
                  dataKey="vector_tilt_deg"
                  name="Vector Tilt (°)"
                  stroke="#a855f7"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}

              {activeChannel === 'vibration' && (
                <Line
                  type="monotone"
                  dataKey="vibration_rms_ms2"
                  name="Vibration RMS (m/s²)"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}

              {activeChannel === 'temperature' && (
                <Line
                  type="monotone"
                  dataKey="temperature_c"
                  name="Temperature (°C)"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Raw Telemetry History Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '0.85rem 1rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
              Recent Telemetry Observation Log — {selectedNodeId}
            </h2>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Immutable kinematic frames received from edge gateway or synthetic simulator
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Showing latest {rawRecords.length} records
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Seq / Event ID</th>
              <th>Displacement</th>
              <th>Velocity</th>
              <th>Accel</th>
              <th>Vector Tilt</th>
              <th>Vibration</th>
              <th>Temp</th>
              <th>Data Source</th>
            </tr>
          </thead>
          <tbody>
            {rawRecords.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                  No telemetry observations recorded for this node yet.
                </td>
              </tr>
            ) : (
              rawRecords.map((r) => (
                <tr key={r.id || r.event_id}>
                  <td style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {r.sequence_number !== null ? `#${r.sequence_number}` : r.event_id.slice(0, 8)}
                  </td>
                  <td style={{ fontWeight: 600, color: r.displacement_mm > 15 ? '#f87171' : '#38bdf8' }}>
                    {r.displacement_mm !== null ? `${r.displacement_mm.toFixed(3)} mm` : 'null'}
                  </td>
                  <td style={{ color: '#f59e0b' }}>
                    {r.velocity_mm_hr !== null ? `${r.velocity_mm_hr.toFixed(3)} mm/hr` : 'null'}
                  </td>
                  <td style={{ color: '#ec4899', fontSize: '0.75rem' }}>
                    {r.acceleration_mm_hr2 !== null ? `${r.acceleration_mm_hr2.toFixed(3)}` : 'null'}
                  </td>
                  <td style={{ color: '#a855f7' }}>
                    {r.vector_tilt_deg !== null ? `${r.vector_tilt_deg.toFixed(2)}°` : 'null'}
                  </td>
                  <td style={{ color: '#ef4444' }}>
                    {r.vibration_rms_ms2 !== null ? `${r.vibration_rms_ms2.toFixed(2)} m/s²` : 'null'}
                  </td>
                  <td style={{ color: '#10b981', fontSize: '0.75rem' }}>
                    {r.temperature_c !== null ? `${r.temperature_c.toFixed(1)} °C` : 'null'}
                  </td>
                  <td>
                    <StatusBadge status={r.data_source} type="source" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
