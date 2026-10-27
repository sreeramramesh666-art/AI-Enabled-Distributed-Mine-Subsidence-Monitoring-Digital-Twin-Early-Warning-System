import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { Plus, Edit, Cpu, Battery, Wifi, Check, AlertCircle } from 'lucide-react';

export function NodesPage() {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editNode, setEditNode] = useState(null);

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
  }, []);

  const loadNodes = async () => {
    try {
      const data = await api.getNodes();
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
            {nodes.map((node) => (
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
                  <button
                    onClick={() => setEditNode(node)}
                    className="btn btn-secondary btn-sm"
                  >
                    <Edit size={13} /> Edit
                  </button>
                </td>
              </tr>
            ))}
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
    </div>
  );
}
