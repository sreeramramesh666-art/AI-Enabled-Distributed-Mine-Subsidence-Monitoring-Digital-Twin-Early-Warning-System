# MineGuard-AI Hardware Integration Guide

## 1. Physical Node Architecture
In a physical deployment, each monitoring node consists of:
- **MCU**: ESP32-WROOM-32 or STM32 ultra-low-power microcontrollers.
- **Inclinometer / Tilt Sensor**: Dual-axis MEMS accelerometer (e.g. SCA103T or MPU6050/ADXL355) with sub-0.01° precision.
- **Displacement Transducer**: Linear Variable Differential Transformer (LVDT), wire extensometer, or optical time-of-flight crack gauge.
- **Seismic / Vibration Sensor**: Piezoelectric or MEMS geophone measuring peak particle velocity (PPV) and RMS vibration.
- **Power**: LiFePO4 battery pack with 10W polycrystalline solar harvesting panel.

## 2. Gateway Edge Architecture
```
[Sensor Node A] --- LoRa (865-867 MHz) ---> [ Field Gateway ] --- 4G LTE / WiFi / Ethernet ---> [ MineGuard-AI ]
[Sensor Node B] --- ESP-NOW Mesh -----------> [ (ESP32-S3)    ] --- MQTT / REST Batch ----------> [ Local Server ]
```

### Edge Buffering (Store-and-Forward)
The field gateway implements a circular flash buffer (SPIFFS / SD card). When field cellular/WiFi signal drops:
1. Readings are cached with exact hardware RTC timestamp and monotonic sequence numbers.
2. Once connection to the MineGuard-AI host is restored, the gateway posts in batch chunks of up to 100 observations to `/api/v1/telemetry/batch`.
3. MineGuard-AI validates sequence numbers, deduplicates redundant packets, and marks backfilled data without treating historical readings as newly occurring real-time emergencies.
