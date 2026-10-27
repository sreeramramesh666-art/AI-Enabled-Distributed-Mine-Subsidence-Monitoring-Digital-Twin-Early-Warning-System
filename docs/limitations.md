# MineGuard-AI Limitations & Technical Boundary Conditions

1. **Demonstration & Prototype Nature**:
   - Developed for Smart India Hackathon 2024 problem SIH26025.
   - Thresholds for subsidence rate, acceleration, and tilt are baseline geotechnical demonstration values. They must be calibrated by a licensed geotechnical engineer before any mine deployment.

2. **No Life-Safety Certification**:
   - This software is not certified as an intrinsically safe or safety-critical SIL-3/SIL-4 industrial protection system.
   - In mining contexts, safety decisions must incorporate multiple redundant physical inspections, radar interferometry, micro-seismic monitoring, and manual borehole extensometer readings.

3. **GPS / Coordinate Resolution**:
   - Standard consumer GPS modules exhibit ±3m horizontal accuracy, which is insufficient for millimetre subsidence detection directly from GPS. In real hardware, subsidence is measured via relative differential displacement sensors (LVDTs, extensometers, inclinometers) anchored to fixed datum benchmarks, not absolute GPS coordinates.

4. **Network & Tile Caching**:
   - When running fully offline without cached OpenStreetMap tiles, the frontend provides a high-contrast localized GIS grid/schematic view that charts relative metric node coordinates without depending on remote tile servers.
