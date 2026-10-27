import math
import random
from typing import Dict, Any, List


class ScenarioGenerator:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.time_step = 0

    def reset(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.time_step = 0

    def next_observation(
        self,
        node_index: int,
        total_nodes: int,
        scenario: str
    ) -> Dict[str, Any]:
        """
        Generate synthetic telemetry frame for a given node under the active scenario.
        """
        t = self.time_step
        # Ambient temperature diurnal variation
        base_temp = 28.0 + 3.0 * math.sin(t * 0.1) + self.rng.gauss(0, 0.2)
        base_battery = max(15.0, 95.0 - (t * 0.02))

        # Default baseline values
        disp_mm = self.rng.gauss(0.1, 0.05)
        tilt_x = self.rng.gauss(0.05, 0.02)
        tilt_y = self.rng.gauss(-0.02, 0.02)
        vib_rms = max(0.05, self.rng.gauss(0.2, 0.05))
        peak_accel = vib_rms * 2.2
        crack_width = None

        # Node 0 or 1 is typically chosen as the primary anomalous node in scenarios
        is_target_node = (node_index == 0 or (node_index == 1 and total_nodes > 3))

        if scenario == "baseline":
            # Stable equilibrium
            pass

        elif scenario == "gradual_settlement":
            if is_target_node:
                # Constant velocity settlement: ~2.0 mm per 10 steps
                rate = 0.2
                disp_mm = (t * rate) + self.rng.gauss(0, 0.05)
                tilt_x = 0.05 + (t * 0.025)
                crack_width = 1.0 + (t * 0.05)

        elif scenario == "accelerating_subsidence":
            if is_target_node:
                # Exponential/polynomial acceleration: d = 0.015 * t^2
                disp_mm = (0.015 * (t ** 2)) + self.rng.gauss(0, 0.1)
                tilt_x = (0.02 * (t ** 1.5)) + self.rng.gauss(0, 0.05)
                tilt_y = (0.01 * (t ** 1.5)) + self.rng.gauss(0, 0.05)
                crack_width = 2.0 + (0.01 * (t ** 2))
                vib_rms = max(0.1, 0.2 + (0.02 * t) + self.rng.gauss(0, 0.1))
            else:
                # Neighbouring peripheral nodes experience slight correlated drag
                disp_mm = (0.002 * (t ** 1.8)) + self.rng.gauss(0, 0.05)

        elif scenario == "sudden_collapse":
            if t < 10:
                disp_mm = 0.2 + self.rng.gauss(0, 0.05)
            else:
                # Sudden fault slip / sinkhole
                disp_mm = 38.5 + self.rng.gauss(0, 0.2)
                tilt_x = 6.2 + self.rng.gauss(0, 0.1)
                tilt_y = 4.8 + self.rng.gauss(0, 0.1)
                vib_rms = 14.5 + self.rng.gauss(0, 1.0)
                crack_width = 45.0 + self.rng.gauss(0, 0.5)

        elif scenario == "vibration_blast":
            # Transient blasting event at t >= 5 and t <= 12
            if 5 <= t <= 12:
                vib_rms = self.rng.uniform(12.0, 24.0)
                peak_accel = vib_rms * 3.5
            else:
                vib_rms = max(0.05, self.rng.gauss(0.2, 0.05))
            # No permanent vertical settlement
            disp_mm = self.rng.gauss(0.1, 0.02)

        elif scenario == "sensor_drift":
            if is_target_node:
                # Transducer drift on tilt without actual displacement
                tilt_x = 0.1 * t
                tilt_y = -0.08 * t
                disp_mm = self.rng.gauss(0.1, 0.02)

        elif scenario == "packet_loss":
            # Simulate dropped packet for target node intermittently
            if is_target_node and (t % 3 == 0):
                return {}  # Dropped
            disp_mm = self.rng.gauss(0.1, 0.05)

        return {
            "displacement_mm": round(disp_mm, 4) if disp_mm is not None else None,
            "tilt_x_deg": round(tilt_x, 3) if tilt_x is not None else None,
            "tilt_y_deg": round(tilt_y, 3) if tilt_y is not None else None,
            "vibration_rms_ms2": round(vib_rms, 3) if vib_rms is not None else None,
            "peak_acceleration_ms2": round(peak_accel, 3) if peak_accel is not None else None,
            "temperature_c": round(base_temp, 2),
            "crack_width_mm": round(crack_width, 2) if crack_width is not None else None,
            "battery_pct": round(base_battery, 1),
            "battery_voltage_v": round(3.3 + (base_battery / 100.0) * 0.9, 2)
        }
