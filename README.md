# MineGuard-AI — SIH26025 Mine Subsidence Monitoring & Early-Warning System

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6-646cff.svg)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Smart India Hackathon Problem SIH26025**: Automated detection of ground deformation and early warning of surface subsidence hazards in active open-cast and underground coal mines.

---

## 1. System Overview

**MineGuard-AI** is an edge-first, local-first geotechnical monitoring platform designed to operate resiliently in mining concessions. It ingests high-frequency kinematic telemetry from distributed monitoring nodes (extensometers, inclinometers, piezometers, crack meters), detects anomalous deformation trends, computes transparent multi-factor risk scores, and manages an operational alert lifecycle.

### Key Capabilities
- **Local-First & Offline Resilient**: Uses a local SQLite geodatabase via SQLAlchemy ORM. Operates completely without internet connectivity, third-party cloud APIs, or proprietary services.
- **Dual Ingestion**: High-throughput REST API (`/api/v1/telemetry`, `/api/v1/telemetry/batch`) and non-blocking MQTT gateway interface (`mineguard/nodes/+/telemetry`).
- **Store-and-Forward Replay**: Gateways buffer observations locally during field wireless dropouts; the backend idempotently ingests buffered batches using monotonic sequence numbers and UUID deduplication.
- **Deterministic Geotechnical Decision Logic**: Real-time velocity ($v = \frac{\Delta d}{\Delta t}$ in mm/hr) and acceleration ($a = \frac{\Delta v}{\Delta t}$ in mm/hr²) derivation, resultant vector tilt calculation ($\theta = \sqrt{\theta_x^2 + \theta_y^2}$), and tertiary creep detection.
- **Unsupervised Multivariate Anomaly Detection**: Integrated Scikit-Learn Isolation Forest model for multi-sensor drift and correlation anomalies.
- **Industrial GIS Dashboard**: Dark-mode React interface with interactive Leaflet GIS map, local schematic grid fallback mode, Recharts kinematic explorer, alert investigation center, and one-click PDF/CSV export.
- **Deterministic Simulator**: Built-in repeatable multi-scenario sensor generator with configurable seeds, sampling rates, and physical scenarios (gradual settlement, accelerating subsidence, sudden collapse, blasting vibration, sensor drift, packet loss).

---

## 2. Architecture

```
+-------------------------------------------------------------------------+
|                              SENSOR LAYER                               |
|   [Node 1: Extensometer]    [Node 2: Inclinometer]    [Node N: Health]  |
+------------------------------------+------------------------------------+
                                     | LoRa / ESP-NOW / RS485 / Mesh
                                     v
+-------------------------------------------------------------------------+
|                           WIRELESS GATEWAY                              |
|   ESP32 / Edge Linux Gateway with Local Ring-Buffer & Replay Engine     |
+-------------------+---------------------------------+-------------------+
                    | MQTT (JSON)                     | REST Batch (HTTP)
                    v                                 v
+-------------------------------------------------------------------------+
|                        MINEGUARD-AI BACKEND                             |
|                                                                         |
|  +--------------------+  +--------------------+  +-------------------+  |
|  | Ingestion Engine   |  | Deduplication &    |  | Telemetry Service |  |
|  | (REST & MQTT)      |  | Out-of-Order Buffer|  | & Validation      |  |
|  +---------+----------+  +---------+----------+  +---------+---------+  |
|            |                       |                       |            |
|            +-----------------------+-----------------------+            |
|                                    v                                    |
|  +-------------------------------------------------------------------+  |
|  | Analytics Pipeline:                                               |  |
|  | 1. Baseline Extraction & Trend Calculus (Velocity / Accel)        |  |
|  | 2. Deterministic Geotechnical Rules (Tilt, Displacement, Strain)  |  |
|  | 3. Multivariate Anomaly Detection (Isolation Forest)              |  |
|  | 4. Multi-Factor Risk Assessment (Physical + Data Quality)         |  |
|  +---------------------------------+---------------------------------+  |
|                                    v                                    |
|  +--------------------+  +--------------------+  +-------------------+  |
|  | Alert Lifecycle    |  | SQLite Persistent  |  | WebSocket         |  |
|  | Manager            |  | Geodatabase (ORM)  |  | Event Broadcaster |  |
|  +--------------------+  +--------------------+  +-------------------+  |
+------------------------------------+------------------------------------+
                                     | REST & WebSockets
                                     v
+-------------------------------------------------------------------------+
|                        MINEGUARD-AI FRONTEND                            |
|  React 18 + Leaflet GIS Dashboard + Recharts Telemetry + Alert Manager  |
+-------------------------------------------------------------------------+
```

---

## 3. SI Units & Geotechnical Standards

All internal database representations and external communications adhere strictly to International System of Units (SI):

