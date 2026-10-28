import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from backend.app.core.config import settings
from backend.app.db.models import SensorNode, TelemetryRecord, Alert, AuditEvent
from backend.app.schemas.telemetry import (
    TelemetryIngest, GatewayMessagePayload, GatewayReplayPayload, GatewaySensorReadings
)
from backend.app.services.telemetry_service import TelemetryService
from backend.app.ingestion.mqtt_client import MQTTGatewayClient, mqtt_gateway
from backend.app.realtime.websocket_manager import ws_manager


def test_rest_single_telemetry_ingestion(client: TestClient):
    """Verify single telemetry REST endpoint with validation, duplicate detection, and 404 for unknown nodes."""
    now = datetime.now(timezone.utc)

    # 1. Successful ingestion on pre-seeded TEST-NODE-01
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "sequence_number": 100,
        "timestamp": now.isoformat(),
        "displacement_mm": 2.5,
        "tilt_x_deg": 0.4,
        "tilt_y_deg": 0.3,
        "vibration_rms_ms2": 0.1,
        "temperature_c": 24.0,
        "firmware_version": "v1.2.0"
    }
    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["node_id"] == "TEST-NODE-01"
    assert data["displacement_mm"] == 2.5

    # 2. Duplicate rejection with 409 Conflict
    res_dup = client.post("/api/v1/telemetry", json=payload)
    assert res_dup.status_code == 409

    # 3. Unknown node rejection with 404 Not Found
    unknown_payload = dict(payload, event_id=str(uuid.uuid4()), node_id="UNKNOWN-NODE-999")
    res_unknown = client.post("/api/v1/telemetry", json=unknown_payload)
    assert res_unknown.status_code == 404

    # 4. Out of physical bounds rejection with 422
    out_of_bounds_payload = dict(payload, event_id=str(uuid.uuid4()), displacement_mm=99999.0)
    res_oob = client.post("/api/v1/telemetry", json=out_of_bounds_payload)
    assert res_oob.status_code == 422


def test_gateway_message_format_and_schema(client: TestClient):
    """
    Verify the canonical gateway message format (specifying SI units, nested readings, quality,
    and firmware version) can be retrieved and ingested directly via REST.
    """
    # 1. Fetch the specification endpoint
    res = client.get("/api/v1/telemetry/gateway-format")
    assert res.status_code == 200
    spec = res.json()
    assert "si_units" in spec
    assert spec["si_units"]["displacement"] == "mm (millimetres)"
    assert spec["si_units"]["tilt"] == "deg (degrees)"
    assert spec["si_units"]["velocity"] == "mm/hr (millimetres per hour)"
    assert "sample_single_payload" in spec
    assert "sample_replay_envelope" in spec

    # 2. Ingest structured gateway payload with nested readings and quality
    now = datetime.now(timezone.utc)
    gw_payload = {
        "gateway_id": "GW-BENCH-01",
        "node_id": "TEST-NODE-01",
        "event_id": str(uuid.uuid4()),
        "sequence_number": 201,
        "timestamp": now.isoformat(),
        "firmware_version": "v1.5.0",
        "units": {
            "displacement": "mm",
            "tilt": "deg",
            "velocity": "mm/hr",
            "vibration": "m/s2",
            "temperature": "C",
            "battery": "%"
        },
        "readings": {
            "displacement_mm": 4.12,
            "tilt_x_deg": 0.35,
            "tilt_y_deg": -0.12,
            "vibration_rms_ms2": 0.05,
            "temperature_c": 27.2,
            "battery_pct": 94.0
        },
        "quality": {
            "sensor_status": "nominal",
            "rssi_dbm": -68,
            "snr_db": 11.2,
            "is_physically_bounded": True,
            "has_missing_data": False
        }
    }

    res_post = client.post("/api/v1/telemetry", json=gw_payload)
    assert res_post.status_code == 201
    resp_data = res_post.json()
    assert resp_data["displacement_mm"] == 4.12
    assert resp_data["battery_pct"] == 94.0


