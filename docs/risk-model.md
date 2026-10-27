# MineGuard-AI Risk Model & Geotechnical Decision Logic

## 1. Safety Notice & Geotechnical Disclaimer
> [!WARNING]
> MineGuard-AI is a prototype research and demonstration platform developed for Smart India Hackathon problem SIH26025. 
> Numerical parameters, warning levels, and simulation scenarios represent demonstration thresholds only. 
> Real-world deployment in active open-cast or underground mining operations mandates certified geotechnical surveys, site-specific rock mass rating (RMR) calibration, and formal regulatory safety approvals.

## 2. Multi-Factor Risk Architecture

Ground subsidence and slope instability risk is calculated by decoupling physical hazard indicators from sensor health indicators.

### 2.1 Physical Deformation Indicators
1. **Cumulative Displacement ($d$)**:
   - Total subsidence or heave in millimetres.
2. **Velocity of Deformation ($v = \frac{d_t - d_{t-\Delta t}}{\Delta t}$)**:
   - Rate of movement expressed in $\text{mm/hr}$.
   - Increasing velocity is the primary physical pre-cursor to slope failure.
3. **Acceleration ($a = \frac{v_t - v_{t-\Delta t}}{\Delta t}$)**:
   - Rate of acceleration in $\text{mm/hr}^2$.
   - Positive acceleration ($a > 0$) indicates tertiary creep (imminent collapse warning).
4. **Resultant Vector Tilt ($\theta = \sqrt{\theta_x^2 + \theta_y^2}$)**:
   - Rotational deviation in degrees from horizontal equilibrium.
5. **Dynamic Blast / Vibration RMS**:
   - Dynamic ground response in $\text{m/s}^2$ indicating blasting influence or seismic slip.

### 2.2 Data Quality & Uncertainty Indicators
- Stale data timeout ($t_{\text{now}} - t_{\text{last}} > \tau_{\text{stale}}$).
- Sensor out-of-bounds or implausible physical gradient ($\Delta d > 500\text{ mm}$ in 1 second).
- Battery low indicator ($< 20\%$).

### 2.3 Categorical Risk Levels
- **NORMAL**: Measurements within nominal baseline bounds; negligible rate of movement.
- **WATCH**: Minor movement or slight tilt detected; elevated monitoring frequency recommended.
- **WARNING**: Sustained deformation rate exceeding normal thresholds ($\ge 2.0\text{ mm/hr}$) or vector tilt $\ge 2.0^\circ$.
- **CRITICAL**: Accelerating deformation ($a > 0.5\text{ mm/hr}^2$), cumulative displacement $\ge 30.0\text{ mm}$, or vector tilt $\ge 5.0^\circ$. Urgent geotechnical inspection required.
- **DATA_UNRELIABLE**: Sensor reports corrupted values, intermittent connectivity, or exceeds stale timeout. Indicates unmonitored ground, NOT guaranteed stability.

## 3. Multivariate Anomaly Detection (Isolation Forest)
- Unsupervised isolation forest model trained on rolling clean baseline telemetry.
- Evaluates joint feature vector: $[d, \theta_x, \theta_y, v, \text{vibration\_rms}, \text{temperature}]$.
- Detects non-linear multi-sensor drifts and anomalous correlation without arbitrary single-variable thresholds.
- Outputs decision score $[-1.0, 1.0]$ and explicit explanatory attribution of top anomalous feature.
