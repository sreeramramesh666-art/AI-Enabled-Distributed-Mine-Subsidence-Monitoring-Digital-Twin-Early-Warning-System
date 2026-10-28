# MineGuard-AI System Architecture

## SIH26025 Mine Subsidence Monitoring & Early-Warning System

### 1. Overview
MineGuard-AI is an industrial, local-first monitoring platform engineered for open-cast and underground mine surface monitoring. It tracks geotechnical ground movement, detects anomalous deformation patterns, computes interpretable risk indicators, and provides actionable alerts to mine safety engineers.

```
+-------------------------------------------------------------------------+
|                              SENSOR LAYER                               |
|   [Node 1: Tilt/Disp/Vib]    [Node 2: Tilt/Disp]    [Node N: Health/Tilt]  |
+------------------------------------+------------------------------------+
                                     | LoRa / ESP-NOW / RS485 / Mesh
                                     v
+-------------------------------------------------------------------------+
|                           WIRELESS GATEWAY                              |
|   ESP32 / Linux Gateway with Local Ring-Buffer & Store-and-Forward      |
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
|  - Real-time GIS Geohazard Markers                                      |
|  - Trend & Time-Series Inspector with Missing-Data Visualization        |
|  - Full Alert Lifecycle (Acknowledge, Investigate, Resolve, Audit)      |
|  - Scenario-based Simulation Control Panel                              |
+-------------------------------------------------------------------------+
```

### 2. Core Architectural Pillars

1. **Local-First & Offline Resilience**:
   - Primary database is local SQLite accessed via SQLAlchemy ORM.
   - Operates completely without internet, third-party CDNs, or cloud APIs.
   - Map viewer supports local tile caching and fallback schematic grid.

2. **Decoupled Ingestion**:
   - Dual ingestion paths: REST API (`/api/v1/telemetry`, `/api/v1/telemetry/batch`) and MQTT subscription (`mineguard/nodes/+/telemetry`).
   - Idempotent processing using `(node_id, sequence_number)` and `event_id` deduplication.
   - Separate ingestion timestamp (`received_at`) from measurement timestamp (`timestamp`).

3. **Deterministic Geotechnical Baseline & Anomaly Engine**:
   - Real-time kinematic velocity ($v = \frac{\Delta d}{\Delta t}$) and acceleration ($a = \frac{\Delta v}{\Delta t}$) computation.
   - Dual-tier risk: Physical deformation severity vs Data-quality reliability. Missing data never falsely implies safe ground.
   - Optional unsupervised Isolation Forest for multi-sensor drift and correlation anomalies.

4. **Auditability & Traceability**:
   - Every alert captures contributing raw measurements, triggering rule/model, and baseline reference.
   - Complete audit trail of operator acknowledgements and resolution notes.

