import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { Plus, Edit, Cpu, Battery, Wifi, Check, AlertCircle, LineChart, Trash2, Search, Filter, RefreshCw } from 'lucide-react';

export function NodesPage({ latestNodeStatus }) {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editNode, setEditNode] = useState(null);
  const [deleteConfirmNode, setDeleteConfirmNode] = useState(null);
  const [hardDelete, setHardDelete] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Form states
  const [newNode, setNewNode] = useState({
    node_id: '',
    name: '',
    latitude: 23.7541,
    longitude: 86.4215,
    elevation_m: 180.0,
    node_type: 'multiparameter',
    installation_location: 'Bench Sector A',
    firmware_version: 'v1.0.0',
    is_enabled: true,
  });

  const [formError, setFormError] = useState('');

  useEffect(() => {
    loadNodes();
    const interval = setInterval(loadNodes, 6000);
    return () => clearInterval(interval);
  }, [statusFilter]);

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
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'ALL') params.status = statusFilter;
      const data = await api.getNodes(params);
      setNodes(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNode = async (e) => {
    e.preventDefault();
    setFormError('');
    try {
      await api.createNode(newNode);
      setIsAddOpen(false);
      setNewNode({
        node_id: '',
        name: '',
        latitude: 23.7541,
        longitude: 86.4215,
        elevation_m: 180.0,
        node_type: 'multiparameter',
        installation_location: 'Bench Sector A',
        firmware_version: 'v1.0.0',
        is_enabled: true,
      });
      loadNodes();
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleUpdateNode = async (e) => {
    e.preventDefault();
    if (!editNode) return;
    try {
      await api.updateNode(editNode.node_id, {
        name: editNode.name,
        elevation_m: editNode.elevation_m,
        is_enabled: editNode.is_enabled,
      });
      setEditNode(null);
      loadNodes();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  };

  const handleDeleteNode = async (e) => {
    e.preventDefault();
    if (!deleteConfirmNode) return;
    try {
      await api.deleteNode(deleteConfirmNode.node_id, hardDelete);
      setDeleteConfirmNode(null);
      setHardDelete(false);
      loadNodes();
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const filteredNodes = nodes.filter((n) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      n.node_id.toLowerCase().includes(q) ||
      (n.name && n.name.toLowerCase().includes(q)) ||
      (n.installation_location && n.installation_location.toLowerCase().includes(q))
    );
  });

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
            Sensor Node Inventory
          </h1>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Registered Extensometers, Inclinometers & Geotechnical Telemetry Nodes
          </p>
        </div>

        <button onClick={() => setIsAddOpen(true)} className="btn btn-primary">
          <Plus size={15} />
          Register New Node
        </button>
      </div>

      {/* Search and Filters Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '220px', maxWidth: '400px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: '#64748b' }} />
            <input
              type="text"
              placeholder="Search by node ID, name, or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '0.45rem 0.75rem 0.45rem 2rem',
                backgroundColor: '#1e293b',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: '#f8fafc',
                fontSize: '0.825rem'
              }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              border: '1px solid var(--border-color)',
              padding: '0.45rem 0.75rem',
              borderRadius: '6px',
              fontSize: '0.825rem'
            }}
          >
            <option value="ALL">All Connectivity</option>
            <option value="ONLINE">Online Only</option>
            <option value="STALE">Stale Only</option>
            <option value="OFFLINE">Offline Only</option>
          </select>

          <button onClick={loadNodes} className="btn btn-secondary btn-sm" title="Refresh Inventory">
            <RefreshCw size={13} /> Refresh
          </button>
        </div>
      </div>

      {/* Nodes Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Node ID</th>
              <th>Name & Description</th>
              <th>Coordinates</th>
              <th>Type</th>
              <th>Status</th>
              <th>Battery</th>
              <th>Last Seen</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                  Loading sensor node inventory...
                </td>
              </tr>
            ) : filteredNodes.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2.5rem', color: '#64748b' }}>
                  No sensor nodes match your search criteria.
                </td>
              </tr>
            ) : (
              filteredNodes.map((node) => (
                <tr key={node.node_id}>
                  <td style={{ fontWeight: 700, color: '#38bdf8' }}>{node.node_id}</td>
                  <td>
                    <div style={{ fontWeight: 600, color: '#f8fafc' }}>{node.name}</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{node.installation_location || 'Field site'}</div>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    {node.latitude.toFixed(4)}°, {node.longitude.toFixed(4)}°
                    {node.elevation_m ? ` (${node.elevation_m}m)` : ''}
                  </td>
                  <td>
                    <span className="badge" style={{ backgroundColor: '#1e293b', color: '#94a3b8' }}>
                      {node.node_type}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={node.connectivity_status} type="connectivity" />
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    {node.battery_pct !== null && node.battery_pct !== undefined
                      ? `${node.battery_pct.toFixed(0)}%`
                      : 'N/A'}
                  </td>
                  <td style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {node.last_seen ? new Date(node.last_seen).toLocaleString() : 'Never'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      <Link
                        to={`/telemetry?node_id=${encodeURIComponent(node.node_id)}`}
                        className="btn btn-secondary btn-sm"
                        title="View Telemetry & Baseline"
                      >
                        <LineChart size={13} />
                      </Link>
                      <button
                        onClick={() => setEditNode(node)}
                        className="btn btn-secondary btn-sm"
                        title="Edit Node Metadata"
                      >
                        <Edit size={13} />
                      </button>
                      <button
                        onClick={() => {
                          setDeleteConfirmNode(node);
                          setHardDelete(false);
                        }}
                        className="btn btn-danger btn-sm"
                        title="Decommission / Remove Node"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Register Node Modal */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Register Geotechnical Node">
        <form onSubmit={handleCreateNode} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
          {formError && (
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid #991b1b', padding: '0.6rem', borderRadius: '4px', color: '#fca5a5', fontSize: '0.8rem' }}>
              {formError}
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              Node Identifier (Unique Alphanumeric) *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. NODE-PIT-EAST-07"
              value={newNode.node_id}
              onChange={(e) => setNewNode({ ...newNode, node_id: e.target.value })}
              style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              Human-Readable Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. East Highwall Catch Bench Sensor"
              value={newNode.name}
              onChange={(e) => setNewNode({ ...newNode, name: e.target.value })}
              style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Latitude (WGS84) *
              </label>
              <input
                type="number"
                step="0.0001"
                required
                value={newNode.latitude}
                onChange={(e) => setNewNode({ ...newNode, latitude: parseFloat(e.target.value) })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Longitude (WGS84) *
              </label>
              <input
                type="number"
                step="0.0001"
                required
                value={newNode.longitude}
                onChange={(e) => setNewNode({ ...newNode, longitude: parseFloat(e.target.value) })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Elevation (m ASL)
              </label>
              <input
                type="number"
                step="0.1"
                value={newNode.elevation_m}
                onChange={(e) => setNewNode({ ...newNode, elevation_m: parseFloat(e.target.value) })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Sensor Hardware Type
              </label>
              <select
                value={newNode.node_type}
                onChange={(e) => setNewNode({ ...newNode, node_type: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              >
                <option value="multiparameter">Multiparameter Sentinel</option>
                <option value="highwall_extensometer">Wire Extensometer</option>
                <option value="inclinometer">Dual-Axis Inclinometer</option>
                <option value="piezometer">Piezometer Gauge</option>
                <option value="crack_meter_lvdt">Crack Meter LVDT</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button type="button" onClick={() => setIsAddOpen(false)} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Register Node
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Node Modal */}
      {editNode && (
        <Modal isOpen={!!editNode} onClose={() => setEditNode(null)} title={`Edit Node ${editNode.node_id}`}>
          <form onSubmit={handleUpdateNode} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Name
              </label>
              <input
                type="text"
                value={editNode.name}
                onChange={(e) => setEditNode({ ...editNode, name: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
                Elevation (m)
              </label>
              <input
                type="number"
                step="0.1"
                value={editNode.elevation_m || 0}
                onChange={(e) => setEditNode({ ...editNode, elevation_m: parseFloat(e.target.value) })}
                style={{ width: '100%', padding: '0.5rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px', color: '#ffffff' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                id="nodeEnabled"
                checked={editNode.is_enabled}
                onChange={(e) => setEditNode({ ...editNode, is_enabled: e.target.checked })}
              />
              <label htmlFor="nodeEnabled" style={{ fontSize: '0.85rem', color: '#f8fafc' }}>
                Node Enabled for Ingestion
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button type="button" onClick={() => setEditNode(null)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Save Changes
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Delete / Decommission Node Modal */}
      {deleteConfirmNode && (
        <Modal
          isOpen={!!deleteConfirmNode}
          onClose={() => setDeleteConfirmNode(null)}
          title={`Decommission Node ${deleteConfirmNode.node_id}`}
        >
          <form onSubmit={handleDeleteNode} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ color: '#cbd5e1', fontSize: '0.875rem', lineHeight: 1.6 }}>
              Are you sure you want to decommission node <strong style={{ color: '#f8fafc' }}>{deleteConfirmNode.node_id}</strong> ({deleteConfirmNode.name})?
            </div>

            <div style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid #991b1b',
              padding: '0.75rem',
              borderRadius: '6px',
              fontSize: '0.8rem',
              color: '#fca5a5'
            }}>
              <strong>Warning:</strong> Soft decommissioning marks the node disabled and offline, preserving audit and historical telemetry records. Hard purge deletes all associated telemetry and active alerts permanently.
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                id="hardDeleteCheck"
                checked={hardDelete}
                onChange={(e) => setHardDelete(e.target.checked)}
              />
              <label htmlFor="hardDeleteCheck" style={{ fontSize: '0.85rem', color: '#f87171', fontWeight: 600 }}>
                Permanently purge all associated telemetry and cascade records (Hard Delete)
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setDeleteConfirmNode(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-danger">
                {hardDelete ? 'Permanently Delete' : 'Decommission Node'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

