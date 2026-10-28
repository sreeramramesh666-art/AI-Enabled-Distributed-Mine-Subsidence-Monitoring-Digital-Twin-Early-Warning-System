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
  getHealthLiveness: () => fetch(`${API_BASE}/health/liveness`).then(handleResponse),
  getHealthReadiness: () => fetch(`${API_BASE}/health/readiness`).then(handleResponse),
  getHealthMQTT: () => fetch(`${API_BASE}/health/mqtt`).then(handleResponse),

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
  deleteNode: (nodeId, hardDelete = false) =>
    fetch(`${API_BASE}/nodes/${nodeId}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    }).then(handleResponse),
  getNodeBaseline: (nodeId) =>
    fetch(`${API_BASE}/nodes/${nodeId}/baseline`).then(handleResponse),
  recalculateBaseline: (nodeId, periodHours = 72.0) =>
    fetch(`${API_BASE}/nodes/${nodeId}/baseline/recalculate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ period_hours: periodHours }),
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
  postGatewayReplay: (data) =>
    fetch(`${API_BASE}/telemetry/replay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  getGatewayFormat: () => fetch(`${API_BASE}/telemetry/gateway-format`).then(handleResponse),

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
  investigateAlert: (alertId, data) =>
    fetch(`${API_BASE}/alerts/${alertId}/investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  reopenAlert: (alertId, data) =>
    fetch(`${API_BASE}/alerts/${alertId}/reopen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Analytics
  getAnalyticsSummary: () => fetch(`${API_BASE}/analytics/summary`).then(handleResponse),
  getTrends: (nodeId, hours = 24) =>
    fetch(`${API_BASE}/analytics/trends?node_id=${encodeURIComponent(nodeId)}&hours=${hours}`).then(handleResponse),
  getNodeHealth: () => fetch(`${API_BASE}/analytics/node-health`).then(handleResponse),
  getSpatialCorroboration: (radiusMeters = 500, timeWindowMin = 60) =>
    fetch(`${API_BASE}/analytics/spatial-corroboration?radius_meters=${radiusMeters}&time_window_minutes=${timeWindowMin}`).then(handleResponse),
  getMLStatus: () => fetch(`${API_BASE}/analytics/ml-status`).then(handleResponse),
  trainML: () => fetch(`${API_BASE}/analytics/ml-train`, { method: 'POST' }).then(handleResponse),

  // Audit Events
  getAuditEvents: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${API_BASE}/audit-events${qs ? `?${qs}` : ''}`).then(handleResponse);
  },

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

  // Test-Rig Experiments (Table 12 Benchmark)
  getTestRuns: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return fetch(`${API_BASE}/test-runs${qs ? `?${qs}` : ''}`).then(handleResponse);
  },
  getTestRun: (testRunId) => fetch(`${API_BASE}/test-runs/${encodeURIComponent(testRunId)}`).then(handleResponse),
  startTestRun: (data) =>
    fetch(`${API_BASE}/test-runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  recordReferenceMovement: (testRunId, data) =>
    fetch(`${API_BASE}/test-runs/${encodeURIComponent(testRunId)}/reference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  completeTestRun: (testRunId, data = {}) =>
    fetch(`${API_BASE}/test-runs/${encodeURIComponent(testRunId)}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),
  getTestRunCsvUrl: (testRunId) => `${API_BASE}/test-runs/${encodeURIComponent(testRunId)}/export/csv`,
  getTestRunPdfUrl: (testRunId) => `${API_BASE}/test-runs/${encodeURIComponent(testRunId)}/export/pdf`,
};