| Measurement | SI Unit | Display Format | Meaning |
|---|---|---|---|
| Cumulative Displacement | $\text{mm}$ (millimetres) | `12.450 mm` | Vertical displacement relative to fixed datum |
| Deformation Velocity | $\text{mm/hr}$ | `2.500 mm/hr` | Rate of ground movement |
| Deformation Acceleration | $\text{mm/hr}^2$ | `0.750 mm/hr²` | Rate of velocity change (Tertiary creep indicator) |
| Vector Rotational Tilt | $^\circ$ (degrees) | `2.45°` | Combined pitch/roll tilt from vertical |
| Dynamic Vibration RMS | $\text{m/s}^2$ | `4.20 m/s²` | Continuous seismic / blasting vibration intensity |
| Ambient Temperature | $^\circ\text{C}$ (Celsius) | `28.5 °C` | Transducer / borehole environmental temperature |

---

## 4. Prerequisites & Installation on Fedora Linux

### 4.1 Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Node.js 18+ and npm
- (Optional) Docker & Docker Compose for containerized MQTT broker

### 4.2 Clone & Set Up Python Environment
```bash
# Clone the repository
git clone https://github.com/your-org/mineguard-ai.git
cd mineguard-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 4.3 Configure Environment Variables
```bash
# Copy example environment configuration
cp .env.example .env
```

### 4.4 Initialize Database & Alembic Migrations
```bash
cd backend
source ../.venv/bin/activate
alembic upgrade head
cd ..
```

### 4.5 Install Frontend Dependencies & Build
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 5. Running the Application

### 5.1 Launch Backend API Server
In terminal 1:
```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive API Documentation (Swagger/OpenAPI): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Status: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- SQLite Database Location: `./data/mineguard.db`

### 5.2 Launch Frontend Development Server
In terminal 2:
```bash
cd frontend
npm run dev
```
- Dashboard URL: [http://localhost:5173](http://localhost:5173)

---

## 6. Deterministic Simulator

The simulator produces repeatable synthetic observations without requiring physical ESP32 hardware.

### 6.1 Control via UI
Navigate to the **Simulator Control** page (`/simulator`) in the dashboard:
1. Select a scenario (e.g. `accelerating_subsidence`).
2. Adjust interval (e.g. 2.0s) and random seed.
3. Click **Start Scenario**. The top navigation bar will display a `SIMULATING DATA` badge.

### 6.2 Control via Standalone CLI Script
```bash
source .venv/bin/activate
PYTHONPATH=. python backend/app/simulator/engine.py --scenario accelerating_subsidence --interval 2.0 --nodes 6
```

### 6.3 Generate a Test Anomaly & Inspect Alert
1. In the simulator, select scenario **Accelerating Subsidence (Tertiary Creep)**.
2. Click **Start Scenario**.
3. Within 10-15 seconds, node `NODE-PIT-NORTH-01` will accelerate past $0.5\text{ mm/hr}^2$ and cumulative displacement will cross warning ($15\text{ mm}$) and critical ($30\text{ mm}$) thresholds.
4. A red **CRITICAL HAZARD** alert appears in the top navigation bar and on the **Alerts Centre** (`/alerts`).
5. Click **Eye (Inspect)** on the alert to view raw telemetry evidence, triggering rule (`RULE_CRITICAL_ACCELERATION`), and timestamp.
6. Click **Ack** to acknowledge with operator details, or **Resolve** to close the incident with formal remediation notes.

---

## 7. Running Automated Tests

All tests run locally inside the sandbox without external network calls.

### Backend Test Suite (Pytest)
```bash
source .venv/bin/activate
PYTHONPATH=. pytest backend/tests -v
```
**Results: 17 passed in 0.37s** (covering models, migrations, telemetry validation, kinematics, deduplication, rules, risk scoring, ML anomaly detection, PDF/CSV generation, and full end-to-end cycle).

### Frontend Test Suite (Vitest)
```bash
cd frontend
npm test
```
**Results: 2 test files passed, 6 unit tests passed in 1.37s**.

### Frontend Production Build Check
```bash
cd frontend
npm run build
```
**Results: built in 2.65s (zero build errors).**

---

## 8. Docker Compose Deployment (Optional)

To launch the backend, frontend, and a local Eclipse Mosquitto MQTT broker in containers:

```bash
docker-compose up --build
```
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Mosquitto MQTT Broker: `localhost:1883`

---

## 9. Geotechnical Disclaimer & Safety Notice

> [!WARNING]
> MineGuard-AI is a prototype research and demonstration platform developed for Smart India Hackathon problem SIH26025. 
> Numerical parameters, warning levels, and simulation scenarios represent demonstration thresholds only. 
> Real-world deployment in active open-cast or underground mining operations mandates certified geotechnical surveys, site-specific rock mass rating (RMR) calibration, and formal regulatory safety approvals under Directorate General of Mines Safety (DGMS) norms.
