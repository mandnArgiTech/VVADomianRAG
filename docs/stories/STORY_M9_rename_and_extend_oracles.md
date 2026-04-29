# STORY M9 — Rename `oracle_physics.json` → `oracle_nav2.json` + add missing chapters

**Branch:** `ngspice_rag`  
**Status:** 🔲 TODO  
**Severity:** 🟡 MEDIUM — clarifies file naming + closes coverage gaps

**Depends on:** M7 (chapter-gap fix), M8 (schema validator)

---

## Why rename

`oracle_physics.json` is misleading — it isn't about physics, it's about **Nav2 (ROS 2 Navigation Framework)**. Its 115 chapters all live in `nav2_*` packages from `github.com/ros-navigation/navigation2`. The kinematica oracle would more accurately be called `oracle_ardupilot.json` for the same reason (it covers ArduPilot Rover/libraries), but we'll leave `oracle_kinematica.json` as-is to avoid scope creep — only `oracle_physics.json` needs renaming.

---

## Coverage Audit — Nav2

**Currently covered (35 packages, 115 chapters):**
nav2_amcl, nav2_behavior_tree, nav2_behaviors, nav2_bringup, nav2_bt_navigator,
nav2_collision_monitor, nav2_constrained_smoother, nav2_controller, nav2_core,
nav2_costmap_2d, nav2_docking, nav2_dwb_controller, nav2_following,
nav2_graceful_controller, nav2_lifecycle_manager, nav2_loopback_sim,
nav2_map_server, nav2_mppi_controller, nav2_navfn_planner, nav2_planner,
nav2_regulated_pure_pursuit_controller, nav2_ros_common,
nav2_rotation_shim_controller, nav2_route, nav2_rviz_plugins,
nav2_simple_commander, nav2_smac_planner, nav2_smoother, nav2_system_tests,
nav2_theta_star_planner, nav2_util, nav2_velocity_smoother, nav2_voxel_grid,
nav2_waypoint_follower, navigation2

**Missing from `navigation2` upstream (verified against the live repo):**

| Package | Why it matters | Suggested chapter title |
|---|---|---|
| `nav2_msgs` | Action/service definitions used by every other server | "Nav2 Action and Service Interface Contracts" |
| `nav2_common` | Build-system helpers, parameter declaration utilities | "Nav2 Build System and Parameter Declaration Macros" |
| `dwb_core` | DWB plugin loader + trajectory generator interface | "DWB Plugin Architecture and Trajectory Generator Hooks" |
| `dwb_critics` | All DWB critic classes (path align, goal align, base obstacle, etc.) | "DWB Critic Plugins and Score Aggregation" |
| `dwb_plugins` | Standard goal checkers + simple trajectory generators | "DWB Standard Trajectory Generators and Goal Checkers" |
| `costmap_queue` | Layer update queue used by inflation propagation | "Costmap Queue and Inflation Propagation" |

**Also un- or under-covered topics (worth adding to fill the 76–80 gap from M7):**

| Topic | Files |
|---|---|
| Nav2 Behavior Tree XML loading + custom BT node plugins (deeper than current Ch_002) | `nav2_behavior_tree/src/behavior_tree_engine.cpp`, `nav2_behavior_tree/src/bt_action_node.cpp` |
| BT Navigator state composition + goal lifecycle | `nav2_bt_navigator/src/bt_navigator.cpp`, `nav2_bt_navigator/src/navigators/navigate_to_pose.cpp` |
| Nav2 plugin discovery via pluginlib | `nav2_core/include/nav2_core/*.hpp`, plugin XML manifests |
| Costmap2D inflation cost mathematics deep-dive | `nav2_costmap_2d/plugins/inflation_layer.cpp` |
| Smoother server plugin architecture | `nav2_smoother/src/nav2_smoother.cpp` |

---

## Coverage Audit — ArduPilot Kinematica

**Currently covered (62 prefixes, 150 chapters)** — see `oracle_kinematica.json`.

