# STORY G: Multi-Domain Support (5 Domains) and Domain-Agnostic Infrastructure Fixes

**Repository:** `mandnArgiTech/VVADomianRAG` branch `ngspice_rag`
**Priority:** High
**Estimated effort:** 5–6 hours
**Files to modify:** `query.py`, `mcp_server.py`, `concept_registry.json`, `ingest.py`
**Files to create:** `system_prompts/kinematica_engineer.md`, `system_prompts/mujoco_engineer.md`, `system_prompts/nav2_engineer.md`, `system_prompts/dart_engineer.md`, `tests/test_multi_domain.py`

---

## Business Context

VVADomainRAG now needs to serve **five codebases** across three engineering domains:

| Domain | Codebase | Language | Purpose |
|---|---|---|---|
| `spice` | ngspice C source + NodalAI Python | C, Python | Circuit simulation kernel hardening |
| `kinematica` | ArduPilot/ArduRover | C++ | Varaham agricultural rover firmware |
| `mujoco` | MuJoCo physics engine | C, C++ | Ghar Ki Rani robot digital twin simulation |
| `nav2` | Nav2 (ROS 2 Navigation) | C++, Python | Robot navigation stack |
| `dart` | DART physics engine | C++ | Dynamics and robotics simulation |

The ingestion pipeline (tree-sitter AST, call-graph, structural importance, hybrid search, reranker) is already domain-agnostic. But three infrastructure issues limit multi-domain effectiveness:

1. **`query.py` persona hardcoded to ngspice** — non-SPICE queries get ngspice terminology in the system prompt
2. **Domain filter uses substring match** — fragile, could collide (e.g., `--domain art` matches `dart_code`)
3. **No concept registries or system prompts for 3 of 5 domains** — MuJoCo/Nav2/DART code chunks get zero concept tags

---

## Acceptance Criteria

### AC-1: Default system prompt changed to generic

**Given** `query.py` line 227: `DEFAULT_SYSTEM_PROMPT = _NGSPICE_SYSTEM_PROMPT`,
**When** this story is complete,
**Then**:
- `DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT`
- Persona auto-switch fallback at line ~1330 uses `_GENERIC_SYSTEM_PROMPT` not `_NGSPICE_SYSTEM_PROMPT`
- Domain-specific expertise comes from `system_prompts/{domain}_engineer.md` files (existing Story D mechanism)
- The `_NGSPICE_SYSTEM_PROMPT` string is NOT deleted — remains in `DEFAULT_SYSTEM_PROMPTS["ngspice"]` dict for backward compat

### AC-2: Domain filter uses prefix match, not substring

**Given** `_domain_filter()` in both `mcp_server.py` (line 558) and `query.py` (line 692),
**When** this story is complete,
**Then** the filter uses prefix matching:

```python
# Before (substring — fragile):
return [n for n in names if d in n.lower()]

# After (prefix — safe):
return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]
```

This prevents `--domain art` from matching `dart_code`, while still allowing `--domain dart` to match `dart_code` and `dart_domain`.

### AC-3: Concept registry for all 5 domains

**Given** `concept_registry.json`,
**When** this story is complete,
**Then** all 5 domains have entries. Existing `"spice"` domain (62 entries) is unchanged. New domains:

**`"kinematica"` (45+ entries):**
```json
{
    "EKF": "extended_kalman_filter", "EKF2": "extended_kalman_filter_v2",
    "EKF3": "extended_kalman_filter_v3", "DCM": "direction_cosine_matrix",
    "AHRS": "attitude_heading_reference", "MAVLink": "mavlink_protocol",
    "DShot": "digital_shot_protocol", "PID": "pid_controller",
    "GCS": "ground_control_station", "HAL": "hardware_abstraction_layer",
    "AP_NavEKF": "navigation_ekf", "AP_Motors": "motor_output",
    "AP_AHRS": "ahrs_system", "RC_Channel": "rc_input_channel",
    "SRV_Channel": "servo_output_channel", "ChibiOS": "chibios_rtos",
    "ArduPilot": "ardupilot_firmware", "ArduRover": "ardurover_vehicle",
    "PWM": "pulse_width_modulation", "I2C": "i2c_bus", "SPI": "spi_bus",
    "CAN": "can_bus", "DroneCAN": "dronecan_protocol",
    "UAVCAN": "uavcan_protocol", "PPM": "ppm_input", "SBUS": "sbus_protocol",
    "NMEA": "nmea_protocol", "RTK": "real_time_kinematic",
    "Pure_Pursuit": "pure_pursuit_navigation", "L1": "l1_navigation_controller",
    "geofence": "geofence_containment", "failsafe": "failsafe_handler",
    "arming": "arming_checks", "WP_Nav": "waypoint_navigation",
    "AP_Scheduler": "task_scheduler", "DataFlash": "dataflash_logging",
    "AP_Logger": "logging_system", "AP_Baro": "barometer_driver",
    "AP_Compass": "compass_driver", "AP_InertialSensor": "imu_driver",
    "AP_GPS": "gps_driver", "AP_RangeFinder": "rangefinder_driver",
    "AP_OpticalFlow": "optical_flow_driver", "LowPassFilter": "low_pass_filter",
    "NotchFilter": "notch_filter", "Steering": "steering_controller"
}
```

