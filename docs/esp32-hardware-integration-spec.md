# MineGuard-AI: ESP32 Hardware Integration Specification & Field Protocol

**Document Version**: 1.0.0  
**Project**: MineGuard-AI — SIH26025 Mine Subsidence Monitoring & Early-Warning System  
**Target Hardware**: Espressif ESP32 / ESP32-S3 / STM32L4 Microcontrollers + Semtech SX1262 / SX1276 LoRa  
**Target Backend**: MineGuard-AI Central Telemetry Ingestion Engine (REST & MQTT)  
**Standard**: SI Units (ISO 80000-1) / RFC 4180 / MQTT v3.1.1 & v5.0 / JSON Schema (Draft 2020-12)

---

## 1. Safety Notice & Hardware Development Disclaimer

> [!WARNING]
> **Prototype & Hardware Development Boundary**:
> Physical ESP32 microcontrollers, LoRa RF transceivers, and mesh network firmware have **not been physically deployed or bench-tested** on active rock faces during this software development phase. 
> All gateway interfaces, packet structures, and buffering protocols specified herein represent the **precise, verified interface contract** that embedded firmware developers must implement and validate on physical target silicon before field deployment in active mining operations.
> 
> Under no circumstances should firmware write fake or estimated sensor readings when transducers are disconnected, damaged, or open-circuit. Numerical stability thresholds ($v \ge 2.0\text{ mm/hr}$, $a \ge 0.5\text{ mm/hr}^2$) represent demonstration values only and require site-specific geotechnical survey calibration under Directorate General of Mines Safety (DGMS) norms prior to operational use.

---

## 2. Distributed 3-Tier System Architecture

To operate reliably in harsh open-cast highwalls and deep underground coal mine workings where cellular or terrestrial Ethernet coverage is absent at individual benches, MineGuard-AI enforces a strict 3-tier decoupling of low-power radio communication from high-level backend application ingestion:

```
+-----------------------------------------------------------------------------------------+
|                                TIER 1: SENSOR NODES                                     |
|  - Controller: ESP32-WROOM-32 / ESP32-S3 / STM32L4 (Ultra-Low Power Deep Sleep)         |
|  - Power: 12.8V LiFePO4 battery pack (20Ah) + 20W Monocrystalline PV Panel + MPPT      |
|  - Transducers: Dual-axis MEMS Inclinometer (SCA103T / ADXL355), Borehole LVDT/Wire     |
|    Extensometer (1000 mm stroke), Geophone / Piezoelectric Vibration Sensor             |
|  - Field Radio: Sub-GHz LoRa (865-867 MHz in India) or 2.4 GHz ESP-NOW Mesh             |
|  - Payload: Packed binary struct (41 bytes compact RF frame)                            |
+--------------------------------------------+--------------------------------------------+
                                             | LoRa P2P / LoRaWAN Class A / ESP-NOW
                                             v
+-----------------------------------------------------------------------------------------+
|                                TIER 2: EDGE WIRELESS GATEWAY                            |
|  - Hardware: Industrial ESP32-S3 Gateway / Linux Single Board Computer (Raspberry Pi 4) |
|  - Timekeeping: DS3231 Temperature-Compensated Hardware RTC ($\pm 2\text{ ppm}$)        |
|  - Local Storage: Wear-levelled SPIFFS / LittleFS / Automotive-grade Industrial SD      |
|  - Backhaul: 4G LTE Cat-M1 / Industrial Wi-Fi / Ruggedized Field Ethernet              |
|  - Responsibilities:                                                                   |
|      1. Demodulates raw 41-byte binary RF packets from node cluster                     |
|      2. Verifies CRC-8 payload integrity and drops corrupt frames                       |
|      3. Appends DS3231 hardware timestamp and generates UUIDv4 event ID                 |
|      4. Serializes unpacked measurements into MineGuard-AI JSON schemas                 |
|      5. Maintains local non-volatile ring-buffer during IP backhaul outages             |
|      6. Streams live observations via MQTT (QoS 1) or REST POST                        |
|      7. Replays buffered frames via POST /api/v1/telemetry/replay on link recovery      |
+--------------------------------------------+--------------------------------------------+
                                             | IP Network (HTTPS / MQTT TLS)
                                             v
+-----------------------------------------------------------------------------------------+
|                                TIER 3: MINEGUARD-AI CENTRAL SERVER                      |
|  - Ingestion: REST Ingestion Engine (`/api/v1/telemetry`) & Paho MQTT Subscriber        |
|  - Real-Time Broadcast: Bidirectional WebSockets (`/ws/telemetry`)                      |
|  - Storage: Local-First Persistent SQLite Geodatabase (SQLAlchemy ORM + Alembic)        |
|  - Analytics: Deterministic Kinematics Calculus, Geotechnical Rules, Isolation Forest ML|
|  - Visualization: Industrial Dark-Mode React 18 GIS Dashboard & Report Generator        |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Tier 1: Sensor Node RF Binary Framing Protocol

To minimize airtime, conserve battery charge during deep sleep cycles, and adhere to wireless regulatory duty cycle limitations, field nodes transmit binary frames formatted as a C structure:

### 3.1 C Structure Definition (`LoRaTelemetryPacket_t`)
```c
#include <stdint.h>