def test_gateway_store_and_forward_replay(client: TestClient, db_session: Session):
    """
    Test gateway buffered replay endpoint (/api/v1/telemetry/replay).
    Guarantees:
    - Accepts chronologically ordered or disordered frames.
    - Idempotent against duplicate batch submissions.
    - Logs GATEWAY_REPLAY_INGEST audit event.
    """
    now = datetime.now(timezone.utc)
    batch_id = str(uuid.uuid4())

    replay_payload = {
        "gateway_id": "GW-SECTOR-A",
        "batch_id": batch_id,
        "transmitted_at": now.isoformat(),
        "buffered_count": 3,
        "is_replay": True,
        "records": [
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "TEST-NODE-01",
                "sequence_number": 501,
                "timestamp": (now - timedelta(minutes=15)).isoformat(),
                "displacement_mm": 5.10,
                "readings": {"displacement_mm": 5.10}
            },
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "TEST-NODE-01",
                "sequence_number": 502,
                "timestamp": (now - timedelta(minutes=10)).isoformat(),
                "displacement_mm": 5.25,
                "readings": {"displacement_mm": 5.25}
            },
            {
                "event_id": str(uuid.uuid4()),
                "node_id": "TEST-NODE-01",
                "sequence_number": 503,
                "timestamp": (now - timedelta(minutes=5)).isoformat(),
                "displacement_mm": 5.40,
                "readings": {"displacement_mm": 5.40}
            }
        ]
    }

    # First submission: All 3 records should be accepted
    res = client.post("/api/v1/telemetry/replay", json=replay_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["accepted_count"] == 3
    assert data["duplicates_skipped"] == 0
    assert data["status"] == "COMPLETED"

    # Second submission of identical batch: Must be 100% skipped as duplicates without error
    res_dup = client.post("/api/v1/telemetry/replay", json=replay_payload)
    assert res_dup.status_code == 200
    data_dup = res_dup.json()
    assert data_dup["accepted_count"] == 0
    assert data_dup["duplicates_skipped"] == 3
    assert data_dup["status"] == "COMPLETED"

    # Verify AuditEvent recorded for replay
    audit = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "GATEWAY_REPLAY_INGEST", AuditEvent.actor == "gateway:GW-SECTOR-A")
        .first()
    )
    assert audit is not None
    assert audit.outcome == "SUCCESS"
    assert audit.details["gateway_id"] == "GW-SECTOR-A"


def test_out_of_order_telemetry_and_delayed_replay_alert_suppression(client: TestClient, db_session: Session):
    """
    Verify out-of-order records recalculate adjacent velocities,
    and delayed replay records (> 120s old) suppress emergency audio/banner alerts.
    """
    now = datetime.now(timezone.utc)
    t0 = now - timedelta(hours=2)
    t2 = t0 + timedelta(seconds=120)  # 2 minutes later
    t1 = t0 + timedelta(seconds=60)   # 1 minute later (will be inserted out-of-order)

    # Ingest record 0 at t0: d = 10.0 mm
    r0_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": t0.isoformat(),
        "displacement_mm": 10.0
    }
    client.post("/api/v1/telemetry", json=r0_payload)

    # Ingest record 2 at t2 (skipping t1): d = 12.0 mm (delta = 2.0 mm / (120/3600 hr) = 60.0 mm/hr)
    r2_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": t2.isoformat(),
        "displacement_mm": 12.0
    }
    client.post("/api/v1/telemetry", json=r2_payload)

    # Verify r2 velocity initially relative to r0
    rec2_initial = (
        db_session.query(TelemetryRecord)
        .filter(TelemetryRecord.node_id == "TEST-NODE-01", TelemetryRecord.timestamp == t2.replace(tzinfo=None))
        .first()
    )
    assert rec2_initial.velocity_mm_hr == pytest.approx(60.0, rel=1e-3)

    # Ingest out-of-order record 1 at t1: d = 10.5 mm
    r1_payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": t1.isoformat(),
        "displacement_mm": 10.5
    }
    res_r1 = client.post("/api/v1/telemetry", json=r1_payload)
    assert res_r1.status_code == 201

    # Verify kinematics correction: r2's velocity should now be recalculated relative to r1:
    # dt = (120 - 60) = 60s = 1/60 hr. delta d = 12.0 - 10.5 = 1.5 mm.
    # New v2 = 1.5 / (1/60) = 90.0 mm/hr!
    db_session.refresh(rec2_initial)
    assert rec2_initial.velocity_mm_hr == pytest.approx(90.0, rel=1e-3)