**`"mujoco"` (30+ entries):**
```json
{
    "mjModel": "mujoco_model_struct", "mjData": "mujoco_data_struct",
    "mjContact": "contact_struct", "mj_step": "simulation_step",
    "mj_forward": "forward_dynamics", "mj_inverse": "inverse_dynamics",
    "mj_collision": "collision_detection", "mj_constraint": "constraint_solver",
    "mj_Euler": "euler_integrator", "mj_RK4": "runge_kutta_integrator",
    "mj_implicit": "implicit_integrator", "mjcf": "mujoco_xml_format",
    "geom": "geometry_primitive", "tendon": "tendon_element",
    "actuator": "actuator_element", "qpos": "generalized_position",
    "qvel": "generalized_velocity", "qacc": "generalized_acceleration",
    "ctrl": "control_input", "xfrc": "external_force",
    "Jacobian": "jacobian_matrix", "inertia": "inertia_tensor",
    "free_joint": "free_floating_joint", "hinge": "hinge_joint",
    "slide": "slide_joint", "ball": "ball_joint",
    "PGS": "projected_gauss_seidel", "CG": "conjugate_gradient",
    "Newton": "newton_solver", "sensor": "sensor_element",
    "MJX": "mujoco_xla_backend"
}
```

**`"nav2"` (30+ entries):**
```json
{
    "nav2": "navigation2_stack", "planner": "path_planner",
    "controller": "trajectory_controller", "costmap": "costmap_2d",
    "behavior_tree": "behavior_tree_navigator", "BT": "behavior_tree",
    "DWB": "dwb_controller", "TEB": "timed_elastic_band",
    "MPPI": "model_predictive_path_integral",
    "NavFn": "navigation_function_planner", "Smac": "smac_planner",
    "A_star": "a_star_search", "Theta_star": "theta_star_search",
    "lifecycle": "ros2_lifecycle_node", "action_server": "ros2_action_server",
    "tf2": "transform_library", "odometry": "odometry_source",
    "amcl": "adaptive_monte_carlo_localization",
    "slam_toolbox": "slam_toolbox", "recovery": "recovery_behavior",
    "spin": "spin_recovery", "backup": "backup_recovery",
    "wait": "wait_recovery", "goal_checker": "goal_checker",
    "progress_checker": "progress_checker", "voxel_layer": "voxel_costmap_layer",
    "inflation_layer": "inflation_costmap_layer",
    "obstacle_layer": "obstacle_costmap_layer",
    "global_planner": "global_path_planner",
    "local_planner": "local_trajectory_planner",
    "waypoint_follower": "waypoint_follower"
}
```

**`"dart"` (25+ entries):**
```json
{
    "Skeleton": "dart_skeleton", "BodyNode": "body_node",
    "Joint": "joint_element", "DegreeOfFreedom": "degree_of_freedom",
    "ShapeNode": "shape_node", "FreeJoint": "free_joint",
    "RevoluteJoint": "revolute_joint", "PrismaticJoint": "prismatic_joint",
    "WeldJoint": "weld_joint", "BallJoint": "ball_joint",
    "InverseKinematics": "inverse_kinematics", "Inertia": "inertia_tensor",
    "WorldFrame": "world_reference_frame",
    "CollisionDetector": "collision_detector",
    "ConstraintSolver": "constraint_solver",
    "BoxedLcpSolver": "boxed_lcp_solver",
    "DantzigLcpSolver": "dantzig_lcp_solver",
    "SimulationWorld": "simulation_world",
    "Featherstone": "featherstone_algorithm",
    "CRBA": "composite_rigid_body_algorithm",
    "ABA": "articulated_body_algorithm",
    "RNE": "recursive_newton_euler",
    "URDF": "unified_robot_description",
    "SDF": "simulation_description_format",
    "Jacobian": "jacobian_matrix", "MassMatrix": "mass_matrix"
}
```

