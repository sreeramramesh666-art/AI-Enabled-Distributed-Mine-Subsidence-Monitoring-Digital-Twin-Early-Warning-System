import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import paho.mqtt.client as mqtt
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal
from backend.app.schemas.telemetry import (
    TelemetryIngest, GatewayMessagePayload, GatewayReplayPayload
)
from backend.app.services.telemetry_service import TelemetryService

logger = logging.getLogger("mineguard.mqtt")


class MQTTGatewayClient:
    """
    Industrial MQTT gateway subscriber for MineGuard-AI.
    Features:
    - Bounded exponential backoff on reconnection.
    - Subscription to individual node telemetry, gateway live streams, and store-and-forward replays.
    - Resilient JSON & Pydantic schema validation for malformed packet rejection.
    - Idempotent duplicate delivery prevention.
    - Graceful non-blocking shutdown.
    - Diagnostic statistics reporting.
    """

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Diagnostic telemetry counters
        self.messages_received_count: int = 0
        self.messages_processed_count: int = 0
        self.malformed_messages_count: int = 0
        self.duplicates_detected_count: int = 0
        self.reconnect_count: int = 0
        self.last_connected_at: Optional[str] = None
        self.last_message_at: Optional[str] = None
        self.last_error: Optional[str] = None

    def initialize(self):
        """Configure Paho MQTT 2.0 client with credentials, TLS, and bounded retry delays."""
        if not settings.MQTT_ENABLED:
            logger.info("MQTT client is disabled via configuration.")
            return

        try:
            client_id = getattr(settings, "MQTT_CLIENT_ID", "mineguard-central-backend")
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
                clean_session=True
            )

            # Bounded exponential retry backoff
            min_delay = int(getattr(settings, "MQTT_RECONNECT_MIN_DELAY_S", 1.0))
            max_delay = int(getattr(settings, "MQTT_RECONNECT_MAX_DELAY_S", 60.0))
            self.client.reconnect_delay_set(min_delay=min_delay, max_delay=max_delay)

            if settings.MQTT_USERNAME:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

            if settings.MQTT_TLS_ENABLED:
                context = ssl.create_default_context()
                self.client.tls_set_context(context)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            logger.info(
                f"MQTT client initialized for {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} "
                f"(Client ID: {client_id}, Reconnect: {min_delay}s-{max_delay}s)"
            )
        except Exception as e:
            logger.warning(f"MQTT client initialization error: {e}")
            self.client = None
            self.last_error = str(e)

    def start(self, loop=None):
        """Start non-blocking background connection loop with event loop integration."""
        if not settings.MQTT_ENABLED or not self.client:
            return

        if loop is not None:
            self._loop = loop
        else:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                try:
                    self._loop = asyncio.get_event_loop()
                except RuntimeError:
                    self._loop = None

        try:
            self.client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                settings.MQTT_KEEPALIVE
            )
            self.client.loop_start()
            logger.info(f"MQTT background loop started connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        except Exception as e:
            logger.warning(
                f"Could not connect to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} ({e}). "
                "Backend will operate in local REST/offline mode."
            )
            self.last_error = str(e)

    def stop(self):
        """Clean, bounded shutdown of MQTT connection and background network loop."""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.is_connected = False
                logger.info("MQTT client disconnected cleanly.")
            except Exception as e:
                logger.warning(f"Error during MQTT shutdown: {e}")

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            self.is_connected = True
            self.last_connected_at = datetime.now(timezone.utc).isoformat()
            self.last_error = None

            # Subscribe to all telemetry and replay topics
            topics = [
                (f"{settings.MQTT_TOPIC_PREFIX}/nodes/+/telemetry", 1),
                (f"{settings.MQTT_TOPIC_PREFIX}/gateways/+/telemetry", 1),
                (f"{settings.MQTT_TOPIC_PREFIX}/gateways/+/replay", 1),
            ]
            for topic, qos in topics:
                client.subscribe(topic, qos=qos)
                logger.info(f"MQTT subscribed to '{topic}' (QoS {qos}).")
        else:
            self.is_connected = False
            self.last_error = f"Connection refused with reason code: {reason_code}"
            logger.warning(f"MQTT connection refused (reason code: {reason_code}). Backing off...")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.is_connected = False
        self.reconnect_count += 1
        self.last_error = f"Disconnected (code {reason_code})"
        logger.warning(f"MQTT disconnected from broker (reason code: {reason_code}). Retrying with bounded backoff...")

    def _on_message(self, client, userdata, msg):
        """
        Handle incoming telemetry or replay frames from edge nodes or gateways.
        Guarantees:
        - Non-JSON or corrupt payloads are caught and logged without crashing the listener.
        - Pydantic schema validation failures are cleanly tracked as malformed messages.
        - Schedules asynchronous DB persistence onto the main application event loop.
        """
        self.messages_received_count += 1
        self.last_message_at = datetime.now(timezone.utc).isoformat()

        try:
            payload_str = msg.payload.decode("utf-8")
        except UnicodeDecodeError:
            self.malformed_messages_count += 1
            logger.warning(f"MQTT received non-UTF8 binary payload on topic '{msg.topic}' ({len(msg.payload)} bytes). Dropped.")
            return

        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as err:
            self.malformed_messages_count += 1
            logger.warning(f"MQTT received malformed JSON on topic '{msg.topic}': {err}. Dropped payload: {payload_str[:120]}")
            return

        # Check topic routing
        is_replay_topic = msg.topic.endswith("/replay") or (isinstance(data, dict) and data.get("is_replay") is True)

        if is_replay_topic:
            # Parse as GatewayReplayPayload
            try:
                replay_payload = GatewayReplayPayload(**data)
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._process_mqtt_replay(replay_payload),
                        self._loop
                    )
            except ValidationError as val_err:
                self.malformed_messages_count += 1
                logger.warning(f"MQTT replay payload validation error on '{msg.topic}': {val_err}")
            except Exception as e:
                self.malformed_messages_count += 1
                logger.error(f"MQTT replay message unexpected processing error: {e}")
        else:
            # Parse as single telemetry (supports GatewayMessagePayload or flat TelemetryIngest)
            telemetry_in = None
            try:
                if isinstance(data, dict) and "readings" in data:
                    gw_msg = GatewayMessagePayload(**data)
                    telemetry_in = gw_msg.to_telemetry_ingest(data_source="mqtt")
                else:
                    if isinstance(data, dict):
                        data["data_source"] = "mqtt"
                    telemetry_in = TelemetryIngest(**data)
            except ValidationError as val_err:
                self.malformed_messages_count += 1
                logger.warning(f"MQTT telemetry schema validation error on '{msg.topic}': {val_err}")
                return
            except Exception as e:
                self.malformed_messages_count += 1
                logger.warning(f"MQTT telemetry payload parsing error on '{msg.topic}': {e}")
                return

            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._process_mqtt_telemetry(telemetry_in),
                    self._loop
                )

    async def _process_mqtt_telemetry(self, telemetry_in: TelemetryIngest):
        db = SessionLocal()
        try:
            record, error, was_dup = await TelemetryService.process_single_telemetry(
                db=db, telemetry=telemetry_in, skip_ws=False
            )
            if was_dup:
                self.duplicates_detected_count += 1
            elif record:
                self.messages_processed_count += 1
            elif error:
                self.malformed_messages_count += 1
                logger.warning(f"MQTT telemetry rejected by ingestion rules: {error}")
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error persisting MQTT telemetry for node {telemetry_in.node_id}: {e}", exc_info=True)
        finally:
            db.close()

    async def _process_mqtt_replay(self, replay: GatewayReplayPayload):
        db = SessionLocal()
        try:
            res = await TelemetryService.process_gateway_replay(db=db, replay=replay)
            self.messages_processed_count += res.accepted_count
            self.duplicates_detected_count += res.duplicates_skipped
            if res.rejected_count > 0:
                self.malformed_messages_count += res.rejected_count
            logger.info(
                f"MQTT gateway replay completed for {replay.gateway_id}: "
                f"{res.accepted_count} accepted, {res.duplicates_skipped} duplicates, {res.rejected_count} rejected."
            )
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error processing MQTT gateway replay for {replay.gateway_id}: {e}", exc_info=True)
        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        """Return real-time diagnostic status of the MQTT gateway client."""
        client_id = getattr(settings, "MQTT_CLIENT_ID", "mineguard-central-backend")
        return {
            "enabled": settings.MQTT_ENABLED,
            "connected": self.is_connected,
            "broker": f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}",
            "client_id": client_id,
            "topic_prefix": settings.MQTT_TOPIC_PREFIX,
            "subscribed_topics": [
                f"{settings.MQTT_TOPIC_PREFIX}/nodes/+/telemetry",
                f"{settings.MQTT_TOPIC_PREFIX}/gateways/+/telemetry",
                f"{settings.MQTT_TOPIC_PREFIX}/gateways/+/replay"
            ],
            "messages_received": self.messages_received_count,
            "messages_processed": self.messages_processed_count,
            "malformed_messages": self.malformed_messages_count,
            "duplicates_detected": self.duplicates_detected_count,
            "reconnect_count": self.reconnect_count,
            "last_connected_at": self.last_connected_at,
            "last_message_at": self.last_message_at,
            "last_error": self.last_error
        }


mqtt_gateway = MQTTGatewayClient()
