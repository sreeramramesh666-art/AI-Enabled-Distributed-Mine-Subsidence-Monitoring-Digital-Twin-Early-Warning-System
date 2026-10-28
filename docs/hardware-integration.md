# MineGuard-AI Hardware Integration Guide & Gateway Architecture

## 1. Safety Notice & Hardware Development Disclaimer

> [!WARNING]
> **Prototype & Emulation Scope**:
> Physical ESP32 microcontrollers, LoRa RF transceivers, and mesh network firmware have **not been physically deployed or bench-tested** in this development phase. 
> All gateway interfaces, packet structures, and buffering protocols specified herein represent the **precise interface contract** that embedded firmware developers must implement and validate on physical target silicon before field deployment in active mining operations.

---

## 2. 3-Tier Distributed Architecture

To monitor unstable open-pit highwalls and underground subsidence zones without relying on cellular towers at every bench, MineGuard-AI separates low-power radio propagation from high-level application messaging:

```
+-----------------------------------------------------------------------------------------+
|                                TIER 1: SENSOR NODES                                     |
|  - Microcontroller: ESP32-WROOM-32 / STM32L4 Ultra-Low Power                            |
|  - Sensors: Borehole extensometer (LVDT), dual-axis inclinometer (MEMS), geophone      |
|  - Physical Radio: Sub-GHz LoRa (865-867 MHz in India) or 2.4 GHz ESP-NOW Mesh         |
|  - Framing: Packed binary struct (41 bytes compact RF payload)                          |
+--------------------------------------------+--------------------------------------------+
                                             | RF Packets (Air Interface)
                                             v
+-----------------------------------------------------------------------------------------+
|                                TIER 2: EDGE WIRELESS GATEWAY                            |
|  - Hardware: Industrial ESP32-S3 / Linux Edge Computer (Raspberry Pi CM4)               |
|  - Storage: Non-volatile circular flash buffer (SPIFFS / eMMC / SD Card)                |
|  - Clock: DS3231 temperature-compensated hardware Real-Time Clock (RTC)                 |
|  - Functions:                                                                           |
|      1. Demodulates raw 41-byte binary RF frames from mesh/star topology                |
|      2. Assigns monotonically increasing gateway sequence numbers                       |
|      3. Serialises binary structs into MineGuard-AI JSON schemas                        |
|      4. Buffers telemetry in non-volatile ring-buffer during network outages             |
|      5. Streams live JSON via MQTT QoS 1 or HTTP POST                                   |
|      6. Replays buffered frames via POST /api/v1/telemetry/replay on link recovery      |
+--------------------------------------------+--------------------------------------------+
                                             | IP Network (Ethernet / WiFi / 4G LTE)
                                             v
+-----------------------------------------------------------------------------------------+
|                                TIER 3: MINEGUARD-AI CENTRAL SERVER                      |
|  - Ingestion: REST Ingestion Engine & Paho MQTT Gateway Subscriber                      |
|  - Real-Time Broadcast: WebSockets (/ws/telemetry)                                      |
|  - Storage: Local-First SQLite persistent database (SQLAlchemy ORM)                     |
|  - Analytics: Deterministic Kinematic Calculus (v, a), Geotechnical Rules, Isolation ML |
|  - Visualization: GIS Monitoring Dashboard & Alert Management Centre                    |
+-----------------------------------------------------------------------------------------+
```

