# MineGuard-AI Sensor & Gateway Protocol Specification

## 1. Overview & Transport Protocol

MineGuard-AI supports dual-transport telemetry ingestion:
1. **HTTP REST**: Direct synchronous ingestion via `POST /api/v1/telemetry`, batch ingestion via `POST /api/v1/telemetry/batch`, and store-and-forward replay via `POST /api/v1/telemetry/replay`.
2. **MQTT**: Asynchronous edge gateway publishing over MQTT 3.1.1 / 5.0 with QoS 1 and configurable TLS encryption.

---

## 2. Canonical Gateway Message Format (JSON)

An edge gateway forwards unpacked field radio packets in the canonical `GatewayMessagePayload` schema. Alternatively, flat payloads are accepted and automatically normalized by the ingestion engine.

### 2.1 Structured Gateway Format
```json
{
  "gateway_id": "GW-BENCH-C-01",
  "node_id": "NODE-PIT-NORTH-01",
  "event_id": "c7b3d8a1-4321-4f1b-8712-4217bb654321",
  "sequence_number": 1042,
  "timestamp": "2026-10-28T06:30:00Z",
  "firmware_version": "v1.2.0",
  "units": {
    "displacement": "mm",
    "tilt": "deg",
    "velocity": "mm/hr",
    "vibration": "m/s2",
    "temperature": "C",
    "battery": "%"
  },
  "readings": {
    "displacement_mm": 12.45,
    "tilt_x_deg": 0.42,
    "tilt_y_deg": -0.15,
    "vibration_rms_ms2": 0.08,
    "peak_acceleration_ms2": 0.12,
    "temperature_c": 26.5,
    "crack_width_mm": 2.1,
    "battery_voltage_v": 3.65,
    "battery_pct": 88.0
  },
  "quality": {
    "sensor_status": "nominal",
    "rssi_dbm": -74,
    "snr_db": 9.2,
    "is_physically_bounded": true,
    "has_missing_data": false
  },
  "raw_metadata": {
    "radio_mesh_hops": 2,
    "gateway_received_at": "2026-10-28T06:30:01Z"
  }
}
```

### 2.2 Flat Ingestion Format (Backward Compatible)
```json
{
  "event_id": "c7b3d8a1-4321-4f1b-8712-4217bb654321",
  "node_id": "NODE-PIT-NORTH-01",
  "sequence_number": 1042,
  "timestamp": "2026-10-28T06:30:00Z",
  "data_source": "rest",
  "displacement_mm": 12.45,
  "tilt_x_deg": 0.42,
  "tilt_y_deg": -0.15,
  "vibration_rms_ms2": 0.08,
  "temperature_c": 26.5,
  "battery_pct": 88.0,
  "firmware_version": "v1.2.0"
}
```

---

## 3. SI Units & Permissible Boundaries

All internal calculations and external communications adhere strictly to International System of Units (SI):

| Channel Name | SI Unit | JSON Key | Valid Range | Meaning |
|---|---|---|---|---|
| Cumulative Displacement | mm | `displacement_mm` | -5000.0 to +5000.0 | Ground settlement (+) or heave (-) |
| Inclinometer X Angle | ° | `tilt_x_deg` | -90.0 to +90.0 | Pitch tilt from horizontal equilibrium |
| Inclinometer Y Angle | ° | `tilt_y_deg` | -90.0 to +90.0 | Roll tilt from horizontal equilibrium |
| Vector Tilt | ° | `vector_tilt_deg` | 0.0 to 90.0 | $\sqrt{\theta_x^2 + \theta_y^2}$ |
| Deformation Rate | mm/hr | `velocity_mm_hr` | -5000.0 to +5000.0 | Derived: $\frac{\Delta d}{\Delta t}$ |
| Acceleration | mm/hr² | `acceleration_mm_hr2` | -10000.0 to +10000.0 | Derived: $\frac{\Delta v}{\Delta t}$ |
| Continuous Vibration | m/s² | `vibration_rms_ms2` | 0.0 to 200.0 | Root-mean-square dynamic acceleration |
| Peak Acceleration | m/s² | `peak_acceleration_ms2` | 0.0 to 500.0 | Peak dynamic blast particle acceleration |
| Ambient Temperature | °C | `temperature_c` | -50.0 to +100.0 | Operating thermal environment |
| Joint / Crack Width | mm | `crack_width_mm` | 0.0 to 1000.0 | Surface tensile crack aperture |
| Battery Rail Voltage | V | `battery_voltage_v` | 0.0 to 30.0 | Direct battery potential |
| State of Charge | % | `battery_pct` | 0.0 to 100.0 | Remaining battery capacity |

