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
  RotateCcw,
  SearchCode,
  ShieldCheck,
} from 'lucide-react';

export function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [panelFilter, setPanelFilter] = useState('ALL');
  const [loading, setLoading] = useState(true);

  // Modals
  const [inspectAlert, setInspectAlert] = useState(null);
  const [ackAlert, setAckAlert] = useState(null);
  const [resolveAlert, setResolveAlert] = useState(null);
  const [investigateModalAlert, setInvestigateModalAlert] = useState(null);
  const [reopenModalAlert, setReopenModalAlert] = useState(null);

  // Form states
  const [operatorName, setOperatorName] = useState('Safety Officer Singh');
  const [noteText, setNoteText] = useState('');

  useEffect(() => {
    loadAlerts();
  }, [statusFilter, severityFilter, panelFilter]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (severityFilter !== 'ALL') params.severity = severityFilter;
      if (panelFilter !== 'ALL') params.mine_panel = panelFilter;
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

  const handleInvestigate = async (e) => {
    e.preventDefault();
    if (!investigateModalAlert) return;
    try {
      await api.investigateAlert(investigateModalAlert.alert_id, {
        investigated_by: operatorName,
        investigation_notes: noteText || 'Field geotechnical survey dispatched to measure crack displacement.',
      });
      setInvestigateModalAlert(null);
      setNoteText('');
      loadAlerts();
    } catch (err) {
      alert(`Investigation update error: ${err.message}`);
    }
  };

  const handleResolve = async (e) => {
    e.preventDefault();
    if (!resolveAlert) return;
    try {
      await api.resolveAlert(resolveAlert.alert_id, {
        resolved_by: operatorName,
        resolution_notes: noteText || 'Hazard stabilized with rock bolt reinforcement and drainage diversion.',
      });
      setResolveAlert(null);
      setNoteText('');
      loadAlerts();
    } catch (err) {
      alert(`Resolution error: ${err.message}`);
    }
  };

  const handleReopen = async (e) => {
    e.preventDefault();
    if (!reopenModalAlert) return;
    try {
      await api.reopenAlert(reopenModalAlert.alert_id, {
        reopened_by: operatorName,
        reason: noteText || 'Subsequent sensor readings indicate continuing displacement progression.',
      });
      setReopenModalAlert(null);
      setNoteText('');
      loadAlerts();
    } catch (err) {
      alert(`Reopen error: ${err.message}`);
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
            Multi-Panel Geotechnical Findings, Actionable Protocols & Investigation Audit Trail
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Panel Filter */}
          <select
            value={panelFilter}
            onChange={(e) => setPanelFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.4rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Mine Panels</option>
            <option value="Panel-North-01">Panel-North-01</option>
            <option value="Panel-West-03">Panel-West-03</option>
            <option value="Panel-East-02">Panel-East-02</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.4rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.8rem'
            }}
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="UNDER_INVESTIGATION">Under Investigation</option>
            <option value="RESOLVED">Resolved</option>
            <option value="REOPENED">Reopened</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.4rem 0.65rem',
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
              <th>Node / Panel</th>
              <th>Category</th>
              <th>Finding Title</th>
              <th>Recommended Action</th>
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
                  <td>
                    <div style={{ fontWeight: 700, color: '#38bdf8' }}>{alert.node_id}</div>
                    {alert.mine_panel && (
                      <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>{alert.mine_panel}</span>
                    )}
                  </td>
                  <td>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>{alert.category}</span>
                  </td>
                  <td style={{ fontWeight: 500, color: '#f8fafc', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {alert.title}
                  </td>
                  <td style={{ fontSize: '0.72rem', color: '#e2e8f0', maxWidth: '260px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={alert.recommended_action}>
                    {alert.recommended_action || 'Inspect field sensor and surroundings.'}
                  </td>
                  <td>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '0.15rem 0.4rem',
                      borderRadius: '4px',
                      backgroundColor: alert.status === 'ACTIVE' ? 'rgba(239, 68, 68, 0.15)' :
                                      alert.status === 'UNDER_INVESTIGATION' ? 'rgba(56, 189, 248, 0.15)' :
                                      alert.status === 'ACKNOWLEDGED' ? 'rgba(245, 158, 11, 0.15)' :
                                      alert.status === 'REOPENED' ? 'rgba(239, 68, 68, 0.2)' :
                                      'rgba(16, 185, 129, 0.15)',
                      color: alert.status === 'ACTIVE' ? '#ef4444' :
                             alert.status === 'UNDER_INVESTIGATION' ? '#38bdf8' :
                             alert.status === 'ACKNOWLEDGED' ? '#f59e0b' :
                             alert.status === 'REOPENED' ? '#f87171' :
                             '#10b981'
                    }}>
                      {alert.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                    {alert.created_at ? new Date(alert.created_at).toLocaleTimeString() : 'N/A'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      <button
                        onClick={() => setInspectAlert(alert)}
                        className="btn btn-secondary btn-sm"
                        title="View Evidence & Raw Observations"
                      >
                        <Eye size={12} />
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

                      {(alert.status === 'ACTIVE' || alert.status === 'ACKNOWLEDGED' || alert.status === 'REOPENED') && (
                        <button
                          onClick={() => {
                            setInvestigateModalAlert(alert);
                            setNoteText('');
                          }}
                          className="btn btn-secondary btn-sm"
                          style={{ borderColor: '#38bdf8', color: '#38bdf8' }}
                          title="Set Under Investigation"
                        >
                          <SearchCode size={12} /> Inv
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
                          <ShieldCheck size={12} /> Resolve
                        </button>
                      )}

                      {alert.status === 'RESOLVED' && (
                        <button
                          onClick={() => {
                            setReopenModalAlert(alert);
                            setNoteText('');
                          }}
                          className="btn btn-secondary btn-sm"
                          style={{ borderColor: '#ef4444', color: '#ef4444' }}
                          title="Reopen Alert"
                        >
                          <RotateCcw size={12} /> Reopen
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
          title={`Alert Details [${inspectAlert.alert_id.slice(0, 8)}...]`}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <StatusBadge status={inspectAlert.severity} />
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Node: <strong style={{ color: '#38bdf8' }}>{inspectAlert.node_id}</strong>
                {inspectAlert.mine_panel && ` • ${inspectAlert.mine_panel}`}
              </span>
            </div>

            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>{inspectAlert.title}</h4>
              <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '0.3rem' }}>{inspectAlert.description}</p>
            </div>

            {/* Recommended Protocol Box */}
            <div style={{ backgroundColor: 'rgba(2, 132, 199, 0.1)', border: '1px solid #0284c7', padding: '0.75rem', borderRadius: '6px' }}>
              <div style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 700, marginBottom: '0.3rem' }}>RECOMMENDED ACTION PROTOCOL:</div>
              <div style={{ fontSize: '0.82rem', color: '#f0f9ff' }}>{inspectAlert.recommended_action || 'Inspect field sensor and verify physical ground conditions.'}</div>
            </div>

            <div style={{ backgroundColor: '#1e293b', padding: '0.75rem', borderRadius: '6px', fontSize: '0.8rem' }}>
              <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '0.4rem' }}>EVIDENCE & RAW METRICS:</div>
              <pre style={{ color: '#38bdf8', fontFamily: 'monospace', overflowX: 'auto', fontSize: '0.75rem' }}>
                {JSON.stringify(inspectAlert.evidence, null, 2)}
              </pre>
            </div>

            {/* Lifecycle History Timeline */}
            <div style={{ backgroundColor: '#0f172a', padding: '0.75rem', borderRadius: '6px', fontSize: '0.78rem' }}>
              <div style={{ color: '#94a3b8', fontWeight: 600, marginBottom: '0.4rem' }}>LIFECYCLE AUDIT TRAIL:</div>
              {inspectAlert.lifecycle_history && inspectAlert.lifecycle_history.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {inspectAlert.lifecycle_history.map((entry, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', borderLeft: '2px solid #38bdf8', paddingLeft: '0.5rem', color: '#cbd5e1' }}>
                      <div>
                        <strong style={{ color: '#f8fafc' }}>{entry.action}</strong>
                        {entry.actor && ` by ${entry.actor}`}
                        {entry.note && ` - "${entry.note}"`}
                        {entry.notes && ` - "${entry.notes}"`}
                        {entry.resolution_notes && ` - "${entry.resolution_notes}"`}
                        {entry.reason && ` - "${entry.reason}"`}
                      </div>
                      <span style={{ color: '#64748b', fontSize: '0.72rem' }}>
                        {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#64748b', fontStyle: 'italic' }}>Created at {new Date(inspectAlert.created_at).toLocaleString()}</div>
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

      {/* Investigate Alert Modal */}
      {investigateModalAlert && (
        <Modal isOpen={!!investigateModalAlert} onClose={() => setInvestigateModalAlert(null)} title="Set Alert Under Geotechnical Investigation">
          <form onSubmit={handleInvestigate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Geotechnical Engineer / Lead Surveyor *
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
                Investigation Protocol & Field Observations *
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Field crew deployed with inclinometer probe and dial gauge; perimeter safety cordon placed."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff', fontFamily: 'inherit' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" onClick={() => setInvestigateModalAlert(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Mark Under Investigation
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

      {/* Reopen Alert Modal */}
      {reopenModalAlert && (
        <Modal isOpen={!!reopenModalAlert} onClose={() => setReopenModalAlert(null)} title="Reopen Resolved Alert">
          <form onSubmit={handleReopen} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Geotechnical Engineer *
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
                Reason for Reopening Incident *
              </label>
              <textarea
                rows={3}
                required
                placeholder="e.g. Post-remediation rainfall triggered recurring shear displacement exceeding 2.0 mm/hr."
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff', fontFamily: 'inherit' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" onClick={() => setReopenModalAlert(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-danger">
                Reopen Incident
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
