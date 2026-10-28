# MineGuard-AI REST & WebSocket API Specification

## Base URL
Default: `http://localhost:8000/api/v1`

Interactive OpenAPI Documentation: `http://localhost:8000/docs`

---

## 1. System Health
- **`GET /health`**
  - Description: Backend status, database connectivity, and simulator status.
  - Returns: HTTP 200 on healthy, HTTP 503 if database connectivity fails.
  - Response:
    ```json
    {
      "status": "healthy",
      "database": "connected",
      "timestamp": "2026-10-28T05:45:00Z",
      "simulator_running": false,
      "mqtt_status": "disabled",
      "version": "1.0.0"
    }
    ```
- **`GET /health/mqtt`**
  - Description: Detailed operational health of background MQTT subscriber client.
  - Returns: Connection state, broker host/port, client ID, topic subscriptions, message counters, duplicate count, reconnect count, last message timestamp, and last error.
- **`GET /health/liveness`**
  - Description: Kubernetes / Docker process liveness probe. Returns HTTP 200.
- **`GET /health/readiness`**
  - Description: Container readiness probe verifying active database connectivity. Returns HTTP 200 or 503.

---

## 2. Sensor Nodes Management
- **`GET /nodes`**
  - Description: List registered sensor nodes with current status, battery, and latest reading.
  - Query parameters: `node_type`, `status` (ONLINE, STALE, OFFLINE), `is_enabled` (boolean), `search` (text search on node_id or name), `skip`, `limit`.

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
      "node_type": "multiparameter",
      "installation_location": "BCCL Jharia Colliery, Bench 4",
      "firmware_version": "v1.2.0"
    }
    ```

- **`GET /nodes/{node_id}`**
  - Description: Fetch node details, hardware configuration, and baseline stats.

- **`PATCH /nodes/{node_id}`**
  - Description: Update node metadata, enabled status, or calibration flags.

- **`DELETE /nodes/{node_id}`**
  - Description: Safely decommission or remove a node and its related telemetry and active alerts.
  - Query parameters: `hard_delete: bool` (default `false`). When `hard_delete=false`, marks node as disabled and connectivity as OFFLINE. When `true`, cascades deletion.

- **`GET /nodes/{node_id}/baseline`**
  - Description: Retrieve the baseline reference statistics (reference displacement, tilt standard deviations, calculation period).

- **`POST /nodes/{node_id}/baseline/recalculate`**
  - Description: Recalculate baseline reference parameters from the last $N$ hours of historical telemetry.
  - Body (optional): `{"period_hours": 72.0}`

- **`GET /nodes/{node_id}/telemetry`**
  - Description: Query time-series telemetry records for a specific node with time range filtering.
  - Query parameters: `start_time` (ISO 8601), `end_time` (ISO 8601), `skip`, `limit`.

---

## 3. Telemetry Ingestion
- **`POST /telemetry`**
  - Description: Ingest a single telemetry observation.
  - Validates physical bounds, calculates velocity/acceleration, evaluates rules, detects duplicates (idempotent), and records audit trail.
  - Handles delayed replay and recalculates kinematics for subsequent out-of-order records.
  - Response: HTTP 201 Created on success, HTTP 409 Conflict on duplicate, HTTP 422 on physical validation error.

- **`POST /telemetry/batch`**
  - Description: Batch ingestion of multiple telemetry observations (used for gateway replay and bulk sync).
  - Body:
    ```json
    {
      "records": [...],
      "atomic": true
    }
    ```
  - When `atomic: true`, any validation failure rolls back the entire batch without leaving orphaned rows.

- **`POST /telemetry/replay`**
  - Description: Field gateway store-and-forward batch replay endpoint. Designed for bulk upload after wireless reconnection.
  - Automatically deduplicates records, suppresses live emergency alarms for delayed historical measurements, and recalculates out-of-order kinematics.
  - Returns batch count, accepted count, duplicate count, and rejected count.

- **`GET /telemetry/gateway-format`**
  - Description: Returns canonical gateway telemetry schema and SI unit specifications for field firmware developers.

---

## 4. Alert Lifecycle
- **`GET /alerts`**
  - Query parameters: `status` (ACTIVE, ACKNOWLEDGED, UNDER_INVESTIGATION, RESOLVED, REOPENED), `severity` (CRITICAL, WARNING, WATCH, DATA_UNRELIABLE), `category` (DISPLACEMENT, VELOCITY, ACCELERATION, TILT, VIBRATION, BATTERY, SENSOR_DRIFT), `node_id`, `mine_panel`, `start_time`, `end_time`, `skip`, `limit`.

- **`GET /alerts/{alert_id}`**
  - Description: Full alert detail with contributing measurements, triggering rule, recommended action, lifecycle history, and audit log.

- **`POST /alerts/{alert_id}/acknowledge`**
  - Body: `{"acknowledged_by": "Safety Officer Singh", "note": "Inspecting site camera"}`

- **`POST /alerts/{alert_id}/investigate`**
  - Description: Mark active or acknowledged alert as under active field geotechnical investigation.
  - Body: `{"investigated_by": "Lead Surveyor Patel", "investigation_notes": "Deploying manual dial gauge"}`

- **`POST /alerts/{alert_id}/resolve`**
  - Body: `{"resolved_by": "Safety Officer Singh", "resolution_notes": "Blasting crew evacuated, slope bench stabilized"}`

- **`POST /alerts/{alert_id}/reopen`**
  - Description: Reopen a previously resolved alert upon detection of recurring movement.
  - Body: `{"reopened_by": "Geotechnical Engineer Sharma", "reason": "Subsequent sensor reading indicated renewed acceleration"}`

---

## 5. Analytics & Risk
- **`GET /analytics/summary`**
  - Summary metrics: total nodes, reporting nodes, active alerts by severity, overall mine risk status.

- **`GET /analytics/trends`**
  - Deformation trends, maximum rates, and historical timeline for a node or across all nodes.
  - Query parameters: `node_id`, `hours` (default 24).

- **`GET /analytics/node-health`**
  - Battery levels, packet loss rates, and stale node indicators.

- **`GET /analytics/spatial-corroboration`**
  - Identifies clusters of simultaneous movement among proximate nodes within a configurable geographic radius (default 500m) to distinguish real localized subsidence from isolated sensor error.

- **`GET /analytics/ml-status`**
  - Inspection of the scikit-learn Isolation Forest multivariate anomaly detector (training status, sample count, contamination threshold).

- **`POST /analytics/ml-train`**
  - Train or refit the multivariate Isolation Forest anomaly detection model using baseline or historical telemetry observations.

---

## 6. Audit Logging
- **`GET /audit-events`**
  - Query parameters: `category` (e.g. `TELEMETRY`, `ALERT`, `NODE`, `SETTINGS`), `node_id`, `alert_id`, `actor`, `start_time`, `end_time`, `skip`, `limit`.
  - Immutable audit trail recording all safety-critical actions and operator acknowledgements.

---

## 7. Simulator Controls
- **`GET /simulator/status`**: Current state, scenario, frequency, generated count.
- **`POST /simulator/start`**: Start deterministic synthetic generation with parameters:
  - `scenario`: `baseline`, `gradual_settlement`, `accelerating_subsidence`, `sudden_collapse`, `vibration_blast`, `sensor_drift`, `packet_loss`, `testrig_baseline`, `testrig_gradual`, `testrig_differential`, `testrig_vibration_only`, `testrig_disconnect_reconnect`, `testrig_comm_loss`, `testrig_return_stable`.
  - `interval_sec`: float (e.g. 2.0).
  - `seed`: integer for repeatable generation.
- **`POST /simulator/stop`**: Halt simulation.
- **`POST /simulator/reset`**: Reset synthetic node states.

---

## 8. Laboratory Test-Rig Benchmark & Evaluation (Table 12)
- **`POST /test-runs`**
  - Description: Initialize a laboratory testbed evaluation run.
  - Body:
    ```json
    {
      "name": "Benchmark Lab Test #1",
      "scenario": "testrig_gradual",
      "test_conditions": "Controlled granular testbed with micrometer lead screw",
      "target_node_id": "NODE-PIT-NORTH-01",
      "intended_movement_mm": 5.0,
      "notes": "Testing 5mm displacement on dial gauge"
    }
    ```
- **`GET /test-runs`**
  - Query parameters: `status` (RUNNING, COMPLETED, ABORTED), `skip`, `limit`.
- **`GET /test-runs/{test_run_id}`**
  - Description: Full benchmark run details and Table 12 evaluation metrics.
- **`POST /test-runs/{test_run_id}/reference`**
  - Description: Log ground truth displacement measured independently via dial indicator / micrometer.
  - Body: `{"reference_movement_mm": 5.02, "notes": "Reading from barrel vernier"}`
- **`POST /test-runs/{test_run_id}/complete`**
  - Description: Conclude test run and compute Table 12 metrics (absolute measurement error, latency, PDR %, false alerts denominator, precision, recall, F1 score).
- **`GET /test-runs/{test_run_id}/export/csv`**
  - Description: Export benchmark evaluation summary and time series in RFC 4180 CSV format.
- **`GET /test-runs/{test_run_id}/export/pdf`**
  - Description: Generate structured Table 12 laboratory evaluation PDF report.

---

## 9. Reports & Settings
- **`GET /reports/export?format=csv&start_time=...&end_time=...`**: Export historical monitoring records as standard CSV.
- **`GET /reports/export?format=pdf&start_time=...&end_time=...`**: Generate comprehensive geotechnical monitoring PDF summary.
- **`GET /settings`**: View configurable thresholds and site metadata.
- **`PATCH /settings`**: Update alert thresholds and ingestion policies.

---

## 10. WebSockets
- **`WS /ws/telemetry`**
  - Streams real-time messages:
    - `{"type": "telemetry", "data": {...}}`
    - `{"type": "alert", "data": {...}}`
    - `{"type": "node_update", "data": {...}}`
    - `{"type": "simulator_status", "data": {...}}`