> [!IMPORTANT]
> **Missing Data Policy**: If a physical channel is uninstrumented or disconnected, it MUST be transmitted as `null` or omitted. It must **NEVER** be sent as `0.0`, because `0.0 mm` represents verified zero displacement equilibrium.

---

## 4. MQTT Topic Architecture

The MQTT client subscribes to topic wildcard hierarchies rooted at `settings.MQTT_TOPIC_PREFIX` (default: `mineguard`):

| Topic Pattern | Direction | QoS | Description |
|---|---|---|---|
| `mineguard/nodes/{node_id}/telemetry` | Node $\to$ Server | 1 | Direct node telemetry frame |
| `mineguard/gateways/{gateway_id}/telemetry` | Gateway $\to$ Server | 1 | Aggregated live telemetry stream forwarded by edge gateway |
| `mineguard/gateways/{gateway_id}/replay` | Gateway $\to$ Server | 1 | Buffered store-and-forward batch replay following link recovery |

### Message Acknowledgement & Quality of Service
- **QoS 1**: All publishing from gateways and nodes MUST use QoS 1 to guarantee at least once delivery across intermittent wireless links.
- **Idempotency**: The MineGuard-AI backend deduplicates messages based on `event_id` and `(node_id, sequence_number)` uniqueness keys.

---

## 5. Store-and-Forward Gateway Replay Envelope

When an edge gateway reconnects following a network partition, it posts buffered observations using the replay envelope:

```json
{
  "gateway_id": "GW-BENCH-C-01",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "transmitted_at": "2026-10-28T07:15:00Z",
  "buffered_count": 25,
  "is_replay": true,
  "records": [
    {
      "node_id": "NODE-PIT-NORTH-01",
      "event_id": "c7b3d8a1-4321-4f1b-8712-4217bb654321",
      "sequence_number": 1042,
      "timestamp": "2026-10-28T06:30:00Z",
      "readings": {
        "displacement_mm": 12.45
      }
    }
  ]
}
```

### Server Replay Response
```json
{
  "gateway_id": "GW-BENCH-C-01",
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "received_count": 25,
  "accepted_count": 23,
  "duplicates_skipped": 2,
  "rejected_count": 0,
  "status": "COMPLETED",
  "errors": []
}
```

---

## 6. Real-Time WebSockets (`/ws/telemetry`)

Dashboard clients establish persistent bidirectional WebSockets for real-time streaming:
- **Telemetry Frame**:
  `{ "type": "telemetry", "data": { "node_id": "...", "displacement_mm": 12.45, "velocity_mm_hr": 2.1 } }`
- **Node Status Update**:
  `{ "type": "node_status", "data": { "node_id": "...", "connectivity_status": "ONLINE", "last_seen": "...", "battery_pct": 88.0, "firmware_version": "v1.2.0" } }`
- **Geotechnical Alert**:
  `{ "type": "alert", "data": { "alert_id": "...", "node_id": "...", "severity": "CRITICAL", "category": "DISPLACEMENT", "title": "..." } }`
- **Replay Completion**:
  `{ "type": "gateway_replay_completed", "data": { "gateway_id": "...", "batch_id": "...", "accepted_count": 23 } }`
- **Heartbeat**:
  Clients send text string `"ping"` every 15 seconds; server replies `"pong"`. If disconnected, clients automatically fall back to periodic REST polling.