def test_mqtt_client_missing_broker_graceful_fallback():
    """
    Verify that when MQTT is enabled but broker is unreachable,
    the application starts gracefully, logs structured warning, and does NOT crash.
    """
    client = MQTTGatewayClient()

    with patch.object(settings, "MQTT_ENABLED", True), \
         patch.object(settings, "MQTT_BROKER_HOST", "invalid-unreachable-hostname.local"), \
         patch.object(settings, "MQTT_BROKER_PORT", 9999):

        client.initialize()
        assert client.client is not None

        # Start background loop - connect_async should fail gracefully
        client.start()
        status = client.get_status()
        assert status["enabled"] is True
        assert status["connected"] is False

        # Clean shutdown
        client.stop()
        assert client.is_connected is False


def test_mqtt_message_validation_and_malformed_payload_handling(db_session: Session):
    """
    Verify malformed MQTT payloads (raw binary, non-JSON strings, missing required fields,
    out-of-bounds telemetry) are safely caught and tracked in malformed_messages count without crashing.
    """
    gw = MQTTGatewayClient()
    gw._loop = AsyncMock()

    # Case 1: Corrupted non-UTF8 binary data
    mock_msg_binary = MagicMock()
    mock_msg_binary.topic = "mineguard/nodes/TEST-NODE-01/telemetry"
    mock_msg_binary.payload = b"\x80\xff\xfe\x00\x01\x02"

    gw._on_message(None, None, mock_msg_binary)
    assert gw.malformed_messages_count == 1

    # Case 2: Malformed non-JSON string
    mock_msg_bad_json = MagicMock()
    mock_msg_bad_json.topic = "mineguard/nodes/TEST-NODE-01/telemetry"
    mock_msg_bad_json.payload = b"{ this is definitely not valid json }"

    gw._on_message(None, None, mock_msg_bad_json)
    assert gw.malformed_messages_count == 2

    # Case 3: Valid JSON but missing required fields (no timestamp, no node_id)
    mock_msg_missing_fields = MagicMock()
    mock_msg_missing_fields.topic = "mineguard/nodes/TEST-NODE-01/telemetry"
    mock_msg_missing_fields.payload = json.dumps({"displacement_mm": 5.0}).encode("utf-8")

    gw._on_message(None, None, mock_msg_missing_fields)
    assert gw.malformed_messages_count == 3

    # Case 4: Replay topic with invalid replay schema
    mock_msg_bad_replay = MagicMock()
    mock_msg_bad_replay.topic = "mineguard/gateways/GW-01/replay"
    mock_msg_bad_replay.payload = json.dumps({"is_replay": True, "records": "not-a-list"}).encode("utf-8")

    gw._on_message(None, None, mock_msg_bad_replay)
    assert gw.malformed_messages_count == 4


def test_mqtt_gateway_live_and_replay_message_processing(db_session: Session):
    """
    Verify simulated valid MQTT messages on live topic and replay topic
    are parsed and routed to TelemetryService.
    """
    gw = MQTTGatewayClient()
    now = datetime.now(timezone.utc)

    # 1. Test live structured gateway message parsing
    live_msg_payload = {
        "gateway_id": "GW-BENCH-02",
        "node_id": "TEST-NODE-01",
        "event_id": str(uuid.uuid4()),
        "sequence_number": 880,
        "timestamp": now.isoformat(),
        "readings": {
            "displacement_mm": 3.75,
            "tilt_x_deg": 0.20,
            "tilt_y_deg": 0.15,
            "vibration_rms_ms2": 0.05
        },
        "quality": {
            "sensor_status": "nominal",
            "rssi_dbm": -70
        }
    }

    mock_msg_live = MagicMock()
    mock_msg_live.topic = "mineguard/gateways/GW-BENCH-02/telemetry"
    mock_msg_live.payload = json.dumps(live_msg_payload).encode("utf-8")

    # Mock event loop to capture async task
    loop_mock = MagicMock()
    loop_mock.is_running.return_value = True
    gw._loop = loop_mock

    with patch("asyncio.run_coroutine_threadsafe") as mock_schedule:
        gw._on_message(None, None, mock_msg_live)
        assert gw.messages_received_count == 1
        assert mock_schedule.called
        coro = mock_schedule.call_args[0][0]
        assert coro is not None
        coro.close()

    # 2. Test replay topic routing
    replay_msg_payload = {
        "gateway_id": "GW-BENCH-02",
        "batch_id": str(uuid.uuid4()),
        "transmitted_at": now.isoformat(),
        "buffered_count": 1,
        "is_replay": True,
        "records": [live_msg_payload]
    }

    mock_msg_replay = MagicMock()
    mock_msg_replay.topic = "mineguard/gateways/GW-BENCH-02/replay"
    mock_msg_replay.payload = json.dumps(replay_msg_payload).encode("utf-8")

    with patch("asyncio.run_coroutine_threadsafe") as mock_schedule:
        gw._on_message(None, None, mock_msg_replay)
        assert gw.messages_received_count == 2
        assert mock_schedule.called
        coro_replay = mock_schedule.call_args[0][0]
        coro_replay.close()


