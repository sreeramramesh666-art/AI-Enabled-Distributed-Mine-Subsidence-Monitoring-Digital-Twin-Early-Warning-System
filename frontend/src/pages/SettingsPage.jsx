import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  Settings,
  Save,
  AlertCircle,
  Wifi,
  Database,
  Check,
  Activity,
  ShieldAlert,
  Server,
  RefreshCw,
  FileCheck
} from 'lucide-react';

export function SettingsPage() {
  const [settingsData, setSettingsData] = useState({
    tilt_warning_deg: 2.0,
    tilt_critical_deg: 5.0,
    displacement_warning_mm: 15.0,
    displacement_critical_mm: 30.0,
    rate_warning_mm_hr: 2.0,
    rate_critical_mm_hr: 5.0,
    accel_warning_mm_hr2: 0.5,
    vibration_warning_ms2: 3.0,
    vibration_critical_ms2: 8.0,
    battery_low_pct: 20.0,
    stale_data_timeout_sec: 120,
    mqtt_enabled: false,
    environment: 'development',
  });

  const [health, setHealth] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    loadSettingsAndHealth();
  }, []);

  const loadSettingsAndHealth = async () => {
    setLoadingHealth(true);
    try {
      const [sets, h, audits] = await Promise.all([
        api.getSettings().catch(() => null),
        api.getHealth().catch(() => null),
        api.getAuditEvents({ limit: 10 }).catch(() => ({ items: [] })),
      ]);
      if (sets) setSettingsData(sets);
      if (h) setHealth(h);
      if (audits) setAuditEvents(audits.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHealth(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setValidationError('');

    // Pre-validate threshold hierarchy
    const dispWarn = parseFloat(settingsData.displacement_warning_mm);
    const dispCrit = parseFloat(settingsData.displacement_critical_mm);
    if (dispWarn >= dispCrit) {
      setValidationError('Displacement Warning threshold must be strictly less than Critical threshold.');
      return;
    }

    const rateWarn = parseFloat(settingsData.rate_warning_mm_hr);
    const rateCrit = parseFloat(settingsData.rate_critical_mm_hr);
    if (rateWarn >= rateCrit) {
      setValidationError('Velocity / Rate Warning threshold must be strictly less than Critical threshold.');
      return;
    }

    const tiltWarn = parseFloat(settingsData.tilt_warning_deg);
    const tiltCrit = parseFloat(settingsData.tilt_critical_deg);
    if (tiltWarn >= tiltCrit) {
      setValidationError('Vector Tilt Warning threshold must be strictly less than Critical threshold.');
      return;
    }

    const vibWarn = parseFloat(settingsData.vibration_warning_ms2);
    const vibCrit = parseFloat(settingsData.vibration_critical_ms2);
    if (vibWarn >= vibCrit) {
      setValidationError('Vibration RMS Warning threshold must be strictly less than Critical threshold.');
      return;
    }

    setSaving(true);
    setSavedSuccess(false);
    try {
      const updated = await api.updateSettings({
        TILT_WARNING_DEG: tiltWarn,
        TILT_CRITICAL_DEG: tiltCrit,
        DISPLACEMENT_WARNING_MM: dispWarn,
        DISPLACEMENT_CRITICAL_MM: dispCrit,
        RATE_WARNING_MM_HR: rateWarn,
        RATE_CRITICAL_MM_HR: rateCrit,
        ACCEL_WARNING_MM_HR2: parseFloat(settingsData.accel_warning_mm_hr2),
        VIBRATION_WARNING_MS2: vibWarn,
        VIBRATION_CRITICAL_MS2: vibCrit,
        BATTERY_LOW_PCT: parseFloat(settingsData.battery_low_pct),
        STALE_DATA_TIMEOUT_SEC: parseInt(settingsData.stale_data_timeout_sec, 10),
      });
      setSettingsData(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
      // Reload audit events to reflect the update action
      api.getAuditEvents({ limit: 10 }).then((res) => setAuditEvents(res.items || [])).catch(() => {});
    } catch (err) {
      setValidationError(`Save error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
          Configuration & System Diagnostics
        </h1>
        <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Physical Decision Limits, Backend Health Probes & Immutable Security Audit Log
        </p>
      </div>

      {/* System Health Diagnostics Card */}
      <div className="card" style={{ backgroundColor: '#0b0f19', border: '1px solid #1e293b' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Server size={18} style={{ color: '#38bdf8' }} />
            <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
              Backend Health & Subsystem Probes
            </h2>
          </div>
          <button onClick={loadSettingsAndHealth} className="btn btn-secondary btn-sm" title="Refresh Health Probes">
            <RefreshCw size={13} /> Probe
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '1rem', fontSize: '0.8rem' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
            <div style={{ color: '#64748b', fontSize: '0.75rem' }}>APPLICATION CORE</div>
            <div style={{ fontWeight: 600, color: '#f8fafc', marginTop: '0.2rem' }}>
              {health?.app || 'MineGuard-AI'} v{health?.version || '1.0.0'}
            </div>
            <div style={{ color: '#38bdf8', fontSize: '0.7rem' }}>
              Mode: {health?.environment || 'development'}
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
            <div style={{ color: '#64748b', fontSize: '0.75rem' }}>DATABASE CONNECTIVITY</div>
            <div style={{ fontWeight: 600, color: health?.database === 'connected' ? '#4ade80' : '#f87171', marginTop: '0.2rem' }}>
              {health?.database === 'connected' ? 'SQLite Engine Connected' : 'Disconnected'}
            </div>
            <div style={{ color: '#64748b', fontSize: '0.7rem' }}>
              Transaction isolation active
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
            <div style={{ color: '#64748b', fontSize: '0.75rem' }}>MQTT GATEWAY BROKER</div>
            <div style={{ fontWeight: 600, color: health?.mqtt_status === 'connected' ? '#4ade80' : '#94a3b8', marginTop: '0.2rem' }}>
              {health?.mqtt_status === 'connected' ? 'Broker Online' : 'Disabled (Local REST Active)'}
            </div>
            <div style={{ color: '#64748b', fontSize: '0.7rem' }}>
              Port 1883 / LoRaWAN bridge
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px' }}>
            <div style={{ color: '#64748b', fontSize: '0.75rem' }}>SIMULATOR CLOCK</div>
            <div style={{ fontWeight: 600, color: health?.simulator_running ? '#fbbf24' : '#64748b', marginTop: '0.2rem' }}>
              {health?.simulator_running ? 'Simulation Clock Active' : 'Simulator Standby'}
            </div>
            <div style={{ color: '#64748b', fontSize: '0.7rem' }}>
              Deterministic scenario engine
            </div>
          </div>
        </div>
      </div>

      {/* Geotechnical Calibration Notice */}
      <div style={{
        backgroundColor: 'rgba(234, 179, 8, 0.08)',
        border: '1px solid #ca8a04',
        borderRadius: '6px',
        padding: '0.75rem 1rem',
        fontSize: '0.8rem',
        color: '#fef08a'
      }}>
        <strong>Demonstration Calibration Notice:</strong> Thresholds configured below drive the deterministic rules engine. In operational pit mines, thresholds must be mathematically derived from rock mass rating (RMR), slope geometry, and local geotechnical radar baseline.
      </div>

      {validationError && (
        <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid #991b1b', padding: '0.75rem 1rem', borderRadius: '6px', color: '#fca5a5', fontSize: '0.85rem' }}>
          <strong>Configuration Error:</strong> {validationError}
        </div>
      )}

      {/* Thresholds Form */}
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Displacement & Velocity */}
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
            Subsidence & Kinematics Thresholds
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Displacement Warning (mm)
              </label>
              <input
                type="number"
                step="0.5"
                value={settingsData.displacement_warning_mm}
                onChange={(e) => setSettingsData({ ...settingsData, displacement_warning_mm: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Displacement Critical (mm)
              </label>
              <input
                type="number"
                step="0.5"
                value={settingsData.displacement_critical_mm}
                onChange={(e) => setSettingsData({ ...settingsData, displacement_critical_mm: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Velocity Warning (mm/hr)
              </label>
              <input
                type="number"
                step="0.1"
                value={settingsData.rate_warning_mm_hr}
                onChange={(e) => setSettingsData({ ...settingsData, rate_warning_mm_hr: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Velocity Critical (mm/hr)
              </label>
              <input
                type="number"
                step="0.1"
                value={settingsData.rate_critical_mm_hr}
                onChange={(e) => setSettingsData({ ...settingsData, rate_critical_mm_hr: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Critical Acceleration (mm/hr²)
              </label>
              <input
                type="number"
                step="0.05"
                value={settingsData.accel_warning_mm_hr2}
                onChange={(e) => setSettingsData({ ...settingsData, accel_warning_mm_hr2: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
          </div>
        </div>

        {/* Tilt & Vibration */}
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
            Tilt Inclinometer & Dynamic Vibration Limits
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Vector Tilt Warning (°)
              </label>
              <input
                type="number"
                step="0.1"
                value={settingsData.tilt_warning_deg}
                onChange={(e) => setSettingsData({ ...settingsData, tilt_warning_deg: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Vector Tilt Critical (°)
              </label>
              <input
                type="number"
                step="0.1"
                value={settingsData.tilt_critical_deg}
                onChange={(e) => setSettingsData({ ...settingsData, tilt_critical_deg: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Vibration RMS Warning (m/s²)
              </label>
              <input
                type="number"
                step="0.5"
                value={settingsData.vibration_warning_ms2}
                onChange={(e) => setSettingsData({ ...settingsData, vibration_warning_ms2: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Vibration RMS Critical (m/s²)
              </label>
              <input
                type="number"
                step="0.5"
                value={settingsData.vibration_critical_ms2}
                onChange={(e) => setSettingsData({ ...settingsData, vibration_critical_ms2: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
          </div>
        </div>

        {/* Node Health & Connectivity */}
        <div className="card">
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.75rem' }}>
            Node Health & Heartbeat Timing
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Stale Data Timeout (seconds)
              </label>
              <input
                type="number"
                step="10"
                min="30"
                value={settingsData.stale_data_timeout_sec}
                onChange={(e) => setSettingsData({ ...settingsData, stale_data_timeout_sec: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Battery Low Alert (%)
              </label>
              <input
                type="number"
                step="1"
                min="5"
                max="50"
                value={settingsData.battery_low_pct}
                onChange={(e) => setSettingsData({ ...settingsData, battery_low_pct: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <button type="submit" disabled={saving} className="btn btn-primary">
            <Save size={15} />
            {saving ? 'Persisting Configuration...' : 'Save Configuration'}
          </button>
          {savedSuccess && (
            <span style={{ color: '#4ade80', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <Check size={16} /> Runtime configuration persisted to geodatabase!
            </span>
          )}
        </div>
      </form>

      {/* Immutable System Audit Trail */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '0.85rem 1rem', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
              Security & Operator Audit Trail
            </h2>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Immutable sequence log of safety parameter modifications and alert lifecycle actions
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
            Latest {auditEvents.length} events
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Category</th>
              <th>Actor</th>
              <th>Target ID</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {auditEvents.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                  No operator audit events recorded yet.
                </td>
              </tr>
            ) : (
              auditEvents.map((evt) => (
                <tr key={evt.id}>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {new Date(evt.timestamp).toLocaleString()}
                  </td>
                  <td>
                    <span className="badge" style={{ backgroundColor: '#1e293b', color: '#38bdf8' }}>
                      {evt.category}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600, color: '#f8fafc' }}>{evt.actor}</td>
                  <td style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                    {evt.node_id || evt.alert_id || 'System'}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    {evt.description}
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