// Total packet size: exactly 41 bytes (no compiler padding)
typedef struct __attribute__((packed)) {
    uint8_t   protocol_version;    // Protocol identifier: 0x01
    char      node_id[16];         // Null-padded alphanumeric ID, e.g., "NODE-PIT-C01\0\0\0\0"
    uint32_t  sequence_number;     // Monotonically increasing counter (0 to 4,294,967,295)
    int32_t   displacement_um;     // Cumulative displacement in micro-metres (1 mm = 1000 um, signed)
    int16_t   tilt_x_cdeg;         // Pitch angle in centi-degrees (0.01 deg resolution, signed: -9000 to +9000)
    int16_t   tilt_y_cdeg;         // Roll angle in centi-degrees (0.01 deg resolution, signed: -9000 to +9000)
    uint16_t  vibration_rms_mg;    // RMS vibration in milli-g (1 g = 9.80665 m/s2, range: 0 to 20,000 mg)
    uint16_t  peak_accel_mg;       // Peak acceleration in milli-g (range: 0 to 50,000 mg)
    int16_t   temperature_cdeg;    // Temperature in centi-Celsius (0.01 deg C resolution, signed)
    uint16_t  crack_width_um;      // Joint aperture in micro-metres (1 mm = 1000 um)
    uint16_t  battery_mv;          // Battery rail potential in milli-volts (e.g. 3650 mV)
    uint8_t   status_flags;        // Status and channel validity bitfield (see Table 3.2)
    uint8_t   crc8;                // CRC-8 polynomial 0x07 (X8 + X2 + X + 1) across bytes [0..34]
} LoRaTelemetryPacket_t;
```

### 3.2 Status Bitfield Specification (`status_flags`)
| Bit | Name | Logic 0 | Logic 1 | Handling Rule |
|---|---|---|---|---|
| **0** | `DISP_VALID` | Extensometer disconnected / error | Transducer reading nominal | If 0, gateway sends `displacement_mm: null` |
| **1** | `TILT_VALID` | Inclinometer disconnected / error | Transducer reading nominal | If 0, gateway sends `tilt_x_deg: null, tilt_y_deg: null` |
| **2** | `VIB_VALID` | Geophone disconnected / error | Transducer reading nominal | If 0, gateway sends `vibration_rms_ms2: null` |
| **3** | `TEMP_VALID` | Thermistor disconnected / error | Transducer reading nominal | If 0, gateway sends `temperature_c: null` |
| **4** | `CRACK_VALID` | Crack gauge disconnected / error | Transducer reading nominal | If 0, gateway sends `crack_width_mm: null` |
| **5** | `BATT_LOW` | Battery $\ge 20\%$ | Battery $< 20\%$ critical rail | Triggers `BATTERY_LOW` quality status |
| **6** | `TAMPER_ALERT` | Enclosure sealed | Enclosure open / tilt shock | Flags raw metadata for physical inspection |
| **7** | `CALIBRATING` | Normal measurement | Field calibration in progress | Suppresses alert generation |

---

## 4. Tier 2: Gateway Deserialization & Conversion Rules

The edge gateway unpacks binary RF frames, applies engineering conversions to International System of Units (SI), appends timekeeping metadata from its hardware RTC, and formats the output into JSON.

### 4.1 Engineering Unit Conversion Formulas
| Struct Field | Raw Range | Conversion Formula | Output JSON Field | Output SI Unit |
|---|---|---|---|---|
| `displacement_um` | $-5,000,000 \dots +5,000,000$ | $\text{val} / 1000.0$ | `displacement_mm` | $\text{mm}$ (millimetres) |
| `tilt_x_cdeg` | $-9000 \dots +9000$ | $\text{val} / 100.0$ | `tilt_x_deg` | $^\circ$ (degrees) |
| `tilt_y_cdeg` | $-9000 \dots +9000$ | $\text{val} / 100.0$ | `tilt_y_deg` | $^\circ$ (degrees) |
| `vibration_rms_mg`| $0 \dots 20000$ | $(\text{val} / 1000.0) \times 9.80665$ | `vibration_rms_ms2` | $\text{m/s}^2$ |
| `peak_accel_mg` | $0 \dots 50000$ | $(\text{val} / 1000.0) \times 9.80665$ | `peak_acceleration_ms2`| $\text{m/s}^2$ |
| `temperature_cdeg`| $-5000 \dots +10000$ | $\text{val} / 100.0$ | `temperature_c` | $^\circ\text{C}$ (Celsius) |
| `crack_width_um` | $0 \dots 1,000,000$ | $\text{val} / 1000.0$ | `crack_width_mm` | $\text{mm}$ (millimetres) |
| `battery_mv` | $0 \dots 30000$ | $\text{val} / 1000.0$ | `battery_voltage_v` | $\text{V}$ (Volts) |
| `battery_mv` (SoC)| $3000 \dots 4200$ (Li-ion) | $\text{clamp}\left(\frac{\text{val} - 3200}{4150 - 3200} \times 100, 0, 100\right)$ | `battery_pct` | $\%$ |

---

## 5. JSON Telemetry Schemas & Ingestion Contracts

MineGuard-AI accepts telemetry in two formats:
1. **Canonical Gateway Structured Format (`GatewayMessagePayload`)**: Preferred format for industrial gateways with explicit hardware metadata.
2. **Flat Ingestion Format (`TelemetryIngest`)**: Direct, flat format for simplified microcontroller implementations.

### 5.1 Canonical Gateway Structured Format
```json
{
  "gateway_id": "GW-BENCH-NORTH-01",
  "node_id": "NODE-PIT-NORTH-01",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "sequence_number": 1042,
  "timestamp": "2026-10-28T08:30:00.000000Z",
  "firmware_version": "v1.2.0",
  "units": {
    "displacement": "mm",
    "tilt": "deg",
    "velocity": "mm/hr",
    "vibration": "m/s2",
    "temperature": "C",
    "crack_width": "mm",
    "battery_voltage": "V",
    "battery": "%"
  },
  "readings": {
    "displacement_mm": 14.850,
    "tilt_x_deg": 1.25,
    "tilt_y_deg": -0.84,
    "vibration_rms_ms2": 0.15,
    "peak_acceleration_ms2": 0.45,
    "temperature_c": 28.5,
    "crack_width_mm": 2.45,
    "battery_voltage_v": 3.92,
    "battery_pct": 86.5
  },
  "quality": {
    "sensor_status": "nominal",
    "rssi_dbm": -74,
    "snr_db": 9.5,
    "is_physically_bounded": true,
    "has_missing_data": false
  },
  "raw_metadata": {
    "mesh_hops": 2,
    "radio_frequency_mhz": 866.5,
    "spiffs_buffer_depth": 0
  }
}
```

### 5.2 Uninstrumented Channel Example (Strict Missing-Data Policy)
If a node lacks a crack meter or vibration sensor, or if a transducer cable is cut, the channel MUST be submitted as `null`. It must **NEVER** be submitted as `0.0`.
```json
{
  "gateway_id": "GW-BENCH-NORTH-01",
  "node_id": "NODE-SLOPE-WEST-05",
  "event_id": "a1b2c3d4-e5f6-47a8-b9c0-112233445566",
  "sequence_number": 512,
  "timestamp": "2026-10-28T08:30:05.000000Z",
  "firmware_version": "v1.2.0",
  "readings": {
    "displacement_mm": null,
    "tilt_x_deg": 2.15,
    "tilt_y_deg": 1.05,
    "vibration_rms_ms2": null,
    "peak_acceleration_ms2": null,
    "temperature_c": 29.1,
    "crack_width_mm": null,
    "battery_voltage_v": 3.88,
    "battery_pct": 82.0
  },
  "quality": {
    "sensor_status": "degraded",
    "rssi_dbm": -88,
    "snr_db": 4.2,
    "is_physically_bounded": true,
    "has_missing_data": true
  }
}
```

### 5.3 Store-and-Forward Replay Batch Envelope (`GatewayReplayPayload`)
When the gateway recovers network connectivity, it uploads stored entries as a batch:
```json
{
  "gateway_id": "GW-BENCH-NORTH-01",
  "batch_id": "8f3b2a1c-9944-482b-b6d3-982347510294",
  "transmitted_at": "2026-10-28T09:00:00.000000Z",
  "buffered_count": 2,
  "is_replay": true,
  "records": [
    {
      "node_id": "NODE-PIT-NORTH-01",
      "event_id": "6a7b8c9d-1122-3344-5566-778899aabbcc",
      "sequence_number": 1043,
      "timestamp": "2026-10-28T08:35:00.000000Z",
      "readings": {
        "displacement_mm": 15.200,
        "tilt_x_deg": 1.30,
        "tilt_y_deg": -0.85,
        "temperature_c": 28.6,
        "battery_pct": 86.0
      }
    },
    {
      "node_id": "NODE-PIT-NORTH-01",
      "event_id": "7b8c9d0e-2233-4455-6677-8899aabbccdd",
      "sequence_number": 1044,
      "timestamp": "2026-10-28T08:40:00.000000Z",
      "readings": {
        "displacement_mm": 15.650,
        "tilt_x_deg": 1.35,
        "tilt_y_deg": -0.86,
        "temperature_c": 28.7,
        "battery_pct": 85.8
      }
    }
  ]
}
```

---

## 6. Node Identifiers & Monotonic Sequence Numbering

### 6.1 Node Identifier Formatting Rules
All `node_id` strings must strictly satisfy regular expression `^[A-Za-z0-9_\-\.]{2,64}$`:
- **Length**: Minimum 2 characters, maximum 64 characters.
- **Allowed Characters**: Uppercase letters `A-Z`, lowercase letters `a-z`, numerals `0-9`, hyphens `-`, underscores `_`, periods `.`.
- **Naming Pattern**: `NODE-[BENCH/ZONE]-[ORIENTATION]-[NUMBER]`, e.g., `NODE-PIT-NORTH-01`, `NODE-BENCH-EAST-04`, `NODE-EXT-SOUTH-02`.

### 6.2 Sequence Number Lifecycle
- **Width**: 32-bit unsigned integer ($0 \dots 4,294,967,295$).
- **Monotonicity**: Each transmitted packet increments the sequence number by exactly 1.
- **Persistence Across Deep Sleep**: Firmware MUST store the sequence counter in RTC Slow Memory (`RTC_DATA_ATTR` on ESP32) or Non-Volatile Storage (NVS Flash).
- **Cold Reboot Recovery**: On battery replacement or brownout reset, firmware must read the last persisted sequence number from NVS, add 100, and resume to prevent accidental sequence collisions.

### 6.3 Event ID (UUIDv4)
Firmware or gateway software must generate a standard RFC 4122 Version 4 UUID for `event_id` (e.g. `c7b3d8a1-4321-4f1b-8712-4217bb654321`). If a lightweight microcontroller submits telemetry without `event_id`, the backend automatically generates a server UUID, but client-side generation is strongly recommended to enable end-to-end deduplication across network retries.

---

## 7. Permissible Measurement Ranges & Anti-False-Safe Validation

MineGuard-AI performs boundary validation against physical extremes:

| Measurement Field | Minimum | Maximum | Backend Validation Action |
|---|---|---|---|
| `displacement_mm` | $-5000.0$ | $+5000.0$ | Reject if exceeded; out of bounds indicates transducer mechanical slippage |
| `tilt_x_deg`, `tilt_y_deg` | $-90.0$ | $+90.0$ | Clamp / reject; sensor upside-down or mechanically decoupled |
| `vibration_rms_ms2` | $0.0$ | $200.0$ | Reject negative; values $> 200\text{ m/s}^2$ indicate transducer saturation |
| `peak_acceleration_ms2` | $0.0$ | $500.0$ | Reject negative |
| `temperature_c` | $-50.0$ | $+100.0$ | Reject if exceeded; indicates thermistor open/short circuit |
| `crack_width_mm` | $0.0$ | $1000.0$ | Reject negative |
| `battery_voltage_v` | $0.0$ | $30.0$ | Reject negative |
| `battery_pct` | $0.0$ | $100.0$ | Reject if $< 0.0$ or $> 100.0$ |

> [!IMPORTANT]
> **Anti-False-Safe Rule**:
> If both `displacement_mm` and `vector_tilt_deg` are `null`, or if the time elapsed since the last observation exceeds `STALE_DATA_TIMEOUT_SEC` (default 120s), the backend forces the node's risk status to `DATA_UNRELIABLE`. Under no circumstances will dropped telemetry result in a false "SAFE" green status.

---

## 8. Ingestion Protocol Examples (REST & MQTT)

### 8.1 REST Ingestion Examples

#### A. Single Telemetry Ingestion (`POST /api/v1/telemetry`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/telemetry" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "NODE-PIT-NORTH-01",
    "event_id": "e83e9b11-5827-4c4f-a9cb-826359174820",
    "sequence_number": 1050,
    "timestamp": "2026-10-28T08:45:00.000Z",
    "displacement_mm": 16.42,
    "tilt_x_deg": 1.45,
    "tilt_y_deg": -0.88,
    "vibration_rms_ms2": 0.12,
    "temperature_c": 28.9,
    "battery_pct": 85.0,
    "firmware_version": "v1.2.0"
  }'
```
**Expected Response**: `HTTP 201 Created`
```json
{
  "id": 1120,
  "event_id": "e83e9b11-5827-4c4f-a9cb-826359174820",
  "node_id": "NODE-PIT-NORTH-01",
  "sequence_number": 1050,
  "timestamp": "2026-10-28T08:45:00Z",
  "displacement_mm": 16.42,
  "vector_tilt_deg": 1.696,
  "velocity_mm_hr": 2.64,
  "acceleration_mm_hr2": 0.35,
  "data_source": "rest"
}
```

