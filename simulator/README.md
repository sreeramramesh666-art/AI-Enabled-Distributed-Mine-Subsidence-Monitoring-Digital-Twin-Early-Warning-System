# MineGuard-AI Deterministic Sensor Simulator

## Overview
The MineGuard-AI simulator provides realistic, physically-grounded synthetic telemetry for testing, algorithm verification, and demonstration when physical IoT hardware is not connected.

## Scenarios Supported
1. `baseline`: Stable operation with low environmental Gaussian noise, minor ambient thermal cycles, and negligible ground deformation.
2. `gradual_settlement`: Steady, constant-velocity subsidence ($v \approx 1.5 - 2.5\text{ mm/hr}$) simulating primary consolidation.
3. `accelerating_subsidence`: Progressive non-linear settlement with positive acceleration ($a > 0.5\text{ mm/hr}^2$), triggering WARNING and CRITICAL early warnings.
4. `sudden_collapse`: Abrupt displacement step-function representing fault slip or crown-hole sinkhole development.
5. `vibration_blast`: High transient peak vibration ($10 - 25\text{ m/s}^2$) without permanent vertical displacement, simulating controlled mine blasting.
6. `sensor_drift`: Slow electronic transducer offset drift on tilt channels with stable physical ground.
7. `packet_loss`: Intermittent dropped transmissions and delayed delivery testing edge replay capabilities.

## Execution
The simulator can be run either:
1. Internally via the Backend API (`POST /api/v1/simulator/start`) and Frontend Dashboard.
2. Standalone script:
   ```bash
   python backend/app/simulator/engine.py --scenario accelerating_subsidence --interval 2.0 --nodes 6
   ```
All synthetic data is explicitly tagged with `data_source: "simulator"` and displayed with prominent simulated data badges in the UI and reports.
