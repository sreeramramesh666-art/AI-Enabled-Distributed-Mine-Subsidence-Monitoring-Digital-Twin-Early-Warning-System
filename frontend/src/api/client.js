const API_BASE = '/api/v1';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const err = await response.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch (e) {
      // Non-JSON response
    }
    throw new Error(`API Error (${response.status}): ${errorDetail}`);
  }
  return response.json();
}

export const api = {
  // System Health
  getHealth: () => fetch(`${API_BASE}/health`).then(handleResponse),

  // Nodes
  getNodes: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${API_BASE}/nodes${qs ? `?${qs}` : ''}`).then(handleResponse);
  },
  createNode: (data) =>
    fetch(`${API_BASE}/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  updateNode: (nodeId, data) =>
    fetch(`${API_BASE}/nodes/${nodeId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  getNodeTelemetry: (nodeId, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${API_BASE}/nodes/${nodeId}/telemetry${qs ? `?${qs}` : ''}`).then(handleResponse);
  },

  // Telemetry
  postTelemetry: (data) =>
    fetch(`${API_BASE}/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  postTelemetryBatch: (data) =>
    fetch(`${API_BASE}/telemetry/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Alerts
  getAlerts: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${API_BASE}/alerts${qs ? `?${qs}` : ''}`).then(handleResponse);
  },
  acknowledgeAlert: (alertId, data) =>
    fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  resolveAlert: (alertId, data) =>
    fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Analytics
  getAnalyticsSummary: () => fetch(`${API_BASE}/analytics/summary`).then(handleResponse),
  getTrends: (nodeId, hours = 24) =>
    fetch(`${API_BASE}/analytics/trends?node_id=${encodeURIComponent(nodeId)}&hours=${hours}`).then(handleResponse),
  getNodeHealth: () => fetch(`${API_BASE}/analytics/node-health`).then(handleResponse),
  getMLStatus: () => fetch(`${API_BASE}/analytics/ml-status`).then(handleResponse),
  trainML: () => fetch(`${API_BASE}/analytics/ml-train`, { method: 'POST' }).then(handleResponse),

  // Simulator
  getSimulatorStatus: () => fetch(`${API_BASE}/simulator/status`).then(handleResponse),
  startSimulator: (data) =>
    fetch(`${API_BASE}/simulator/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  stopSimulator: () => fetch(`${API_BASE}/simulator/stop`, { method: 'POST' }).then(handleResponse),
  resetSimulator: () => fetch(`${API_BASE}/simulator/reset`, { method: 'POST' }).then(handleResponse),

  // Settings
  getSettings: () => fetch(`${API_BASE}/settings`).then(handleResponse),
  updateSettings: (data) =>
    fetch(`${API_BASE}/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
};
