import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import {
  TrendingUp,
  Brain,
  ShieldAlert,
  Cpu,
  RefreshCw,
  Info,
  CheckCircle2,
  AlertCircle,
  MapPin,
  Layers
} from 'lucide-react';

export function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [healthList, setHealthList] = useState([]);
  const [mlStatus, setMlStatus] = useState(null);
  const [spatialCorrob, setSpatialCorrob] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainMessage, setTrainMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, health, ml, spatial] = await Promise.all([
        api.getAnalyticsSummary().catch(() => null),
        api.getNodeHealth().catch(() => []),
        api.getMLStatus().catch(() => null),
        api.getSpatialCorroboration().catch(() => null),
      ]);
      setSummary(sum);
      setHealthList(health || []);
      setMlStatus(ml);
      setSpatialCorrob(spatial);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleTrainML = async () => {
    setTraining(true);
    setTrainMessage('');
    try {
      const res = await api.trainML();
      if (res.success) {
        setTrainMessage(`Successfully trained Isolation Forest on ${res.sample_count} baseline observations.`);
      } else {
        setTrainMessage(`Model training requires at least 30 baseline samples (currently ${res.sample_count}). Run the simulator to generate baseline observations.`);
      }
      setMlStatus(res.status);
    } catch (e) {
      setTrainMessage(`Error: ${e.message}`);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Title */}
      <div>
        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
          Geotechnical Analytics & Machine Learning Support
        </h1>
        <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Transparent Multi-Factor Risk Assessment, Health Diagnostics & Isolation Forest Outlier Analysis
        </p>
      </div>

      {/* Multi-Factor Risk Breakdown Card */}
      <div className="card">
        <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', marginBottom: '0.5rem' }}>
          Deterministic Multi-Factor Geotechnical Risk Model
        </h2>
        <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>
          Decouples physical ground movement hazard from edge telemetry communication uncertainty.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
          <div style={{ backgroundColor: '#1e293b', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>CUMULATIVE DISPLACEMENT</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8', marginTop: '0.2rem' }}>
              Extensometer Datum
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem' }}>
              Threshold: Warning &ge; 15.0 mm | Critical &ge; 30.0 mm
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>DEFORMATION VELOCITY & ACCELERATION</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f59e0b', marginTop: '0.2rem' }}>
              Tertiary Creep Indicator
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem' }}>
              Warning &ge; 2.0 mm/hr | Accel &ge; 0.5 mm/hr²
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>VECTOR ROTATIONAL TILT</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#a855f7', marginTop: '0.2rem' }}>
              Dual-Axis Pitch/Roll
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem' }}>
              Warning &ge; 2.0° | Critical &ge; 5.0°
            </div>
          </div>

          <div style={{ backgroundColor: '#1e293b', padding: '0.85rem', borderRadius: '6px' }}>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>DATA QUALITY & HEARTBEAT</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981', marginTop: '0.2rem' }}>
              Fidelity Metric
            </div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.3rem' }}>
              Stale timeout &gt; 120s marks DATA_UNRELIABLE
            </div>
          </div>
        </div>
      </div>

      {/* Machine Learning Isolation Forest Status */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Brain size={18} style={{ color: '#38bdf8' }} />
              <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
                Unsupervised Multivariate Anomaly Detection (Isolation Forest)
              </h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Detects joint multi-sensor divergence across displacement, vector tilt, rate, vibration, and temperature.
            </p>
          </div>

          <button
            onClick={handleTrainML}
            disabled={training}
            className="btn btn-secondary btn-sm"
          >
            <RefreshCw size={13} className={training ? 'animate-spin' : ''} />
            {training ? 'Training Model...' : 'Train / Retrain Model'}
          </button>
        </div>

        {trainMessage && (
          <div style={{ backgroundColor: 'rgba(56, 189, 248, 0.1)', border: '1px solid #0284c7', padding: '0.5rem 0.75rem', borderRadius: '4px', color: '#7dd3fc', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
            {trainMessage}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.8rem' }}>
          <div>
            <span style={{ color: '#64748b' }}>Model State: </span>
            <strong style={{ color: mlStatus?.trained ? '#4ade80' : '#f59e0b' }}>
              {mlStatus?.trained ? 'Trained & Operational' : 'Untrained (Baseline Rules Active)'}
            </strong>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Baseline Sample Count: </span>
            <strong style={{ color: '#f8fafc' }}>{mlStatus?.sample_count || 0} observations</strong>
          </div>
          <div>
            <span style={{ color: '#64748b' }}>Features Analyzed: </span>
            <strong style={{ color: '#f8fafc' }}>{mlStatus?.features?.length || 6} channels</strong>
          </div>
        </div>

        <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', backgroundColor: '#0b0f19', borderRadius: '4px', borderLeft: '3px solid #f59e0b', fontSize: '0.75rem', color: '#cbd5e1' }}>
          <strong>Notice:</strong> {mlStatus?.note || 'Isolation Forest identifies multi-sensor statistical anomalies. It does NOT produce an empirical collapse probability.'}
        </div>
      </div>

      {/* Spatial Multi-Node Subsidence Corroboration */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MapPin size={18} style={{ color: '#ec4899' }} />
              <h2 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
                Spatial Multi-Node Movement Corroboration
              </h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.2rem' }}>
              Corroborates concurrent displacement across proximate nodes within a {spatialCorrob?.radius_meters || 500}m radius to distinguish true macro ground subsidence from isolated transducer anomalies.
            </p>
          </div>

          <button onClick={loadData} className="btn btn-secondary btn-sm" title="Refresh Corroboration Analysis">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {spatialCorrob?.clusters && spatialCorrob.clusters.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {spatialCorrob.clusters.map((c) => (
              <div
                key={c.cluster_id}
                style={{
                  backgroundColor: c.is_multi_node_hazard ? 'rgba(239, 68, 68, 0.1)' : '#1e293b',
                  border: c.is_multi_node_hazard ? '1px solid #ef4444' : '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.85rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.9rem' }}>
                      Cluster {c.cluster_id} ({c.node_count} Proximate Nodes)
                    </span>
                    {c.is_multi_node_hazard && (
                      <span className="badge badge-critical" style={{ fontSize: '0.7rem' }}>
                        Macro Subsidence Corroborated
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    Avg Disp: <strong style={{ color: '#38bdf8' }}>{c.average_displacement_mm !== null ? `${c.average_displacement_mm.toFixed(2)} mm` : 'N/A'}</strong> •
                    Avg Rate: <strong style={{ color: '#f59e0b' }}>{c.average_velocity_mm_hr !== null ? `${c.average_velocity_mm_hr.toFixed(2)} mm/hr` : 'N/A'}</strong>
                  </div>
                </div>

                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.4rem' }}>
                  Nodes in Cluster: {c.node_ids.map((id) => (
                    <span key={id} style={{ display: 'inline-block', backgroundColor: '#0f172a', padding: '0.15rem 0.45rem', borderRadius: '4px', margin: '0.15rem', color: '#38bdf8', fontWeight: 600 }}>
                      {id}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '1.25rem', backgroundColor: '#0b0f19', borderRadius: '6px', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
            No multi-node spatial movement clusters detected. All sensor nodes are operating in isolated equilibrium within 500m radius.
          </div>
        )}
      </div>

      {/* Node Health Matrix */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '0.85rem 1rem', borderBottom: '1px solid #1e293b' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
            Node Health, Battery & Packet Loss Diagnostics
          </h2>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Name</th>
              <th>Connectivity</th>
              <th>Battery State</th>
              <th>Est. Packet Loss</th>
              <th>Diagnostic Quality Status</th>
            </tr>
          </thead>
          <tbody>
            {healthList.map((h) => (
              <tr key={h.node_id}>
                <td style={{ fontWeight: 700, color: '#38bdf8' }}>{h.node_id}</td>
                <td>{h.name}</td>
                <td>
                  <StatusBadge status={h.connectivity_status} type="connectivity" />
                </td>
                <td style={{ fontSize: '0.8rem', color: h.battery_pct < 20 ? '#ef4444' : '#cbd5e1' }}>
                  {h.battery_pct !== null ? `${h.battery_pct.toFixed(0)}%` : 'N/A'}
                </td>
                <td style={{ fontSize: '0.8rem', color: h.packet_loss_estimate_pct > 10 ? '#f59e0b' : '#cbd5e1' }}>
                  {h.packet_loss_estimate_pct.toFixed(1)}%
                </td>
                <td>
                  <span className="badge" style={{ backgroundColor: '#1e293b', color: h.quality_status === 'NOMINAL' ? '#4ade80' : '#f59e0b' }}>
                    {h.quality_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

