# Nav2 (ROS 2 Navigation2) — Deep PageIndex

> **Purpose:** Machine-navigable index of **`Studio-Portable-RAG/Codebase/navigation2`** (upstream [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2)), structured like [PageIndex](https://github.com/VectifyAI/PageIndex): **logical layering**, **per-package source inventory** (grouped paths), **roles**, and **interface** listings. Human docs: [docs.nav2.org](https://docs.nav2.org/).

**Detected stack version:** `1.4.0` (from `nav2_core/package.xml`).

## Document map

| § | Contents |
|---|----------|
| §1 | [Stack layers & dependency story](#1-stack-layers--dependency-story) |
| §2 | [`nav2_msgs` interface inventory](#2-nav2_msgs--interface-inventory) |
| §3 | [`nav2_bringup` assets (no C++)](#3-nav2_bringup--launch-params-maps-no-c-sources) |
| §4 | [Per-package source catalog](#4-per-package-source-catalog) — **every package**, files grouped |
| §5 | [Runtime execution & data flow](#5-runtime-execution--data-flow) |
| §6 | [Quick lookup: class ↔ file](#6-quick-lookup-class--file) |

**Legend (§4):** Files exclude `test/` trees. Extensions: `.cpp/.c/.hpp/.h`. `★` in prose = typical production bringup path.

---

## 1. Stack layers & dependency story

Nav2 is a **collection of lifecycle-managed ROS 2 action servers** wired by **behavior trees** or direct action clients. Dependencies generally flow: **`nav2_msgs`** ← **`nav2_util` / `nav2_ros_common`** ← **`nav2_core`** (interfaces) ← **algorithm packages** ← **servers** (`nav2_planner`, `nav2_controller`, …) ← **`nav2_bt_navigator`**.

### 1.1 Logical layers (top → bottom)

| Layer | Packages (representative) | Responsibility |
|-------|---------------------------|----------------|
| **Application** | `nav2_simple_commander` (Python), your nodes | Call `NavigateToPose`, `FollowWaypoints`, … |
| **Orchestration ★** | `nav2_bt_navigator`, `nav2_behavior_tree`, `nav2_behaviors`, `nav2_waypoint_follower` | BT XML, recovery behaviors, waypoint tasks |
| **Servers ★** | `nav2_planner`, `nav2_controller`, `nav2_smoother`, `nav2_map_server` | `pluginlib` hosts + actions |
| **Algorithms** | `nav2_*planner`, `nav2_*controller`, `nav2_constrained_smoother`, `nav2_route`, OpenNav | Concrete plugins |
| **World model ★** | `nav2_costmap_2d`, `nav2_voxel_grid` | Occupancy, inflation, sensors → cost |
| **State estimation ★** | `nav2_amcl` | Map → `map` frame particle filter |
| **Infrastructure ★** | `nav2_lifecycle_manager`, `nav2_velocity_smoother`, `nav2_collision_monitor` | Bring-up order, cmd_vel shaping, safety |
| **Foundation** | `nav2_core`, `nav2_util`, `nav2_ros_common`, `nav2_msgs`, `nav2_common` | Types, helpers, interfaces, build |

### 1.2 `pluginlib` contract

Servers load plugins by **fully qualified class name** from YAML. Each plugin package ships an XML export under `share/<pkg>/` referencing base classes in `nav2_core` (`Controller`, `GlobalPlanner`, `Smoother`, `Behavior`, …).

---

## 2. `nav2_msgs` — interface inventory

All cross-package contracts live here: **19** actions, **18** services, **21** messages (file names below are the API surface for RAG).

### 2.1 Action definitions (`nav2_msgs/action/*.action`)

- `AssistedTeleop.action`, `BackUp.action`, `ComputeAndTrackRoute.action`, `ComputePathThroughPoses.action`, `ComputePathToPose.action`
- `ComputeRoute.action`, `DockRobot.action`, `DriveOnHeading.action`, `DummyBehavior.action`, `FollowGPSWaypoints.action`
- `FollowObject.action`, `FollowPath.action`, `FollowWaypoints.action`, `NavigateThroughPoses.action`, `NavigateToPose.action`
- `SmoothPath.action`, `Spin.action`, `UndockRobot.action`, `Wait.action`

### 2.2 Service definitions (`nav2_msgs/srv/*.srv`)

- `AddShapes.srv`, `ClearCostmapAroundPose.srv`, `ClearCostmapAroundRobot.srv`, `ClearCostmapExceptRegion.srv`, `ClearEntireCostmap.srv`
- `DynamicEdges.srv`, `GetCostmap.srv`, `GetCosts.srv`, `GetShapes.srv`, `IsPathValid.srv`
- `LoadMap.srv`, `ManageLifecycleNodes.srv`, `ReloadDockDatabase.srv`, `RemoveShapes.srv`, `SaveMap.srv`
- `SetInitialPose.srv`, `SetRouteGraph.srv`, `Toggle.srv`

### 2.3 Message definitions (`nav2_msgs/msg/*.msg`)

- `BehaviorTreeLog.msg`, `BehaviorTreeStatusChange.msg`, `CircleObject.msg`, `CollisionDetectorState.msg`, `CollisionMonitorState.msg`, `Costmap.msg`
- `CostmapFilterInfo.msg`, `CostmapMetaData.msg`, `CostmapUpdate.msg`, `CriticsStats.msg`, `EdgeCost.msg`, `Particle.msg`
- `ParticleCloud.msg`, `PolygonObject.msg`, `Route.msg`, `RouteEdge.msg`, `RouteNode.msg`, `SpeedLimit.msg`
- `TrackingFeedback.msg`, `VoxelGrid.msg`, `WaypointStatus.msg`

---

## 3. `nav2_bringup` — launch, params, maps (no C++ sources)

### 3.1 `launch/`

*13 files*

- `launch/bringup_launch.py`
- `launch/cloned_multi_tb3_simulation_launch.py`
- `launch/keepout_zone_launch.py`
- `launch/localization_launch.py`
- `launch/navigation_launch.py`
- `launch/rviz_launch.py`
- `launch/slam_launch.py`
- `launch/speed_zone_launch.py`
- `launch/tb3_loopback_simulation_launch.py`
- `launch/tb3_simulation_launch.py`
- `launch/tb4_loopback_simulation_launch.py`
- `launch/tb4_simulation_launch.py`
- `launch/unique_multi_tb3_simulation_launch.py`

### 3.2 `params/`

*1 files*

- `params/nav2_params.yaml`

### 3.3 `maps/`

*14 files*

- `maps/depot.pgm`
- `maps/depot.yaml`
- `maps/depot_keepout.pgm`
- `maps/depot_keepout.yaml`
- `maps/depot_speed.pgm`
- `maps/depot_speed.yaml`
- `maps/tb3_sandbox.pgm`
- `maps/tb3_sandbox.yaml`
- `maps/warehouse.pgm`
- `maps/warehouse.yaml`
- `maps/warehouse_keepout.pgm`
- `maps/warehouse_keepout.yaml`
- `maps/warehouse_speed.pgm`
- `maps/warehouse_speed.yaml`

### 3.4 `graphs/`

*3 files*

- `graphs/depot_graph.geojson`
- `graphs/turtlebot3_graph.geojson`
- `graphs/warehouse_graph.geojson`

### 3.5 `rviz/`

*1 files*

- `rviz/nav2_default_view.rviz`

---

## 4. Per-package source catalog

Each subsection is one **ament package** (directory containing `package.xml`). Sources are grouped: **executables** (`main`), **src/**, **plugins/**, **include/**, **benchmark/**. Purpose combines `package.xml` and stack context.

### 4.1 `navigation2/` — package **`navigation2`**

- **Version:** `1.4.0`
- **package.xml description:** ROS2 Navigation Stack
- **Purpose:** Metapackage: `package.xml` lists dependencies so `rosdep` / `colcon` install the full stack.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.2 `nav2_bringup/` — package **`nav2_bringup`**

- **Version:** `1.4.0`
- **package.xml description:** Bringup scripts and configurations for the Nav2 stack
- **Purpose:** No compiled code: Python launch files, YAML parameters, demo maps, GeoJSON route graphs, RViz configs.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.3 `nav2_msgs/` — package **`nav2_msgs`**

- **Version:** `1.4.0`
- **package.xml description:** Messages and service files for the Nav2 stack
- **Purpose:** Canonical ROS interface: actions for navigate/smooth/dock/follow, services for lifecycle and costmaps, messages shared across servers.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.4 `nav2_common/` — package **`nav2_common`**

- **Version:** `1.4.0`
- **package.xml description:** Common support functionality used throughout the navigation 2 stack
- **Purpose:** CMake macros (`nav2_package()`), compile flags, shared build logic — no runtime sources.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.5 `nav2_util/` — package **`nav2_util`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 utilities
- **Purpose:** Geometry, path, costmap helpers, lifecycle client utilities, string parsing — depended on by nearly all C++ packages.
- **Source file count (excl. tests):** 29

#### sources (src/)

- `src/array_parser.cpp`
- `src/base_footprint_publisher.cpp`
- `src/base_footprint_publisher.hpp`
- `src/controller_utils.cpp`
- `src/costmap.cpp`
- `src/lifecycle_bringup_commandline.cpp`
- `src/lifecycle_service_client.cpp`
- `src/odometry_utils.cpp`
- `src/path_utils.cpp`
- `src/robot_utils.cpp`
- `src/string_utils.cpp`

#### headers (include/)

- `include/nav2_util/array_parser.hpp`
- `include/nav2_util/controller_utils.hpp`
- `include/nav2_util/costmap.hpp`
- `include/nav2_util/execution_timer.hpp`
- `include/nav2_util/geometry_utils.hpp`
- `include/nav2_util/lifecycle_service_client.hpp`
- `include/nav2_util/line_iterator.hpp`
- `include/nav2_util/occ_grid_utils.hpp`
- `include/nav2_util/occ_grid_values.hpp`
- `include/nav2_util/odometry_utils.hpp`
- `include/nav2_util/parameter_handler.hpp`
- `include/nav2_util/path_utils.hpp`
- `include/nav2_util/raytrace_line_2d.hpp`
- `include/nav2_util/robot_utils.hpp`
- `include/nav2_util/smoother_utils.hpp`
- `include/nav2_util/string_utils.hpp`
- `include/nav2_util/twist_publisher.hpp`
- `include/nav2_util/twist_subscriber.hpp`

---

### 4.6 `nav2_ros_common/` — package **`nav2_ros_common`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 utilities
- **Purpose:** Reusable lifecycle nodes, action servers, QoS helpers — base patterns for Nav2 servers.
- **Source file count (excl. tests):** 12

#### headers (include/)

- `include/nav2_ros_common/action_client.hpp`
- `include/nav2_ros_common/interface_factories.hpp`
- `include/nav2_ros_common/lifecycle_node.hpp`
- `include/nav2_ros_common/node_thread.hpp`
- `include/nav2_ros_common/node_utils.hpp`
- `include/nav2_ros_common/publisher.hpp`
- `include/nav2_ros_common/qos_profiles.hpp`
- `include/nav2_ros_common/service_client.hpp`
- `include/nav2_ros_common/service_server.hpp`
- `include/nav2_ros_common/simple_action_server.hpp`
- `include/nav2_ros_common/subscription.hpp`
- `include/nav2_ros_common/validate_messages.hpp`

---

### 4.7 `nav2_core/` — package **`nav2_core`**

- **Version:** `1.4.0`
- **package.xml description:** A set of headers for plugins core to the Nav2 stack
- **Purpose:** Pure abstract C++ interfaces (`nav2_core/*.hpp`) implemented by planner/controller/smoother/behavior plugins via `pluginlib`.
- **Source file count (excl. tests):** 13

#### headers (include/)

- `include/nav2_core/behavior.hpp`
- `include/nav2_core/behavior_tree_navigator.hpp`
- `include/nav2_core/controller.hpp`
- `include/nav2_core/controller_exceptions.hpp`
- `include/nav2_core/global_planner.hpp`
- `include/nav2_core/goal_checker.hpp`
- `include/nav2_core/path_handler.hpp`
- `include/nav2_core/planner_exceptions.hpp`
- `include/nav2_core/progress_checker.hpp`
- `include/nav2_core/route_exceptions.hpp`
- `include/nav2_core/smoother.hpp`
- `include/nav2_core/smoother_exceptions.hpp`
- `include/nav2_core/waypoint_task_executor.hpp`

---

### 4.8 `nav2_map_server/` — package **`nav2_map_server`**

- **Version:** `1.4.0`
- **package.xml description:** Refactored map server for ROS2 Navigation
- **Purpose:** Lifecycle `map_server`, CLI/server map savers, optional costmap filter info server, vector-object (annotation) server.
- **Source file count (excl. tests):** 20

#### executables (main entry)

- `src/costmap_filter_info/main.cpp`
- `src/map_saver/main_cli.cpp`
- `src/map_saver/main_server.cpp`
- `src/map_server/main.cpp`
- `src/vo_server/main.cpp`

#### sources (src/)

- `src/costmap_filter_info/costmap_filter_info_server.cpp`
- `src/map_io.cpp`
- `src/map_mode.cpp`
- `src/map_saver/map_saver.cpp`
- `src/map_server/map_server.cpp`
- `src/vo_server/vector_object_server.cpp`
- `src/vo_server/vector_object_shapes.cpp`

#### headers (include/)

- `include/nav2_map_server/costmap_filter_info_server.hpp`
- `include/nav2_map_server/map_io.hpp`
- `include/nav2_map_server/map_mode.hpp`
- `include/nav2_map_server/map_saver.hpp`
- `include/nav2_map_server/map_server.hpp`
- `include/nav2_map_server/vector_object_server.hpp`
- `include/nav2_map_server/vector_object_shapes.hpp`
- `include/nav2_map_server/vector_object_utils.hpp`

---

### 4.9 `nav2_amcl/` — package **`nav2_amcl`**

- **Version:** `1.4.0`
- **Purpose:** Particle filter localization: motion models, laser likelihood models, KD-tree particle set, `amcl` node.
- **Source file count (excl. tests):** 31

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/amcl_node.cpp`
- `src/map/map.c`
- `src/map/map_cspace.cpp`
- `src/map/map_draw.c`
- `src/map/map_range.c`
- `src/motion_model/differential_motion_model.cpp`
- `src/motion_model/omni_motion_model.cpp`
- `src/pf/eig3.c`
- `src/pf/pf.c`
- `src/pf/pf_draw.c`
- `src/pf/pf_kdtree.c`
- `src/pf/pf_pdf.c`
- `src/pf/pf_vector.c`
- `src/sensors/laser/beam_model.cpp`
- `src/sensors/laser/laser.cpp`
- `src/sensors/laser/likelihood_field_model.cpp`
- `src/sensors/laser/likelihood_field_model_prob.cpp`

#### headers (include/)

- `include/nav2_amcl/amcl_node.hpp`
- `include/nav2_amcl/angleutils.hpp`
- `include/nav2_amcl/map/map.hpp`
- `include/nav2_amcl/motion_model/differential_motion_model.hpp`
- `include/nav2_amcl/motion_model/motion_model.hpp`
- `include/nav2_amcl/motion_model/omni_motion_model.hpp`
- `include/nav2_amcl/pf/eig3.hpp`
- `include/nav2_amcl/pf/pf.hpp`
- `include/nav2_amcl/pf/pf_kdtree.hpp`
- `include/nav2_amcl/pf/pf_pdf.hpp`
- `include/nav2_amcl/pf/pf_vector.hpp`
- `include/nav2_amcl/portable_utils.hpp`
- `include/nav2_amcl/sensors/laser/laser.hpp`

---

### 4.10 `nav2_voxel_grid/` — package **`nav2_voxel_grid`**

- **Version:** `1.4.0`
- **package.xml description:** voxel_grid provides an implementation of an efficient 3D voxel grid. The occupancy grid can support 3 different representations for the state of a cell: marked, free, or unknown. Due to the underlying implementation relying on bitwise and and or integer operations, the voxel g…
- **Purpose:** Standalone 3D voxel occupancy grid implementation used by voxel costmap layer.
- **Source file count (excl. tests):** 2

#### sources (src/)

- `src/voxel_grid.cpp`

#### headers (include/)

- `include/nav2_voxel_grid/voxel_grid.hpp`

---

### 4.11 `nav2_costmap_2d/` — package **`nav2_costmap_2d`**

- **Version:** `1.4.0`
- **package.xml description:** This package provides an implementation of a 2D costmap that takes in sensor data from the world, builds a 2D or 3D occupancy grid of the data (depending on whether a voxel based implementation is used), and inflates costs in a 2D costmap based on the occupancy grid and a user…
- **Purpose:** `LayeredCostmap` + ROS wrapper, inflation, static/obstacle/voxel layers, costmap filters, clearing services.
- **Source file count (excl. tests):** 63

#### sources (src/)

- `src/clear_costmap_service.cpp`
- `src/costmap_2d.cpp`
- `src/costmap_2d_cloud.cpp`
- `src/costmap_2d_markers.cpp`
- `src/costmap_2d_node.cpp`
- `src/costmap_2d_publisher.cpp`
- `src/costmap_2d_ros.cpp`
- `src/costmap_layer.cpp`
- `src/costmap_math.cpp`
- `src/costmap_subscriber.cpp`
- `src/costmap_topic_collision_checker.cpp`
- `src/footprint.cpp`
- `src/footprint_collision_checker.cpp`
- `src/footprint_subscriber.cpp`
- `src/layer.cpp`
- `src/layered_costmap.cpp`
- `src/observation_buffer.cpp`

#### plugins/

- `plugins/costmap_filters/binary_filter.cpp`
- `plugins/costmap_filters/costmap_filter.cpp`
- `plugins/costmap_filters/keepout_filter.cpp`
- `plugins/costmap_filters/speed_filter.cpp`
- `plugins/denoise_layer.cpp`
- `plugins/inflation_layer.cpp`
- `plugins/legacy_inflation_layer.cpp`
- `plugins/obstacle_layer.cpp`
- `plugins/plugin_container_layer.cpp`
- `plugins/range_sensor_layer.cpp`
- `plugins/static_layer.cpp`
- `plugins/voxel_layer.cpp`

#### headers (include/)

- `include/nav2_costmap_2d/clear_costmap_service.hpp`
- `include/nav2_costmap_2d/cost_values.hpp`
- `include/nav2_costmap_2d/costmap_2d.hpp`
- `include/nav2_costmap_2d/costmap_2d_publisher.hpp`
- `include/nav2_costmap_2d/costmap_2d_ros.hpp`
- `include/nav2_costmap_2d/costmap_filters/binary_filter.hpp`
- `include/nav2_costmap_2d/costmap_filters/costmap_filter.hpp`
- `include/nav2_costmap_2d/costmap_filters/filter_values.hpp`
- `include/nav2_costmap_2d/costmap_filters/keepout_filter.hpp`
- `include/nav2_costmap_2d/costmap_filters/speed_filter.hpp`
- `include/nav2_costmap_2d/costmap_layer.hpp`
- `include/nav2_costmap_2d/costmap_math.hpp`
- `include/nav2_costmap_2d/costmap_subscriber.hpp`
- `include/nav2_costmap_2d/costmap_topic_collision_checker.hpp`
- `include/nav2_costmap_2d/denoise/image.hpp`
- `include/nav2_costmap_2d/denoise/image_processing.hpp`
- `include/nav2_costmap_2d/denoise_layer.hpp`
- `include/nav2_costmap_2d/distance_transform.hpp`
- `include/nav2_costmap_2d/exceptions.hpp`
- `include/nav2_costmap_2d/footprint.hpp`
- `include/nav2_costmap_2d/footprint_collision_checker.hpp`
- `include/nav2_costmap_2d/footprint_subscriber.hpp`
- `include/nav2_costmap_2d/inflation_layer.hpp`
- `include/nav2_costmap_2d/inflation_layer_interface.hpp`
- `include/nav2_costmap_2d/layer.hpp`
- `include/nav2_costmap_2d/layered_costmap.hpp`
- `include/nav2_costmap_2d/legacy_inflation_layer.hpp`
- `include/nav2_costmap_2d/observation.hpp`
- `include/nav2_costmap_2d/observation_buffer.hpp`
- `include/nav2_costmap_2d/obstacle_layer.hpp`
- `include/nav2_costmap_2d/plugin_container_layer.hpp`
- `include/nav2_costmap_2d/range_sensor_layer.hpp`
- `include/nav2_costmap_2d/static_layer.hpp`
- `include/nav2_costmap_2d/voxel_layer.hpp`

---

### 4.12 `nav2_planner/` — package **`nav2_planner`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 planner server package
- **Purpose:** `PlannerServer` lifecycle node: loads `nav2_core::GlobalPlanner` plugins, exposes `ComputePathToPose` and related actions.
- **Source file count (excl. tests):** 6

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/parameter_handler.cpp`
- `src/planner_server.cpp`

#### headers (include/)

- `include/nav2_planner/is_path_valid_service.hpp`
- `include/nav2_planner/parameter_handler.hpp`
- `include/nav2_planner/planner_server.hpp`

---

### 4.13 `nav2_navfn_planner/` — package **`nav2_navfn_planner`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 NavFn planner
- **Purpose:** Grid Dijkstra / NavFn global planner plugin (gradient-based).
- **Source file count (excl. tests):** 6

#### sources (src/)

- `src/navfn.cpp`
- `src/navfn_planner.cpp`
- `src/parameter_handler.cpp`

#### headers (include/)

- `include/nav2_navfn_planner/navfn.hpp`
- `include/nav2_navfn_planner/navfn_planner.hpp`
- `include/nav2_navfn_planner/parameter_handler.hpp`

---

### 4.14 `nav2_smac_planner/` — package **`nav2_smac_planner`**

- **Version:** `1.4.0`
- **package.xml description:** Smac global planning plugin: A*, Hybrid-A*, State Lattice
- **Purpose:** Smac 2D / Hybrid-A* / State Lattice planner plugins with analytic expansion and optional smoothing.
- **Source file count (excl. tests):** 33

#### sources (src/)

- `src/a_star.cpp`
- `src/analytic_expansion.cpp`
- `src/collision_checker.cpp`
- `src/costmap_downsampler.cpp`
- `src/distance_heuristic.cpp`
- `src/node_2d.cpp`
- `src/node_basic.cpp`
- `src/node_hybrid.cpp`
- `src/node_lattice.cpp`
- `src/obstacle_heuristic.cpp`
- `src/smac_planner_2d.cpp`
- `src/smac_planner_hybrid.cpp`
- `src/smac_planner_lattice.cpp`
- `src/smoother.cpp`

#### headers (include/)

- `include/nav2_smac_planner/a_star.hpp`
- `include/nav2_smac_planner/analytic_expansion.hpp`
- `include/nav2_smac_planner/collision_checker.hpp`
- `include/nav2_smac_planner/constants.hpp`
- `include/nav2_smac_planner/costmap_downsampler.hpp`
- `include/nav2_smac_planner/distance_heuristic.hpp`
- `include/nav2_smac_planner/goal_manager.hpp`
- `include/nav2_smac_planner/node_2d.hpp`
- `include/nav2_smac_planner/node_basic.hpp`
- `include/nav2_smac_planner/node_hybrid.hpp`
- `include/nav2_smac_planner/node_lattice.hpp`
- `include/nav2_smac_planner/obstacle_heuristic.hpp`
- `include/nav2_smac_planner/smac_planner_2d.hpp`
- `include/nav2_smac_planner/smac_planner_hybrid.hpp`
- `include/nav2_smac_planner/smac_planner_lattice.hpp`
- `include/nav2_smac_planner/smoother.hpp`
- `include/nav2_smac_planner/thirdparty/robin_hood.h`
- `include/nav2_smac_planner/types.hpp`
- `include/nav2_smac_planner/utils.hpp`

---

### 4.15 `nav2_theta_star_planner/` — package **`nav2_theta_star_planner`**

- **Version:** `1.4.0`
- **package.xml description:** Theta* Global Planning Plugin
- **Purpose:** Theta* any-angle grid planner plugin.
- **Source file count (excl. tests):** 6

#### sources (src/)

- `src/parameter_handler.cpp`
- `src/theta_star.cpp`
- `src/theta_star_planner.cpp`

#### headers (include/)

- `include/nav2_theta_star_planner/parameter_handler.hpp`
- `include/nav2_theta_star_planner/theta_star.hpp`
- `include/nav2_theta_star_planner/theta_star_planner.hpp`

---

### 4.16 `nav2_route/` — package **`nav2_route`**

- **Version:** `1.1.0`
- **package.xml description:** A Route Graph planner to compliment the Planner Server
- **Purpose:** Route graph server: GeoJSON load/save, edge scorers, route tracker, typed **route operations** plugins.
- **Source file count (excl. tests):** 60

#### executables (main entry)

- `src/main.cpp`

#### sources (`src/edge_scorer.cpp/`)

- `src/edge_scorer.cpp`

#### sources (`src/goal_intent_extractor.cpp/`)

- `src/goal_intent_extractor.cpp`

#### sources (`src/graph_loader.cpp/`)

- `src/graph_loader.cpp`

#### sources (`src/graph_saver.cpp/`)

- `src/graph_saver.cpp`

#### sources (`src/node_spatial_tree.cpp/`)

- `src/node_spatial_tree.cpp`

#### sources (`src/operations_manager.cpp/`)

- `src/operations_manager.cpp`

#### sources (`src/path_converter.cpp/`)

- `src/path_converter.cpp`

#### sources (`src/plugins/`)

- `src/plugins/edge_cost_functions/costmap_scorer.cpp`
- `src/plugins/edge_cost_functions/distance_scorer.cpp`
- `src/plugins/edge_cost_functions/dynamic_edges_scorer.cpp`
- `src/plugins/edge_cost_functions/goal_orientation_scorer.cpp`
- `src/plugins/edge_cost_functions/penalty_scorer.cpp`
- `src/plugins/edge_cost_functions/semantic_scorer.cpp`
- `src/plugins/edge_cost_functions/start_pose_orientation_scorer.cpp`
- `src/plugins/edge_cost_functions/time_scorer.cpp`
- `src/plugins/graph_file_loaders/geojson_graph_file_loader.cpp`
- `src/plugins/graph_file_savers/geojson_graph_file_saver.cpp`
- `src/plugins/route_operations/adjust_speed_limit.cpp`
- `src/plugins/route_operations/collision_monitor.cpp`
- `src/plugins/route_operations/rerouting_service.cpp`
- `src/plugins/route_operations/time_marker.cpp`
- `src/plugins/route_operations/trigger_event.cpp`

#### sources (`src/route_planner.cpp/`)

- `src/route_planner.cpp`

#### sources (`src/route_server.cpp/`)

- `src/route_server.cpp`

#### sources (`src/route_tracker.cpp/`)

- `src/route_tracker.cpp`

#### headers (include/)

- `include/nav2_route/corner_smoothing.hpp`
- `include/nav2_route/edge_scorer.hpp`
- `include/nav2_route/goal_intent_extractor.hpp`
- `include/nav2_route/goal_intent_search.hpp`
- `include/nav2_route/graph_loader.hpp`
- `include/nav2_route/graph_saver.hpp`
- `include/nav2_route/interfaces/edge_cost_function.hpp`
- `include/nav2_route/interfaces/graph_file_loader.hpp`
- `include/nav2_route/interfaces/graph_file_saver.hpp`
- `include/nav2_route/interfaces/route_operation.hpp`
- `include/nav2_route/node_spatial_tree.hpp`
- `include/nav2_route/operations_manager.hpp`
- `include/nav2_route/path_converter.hpp`
- `include/nav2_route/plugins/edge_cost_functions/costmap_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/distance_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/dynamic_edges_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/goal_orientation_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/penalty_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/semantic_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/start_pose_orientation_scorer.hpp`
- `include/nav2_route/plugins/edge_cost_functions/time_scorer.hpp`
- `include/nav2_route/plugins/graph_file_loaders/geojson_graph_file_loader.hpp`
- `include/nav2_route/plugins/graph_file_savers/geojson_graph_file_saver.hpp`
- `include/nav2_route/plugins/route_operation_client.hpp`
- `include/nav2_route/plugins/route_operations/adjust_speed_limit.hpp`
- `include/nav2_route/plugins/route_operations/collision_monitor.hpp`
- `include/nav2_route/plugins/route_operations/rerouting_service.hpp`
- `include/nav2_route/plugins/route_operations/time_marker.hpp`
- `include/nav2_route/plugins/route_operations/trigger_event.hpp`
- `include/nav2_route/route_planner.hpp`
- `include/nav2_route/route_server.hpp`
- `include/nav2_route/route_tracker.hpp`
- `include/nav2_route/types.hpp`
- `include/nav2_route/utils.hpp`

---

### 4.17 `nav2_smoother/` — package **`nav2_smoother`**

- **Version:** `1.4.0`
- **package.xml description:** Smoother action interface
- **Purpose:** `SmootherServer`: hosts `nav2_core::Smoother` plugins (simple / Savitzky–Golay / constrained via separate package).
- **Source file count (excl. tests):** 7

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/nav2_smoother.cpp`
- `src/savitzky_golay_smoother.cpp`
- `src/simple_smoother.cpp`

#### headers (include/)

- `include/nav2_smoother/nav2_smoother.hpp`
- `include/nav2_smoother/savitzky_golay_smoother.hpp`
- `include/nav2_smoother/simple_smoother.hpp`

---

### 4.18 `nav2_constrained_smoother/` — package **`nav2_constrained_smoother`**

- **Version:** `1.4.0`
- **package.xml description:** Ceres constrained smoother
- **Purpose:** Ceres-based path smoother plugin with kinematic constraints.
- **Source file count (excl. tests):** 6

#### sources (src/)

- `src/constrained_smoother.cpp`

#### headers (include/)

- `include/nav2_constrained_smoother/constrained_smoother.hpp`
- `include/nav2_constrained_smoother/options.hpp`
- `include/nav2_constrained_smoother/smoother.hpp`
- `include/nav2_constrained_smoother/smoother_cost_function.hpp`
- `include/nav2_constrained_smoother/utils.hpp`

---

### 4.19 `nav2_controller/` — package **`nav2_controller`**

- **Version:** `1.4.0`
- **package.xml description:** Controller action interface
- **Purpose:** `ControllerServer` lifecycle node: loads `Controller`, `GoalChecker`, `ProgressChecker`, `PathHandler` plugins; publishes `cmd_vel`.
- **Source file count (excl. tests):** 19

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/controller_server.cpp`
- `src/parameter_handler.cpp`

#### plugins/

- `plugins/axis_goal_checker.cpp`
- `plugins/feasible_path_handler.cpp`
- `plugins/pose_progress_checker.cpp`
- `plugins/position_goal_checker.cpp`
- `plugins/simple_goal_checker.cpp`
- `plugins/simple_progress_checker.cpp`
- `plugins/stopped_goal_checker.cpp`

#### headers (include/)

- `include/nav2_controller/controller_server.hpp`
- `include/nav2_controller/parameter_handler.hpp`
- `include/nav2_controller/plugins/axis_goal_checker.hpp`
- `include/nav2_controller/plugins/feasible_path_handler.hpp`
- `include/nav2_controller/plugins/pose_progress_checker.hpp`
- `include/nav2_controller/plugins/position_goal_checker.hpp`
- `include/nav2_controller/plugins/simple_goal_checker.hpp`
- `include/nav2_controller/plugins/simple_progress_checker.hpp`
- `include/nav2_controller/plugins/stopped_goal_checker.hpp`

---

### 4.20 `nav2_regulated_pure_pursuit_controller/` — package **`nav2_regulated_pure_pursuit_controller`**

- **Version:** `1.4.0`
- **package.xml description:** Regulated Pure Pursuit Controller
- **Purpose:** Curvature-regulated pure pursuit local trajectory follower plugin.
- **Source file count (excl. tests):** 8

#### sources (src/)

- `src/collision_checker.cpp`
- `src/parameter_handler.cpp`
- `src/regulated_pure_pursuit_controller.cpp`

#### headers (include/)

- `include/nav2_regulated_pure_pursuit_controller/collision_checker.hpp`
- `include/nav2_regulated_pure_pursuit_controller/dynamic_window_pure_pursuit_functions.hpp`
- `include/nav2_regulated_pure_pursuit_controller/parameter_handler.hpp`
- `include/nav2_regulated_pure_pursuit_controller/regulated_pure_pursuit_controller.hpp`
- `include/nav2_regulated_pure_pursuit_controller/regulation_functions.hpp`

---

### 4.21 `nav2_mppi_controller/` — package **`nav2_mppi_controller`**

- **Version:** `1.4.0`
- **package.xml description:** nav2_mppi_controller
- **Purpose:** MPPI model predictive controller: motion model rollouts + critic scoring + optimizer loop.
- **Source file count (excl. tests):** 48

#### sources (src/)

- `src/controller.cpp`
- `src/critic_manager.cpp`
- `src/critics/constraint_critic.cpp`
- `src/critics/cost_critic.cpp`
- `src/critics/goal_angle_critic.cpp`
- `src/critics/goal_critic.cpp`
- `src/critics/obstacles_critic.cpp`
- `src/critics/path_align_critic.cpp`
- `src/critics/path_angle_critic.cpp`
- `src/critics/path_follow_critic.cpp`
- `src/critics/prefer_forward_critic.cpp`
- `src/critics/twirling_critic.cpp`
- `src/critics/velocity_deadband_critic.cpp`
- `src/noise_generator.cpp`
- `src/optimizer.cpp`
- `src/parameters_handler.cpp`
- `src/trajectory_validators/optimal_trajectory_validator.cpp`
- `src/trajectory_visualizer.cpp`

#### headers (include/)

- `include/nav2_mppi_controller/controller.hpp`
- `include/nav2_mppi_controller/critic_data.hpp`
- `include/nav2_mppi_controller/critic_function.hpp`
- `include/nav2_mppi_controller/critic_manager.hpp`
- `include/nav2_mppi_controller/critics/constraint_critic.hpp`
- `include/nav2_mppi_controller/critics/cost_critic.hpp`
- `include/nav2_mppi_controller/critics/goal_angle_critic.hpp`
- `include/nav2_mppi_controller/critics/goal_critic.hpp`
- `include/nav2_mppi_controller/critics/obstacles_critic.hpp`
- `include/nav2_mppi_controller/critics/path_align_critic.hpp`
- `include/nav2_mppi_controller/critics/path_angle_critic.hpp`
- `include/nav2_mppi_controller/critics/path_follow_critic.hpp`
- `include/nav2_mppi_controller/critics/prefer_forward_critic.hpp`
- `include/nav2_mppi_controller/critics/twirling_critic.hpp`
- `include/nav2_mppi_controller/critics/velocity_deadband_critic.hpp`
- `include/nav2_mppi_controller/models/constraints.hpp`
- `include/nav2_mppi_controller/models/control_sequence.hpp`
- `include/nav2_mppi_controller/models/optimizer_settings.hpp`
- `include/nav2_mppi_controller/models/path.hpp`
- `include/nav2_mppi_controller/models/state.hpp`
- `include/nav2_mppi_controller/models/trajectories.hpp`
- `include/nav2_mppi_controller/motion_models.hpp`
- `include/nav2_mppi_controller/optimal_trajectory_validator.hpp`
- `include/nav2_mppi_controller/optimizer.hpp`
- `include/nav2_mppi_controller/tools/noise_generator.hpp`
- `include/nav2_mppi_controller/tools/parameters_handler.hpp`
- `include/nav2_mppi_controller/tools/trajectory_visualizer.hpp`
- `include/nav2_mppi_controller/tools/utils.hpp`

#### benchmark/

- `benchmark/controller_benchmark.cpp`
- `benchmark/optimizer_benchmark.cpp`

---

### 4.22 `nav2_graceful_controller/` — package **`nav2_graceful_controller`**

- **Version:** `1.4.0`
- **package.xml description:** Graceful motion controller
- **Purpose:** Smooth polar-coordinate control law for near-goal graceful slowing.
- **Source file count (excl. tests):** 9

#### sources (src/)

- `src/graceful_controller.cpp`
- `src/parameter_handler.cpp`
- `src/smooth_control_law.cpp`
- `src/utils.cpp`

#### headers (include/)

- `include/nav2_graceful_controller/ego_polar_coords.hpp`
- `include/nav2_graceful_controller/graceful_controller.hpp`
- `include/nav2_graceful_controller/parameter_handler.hpp`
- `include/nav2_graceful_controller/smooth_control_law.hpp`
- `include/nav2_graceful_controller/utils.hpp`

---

### 4.23 `nav2_rotation_shim_controller/` — package **`nav2_rotation_shim_controller`**

- **Version:** `1.4.0`
- **package.xml description:** Rotation Shim Controller
- **Purpose:** Wrapper controller: performs in-place rotation before delegating to inner controller.
- **Source file count (excl. tests):** 4

#### sources (src/)

- `src/nav2_rotation_shim_controller.cpp`
- `src/parameter_handler.cpp`

#### headers (include/)

- `include/nav2_rotation_shim_controller/nav2_rotation_shim_controller.hpp`
- `include/nav2_rotation_shim_controller/parameter_handler.hpp`

---

### 4.24 `nav2_dwb_controller/nav2_dwb_controller/` — package **`nav2_dwb_controller`**

- **Version:** `1.4.0`
- **package.xml description:** ROS2 controller (DWB) metapackage
- **Purpose:** Metapackage wiring DWB as a `nav2_core::Controller` plugin.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.25 `nav2_dwb_controller/dwb_core/` — package **`dwb_core`**

- **Version:** `1.4.0`
- **package.xml description:** DWB core interfaces package
- **Purpose:** Dynamic Window Benchmark core: trajectory generator + critic scoring loop + `dwb_local_planner`.
- **Source file count (excl. tests):** 11

#### sources (src/)

- `src/dwb_local_planner.cpp`
- `src/illegal_trajectory_tracker.cpp`
- `src/publisher.cpp`
- `src/trajectory_utils.cpp`

#### headers (include/)

- `include/dwb_core/dwb_local_planner.hpp`
- `include/dwb_core/exceptions.hpp`
- `include/dwb_core/illegal_trajectory_tracker.hpp`
- `include/dwb_core/publisher.hpp`
- `include/dwb_core/trajectory_critic.hpp`
- `include/dwb_core/trajectory_generator.hpp`
- `include/dwb_core/trajectory_utils.hpp`

---

### 4.26 `nav2_dwb_controller/dwb_critics/` — package **`dwb_critics`**

- **Version:** `1.4.0`
- **package.xml description:** The dwb_critics package
- **Purpose:** Trajectory cost functions (obstacle, path alignment, oscillation, …).
- **Source file count (excl. tests):** 25

#### sources (src/)

- `src/alignment_util.cpp`
- `src/base_obstacle.cpp`
- `src/goal_align.cpp`
- `src/goal_dist.cpp`
- `src/map_grid.cpp`
- `src/obstacle_footprint.cpp`
- `src/oscillation.cpp`
- `src/path_align.cpp`
- `src/path_dist.cpp`
- `src/prefer_forward.cpp`
- `src/rotate_to_goal.cpp`
- `src/twirling.cpp`

#### headers (include/)

- `include/dwb_critics/alignment_util.hpp`
- `include/dwb_critics/base_obstacle.hpp`
- `include/dwb_critics/goal_align.hpp`
- `include/dwb_critics/goal_dist.hpp`
- `include/dwb_critics/line_iterator.hpp`
- `include/dwb_critics/map_grid.hpp`
- `include/dwb_critics/obstacle_footprint.hpp`
- `include/dwb_critics/oscillation.hpp`
- `include/dwb_critics/path_align.hpp`
- `include/dwb_critics/path_dist.hpp`
- `include/dwb_critics/prefer_forward.hpp`
- `include/dwb_critics/rotate_to_goal.hpp`
- `include/dwb_critics/twirling.hpp`

---

### 4.27 `nav2_dwb_controller/dwb_plugins/` — package **`dwb_plugins`**

- **Version:** `1.4.0`
- **package.xml description:** Standard implementations of the GoalChecker and TrajectoryGenerators for dwb_core
- **Purpose:** Standard trajectory generators and goal checkers for DWB.
- **Source file count (excl. tests):** 10

#### sources (src/)

- `src/kinematic_parameters.cpp`
- `src/limited_accel_generator.cpp`
- `src/standard_traj_generator.cpp`
- `src/xy_theta_iterator.cpp`

#### headers (include/)

- `include/dwb_plugins/kinematic_parameters.hpp`
- `include/dwb_plugins/limited_accel_generator.hpp`
- `include/dwb_plugins/one_d_velocity_iterator.hpp`
- `include/dwb_plugins/standard_traj_generator.hpp`
- `include/dwb_plugins/velocity_iterator.hpp`
- `include/dwb_plugins/xy_theta_iterator.hpp`

---

### 4.28 `nav2_dwb_controller/costmap_queue/` — package **`costmap_queue`**

- **Version:** `1.4.0`
- **package.xml description:** The costmap_queue package
- **Purpose:** Thread-safe cost sampling queue aligned with DWB trajectory discretization.
- **Source file count (excl. tests):** 5

#### sources (src/)

- `src/costmap_queue.cpp`
- `src/limited_costmap_queue.cpp`

#### headers (include/)

- `include/costmap_queue/costmap_queue.hpp`
- `include/costmap_queue/limited_costmap_queue.hpp`
- `include/costmap_queue/map_based_queue.hpp`

---

### 4.29 `nav2_dwb_controller/dwb_msgs/` — package **`dwb_msgs`**

- **Version:** `1.4.0`
- **package.xml description:** Message/Service definitions specifically for the dwb_core
- **Purpose:** Messages for critic scores and trajectory evaluation.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.30 `nav2_dwb_controller/nav_2d_msgs/` — package **`nav_2d_msgs`**

- **Version:** `1.4.0`
- **package.xml description:** Basic message types for two dimensional navigation, extending from geometry_msgs::Pose.
- **Purpose:** 2D navigation message extensions.
- **Source file count (excl. tests):** 0

*No `.cpp/.c/.hpp/.h` sources in this package (metapackage, CMake-only, or assets-only).*

---

### 4.31 `nav2_dwb_controller/nav_2d_utils/` — package **`nav_2d_utils`**

- **Version:** `1.4.0`
- **package.xml description:** A handful of useful utility functions for nav_2d packages.
- **Purpose:** 2D path/pose utilities for DWB.
- **Source file count (excl. tests):** 4

#### sources (src/)

- `src/conversions.cpp`
- `src/path_ops.cpp`

#### headers (include/)

- `include/nav_2d_utils/conversions.hpp`
- `include/nav_2d_utils/path_ops.hpp`

---

### 4.32 `nav2_behavior_tree/` — package **`nav2_behavior_tree`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 behavior tree wrappers, nodes, and utilities
- **Purpose:** BT.CPP node plugins + `BehaviorTreeEngine` + typed `BtActionNode` / service wrappers used by all Nav2 XML trees.
- **Source file count (excl. tests):** 165

#### Special detail: `nav2_behavior_tree/` directory layout

This package is the **largest** in Nav2 by file count. It separates **framework** code from **BT node plugins** registered against BehaviorTree.CPP.

##### `include/nav2_behavior_tree/` — Framework headers (templates for action/service BT nodes)

*File count:* 87

- `include/nav2_behavior_tree/behavior_tree_engine.hpp`, `include/nav2_behavior_tree/bt_action_node.hpp`, `include/nav2_behavior_tree/bt_action_server.hpp`, `include/nav2_behavior_tree/bt_action_server_impl.hpp`, `include/nav2_behavior_tree/bt_cancel_action_node.hpp`, `include/nav2_behavior_tree/bt_service_node.hpp`, `include/nav2_behavior_tree/bt_utils.hpp`, `include/nav2_behavior_tree/json_utils.hpp`
- `include/nav2_behavior_tree/plugins/action/append_goal_pose_to_goals_action.hpp`, `include/nav2_behavior_tree/plugins/action/assisted_teleop_action.hpp`, `include/nav2_behavior_tree/plugins/action/assisted_teleop_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/back_up_action.hpp`, `include/nav2_behavior_tree/plugins/action/back_up_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/check_pose_occupancy_action.hpp`, `include/nav2_behavior_tree/plugins/action/check_stop_status_action.hpp`, `include/nav2_behavior_tree/plugins/action/clear_costmap_service.hpp`
- `include/nav2_behavior_tree/plugins/action/compute_and_track_route_action.hpp`, `include/nav2_behavior_tree/plugins/action/compute_and_track_route_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/compute_path_through_poses_action.hpp`, `include/nav2_behavior_tree/plugins/action/compute_path_to_pose_action.hpp`, `include/nav2_behavior_tree/plugins/action/compute_route_action.hpp`, `include/nav2_behavior_tree/plugins/action/concatenate_paths_action.hpp`, `include/nav2_behavior_tree/plugins/action/controller_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/controller_selector_node.hpp`
- `include/nav2_behavior_tree/plugins/action/drive_on_heading_action.hpp`, `include/nav2_behavior_tree/plugins/action/drive_on_heading_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/extract_route_nodes_as_goals_action.hpp`, `include/nav2_behavior_tree/plugins/action/follow_object_action.hpp`, `include/nav2_behavior_tree/plugins/action/follow_object_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/follow_path_action.hpp`, `include/nav2_behavior_tree/plugins/action/get_current_pose_action.hpp`, `include/nav2_behavior_tree/plugins/action/get_next_few_goals_action.hpp`
- `include/nav2_behavior_tree/plugins/action/get_pose_from_path_action.hpp`, `include/nav2_behavior_tree/plugins/action/goal_checker_selector_node.hpp`, `include/nav2_behavior_tree/plugins/action/navigate_through_poses_action.hpp`, `include/nav2_behavior_tree/plugins/action/navigate_to_pose_action.hpp`, `include/nav2_behavior_tree/plugins/action/path_handler_selector_node.hpp`, `include/nav2_behavior_tree/plugins/action/planner_selector_node.hpp`, `include/nav2_behavior_tree/plugins/action/progress_checker_selector_node.hpp`, `include/nav2_behavior_tree/plugins/action/reinitialize_global_localization_service.hpp`
- `include/nav2_behavior_tree/plugins/action/remove_in_collision_goals_action.hpp`, `include/nav2_behavior_tree/plugins/action/remove_passed_goals_action.hpp`, `include/nav2_behavior_tree/plugins/action/smooth_path_action.hpp`, `include/nav2_behavior_tree/plugins/action/smoother_selector_node.hpp`, `include/nav2_behavior_tree/plugins/action/spin_action.hpp`, `include/nav2_behavior_tree/plugins/action/spin_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/action/toggle_collision_monitor_service.hpp`, `include/nav2_behavior_tree/plugins/action/truncate_path_action.hpp`
- `include/nav2_behavior_tree/plugins/action/truncate_path_local_action.hpp`, `include/nav2_behavior_tree/plugins/action/validate_path_action.hpp`, `include/nav2_behavior_tree/plugins/action/wait_action.hpp`, `include/nav2_behavior_tree/plugins/action/wait_cancel_node.hpp`, `include/nav2_behavior_tree/plugins/condition/are_error_codes_present_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/are_poses_near_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/distance_traveled_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/globally_updated_goal_condition.hpp`
- `include/nav2_behavior_tree/plugins/condition/goal_reached_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/goal_updated_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/initial_pose_received_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/is_battery_charging_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/is_battery_low_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/is_goal_nearby_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/is_stuck_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/is_within_path_tracking_bounds_condition.hpp`
- `include/nav2_behavior_tree/plugins/condition/path_expiring_timer_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/time_expired_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/transform_available_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/would_a_controller_recovery_help_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/would_a_planner_recovery_help_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/would_a_route_recovery_help_condition.hpp`, `include/nav2_behavior_tree/plugins/condition/would_a_smoother_recovery_help_condition.hpp`, `include/nav2_behavior_tree/plugins/control/nonblocking_sequence.hpp`
- `include/nav2_behavior_tree/plugins/control/pause_resume_controller.hpp`, `include/nav2_behavior_tree/plugins/control/persistent_sequence.hpp`, `include/nav2_behavior_tree/plugins/control/pipeline_sequence.hpp`, `include/nav2_behavior_tree/plugins/control/recovery_node.hpp`, `include/nav2_behavior_tree/plugins/control/round_robin_node.hpp`, `include/nav2_behavior_tree/plugins/decorator/distance_controller.hpp`, `include/nav2_behavior_tree/plugins/decorator/goal_updated_controller.hpp`, `include/nav2_behavior_tree/plugins/decorator/goal_updater_node.hpp`
- `include/nav2_behavior_tree/plugins/decorator/path_longer_on_approach.hpp`, `include/nav2_behavior_tree/plugins/decorator/rate_controller.hpp`, `include/nav2_behavior_tree/plugins/decorator/single_trigger_node.hpp`, `include/nav2_behavior_tree/plugins/decorator/speed_controller.hpp`, `include/nav2_behavior_tree/ros_topic_logger.hpp`, `include/nav2_behavior_tree/utils/loop_rate.hpp`, `include/nav2_behavior_tree/utils/test_action_server.hpp`

##### `src/` — Framework implementations (`behavior_tree_engine.cpp`, logging, utils)

*File count:* 2

- `src/behavior_tree_engine.cpp`, `src/generate_nav2_tree_nodes_xml.cpp`

##### `plugins/action/` — Action-style BT leaves (call Nav2 servers)

*File count:* 44

- `plugins/action/append_goal_pose_to_goals_action.cpp`, `plugins/action/assisted_teleop_action.cpp`, `plugins/action/assisted_teleop_cancel_node.cpp`, `plugins/action/back_up_action.cpp`, `plugins/action/back_up_cancel_node.cpp`, `plugins/action/check_pose_occupancy_action.cpp`, `plugins/action/check_stop_status_action.cpp`, `plugins/action/clear_costmap_service.cpp`
- `plugins/action/compute_and_track_route_action.cpp`, `plugins/action/compute_and_track_route_cancel_node.cpp`, `plugins/action/compute_path_through_poses_action.cpp`, `plugins/action/compute_path_to_pose_action.cpp`, `plugins/action/compute_route_action.cpp`, `plugins/action/concatenate_paths_action.cpp`, `plugins/action/controller_cancel_node.cpp`, `plugins/action/controller_selector_node.cpp`
- `plugins/action/drive_on_heading_action.cpp`, `plugins/action/drive_on_heading_cancel_node.cpp`, `plugins/action/extract_route_nodes_as_goals_action.cpp`, `plugins/action/follow_object_action.cpp`, `plugins/action/follow_object_cancel_node.cpp`, `plugins/action/follow_path_action.cpp`, `plugins/action/get_current_pose_action.cpp`, `plugins/action/get_next_few_goals_action.cpp`
- `plugins/action/get_pose_from_path_action.cpp`, `plugins/action/goal_checker_selector_node.cpp`, `plugins/action/navigate_through_poses_action.cpp`, `plugins/action/navigate_to_pose_action.cpp`, `plugins/action/path_handler_selector_node.cpp`, `plugins/action/planner_selector_node.cpp`, `plugins/action/progress_checker_selector_node.cpp`, `plugins/action/reinitialize_global_localization_service.cpp`
- `plugins/action/remove_in_collision_goals_action.cpp`, `plugins/action/remove_passed_goals_action.cpp`, `plugins/action/smooth_path_action.cpp`, `plugins/action/smoother_selector_node.cpp`, `plugins/action/spin_action.cpp`, `plugins/action/spin_cancel_node.cpp`, `plugins/action/toggle_collision_monitor_service.cpp`, `plugins/action/truncate_path_action.cpp`
- `plugins/action/truncate_path_local_action.cpp`, `plugins/action/validate_path_action.cpp`, `plugins/action/wait_action.cpp`, `plugins/action/wait_cancel_node.cpp`

##### `plugins/condition/` — Condition BT nodes (check goal, battery, TF, recovery hints)

*File count:* 19

- `plugins/condition/are_error_codes_present_condition.cpp`, `plugins/condition/are_poses_near_condition.cpp`, `plugins/condition/distance_traveled_condition.cpp`, `plugins/condition/globally_updated_goal_condition.cpp`, `plugins/condition/goal_reached_condition.cpp`, `plugins/condition/goal_updated_condition.cpp`, `plugins/condition/initial_pose_received_condition.cpp`, `plugins/condition/is_battery_charging_condition.cpp`
- `plugins/condition/is_battery_low_condition.cpp`, `plugins/condition/is_goal_nearby_condition.cpp`, `plugins/condition/is_stuck_condition.cpp`, `plugins/condition/is_within_path_tracking_bounds_condition.cpp`, `plugins/condition/path_expiring_timer_condition.cpp`, `plugins/condition/time_expired_condition.cpp`, `plugins/condition/transform_available_condition.cpp`, `plugins/condition/would_a_controller_recovery_help_condition.cpp`
- `plugins/condition/would_a_planner_recovery_help_condition.cpp`, `plugins/condition/would_a_route_recovery_help_condition.cpp`, `plugins/condition/would_a_smoother_recovery_help_condition.cpp`

##### `plugins/control/` — Control BT nodes (pipeline, recovery, round-robin)

*File count:* 6

- `plugins/control/nonblocking_sequence.cpp`, `plugins/control/pause_resume_controller.cpp`, `plugins/control/persistent_sequence.cpp`, `plugins/control/pipeline_sequence.cpp`, `plugins/control/recovery_node.cpp`, `plugins/control/round_robin_node.cpp`

##### `plugins/decorator/` — Decorator BT nodes (rate control, goal update, speed control)

*File count:* 7

- `plugins/decorator/distance_controller.cpp`, `plugins/decorator/goal_updated_controller.cpp`, `plugins/decorator/goal_updater_node.cpp`, `plugins/decorator/path_longer_on_approach.cpp`, `plugins/decorator/rate_controller.cpp`, `plugins/decorator/single_trigger_node.cpp`, `plugins/decorator/speed_controller.cpp`

---

### 4.33 `nav2_bt_navigator/` — package **`nav2_bt_navigator`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 BT Navigator Server
- **Purpose:** `BtNavigator` + per-mode **navigator** plugins (`NavigateToPose`, `NavigateThroughPoses`) — loads BT XML and connects to other servers via actions.
- **Source file count (excl. tests):** 7

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/bt_navigator.cpp`
- `src/navigators/navigate_through_poses.cpp`
- `src/navigators/navigate_to_pose.cpp`

#### headers (include/)

- `include/nav2_bt_navigator/bt_navigator.hpp`
- `include/nav2_bt_navigator/navigators/navigate_through_poses.hpp`
- `include/nav2_bt_navigator/navigators/navigate_to_pose.hpp`

---

### 4.34 `nav2_behaviors/` — package **`nav2_behaviors`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2 behavior server
- **Purpose:** `BehaviorServer` hosting timed motion behaviors (spin, backup, drive on heading, assisted teleop, wait).
- **Source file count (excl. tests):** 14

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/behavior_server.cpp`

#### plugins/

- `plugins/assisted_teleop.cpp`
- `plugins/back_up.cpp`
- `plugins/drive_on_heading.cpp`
- `plugins/spin.cpp`
- `plugins/wait.cpp`

#### headers (include/)

- `include/nav2_behaviors/behavior_server.hpp`
- `include/nav2_behaviors/plugins/assisted_teleop.hpp`
- `include/nav2_behaviors/plugins/back_up.hpp`
- `include/nav2_behaviors/plugins/drive_on_heading.hpp`
- `include/nav2_behaviors/plugins/spin.hpp`
- `include/nav2_behaviors/plugins/wait.hpp`
- `include/nav2_behaviors/timed_behavior.hpp`

---

### 4.35 `nav2_waypoint_follower/` — package **`nav2_waypoint_follower`**

- **Version:** `1.4.0`
- **package.xml description:** A waypoint follower navigation server
- **Purpose:** `WaypointFollower` server + `WaypointTaskExecutor` plugins (wait, photo, user input at waypoint).
- **Source file count (excl. tests):** 11

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/parameter_handler.cpp`
- `src/waypoint_follower.cpp`

#### plugins/

- `plugins/input_at_waypoint.cpp`
- `plugins/photo_at_waypoint.cpp`
- `plugins/wait_at_waypoint.cpp`

#### headers (include/)

- `include/nav2_waypoint_follower/parameter_handler.hpp`
- `include/nav2_waypoint_follower/plugins/input_at_waypoint.hpp`
- `include/nav2_waypoint_follower/plugins/photo_at_waypoint.hpp`
- `include/nav2_waypoint_follower/plugins/wait_at_waypoint.hpp`
- `include/nav2_waypoint_follower/waypoint_follower.hpp`

---

### 4.36 `nav2_lifecycle_manager/` — package **`nav2_lifecycle_manager`**

- **Version:** `1.4.0`
- **package.xml description:** A controller/manager for the lifecycle nodes of the Navigation 2 system
- **Purpose:** Brings configured lifecycle node names up/down in order; bond/watchdog support.
- **Source file count (excl. tests):** 5

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/lifecycle_manager.cpp`
- `src/lifecycle_manager_client.cpp`

#### headers (include/)

- `include/nav2_lifecycle_manager/lifecycle_manager.hpp`
- `include/nav2_lifecycle_manager/lifecycle_manager_client.hpp`

---

### 4.37 `nav2_velocity_smoother/` — package **`nav2_velocity_smoother`**

- **Version:** `1.4.0`
- **package.xml description:** Nav2's Output velocity smoother
- **Purpose:** Final-stage `cmd_vel` acceleration/jerk limiting independent of controller plugin.
- **Source file count (excl. tests):** 3

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/velocity_smoother.cpp`

#### headers (include/)

- `include/nav2_velocity_smoother/velocity_smoother.hpp`

---

### 4.38 `nav2_collision_monitor/` — package **`nav2_collision_monitor`**

- **Version:** `1.4.0`
- **package.xml description:** Collision Monitor
- **Purpose:** Safety node: polygon/scan/range sources → stop/slow/downscale `cmd_vel` outside full planner stack.
- **Source file count (excl. tests):** 27

#### executables (main entry)

- `src/collision_detector_main.cpp`
- `src/collision_monitor_main.cpp`

#### sources (src/)

- `src/circle.cpp`
- `src/collision_detector_node.cpp`
- `src/collision_monitor_node.cpp`
- `src/costmap.cpp`
- `src/kinematics.cpp`
- `src/pointcloud.cpp`
- `src/polygon.cpp`
- `src/polygon_source.cpp`
- `src/range.cpp`
- `src/scan.cpp`
- `src/source.cpp`
- `src/velocity_polygon.cpp`

#### headers (include/)

- `include/nav2_collision_monitor/circle.hpp`
- `include/nav2_collision_monitor/collision_detector_node.hpp`
- `include/nav2_collision_monitor/collision_monitor_node.hpp`
- `include/nav2_collision_monitor/costmap.hpp`
- `include/nav2_collision_monitor/kinematics.hpp`
- `include/nav2_collision_monitor/pointcloud.hpp`
- `include/nav2_collision_monitor/polygon.hpp`
- `include/nav2_collision_monitor/polygon_source.hpp`
- `include/nav2_collision_monitor/range.hpp`
- `include/nav2_collision_monitor/scan.hpp`
- `include/nav2_collision_monitor/source.hpp`
- `include/nav2_collision_monitor/types.hpp`
- `include/nav2_collision_monitor/velocity_polygon.hpp`

---

### 4.39 `nav2_docking/opennav_docking_core/` — package **`opennav_docking_core`**

- **Version:** `1.4.0`
- **package.xml description:** A set of headers for plugins core to the opennav docking framework
- **Purpose:** Dock plugin base interfaces (`ChargingDock`, `NonChargingDock`).
- **Source file count (excl. tests):** 3

#### headers (include/)

- `include/opennav_docking_core/charging_dock.hpp`
- `include/opennav_docking_core/docking_exceptions.hpp`
- `include/opennav_docking_core/non_charging_dock.hpp`

---

### 4.40 `nav2_docking/opennav_docking/` — package **`opennav_docking`**

- **Version:** `1.4.0`
- **package.xml description:** A Task Server for robot charger docking
- **Purpose:** `DockingServer` + dock database + simple dock plugins + approach controller.
- **Source file count (excl. tests):** 19

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/controller.cpp`
- `src/dock_database.cpp`
- `src/docking_server.cpp`
- `src/navigator.cpp`
- `src/parameter_handler.cpp`
- `src/pose_filter.cpp`
- `src/simple_charging_dock.cpp`
- `src/simple_non_charging_dock.cpp`

#### headers (include/)

- `include/opennav_docking/controller.hpp`
- `include/opennav_docking/dock_database.hpp`
- `include/opennav_docking/docking_server.hpp`
- `include/opennav_docking/navigator.hpp`
- `include/opennav_docking/parameter_handler.hpp`
- `include/opennav_docking/pose_filter.hpp`
- `include/opennav_docking/simple_charging_dock.hpp`
- `include/opennav_docking/simple_non_charging_dock.hpp`
- `include/opennav_docking/types.hpp`
- `include/opennav_docking/utils.hpp`

---

### 4.41 `nav2_docking/opennav_docking_bt/` — package **`opennav_docking_bt`**

- **Version:** `1.4.0`
- **package.xml description:** A set of BT nodes and XMLs for docking
- **Purpose:** `DockRobot` / `UndockRobot` BT action nodes + include headers; ships XML trees used by `nav2_bt_navigator` when docking is enabled.
- **Source file count (excl. tests):** 4

#### sources (src/)

- `src/dock_robot.cpp`
- `src/undock_robot.cpp`

#### headers (include/)

- `include/opennav_docking_bt/dock_robot.hpp`
- `include/opennav_docking_bt/undock_robot.hpp`

---

### 4.42 `nav2_following/opennav_following/` — package **`opennav_following`**

- **Version:** `1.4.0`
- **package.xml description:** A Task Server for dynamic following object
- **Purpose:** Task server for `FollowObject` using detector + controller hooks.
- **Source file count (excl. tests):** 5

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/following_server.cpp`
- `src/parameter_handler.cpp`

#### headers (include/)

- `include/opennav_following/following_server.hpp`
- `include/opennav_following/parameter_handler.hpp`

---

### 4.43 `nav2_loopback_sim/` — package **`nav2_loopback_sim`**

- **Version:** `1.4.0`
- **package.xml description:** A loopback simulator to replace physics simulation
- **Purpose:** Lightweight TF + sensor loopback for testing without Gazebo.
- **Source file count (excl. tests):** 5

#### executables (main entry)

- `src/main.cpp`

#### sources (src/)

- `src/clock_publisher.cpp`
- `src/loopback_simulator.cpp`

#### headers (include/)

- `include/nav2_loopback_sim/clock_publisher.hpp`
- `include/nav2_loopback_sim/loopback_simulator.hpp`

---

### 4.44 `nav2_rviz_plugins/` — package **`nav2_rviz_plugins`**

- **Version:** `1.4.0`
- **package.xml description:** Navigation 2 plugins for rviz
- **Purpose:** RViz2 panels and tools (goal, route, docking, particle cloud, cost tool).
- **Source file count (excl. tests):** 21

#### sources (src/)

- `src/costmap_cost_tool.cpp`
- `src/docking_panel.cpp`
- `src/goal_tool.cpp`
- `src/nav2_panel.cpp`
- `src/particle_cloud_display/flat_weighted_arrows_array.cpp`
- `src/particle_cloud_display/particle_cloud_display.cpp`
- `src/route_tool.cpp`
- `src/selector.cpp`
- `src/utils.cpp`

#### headers (include/)

- `include/nav2_rviz_plugins/costmap_cost_tool.hpp`
- `include/nav2_rviz_plugins/docking_panel.hpp`
- `include/nav2_rviz_plugins/goal_common.hpp`
- `include/nav2_rviz_plugins/goal_pose_updater.hpp`
- `include/nav2_rviz_plugins/goal_tool.hpp`
- `include/nav2_rviz_plugins/nav2_panel.hpp`
- `include/nav2_rviz_plugins/particle_cloud_display/flat_weighted_arrows_array.hpp`
- `include/nav2_rviz_plugins/particle_cloud_display/particle_cloud_display.hpp`
- `include/nav2_rviz_plugins/ros_action_qevent.hpp`
- `include/nav2_rviz_plugins/route_tool.hpp`
- `include/nav2_rviz_plugins/selector.hpp`
- `include/nav2_rviz_plugins/utils.hpp`

---

### 4.45 `nav2_simple_commander/` — package **`nav2_simple_commander`**

- **Version:** `1.4.0`
- **package.xml description:** An importable library for writing mobile robot applications in python3
- **Purpose:** Python library wrapping Nav2 actions for application scripts (no C++ in package).
- **Source file count (excl. tests):** 0

#### Python modules (`*.py`, excl. tests)

- `launch/assisted_teleop_example_launch.py`
- `launch/follow_path_example_launch.py`
- `launch/inspection_demo_launch.py`
- `launch/nav_through_poses_example_launch.py`
- `launch/nav_to_pose_example_launch.py`
- `launch/picking_demo_launch.py`
- `launch/recoveries_example_launch.py`
- `launch/route_example_launch.py`
- `launch/security_demo_launch.py`
- `launch/waypoint_follower_example_launch.py`
- `nav2_simple_commander/__init__.py`
- `nav2_simple_commander/costmap_2d.py`
- `nav2_simple_commander/demo_inspection.py`
- `nav2_simple_commander/demo_picking.py`
- `nav2_simple_commander/demo_recoveries.py`
- `nav2_simple_commander/demo_security.py`
- `nav2_simple_commander/example_assisted_teleop.py`
- `nav2_simple_commander/example_follow_path.py`
- `nav2_simple_commander/example_nav_through_poses.py`
- `nav2_simple_commander/example_nav_to_pose.py`
- `nav2_simple_commander/example_route.py`
- `nav2_simple_commander/example_waypoint_follower.py`
- `nav2_simple_commander/footprint_collision_checker.py`
- `nav2_simple_commander/line_iterator.py`
- `nav2_simple_commander/occupancy_grid.py`
- `nav2_simple_commander/robot_navigator.py`
- `nav2_simple_commander/utils.py`
- `setup.py`

---

### 4.46 `nav2_system_tests/` — package **`nav2_system_tests`**

- **Version:** `1.4.0`
- **package.xml description:** A sets of system-level tests for Nav2 usually involving full robot simulation
- **Purpose:** GTest-based integration tests with dummy planner/controller and BT harnesses.
- **Source file count (excl. tests):** 31

#### executables (main entry)

- `src/dummy_controller/main.cpp`
- `src/dummy_planner/main.cpp`

#### sources (`src/behavior_tree/`)

- `src/behavior_tree/dummy_action_server.hpp`
- `src/behavior_tree/dummy_service.hpp`
- `src/behavior_tree/server_handler.cpp`
- `src/behavior_tree/server_handler.hpp`
- `src/behavior_tree/test_behavior_tree_node.cpp`

#### sources (`src/behaviors/`)

- `src/behaviors/assisted_teleop/assisted_teleop_behavior_tester.cpp`
- `src/behaviors/assisted_teleop/assisted_teleop_behavior_tester.hpp`
- `src/behaviors/assisted_teleop/test_assisted_teleop_behavior_node.cpp`
- `src/behaviors/wait/test_wait_behavior_node.cpp`
- `src/behaviors/wait/wait_behavior_tester.cpp`
- `src/behaviors/wait/wait_behavior_tester.hpp`

#### sources (`src/dummy_controller/`)

- `src/dummy_controller/dummy_controller.cpp`
- `src/dummy_controller/dummy_controller.hpp`

#### sources (`src/dummy_planner/`)

- `src/dummy_planner/dummy_planner.cpp`
- `src/dummy_planner/dummy_planner.hpp`

#### sources (`src/error_codes/`)

- `src/error_codes/controller/controller_error_plugins.cpp`
- `src/error_codes/controller/controller_error_plugins.hpp`
- `src/error_codes/planner/planner_error_plugin.cpp`
- `src/error_codes/planner/planner_error_plugin.hpp`
- `src/error_codes/smoother/smoother_error_plugin.cpp`
- `src/error_codes/smoother/smoother_error_plugin.hpp`

#### sources (`src/localization/`)

- `src/localization/test_localization_node.cpp`

#### sources (`src/planning/`)

- `src/planning/planner_tester.cpp`
- `src/planning/planner_tester.hpp`
- `src/planning/test_planner_costmaps_node.cpp`
- `src/planning/test_planner_is_path_valid.cpp`
- `src/planning/test_planner_plugins.cpp`
- `src/planning/test_planner_random_node.cpp`

#### sources (`src/updown/`)

- `src/updown/test_updown.cpp`

---

## 5. Runtime execution & data flow

```
[Application]
   │ NavigateToPose / FollowWaypoints (nav2_msgs actions)
   ▼
bt_navigator (loads behavior_tree.xml)
   ├─► planner_server  ──► GlobalPlanner plugin (Smac, NavFn, Theta*, Route…)
   ├─► smoother_server ──► Smoother plugins
   ├─► controller_server ──► Controller plugin (RPP, MPPI, DWB, Graceful, …)
   │         ▲
   │         │ local_costmap + global_costmap (nav2_costmap_2d)
   │         │ map from map_server + static layer
   │         │ AMCL publishes map→odom
   ├─► behavior_server (Spin, BackUp, …)
   └─► optional: docking_server, following, collision_monitor
velocity_smoother → cmd_vel → /diff_drive_controller (your stack)
lifecycle_manager: configure/activate ordering for all managed nodes
```

---

## 6. Quick lookup: class ↔ file

| Class / node (approx.) | Primary file |
|------------------------|----------------|
| `PlannerServer` | `nav2_planner/src/planner_server.cpp` |
| `ControllerServer` | `nav2_controller/src/controller_server.cpp` |
| `SmootherServer` | `nav2_smoother/src/nav2_smoother.cpp` |
| `BtNavigator` | `nav2_bt_navigator/src/bt_navigator.cpp` |
| `NavigateToPose` navigator | `nav2_bt_navigator/src/navigators/navigate_to_pose.cpp` |
| `BehaviorTreeEngine` | `nav2_behavior_tree/src/behavior_tree_engine.cpp` |
| `LayeredCostmap` / `Costmap2DROS` | `nav2_costmap_2d/src/layered_costmap.cpp`, `costmap_2d_ros.cpp` |
| `AmclNode` | `nav2_amcl/src/amcl_node.cpp` |
| `LifecycleManager` | `nav2_lifecycle_manager/src/lifecycle_manager.cpp` |
| `DockingServer` | `nav2_docking/opennav_docking/src/docking_server.cpp` |
| `RouteServer` | `nav2_route/src/route_server.cpp` |
| `MPPIController` | `nav2_mppi_controller/src/controller.cpp` |
| `Optimizer` (MPPI) | `nav2_mppi_controller/src/optimizer.cpp` |
| `Costmap2DROS` | `nav2_costmap_2d/src/costmap_2d_ros.cpp` |
| `LayeredCostmap` | `nav2_costmap_2d/src/layered_costmap.cpp` |
| `NavFnPlanner` | `nav2_navfn_planner/src/navfn_planner.cpp` |
| `VelocitySmoother` | `nav2_velocity_smoother/src/velocity_smoother.cpp` |

