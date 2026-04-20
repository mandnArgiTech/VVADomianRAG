# ArduRover + ArduPilot `libraries/` — PageIndex

> **Purpose:** Hierarchical tree index of the ArduPilot/ardupilot source tree
> focused on the **Rover** (ground vehicle) vehicle, inspired by the
> [PageIndex](https://github.com/VectifyAI/PageIndex) framework.
> **Section 2** expands **`ardupilot/libraries/`** in depth: every top-level package,
> category maps, HAL/sensor/EKF/GCS/CAN tables, and façade-class lookup for RAG navigation.

## Document map

| § | Topic |
|---|--------|
| [0](#0-root-ardupilot) | Repository root layout |
| [1](#1-rover--vehicle-firmware-ardurover) | `Rover/` firmware, modes, scheduler |
| [2](#2-libraries--full-catalog-breadth--depth) | **`libraries/` full catalog** (master index, HAL, sensors, EKF, control, GCS, …) |
| [3](#3-modules--git-submodules) | Git submodules (`modules/`) |
| [4](#4-tools--toolchain-and-simulation) | `Tools/` and SITL |
| [5](#5-function--file-cross-reference-ardurover) | Rover symbol → file cross-reference |
| [6](#6-ardurover-control-flow-diagram) | End-to-end control-flow diagram |

**Legend (§2.1):** `★` = Rover hot path · `◆` = common optional · `○` = other vehicles / specialist.

---

## 0. Root (`ardupilot/`)

**Summary:** ArduPilot is an open-source autopilot platform supporting multiple
vehicle types. The Rover firmware (ArduRover) handles wheeled and boat vehicles.
The repository is split into vehicle-specific top-level directories and a shared
`libraries/` subtree. All Rover-specific logic is in `Rover/`; shared algorithms
(EKF, PID, navigation, sensors) live in `libraries/`.

```
ardupilot/
├── Rover/              ← ArduRover vehicle firmware (main focus)
├── ArduCopter/         ← multirotor (shares most libraries with Rover)
├── ArduPlane/          ← fixed-wing
├── ArduSub/            ← submarine
├── AntennaTracker/     ← antenna tracker
├── Blimp/              ← blimp vehicle
├── libraries/          ← ALL shared C++ libraries (sensors, control, HAL, comms)
├── modules/            ← git submodules: ChibiOS, DroneCAN, MAVLink, etc.
├── Tools/              ← build tools, simulation (SITL), log analysis
├── tests/              ← unit test infrastructure
└── wscript / waf       ← Waf build system entry point
```

---

## 1. `Rover/` — Vehicle Firmware (ArduRover)

**Summary:** Contains everything unique to a ground rover or boat. The `Rover`
class (singleton) is the vehicle state machine; it owns all library instances and
runs the cooperative scheduler task table.

### 1.1 Entry point and scheduler

| File | Summary |
|------|---------|
| `Rover.cpp` | `AP_HAL_MAIN_CALLBACKS(&rover)` — program entry. Defines the `scheduler_tasks[]` table that drives every periodic function at a specified rate and time budget. |
| `Rover.h` | The `Rover` singleton class: declares all subsystem instances (AHRS, GPS, motors, EKF, mission, GCS, etc.) and task function prototypes. |
| `system.cpp` | `init_ardupilot()` — hardware and library initialisation on boot. Loads parameters, sets up HAL, and initialises every subsystem before the scheduler starts. |

**Scheduler task table (key entries from `Rover.cpp`):**

| Task | Rate (Hz) | Budget (µs) | Purpose |
|------|-----------|-------------|---------|
| `read_radio` | 50 | 200 | RC input from `RC_Channels` |
| `ahrs_update` | **400** | 400 | IMU → AHRS/EKF at full rate |
| `read_rangefinders` | 50 | 200 | Obstacle/terrain sensors |
| `update_current_mode` | **400** | 200 | Mode update → navigation → outputs |
| `set_servos` | **400** | 200 | Motor/servo output via `AP_MotorsUGV` |
| `GPS::update` | 50 | 300 | GNSS fix + velocity |
| `AP_Baro::update` | 10 | 200 | Barometer |
| `AP_Beacon::update` | 50 | 200 | IndoorBeacon positioning |
| `AP_Proximity::update` | 50 | 200 | Forward-looking lidar/sonar |
| `AP_WindVane::update` | 20 | 100 | Wind direction (sailboat) |
| `AC_Fence::update` | 10 | 100 | Geofence monitoring |
| `update_wheel_encoder` | 50 | 200 | Odometry |
| `update_compass` | 10 | 200 | Magnetometer |
| `GCS::update_receive/send` | 400 | 500/1000 | MAVLink receive and send |
| `AP_BattMonitor::read` | 10 | 300 | Battery voltage/current |
| `AP_Logger::periodic_tasks` | 50 | 300 | Dataflash / SD log flush |
| `AP_Terrain::update` | 10 | 100 | Terrain database lookup |
| `update_altitude` | 10 | 200 | Height estimate (baro+GPS+EKF) |
| `cruise_learn.update` | 10 | 200 | Throttle/speed self-tuning |

### 1.2 Flight modes (`mode*.cpp` / `mode.h`)

**Summary:** All control modes inherit from the `Mode` base class. The active
mode's `update()` is called at **400 Hz** from `update_current_mode()`.

| Mode | Class | File | Summary |
|------|-------|------|---------|
| `MANUAL` (0) | `ModeManual` | `mode_manual.cpp` | Raw RC passthrough; no navigation. Steering and throttle directly from pilot. |
| `ACRO` (1) | `ModeAcro` | `mode_acro.cpp` | Rate-controlled steering. RC stick → desired yaw rate → `AR_AttitudeControl`. No heading hold. |
| `STEERING` (3) | `ModeSteering` | `mode_steering.cpp` | Heading-hold + speed-hold. Stick → desired heading and speed; closed-loop on both. |
| `HOLD` (4) | `ModeHold` | `mode_hold.cpp` | Zero throttle, steering centred. Safe fallback. |
| `LOITER` (5) | `ModeLoiter` | `mode_loiter.cpp` | Position hold using `AR_WPNav` with zero forward speed. |
| `FOLLOW` (6) | `ModeFollow` | `mode_follow.cpp` | Follows another vehicle via `AP_Follow` MAVLink target. |
| `SIMPLE` (7) | `ModeSimple` | `mode_simple.cpp` | Earth-frame steering: stick always points in fixed compass direction. |
| `AUTO` (10) | `ModeAuto` | `mode_auto.cpp` | Mission execution via `AP_Mission`. Handles `NAV_WAYPOINT`, `DO_JUMP`, `NAV_LOITER_UNLIM`, etc. Uses `AR_WPNav` for all navigation. |
| `RTL` (11) | `ModeRTL` | `mode_rtl.cpp` | Return-to-launch via `AR_WPNav`. Calculates home position from GPS; drives directly or via SmartRTL path. |
| `SMART_RTL` (12) | `ModeSmartRTL` | `mode_smart_rtl.cpp` | Return-to-launch retracing the outbound path via `AP_SmartRTL`. |
| `GUIDED` (15) | `ModeGuided` | `mode_guided.cpp` | External (GCS/companion) position/velocity/heading target. Accepts `MAV_CMD_NAV_WAYPOINT` via MAVLink. |

**Mode base class interface (`mode.h`):**

```cpp
class Mode {
    virtual void update() = 0;          // called at 400 Hz
    virtual bool _enter() { return true; }  // mode transition in
    virtual void _exit() {}             // mode transition out
    virtual bool is_autopilot_mode() const { return false; }
};
```

### 1.3 Sensors and radio

| File | Summary |
|------|---------|
| `sensors.cpp` | `update_compass()`, `update_alt()`, `update_wheel_encoder()` — reads all sensors and updates state. |
| `radio.cpp` | `read_radio()` — reads `RC_Channels`, applies expo/deadzone, maps sticks to throttle, steering, and auxiliary functions. |
| `ekf_check.cpp` | `ekf_check()` — monitors EKF variance; triggers `EKF_BAD` failsafe if innovation variances exceed threshold. |
| `crash_check.cpp` | Detects roll/pitch beyond limits (boat capsize, rover tip-over) and triggers disarm. |

### 1.4 Navigation and output pipeline

| File | Summary |
|------|---------|
| `Steering.cpp` | `set_servos()` — calls `g2.motors.output(armed, speed, dt)` to translate throttle and steering demands into PWM outputs. |
| `commands.cpp` | Handles DO-type mission commands: `do_set_reverse()`, `do_guided()`, `start_guided()`. |
| `cruise_learn.cpp` | Self-learning throttle-to-speed model used to improve speed control accuracy over time. |
| `fence.cpp` | Geofence: calls `AC_Fence::check_fence()`, switches to `HOLD` or `RTL` if fence is breached. |
| `failsafe.cpp` | Main loop lockup detection (heartbeat watchdog), GCS heartbeat failsafe, battery failsafe, EKF failsafe. |
| `Log.cpp` | Writes rover-specific log messages (`STER`, `NTUN`, `MOD`, `FENCE`, `BAT`, `BSIM` etc.). |

### 1.5 Ground Control System interface

| File | Summary |
|------|---------|
| `GCS_Mavlink.cpp` | `GCS_MAVLINK_Rover` — handles all MAVLink input for Rover: `COMMAND_LONG`, `SET_POSITION_TARGET`, `SET_ATTITUDE_TARGET`, `MISSION_ITEM`. |
| `GCS_Rover.cpp` | Rover-specific GCS extensions: custom status text, custom telemetry formatting. |

### 1.6 Sailboat and balance-bot variants

| File | Summary |
|------|---------|
| `sailboat.cpp / sailboat.h` | Sailboat-specific motor and sail control. Overrides `AP_MotorsUGV` to drive a main sail servo instead of throttle. Wind vane input feeds into tack/gybe logic. |
| `balance_bot.cpp` | Self-balancing robot mode. Fuses IMU pitch angle with `AR_AttitudeControl` for balance. |

### 1.7 Parameters and arming

| File | Summary |
|------|---------|
| `Parameters.cpp / Parameters.h` | Declares `g` (legacy param group) and `g2` (new param group). Every tunable value stored in EEPROM via `AP_Param`. |
| `AP_Arming.cpp / AP_Arming.h` | Rover arming checks: EKF health, GPS lock, compass calibration, RC calibration, battery voltage floor. |

---

## 2. `libraries/` — Full catalog (breadth & depth)

**Scope:** `ardupilot/libraries/` holds **~136** top-level packages shared by Copter, Plane, Rover, Sub, Tracker, and Blimp. This section expands the original brief overview into a **navigable PageIndex**: master table → category map → subsystem deep dives (HAL, sensors, estimation, control, GCS, CAN, logging).

**Markers:** `★` Rover hot path (scheduler / AHRS / nav / motors / GCS); `◆` common optional; `○` other vehicles or specialist.

---

### 2.0 Section map (libraries)

| § | Topic |
|---|-------|
| 2.1 | Master index (every package) |
| 2.2 | Category → library map |
| 2.3 | HAL & board |
| 2.4 | Sensor backend tables |
| 2.5 | AHRS / DAL / EKF |
| 2.6 | Control (copter/plane/PID) |
| 2.7 | Rover / boat (`AR_*`, wind, Torqeedo) |
| 2.8 | Avoidance / fence / terrain / SmartRTL |
| 2.9 | Servos / RC / relays |
| 2.10 | Power / engine |
| 2.11 | GCS / MAVLink / MSP / telemetry |
| 2.12 | CAN / DroneCAN |
| 2.13 | Payloads / OSD |
| 2.14 | Logger / params / scheduler |
| 2.15 | Notify / scripting / SITL |
| 2.16 | Façade class lookup |

---

### 2.1 Master index — every `libraries/` package

| Marker | Library | Role |
|--------|---------|------|
| ◆ | `AC_AttitudeControl/` | Multicopter attitude + rate controllers; lean angle limits; feeds `AP_Motors` matrix mixer. |
| ○ | `AC_AutoTune/` | In-flight excitation + automatic PID gain selection (copter/plane). |
| ○ | `AC_Autorotation/` | Helicopter autorotation glide controller and flare logic. |
| ★ | `AC_Avoidance/` | Velocity obstacle avoidance using fence + proximity; integrates `AP_OAPathPlanner` for global detours. |
| ★ | `AC_Fence/` | Circle / polygon / altitude fence; breach actions RTL / LAND / report. |
| ○ | `AC_InputManager/` | Pilot stick expo / curve shaping for copter manual modes. |
| ★ | `AC_PID/` | PID / PI / P / 2D variants with slew, D-term LPF, anti-windup. |
| ○ | `AC_PrecLand/` | IRLock / companion-computer landing target tracking. |
| ○ | `AC_Sprayer/` | Sprayer pump PWM synced to ground speed for ag missions. |
| ◆ | `AC_WPNav/` | Copter horizontal + vertical waypoint spline / jerk-limited profiles. |
| ★ | `APM_Control/` | Plane roll/pitch/yaw PID + **`AR_AttitudeControl`** for Rover. |
| ○ | `AP_ADC/` | Board ADC scaling helpers for analog sensors. |
| ◆ | `AP_ADSB/` | 1090ES / uAvionix / MAV ADS-B transponder and traffic ingest. |
| ★ | `AP_AHRS/` | Primary attitude/position API: selects DCM vs EKF2 vs EKF3 backends. |
| ◆ | `AP_AIS/` | Marine AIS VDM/VDO parsing and logger integration. |
| ○ | `AP_AccelCal/` | Six-orientation accelerometer calibration + orientation solver. |
| ○ | `AP_AdvancedFailsafe/` | State-machine failsafe beyond simple RTL (geo sequences). |
| ◆ | `AP_Airspeed/` | Pitot, MS5525, DLVR, DroneCAN airspeed backends + health checks. |
| ★ | `AP_Arming/` | Base arming checks; vehicle code registers callbacks. |
| ○ | `AP_Avoidance/` | Thin layer / compatibility declarations around avoidance stack. |
| ◆ | `AP_BLHeli/` | 4-way-if passthrough to configure BLHeli ESCs over servo UART. |
| ★ | `AP_Baro/` | MS5611, BMP280/388, SPL06, ICP101XX, UAVCAN, SITL baro drivers. |
| ★ | `AP_BattMonitor/` | Analog V/I, SMBus smart batteries, UAVCAN, ESC-telemetried sum. |
| ★ | `AP_Beacon/` | Indoor beacon triangulation (Marvelmind / Pozyx class backends). |
| ○ | `AP_BoardConfig/` | Board manifest: BRD_* pins, VBUS, IMU heater, safety switch. |
| ◆ | `AP_Button/` | Debounced GPIO buttons → `BUTTON_CHANGE` events. |
| ★ | `AP_CANManager/` | CAN driver registry, loop threads, frame filtering. |
| ★ | `AP_Camera/` | Distance / time / relay camera triggers; mount angle sync. |
| ○ | `AP_CheckFirmware/` | CRC / signing verification between bootloader and app. |
| ★ | `AP_Common/` | `Location`, `AP_Bitmask`, vehicle type enum, flash string helpers. |
| ★ | `AP_Compass/` | I2C/SPI mag drivers, calibrator, motor interference learning. |
| ★ | `AP_DAL/` | Replay-only façade: EKF reads frozen structs matching log fields. |
| ○ | `AP_Declination/` | WMM coefficients for magnetic declination vs lat/lon/alt. |
| ○ | `AP_Devo_Telem/` | Walkera Devo telemetry framing. |
| ◆ | `AP_EFI/` | Electronic fuel injection protocols (MegaSquirt, NWPM, Lutan, …). |
| ★ | `AP_ESC_Telem/` | Unifies RPM/temp/current from DShot, UAVCAN, Piccolo, Toshiba. |
| ★ | `AP_ExternalAHRS/` | VectorNav / Microstrain external INS as AHRS source. |
| ○ | `AP_FETtecOneWire/` | FETtec ESC telemetry + command on single wire. |
| ○ | `AP_Filesystem/` | FAT / LittleFS / posix wrappers for logs and terrain cache. |
| ○ | `AP_FlashIface/` | Abstract erase/program for external SPI flash chips. |
| ○ | `AP_FlashStorage/` | KVS wear leveling on raw NOR. |
| ★ | `AP_Follow/` | Consumes `FOLLOW_TARGET` / `GLOBAL_POSITION_INT` for follow mode. |
| ◆ | `AP_Frsky_Telem/` | FrSky S.Port / D / MAVlite encoders and passthrough slots. |
| ★ | `AP_GPS/` | Multi-instance GNSS: u-blox, NMEA, Septentrio, SBF, SBP, MAV relay. |
| ★ | `AP_Generator/` | Onboard generator control (fuel pump, starter, RPM, temps). |
| ◆ | `AP_Gripper/` | EPMA / servo gripper open/close/release mission integration. |
| ○ | `AP_GyroFFT/` | On-IMU FFT to suggest harmonic notch centre frequencies. |
| ★ | `AP_HAL/` | Virtual HAL: `HAL::rcin`, `rcout`, `UART`, `I2C`, `scheduler`, `storage`. |
| ★ | `AP_HAL_ChibiOS/` | STM32F4/F7/H7: ChibiOS threads, DMA UART, dshot, RC input. |
| ○ | `AP_HAL_ESP32/` | ESP32-specific drivers and WiFi hooks. |
| ○ | `AP_HAL_Empty/` | Null HAL for port bring-up without hardware. |
| ○ | `AP_HAL_Linux/` | RPI/BBB/Edge: sysfs GPIO, RCInput multiplexer, UDP CAN. |
| ★ | `AP_HAL_SITL/` | Host UDP RC, fake GPIO, wall-clock scheduling for `SITL` models. |
| ○ | `AP_Hott_Telem/` | Graupner HoTT binary telemetry. |
| ◆ | `AP_ICEngine/` | Starter, choke, ignition sequencing for ICE planes. |
| ○ | `AP_IOMCU/` | F103 coprocessor bridge: SBUS in, SBUS/PWM out, safety regs. |
| ◆ | `AP_IRLock/` | IR-LOCK precision landing sensor parsers. |
| ◆ | `AP_InertialNav/` | Legacy complementary filter bridge (superseded by EKF outputs). |
| ★ | `AP_InertialSensor/` | IMU backends, notch filters, fast sampling, batch sampler. |
| ○ | `AP_InternalError/` | `INTERNAL_ERROR()` codes + optional `panic()`. |
| ◆ | `AP_JSButton/` | Joystick button → MAVLink button bitmask tables. |
| ○ | `AP_KDECAN/` | KDE Direct CAN ESC protocol implementation. |
| ★ | `AP_L1_Control/` | L1 lateral guidance law; inherited by plane and `AR_WPNav`. |
| ○ | `AP_LTM_Telem/` | LTM lightweight radio telemetry protocol. |
| ◆ | `AP_Landing/` | Plane landing approach state machine (deepstall, flare). |
| ○ | `AP_LandingGear/` | Retract timing + position feedback. |
| ○ | `AP_LeakDetector/` | Sub leak probes (GPIO / analog). |
| ★ | `AP_Logger/` | Message catalog, ring buffers, backends: FILE, DataFlash, MAVLink. |
| ◆ | `AP_MSP/` | MultiWii MSP for DJI goggles / Betaflight OSD compatibility. |
| ★ | `AP_Math/` | `Vector3f`, `Matrix3f`, `Quaternion`, `wrap_PI`, location projections. |
| ○ | `AP_Menu/` | Deprecated CLI parameter menu over UART. |
| ★ | `AP_Mission/` | Mission storage, `DO_JUMP`, conditional nav, mission protocols. |
| ◆ | `AP_Module/` | Stable C ABI structs for external `.so` sensor fusion modules. |
| ◆ | `AP_Motors/` | Copter motor mixing: matrix, tri, coax, heli, tailsitter, 6DOF. |
| ★ | `AP_Mount/` | Gimbal drivers: Servo, Gremsy, Siyi, STorM32, Viewpro, Sony UART. |
| ◆ | `AP_NMEA_Output/` | Configurable NMEA GGA/RMC export on a UART. |
| ◆ | `AP_NavEKF/` | Original 22-state EKF (legacy; kept for regression / old boards). |
| ◆ | `AP_NavEKF2/` | EKF2 multi-core estimator; still selectable via parameters. |
| ★ | `AP_NavEKF3/` | Primary 24-state EKF3: GPS, mag, baro, OF, RNGFND, wheel ODO. |
| ★ | `AP_Navigation/` | Abstract `nav_roll_cd()`, `lateral_acceleration()` interface. |
| ◆ | `AP_Notify/` | Tone alarm, RGB LED chains, OLED, ProfiLED, scripting LEDs. |
| ○ | `AP_OLC/` | Open Location Code string formatter for OSD. |
| ○ | `AP_ONVIF/` | IP camera discovery via ONVIF WS discovery. |
| ◆ | `AP_OSD/` | Screen layouts, stats panels, MSP + MAX7456 video overlay. |
| ◆ | `AP_OpenDroneID/` | ANSI/CTA-2063-A remote ID message packing and UART export. |
| ★ | `AP_OpticalFlow/` | PX4FLOW, UPixels, CXOF, MAVLink optical flow backends. |
| ◆ | `AP_Parachute/` | Hold-open servo timing for copter/plane parachutes. |
| ★ | `AP_Param/` | `AP_GROUPINFO` tree, defaults, GCS param protocol, FRAM mirror. |
| ○ | `AP_PiccoloCAN/` | Piccolo/Zubax-compatible CAN ESC commands. |
| ★ | `AP_Proximity/` | 360° boundary from lidar towers, LightWare, Cygbot, MAV. |
| ○ | `AP_RAMTRON/` | Ferroelectric RAM driver for params on some boards. |
| ○ | `AP_RCMapper/` | Swaps RC channel order for non-standard receivers. |
| ★ | `AP_RCProtocol/` | Demux SBUS/DSM/CRSF/FPort/IBUS/ST24 into `RCInput` pulses. |
| ○ | `AP_RCTelemetry/` | Cross-protocol telemetry injection (e.g. CRSF CRSFShot). |
| ○ | `AP_ROMFS/` | `ROMFS_*` embedded files (defaults, fonts, Lua applets). |
| ◆ | `AP_RPM/` | Harmonic notch RPM from GPIO, eRPM, EFI, ESC telemetry. |
| ◆ | `AP_RSSI/` | Analog RSSI PWM → percent mapping. |
| ★ | `AP_RTC/` | RTC chip + GPS time sync + timezone helpers. |
| ○ | `AP_Radio/` | 3DR Radio firmware update / configuration UART protocol. |
| ◆ | `AP_Rally/` | Rally point list separate from main mission. |
| ★ | `AP_RangeFinder/` | Benewake, LightWare, LeddarOne, VL53Lx, MAV, CAN, PWM, … |
| ◆ | `AP_Relay/` | AUX relay matrix for camera / parachute / lights. |
| ○ | `AP_RobotisServo/` | Dynamixel packet protocol for serial servos. |
| ◆ | `AP_SBusOut/` | Encodes 16 SBUS channels on UART for external servos. |
| ★ | `AP_Scheduler/` | `AP::scheduler().run()` task slip + perf counters. |
| ★ | `AP_Scripting/` | Lua 5.4 bindings: bindings generator + applets in `libraries/AP_Scripting/applets/`. |
| ○ | `AP_SerialLED/` | WS2812b timing on spare GPIO / UART. |
| ★ | `AP_SerialManager/` | `SERIALn_PROTOCOL` allocation: MAVLink, GPS, RCIN, … |
| ○ | `AP_ServoRelayEvents/` | `DO_REPEAT_SERVO`, timed relay pulses during missions. |
| ★ | `AP_SmartRTL/` | Douglas–Peucker pruned path tree for safe return path. |
| ○ | `AP_Soaring/` | Speed-to-fly / thermal centering for autonomous sailplanes. |
| ◆ | `AP_Stats/` | Flight time, arm count, last arm user — persistent stats. |
| ○ | `AP_TECS/` | Total Energy Control System — height + airspeed for planes. |
| ○ | `AP_TempCalibration/` | Per-IMU temperature polynomial calibration curves. |
| ○ | `AP_TemperatureSensor/` | I2C temperature probes for ESC / ambient logging. |
| ★ | `AP_Terrain/` | SRTM tile cache, `TERRAIN_*` MAVLink, mission prefetch. |
| ★ | `AP_Torqeedo/` | Torqeedo electric marine motor CAN bus interface. |
| ○ | `AP_ToshibaCAN/` | Toshiba CAN ESC driver. |
| ◆ | `AP_Tuning/` | `CH6_OPT` style in-flight multiplier for selected gains. |
| ★ | `AP_UAVCAN/` | DroneCAN node mode: publish ESC, RGB, airspeed, rangefinder. |
| ★ | `AP_Vehicle/` | `AP_Vehicle` base: mode helpers, `set_mode`, shared scheduler hooks. |
| ○ | `AP_VideoTX/` | SmartAudio / Tramp VTX band/power/freq control. |
| ◆ | `AP_VisualOdom/` | VIO pose ingest (Vicon, Intel T265 class backends). |
| ○ | `AP_Volz_Protocol/` | Volz daisy-chain actuator protocol. |
| ★ | `AP_WheelEncoder/` | Quadrature odometry + `AP_WheelRateControl` inner loop. |
| ★ | `AP_Winch/` | Servo winch length / tension modes for delivery / sampling. |
| ★ | `AP_WindVane/` | Wind direction / speed for sailboats; feeds sail modes. |
| ★ | `AR_Motors/` | `AP_MotorsUGV`: skid-steer, omni, sail, walking robot mixing. |
| ★ | `AR_WPNav/` | Rover waypoint follower: L1, OA, pivot turns, reversing. |
| ★ | `Filter/` | `LowPassFilter`, `NotchFilter`, `Butter`, `DerivativeFilter`. |
| ★ | `GCS_MAVLink/` | `GCS` base, routing, mission/rally/fence protocols, FTP, signing. |
| ★ | `PID/` | Legacy single-loop PID (prefer `AC_PID` in new code). |
| ★ | `RC_Channel/` | `RC_Channel`/`RC_Channels`: aux functions, mode switch, options. |
| ★ | `SITL/` | JSON/Zephyr physics interfaces; `SIM_*` models per vehicle. |
| ★ | `SRV_Channel/` | Function-based servo mapping (`k_throttle`, `k_steering`, …). |
| ★ | `StorageManager/` | Flash partition table: params, mission, fence, rally, OA DB. |

---

### 2.2 Category → library map

#### HAL & board

`AP_BoardConfig`, `AP_CheckFirmware`, `AP_Filesystem`, `AP_FlashIface`, `AP_FlashStorage`, `AP_HAL`, `AP_HAL_ChibiOS`, `AP_HAL_ESP32`, `AP_HAL_Empty`, `AP_HAL_Linux`, `AP_HAL_SITL`, `AP_IOMCU`, `AP_InternalError`, `AP_RAMTRON`, `AP_ROMFS`

#### Sensors & drivers

`AP_ADC`, `AP_AccelCal`, `AP_Airspeed`, `AP_Baro`, `AP_Beacon`, `AP_Compass`, `AP_GPS`, `AP_GyroFFT`, `AP_IRLock`, `AP_InertialSensor`, `AP_LeakDetector`, `AP_OpticalFlow`, `AP_Proximity`, `AP_RPM`, `AP_RSSI`, `AP_RangeFinder`, `AP_TempCalibration`, `AP_TemperatureSensor`, `AP_WheelEncoder`

#### State estimation & navigation

`AP_AHRS`, `AP_DAL`, `AP_Declination`, `AP_ExternalAHRS`, `AP_InertialNav`, `AP_L1_Control`, `AP_NavEKF`, `AP_NavEKF2`, `AP_NavEKF3`, `AP_Navigation`, `AP_VisualOdom`

#### Control & motion (airframe)

`AC_AttitudeControl`, `AC_AutoTune`, `AC_Autorotation`, `AC_InputManager`, `AC_PID`, `AC_PrecLand`, `AC_WPNav`, `APM_Control`, `AP_Motors`, `PID`

#### Ground / Rover / boat

`AP_Torqeedo`, `AP_WindVane`, `AR_Motors`, `AR_WPNav`

#### Avoidance, fence, rally, follow

`AC_Avoidance`, `AC_Fence`, `AP_Avoidance`, `AP_Follow`, `AP_Rally`, `AP_SmartRTL`, `AP_Terrain`

#### Plane / heli / special flight

`AC_Sprayer`, `AP_AdvancedFailsafe`, `AP_ICEngine`, `AP_Landing`, `AP_LandingGear`, `AP_Parachute`, `AP_Soaring`, `AP_TECS`

#### Actuators & RC

`AP_BLHeli`, `AP_Button`, `AP_JSButton`, `AP_RCMapper`, `AP_RCProtocol`, `AP_Relay`, `AP_SBusOut`, `AP_SerialLED`, `AP_ServoRelayEvents`, `RC_Channel`, `SRV_Channel`

#### Power & electrical

`AP_BattMonitor`, `AP_EFI`, `AP_Generator`

#### Comms, GCS, telemetry

`AP_Devo_Telem`, `AP_Frsky_Telem`, `AP_Hott_Telem`, `AP_LTM_Telem`, `AP_MSP`, `AP_NMEA_Output`, `AP_RCTelemetry`, `AP_SerialManager`, `GCS_MAVLink`

#### CAN & bus protocols

`AP_CANManager`, `AP_ESC_Telem`, `AP_FETtecOneWire`, `AP_KDECAN`, `AP_PiccoloCAN`, `AP_ToshibaCAN`, `AP_UAVCAN`

#### Safety, arming, identity

`AP_ADSB`, `AP_AIS`, `AP_Arming`, `AP_OpenDroneID`

#### Payloads & mission peripherals

`AP_Camera`, `AP_Gripper`, `AP_Mission`, `AP_Mount`, `AP_OLC`, `AP_ONVIF`, `AP_OSD`, `AP_RobotisServo`, `AP_VideoTX`, `AP_Volz_Protocol`, `AP_Winch`

#### Logging, params, scheduling

`AP_Logger`, `AP_Menu`, `AP_Param`, `AP_Scheduler`, `AP_Stats`, `AP_Tuning`, `StorageManager`

#### Notify & UX

`AP_Notify`

#### Scripting & modules

`AP_Module`, `AP_Scripting`

#### Radio hardware

`AP_Radio`

#### Core math & common

`AP_Common`, `AP_Math`, `Filter`

#### Vehicle abstraction & sim

`AP_RTC`, `AP_Vehicle`, `SITL`

### 2.3 HAL and board bring-up

**Pattern:** Vehicle code calls only `AP_HAL` interfaces; each port implements `HAL` singleton methods. Board selection is compile-time via `hwdef.dat` + `waf` board list.

| Library | Responsibility |
|---------|----------------|
| `AP_HAL/` | Virtual interfaces: `UARTDriver`, `I2CDevice`, `SPIDevice`, `RCInput`, `RCOutput`, `Scheduler`, `Storage`, `GPIO`, `CAN`, `Util`. |
| `AP_HAL_ChibiOS/` | Production STM32: ChibiOS `CH_CFG_*`, DMA UART, DShot, IOMCU bridge, watchdog, MCU reset reason. |
| `AP_HAL_SITL/` | Host simulation: connects to `libraries/SITL/` models via UDP/TCP; no hard real-time. |
| `AP_HAL_Linux/` | Capable boards running Linux kernel; sysfs PWM, RPI GPIO, PPM/SBUS on UART. |
| `AP_HAL_ESP32/` | WiFi-capable autopilots; different flash layout. |
| `AP_HAL_Empty/` | Stub implementations for early porting. |
| `AP_BoardConfig/` | `BOARD_CONFIG` parameters: safety LED, VBUS detect, IMU heater GPIO. |
| `AP_IOMCU/` | Binary protocol to STM32F103 IOMCU (RC in, PWM out, failsafe values). |
| `AP_ROMFS/` | Compile-time file system for default params, fonts, Lua. |
| `AP_Filesystem/` | Run-time FAT / LittleFS on SD or external flash. |
| `AP_FlashIface` + `AP_FlashStorage` | On-chip or external NOR flash KVS for boards without SD. |
| `AP_RAMTRON` | Ferroelectric RAM for fast param commits. |
| `AP_CheckFirmware` | Secure boot chain verification. |
| `AP_InternalError` | Lightweight fault registry (`INTERNAL_ERROR_*`). |

**ChibiOS HAL file clusters** (typical): `hwdef/`, `hwdef/scripts/`, `STM32/*_hw.cpp`, `shared_dma.cpp`, `RCOutput.cpp`, `GPIO.cpp`.

### 2.4 Sensors and drivers — multi-backend breadth

Large ArduPilot libraries use a **singleton + backend** pattern: `AP_<Sensor>::detect()` probes buses; each backend inherits `AP_<Sensor>_Backend` and implements `update()`.

#### AP_RangeFinder — `AP_RangeFinder/` `.cpp` modules

**Count:** 31 translation units (excluding `AP_RangeFinder.cpp` / params).

- `AP_RangeFinder_BBB_PRU`, `AP_RangeFinder_BLPing`, `AP_RangeFinder_Backend`, `AP_RangeFinder_Backend_Serial`, `AP_RangeFinder_Bebop`
- `AP_RangeFinder_Benewake`, `AP_RangeFinder_Benewake_CAN`, `AP_RangeFinder_Benewake_TFMiniPlus`, `AP_RangeFinder_GYUS42v2`, `AP_RangeFinder_HC_SR04`
- `AP_RangeFinder_Lanbao`, `AP_RangeFinder_LeddarOne`, `AP_RangeFinder_LeddarVu8`, `AP_RangeFinder_LightWareI2C`, `AP_RangeFinder_LightWareSerial`
- `AP_RangeFinder_MAVLink`, `AP_RangeFinder_MSP`, `AP_RangeFinder_MaxsonarI2CXL`, `AP_RangeFinder_MaxsonarSerialLV`, `AP_RangeFinder_NMEA`
- `AP_RangeFinder_PWM`, `AP_RangeFinder_PulsedLightLRF`, `AP_RangeFinder_SITL`, `AP_RangeFinder_TeraRangerI2C`, `AP_RangeFinder_UAVCAN`
- `AP_RangeFinder_USD1_CAN`, `AP_RangeFinder_USD1_Serial`, `AP_RangeFinder_VL53L0X`, `AP_RangeFinder_VL53L1X`, `AP_RangeFinder_Wasp`
- `AP_RangeFinder_analog`

#### AP_Baro — `AP_Baro/` `.cpp` modules

**Count:** 21 translation units (excluding `AP_Baro.cpp` / params).

- `AP_Baro_BMP085`, `AP_Baro_BMP280`, `AP_Baro_BMP388`, `AP_Baro_Backend`, `AP_Baro_DPS280`
- `AP_Baro_Dummy`, `AP_Baro_ExternalAHRS`, `AP_Baro_FBM320`, `AP_Baro_HIL`, `AP_Baro_ICM20789`
- `AP_Baro_ICP101XX`, `AP_Baro_ICP201XX`, `AP_Baro_KellerLD`, `AP_Baro_LPS2XH`, `AP_Baro_Logging`
- `AP_Baro_MS5611`, `AP_Baro_MSP`, `AP_Baro_SITL`, `AP_Baro_SPL06`, `AP_Baro_UAVCAN`
- `AP_Baro_Wind`

#### AP_GPS — `AP_GPS/` `.cpp` modules

**Count:** 16 translation units (excluding `AP_GPS.cpp` / params).

- `AP_GPS_ERB`, `AP_GPS_ExternalAHRS`, `AP_GPS_GSOF`, `AP_GPS_MAV`, `AP_GPS_MSP`
- `AP_GPS_NMEA`, `AP_GPS_NOVA`, `AP_GPS_SBF`, `AP_GPS_SBP`, `AP_GPS_SBP2`
- `AP_GPS_SIRF`, `AP_GPS_UAVCAN`, `AP_GPS_UBLOX`, `GPS_Backend`, `MovingBase`
- `RTCM3_Parser`

#### AP_Compass — `AP_Compass/` `.cpp` modules

**Count:** 23 translation units (excluding `AP_Compass.cpp` / params).

- `AP_Compass_AK09916`, `AP_Compass_AK8963`, `AP_Compass_BMM150`, `AP_Compass_Backend`, `AP_Compass_Calibration`
- `AP_Compass_ExternalAHRS`, `AP_Compass_HMC5843`, `AP_Compass_IST8308`, `AP_Compass_IST8310`, `AP_Compass_LIS3MDL`
- `AP_Compass_LSM303D`, `AP_Compass_LSM9DS1`, `AP_Compass_MAG3110`, `AP_Compass_MMC3416`, `AP_Compass_MMC5xx3`
- `AP_Compass_MSP`, `AP_Compass_QMC5883L`, `AP_Compass_RM3100`, `AP_Compass_SITL`, `AP_Compass_UAVCAN`
- `CompassCalibrator`, `Compass_PerMotor`, `Compass_learn`

#### AP_InertialSensor — `AP_InertialSensor/` `.cpp` modules

**Count:** 20 translation units (excluding `AP_InertialSensor.cpp` / params).

- `AP_InertialSensor_ADIS1647x`, `AP_InertialSensor_BMI055`, `AP_InertialSensor_BMI088`, `AP_InertialSensor_BMI160`, `AP_InertialSensor_BMI270`
- `AP_InertialSensor_Backend`, `AP_InertialSensor_ExternalAHRS`, `AP_InertialSensor_Invensense`, `AP_InertialSensor_Invensensev2`, `AP_InertialSensor_Invensensev3`
- `AP_InertialSensor_L3G4200D`, `AP_InertialSensor_LSM9DS0`, `AP_InertialSensor_LSM9DS1`, `AP_InertialSensor_Logging`, `AP_InertialSensor_NONE`
- `AP_InertialSensor_RST`, `AP_InertialSensor_SITL`, `AP_InertialSensor_tempcal`, `AuxiliaryBus`, `BatchSampler`

#### AP_OpticalFlow — `AP_OpticalFlow/` `.cpp` modules

**Count:** 11 translation units (excluding `AP_OpticalFlow.cpp` / params).

- `AP_OpticalFlow_Backend`, `AP_OpticalFlow_CXOF`, `AP_OpticalFlow_Calibrator`, `AP_OpticalFlow_HereFlow`, `AP_OpticalFlow_MAV`
- `AP_OpticalFlow_MSP`, `AP_OpticalFlow_Onboard`, `AP_OpticalFlow_PX4Flow`, `AP_OpticalFlow_Pixart`, `AP_OpticalFlow_SITL`
- `AP_OpticalFlow_UPFLOW`

#### AP_Airspeed — `AP_Airspeed/` `.cpp` modules

**Count:** 12 translation units (excluding `AP_Airspeed.cpp` / params).

- `AP_Airspeed_ASP5033`, `AP_Airspeed_Backend`, `AP_Airspeed_DLVR`, `AP_Airspeed_Health`, `AP_Airspeed_MS4525`
- `AP_Airspeed_MS5525`, `AP_Airspeed_MSP`, `AP_Airspeed_NMEA`, `AP_Airspeed_SDP3X`, `AP_Airspeed_UAVCAN`
- `AP_Airspeed_analog`, `Airspeed_Calibration`

#### AP_Proximity — `AP_Proximity/` `.cpp` modules

**Count:** 14 translation units (excluding `AP_Proximity.cpp` / params).

- `AP_Proximity_AirSimSITL`, `AP_Proximity_Backend`, `AP_Proximity_Backend_Serial`, `AP_Proximity_Boundary_3D`, `AP_Proximity_Cygbot_D1`
- `AP_Proximity_LightWareSF40C`, `AP_Proximity_LightWareSF45B`, `AP_Proximity_LightWareSerial`, `AP_Proximity_MAV`, `AP_Proximity_RPLidarA2`
- `AP_Proximity_RangeFinder`, `AP_Proximity_SITL`, `AP_Proximity_TeraRangerTower`, `AP_Proximity_TeraRangerTowerEvo`

#### AP_RCProtocol — `AP_RCProtocol/` `.cpp` modules

**Count:** 14 translation units (excluding `AP_RCProtocol.cpp` / params).

- `AP_RCProtocol_Backend`, `AP_RCProtocol_CRSF`, `AP_RCProtocol_DSM`, `AP_RCProtocol_FPort`, `AP_RCProtocol_FPort2`
- `AP_RCProtocol_IBUS`, `AP_RCProtocol_PPMSum`, `AP_RCProtocol_SBUS`, `AP_RCProtocol_SRXL`, `AP_RCProtocol_SRXL2`
- `AP_RCProtocol_ST24`, `AP_RCProtocol_SUMD`, `SoftSerial`, `spm_srxl`

#### AP_BattMonitor — `AP_BattMonitor/` `.cpp` modules

**Count:** 19 translation units (excluding `AP_BattMonitor.cpp` / params).

- `AP_BattMonitor_Analog`, `AP_BattMonitor_Backend`, `AP_BattMonitor_Bebop`, `AP_BattMonitor_ESC`, `AP_BattMonitor_FuelFlow`
- `AP_BattMonitor_FuelLevel_PWM`, `AP_BattMonitor_Generator`, `AP_BattMonitor_INA2xx`, `AP_BattMonitor_LTC2946`, `AP_BattMonitor_Logging`
- `AP_BattMonitor_SMBus`, `AP_BattMonitor_SMBus_Generic`, `AP_BattMonitor_SMBus_NeoDesign`, `AP_BattMonitor_SMBus_Rotoye`, `AP_BattMonitor_SMBus_SUI`
- `AP_BattMonitor_SMBus_Solo`, `AP_BattMonitor_Sum`, `AP_BattMonitor_Torqeedo`, `AP_BattMonitor_UAVCAN`

#### AP_Motors (multicopter mixers) — `AP_Motors/` `.cpp` modules

**Count:** 16 translation units (excluding `AP_Motors.cpp` / params).

- `AP_Motors6DOF`, `AP_MotorsCoax`, `AP_MotorsHeli`, `AP_MotorsHeli_Dual`, `AP_MotorsHeli_Quad`
- `AP_MotorsHeli_RSC`, `AP_MotorsHeli_Single`, `AP_MotorsHeli_Swash`, `AP_MotorsMatrix`, `AP_MotorsMatrix_6DoF_Scripting`
- `AP_MotorsMatrix_Scripting_Dynamic`, `AP_MotorsMulticopter`, `AP_MotorsSingle`, `AP_MotorsTailsitter`, `AP_MotorsTri`
- `AP_Motors_Class`

#### AP_Mount (gimbal backends) — `AP_Mount/` `.cpp` modules

**Count:** 9 translation units (excluding `AP_Mount.cpp` / params).

- `AP_Mount_Alexmos`, `AP_Mount_Backend`, `AP_Mount_SToRM32`, `AP_Mount_SToRM32_serial`, `AP_Mount_Servo`
- `AP_Mount_SoloGimbal`, `SoloGimbal`, `SoloGimbalEKF`, `SoloGimbal_Parameters`

#### AP_Notify (LED / buzzer backends) — `AP_Notify/` `.cpp` modules

**Count:** 29 translation units (excluding `AP_Notify.cpp` / params).

- `AP_BoardLED`, `AP_BoardLED2`, `Buzzer`, `DShotLED`, `DiscoLED`
- `DiscreteRGBLed`, `Display`, `Display_SH1106_I2C`, `Display_SITL`, `Display_SSD1306_I2C`
- `ExternalLED`, `Led_Sysfs`, `MMLPlayer`, `NCP5623`, `NavigatorLED`
- `NeoPixel`, `OreoLED_I2C`, `PCA9685LED_I2C`, `PixRacerLED`, `ProfiLED`
- `RCOutputRGBLed`, `RGBLed`, `SITL_SFML_LED`, `ScriptingLED`, `SerialLED`
- `ToneAlarm`, `ToshibaLED_I2C`, `UAVCAN_RGB_LED`, `VRBoard_LED`

#### GCS_MAVLink (MAVLink handlers) — `GCS_MAVLink/` `.cpp` modules

**Count:** 16 translation units (excluding `GCS_MAVLink.cpp` / params).

- `GCS`, `GCS_Common`, `GCS_DeviceOp`, `GCS_Dummy`, `GCS_FTP`
- `GCS_Fence`, `GCS_Param`, `GCS_Rally`, `GCS_ServoRelay`, `GCS_Signing`
- `GCS_serial_control`, `MAVLink_routing`, `MissionItemProtocol`, `MissionItemProtocol_Fence`, `MissionItemProtocol_Rally`
- `MissionItemProtocol_Waypoints`

### 2.5 State estimation — AHRS, DAL, EKF family

**Data flow:** raw IMU (`AP_InertialSensor`) → predict step in `NavEKF3_core` → GPS/mag/baro/rangefinder/flow/wheel updates → `AP_AHRS` reads selected EKF output quaternion + NED states.

#### AP_NavEKF3 — source files

- `AP_NavEKF3.cpp` — fusion / control / logging slice
- `AP_NavEKF3_AirDataFusion.cpp` — fusion / control / logging slice
- `AP_NavEKF3_Control.cpp` — fusion / control / logging slice
- `AP_NavEKF3_GyroBias.cpp` — fusion / control / logging slice
- `AP_NavEKF3_Logging.cpp` — fusion / control / logging slice
- `AP_NavEKF3_MagFusion.cpp` — fusion / control / logging slice
- `AP_NavEKF3_Measurements.cpp` — fusion / control / logging slice
- `AP_NavEKF3_OptFlowFusion.cpp` — fusion / control / logging slice
- `AP_NavEKF3_Outputs.cpp` — fusion / control / logging slice
- `AP_NavEKF3_PosVelFusion.cpp` — fusion / control / logging slice
- `AP_NavEKF3_RngBcnFusion.cpp` — fusion / control / logging slice
- `AP_NavEKF3_VehicleStatus.cpp` — fusion / control / logging slice
- `AP_NavEKF3_core.cpp` — fusion / control / logging slice

#### AP_NavEKF2 — source files

- `AP_NavEKF2.cpp`
- `AP_NavEKF2_AirDataFusion.cpp`
- `AP_NavEKF2_Control.cpp`
- `AP_NavEKF2_Logging.cpp`
- `AP_NavEKF2_MagFusion.cpp`
- `AP_NavEKF2_Measurements.cpp`
- `AP_NavEKF2_OptFlowFusion.cpp`
- `AP_NavEKF2_Outputs.cpp`
- `AP_NavEKF2_PosVelFusion.cpp`
- `AP_NavEKF2_RngBcnFusion.cpp`
- `AP_NavEKF2_VehicleStatus.cpp`
- `AP_NavEKF2_core.cpp`
- `AP_NavEKF_GyroBias.cpp`

#### AP_AHRS — source files

- `AP_AHRS.cpp`
- `AP_AHRS_Backend.cpp`
- `AP_AHRS_DCM.cpp`
- `AP_AHRS_Logging.cpp`
- `AP_AHRS_View.cpp`

#### AP_DAL — replay façade

Each `AP_DAL_<Sensor>.h` mirrors the runtime API but reads packed log structures so `AP_NavEKF3` can execute **identical code paths** during `Tools/Replay` without hardware.

- `AP_DAL.cpp`
- `AP_DAL_Airspeed.cpp`
- `AP_DAL_Baro.cpp`
- `AP_DAL_Beacon.cpp`
- `AP_DAL_Compass.cpp`
- `AP_DAL_GPS.cpp`
- `AP_DAL_InertialSensor.cpp`
- `AP_DAL_RangeFinder.cpp`
- `AP_DAL_VisualOdom.cpp`

### 2.6 Control libraries — multicopter, plane, shared PID

| Library | Vehicle focus | Notes |
|---------|---------------|-------|
| `AC_AttitudeControl/` | Copter | `AC_AttitudeControl_Multi`, `AC_PosControl`, input shaping. |
| `AC_WPNav/` | Copter | Jerk-limited WP + spline nav. |
| `AP_Motors/` | Copter / heli / tailsitter | Matrix, tri, coax, `AP_MotorsHeli_*`, `AP_Motors6DOF`. |
| `APM_Control/` | Plane + **Rover** | `AP_RollController`, `AP_SteerController`, **`AR_AttitudeControl`**. |
| `AC_PID/`, `PID/` | All | Shared control primitives. |
| `AC_AutoTune/` | Copter/plane | Excitation sweeps + gain rules. |
| `AC_InputManager/` | Copter | Stick shaping. |
| `AC_PrecLand/` | Copter | Precision landing controllers. |
| `AC_Autorotation/` | Heli | Autorotation guidance. |

### 2.7 Ground vehicle (`AR_*`) and marine helpers

| Library | Primary classes | Rover integration |
|---------|-----------------|-------------------|
| `AR_WPNav/` | `AR_WPNav` | `Rover.h` member `g2.wp_nav`; used by AUTO, RTL, GUIDED, LOITER. |
| `AR_Motors/` | `AP_MotorsUGV` | `g2.motors`; `set_servos()` → `output(armed, speed, dt)`. |
| `AP_WindVane/` | `AP_WindVane` | Sailboat modes; scheduler task in `Rover.cpp`. |
| `AP_Torqeedo/` | `AP_Torqeedo` | Electric boat main drive; optional on marine Rovers. |

### 2.8 Avoidance, fence, terrain, SmartRTL, rally, follow

| Library | Mechanism |
|---------|-----------|
| `AC_Avoidance/` | `AC_Avoid` velocity limits; `AP_OAPathPlanner` Dijkstra / BendyRuler; `AP_OADatabase` obstacle points; `AP_OAVisGraph`. |
| `AC_Fence/` | Alt + circle + polygon inclusion tests; `FENCE_TYPE` bitmask. |
| `AP_Terrain/` | `TerrainTile` cache; DMA-friendly disk IO; mission prefetch. |
| `AP_SmartRTL/` | FIFO of prune-safe home-return waypoints. |
| `AP_Rally/` | Rally point storage + MAVLink rally protocol. |
| `AP_Follow/` | Subscribes to follow-target telemetry; offset control. |

### 2.9 Actuation — servos, RC protocols, relays

- **`SRV_Channel/`** — assigns each physical output a `SRV_Channel::Function` (e.g. `k_throttle`, `k_steering`, `k_mount_pan`).
- **`RC_Channel/`** — `RC_Channel_aux_func` options (arm, RTL, mode, gripper, scripting triggers).
- **`AP_RCProtocol/`** — interrupt-driven parsers sharing a single UART; auto-detect SBUS vs DSM vs CRSF.
- **`AP_ServoRelayEvents/`** — mission `DO_REPEAT_SERVO` timing.
- **`AP_Relay`**, **`AP_Button`**, **`AP_SerialLED`**, **`AP_SBusOut`** — peripheral actuators.

### 2.10 Power, engine, generator

`AP_BattMonitor` backends cover analog shunt, SMBus smart packs, generator bus, ESC telemetry aggregation, and fuel flow meters. `AP_Generator` and `AP_EFI` extend ICE / hybrid platforms (rare on Rover).

### 2.11 GCS, MAVLink, MSP, and third-party telemetry

**`GCS_MAVLink/`** is one of the largest libraries: vehicle-specific subclasses (`GCS_Rover`, `GCS_Copter`, …) inherit `GCS_MAVLINK` templates for command dispatch, statustext, mission item protocols, parameter transactions, log download, and MAVFTP.

| Library | Role |
|---------|------|
| `GCS_MAVLink/` | Core MAVLink stack + routing + signing hooks. |
| `AP_MSP/` | DJI / Betaflight OSD compatibility layer. |
| `AP_Frsky_Telem/` | FrSky passthrough slots (flight mode, RPM, coords). |
| `AP_Hott_Telem/`, `AP_LTM_Telem/`, `AP_Devo_Telem/` | Vendor radio protocols. |
| `AP_NMEA_Output/` | Export position as NMEA for chartplotters. |
| `AP_SerialManager/` | Declares which UART index runs which protocol. |

### 2.12 CAN, DroneCAN, and vendor ESC buses

`AP_CANManager` starts the CAN thread and registers interfaces. `AP_UAVCAN` publishes node status, actuator commands, and forwards sensor frames into existing backends (GPS, baro, airspeed, rangefinder, compass, battery).

### 2.13 Payloads, OSD, camera, mount, winch

Mission `DO_*` commands invoke `AP_Camera`, `AP_Mount`, `AP_Gripper`, `AP_Winch` helpers. `AP_OSD` composes screen elements independent of vehicle; `AP_VideoTX` sets RF parameters.

### 2.14 Logging, parameters, scheduler, storage layout

- **`AP_Logger`** — `AP_Logger::Write()` packs structs; `LogStructure.h` defines hundreds of message IDs shared with `Tools/LogAnalyzer`.
- **`AP_Param`** — type-safe tree; `AP_Float`, `AP_Int8`, `AP_Vector3f`, vehicle `VAR_INFO` tables.
- **`AP_Scheduler`** — `SCHED_TASK` macro builds const task tables; slip diagnostics in logs.
- **`StorageManager`** — partition offsets avoid mission vs param collisions on small flash.

### 2.15 Notify, scripting, `AP_Module`, SITL

- **`AP_Notify`** — tone vs LED priority arbitration; board-specific LED patterns in `AP_Notify/examples`.
- **`AP_Scripting`** — Lua bindings auto-generated; scripts in ROMFS or SD `APM/scripts`.
- **`AP_Module`** — experimental dynamic linking for external AHRS modules.
- **`SITL/`** — `SIM_*` vehicle dynamics, sensor noise, JSON interface for external physics (Gazebo, JSBSim integration points).

### 2.16 Library → primary façade class (quick lookup)

| Library | Main type(s) to `grep` |
|---------|-------------------------|
| `AP_GPS/` | `AP_GPS` |
| `AP_InertialSensor/` | `AP_InertialSensor` |
| `AP_Compass/` | `Compass` / `AP_Compass` |
| `AP_Baro/` | `AP_Baro` |
| `AP_RangeFinder/` | `RangeFinder` |
| `AP_AHRS/` | `AP_AHRS` |
| `AP_NavEKF3/` | `NavEKF3` |
| `AP_Mission/` | `AP_Mission` |
| `GCS_MAVLink/` | `GCS_MAVLINK`, `GCS` |
| `AP_Param/` | `AP_Param` |
| `AP_Logger/` | `AP_Logger` |
| `AP_Scheduler/` | `AP_Scheduler` |
| `SRV_Channel/` | `SRV_Channels` |
| `RC_Channel/` | `RC_Channels` |
| `AP_HAL/` | `AP_HAL::get_HAL()` |
| `AP_Vehicle/` | `AP_Vehicle` |
| `AR_WPNav/` | `AR_WPNav` |
| `AR_Motors/` | `AP_MotorsUGV` |
| `AC_Fence/` | `AC_Fence` |
| `AC_Avoidance/` | `AC_Avoid`, `AP_OAPathPlanner` |
| `AP_Proximity/` | `AP_Proximity` |
| `AP_WheelEncoder/` | `AP_WheelEncoder` |
| `AP_Terrain/` | `AP_Terrain` |
| `AP_SmartRTL/` | `AP_SmartRTL` |
| `AP_Scripting/` | `AP_Scripting` |

---

## 3. `modules/` — Git Submodules

**Summary:** External dependencies tracked as submodules.

| Submodule | Contents |
|-----------|---------|
| `ChibiOS/` | RTOS for STM32; provides threading, timers, and HAL drivers for the ChibiOS HAL. |
| `mavlink/` | MAVLink v2 message definitions and generated C headers. |
| `DroneCAN/` | DroneCAN (formerly UAVCAN v1) protocol library. |
| `uavcan/` | UAVCAN v0 library (legacy CAN sensors). |
| `gtest/` | Google Test for unit tests in `tests/`. |
| `gbenchmark/` | Google Benchmark framework. |
| `waf/` | Waf build system Python source. |

---

## 4. `Tools/` — Toolchain and Simulation

| Tool | Summary |
|------|---------|
| `Tools/autotest/` | Automated hardware-in-loop and SITL tests (`sim_vehicle.py`, `autotest.py`). |
| `Tools/Replay/` | Log replay tool: replays sensor data from a `.bin` log through the EKF for offline analysis. |
| `Tools/LogAnalyzer/` | Python log analysis: detects vibration, EKF health, GPS glitches. |
| `Tools/ardupilotwaf/` | ArduPilot-specific Waf build rules and board configuration. |
| `Tools/AP_Bootloader/` | Bootloader firmware for STM32 autopilots. |
| `SITL/` (in `libraries/SITL/`) | Software-In-The-Loop simulator: physics model for Rover (`SIM_Rover.cpp`), communicates with SITL HAL via UDP. |

---

## 5. Function → File Cross-Reference (ArduRover)

| Function / Symbol | File | Role |
|-------------------|------|------|
| `Rover::scheduler_tasks[]` | `Rover/Rover.cpp` | Task table; drives every periodic function |
| `Rover::init_ardupilot()` | `Rover/system.cpp` | Boot initialisation |
| `Rover::update_current_mode()` | `Rover/Rover.cpp` | Dispatches `mode->update()` at 400 Hz |
| `Rover::set_servos()` | `Rover/Steering.cpp` | Calls `motors.output()` → PWM |
| `Rover::read_radio()` | `Rover/radio.cpp` | RC stick to control inputs |
| `Rover::failsafe_check()` | `Rover/failsafe.cpp` | Watchdog + GCS heartbeat failsafe |
| `ModeAuto::update()` | `Rover/mode_auto.cpp` | Mission execution loop |
| `ModeGuided::update()` | `Rover/mode_guided.cpp` | External position target tracking |
| `AR_WPNav::update()` | `libraries/AR_WPNav/AR_WPNav.cpp` | Waypoint nav: speed + turn rate demands |
| `AR_WPNav::set_desired_location()` | `libraries/AR_WPNav/AR_WPNav.cpp` | Set next waypoint |
| `AR_AttitudeControl::get_steering_out_heading()` | `libraries/APM_Control/AR_AttitudeControl.cpp` | Heading → steering PID |
| `AR_AttitudeControl::get_throttle_out_speed()` | `libraries/APM_Control/AR_AttitudeControl.cpp` | Speed → throttle PID |
| `AP_MotorsUGV::output()` | `libraries/AR_Motors/AP_MotorsUGV.cpp` | Motor mixing → servo PWM |
| `AP_MotorsUGV::output_skid_steering()` | `libraries/AR_Motors/AP_MotorsUGV.cpp` | Differential drive mixing |
| `AP_L1_Control::update_waypoint()` | `libraries/AP_L1_Control/AP_L1_Control.cpp` | L1 path tracking → lateral accel |
| `NavEKF3::UpdateFilter()` | `libraries/AP_NavEKF3/AP_NavEKF3_core.cpp` | Full EKF predict + update |
| `NavEKF3::FuseVelPosNED()` | `libraries/AP_NavEKF3/AP_NavEKF3_PosVelFusion.cpp` | GPS/position sensor fusion |
| `AP_AHRS::get_position()` | `libraries/AP_AHRS/AP_AHRS.cpp` | Current GPS+EKF position |
| `AP_AHRS::get_yaw()` | `libraries/AP_AHRS/AP_AHRS.cpp` | Heading in radians |
| `AP_Mission::update()` | `libraries/AP_Mission/AP_Mission.cpp` | Advance mission to next command |
| `AC_Avoid::adjust_velocity()` | `libraries/AC_Avoidance/AC_Avoid.cpp` | Proximity avoidance velocity correction |
| `AP_OAPathPlanner::mission_avoidance()` | `libraries/AC_Avoidance/AP_OAPathPlanner.cpp` | Detour path computation |
| `AP_GPS::update()` | `libraries/AP_GPS/AP_GPS.cpp` | Poll all GPS backends |
| `AP_WheelEncoder::update()` | `libraries/AP_WheelEncoder/AP_WheelEncoder.cpp` | Read quadrature encoder ticks |
| `AC_Fence::check_fence()` | `libraries/AC_Fence/AC_Fence.cpp` | Geofence breach detection |
| `AP_SmartRTL::add_point()` | `libraries/AP_SmartRTL/AP_SmartRTL.cpp` | Record outbound breadcrumb |

---

## 6. ArduRover Control Flow Diagram

```
RC Input (50 Hz)          IMU (400 Hz)          GPS (5-20 Hz)
     │                        │                      │
     ▼                        ▼                      ▼
RC_Channels              AP_InertialSensor       AP_GPS
  (read_radio)              (update)              (update)
     │                        │                      │
     │                        └──────────┬───────────┘
     │                                   ▼
     │                          AP_NavEKF3::UpdateFilter()
     │                          (predict + GPS/mag/wheel fuse)
     │                                   │
     │                                   ▼
     │                          AP_AHRS (get_position, get_yaw,
     │                                   get_velocity_NED)
     │                                   │
     ├──────── Mode Update (400 Hz) ─────┤
     │         update_current_mode()     │
     │              │                    │
     │    ┌─────────┴──────────┐         │
     │    │  Active Mode       │         │
     │    │  (e.g. ModeAuto)   │         │
     │    │  .update()         │         │
     │    └─────────┬──────────┘         │
     │              │                    │
     │              ▼                    │
     │    AP_Mission::update()           │
     │    (next command dispatch)        │
     │              │                    │
     │              ▼                    │
     │    AR_WPNav::update(dt)    ◄──────┘  position/yaw
     │    ├─ AP_L1_Control (lat accel)
     │    ├─ AC_Avoid (proximity adjust)
     │    ├─ AP_OAPathPlanner (detour)
     │    └─ outputs: speed_desired, turn_rate_desired
     │              │
     │              ▼
     │    AR_AttitudeControl
     │    ├─ get_steering_out_heading() → AC_PID (yaw rate)
     │    └─ get_throttle_out_speed()  → AC_PID (speed)
     │              │
     ▼              ▼
  AP_MotorsUGV::output()
  ├─ Skid-steer mixing
  ├─ SRV_Channel::set_output_pwm()
  └─ AP_HAL::RCOutput::write()  → ESC / Servo PWM
```
