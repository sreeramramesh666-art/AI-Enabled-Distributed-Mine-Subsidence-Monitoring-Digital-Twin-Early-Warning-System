import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import {
  Bell,
  CheckCircle,
  Clock,
  ShieldAlert,
  Search,
  Filter,
  Eye,
  FileCheck2,
  AlertTriangle,
} from 'lucide-react';

export function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  // Modals
  const [inspectAlert, setInspectAlert] = useState(null);
  const [ackAlert, setAckAlert] = useState(null);
  const [resolveAlert, setResolveAlert] = useState(null);

  // Form states
  const [operatorName, setOperatorName] = useState('Safety Officer Singh');
  const [noteText, setNoteText] = useState('');

  useEffect(() => {
    loadAlerts();
  }, [statusFilter, severityFilter]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (severityFilter !== 'ALL') params.severity = severityFilter;
      const data = await api.getAlerts(params);
      setAlerts(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (e) => {
    e.preventDefault();
    if (!ackAlert) return;
    try {
      await api.acknowledgeAlert(ackAlert.alert_id, {
        acknowledged_by: operatorName,
        note: noteText || 'Inspection underway',
      });
      setAckAlert(null);
      setNoteText('');
      loadAlerts();
    } catch (err) {
      alert(`Acknowledgement error: ${err.message}`);
    }
  };

  const handleResolve = async (e) => {
    e.preventDefault();
    if (!resolveAlert) return;
    try {
      await api.resolveAlert(resolveAlert.alert_id, {
        resolved_by: operatorName,
        resolution_notes: noteText || 'Hazard stabilized with rock bolt reinforcement',
      });
      setResolveAlert(null);
      setNoteText('');
      loadAlerts();
    } catch (err) {
      alert(`Resolution error: ${err.message}`);
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Geotechnical Disclaimer Alert */}
      <div style={{
        backgroundColor: 'rgba(185, 28, 28, 0.1)',
        border: '1px solid #991b1b',
        borderRadius: '8px',
        padding: '0.75rem 1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        fontSize: '0.8rem',
        color: '#fca5a5'
      }}>
        <AlertTriangle size={18} style={{ flexShrink: 0, color: '#ef4444' }} />
        <div>
          <strong>Operational Notice:</strong> Prototype automated alerts provide early geohazard awareness for SIH26025. They are NOT certified by statutory bodies (DGMS) as an autonomous safety-critical shutdown system. Evacuation and bench closure decisions require qualified geotechnical surveyor authorization.
        </div>
      </div>

      {/* Header & Filters */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Alerts & Geohazard Lifecycle Centre
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Triaged Geotechnical Findings, Evidence Attribution & Investigation Audit History
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active Only</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="RESOLVED">Resolved</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.4rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
            <option value="WATCH">Watch</option>
            <option value="DATA_UNRELIABLE">Data Unreliable</option>
          </select>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Node ID</th>
              <th>Category</th>
              <th>Finding Title</th>
              <th>Rule / Model</th>
              <th>Status</th>
              <th>Created (UTC)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: '#64748b' }}>
                  No alerts match the selected criteria.
                </td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.alert_id}>
                  <td>
                    <StatusBadge status={alert.severity} />
                  </td>
                  <td style={{ fontWeight: 700, color: '#38bdf8' }}>{alert.node_id}</td>
                  <td>{alert.category}</td>
                  <td style={{ fontWeight: 500, color: '#f8fafc', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {alert.title}
                  </td>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{alert.triggering_rule}</td>
                  <td>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: alert.status === 'ACTIVE' ? '#ef4444' : alert.status === 'ACKNOWLEDGED' ? '#f59e0b' : '#10b981'
                    }}>
                      {alert.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : 'N/A'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                      <button
                        onClick={() => setInspectAlert(alert)}
                        className="btn btn-secondary btn-sm"
                        title="View Evidence & Raw Observations"
                      >
                        <Eye size={13} />
                      </button>

                      {alert.status === 'ACTIVE' && (
                        <button
                          onClick={() => {
                            setAckAlert(alert);
                            setNoteText('');
                          }}
                          className="btn btn-warning btn-sm"
                          title="Acknowledge Alert"
                        >
                          Ack
                        </button>
                      )}

                      {alert.status !== 'RESOLVED' && (
                        <button
                          onClick={() => {
                            setResolveAlert(alert);
                            setNoteText('');
                          }}
                          className="btn btn-primary btn-sm"
                          title="Resolve Alert"
                        >
                          Resolve
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Inspect Alert Modal */}
      {inspectAlert && (
        <Modal
          isOpen={!!inspectAlert}
          onClose={() => setInspectAlert(null)}
          title={`Alert Inspection [${inspectAlert.alert_id.slice(0, 8)}...]`}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <StatusBadge status={inspectAlert.severity} />
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Node: <strong style={{ color: '#f8fafc' }}>{inspectAlert.node_id}</strong>
              </span>
            </div>

            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>{inspectAlert.title}</h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.3rem' }}>{inspectAlert.description}</p>
            </div>

            <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px', fontSize: '0.8rem' }}>
              <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '0.4rem' }}>EVIDENCE & RAW METRICS:</div>
              <pre style={{ color: '#38bdf8', fontFamily: 'monospace', overflowX: 'auto', fontSize: '0.75rem' }}>
                {JSON.stringify(inspectAlert.evidence, null, 2)}
              </pre>
            </div>

            <div style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div>Triggering Decision Rule: <strong style={{ color: '#f8fafc' }}>{inspectAlert.triggering_rule}</strong></div>
              <div>Reported: {new Date(inspectAlert.created_at).toLocaleString()}</div>
              {inspectAlert.acknowledged_by && (
                <div>Acknowledged by: {inspectAlert.acknowledged_by} ({new Date(inspectAlert.acknowledged_at).toLocaleString()}) - Note: "{inspectAlert.acknowledgement_note}"</div>
              )}
              {inspectAlert.resolved_by && (
                <div>Resolved by: {inspectAlert.resolved_by} ({new Date(inspectAlert.resolved_at).toLocaleString()}) - Resolution: "{inspectAlert.resolution_notes}"</div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button onClick={() => setInspectAlert(null)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Acknowledge Alert Modal */}
      {ackAlert && (
        <Modal isOpen={!!ackAlert} onClose={() => setAckAlert(null)} title="Acknowledge Geohazard Alert">
          <form onSubmit={handleAcknowledge} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Safety Officer / Operator Name *
              </label>
              <input
                type="text"
                required
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Investigation Note / Initial Action Taken
              </label>
              <textarea
                rows={3}
                placeholder="e.g. Dispatched geotechnical surveyor to bench sector; laser scanning initiated."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff', fontFamily: 'inherit' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" onClick={() => setAckAlert(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-warning">
                Confirm Acknowledgement
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Resolve Alert Modal */}
      {resolveAlert && (
        <Modal isOpen={!!resolveAlert} onClose={() => setResolveAlert(null)} title="Resolve Geohazard Alert">
          <form onSubmit={handleResolve} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Authorized Geotechnical Officer *
              </label>
              <input
                type="text"
                required
                value={operatorName}
                onChange={(e) => setOperatorName(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Formal Remediation & Resolution Notes *
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Highwall crest unloaded; rock anchor bolts torqued; displacement rate returned to < 0.2 mm/hr baseline."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff', fontFamily: 'inherit' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" onClick={() => setResolveAlert(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Resolve Alert & Close Incident
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