> [!NOTE]
> For the exhaustive hardware integration specification and HIL test procedure, see [ESP32 Hardware Integration Specification](file:///home/sreeramkramesh/Ai-mine/docs/esp32-hardware-integration-spec.md).

---

## 3. Tier 1: Radio Mesh Binary Protocol (C Struct Layout)

Sensor nodes communicate with the gateway over LoRa or ESP-NOW using a packed, fixed-width binary frame to minimize airtime and conserve battery power:

```c
// Compact 41-byte binary payload transmitted by field nodes
typedef struct __attribute__((packed)) {
    uint8_t   protocol_version;    // 0x01
    char      node_id[16];         // Null-terminated string, e.g., "NODE-PIT-C01\0"
    uint32_t  sequence_number;    // Monotonically increasing counter (0 - 4,294,967,295)
    int32_t   displacement_um;    // Micro-metres (1 mm = 1000 um, signed)
    int16_t   tilt_x_cdeg;        // Centi-degrees (0.01 deg resolution, signed)
    int16_t   tilt_y_cdeg;        // Centi-degrees (0.01 deg resolution, signed)
    uint16_t  vibration_rms_mg;   // Milli-g (1 g ~ 9.80665 m/s2)
    int16_t   temperature_cdeg;   // Centi-Celsius (0.01 deg C resolution)
    uint16_t  battery_mv;         // Battery rail voltage in milli-volts (e.g. 3650 mV)
    uint8_t   status_flags;       // Bit 0: Tamper, Bit 1: Bounds error, Bit 2: Calibrating
    uint8_t   crc8;               // CRC-8 polynomial 0x07 error check
} LoRaTelemetryPacket_t;
```

---

## 4. Tier 2: Edge Gateway Buffering & Replay Engine

When wireless cellular/Ethernet coverage is lost at the mine bench:

### 4.1 Ring-Buffer Storage
- **Media**: Wear-levelled SPI Flash or automotive-grade SD card using a FAT/LittleFS circular ring buffer.
- **Entry Structure**: The gateway persists each unpacked packet with its RTC timestamp and a locally generated UUID `event_id`.
- **FIFO Eviction Policy**: If the ring buffer fills to 95% capacity (e.g. after weeks of outage), the oldest unacknowledged records are archived to a secondary backup partition rather than overwriting un-uploaded data.

### 4.2 Replay Protocol
1. **Connection Recovery**: Gateway monitors TCP socket to the MineGuard-AI backend or ping responses to the MQTT broker.
2. **Chunking**: Upon reconnection, the gateway reads buffered entries in batches of $N \le 100$ records (configurable up to `GATEWAY_REPLAY_MAX_BATCH_SIZE = 2000`).
3. **Payload Construction**: Gateway wraps the chunk into `GatewayReplayPayload`:
   ```json
   {
     "gateway_id": "GW-BENCH-C-01",
     "batch_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
     "transmitted_at": "2026-10-28T07:15:00Z",
     "buffered_count": 25,
     "is_replay": true,
     "records": [ ... ]
   }
   ```
4. **Transmission**: The gateway uploads to:
   - REST: `POST /api/v1/telemetry/replay`
   - MQTT: `mineguard/gateways/{gateway_id}/replay` (QoS 1)
5. **Idempotency Guarantee**: If network drops mid-replay and the gateway re-submits the batch, the backend detects pre-existing `event_id` or `(node_id, sequence_number)` pairs, skips them, and returns `duplicates_skipped: 25`, guaranteeing **zero duplicate rows or corrupted trends**.
6. **Alert Flood Suppression**: Historical replayed records (older than `STALE_DATA_TIMEOUT_SEC`) update trends and database audit events, but suppress audible alarms and live WebSocket push banners.

---

## 5. Physical Sensor Interfacing Guidelines

1. **Dual-Axis Inclinometer**:
   - Transducer: SCA103T / ADXL355 MEMS inclinometer.
   - Mounting: Non-magnetic stainless steel mounting bracket anchored into solid bedrock via non-shrink grout.
   - Axis Alignment: Axis X aligned parallel to the slope face (dip direction); Axis Y perpendicular (strike direction).

2. **Borehole Wire Extensometer**:
   - Transducer: 1000 mm stroke draw-wire sensor with optical rotary encoder or linear potentiometer.
   - Anchor: Grouted 15 metres below the active slip plane to ensure an invariant datum benchmark.
   - Casing: Telescopic PVC pipe protecting wire against rockfall impact.

3. **Power Subsystem**:
   - Battery: 12.8V 20Ah LiFePO4 battery pack with internal BMS.
   - Solar: 20W polycrystalline panel with MPPT solar charge controller.
   - Autonomy: Minimum 14 continuous days without sunlight (continuous monsoon cloud cover).