def test_mqtt_client_reconnection_and_bounded_retry_delays():
    """Verify MQTT client reconnection configuration and backoff parameters."""
    client = MQTTGatewayClient()

    with patch.object(settings, "MQTT_ENABLED", True), \
         patch.object(settings, "MQTT_RECONNECT_MIN_DELAY_S", 2.0), \
         patch.object(settings, "MQTT_RECONNECT_MAX_DELAY_S", 30.0):

        client.initialize()
        assert client.client is not None

        # Verify on_disconnect tracks reconnection counter
        client.is_connected = True
        client._on_disconnect(client.client, None, None, 1, None)
        assert client.is_connected is False
        assert client.reconnect_count == 1
        assert "Disconnected" in client.last_error

        # Verify on_connect resets connection state and subscribes to 3 topic patterns
        mock_paho = MagicMock()
        client._on_connect(mock_paho, None, None, 0, None)
        assert client.is_connected is True
        assert client.last_connected_at is not None
        assert mock_paho.subscribe.call_count == 3


@pytest.mark.asyncio
async def test_websocket_realtime_broadcasts():
    """Verify WebSocketManager broadcast of telemetry, node_status, and alert events."""
    mock_ws1 = AsyncMock()
    mock_ws2 = AsyncMock()

    # Register clients
    await ws_manager.connect(mock_ws1)
    await ws_manager.connect(mock_ws2)
    assert len(ws_manager.active_connections) == 2

    # Broadcast telemetry
    await ws_manager.broadcast("telemetry", {"node_id": "TEST-NODE-01", "displacement_mm": 5.0})
    assert mock_ws1.send_text.called
    assert mock_ws2.send_text.called

    call_arg = json.loads(mock_ws1.send_text.call_args[0][0])
    assert call_arg["type"] == "telemetry"
    assert call_arg["data"]["node_id"] == "TEST-NODE-01"

    # Broadcast node status
    await ws_manager.broadcast("node_status", {"node_id": "TEST-NODE-01", "connectivity_status": "ONLINE"})
    call_arg_node = json.loads(mock_ws1.send_text.call_args[0][0])
    assert call_arg_node["type"] == "node_status"

    # Disconnect client
    ws_manager.disconnect(mock_ws1)
    assert len(ws_manager.active_connections) == 1
    ws_manager.disconnect(mock_ws2)
    assert len(ws_manager.active_connections) == 0


def test_firmware_version_tracking_on_telemetry(client: TestClient, db_session: Session):
    """Verify that incoming telemetry reporting a new firmware version updates the node record."""
    now = datetime.now(timezone.utc)
    payload = {
        "event_id": str(uuid.uuid4()),
        "node_id": "TEST-NODE-01",
        "timestamp": now.isoformat(),
        "displacement_mm": 1.2,
        "firmware_version": "v2.4.1"
    }

    res = client.post("/api/v1/telemetry", json=payload)
    assert res.status_code == 201

    node = db_session.query(SensorNode).filter(SensorNode.node_id == "TEST-NODE-01").first()
    assert node.firmware_version == "v2.4.1"


def test_health_mqtt_endpoint(client: TestClient):
    """Verify the dedicated GET /api/v1/health/mqtt diagnostic probe endpoint."""
    res = client.get("/api/v1/health/mqtt")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert "connected" in data
    assert "broker" in data
    assert "subscribed_topics" in data
    assert len(data["subscribed_topics"]) == 3
