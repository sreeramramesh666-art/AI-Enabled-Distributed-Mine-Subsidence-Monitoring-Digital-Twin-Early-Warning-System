# MineGuard-AI Limitations & Technical Boundary Conditions

## 1. Prototype & Demonstration Scope
- Developed for Smart India Hackathon problem SIH26025.
- Kinematic thresholds (displacement limits, deformation velocity, tertiary creep acceleration) represent baseline demonstration values. Site-specific geotechnical engineering calibration is mandatory prior to physical deployment in active mining operations.

## 2. Regulatory & Life-Safety Boundaries
- **No Direct Collapse Prediction**: Ground collapse in heterogeneous rock masses depends on joint water pressure, discontinuity dip/strike, blast damage zones, and lithology. MineGuard-AI provides algorithmic early-awareness and anomaly detection; it does NOT predict the exact moment of rock slope collapse.
- **DGMS Circulars**: Real-world operations in Indian mines require compliance with Directorate General of Mines Safety (DGMS) guidelines and mandatory human inspection by qualified geotechnical surveyors.
- **Machine Learning Scope**: The Isolation Forest detector identifies multi-sensor statistical deviation. Its decision score is an unsupervised outlier distance ($-1.0$ to $1.0$), NOT an empirical or Bayesian probability of structural collapse.

## 3. Sensor & Hardware Boundary Conditions
- **Direct GPS Limitations**: Consumer-grade single-frequency GPS receivers (±3m error) are incapable of directly detecting millimetre-level ground subsidence. In production hardware, displacement is measured using differential borehole extensometers, linear variable differential transformers (LVDTs), and MEMS dual-axis tiltmeters referenced to deep bedrock anchors.
- **Blasting Vibration Artifacts**: Production blasting generates high transient ground acceleration ($> 5.0\text{ m/s}^2$). MineGuard-AI discriminates blasting by verifying whether vibration is accompanied by permanent displacement increment ($|\Delta d| > 0.15\text{ mm}$). However, blast-induced acoustic noise or transducer casing resonance may still produce brief sensor anomalies.
- **Frozen Transducer & Drift**: MEMS inclinometers are subject to long-term electronic and thermal baseline drift. MineGuard-AI flags monotonic drift without displacement, but physical re-zeroing and periodic field recalibration are necessary.

## 4. Connectivity & Offline Buffering
- **Gateway Disconnection**: When field gateway connectivity to the central server is interrupted, the edge gateway buffers telemetry in local non-volatile storage. Upon reconnection, buffered records are ingested via the idempotent replay API.
- **Anti-False-Safe Guarantee**: In the event of packet loss or offline node status, the system forces the risk classification to `DATA_UNRELIABLE`. The system will never show nominal green status when data channels are stale or missing.
- **Offline Map Tiles & IDW Surface**: In air-gapped environments without OpenStreetMap access, the frontend seamlessly switches to a localized metric Cartesian GIS grid layout. Spatial IDW surface interpolation represents an inverse distance mathematical proximity model ($p=2$, radius $350\text{m}$) and does not simulate subsurface geotechnical shear planes or discontinuity friction angles. Unmeasured areas beyond the 350m radius of active nodes must never be assumed stable or safe.
