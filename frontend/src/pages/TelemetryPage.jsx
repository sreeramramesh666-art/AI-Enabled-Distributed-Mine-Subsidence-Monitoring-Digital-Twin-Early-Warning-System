import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
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
import { Download, Calendar, Activity, AlertTriangle, Layers } from 'lucide-react';

export function TelemetryPage() {
  const [nodes, setNodes] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [timeWindow, setTimeWindow] = useState(24);
  const [dataPoints, setDataPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeChannel, setActiveChannel] = useState('displacement');

  useEffect(() => {
    api.getNodes().then((data) => {
      const items = data.items || [];
      setNodes(items);
      if (items.length > 0) {
        setSelectedNodeId(items[0].node_id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedNodeId) {
      loadTelemetry();
    }
  }, [selectedNodeId, timeWindow]);

  const loadTelemetry = async () => {
    setLoading(true);
    try {
      const res = await api.getTrends(selectedNodeId, timeWindow);
      // Format timestamp for chart x-axis
      const formatted = (res.series || []).map((pt) => ({
        ...pt,
        formattedTime: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }));
      setDataPoints(formatted);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCsv = () => {
    window.open(`/api/v1/reports/export?format=csv&node_id=${encodeURIComponent(selectedNodeId)}`, '_blank');
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Geotechnical Telemetry Explorer
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Multi-Channel Time-Series Kinematics & Environmental Verification
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {/* Node Selector */}
          <select
            value={selectedNodeId}
            onChange={(e) => setSelectedNodeId(e.target.value)}
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
                {n.node_id} ({n.name.slice(0, 22)})
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

          <button onClick={handleExportCsv} className="btn btn-secondary btn-sm">
            <Download size={14} /> Export CSV
          </button>
        </div>
      </div>

      {/* Channel Switcher Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #1e293b', paddingBottom: '0.5rem' }}>
        {[
          { key: 'displacement', label: 'Displacement (mm)', color: '#38bdf8' },
          { key: 'velocity', label: 'Rate / Velocity (mm/hr)', color: '#f59e0b' },
          { key: 'tilt', label: 'Vector Tilt (°)', color: '#a855f7' },
          { key: 'vibration', label: 'Vibration RMS (m/s²)', color: '#ef4444' },
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
      <div className="card" style={{ height: '480px', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc' }}>
            {selectedNodeId} — Time-Series History ({timeWindow}h Window)
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            [Integrity Rule]: connectNulls=false prevents false interpolation across missing data intervals
          </div>
        </div>

        {loading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
            Loading telemetry observations...
          </div>
        ) : dataPoints.length === 0 ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.875rem' }}>
            No measurements recorded for this node in the selected time window.
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
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