### AC-4: System prompts for all 4 new domains

Create `system_prompts/kinematica_engineer.md`, `system_prompts/mujoco_engineer.md`, `system_prompts/nav2_engineer.md`, `system_prompts/dart_engineer.md` with domain-specific prompts. Each prompt should:
- State the engineering role and codebase context
- List 4–5 specific debugging steps relevant to that domain
- End with "Only reference function and symbol names present in the provided RAG context."

See the full prompt text for each domain in the Implementation Guide below.

### AC-5: Studio-Portable-RAG copies synced

`Studio-Portable-RAG/concept_registry.json`, all `Studio-Portable-RAG/system_prompts/*.md` files, and `_domain_filter` in `Studio-Portable-RAG/query.py` and `Studio-Portable-RAG/mcp_server.py` must match root copies.

### AC-6: Ingest commands documented

Add to `README.md` a "Multi-Domain Ingestion" section:

```bash
# All domains use the same embedding model
export EMBEDDING_MODEL=mxbai-embed-large

# SPICE (ngspice + NodalAI)
./run.sh --mode code --domain spice --source /path/to/ngspice/src
./run.sh --mode code --domain spice --source /path/to/NodalAI/ecad
./run.sh --mode domain --domain spice --source ./Studio-Portable-RAG/DomainDocs/ngspice

# Kinematica (ArduPilot/ArduRover)
./run.sh --mode code --domain kinematica --source /path/to/ardupilot
./run.sh --mode domain --domain kinematica --source ./Studio-Portable-RAG/DomainDocs/kinematica

# MuJoCo
./run.sh --mode code --domain mujoco --source /path/to/mujoco/src

# Nav2
./run.sh --mode code --domain nav2 --source /path/to/navigation2

# DART
./run.sh --mode code --domain dart --source /path/to/dart
```

### AC-7: All existing tests pass

`pytest tests/` — 0 failures.

---

## Implementation Guide

### Step 1: Fix DEFAULT_SYSTEM_PROMPT in query.py (line 227)
```python
DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT
```

### Step 2: Fix persona auto-switch fallback (line ~1330)
```python
        else:
            base = _GENERIC_SYSTEM_PROMPT
```

### Step 3: Fix _domain_filter in BOTH files

**`mcp_server.py` line 558 AND `query.py` line 692:**
```python
def _domain_filter(names: List[str], domain: str) -> List[str]:
    d = domain.strip().lower()
    if not d or d == "general":
        return names
    return [n for n in names if n.lower().startswith(d + "_") or n.lower() == d]
```

### Step 4: Add all concept registries to concept_registry.json
Add `"kinematica"`, `"mujoco"`, `"nav2"`, `"dart"` domains with entries from AC-3.

### Step 5: Create 4 system prompt files
Content specified in AC-4.

**`system_prompts/kinematica_engineer.md`:**
Embedded systems / ArduPilot focus. ChibiOS RTOS, EKF, DCM, MAVLink, sensor drivers, failsafe. Debug steps: sensor health → EKF innovations → mode transitions → motor output.

**`system_prompts/mujoco_engineer.md`:**
Physics simulation focus. mjModel/mjData, forward/inverse dynamics, contact solver, integrator selection. Debug steps: contact params → integrator/timestep → actuator config → solver iterations.

**`system_prompts/nav2_engineer.md`:**
ROS 2 navigation focus. Planners, controllers, costmap layers, behavior trees, lifecycle nodes. Debug steps: costmap config → planner params → controller tuning → BT recovery.

**`system_prompts/dart_engineer.md`:**
Dynamics simulation focus. Skeleton/BodyNode hierarchy, Featherstone (ABA/CRBA/RNE), LCP constraint solvers, URDF/SDF loading. Debug steps: joint config → mass/inertia → constraint solver → timestep.

