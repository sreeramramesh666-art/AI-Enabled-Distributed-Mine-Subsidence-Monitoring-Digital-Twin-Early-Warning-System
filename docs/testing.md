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

### Backend Tests
```bash
# In project root with active venv:
pytest backend/tests -v
```

### Frontend Tests & Production Build Check
```bash
# In frontend directory:
cd frontend
npm test
npm run build
```

## 3. Test Fixtures and Safety
- All tests operate on temporary SQLite in-memory or throwaway databases (`:memory:` or test files).
- Sensor data is generated using deterministic fixed seeds (`seed=42`).