**Missing ArduPilot subsystems** (verified by directory listing of the upstream `ardupilot/libraries/` tree):

| Library | Chapter topic |
|---|---|
| `AP_Airspeed` | Airspeed sensor backends (analog, MS4525, SDP3X), pitot-static math |
| `AP_RangeFinder` | LiDAR/sonar/ToF backends (LightWare, TFmini, Benewake, etc.) and median-filter math |
| `AP_OpticalFlow` | PMW3901, PX4Flow backends and feature-tracking quality scoring |
| `AP_Beacon` | UWB beacon localization (Pozyx, Marvelmind) trilateration math |
| `AP_OAPathPlanner` | Object-avoidance Bendy-Ruler / Dijkstra path replanner |
| `AP_TerrainHELI` | Helicopter-specific terrain-following hover compensation |
| `AP_KDECAN` / `AP_PiccoloCAN` | Specialty CAN-ESC protocols |
| `AP_RPM` | Tachometer and rotor-RPM sensor backends |
| `AP_TempSensor` (separate from `AP_TemperatureSensor`) | Backend hierarchy for thermistor / TSYS01 / MAX31865 |
| `AP_Volz_Protocol` | Volz servo telemetry (industrial high-torque servos) |
| `AP_Frsky_Telem` | Frsky S.Port / D-port telemetry with EKF status injection |
| `AP_Mount` | Camera-gimbal stabilization (Storm32, Solo, ViewPro, Servo) |
| `AP_Notify` | LED/buzzer state machine — flight-mode → blink pattern math |
| `AP_RPM` | Tachometer fallback (PWM, EFI, harmonic notch) |
| `AP_Stats` | Persistent vehicle-lifetime statistics (flight time, distance) |
| `AP_OSD` plug-ins per backend (`AP_OSD_MAX7456`, `AP_OSD_MSP`, `AP_OSD_SITL`) | Already partly covered (Ch_060–062); a plugin-architecture chapter is missing |
| `AP_Vehicle` | Common vehicle-state base class shared by Rover/Plane/Copter |
| `AC_Loiter` | Loiter mode kinematic state machine (Copter shared with Rover via API) |
| `AP_HAL_QURT` | Qualcomm HAL backend (used for Snapdragon flight controllers) |
| `AP_HAL_ESP32` | ESP32 HAL backend (low-cost flight controller class) |
| `AP_PiccoloCAN` | Currawong Piccolo CAN ESC protocol |
| `AP_DroneCAN` | DroneCAN superseder of `AP_UAVCAN` (ArduPilot is migrating) |

The kinematica oracle is dense; we don't need to add all of these. **Recommended additions (10 chapters):** Airspeed, RangeFinder, OpticalFlow, Beacon, OAPathPlanner, Mount, Notify, Vehicle (base class), Frsky_Telem, DroneCAN.

---

## Implementation Plan

### Phase A — Rename `oracle_physics.json` → `oracle_nav2.json`

**A1. Move the file**

```bash
git mv crewai/oracle_physics.json crewai/oracle_nav2.json
```

**A2. Update every reference**

Search the codebase:
```bash
grep -rn "oracle_physics" crewai/ docs/ README.md  config.yaml || true
```

Update each hit:

| File | Change |
|---|---|
| `crewai/README.md` | Replace `oracle_physics.json` → `oracle_nav2.json` (~1 occurrence in "Operational notes") |
| `crewai/config.yaml` | If `chapter_ledger:` ever pointed at it, rename here too. Today it points at `chapter_ledger.json` — leave that. Add a comment block showing the kinematica/nav2 alternatives. |
| `docs/stories/STORY_M5_*` through `STORY_M8_*` | Search for `oracle_physics` and replace; story M7 specifically references it heavily |
| `docs/stories/` (all M-series) | global find/replace |
| `crewai/scripts/validate_oracle_paths.py` (when M5 lands) | Check for hard-coded paths |
| `crewai/scripts/validate_configs.py` (when M8 lands) | Update the `targets` dict key |
| `crewai/book_factory/cli.py` and any helper modules | Search for any hard-coded `"oracle_physics"` string |

