# MineGuard-AI Testing Strategy

## 1. Automated Testing Architecture
Testing spans four layers:
1. **Unit Tests (Backend & Analytics)**:
   - Pytest suites for deterministic rule evaluations, mathematical velocity/acceleration derivation, Isolation Forest anomaly detection, deduplication, and schema validation.
2. **Integration & API Tests**:
   - FastAPI `TestClient` / `httpx` testing SQLite database transactions, ingestion idempotency, batch replay, alert state transitions, and CSV/PDF report generation.
3. **Frontend Component & Hook Tests**:
   - Vitest and React Testing Library verifying state management, dark mode rendering, missing-data handling, alert acknowledge modals, and Leaflet fallback schematic view.
4. **End-to-End Synthetic Scenarios**:
   - Verification of simulated accelerating displacement triggering CRITICAL alert and dispatching WebSocket updates.

## 2. Test Commands

### Backend Pytest Suite
```bash
# In project root with active venv:
source .venv/bin/activate
PYTHONPATH=. pytest backend/tests -v
```
**Results: 66 passed in ~1.0s**
- `test_alerts.py`: Alert lifecycle, investigation notes, resolution, reopening, 404 cases, category and temporal filtering.
- `test_experiments.py`: Laboratory benchmark lifecycle, reference movement entry, Table 12 metrics computation, CSV/PDF export.
- `test_analytics.py`: Summary metrics, trends, Isolation Forest ML model training and status.
- `test_analytics_pipeline.py`: Baseline establishment & storage, kinematics derivation with actual timestamps, stable data false-alarm suppression, gradual subsidence threshold crossings, tertiary creep acceleration, sudden step fault slip, blasting vibration discrimination, anti-false-safe data quality safeguards, frozen transducer detection, monotonic electronic drift, cross-channel sensor disagreement, persistent inclinometer baseline departure, spatial neighbor corroboration, Isolation Forest disclaimer verification, alert deduplication and severity escalation.
- `test_audit.py`: Immutable audit events pagination and category filtering.
- `test_database_failure.py`: Real disk SQLite database transaction integrity and rollback on failure.
- `test_e2e_workflow.py`: Full end-to-end monitoring cycle (node registration -> baseline ingestion -> anomaly -> alert -> acknowledge -> resolve -> audit event).
- `test_health.py`: Core health check, Kubernetes liveness and readiness probes, and database failure reporting.
- `test_nodes.py`: Node CRUD, validation, pagination, baseline retrieval, and time-range filtering.
- `test_reports.py`: CSV export, invalid time-range rejection, CSV formula injection sanitization, PDF report generation.
- `test_rules.py`: Resultant vector tilt calculation, kinematics calculation, critical geotechnical thresholds.
- `test_settings.py`: Site metadata and threshold management, hierarchy validation (warning < critical).
- `test_simulator.py`: Deterministic multi-scenario generator and API controls.
- `test_telemetry.py`: REST ingestion, deduplication, unknown/disabled node rejection, physical bounds validation, missing data preservation, out-of-order kinematics correction, atomic batch rollbacks.
- `test_telemetry_pipeline.py`: Single telemetry ingestion, canonical gateway schema, store-and-forward batch replay, delayed replay alarm suppression, MQTT client broker fallback, payload validation, live & replay message routing, bounded retry delays, WebSocket broadcast, firmware version tracking, MQTT health endpoint.

### Hardware-in-the-Loop (HIL) Firmware Validator
```bash
source .venv/bin/activate
python simulator/hil_firmware_validator.py
```
**Results: 6 out of 6 stages passed**
- Stage 1: LittleFS non-volatile ring buffer write/read/recovery.
- Stage 2: 41-byte binary packed struct validation with IEEE-754 float channels and CRC16 checksum.
- Stage 3: UART 115200 baud packet transmitter framing and byte alignment.
- Stage 4: Gateway store-and-forward batch replay ingestion and idempotent duplicate suppression.
- Stage 5: Out-of-order sequence correction and kinematic velocity re-derivation.
- Stage 6: Geotechnical rule alert trigger verification on tertiary creep threshold.

### Frontend Vitest Suite
```bash
# In frontend directory:
cd frontend
npm test -- --run
```
**Results: 9 test files, 22 passed in ~1.9s**
- `Navbar.test.jsx`: Simulation status indicator and navigation links.
- `StatusBadge.test.jsx`: Severity levels, connectivity indicators, and data source tags.
- `DashboardPage.test.jsx`: Command center KPIs, live ticker, and alert feed.
- `NodesPage.test.jsx`: Sensor node inventory, registration modal, soft and hard decommissioning.
- `AlertsPage.test.jsx`: Regulatory hazard alerts, inspection modal, operator acknowledgement, resolution, and reopening.
- `ExperimentsPage.test.jsx`: Table 12 laboratory benchmark metrics, reference tracking, scenario launching, and export triggers.
- `ReportsPage.test.jsx`: Report cards, CSV export trigger, and PDF report download.
- `SettingsPage.test.jsx`: Threshold configuration, hierarchy validation error banners, persistence.
- `SimulatorPage.test.jsx`: Scenario selector, frequency adjustment, and start/stop controls.

### Frontend Production Build
```bash
cd frontend
npm run build
```
**Results: Vite production build succeeded in ~2.49s with zero errors.**

---

## 3. End-to-End Workflow Verification Script
To execute a live end-to-end audit check against the running database:
```bash
source .venv/bin/activate
python3 -c "
import uuid, datetime
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
node_id = f'AUDIT-{uuid.uuid4().hex[:6]}'
assert client.get('/api/v1/health').status_code == 200
assert client.post('/api/v1/nodes/', json={'node_id': node_id, 'name': 'Audit Pit Wall Monitor', 'latitude': 23.79, 'longitude': 86.43, 'is_enabled': True}).status_code == 201
ts = datetime.datetime.now(datetime.timezone.utc)
client.post('/api/v1/telemetry/', json={'node_id': node_id, 'timestamp': (ts - datetime.timedelta(hours=1)).isoformat(), 'displacement_mm': 0.1})
client.post('/api/v1/telemetry/', json={'node_id': node_id, 'timestamp': ts.isoformat(), 'displacement_mm': 65.0, 'tilt_x_deg': 5.5})
alerts = client.get(f'/api/v1/alerts/?node_id={node_id}&status=ACTIVE').json()['items']
assert len(alerts) > 0
aid = alerts[0]['alert_id']
client.post(f'/api/v1/alerts/{aid}/acknowledge', json={'acknowledged_by': 'Audit-Op', 'note': 'Dispatched team'})
client.post(f'/api/v1/alerts/{aid}/resolve', json={'resolved_by': 'Audit-Lead', 'resolution_notes': 'Secured'})
assert client.get('/api/v1/reports/export?format=csv').status_code == 200
assert client.get('/api/v1/reports/export?format=pdf').status_code == 200
print('ALL VERIFICATION CHECKS PASSED!')
"
```

## 3. Test Fixtures and Safety
- All tests operate on temporary SQLite in-memory or throwaway databases (`:memory:` or test files).
- Sensor data is generated using deterministic fixed seeds (`seed=42`).

