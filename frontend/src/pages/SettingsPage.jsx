import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Settings, Save, AlertCircle, Wifi, Database, Check } from 'lucide-react';

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

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    api.getSettings().then(setSettingsData).catch(console.error);
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    try {
      const updated = await api.updateSettings({
        TILT_WARNING_DEG: parseFloat(settingsData.tilt_warning_deg),
        TILT_CRITICAL_DEG: parseFloat(settingsData.tilt_critical_deg),
        DISPLACEMENT_WARNING_MM: parseFloat(settingsData.displacement_warning_mm),
        DISPLACEMENT_CRITICAL_MM: parseFloat(settingsData.displacement_critical_mm),
        RATE_WARNING_MM_HR: parseFloat(settingsData.rate_warning_mm_hr),
        RATE_CRITICAL_MM_HR: parseFloat(settingsData.rate_critical_mm_hr),
        ACCEL_WARNING_MM_HR2: parseFloat(settingsData.accel_warning_mm_hr2),
        VIBRATION_WARNING_MS2: parseFloat(settingsData.vibration_warning_ms2),
        VIBRATION_CRITICAL_MS2: parseFloat(settingsData.vibration_critical_ms2),
        BATTERY_LOW_PCT: parseFloat(settingsData.battery_low_pct),
        STALE_DATA_TIMEOUT_SEC: parseInt(settingsData.stale_data_timeout_sec, 10),
      });
      setSettingsData(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert(`Save error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
          Geotechnical & Ingestion Settings
        </h1>
        <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Configurable Physical Decision Limits & Edge Gateway Parameters
        </p>
      </div>

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

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button type="submit" disabled={saving} className="btn btn-primary">
            <Save size={15} />
            {saving ? 'Persisting Configuration...' : 'Save Configuration'}
          </button>
          {savedSuccess && (
            <span style={{ color: '#4ade80', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <Check size={16} /> Runtime configuration persisted successfully!
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