### Step 6: Sync Studio-Portable-RAG
```bash
cp concept_registry.json Studio-Portable-RAG/
cp -r system_prompts/ Studio-Portable-RAG/
```
Also apply `_domain_filter` fix to Studio copies.

### Step 7: Update README with multi-domain ingest section

---

## Test Plan

### File: `tests/test_multi_domain.py`

```
Test ID | Description | Approach
--------|-------------|----------
MD-01   | DEFAULT_SYSTEM_PROMPT is _GENERIC | assert query.DEFAULT_SYSTEM_PROMPT == query._GENERIC_SYSTEM_PROMPT
MD-02   | Auto-switch uses generic for code results without domain | Mock code hits, no domain. Assert base is _GENERIC not _NGSPICE
MD-03   | domain=spice loads spice_engineer.md | Assert spice prompt content prepended
MD-04   | domain=kinematica loads kinematica_engineer.md | Assert kinematica prompt prepended
MD-05   | domain=mujoco loads mujoco_engineer.md | Assert mujoco prompt prepended
MD-06   | domain=nav2 loads nav2_engineer.md | Assert nav2 prompt prepended
MD-07   | domain=dart loads dart_engineer.md | Assert dart prompt prepended
MD-08   | _domain_filter: dart matches dart_code only | names=["dart_code","standard_code"]. domain="dart" → ["dart_code"]
MD-09   | _domain_filter: art does NOT match dart_code | names=["dart_code"]. domain="art" → []
MD-10   | _domain_filter: nav does NOT match nav2_code | names=["nav2_code"]. domain="nav" → []. domain="nav2" → ["nav2_code"]
MD-11   | _domain_filter: empty domain returns all | domain="" → all names
MD-12   | concept_registry has all 5 domains | Assert "spice","kinematica","mujoco","nav2","dart" all present
MD-13   | kinematica concepts tag EKF correctly | Text "EKF" → concept "extended_kalman_filter"
MD-14   | mujoco concepts tag mjModel correctly | Text "mjModel" → concept "mujoco_model_struct"
MD-15   | nav2 concepts tag costmap correctly | Text "costmap" → concept "costmap_2d"
MD-16   | dart concepts tag Skeleton correctly | Text "Skeleton" → concept "dart_skeleton"
MD-17   | All 5 system prompt files exist | Assert all 5 .md files in system_prompts/
MD-18   | No domain → no forced prompt | domain="" → _load_system_prompt returns ""
MD-19   | Studio concept_registry synced | Compare root vs Studio, all 5 domains match
MD-20   | _domain_filter identical in mcp_server and query | Compare function source
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Changing DEFAULT_SYSTEM_PROMPT breaks spice queries | No — `system_prompts/spice_engineer.md` loaded for `--domain spice` regardless |
| Prefix domain filter breaks existing spice queries | `"spice_code".startswith("spice_")` = True. No breakage. |
| `_device_family_for_path` returns "CORE" for all non-ngspice | Acceptable. Concept registry provides domain semantics instead. |
| Semantic chunk typing doesn't fire for non-ngspice | Correct and harmless. Non-SPICE functions get generic `function_definition` type. |
| Too many concept registry entries slow ingest | Only active domain's entries checked. 200 total across 5 domains, ~40 per domain. No issue. |
| MuJoCo C core vs C++ bindings | Tree-sitter handles both C and C++. Strategy routing selects correct grammar by file extension. |
| Nav2 uses ROS 2 CMake/ament build | Build files skipped. Only `.cpp`/`.py`/`.h` files ingested. |

---

## Definition of Done

- [ ] `DEFAULT_SYSTEM_PROMPT = _GENERIC_SYSTEM_PROMPT` in `query.py`
- [ ] Persona auto-switch fallback uses `_GENERIC_SYSTEM_PROMPT`
- [ ] `_domain_filter` uses prefix match in `mcp_server.py`, `query.py`, and both Studio copies
- [ ] `concept_registry.json` has all 5 domains: spice (62), kinematica (45+), mujoco (30+), nav2 (30+), dart (25+)
- [ ] 5 system prompt files: `spice_engineer.md`, `kinematica_engineer.md`, `mujoco_engineer.md`, `nav2_engineer.md`, `dart_engineer.md`
- [ ] Studio-Portable-RAG fully synced
- [ ] README documents multi-domain ingest commands
- [ ] All 20 new tests pass, all existing tests pass
