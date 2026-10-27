import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.database import SessionLocal
from backend.app.db.models import SensorNode
from backend.app.schemas.node import SensorNodeCreate
from backend.app.schemas.telemetry import TelemetryIngest
from backend.app.services.node_service import NodeService
from backend.app.services.telemetry_service import TelemetryService
from backend.app.simulator.scenarios import ScenarioGenerator
from backend.app.realtime.websocket_manager import ws_manager

logger = logging.getLogger("mineguard.simulator")

# Realistic demonstration coordinates (Jharia Mining Region demonstration site)
DEMO_NODES = [
    {"node_id": "NODE-PIT-NORTH-01", "name": "North Highwall Bench Sector A", "lat": 23.7541, "lon": 86.4215, "elev": 185.0, "type": "highwall_extensometer"},
    {"node_id": "NODE-PIT-NORTH-02", "name": "North Highwall Toe Sensor B", "lat": 23.7552, "lon": 86.4228, "elev": 162.0, "type": "piezometer_tilt"},
    {"node_id": "NODE-PIT-SOUTH-03", "name": "South Haul-Road Monitoring Node", "lat": 23.7518, "lon": 86.4201, "elev": 195.0, "type": "inclinometer_gauge"},
    {"node_id": "NODE-BENCH-EAST-04", "name": "East Waste-Dump Stability Node", "lat": 23.7535, "lon": 86.4265, "elev": 210.0, "type": "extensometer_multiparam"},
    {"node_id": "NODE-SLOPE-WEST-05", "name": "West Catch-Bench Inclinometer", "lat": 23.7522, "lon": 86.4178, "elev": 178.0, "type": "tiltmeter_acoustic"},
    {"node_id": "NODE-PIPELINE-06", "name": "Mine Water De-watering Pipeline Gauge", "lat": 23.7560, "lon": 86.4240, "elev": 190.0, "type": "crack_meter_lvdt"},
]


class SimulationEngine:
    def __init__(self):
        self.is_running: bool = False
        self.scenario: str = "baseline"
        self.interval_sec: float = settings.SIMULATOR_DEFAULT_INTERVAL_SEC
        self.node_count: int = settings.SIMULATOR_DEFAULT_NODES
        self.seed: int = settings.SIMULATOR_RANDOM_SEED
        self.generator: ScenarioGenerator = ScenarioGenerator(seed=self.seed)
        self.task: Optional[asyncio.Task] = None
        self.ticks_generated: int = 0
        self.sequence_numbers: Dict[str, int] = {}

    def ensure_default_nodes(self, db: Session):
        """Seed initial demonstration monitoring nodes if table is empty."""
        count = NodeService.count_nodes(db=db)
        if count == 0:
            logger.info("Initializing demonstration sensor nodes...")
            for d in DEMO_NODES[:self.node_count]:
                node_in = SensorNodeCreate(
                    node_id=d["node_id"],
                    name=d["name"],
                    latitude=d["lat"],
                    longitude=d["lon"],
                    elevation_m=d["elev"],
                    node_type=d["type"],
                    installation_location="Demonstration Pit Sector",
                    firmware_version="v1.2-sim",
                    is_enabled=True
                )
                try:
                    NodeService.create_node(db=db, node_in=node_in)
                except Exception as e:
                    logger.warning(f"Default node creation error: {e}")

    async def start(
        self,
        scenario: str = "baseline",
        interval_sec: float = 3.0,
        node_count: int = 6,
        seed: int = 42
    ) -> Dict[str, Any]:
        """Start or reconfigure simulator background task."""
        if self.is_running:
            await self.stop()

        self.scenario = scenario
        self.interval_sec = max(0.5, min(60.0, interval_sec))
        self.node_count = max(1, min(len(DEMO_NODES), node_count))
        self.seed = seed
        self.generator.reset(seed=self.seed)
        self.is_running = True

        db = SessionLocal()
        try:
            self.ensure_default_nodes(db)
        finally:
            db.close()

        self.task = asyncio.create_task(self._simulation_loop())
        logger.info(f"Simulator started: scenario='{self.scenario}', interval={self.interval_sec}s, nodes={self.node_count}")

        # Broadcast simulator status
        await ws_manager.broadcast("simulator_status", self.get_status())
        return self.get_status()

    async def stop(self) -> Dict[str, Any]:
        """Stop simulator background task."""
        self.is_running = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        logger.info("Simulator halted.")
        await ws_manager.broadcast("simulator_status", self.get_status())
        return self.get_status()

    def reset(self) -> Dict[str, Any]:
        """Reset internal scenario generator and sequence counters."""
        self.generator.reset(seed=self.seed)
        self.ticks_generated = 0
        self.sequence_numbers.clear()
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "scenario": self.scenario,
            "interval_sec": self.interval_sec,
            "node_count": self.node_count,
            "ticks_generated": self.ticks_generated,
            "seed": self.seed,
            "is_simulated_data": True
        }

    async def _simulation_loop(self):
        """Asynchronous simulator clock tick."""
        while self.is_running:
            try:
                await self._tick()
                await asyncio.sleep(self.interval_sec)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Simulator loop error: {e}", exc_info=True)
                await asyncio.sleep(self.interval_sec)

    async def _tick(self):
        self.generator.time_step += 1
        self.ticks_generated += 1
        now_utc = datetime.now(timezone.utc)

        db = SessionLocal()
        try:
            nodes = db.query(SensorNode).filter(SensorNode.is_enabled == True).limit(self.node_count).all()
            for idx, node in enumerate(nodes):
                obs = self.generator.next_observation(
                    node_index=idx,
                    total_nodes=len(nodes),
                    scenario=self.scenario
                )
                if not obs:
                    continue  # Simulating dropped frame

                seq = self.sequence_numbers.get(node.node_id, 1)
                self.sequence_numbers[node.node_id] = seq + 1

                telemetry_in = TelemetryIngest(
                    event_id=str(uuid.uuid4()),
                    node_id=node.node_id,
                    sequence_number=seq,
                    timestamp=now_utc,
                    data_source="simulator",
                    displacement_mm=obs.get("displacement_mm"),
                    tilt_x_deg=obs.get("tilt_x_deg"),
                    tilt_y_deg=obs.get("tilt_y_deg"),
                    vibration_rms_ms2=obs.get("vibration_rms_ms2"),
                    peak_acceleration_ms2=obs.get("peak_acceleration_ms2"),
                    temperature_c=obs.get("temperature_c"),
                    crack_width_mm=obs.get("crack_width_mm"),
                    battery_pct=obs.get("battery_pct"),
                    battery_voltage_v=obs.get("battery_voltage_v"),
                    sensor_quality={"simulated": True, "scenario": self.scenario}
                )

                await TelemetryService.process_single_telemetry(
                    db=db,
                    telemetry=telemetry_in,
                    skip_ws=False
                )
        finally:
            db.close()


simulator_engine = SimulationEngine()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MineGuard-AI Standalone Simulator")
    parser.add_argument("--scenario", default="accelerating_subsidence", help="Scenario to run")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval in seconds")
    parser.add_argument("--nodes", type=int, default=6, help="Number of nodes")
    args = parser.parse_args()

    async def main():
        print(f"Starting Standalone MineGuard-AI Simulator [Scenario: {args.scenario}]...")
        await simulator_engine.start(
            scenario=args.scenario,
            interval_sec=args.interval,
            node_count=args.nodes
        )
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await simulator_engine.stop()
            print("Simulator terminated.")

    asyncio.run(main())
