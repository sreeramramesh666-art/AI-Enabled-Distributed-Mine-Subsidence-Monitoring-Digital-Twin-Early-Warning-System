# MineGuard-AI Sensor & Gateway Protocol Specification

## 1. Overview
The MineGuard-AI telemetry ingestion protocol is designed for constrained IoT sensor nodes (e.g., ESP32, STM32) communicating over wireless field protocols (LoRa, ESP-NOW, RS-485 Modbus) via an edge gateway into the central backend via REST or MQTT.

## 2. Telemetry Payload Format (JSON)

Each telemetry event represents a synchronized physical observation snapshot from a monitoring node.

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "node_id": "NODE-PIT-NORTH-01",
  "sequence_number": 1042,
  "timestamp": "2026-10-27T17:45:00.000Z",
  "data_source": "simulator",
  "displacement_mm": 12.45,
  "tilt_x_deg": 1.25,
  "tilt_y_deg": -0.42,
  "vibration_rms_ms2": 0.85,
  "peak_acceleration_ms2": 2.10,
  "temperature_c": 28.4,
  "crack_width_mm": 4.15,
  "battery_voltage_v": 3.95,
  "battery_pct": 88.0,
  "sensor_quality": {
    "tilt_valid": true,
    "displacement_valid": true,
    "vibration_valid": true,
    "signal_rssi_dbm": -68
  },
  "raw_metadata": {}
}
```

## 3. Physical Units & Precision (SI Standards)

| Field | SI Unit | Data Type | Permissible Range | Physical Meaning |
|---|---|---|---|---|
| `displacement_mm` | mm (millimetres) | Float | -5000.0 to +5000.0 | Cumulative vertical/normal displacement relative to initial benchmark |
| `tilt_x_deg` | ° (degrees) | Float | -90.0 to +90.0 | Pitch tilt angle from local horizontal |
| `tilt_y_deg` | ° (degrees) | Float | -90.0 to +90.0 | Roll tilt angle from local horizontal |
| `vibration_rms_ms2` | m/s² | Float | 0.0 to 100.0 | Root-mean-square continuous seismic/blast vibration |
| `peak_acceleration_ms2`| m/s² | Float | 0.0 to 250.0 | Peak dynamic ground acceleration |
| `temperature_c` | °C | Float | -40.0 to +85.0 | Ambient / transducer temperature |
| `crack_width_mm` | mm | Float | 0.0 to 500.0 | Optical or LVDT crack meter aperture |
| `battery_pct` | % | Float | 0.0 to 100.0 | State of charge of node power subsystem |

> [!IMPORTANT]
> Missing measurements must be transmitted as `null` or omitted entirely. Never send `0.0` for a non-existent or uncalibrated sensor, as `0.0 mm` represents zero ground movement.

## 4. Ingestion Channels

### 4.1 REST Endpoints
- `POST /api/v1/telemetry`: Ingest single telemetry record.
- `POST /api/v1/telemetry/batch`: Ingest array of records (used during gateway replay after network recovery).

### 4.2 MQTT Topic Scheme
- Topic: `mineguard/nodes/{node_id}/telemetry`
- QoS: 1 (At least once delivery)
- Retain: False

## 5. Gateway Reconnection and Buffering
When edge connectivity is lost:
1. The gateway appends telemetry frames to local SPIFFS / SD card ring-buffer.
2. Upon connection restoral, gateway replays buffered frames sequentially or in batches.
3. The backend idempotently accepts frames using `event_id` or `(node_id, sequence_number)` deduplication without raising duplicate alerts.
