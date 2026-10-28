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

        # -------------------------------------------------------------
        # Physical Test-Rig Benchmark Scenarios (SIH26025 Table 12)
        # -------------------------------------------------------------
        elif scenario == "testrig_baseline":
            # Controlled laboratory testbed at static equilibrium on reference plate
            disp_mm = self.rng.gauss(0.02, 0.01)
            tilt_x = self.rng.gauss(0.01, 0.005)
            tilt_y = self.rng.gauss(-0.01, 0.005)
            vib_rms = max(0.01, self.rng.gauss(0.04, 0.01))

        elif scenario == "testrig_gradual":
            # Micrometer lead screw turning at constant rate: 0.5 mm per tick up to 10.0 mm
            rate = 0.5
            disp_target = min(10.0, t * rate)
            disp_mm = disp_target + self.rng.gauss(0, 0.02)
            tilt_x = (disp_target * 0.04) + self.rng.gauss(0, 0.01)
            tilt_y = (disp_target * 0.02) + self.rng.gauss(0, 0.01)
            vib_rms = max(0.02, self.rng.gauss(0.06, 0.01))

        elif scenario == "testrig_differential":
            # Differential subsidence: target node tilts and drops while adjacent reference remains static
            if is_target_node:
                disp_val = min(15.0, t * 0.8)
                disp_mm = disp_val + self.rng.gauss(0, 0.03)
                tilt_x = min(3.5, 0.15 * t) + self.rng.gauss(0, 0.02)
                tilt_y = min(2.0, 0.08 * t) + self.rng.gauss(0, 0.02)
            else:
                disp_mm = self.rng.gauss(0.02, 0.01)
                tilt_x = self.rng.gauss(0.01, 0.005)

        elif scenario == "testrig_vibration_only":
            # Test-rig bench shaker active: high transient vibration, zero net settlement
            disp_mm = self.rng.gauss(0.02, 0.01)
            vib_rms = self.rng.uniform(6.5, 14.0)
            peak_accel = vib_rms * 2.8

        elif scenario == "testrig_disconnect_reconnect":
            # Sensor cable pull or edge power disconnect at t between 4 and 9, then reconnected
            if 4 <= t <= 9 and is_target_node:
                return {}  # Disconnected
            disp_mm = 2.5 + (0.1 * t) + self.rng.gauss(0, 0.02)

        elif scenario == "testrig_comm_loss":
            # Radio link interruption to gateway
            if t > 5 and is_target_node:
                return {}  # Gateway not receiving packets
            disp_mm = 0.5 + self.rng.gauss(0, 0.02)

        elif scenario == "testrig_return_stable":
            # Movement introduced up to t=8, then micrometer halts and plate returns to stable rest
            if t <= 8:
                disp_mm = (t * 0.6) + self.rng.gauss(0, 0.02)
                tilt_x = (t * 0.05) + self.rng.gauss(0, 0.01)
            else:
                disp_mm = 4.8 + self.rng.gauss(0, 0.01)
                tilt_x = 0.40 + self.rng.gauss(0, 0.005)
                vib_rms = max(0.01, self.rng.gauss(0.03, 0.005))

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

