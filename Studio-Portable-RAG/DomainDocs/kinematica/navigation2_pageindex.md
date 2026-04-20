# Nav2 (ROS 2 Navigation2) — PageIndex

> **Purpose:** Hierarchical index of the **Navigation2** (`navigation2`) repository — the ROS 2 Nav2 stack for mobile robots — structured for RAG navigation, in the same spirit as [PageIndex](https://github.com/VectifyAI/PageIndex). Upstream: [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2); documentation: [docs.nav2.org](https://docs.nav2.org/).

**Tree snapshot:** This workspace copy is **Nav2 1.4.x** (see `<version>` in `package.xml` files under `nav2_core/` and peers).

## Document map

| § | Topic |
|---|--------|
| §0 | [Repository root](#0-repository-root) |
| §1 | [Architecture](#1-architecture-lifecycle-actions-behavior-trees) |
| §2 | [Package catalog](#2-full-package-catalog) (master index, categories, BT/costmap/Smac/DWB depth) |
| §3 | [`doc/` and `tools/`](#3-doc-and-tools) |
| §4 | [Data-flow diagram](#4-runtime-data-flow-nav2) |
| §5 | [Package → artifacts](#5-package--primary-artifacts) |
| §6 | [Configs & plugins](#6-configs-plugin-xml-and-bringup) |

**Legend (§2.1):** `★` core stack bringup path · `◆` common plugin/server family · `○` nested or specialist package.

---

## 0. Repository root

**Summary:** Monorepo of **ament/colcon** packages. Top-level folders are mostly `nav2_*` ROS packages; **`nav2_docking/`**, **`nav2_dwb_controller/`**, and **`nav2_following/`** contain additional nested packages. **`navigation2/`** is the metapackage that depends on the full stack.

```
navigation2/
├── navigation2/          ← metapackage (depends on stack)
├── nav2_bringup/         ← launch, params, maps, RViz configs
├── nav2_msgs/            ← actions, srv, msg
├── nav2_util/ nav2_common/ nav2_ros_common/
├── nav2_core/            ← plugin base classes (headers)
├── nav2_costmap_2d/ nav2_voxel_grid/
├── nav2_map_server/
├── nav2_amcl/
├── nav2_planner/ nav2_smoother/ nav2_controller/
├── nav2_bt_navigator/ nav2_behavior_tree/ nav2_behaviors/
├── nav2_*_planner/ nav2_*_controller/ … (plugin implementations)
├── nav2_lifecycle_manager/
├── nav2_waypoint_follower/ nav2_velocity_smoother/
├── nav2_collision_monitor/
├── nav2_docking/         ← opennav_docking{,_bt,_core}
├── nav2_dwb_controller/← dwb_*, nav_2d_*, nav2_dwb_controller
├── nav2_following/       ← opennav_following
├── doc/ tools/ .github/
└── README.md Dockerfile Doxyfile …
```

---

## 1. Architecture (lifecycle, actions, behavior trees)

**Sense–plan–act (Nav2):** Map / TF / sensors feed **costmaps** and **localization** (`nav2_amcl`). **Global planner** plugins compute a path; **smoother** plugins optionally refine it. **Controller** plugins produce cmd_vel from the local costmap and path. **Behavior tree** (`nav2_bt_navigator`) orchestrates navigate-to-pose, recovery, and docking/following task servers.

**Lifecycle:** Managed nodes transition `unconfigured → inactive → active` via `nav2_lifecycle_manager` (responds to `ManageLifecycleNodes.srv`). Typical launch brings planner, controller, smoother, BT navigator, map_server, amcl, and costmaps under coordinated lifecycle.

**Actions:** Clients (e.g. `nav2_simple_commander`, application nodes) call `nav2_msgs` actions such as `NavigateToPose`, `FollowWaypoints`, `ComputePathToPose`, `SmoothPath`, `Spin`, `BackUp`, `Wait`, `DockRobot`, `FollowObject`, `ComputeRoute`, etc. BT leaves wrap these as `BtActionNode` specializations in `nav2_behavior_tree`.

---

## 2. Full package catalog

### 2.0 Section map (this section)

| §2.x | Topic |
|------|-------|
| 2.1 | Master index (all `package.xml` packages) |
| 2.2 | Category → package map |
| 2.3 | `nav2_core` plugin interfaces |
| 2.4 | Orchestration: BT + navigator + behaviors |
| 2.5 | Costmaps & `nav2_voxel_grid` |
| 2.6 | Global planners |
| 2.7 | Local controllers & smoothers |
| 2.8 | OpenNav docking & following |
| 2.9 | DWB nested packages |
| 2.10 | `nav2_msgs` actions & services |
| 2.11 | Bringup, tools, tests, Python API |
| 2.12 | Façade → header lookup |
| 2.13 | `nav2_behavior_tree` plugin `.cpp` inventory |
| 2.14 | `nav2_costmap_2d` default layer plugins |
| 2.15 | `nav2_smac_planner` source modules |
| 2.16 | `dwb_critics` trajectory critics |

---

### 2.1 Master index — every ROS package

| M | Package | Path | Role |
|---|---------|------|------|
| ○ | `costmap_queue` | `nav2_dwb_controller/costmap_queue/` | The costmap_queue package |
| ○ | `dwb_core` | `nav2_dwb_controller/dwb_core/` | DWB core interfaces package |
| ○ | `dwb_critics` | `nav2_dwb_controller/dwb_critics/` | The dwb_critics package |
| ○ | `dwb_msgs` | `nav2_dwb_controller/dwb_msgs/` | Message/Service definitions specifically for the dwb_core |
| ○ | `dwb_plugins` | `nav2_dwb_controller/dwb_plugins/` | Standard implementations of the GoalChecker and TrajectoryGenerators for dwb_core |
| ★ | `nav2_amcl` | `nav2_amcl/` | Adaptive Monte Carlo Localization on a static map. |
| ★ | `nav2_behavior_tree` | `nav2_behavior_tree/` | Nav2 behavior tree wrappers, nodes, and utilities |
| ◆ | `nav2_behaviors` | `nav2_behaviors/` | Nav2 behavior server |
| ★ | `nav2_bringup` | `nav2_bringup/` | Bringup scripts and configurations for the Nav2 stack |
| ★ | `nav2_bt_navigator` | `nav2_bt_navigator/` | Nav2 BT Navigator Server |
| ◆ | `nav2_collision_monitor` | `nav2_collision_monitor/` | Collision Monitor |
| ★ | `nav2_common` | `nav2_common/` | Common support functionality used throughout the navigation 2 stack |
| ◆ | `nav2_constrained_smoother` | `nav2_constrained_smoother/` | Ceres constrained smoother |
| ★ | `nav2_controller` | `nav2_controller/` | Controller action interface |
| ★ | `nav2_core` | `nav2_core/` | A set of headers for plugins core to the Nav2 stack |
| ★ | `nav2_costmap_2d` | `nav2_costmap_2d/` | This package provides an implementation of a 2D costmap that takes in sensor data from the world, builds a 2D or 3D occupancy grid of the data (depending on whether a voxel based implementation is used), and inflates … |
| ◆ | `nav2_dwb_controller` | `nav2_dwb_controller/nav2_dwb_controller/` | ROS2 controller (DWB) metapackage |
| ◆ | `nav2_graceful_controller` | `nav2_graceful_controller/` | Graceful motion controller |
| ★ | `nav2_lifecycle_manager` | `nav2_lifecycle_manager/` | A controller/manager for the lifecycle nodes of the Navigation 2 system |
| ○ | `nav2_loopback_sim` | `nav2_loopback_sim/` | A loopback simulator to replace physics simulation |
| ★ | `nav2_map_server` | `nav2_map_server/` | Refactored map server for ROS2 Navigation |
| ◆ | `nav2_mppi_controller` | `nav2_mppi_controller/` | nav2_mppi_controller |
| ★ | `nav2_msgs` | `nav2_msgs/` | Messages and service files for the Nav2 stack |
| ◆ | `nav2_navfn_planner` | `nav2_navfn_planner/` | Nav2 NavFn planner |
| ★ | `nav2_planner` | `nav2_planner/` | Nav2 planner server package |
| ◆ | `nav2_regulated_pure_pursuit_controller` | `nav2_regulated_pure_pursuit_controller/` | Regulated Pure Pursuit Controller |
| ★ | `nav2_ros_common` | `nav2_ros_common/` | Nav2 utilities |
| ◆ | `nav2_rotation_shim_controller` | `nav2_rotation_shim_controller/` | Rotation Shim Controller |
| ◆ | `nav2_route` | `nav2_route/` | A Route Graph planner to compliment the Planner Server |
| ○ | `nav2_rviz_plugins` | `nav2_rviz_plugins/` | Navigation 2 plugins for rviz |
| ○ | `nav2_simple_commander` | `nav2_simple_commander/` | An importable library for writing mobile robot applications in python3 |
| ◆ | `nav2_smac_planner` | `nav2_smac_planner/` | Smac global planning plugin: A*, Hybrid-A*, State Lattice |
| ★ | `nav2_smoother` | `nav2_smoother/` | Smoother action interface |
| ○ | `nav2_system_tests` | `nav2_system_tests/` | A sets of system-level tests for Nav2 usually involving full robot simulation |
| ◆ | `nav2_theta_star_planner` | `nav2_theta_star_planner/` | Theta* Global Planning Plugin |
| ★ | `nav2_util` | `nav2_util/` | Nav2 utilities |
| ★ | `nav2_velocity_smoother` | `nav2_velocity_smoother/` | Nav2's Output velocity smoother |
| ★ | `nav2_voxel_grid` | `nav2_voxel_grid/` | voxel_grid provides an implementation of an efficient 3D voxel grid. The occupancy grid can support 3 different representations for the state of a cell: marked, free, or unknown. Due to the underlying implementation r… |
| ◆ | `nav2_waypoint_follower` | `nav2_waypoint_follower/` | A waypoint follower navigation server |
| ○ | `nav_2d_msgs` | `nav2_dwb_controller/nav_2d_msgs/` | Basic message types for two dimensional navigation, extending from geometry_msgs::Pose. |
| ○ | `nav_2d_utils` | `nav2_dwb_controller/nav_2d_utils/` | A handful of useful utility functions for nav_2d packages. |
| ◆ | `navigation2` | `navigation2/` | ROS2 Navigation Stack |
| ○ | `opennav_docking` | `nav2_docking/opennav_docking/` | A Task Server for robot charger docking |
| ○ | `opennav_docking_bt` | `nav2_docking/opennav_docking_bt/` | A set of BT nodes and XMLs for docking |
| ○ | `opennav_docking_core` | `nav2_docking/opennav_docking_core/` | A set of headers for plugins core to the opennav docking framework |
| ○ | `opennav_following` | `nav2_following/opennav_following/` | A Task Server for dynamic following object |

---

### 2.2 Category → package map

#### Common utilities

`nav2_common`, `nav2_ros_common`, `nav2_util`

#### DWB controller subtree

`costmap_queue`, `dwb_core`, `dwb_critics`, `dwb_msgs`, `dwb_plugins`, `nav2_dwb_controller`, `nav_2d_msgs`, `nav_2d_utils`

#### Global planning

`nav2_navfn_planner`, `nav2_planner`, `nav2_route`, `nav2_smac_planner`, `nav2_theta_star_planner`

#### Lifecycle management

`nav2_lifecycle_manager`

#### Local control & smoothing

`nav2_constrained_smoother`, `nav2_controller`, `nav2_graceful_controller`, `nav2_mppi_controller`, `nav2_regulated_pure_pursuit_controller`, `nav2_rotation_shim_controller`, `nav2_smoother`, `nav2_velocity_smoother`

#### Localization

`nav2_amcl`

#### Mapping / maps

`nav2_map_server`

#### Messages & actions

`nav2_msgs`

#### Metapackage & bringup

`nav2_bringup`, `navigation2`

#### OpenNav docking

`opennav_docking`, `opennav_docking_bt`, `opennav_docking_core`

#### OpenNav following

`opennav_following`

#### Orchestration & BT

`nav2_behavior_tree`, `nav2_behaviors`, `nav2_bt_navigator`, `nav2_waypoint_follower`

#### Plugin interfaces (headers)

`nav2_core`

#### Safety

`nav2_collision_monitor`

#### Tools, sim, tests, Python API

`nav2_loopback_sim`, `nav2_rviz_plugins`, `nav2_simple_commander`, `nav2_system_tests`

#### World model & costmaps

`nav2_costmap_2d`, `nav2_voxel_grid`

---

### 2.3 `nav2_core` plugin interfaces

Headers under `nav2_core/include/nav2_core/` define **pluginlib** interfaces implemented by packages in §2.6–2.7. Typical mapping:

| Header | Implementations (examples) |
|--------|------------------------------|
| `global_planner.hpp` | `nav2_navfn_planner`, `nav2_smac_planner`, `nav2_theta_star_planner`, `nav2_route` |
| `controller.hpp` | `nav2_dwb_controller`, `nav2_mppi_controller`, `nav2_regulated_pure_pursuit_controller`, `nav2_graceful_controller`, `nav2_rotation_shim_controller` |
| `smoother.hpp` | `nav2_smoother` server + plugins; `nav2_constrained_smoother` |
| `goal_checker.hpp`, `progress_checker.hpp` | Used by controller plugins (DWB, RPP, …) |
| `behavior.hpp` | `nav2_behaviors` recovery / assisted teleop plugins |
| `waypoint_task_executor.hpp` | `nav2_waypoint_follower` task plugins |
| `path_handler.hpp`, `route_exceptions.hpp` | Route graph / typed route APIs |

---

### 2.4 Orchestration: BT + navigator + behaviors

- **`nav2_bt_navigator`** — Lifecycle node loading XML behavior trees; registers navigator plugins (`navigator_plugins.xml`). Entry: `bt_navigator.cpp`.
- **`nav2_behavior_tree`** — BT node library (Navigate, Recovery, Docking, Route, Conversions, …), `BehaviorTreeEngine`, action/service BT wrappers.
- **`nav2_behaviors`** — `BehaviorServer` hosting spin, backup, drive-on-heading, assisted teleop, etc., as `nav2_core::Behavior` plugins.
- **`nav2_waypoint_follower`** — Waypoint task pipeline using `WaypointTaskExecutor` plugins.

---

### 2.5 Costmaps & `nav2_voxel_grid`

**`nav2_costmap_2d`** — `Costmap2DROS`, layered costmaps, inflation, obstacles, static map, range, denoise, voxel projection plugins; footprint collision checking; clearing services (`ClearEntireCostmap`, …).

**`nav2_voxel_grid`** — Efficient 3D voxel grid used when costmap operates in 3D/voxel mode before projection to 2D.

---

### 2.6 Global planners

| Package | Algorithm family |
|---------|------------------|
| `nav2_planner` | **Planner server** — plugin host for global planning |
| `nav2_navfn_planner` | Dijkstra / gradient on grid (NavFn) |
| `nav2_smac_planner` | 2D A*, Hybrid-A*, State Lattice (kinematically feasible) |
| `nav2_theta_star_planner` | Theta* any-angle grid search |
| `nav2_route` | Route graph / logical route layer complementing geometric planner |

---

### 2.7 Local controllers & smoothers

| Package | Notes |
|---------|-------|
| `nav2_controller` | **Controller server** — loads `controller` plugins, publishes `cmd_vel` |
| `nav2_regulated_pure_pursuit_controller` | Curvature-regulated pure pursuit |
| `nav2_mppi_controller` | MPPI sampling-based optimization |
| `nav2_graceful_controller` | Smooth near-goal behavior |
| `nav2_rotation_shim_controller` | In-place rotation shim wrapping another controller |
| `nav2_dwb_controller` | DWB trajectory scoring (see §2.9) |
| `nav2_smoother` | Path smoother server + plugins |
| `nav2_constrained_smoother` | Ceres-based constrained smoothing |
| `nav2_velocity_smoother` | Output **cmd_vel** low-pass / rate limiting |

---

### 2.8 OpenNav docking & following

- **`opennav_docking`** — Docking task server (`DockRobot.action` integration).
- **`opennav_docking_bt`** — BT nodes and XML for docking sequences.
- **`opennav_docking_core`** — Dock plugin base interfaces.
- **`opennav_following`** — Dynamic object following (`FollowObject.action`).

---

### 2.9 DWB nested packages (`nav2_dwb_controller/`)

| Package | Role |
|---------|------|
| `dwb_core` | Trajectory critic interface, trajectory generator, DWB local planner core |
| `dwb_critics` | Obstacle footprint, path alignment, goal dist, oscillation, … critics |
| `dwb_plugins` | Standard trajectory generators and goal checkers |
| `costmap_queue` | DWB-aligned costmap sampling |
| `dwb_msgs` | DWB-specific messages |
| `nav_2d_msgs` | 2D pose / twist message extensions |
| `nav_2d_utils` | 2D geometry helpers |
| `nav2_dwb_controller` | Metapackage / integration with `nav2_controller` |

---

### 2.10 `nav2_msgs` — actions & services

**Actions (`nav2_msgs/action/`):**

- `AssistedTeleop.action`, `BackUp.action`, `ComputeAndTrackRoute.action`, `ComputePathThroughPoses.action`, `ComputePathToPose.action`, `ComputeRoute.action`
- `DockRobot.action`, `DriveOnHeading.action`, `DummyBehavior.action`, `FollowGPSWaypoints.action`, `FollowObject.action`, `FollowPath.action`
- `FollowWaypoints.action`, `NavigateThroughPoses.action`, `NavigateToPose.action`, `SmoothPath.action`, `Spin.action`, `UndockRobot.action`
- `Wait.action`

**Services (`nav2_msgs/srv/`):**

- `AddShapes.srv`, `ClearCostmapAroundPose.srv`, `ClearCostmapAroundRobot.srv`, `ClearCostmapExceptRegion.srv`, `ClearEntireCostmap.srv`
- `DynamicEdges.srv`, `GetCostmap.srv`, `GetCosts.srv`, `GetShapes.srv`, `IsPathValid.srv`
- `LoadMap.srv`, `ManageLifecycleNodes.srv`, `ReloadDockDatabase.srv`, `RemoveShapes.srv`, `SaveMap.srv`
- `SetInitialPose.srv`, `SetRouteGraph.srv`, `Toggle.srv`

---

### 2.11 Bringup, tools, tests, Python API

- **`nav2_bringup`** — `launch/`, `params/`, `maps/`, `graphs/`, `rviz/` for reference robots (TurtleBot3, etc.).
- **`navigation2`** — Metapackage depending on released stack.
- **`nav2_simple_commander`** — Python 3 API wrapping actions for applications.
- **`nav2_loopback_sim`** — Lightweight sim feeding TF/sensors without full Gazebo.
- **`nav2_system_tests`** — Integration tests (often Gz/RViz pipelines).
- **`nav2_rviz_plugins`** — Panel plugins for Nav2 in RViz2.

---

### 2.12 Façade → header / entry lookup

| Concern | Where to start |
|---------|----------------|
| Global plan plugin | `nav2_core/global_planner.hpp` → chosen planner package `include/` |
| Local control plugin | `nav2_core/controller.hpp` → controller package |
| Costmap layer plugin | `nav2_costmap_2d/layer.hpp` → layer `.cpp` in same package |
| BT node | `nav2_behavior_tree/nav2_behavior_tree/plugins/` (XML under `behavior_trees/`) |
| Navigator plugin | `nav2_bt_navigator/include/` + `navigator_plugins.xml` |
| Lifecycle | `nav2_lifecycle_manager` sources |

---

### 2.13 `nav2_behavior_tree` — plugin `.cpp` inventory

Sources live under `nav2_behavior_tree/plugins/{action,condition,control,decorator}/`. These classes register as BT nodes and wrap Nav2 actions, services, or state checks.

**Action plugins (`plugins/action/`, 44 files):**

- `append_goal_pose_to_goals_action`, `assisted_teleop_action`, `assisted_teleop_cancel_node`, `back_up_action`, `back_up_cancel_node`
- `check_pose_occupancy_action`, `check_stop_status_action`, `clear_costmap_service`, `compute_and_track_route_action`, `compute_and_track_route_cancel_node`
- `compute_path_through_poses_action`, `compute_path_to_pose_action`, `compute_route_action`, `concatenate_paths_action`, `controller_cancel_node`
- `controller_selector_node`, `drive_on_heading_action`, `drive_on_heading_cancel_node`, `extract_route_nodes_as_goals_action`, `follow_object_action`
- `follow_object_cancel_node`, `follow_path_action`, `get_current_pose_action`, `get_next_few_goals_action`, `get_pose_from_path_action`
- `goal_checker_selector_node`, `navigate_through_poses_action`, `navigate_to_pose_action`, `path_handler_selector_node`, `planner_selector_node`
- `progress_checker_selector_node`, `reinitialize_global_localization_service`, `remove_in_collision_goals_action`, `remove_passed_goals_action`, `smoother_selector_node`
- `smooth_path_action`, `spin_action`, `spin_cancel_node`, `toggle_collision_monitor_service`, `truncate_path_action`
- `truncate_path_local_action`, `validate_path_action`, `wait_action`, `wait_cancel_node`

**Condition plugins (`plugins/condition/`, 19 files):**

- `are_error_codes_present_condition`, `are_poses_near_condition`, `distance_traveled_condition`, `globally_updated_goal_condition`, `goal_reached_condition`
- `goal_updated_condition`, `initial_pose_received_condition`, `is_battery_charging_condition`, `is_battery_low_condition`, `is_goal_nearby_condition`
- `is_stuck_condition`, `is_within_path_tracking_bounds_condition`, `path_expiring_timer_condition`, `time_expired_condition`, `transform_available_condition`
- `would_a_controller_recovery_help_condition`, `would_a_planner_recovery_help_condition`, `would_a_route_recovery_help_condition`, `would_a_smoother_recovery_help_condition`

**Control plugins (`plugins/control/`, 6 files):**

- `nonblocking_sequence`, `pause_resume_controller`, `persistent_sequence`, `pipeline_sequence`, `recovery_node`, `round_robin_node`

**Decorator plugins (`plugins/decorator/`, 7 files):**

- `distance_controller`, `goal_updated_controller`, `goal_updater_node`, `path_longer_on_approach`, `rate_controller`, `single_trigger_node`, `speed_controller`

Shared infrastructure (not under `plugins/`): `behavior_tree_engine.cpp`, BT logger, JSON utils, cancelable action node templates — see `nav2_behavior_tree/src/` and `include/nav2_behavior_tree/`.

---

### 2.14 `nav2_costmap_2d` — default layer plugins (`plugins/*.cpp`)

Bundled **costmap layer** plugin libraries (loaded by name from YAML):

- `static_layer` — OccupancyGrid from `map_server`
- `obstacle_layer` — LaserScan / PointCloud2 marking
- `voxel_layer` — 3D voxel projection to 2D
- `inflation_layer`, `legacy_inflation_layer` — cost decay around obstacles
- `range_sensor_layer` — sonar / IR range arcs
- `denoise_layer` — morphological cleanup
- `plugin_container_layer` — nest other layers dynamically

Core library (non-plugin) highlights: `layered_costmap.cpp`, `costmap_2d_ros.cpp`, `footprint_collision_checker.cpp`, clearing services, costmap publishers.

---

### 2.15 `nav2_smac_planner` — planner source modules (`src/*.cpp`)

Smac exposes multiple **pluginlib** global planners (2D grid A*, Hybrid-A*, lattice):

- `smac_planner_2d.cpp`, `smac_planner_hybrid.cpp`, `smac_planner_lattice.cpp` — plugin entry points
- `a_star.cpp`, `node_2d.cpp`, `node_basic.cpp`, `node_hybrid.cpp`, `node_lattice.cpp` — search graph nodes / expansions
- `collision_checker.cpp`, `obstacle_heuristic.cpp`, `distance_heuristic.cpp`, `analytic_expansion.cpp` — validity and heuristics
- `costmap_downsampler.cpp`, `smoother.cpp` — grid preprocessing and path cleanup

---

### 2.16 `dwb_critics` — trajectory critic modules (`src/*.cpp`)

DWB scores each simulated trajectory with a weighted sum of **critics**:

- `base_obstacle`, `obstacle_footprint` — collision and inscribed/circumscribed footprint costs
- `path_dist`, `path_align`, `goal_dist`, `goal_align` — tracking and terminal pose costs
- `prefer_forward`, `rotate_to_goal`, `twirling` — motion quality / orientation preferences
- `oscillation` — penalize direction reversals
- `map_grid` — alignment to underlying grid features
- `alignment_util` — shared math for alignment critics

---

## 3. `doc/` and `tools/`

- **`doc/`** — Logo, design images, additional documentation assets; primary docs live on [docs.nav2.org](https://docs.nav2.org/).
- **`tools/`** — Maintainer scripts (smoke tests, release helpers, etc.; inspect per-file for purpose).

---

## 4. Runtime data-flow (Nav2)

```
map_server (map) ─┐
localization (AMCL) ─┼→ TF map→odom→base_link
sensors / SLAM ───────┘         │
                                ▼
                    layered_costmap (global + local)
                                │
   NavigateToPose.action       │   ComputePathToPose / SmoothPath
         │                      ▼           │
   bt_navigator (BT XML) ← planner_server → path
         │                      │
         ├──────────────────────┼── controller_server → cmd_vel
         │                      │           │
         └── recovery behaviors ┘           ▼
                          velocity_smoother → robot hardware
lifecycle_manager orchestrates configure/activate on all servers
```

---

## 5. Package → primary artifacts

| Package | Typical artifacts |
|---------|-------------------|
| `nav2_bt_navigator` | executable **bt_navigator**, `navigator_plugins.xml` |
| `nav2_controller` | executable **controller_server** |
| `nav2_planner` | executable **planner_server** |
| `nav2_smoother` | executable **smoother_server** |
| `nav2_map_server` | **map_server**, **map_saver_cli**, **map_saver_server**, **costmap_filter_info_server**, **vector_object_server**, `map_io` library |
| `nav2_amcl` | **amcl** |
| `nav2_lifecycle_manager` | **lifecycle_manager** |
| `nav2_velocity_smoother` | **velocity_smoother** node |
| `nav2_collision_monitor` | **collision_monitor** |
| `nav2_waypoint_follower` | **waypoint_follower** |
| `nav2_behaviors` | **behavior_server** |
| Plugin packages | `pluginlib` XML exports in `share/<pkg>/` |

*Exact executable names may vary slightly by release; confirm with each package’s `CMakeLists.txt` `add_executable` and installed launch files.*

---

## 6. Configs, plugin XML, and bringup

- **Parameter YAML** — Under `nav2_bringup/params/` (e.g. `nav2_params.yaml`): planner/controller plugin types, costmap layer lists, robot footprint, speeds.
- **Behavior XML** — Under `nav2_bt_navigator/behavior_trees/` (installed via package share): default navigation BT.
- **Plugin description XML** — Each plugin package exports `pluginlib` class lists (e.g. `global_planner_plugin.xml`, controller plugins).
- **RViz** — `nav2_bringup/rviz/` default configs for visualization.

---

**Citation:** If you use Nav2 in research, cite the Marathon 2 and related papers listed in the upstream `README.md`.