#### B. Gateway Store-and-Forward Replay (`POST /api/v1/telemetry/replay`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/telemetry/replay" \
  -H "Content-Type: application/json" \
  -d '{
    "gateway_id": "GW-BENCH-NORTH-01",
    "batch_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "transmitted_at": "2026-10-28T09:00:00.000Z",
    "buffered_count": 1,
    "is_replay": true,
    "records": [
      {
        "node_id": "NODE-PIT-NORTH-01",
        "event_id": "e83e9b11-5827-4c4f-a9cb-826359174820",
        "sequence_number": 1050,
        "timestamp": "2026-10-28T08:45:00.000Z",
        "readings": {
          "displacement_mm": 16.42
        }
      }
    ]
  }'
```
**Expected Response**: `HTTP 200 OK`
```json
{
  "gateway_id": "GW-BENCH-NORTH-01",
  "batch_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "received_count": 1,
  "accepted_count": 0,
  "duplicates_skipped": 1,
  "rejected_count": 0,
  "status": "COMPLETED",
  "errors": []
}
```

### 8.2 MQTT Ingestion Examples

The edge gateway connects to the MQTT broker using the credentials configured in `.env` (`MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`).

#### A. Publish Single Telemetry via Mosquitto CLI
```bash
# Publish to live gateway ingestion topic
mosquitto_pub -h localhost -p 1883 -q 1 \
  -t "mineguard/gateways/GW-BENCH-NORTH-01/telemetry" \
  -m '{
    "gateway_id": "GW-BENCH-NORTH-01",
    "node_id": "NODE-PIT-NORTH-01",
    "event_id": "d1e2f3a4-b5c6-47e8-9900-aabbccddeeff",
    "sequence_number": 1051,
    "timestamp": "2026-10-28T08:50:00Z",
    "readings": {
      "displacement_mm": 16.65,
      "tilt_x_deg": 1.48,
      "tilt_y_deg": -0.89,
      "temperature_c": 29.0,
      "battery_pct": 84.8
    }
  }'