Use this one-shot:
```bash
find . -path ./.git -prune -o -type f \
  \( -name "*.py" -o -name "*.yaml" -o -name "*.md" -o -name "*.json" \) \
  -print 2>/dev/null \
  | xargs grep -l "oracle_physics" 2>/dev/null \
  | xargs sed -i 's/oracle_physics/oracle_nav2/g'
```

**A3. Add a back-compat shim (optional, recommended)**

If anyone has scripts pointing at the old name, soft-link it for one release cycle:

```bash
# Posix only — skip on Windows
( cd crewai && ln -sf oracle_nav2.json oracle_physics.json )
```

Document the symlink in `crewai/README.md` with a deprecation note: "the symlink will be removed in the next refactor."  
**Or** skip the shim entirely if you control all callers — a clean rename is cleaner.

---

### Phase B — Add 6 missing-package chapters to `oracle_nav2.json`

Add these as **new chapter entries** (after renumbering per Story M7, or appended to the end if M7 chose Option B/C). Each follows the existing Nav2 oracle schema (chapter_title, files, research_prompt with CRITICAL H3 directive).

**Suggested chapter slots — append at end (Chapter_121 onward):**

```json
"Chapter_121_Nav2_Action_Service_Interface_Contracts.md": {
  "chapter_title": "Nav2 Action and Service Interface Contracts",
  "files": [
    "nav2_msgs/action/NavigateToPose.action",
    "nav2_msgs/action/ComputePathToPose.action",
    "nav2_msgs/action/FollowPath.action",
    "nav2_msgs/srv/ClearCostmapAroundRobot.srv",
    "nav2_msgs/msg/BehaviorTreeStatusChange.msg"
  ],
  "research_prompt": "Perform a forensic extraction of the Nav2 action/service interface layer in `nav2_msgs`. Write an 'Action Lifecycle Formulation' detailing the goal/feedback/result schema for `NavigateToPose`, `ComputePathToPose`, and `FollowPath`, and explain how clients track multi-second goals via UUID-keyed feedback streams. Write a 'Service Catalog Analysis' covering parameter-clear, costmap-clear, and waypoint-management services. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### NavigateToPose Action Schema (NavigateToPose.action)', '### Costmap Clearing Service Surface (ClearCostmap*.srv)', and '### BehaviorTree Status Streaming (BehaviorTreeStatusChange.msg)'."
},

"Chapter_122_Nav2_Build_System_Param_Macros.md": {
  "chapter_title": "Nav2 Build System and Parameter Declaration Macros",
  "files": [
    "nav2_common/cmake/nav2_package.cmake",
    "nav2_common/launch/rewritten_yaml.py",
    "nav2_common/launch/replace_string.py"
  ],
  "research_prompt": "Perform a forensic extraction of `nav2_common`. Write a 'CMake Build Flag Standardization' section explaining how `nav2_package.cmake` enforces -Werror, sanitizers, and ABI flags across every Nav2 package. Write a 'Launch-Time YAML Rewriting Analysis' detailing how `rewritten_yaml.py` and `replace_string.py` substitute namespaces and topic names at launch without forcing static config files. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Standardized Compiler Flags (nav2_package.cmake)', '### YAML Substitution Engine (rewritten_yaml.py)', and '### Launch String Rewriter (replace_string.py)'."
},

"Chapter_123_DWB_Plugin_Architecture.md": {
  "chapter_title": "DWB Plugin Architecture and Trajectory Generator Hooks",
  "files": [
    "nav2_dwb_controller/dwb_core/src/dwb_local_planner.cpp",
    "nav2_dwb_controller/dwb_core/src/publisher.cpp",
    "nav2_dwb_controller/dwb_core/include/dwb_core/trajectory_generator.hpp",
    "nav2_dwb_controller/dwb_core/include/dwb_core/trajectory_critic.hpp"
  ],
  "research_prompt": "Perform a forensic extraction of the DWB plugin loader infrastructure in `dwb_core`. Write a 'Plugin Discovery and Loading Formulation' detailing how `dwb_local_planner.cpp` uses pluginlib to instantiate trajectory generator and critic plugins from XML manifests at runtime. Write a 'Trajectory Generator Contract Analysis' covering the `TrajectoryGenerator` virtual interface and how candidate trajectories flow through the critic chain to a final score. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Plugin Loading via pluginlib (dwb_local_planner.cpp)', '### TrajectoryGenerator Virtual Interface (trajectory_generator.hpp)', and '### TrajectoryCritic Score Contract (trajectory_critic.hpp)'."
},

"Chapter_124_DWB_Critic_Plugins.md": {
  "chapter_title": "DWB Critic Plugins and Score Aggregation",
  "files": [
    "nav2_dwb_controller/dwb_critics/src/path_align.cpp",
    "nav2_dwb_controller/dwb_critics/src/goal_align.cpp",
    "nav2_dwb_controller/dwb_critics/src/path_dist.cpp",
    "nav2_dwb_controller/dwb_critics/src/goal_dist.cpp",
    "nav2_dwb_controller/dwb_critics/src/base_obstacle.cpp",
    "nav2_dwb_controller/dwb_critics/src/obstacle_footprint.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of every DWB critic plugin in `dwb_critics`. Write a 'Critic Score Mathematics' section detailing the per-cell cost evaluation in path-align, goal-align, path-dist, goal-dist, base-obstacle, and obstacle-footprint critics, including how each weights position vs heading vs swept-volume contributions. Write a 'Score Aggregation Analysis' covering how the local planner sums weighted critic scores into a single trajectory ranking. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Path-Align Heading-Drift Cost (path_align.cpp)', '### Obstacle Footprint Sweep Cost (obstacle_footprint.cpp)', and '### Weighted Score Aggregation (dwb_local_planner.cpp)'."
},

"Chapter_125_DWB_Standard_Generators_GoalCheckers.md": {
  "chapter_title": "DWB Standard Trajectory Generators and Goal Checkers",
  "files": [
    "nav2_dwb_controller/dwb_plugins/src/standard_traj_generator.cpp",
    "nav2_dwb_controller/dwb_plugins/src/limited_accel_generator.cpp",
    "nav2_dwb_controller/dwb_plugins/src/simple_goal_checker.cpp",
    "nav2_dwb_controller/dwb_plugins/src/stopped_goal_checker.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the standard DWB trajectory generators and goal checkers in `dwb_plugins`. Write a 'Trajectory Sampling Math' section explaining how `standard_traj_generator.cpp` samples velocity rectangles within `vmin`/`vmax`/`acc_lim` bounds, and how `limited_accel_generator.cpp` enforces second-order acceleration constraints during sampling. Write a 'Goal Checker State Machine' analysis covering the simple xy-tolerance check vs the stopped-goal-checker's velocity gate. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Velocity Rectangle Sampling (standard_traj_generator.cpp)', '### Acceleration-Limited Sampling (limited_accel_generator.cpp)', and '### Stopped Goal Velocity Gate (stopped_goal_checker.cpp)'."
},

"Chapter_126_Costmap_Queue_Inflation_Propagation.md": {
  "chapter_title": "Costmap Queue and Inflation Cost Propagation",
  "files": [
    "nav2_costmap_2d/plugins/costmap_queue/costmap_queue.cpp",
    "nav2_costmap_2d/plugins/inflation_layer.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the costmap queue used by the inflation layer. Write an 'Inflation Cost Decay Formulation' detailing the exponential cost decay equation `cost = (LETHAL_OBSTACLE - 1) * e^(-decay_rate * d)` and how `costmap_queue.cpp` implements a wave-front BFS to propagate this decay outward from every lethal cell. Write a 'Queue Performance Analysis' explaining how `inflation_layer.cpp` reuses a pre-allocated cell buffer to avoid heap churn during 100Hz costmap updates. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Exponential Cost Decay Math (inflation_layer.cpp)', '### Wave-Front BFS Propagation (costmap_queue.cpp)', and '### Pre-Allocated Cell Buffer Reuse (inflation_layer.cpp)'."
}
```

