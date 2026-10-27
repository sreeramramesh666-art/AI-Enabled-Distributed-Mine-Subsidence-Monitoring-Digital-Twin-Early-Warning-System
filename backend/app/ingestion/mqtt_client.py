import asyncio
import json
import logging
import ssl
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal
from backend.app.schemas.telemetry import TelemetryIngest
from backend.app.services.telemetry_service import TelemetryService

logger = logging.getLogger("mineguard.mqtt")


class MQTTGatewayClient:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self.loop_task: Optional[asyncio.Task] = None
        self._loop = None

    def initialize(self):
        """Configure paho MQTT client with TLS and auth if enabled."""
        if not settings.MQTT_ENABLED:
            logger.info("MQTT client is disabled via configuration.")
            return

        try:
            # Paho MQTT 2.0 compatible client initialization
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id="mineguard-central-backend"
            )

            if settings.MQTT_USERNAME:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

            if settings.MQTT_TLS_ENABLED:
                context = ssl.create_default_context()
                self.client.tls_set_context(context)

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            logger.info(f"MQTT client configured for {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        except Exception as e:
            logger.warning(f"MQTT client initialization error: {e}")
            self.client = None

    def start(self, loop=None):
        """Start non-blocking background connection loop."""
        if not settings.MQTT_ENABLED or not self.client:
            return

        self._loop = loop or asyncio.get_event_loop()
        try:
            self.client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                settings.MQTT_KEEPALIVE
            )
            self.client.loop_start()
            logger.info("MQTT background loop started.")
        except Exception as e:
            logger.warning(f"Could not connect to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} ({e}). Backend will continue in REST/offline mode.")

    def stop(self):
        """Clean shutdown of MQTT connection."""
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
            topic = f"{settings.MQTT_TOPIC_PREFIX}/nodes/+/telemetry"
            client.subscribe(topic, qos=1)
            logger.info(f"MQTT Connected successfully to broker. Subscribed to '{topic}'.")
        else:
            self.is_connected = False
            logger.warning(f"MQTT Connection refused with reason code: {reason_code}")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.is_connected = False
        logger.warning(f"MQTT Disconnected from broker (reason code: {reason_code}). Will retry with backoff...")

    def _on_message(self, client, userdata, msg):
        """Handle incoming telemetry message on topic: mineguard/nodes/{node_id}/telemetry"""
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)
            data["data_source"] = "mqtt"

            # Parse and validate schema
            telemetry_in = TelemetryIngest(**data)

            # Schedule async telemetry processing on main event loop
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._process_mqtt_telemetry(telemetry_in),
                    self._loop
                )
        except json.JSONDecodeError:
            logger.warning(f"MQTT received malformed non-JSON payload on topic {msg.topic}")
        except Exception as e:
            logger.error(f"MQTT message processing error: {e}")

    async def _process_mqtt_telemetry(self, telemetry_in: TelemetryIngest):
        db = SessionLocal()
        try:
            await TelemetryService.process_single_telemetry(db=db, telemetry=telemetry_in, skip_ws=False)
        except Exception as e:
            logger.error(f"Error persisting MQTT telemetry: {e}")
        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": settings.MQTT_ENABLED,
            "connected": self.is_connected,
            "broker": f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}",
            "topic_prefix": settings.MQTT_TOPIC_PREFIX
        }


mqtt_gateway = MQTTGatewayClient()
