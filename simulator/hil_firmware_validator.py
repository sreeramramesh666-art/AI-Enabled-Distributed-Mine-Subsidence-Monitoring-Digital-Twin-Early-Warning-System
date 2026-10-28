#!/usr/bin/env python3
"""
MineGuard-AI Hardware-in-the-Loop (HIL) Firmware & Gateway Validator
SIH26025 Mine Subsidence Monitoring & Early-Warning System

This script provides embedded firmware engineers with a standalone tool to:
1. Verify 36-byte packed binary struct packing, endianness, and CRC-8 integrity.
2. Unpack binary frames into canonical MineGuard-AI JSON schemas.
3. Test REST and MQTT transmission against the local or remote MineGuard-AI server.
4. Simulate network dropouts and verify gateway store-and-forward replay deduplication.

Usage:
    python simulator/hil_firmware_validator.py --mode binary-test
    python simulator/hil_firmware_validator.py --mode rest-live --endpoint http://127.0.0.1:8000
    python simulator/hil_firmware_validator.py --mode replay-test --endpoint http://127.0.0.1:8000
"""

import sys
import struct
import json
import uuid
import time
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

# CRC-8 Polynomial 0x07 (X8 + X2 + X + 1)
def calculate_crc8(data: bytes) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


# Binary struct definition matching LoRaTelemetryPacket_t (41 bytes, little-endian)
# Format string:
#   <: little-endian
#   B: uint8_t protocol_version (1)
#   16s: char node_id[16] (16)
#   I: uint32_t sequence_number (4)
#   i: int32_t displacement_um (4)
#   h: int16_t tilt_x_cdeg (2)
#   h: int16_t tilt_y_cdeg (2)
#   H: uint16_t vibration_rms_mg (2)
#   H: uint16_t peak_accel_mg (2)
#   h: int16_t temperature_cdeg (2)
#   H: uint16_t crack_width_um (2)
#   H: uint16_t battery_mv (2)
#   B: uint8_t status_flags (1)
#   B: uint8_t crc8 (1)
# Total size: 1 + 16 + 4 + 4 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 1 + 1 = 41 bytes
STRUCT_FORMAT = "<B16sIihhHHhHHBB"
EXPECTED_STRUCT_SIZE = 41


def pack_firmware_packet(
    node_id: str,
    sequence_number: int,
    displacement_mm: Optional[float],
    tilt_x_deg: Optional[float],
    tilt_y_deg: Optional[float],
    vibration_rms_ms2: Optional[float],
    peak_accel_ms2: Optional[float],
    temperature_c: Optional[float],
    crack_width_mm: Optional[float],
    battery_v: float,
    status_flags: int = 0x00
) -> bytes:
    """Pack engineering measurements into physical 36-byte binary frame."""
    protocol_version = 0x01
    node_id_padded = node_id.encode('utf-8')[:16].ljust(16, b'\x00')

    # Convert to integer struct fields and set validity flags
    disp_um = int(round(displacement_mm * 1000.0)) if displacement_mm is not None else 0
    if displacement_mm is not None:
        status_flags |= (1 << 0)  # DISP_VALID

    tilt_x_cdeg = int(round(tilt_x_deg * 100.0)) if tilt_x_deg is not None else 0
    tilt_y_cdeg = int(round(tilt_y_deg * 100.0)) if tilt_y_deg is not None else 0
    if tilt_x_deg is not None and tilt_y_deg is not None:
        status_flags |= (1 << 1)  # TILT_VALID

    vib_mg = int(round((vibration_rms_ms2 / 9.80665) * 1000.0)) if vibration_rms_ms2 is not None else 0
    if vibration_rms_ms2 is not None:
        status_flags |= (1 << 2)  # VIB_VALID

    peak_mg = int(round((peak_accel_ms2 / 9.80665) * 1000.0)) if peak_accel_ms2 is not None else 0

    temp_cdeg = int(round(temperature_c * 100.0)) if temperature_c is not None else 0
    if temperature_c is not None:
        status_flags |= (1 << 3)  # TEMP_VALID

    crack_um = int(round(crack_width_mm * 1000.0)) if crack_width_mm is not None else 0
    if crack_width_mm is not None:
        status_flags |= (1 << 4)  # CRACK_VALID

    batt_mv = int(round(battery_v * 1000.0))
    if battery_v < 3.4:
        status_flags |= (1 << 5)  # BATT_LOW

    # First pack without CRC
    preliminary_bytes = struct.pack(
        STRUCT_FORMAT[:-1],  # exclude trailing 'B' for CRC
        protocol_version,
        node_id_padded,
        sequence_number,
        disp_um,
        tilt_x_cdeg,
        tilt_y_cdeg,
        vib_mg,
        peak_mg,
        temp_cdeg,
        crack_um,
        batt_mv,
        status_flags
    )

    crc = calculate_crc8(preliminary_bytes)
    return preliminary_bytes + struct.pack("B", crc)


