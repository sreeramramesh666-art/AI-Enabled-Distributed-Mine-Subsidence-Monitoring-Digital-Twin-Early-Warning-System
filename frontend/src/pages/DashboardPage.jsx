import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Wifi,
  Radio,
  Sliders,
  TrendingDown,
  Layers,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { Link } from 'react-router-dom';

export function DashboardPage({ latestTelemetry, latestAlert }) {
  const [summary, setSummary] = useState(null);
  const [simStatus, setSimStatus] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadData = async () => {
    try {
      const [sumData, simData, alertsData] = await Promise.all([
        api.getAnalyticsSummary(),
        api.getSimulatorStatus(),
        api.getAlerts({ limit: 5 }),
      ]);
      setSummary(sumData);
      setSimStatus(simData);
      setRecentAlerts(alertsData.items || []);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Update on WebSocket alert
  useEffect(() => {
    if (latestAlert) {
      setRecentAlerts((prev) => [latestAlert, ...prev.slice(0, 4)]);
      loadData();
    }
  }, [latestAlert]);

  const handleToggleSimulator = async () => {
    try {
      if (simStatus?.is_running) {
        await api.stopSimulator();
      } else {
        await api.startSimulator({ scenario: 'accelerating_subsidence', interval_sec: 2.0 });
      }
      loadData();
    } catch (err) {
      alert(`Simulator error: ${err.message}`);
    }
  };

  if (loading && !summary) {
    return (
      <div className="page-wrapper" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <div style={{ color: '#94a3b8' }}>Connecting to MineGuard-AI backend services...</div>
      </div>
    );
  }

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Page Title & Simulator Action Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc' }}>
            Mine Geohazard Command Center
          </h1>
          <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.2rem' }}>
            SIH26025 Real-Time Subsidence & Geotechnical Stability Monitoring
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginRight: '0.5rem' }}>
            Updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Live'}
          </div>
          <button
            onClick={loadData}
            className="btn btn-secondary btn-sm"
            title="Refresh metrics immediately"
          >
            <RefreshCw size={13} /> Refresh
          </button>
          <button
            onClick={handleToggleSimulator}
            className={`btn btn-sm ${simStatus?.is_running ? 'btn-danger' : 'btn-primary'}`}
          >
            <Sliders size={13} />
            {simStatus?.is_running ? 'Halt Simulator' : 'Start Simulation'}
          </button>
          <Link to="/reports" className="btn btn-secondary btn-sm">
            Generate Report
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid #991b1b', padding: '0.75rem 1rem', borderRadius: '6px', color: '#fca5a5', fontSize: '0.875rem' }}>
          <strong>Communication Notice:</strong> {error}
        </div>
      )}

      {/* KPI Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        {/* Total Nodes */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>
            <span>MONITORED NODES</span>
            <Layers size={16} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.4rem' }}>
            {summary?.total_nodes || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
            {summary?.online_nodes || 0} online • {summary?.stale_nodes || 0} stale • {summary?.offline_nodes || 0} offline
          </div>
        </div>

        {/* Stability Risk Level */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>
            <span>MINE RISK STATUS</span>
            <Activity size={16} />
          </div>
          <div style={{ marginTop: '0.4rem' }}>
            <StatusBadge status={summary?.overall_risk_category || 'NORMAL'} />
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.45rem' }}>
            Multi-factor geotechnical score
          </div>
        </div>

        {/* Active Critical Alerts */}
        <div className="card" style={{ borderColor: summary?.active_critical_alerts > 0 ? '#991b1b' : 'var(--border-color)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>
            <span>CRITICAL HAZARDS</span>
            <AlertTriangle size={16} style={{ color: '#ef4444' }} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: summary?.active_critical_alerts > 0 ? '#f87171' : '#f8fafc', marginTop: '0.4rem' }}>
            {summary?.active_critical_alerts || 0}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
            {summary?.active_warning_alerts || 0} warnings pending
          </div>
        </div>

        {/* Data Completeness */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>
            <span>DATA FIDELITY</span>
            <Wifi size={16} />
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.4rem' }}>
            {summary?.data_completeness_pct || 0}%
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
            Edge packet loss & freshness
          </div>
        </div>
      </div>

      {/* Real-Time Live Telemetry Stream Ticker */}
      <div className="card" style={{ backgroundColor: '#0b0f19', border: '1px solid #1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '0.75rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8' }}>
            <Radio size={15} className="animate-pulse" />
            <span>LATEST LIVE OBSERVATION STREAM</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            SI Units: mm, mm/hr, °, m/s²
          </div>
        </div>

        {latestTelemetry ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', fontSize: '0.875rem' }}>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Node</div>
              <div style={{ fontWeight: 600, color: '#f8fafc' }}>{latestTelemetry.node_id}</div>
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Displacement</div>
              <div style={{ fontWeight: 600, color: latestTelemetry.displacement_mm > 15 ? '#f87171' : '#38bdf8' }}>
                {latestTelemetry.displacement_mm !== null ? `${latestTelemetry.displacement_mm.toFixed(3)} mm` : 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Velocity</div>
              <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                {latestTelemetry.velocity_mm_hr !== null ? `${latestTelemetry.velocity_mm_hr.toFixed(3)} mm/hr` : 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Vector Tilt</div>
              <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                {latestTelemetry.vector_tilt_deg !== null ? `${latestTelemetry.vector_tilt_deg.toFixed(2)}°` : 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Vibration RMS</div>
              <div style={{ fontWeight: 600, color: '#e2e8f0' }}>
                {latestTelemetry.vibration_rms_ms2 !== null ? `${latestTelemetry.vibration_rms_ms2.toFixed(2)} m/s²` : 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ color: '#64748b', fontSize: '0.75rem' }}>Source</div>
              <div style={{ marginTop: '0.2rem' }}>
                <StatusBadge status={latestTelemetry.data_source} type="source" />
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: '#64748b', fontSize: '0.85rem', fontStyle: 'italic' }}>
            Awaiting incoming telemetry from wireless gateway or active simulator...
          </div>
        )}
      </div>

      {/* Recent Alerts Feed */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
            Operational Geohazard Alerts
          </h2>
          <Link to="/alerts" style={{ fontSize: '0.8rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            View all alerts <ArrowRight size={13} />
          </Link>
        </div>

        {recentAlerts.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.875rem' }}>
            No active hazards recorded. All nodes reporting within normal baseline tolerances.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Node ID</th>
                <th>Hazard Category</th>
                <th>Description</th>
                <th>Time (UTC)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentAlerts.map((a) => (
                <tr key={a.alert_id || a.id}>
                  <td>
                    <StatusBadge status={a.severity} />
                  </td>
                  <td style={{ fontWeight: 600, color: '#f8fafc' }}>{a.node_id}</td>
                  <td>{a.category}</td>
                  <td style={{ maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.title}
                  </td>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {a.created_at ? new Date(a.created_at).toLocaleTimeString() : 'Recent'}
                  </td>
                  <td>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: a.status === 'ACTIVE' ? '#f87171' : '#4ade80' }}>
                      {a.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