---

### Phase C — Add 10 missing-subsystem chapters to `oracle_kinematica.json`

Add these at the end (Chapter_151 onward, **after** Story M5/M6 path/CRITICAL fixes land, otherwise the M6 audit will flag these as missing-CRITICAL too).

Each entry follows the existing kinematica oracle schema. Concrete starter blocks:

```json
"Chapter_151_Airspeed_Sensor_Backends_and_Pitot_Math.md": {
  "chapter_title": "Airspeed Sensor Backends and Pitot-Static Math",
  "files": [
    "libraries/AP_Airspeed/AP_Airspeed.cpp",
    "libraries/AP_Airspeed/AP_Airspeed_Backend.cpp",
    "libraries/AP_Airspeed/AP_Airspeed_MS4525.cpp",
    "libraries/AP_Airspeed/AP_Airspeed_SDP3X.cpp",
    "libraries/AP_Airspeed/AP_Airspeed_analog.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the airspeed sensor frontend/backend architecture. Write a 'Pitot-Static Differential Pressure Math' section detailing how `AP_Airspeed.cpp` converts raw differential pressure into true airspeed using `sqrt(2 * delta_p / rho)` with on-the-fly air-density compensation from baro+temp. Write a 'Backend Plugin Hierarchy Analysis' covering MS4525/SDP3X/analog backends and the auto-zeroing routine that trims sensor offsets at startup. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Differential Pressure to Airspeed (AP_Airspeed.cpp)', '### MS4525 I2C Driver (AP_Airspeed_MS4525.cpp)', and '### SDP3X Auto-Zero Sequence (AP_Airspeed_SDP3X.cpp)'."
},

"Chapter_152_RangeFinder_Backends_and_Median_Filtering.md": {
  "chapter_title": "RangeFinder Backends, ToF Drivers, and Median-Filter Math",
  "files": [
    "libraries/AP_RangeFinder/AP_RangeFinder.cpp",
    "libraries/AP_RangeFinder/AP_RangeFinder_Backend.cpp",
    "libraries/AP_RangeFinder/AP_RangeFinder_LightWareI2C.cpp",
    "libraries/AP_RangeFinder/AP_RangeFinder_TFMini.cpp",
    "libraries/AP_RangeFinder/AP_RangeFinder_Benewake.cpp",
    "libraries/AP_RangeFinder/AP_RangeFinder_LeddarOne.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the rangefinder driver hierarchy. Write a 'Median-Filter Smoothing Math' section detailing how `AP_RangeFinder.cpp` runs a 5-sample median filter to reject ToF outliers without introducing the lag that a moving-average would cause. Write a 'Backend Driver Hierarchy Analysis' covering LightWare I2C, TFmini UART, Benewake CAN, and LeddarOne backends, including the auto-detection scan that probes I2C addresses at boot. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### 5-Sample Median Filter Math (AP_RangeFinder.cpp)', '### LightWare I2C Address Probe (AP_RangeFinder_LightWareI2C.cpp)', and '### TFmini UART Frame Parser (AP_RangeFinder_TFMini.cpp)'."
},

"Chapter_153_Optical_Flow_Backends_and_Feature_Tracking.md": {
  "chapter_title": "Optical Flow Backends, PMW3901, and Feature-Tracking Quality",
  "files": [
    "libraries/AP_OpticalFlow/AP_OpticalFlow.cpp",
    "libraries/AP_OpticalFlow/AP_OpticalFlow_PX4Flow.cpp",
    "libraries/AP_OpticalFlow/AP_OpticalFlow_Pixart.cpp",
    "libraries/AP_OpticalFlow/AP_OpticalFlow_HereFlow.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the optical-flow sensor stack. Write a 'Pixel Velocity to Body Velocity Formulation' detailing how `AP_OpticalFlow.cpp` converts raw pixel-shift measurements into body-frame velocity using altitude scaling (`v = pixel_shift * altitude / focal_length`) and gyro-derotation. Write a 'PMW3901 SPI Driver Analysis' covering the bit-banging sequence used for sensor configuration and the surface-quality threshold that suppresses flow on featureless terrain. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Pixel-Shift to Velocity Math (AP_OpticalFlow.cpp)', '### PMW3901 SPI Configuration (AP_OpticalFlow_Pixart.cpp)', and '### Surface Quality Threshold Gating (AP_OpticalFlow.cpp)'."
},

"Chapter_154_Beacon_Trilateration_and_UWB_Positioning.md": {
  "chapter_title": "UWB Beacon Trilateration and Indoor Positioning Math",
  "files": [
    "libraries/AP_Beacon/AP_Beacon.cpp",
    "libraries/AP_Beacon/AP_Beacon_Pozyx.cpp",
    "libraries/AP_Beacon/AP_Beacon_Marvelmind.cpp",
    "libraries/AP_Beacon/AP_Beacon_SITL.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the UWB beacon stack. Write a 'Multi-Beacon Trilateration Math' section detailing how `AP_Beacon.cpp` solves the over-determined least-squares system that converts ≥4 beacon distances into a 3D position fix. Write a 'Pozyx I2C Protocol Analysis' covering the binary frame format and how Marvelmind's UART backend differs in its hedge-position parsing. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Least-Squares Trilateration (AP_Beacon.cpp)', '### Pozyx I2C Frame Format (AP_Beacon_Pozyx.cpp)', and '### Marvelmind UART Hedge Parser (AP_Beacon_Marvelmind.cpp)'."
},

"Chapter_155_Object_Avoidance_Path_Planning_BendyRuler.md": {
  "chapter_title": "Object Avoidance Path Planner: BendyRuler and Dijkstra",
  "files": [
    "libraries/AP_OAPathPlanner/AP_OAPathPlanner.cpp",
    "libraries/AP_OAPathPlanner/AP_OABendyRuler.cpp",
    "libraries/AP_OAPathPlanner/AP_OADijkstra.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the object-avoidance path planner. Write a 'BendyRuler Heuristic Formulation' detailing how `AP_OABendyRuler.cpp` projects candidate vehicle positions along multiple bearing offsets and selects the one that maximizes lookahead clearance. Write a 'Dijkstra Polygon Avoidance Analysis' covering how `AP_OADijkstra.cpp` builds a visibility graph from polygon-fence corners and runs shortest-path search to route around static obstacles. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### BendyRuler Bearing Offset Search (AP_OABendyRuler.cpp)', '### Visibility Graph Construction (AP_OADijkstra.cpp)', and '### Path Replan Trigger Logic (AP_OAPathPlanner.cpp)'."
},

"Chapter_156_Camera_Mount_Gimbal_Stabilization.md": {
  "chapter_title": "Camera Mount Plugins: Storm32, Solo, ViewPro, Servo",
  "files": [
    "libraries/AP_Mount/AP_Mount.cpp",
    "libraries/AP_Mount/AP_Mount_Backend.cpp",
    "libraries/AP_Mount/AP_Mount_Servo.cpp",
    "libraries/AP_Mount/AP_Mount_Storm32_serial.cpp",
    "libraries/AP_Mount/AP_Mount_SoloGimbal.cpp",
    "libraries/AP_Mount/AP_Mount_Viewpro.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the camera-gimbal mount stack. Write an 'Earth-Frame to Gimbal-Frame Math' section detailing how `AP_Mount.cpp` converts target Lat/Lng into roll/pitch/yaw commands using the vehicle's AHRS quaternion to subtract airframe attitude from the desired pointing vector. Write a 'Backend Protocol Analysis' covering the Storm32 serial frame format, Solo Gimbal MAVLink-over-CAN, and the simple PWM servo backend. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Geo-Pointing Vector Math (AP_Mount.cpp)', '### Storm32 Serial Frame Format (AP_Mount_Storm32_serial.cpp)', and '### ViewPro CAN Protocol (AP_Mount_Viewpro.cpp)'."
},

"Chapter_157_Notify_LED_Buzzer_State_Machine.md": {
  "chapter_title": "Notify Subsystem: LED Patterns and Audible Alarm State Machine",
  "files": [
    "libraries/AP_Notify/AP_Notify.cpp",
    "libraries/AP_Notify/RGBLed.cpp",
    "libraries/AP_Notify/Buzzer.cpp",
    "libraries/AP_Notify/ToshibaLED_I2C.cpp",
    "libraries/AP_Notify/NeoPixel.cpp",
    "libraries/AP_Notify/Display.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the operator-notification subsystem. Write a 'Flight-Mode to Blink Pattern Map' detailing the state machine in `AP_Notify.cpp` that translates flight modes, EKF status, and arming state into per-LED RGB patterns and per-buzzer tone sequences. Write a 'NeoPixel Bit-Banged Timing Analysis' covering the precise nanosecond-level WS2812 protocol implementation in `NeoPixel.cpp`. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Flight-Mode to RGB State Table (AP_Notify.cpp)', '### Buzzer Tone Sequencer (Buzzer.cpp)', and '### NeoPixel WS2812 Bit-Bang Timing (NeoPixel.cpp)'."
},

"Chapter_158_AP_Vehicle_Common_Base_Class_and_Loop.md": {
  "chapter_title": "AP_Vehicle Common Base Class and Shared Loop Infrastructure",
  "files": [
    "libraries/AP_Vehicle/AP_Vehicle.cpp",
    "libraries/AP_Vehicle/AP_Vehicle.h"
  ],
  "research_prompt": "Perform a forensic extraction of the `AP_Vehicle` base class shared by Rover, Plane, and Copter. Write a 'Common Loop Scheduling Architecture' detailing how `AP_Vehicle.cpp` provides a unified `loop()` and `setup()` lifecycle plus the standardized `update_arming_checks()` virtual that every vehicle subclass overrides. Write a 'Sensor and Logging Bootstrap Analysis' covering the singleton pattern that gives the EKF, AHRS, and Logger their cross-vehicle dependencies. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### Common Setup and Loop Lifecycle (AP_Vehicle.cpp)', '### Vehicle-Wide Singleton Bootstrap (AP_Vehicle.cpp)', and '### Virtual Arming Check Hook (AP_Vehicle.h)'."
},

"Chapter_159_Frsky_SmartPort_Telemetry.md": {
  "chapter_title": "FrSky S.Port and D-Port Telemetry Bridges",
  "files": [
    "libraries/AP_Frsky_Telem/AP_Frsky_Telem.cpp",
    "libraries/AP_Frsky_Telem/AP_Frsky_SPort.cpp",
    "libraries/AP_Frsky_Telem/AP_Frsky_SPort_Passthrough.cpp",
    "libraries/AP_Frsky_Telem/AP_Frsky_D.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the FrSky telemetry stack. Write a 'S.Port Frame Encoding Math' section detailing the byte-stuffing protocol used by `AP_Frsky_SPort.cpp` to encode EKF status, GPS coordinates, and battery telemetry into 8-byte sensor frames at 9600 baud. Write a 'Passthrough Protocol Analysis' covering how `AP_Frsky_SPort_Passthrough.cpp` packs ArduPilot-specific status (flight mode, AP custom messages) into the standard FrSky frame ID space. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### S.Port Byte-Stuffing Encoder (AP_Frsky_SPort.cpp)', '### AP Passthrough Frame ID Map (AP_Frsky_SPort_Passthrough.cpp)', and '### Legacy D-Port Sensor Hub Format (AP_Frsky_D.cpp)'."
},

"Chapter_160_DroneCAN_Migration_from_UAVCAN.md": {
  "chapter_title": "DroneCAN Stack and Migration from Legacy UAVCAN",
  "files": [
    "libraries/AP_DroneCAN/AP_DroneCAN.cpp",
    "libraries/AP_DroneCAN/AP_DroneCAN.h",
    "libraries/AP_DroneCAN/AP_DroneCAN_DNA_Server.cpp",
    "libraries/AP_DroneCAN/AP_DroneCAN_serial.cpp"
  ],
  "research_prompt": "Perform a forensic extraction of the DroneCAN stack that supersedes legacy `AP_UAVCAN`. Write a 'Dynamic Node Allocation (DNA) Math' section detailing how `AP_DroneCAN_DNA_Server.cpp` assigns persistent node IDs to anonymous CAN devices via a hash-based handshake. Write a 'CAN-over-Serial Tunneling Analysis' covering how `AP_DroneCAN_serial.cpp` bridges DroneCAN frames over a regular UART for development and debugging. CRITICAL: In the 'C++ Implementation' section, use '###' (H3) headers: '### DNA Hash Handshake Sequence (AP_DroneCAN_DNA_Server.cpp)', '### CAN Frame Multiplexer and Filters (AP_DroneCAN.cpp)', and '### Serial Tunnel Frame Encapsulation (AP_DroneCAN_serial.cpp)'."
}
```