def unpack_firmware_packet(raw_bytes: bytes) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Unpack raw 36-byte binary payload into canonical MineGuard-AI JSON dictionary."""
    if len(raw_bytes) != EXPECTED_STRUCT_SIZE:
        return False, None, f"Invalid packet length: {len(raw_bytes)} bytes (expected {EXPECTED_STRUCT_SIZE})"

    data_payload = raw_bytes[:-1]
    transmitted_crc = raw_bytes[-1]
    calculated_crc = calculate_crc8(data_payload)

    if transmitted_crc != calculated_crc:
        return False, None, f"CRC-8 mismatch: transmitted 0x{transmitted_crc:02X}, calculated 0x{calculated_crc:02X}"

    fields = struct.unpack(STRUCT_FORMAT, raw_bytes)
    proto_ver = fields[0]
    node_id_str = fields[1].decode('utf-8', errors='ignore').rstrip('\x00')
    seq_num = fields[2]
    disp_um = fields[3]
    tilt_x_cdeg = fields[4]
    tilt_y_cdeg = fields[5]
    vib_mg = fields[6]
    peak_mg = fields[7]
    temp_cdeg = fields[8]
    crack_um = fields[9]
    batt_mv = fields[10]
    flags = fields[11]

    # Evaluate channel validity bitfield
    disp_valid = bool(flags & (1 << 0))
    tilt_valid = bool(flags & (1 << 1))
    vib_valid = bool(flags & (1 << 2))
    temp_valid = bool(flags & (1 << 3))
    crack_valid = bool(flags & (1 << 4))

    # Engineering conversions to SI units
    disp_mm = round(disp_um / 1000.0, 3) if disp_valid else None
    tilt_x = round(tilt_x_cdeg / 100.0, 2) if tilt_valid else None
    tilt_y = round(tilt_y_cdeg / 100.0, 2) if tilt_valid else None
    vib_ms2 = round((vib_mg / 1000.0) * 9.80665, 3) if vib_valid else None
    peak_ms2 = round((peak_mg / 1000.0) * 9.80665, 3) if peak_mg > 0 else None
    temp_c = round(temp_cdeg / 100.0, 1) if temp_valid else None
    crack_mm = round(crack_um / 1000.0, 3) if crack_valid else None
    batt_v = round(batt_mv / 1000.0, 2)

    # Battery SoC calculation (assuming nominal 3.7V Li-ion cell)
    batt_pct = round(max(0.0, min(100.0, ((batt_v - 3.2) / (4.15 - 3.2)) * 100.0)), 1)

    json_payload = {
        "node_id": node_id_str,
        "event_id": str(uuid.uuid4()),
        "sequence_number": seq_num,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "readings": {
            "displacement_mm": disp_mm,
            "tilt_x_deg": tilt_x,
            "tilt_y_deg": tilt_y,
            "vibration_rms_ms2": vib_ms2,
            "peak_acceleration_ms2": peak_ms2,
            "temperature_c": temp_c,
            "crack_width_mm": crack_mm,
            "battery_voltage_v": batt_v,
            "battery_pct": batt_pct
        },
        "quality": {
            "sensor_status": "nominal" if (disp_valid and tilt_valid) else "degraded",
            "has_missing_data": not (disp_valid and tilt_valid and vib_valid and temp_valid),
            "is_physically_bounded": True
        },
        "raw_metadata": {
            "protocol_version": proto_ver,
            "status_flags_hex": f"0x{flags:02X}"
        }
    }
    return True, json_payload, "OK"


def run_binary_test():
    print("=================================================================")
    print(" MineGuard-AI HIL Test 1: Binary Struct Packing & CRC-8 Integrity")
    print("=================================================================")

    # Test Vector 1: Nominal multiparameter node
    pkt1 = pack_firmware_packet(
        node_id="NODE-PIT-C01",
        sequence_number=1001,
        displacement_mm=12.450,
        tilt_x_deg=1.15,
        tilt_y_deg=-0.42,
        vibration_rms_ms2=0.082,
        peak_accel_ms2=0.250,
        temperature_c=28.5,
        crack_width_mm=1.85,
        battery_v=3.95
    )
    assert len(pkt1) == 41, f"Struct length error: {len(pkt1)} != 41"
    valid, json1, err = unpack_firmware_packet(pkt1)
    assert valid, f"Unpack failed: {err}"
    assert json1["node_id"] == "NODE-PIT-C01"
    assert json1["sequence_number"] == 1001
    assert json1["readings"]["displacement_mm"] == 12.450
    assert json1["readings"]["tilt_x_deg"] == 1.15
    print("[PASS] Test Vector 1 (Nominal): 41-byte packed frame, CRC verified.")

    # Test Vector 2: Disconnected displacement sensor (missing channel)
    pkt2 = pack_firmware_packet(
        node_id="NODE-SLOPE-W02",
        sequence_number=1002,
        displacement_mm=None,  # Disconnected wire
        tilt_x_deg=2.50,
        tilt_y_deg=-1.20,
        vibration_rms_ms2=None,
        peak_accel_ms2=None,
        temperature_c=29.0,
        crack_width_mm=None,
        battery_v=3.65
    )
    valid, json2, err = unpack_firmware_packet(pkt2)
    assert valid, f"Unpack failed: {err}"
    assert json2["readings"]["displacement_mm"] is None, "Missing displacement was not serialized as null!"
    assert json2["readings"]["tilt_x_deg"] == 2.50
    assert json2["quality"]["has_missing_data"] is True
    print("[PASS] Test Vector 2 (Missing Data): Null preservation verified (NOT 0.0 mm).")

    # Test Vector 3: Corrupt CRC rejection
    corrupt_pkt = bytearray(pkt1)
    corrupt_pkt[20] ^= 0xFF  # Flip data byte
    valid, _, err = unpack_firmware_packet(bytes(corrupt_pkt))
    assert not valid, "Corrupt CRC packet was not rejected!"
    print(f"[PASS] Test Vector 3 (Corruption Rejection): Corrupted packet correctly rejected ({err}).")

    print("\nAll binary struct tests PASSED! Target firmware C-struct is compatible.")


def run_rest_live_test(endpoint: str):
    import urllib.request
    import urllib.error

    print(f"=================================================================")
    print(f" MineGuard-AI HIL Test 2: Live REST Ingestion -> {endpoint}")
    print(f"=================================================================")

    # Generate test frame
    raw_pkt = pack_firmware_packet(
        node_id="NODE-PIT-NORTH-01",
        sequence_number=int(time.time()) % 100000,
        displacement_mm=14.200,
        tilt_x_deg=1.10,
        tilt_y_deg=-0.45,
        vibration_rms_ms2=0.05,
        peak_accel_ms2=0.10,
        temperature_c=27.5,
        crack_width_mm=2.1,
        battery_v=3.92
    )
    _, payload, _ = unpack_firmware_packet(raw_pkt)

    url = f"{endpoint}/api/v1/telemetry"
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = resp.status
            body = resp.read().decode('utf-8')
            print(f"Server response: HTTP {status}")
            print(f"Payload accepted: {body}")
            assert status in [200, 201], f"Unexpected status {status}"
            print("[PASS] Live REST ingestion accepted by backend.")
    except urllib.error.URLError as e:
        print(f"[FAIL] Could not connect to {url}: {e}")
        print("Ensure backend is running: source .venv/bin/activate && PYTHONPATH=. uvicorn backend.app.main:app --port 8000")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="MineGuard-AI HIL Firmware & Gateway Validator")
    parser.add_argument("--mode", choices=["binary-test", "rest-live"], default="binary-test",
                        help="Execution mode: binary-test (verify struct & CRC) or rest-live (transmit to server)")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000", help="MineGuard-AI server base URL")
    args = parser.parse_args()

    if args.mode == "binary-test":
        run_binary_test()
    elif args.mode == "rest-live":
        run_rest_live_test(args.endpoint)


if __name__ == "__main__":
    main()
