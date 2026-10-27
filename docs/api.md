# MineGuard-AI REST & WebSocket API Specification

## Base URL
Default: `http://localhost:8000/api/v1`

Interactive OpenAPI Documentation: `http://localhost:8000/docs`

---

## 1. System Health
- **`GET /health`**
  - Description: Backend, database connectivity, and simulator status.
  - Response:
    ```json
    {
      "status": "healthy",
      "database": "connected",
      "timestamp": "2026-10-27T17:50:00Z",
      "simulator_running": false,
      "mqtt_status": "disconnected"
    }
    ```

---

## 2. Sensor Nodes Management
- **`GET /nodes`**
  - Description: List registered sensor nodes with current status, battery, and latest reading.
  - Query parameters: `node_type`, `status`, `skip`, `limit`.

- **`POST /nodes`**
  - Description: Register a new sensor node.
  - Body:
    ```json
    {
      "node_id": "NODE-PIT-01",
      "name": "Highwall Bench Sector A",
      "latitude": 23.7541,
      "longitude": 86.4215,
      "elevation_m": 182.5,
      "node_type": "highwall_extensometer",
      "installation_location": "BCCL Jharia Colliery, Bench 4",
      "firmware_version": "v1.2.0"
    }
    ```

- **`GET /nodes/{node_id}`**
  - Description: Fetch node details, hardware configuration, and baseline stats.

- **`PATCH /nodes/{node_id}`**
  - Description: Update node metadata, enabled status, or calibration flags.

- **`GET /nodes/{node_id}/telemetry`**
  - Description: Query time-series telemetry records for a specific node with time range filtering.
  - Query parameters: `start_time`, `end_time`, `limit`.

---

## 3. Telemetry Ingestion
- **`POST /telemetry`**
  - Description: Ingest a single telemetry observation.
  - Validates physical bounds, calculates velocity/acceleration, evaluates rules, and records audit trail.

- **`POST /telemetry/batch`**
  - Description: Atomic ingestion of multiple telemetry observations (used for gateway replay).

---

## 4. Alert Lifecycle
- **`GET /alerts`**
  - Query parameters: `status` (ACTIVE, ACKNOWLEDGED, RESOLVED), `severity` (CRITICAL, WARNING, WATCH, DATA_UNRELIABLE), `node_id`, `skip`, `limit`.

- **`GET /alerts/{alert_id}`**
  - Description: Full alert detail with contributing measurements, triggering rule, and audit log.

- **`POST /alerts/{alert_id}/acknowledge`**
  - Body: `{"acknowledged_by": "Safety Officer Singh", "note": "Inspecting site camera"}`

- **`POST /alerts/{alert_id}/resolve`**
  - Body: `{"resolved_by": "Safety Officer Singh", "resolution_notes": "Blasting crew evacuated, slope bench stabilized"}`

---

## 5. Analytics & Risk
- **`GET /analytics/summary`**
  - Summary metrics: total nodes, reporting nodes, active alerts by severity, overall mine risk status.

- **`GET /analytics/trends`**
  - Deformation trends, maximum rates, and historical timeline.

- **`GET /analytics/node-health`**
  - Battery levels, packet loss rates, and stale node indicators.

---

## 6. Simulator Controls
- **`GET /simulator/status`**: Current state, scenario, frequency, generated count.
- **`POST /simulator/start`**: Start deterministic synthetic generation with parameters:
  - `scenario`: `baseline`, `gradual_settlement`, `accelerating_subsidence`, `sudden_collapse`, `vibration_blast`, `sensor_drift`, `packet_loss`.
  - `interval_sec`: float (e.g. 2.0).
  - `seed`: integer for repeatable generation.
- **`POST /simulator/stop`**: Halt simulation.
- **`POST /simulator/reset`**: Reset synthetic node states.

---

## 7. Reports & Settings
- **`GET /reports/export?format=csv&start_time=...&end_time=...`**: Export historical monitoring records as standard CSV.
- **`GET /reports/export?format=pdf&start_time=...&end_time=...`**: Generate comprehensive geotechnical monitoring PDF summary.
- **`GET /settings`**: View configurable thresholds and site metadata.
- **`PATCH /settings`**: Update alert thresholds and ingestion policies.

---

## 8. WebSockets
- **`WS /ws/telemetry`**
  - Streams real-time messages:
    - `{"type": "telemetry", "data": {...}}`
    - `{"type": "alert", "data": {...}}`
    - `{"type": "node_update", "data": {...}}`
    - `{"type": "simulator_status", "data": {...}}`