---

## Verification

```bash
# 1. Old name removed everywhere
! grep -rn "oracle_physics" crewai/ docs/ README.md config.yaml

# 2. New name shows up where expected
grep -rn "oracle_nav2" crewai/ docs/

# 3. Both files validate (after M5/M6/M7/M8 land)
python3 crewai/scripts/validate_configs.py

# 4. Chapter-count sanity
python3 -c "
import json
nav2 = json.load(open('crewai/oracle_nav2.json'))
ki = json.load(open('crewai/oracle_kinematica.json'))
print(f'oracle_nav2.json:        {len(nav2)} chapters')
print(f'oracle_kinematica.json:  {len(ki)} chapters')
"
```

Expected output (assuming Phase A + B + C all land):
- `oracle_nav2.json`: 121 chapters (115 existing + 6 new)
- `oracle_kinematica.json`: 160 chapters (150 existing + 10 new)

If Story M7 chose Option A (filling 76–80), nav2 will be 126 chapters.

---

## Acceptance Criteria

- [ ] **Phase A:** `crewai/oracle_physics.json` renamed to `crewai/oracle_nav2.json` via `git mv` (preserves history).
- [ ] **Phase A:** Zero remaining references to `oracle_physics` anywhere in the repo (`grep -r oracle_physics` returns empty).
- [ ] **Phase A:** `crewai/README.md`, `crewai/config.yaml`, all M-series stories, and any helper scripts updated to reference `oracle_nav2.json`.
- [ ] **Phase B:** 6 new Nav2 chapters added covering `nav2_msgs`, `nav2_common`, `dwb_core`, `dwb_critics`, `dwb_plugins`, `costmap_queue`.
- [ ] **Phase B:** Each new chapter contains the `CRITICAL: '###' (H3) headers: ...` directive with file-specific sub-section names.
- [ ] **Phase C:** 10 new ArduPilot kinematica chapters added covering Airspeed, RangeFinder, OpticalFlow, Beacon, OAPathPlanner, Mount, Notify, AP_Vehicle, Frsky_Telem, DroneCAN.
- [ ] **Phase C:** Each new kinematica chapter uses `libraries/<DIR>/<file>` paths (no bare filenames — Story M5 rule).
- [ ] **Phase C:** Each new kinematica chapter contains the `CRITICAL` directive (Story M6 rule).
- [ ] All five JSON files (`oracle_nav2.json`, `oracle_kinematica.json`, `chapter_ledger.json`, `project_prompts_*.json`) parse as valid JSON.
- [ ] After M5–M8 land, `python3 crewai/scripts/validate_configs.py` exits 0 against `oracle_nav2.json` and `oracle_kinematica.json`.
- [ ] Committed as a single commit: `refactor(crewai): rename oracle_physics→oracle_nav2 and add 16 new chapters (6 nav2 + 10 ardupilot)`.