```

#### B. Publish Replay Batch via Mosquitto CLI
```bash
mosquitto_pub -h localhost -p 1883 -q 1 \
  -t "mineguard/gateways/GW-BENCH-NORTH-01/replay" \
  -m '{
    "gateway_id": "GW-BENCH-NORTH-01",
    "batch_id": "11223344-5566-7788-99aa-bbccddeeff00",
    "transmitted_at": "2026-10-28T09:05:00Z",
    "buffered_count": 1,
    "is_replay": true,
    "records": [
      {
        "node_id": "NODE-PIT-NORTH-01",
        "event_id": "99887766-5544-3322-1100-ffeeddccbbaa",
        "sequence_number": 1052,
        "timestamp": "2026-10-28T08:55:00Z",
        "readings": { "displacement_mm": 16.88 }
      }
    ]
  }'
```

---

## 9. Gateway Reconnection & Flash Buffering Behavior

### 9.1 Non-Volatile Storage (Ring-Buffer Architecture)
When backhaul connectivity fails:
1. **Partition Setup**: Gateway allocates a dedicated SPI Flash partition (`storage`, 4 MB LittleFS) or industrial microSD card (`/data/ringbuf`).
2. **Binary Buffer File**: Telemetry entries are appended sequentially as 48-byte records:
   - `[Timestamp: 8B uint64_t]` + `[EventUUID: 16B]` + `[BinaryFrame: 36B]` = 60 bytes per entry.
   - A 4 MB partition stores $\approx 65,000$ telemetry frames ($> 45\text{ days}$ of autonomous storage at 1 sample/minute for a 6-node cluster).
3. **Circular Wrap-Around Policy**: If partition reaches $95\%$ utilization, the oldest uploaded entries are deleted. If un-uploaded entries fill $98\%$ of storage, gateway sets `storage_overflow` flag in status telemetry rather than silently corrupting existing data.

### 9.2 Reconnection Backoff Algorithm
The gateway must implement truncated exponential backoff with random jitter to prevent server connection storms:
```
T_backoff = min(T_max, T_min * 2^attempt) + uniform(0, jitter)
```
- `T_min`: 1.0 second
- `T_max`: 60.0 seconds
- `jitter`: 0.0 to 1.5 seconds

### 9.3 Batch Upload Chunking
Upon reconnecting, the gateway MUST chunk stored records into batches of $N \le 100$ records per HTTP POST or MQTT packet. Gateways must **not** attempt to upload thousands of buffered records in a single payload, as this risks socket timeouts and heap allocation failure on embedded microcontrollers.

---

## 10. Duplicate Handling & Replay Rules

### 10.1 Deduplication Keys
The MineGuard-AI backend deduplicates observations across two unique constraints:
1. **Primary Key**: `telemetry_records.event_id` (UUIDv4).
2. **Secondary Composite Key**: `(node_id, sequence_number)` pair.

### 10.2 Server Handling Behavior
- **Single REST Endpoint (`POST /telemetry`)**: Returns `HTTP 409 Conflict` with `detail: "Duplicate observation detected."`.
- **Replay Endpoint (`POST /telemetry/replay`)**: Detects existing duplicates, increments `duplicates_skipped` counter, and continues ingesting non-duplicate entries without transaction rollback.
- **Delayed Replay Alert Suppression**: If an observation has a timestamp older than `STALE_DATA_TIMEOUT_SEC` (default 120s), the measurement is stored and kinematics are updated, but active siren/alarm dispatch is suppressed.
- **Out-of-Order Kinematic Correction**: When historical records arrive out of chronological order, the backend automatically recalculates velocity ($v$) and acceleration ($a$) for the immediately following record using true measurement timestamps ($\Delta t$).

---

## 11. Firmware Responsibilities for ESP32 Nodes

### 11.1 What Firmware MUST Do
1. **Strict Power Gating**: De-energize transducers between measurement cycles using high-side P-channel MOSFET switches to achieve sleep currents $< 25\,\mu\text{A}$.
2. **Sensor Pre-Warm Delay**: Wait for transducer stabilization after power-on before ADC sampling (e.g. 50 ms for MEMS inclinometers, 20 ms for linear potentiometer excitation).
3. **Multi-Sample Averaging**: Take 16 consecutive ADC readings and compute trimmed median to eliminate electrical switching noise.
4. **Brownout & Watchdog Protection**: Enable hardware Watchdog Timer (WDT = 8.0s) and configure ESP32 Brownout Detector to Level 7 (2.8V).
5. **Non-Volatile Sequence Preservation**: Maintain sequence counters in RTC slow memory across deep sleep cycles.
6. **Explicit Channel Validity Reporting**: If a sensor fails to respond over I2C or returns ADC railed to $0\text{V}$ or $3.3\text{V}$ (open/short circuit), clear the corresponding bit in `status_flags` and report `null` in JSON.

### 11.2 What Firmware MUST NOT Do
1. **NEVER Synthesize Measurements**: If a transducer wire is broken, never output $0.0\text{ mm}$ or last-known-good values. Clear the channel validity flag.
2. **NEVER Claim Unverified Calibration**: Firmware must transmit raw converted physical values without applying proprietary unverified smoothing algorithms that mask sudden fault steps.
3. **NEVER Block Indefinitely**: Network communication calls must enforce a strict timeout (e.g. LoRa TX timeout: 2000 ms, Wi-Fi connect timeout: 5000 ms).

---

## 12. Hardware-in-the-Loop (HIL) Test Plan

To validate physical hardware prior to mine deployment, the engineering team must follow this 6-stage test procedure:

### Stage 1: Power & Electrical Bring-up
- **Equipment**: Digital multimeter, bench power supply (3.3V / 12V), oscilloscope / Joulescope.
- **Steps**:
  1. Measure quiescent deep-sleep current of sensor node ($I_{\text{sleep}} < 25\,\mu\text{A}$).
  2. Verify transducer rail turns off completely during sleep ($V_{\text{rail}} < 50\,\text{mV}$).
  3. Verify battery rail voltage divider calibration: compare ADC reading with calibrated multimeter across $3.0\text{V} - 4.2\text{V}$ range (error $< \pm 20\,\text{mV}$).
- **Pass Criteria**: Sleep current $< 30\,\mu\text{A}$; rail turns off cleanly; voltage measurement accurate within $\pm 1\%$.

### Stage 2: Framing & Binary Serialization Verification
- **Equipment**: ESP32 development board connected via USB-UART to Linux workstation.
- **Steps**:
  1. Flash test firmware transmitting `LoRaTelemetryPacket_t` structs over UART.
  2. Run python test validator (`hil_firmware_validator.py`).
  3. Verify struct size is exactly 36 bytes.
  4. Verify CRC-8 calculation matches `backend/app/ingestion/message_validation.py`.
- **Pass Criteria**: Byte-for-byte alignment confirmed; zero padding offsets; CRC-8 verified.

### Stage 3: RF Range & Packet Error Rate (PER) Test
- **Equipment**: 1 Gateway + 2 Node prototypes, RF step attenuators (30 dB, 60 dB).
- **Steps**:
  1. Position nodes in line-of-sight test range (or with 60 dB attenuation).
  2. Transmit 1,000 packets per node at 5-second intervals.
  3. Record sequence numbers received at gateway.
  4. Calculate Packet Error Rate: $\text{PER} = (N_{\text{expected}} - N_{\text{received}}) / N_{\text{expected}}$.
- **Pass Criteria**: $\text{PER} < 2\%$ at $\text{RSSI} > -110\,\text{dBm}$; sequence numbers monotonic.

### Stage 4: Flash Ring-Buffer & Reconnect Stress Test
- **Equipment**: Gateway running under continuous telemetry reception.
- **Steps**:
  1. Disable gateway Ethernet / Wi-Fi backhaul for 60 minutes while nodes transmit 720 packets.
  2. Verify gateway stores all 720 packets to SPI Flash / SD card without dropping or crashing.
  3. Re-enable network backhaul.
  4. Verify gateway uploads buffered batches to `POST /api/v1/telemetry/replay`.
  5. Check backend database: verify all 720 records are present with exact timestamps.
  6. Re-trigger replay of the same batch to verify backend returns `duplicates_skipped: 720`.
- **Pass Criteria**: Zero packet loss; zero duplicate records in DB; duplicate rejection verified.

### Stage 5: Geotechnical Calibration Fixture Test
- **Equipment**: Precision micrometer linear translation stage ($0.01\,\text{mm}$ resolution) and rotary tilting index table ($0.05^\circ$ resolution).
- **Steps**:
  1. Mount physical extensometer to micrometer stage. Set initial baseline datum.
  2. Step displacement in calibrated increments: $+1.0\,\text{mm}, +5.0\,\text{mm}, +15.0\,\text{mm}, +35.0\,\text{mm}$.
  3. Step inclinometer angle: $+1.0^\circ, +2.5^\circ, +5.5^\circ$.
  4. Inspect MineGuard-AI GIS Dashboard:
     - Verify displacement graph displays exact micrometer values within $\pm 0.1\,\text{mm}$.
     - Verify $+15.0\,\text{mm}$ triggers `RULE_WARNING_DISPLACEMENT`.
     - Verify $+35.0\,\text{mm}$ triggers `RULE_CRITICAL_DISPLACEMENT`.
     - Verify $+5.5^\circ$ triggers `RULE_CRITICAL_TILT`.
- **Pass Criteria**: Measurement accuracy matches fixture within transducer tolerances; threshold rules trigger at exact calibrated values.

### Stage 6: Disconnection & Fault Injection Test
- **Equipment**: Operating sensor node on live test bench.
- **Steps**:
  1. Unplug the extensometer signal wire while the node is operating.
  2. Verify node firmware detects open-circuit and sets `DISP_VALID = 0`.
  3. Verify gateway forwards `displacement_mm: null`.
  4. Inspect MineGuard-AI dashboard:
     - Verify displacement is rendered as missing / dashed line.
     - Verify system raises `DATA_UNRELIABLE` warning.
     - Verify system DOES NOT display a false safe status.
- **Pass Criteria**: Transducer failure correctly detected; missing data policy enforced; false safe status prevented.

---

## 13. Traceability Matrix: Tested vs Simulated Interfaces

| Interface / Subsystem | Current Implementation Status | Testing Method Used | Field Hardware Validation Status |
|---|---|---|---|
| **REST Single Telemetry (`POST /telemetry`)** | Fully Implemented | Pytest + Live SQLite Integration Tests | Verified in software; ready for gateway target |
| **REST Batch Ingestion (`POST /telemetry/batch`)** | Fully Implemented | Pytest atomic rollback & partial ingest tests | Verified in software; ready for gateway target |
| **REST Store-and-Forward Replay (`POST /replay`)** | Fully Implemented | Pytest batch replay & deduplication tests | Verified in software; ready for gateway target |
| **MQTT Client Subscriber & Topic Routing** | Fully Implemented | Integration tests with simulated MQTT payloads | Verified in software; broker-ready |
| **Idempotent Deduplication Engine** | Fully Implemented | Pytest sequence & event ID conflict tests | Verified in software |
| **Kinematics Derivation ($v, a$)** | Fully Implemented | Synthetic calculus tests with irregular intervals | Verified with deterministic mathematical proof |
| **Geotechnical Threshold Rules** | Fully Implemented | Pytest rule suite across 8 critical conditions | Verified against mathematical criteria |
| **Isolation Forest Anomaly Detection** | Fully Implemented | Scikit-learn baseline training & test vectors | Verified in software |
| **Real-time WebSockets (`/ws/telemetry`)** | Fully Implemented | Pytest client WebSocket broadcast tests | Verified in software |
| **Reporting (CSV & PDF)** | Fully Implemented | Formula injection sanitization & PDF header tests | Verified in software |
| **Physical ESP32 Silicon** | Specified / Contracted | Firmware validator script (`hil_firmware_validator.py`) | **Awaiting physical microcontroller flashing** |
| **Semtech SX1262 LoRa RF Link** | Specified / Contracted | Emulated binary payload parser | **Awaiting physical RF transceiver bench test** |
| **Physical Rock Mass Sensors (LVDT, MEMS)** | Specified / Contracted | Synthetic scenario profiles | **Awaiting physical geotechnical calibration** |
| **Active Mine Concession Deployment** | **PROTOTYPE STAGE** | Laboratory & synthetic validation only | **Requires DGMS regulatory survey certification** |

---

## 14. Hardware Integration Reference Contacts & File Map

- **Schema Definition**: [`backend/app/schemas/telemetry.py`](file:///home/sreeramkramesh/Ai-mine/backend/app/schemas/telemetry.py)
- **Validation Engine**: [`backend/app/ingestion/message_validation.py`](file:///home/sreeramkramesh/Ai-mine/backend/app/ingestion/message_validation.py)
- **MQTT Gateway Service**: [`backend/app/ingestion/mqtt_client.py`](file:///home/sreeramkramesh/Ai-mine/backend/app/ingestion/mqtt_client.py)
- **Deduplication Engine**: [`backend/app/ingestion/deduplication.py`](file:///home/sreeramkramesh/Ai-mine/backend/app/ingestion/deduplication.py)
- **Hardware-in-the-Loop Validator**: [`simulator/hil_firmware_validator.py`](file:///home/sreeramkramesh/Ai-mine/simulator/hil_firmware_validator.py)
