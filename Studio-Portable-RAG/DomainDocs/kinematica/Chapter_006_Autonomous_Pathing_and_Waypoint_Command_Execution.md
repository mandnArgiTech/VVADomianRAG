# Autonomous Pathing, Guided Navigation, and Mission Commands

_Generated 2026-04-14 18:38 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_auto.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_guided.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/commands.cpp`

# Autonomous Pathing, Guided Navigation, and Mission Commands

This chapter documents the high-level autonomous navigation stack for the 400Hz agricultural rover. The system, implemented across `mode_auto.cpp`, `mode_guided.cpp`, and `commands.cpp`, provides waypoint-based path following using L1/Pure Pursuit guidance, MAVLink mission command execution, and off-board guided velocity control. These modules translate mission objectives into precise skid-steer force commands while guaranteeing stability through rigorous mathematical formulations.

## Waypoint Vector Formulation: L1/Pure Pursuit Navigation Mathematics

**L1 Navigation Algorithm Formulation:**
The L1 navigation algorithm computes the cross-track error (XTE) and desired heading using a look-ahead point on the path segment. Given waypoints WPᵢ and WPᵢ₊₁ forming a path segment, and vehicle position P:

```
e = (P - WPᵢ) - ((P - WPᵢ)·û)·û  // Cross-track error vector
η = ||e||  // Cross-track error magnitude
L1 = √(η² + L₁²)  // L1 distance (L₁ = look-ahead distance)
ψ_desired = atan2(û_y, û_x) + atan(K·η/L₁)  // Desired heading
```

Where:
- û = unit vector from WPᵢ to WPᵢ₊₁
- K = curvature gain (typically 2.0)
- L₁ = look-ahead distance (function of ground speed)

**Pure Pursuit Algorithm:**
The pure pursuit algorithm uses a circular arc to intercept the path:

```
R = L₁²/(2·η)  // Radius of pursuit circle
ω_desired = v/R = (2·v·η)/L₁²  // Desired turn rate
```

**3D Waypoint Interpolation with Altitude:**
For 3D navigation with altitude waypoints:
```
P_target = WPᵢ + λ·(WPᵢ₊₁ - WPᵢ)  // Linear interpolation
λ = max(0, min(1, (P - WPᵢ)·û / ||WPᵢ₊₁ - WPᵢ||))
alt_target = altᵢ + λ·(altᵢ₊₁ - altᵢ)
```

**Cross-Track Error Calculation:**
The cross-track error vector is computed using vector projection:
```
along_track_dist = (P - WPᵢ)·û
along_track_vector = along_track_dist·û
cross_track_vector = (P - WPᵢ) - along_track_vector
η = ||cross_track_vector||
```

**Look-Ahead Distance Adaptation:**
For the heavy agricultural rover, L₁ adapts based on ground speed:
```
L₁ = clamp(v·τ, L₁_min, L₁_max)
```
Where τ = 2.0 seconds (typical time constant), L₁_min = 5.0m, L₁_max = 20.0m.

**Waypoint Reached Detection:**
A waypoint is considered reached when:
```
distance_to_wp = ||P - WPᵢ|| ≤ acceptance_radius
AND
altitude_difference = |alt_current - alt_wp| ≤ 5.0m
```

## Mission Command Execution Analysis: MAVLink Parsing and Trajectory Generation

**MAVLink Mission Item Structure:**
MAVLink mission items contain 7 float32 parameters with specific meanings per command type. For MAV_CMD_NAV_WAYPOINT:
- param1: Hold time (seconds)
- param2: Acceptance radius (meters)
- param3: Pass through radius (meters)
- param4: Desired yaw angle (degrees)
- x, y, z: Latitude, Longitude, Altitude

**Command Execution State Machine:**
The state machine implements:
```
State Machine: IDLE → PARSING → EXECUTING → COMPLETING → NEXT
Transition conditions:
- IDLE → PARSING: mission item received via MAVLink
- PARSING → EXECUTING: command validated, resources allocated
- EXECUTING → COMPLETING: command completion condition met
- COMPLETING → NEXT: cleanup complete, advance to next item
```

**Trajectory Generation Matrices:**
For velocity-controlled guided mode:
```
ẋ = A·x + B·u
y = C·x
```
Where:
- x = [position, velocity]ᵀ ∈ ℝ⁶
- u = [desired_velocity, desired_acceleration]ᵀ ∈ ℝ³
- A = [[0, I], [0, 0]] (6×6)
- B = [[0], [I]] (6×3)
- C = [I, 0] (3×6)

**Cubic Polynomial Trajectory Generation:**
For smooth motion between waypoints, cubic polynomials are used:
```
p(t) = a₀ + a₁·t + a₂·t² + a₃·t³
```
With boundary conditions:
```
p(0) = start_position, p(T) = end_position
ṗ(0) = start_velocity, ṗ(T) = end_velocity
```

Solving for coefficients:
```
a₀ = start_position
a₁ = start_velocity
a₂ = (3/T²)·(end_position - start_position) - (2/T)·start_velocity - (1/T)·end_velocity
a₃ = (-2/T³)·(end_position - start_position) + (1/T²)·(start_velocity + end_velocity)
```

**Position Control PID Law:**
The position controller implements:
```
a_cmd = K_p·e_position + K_i·∫e_position dt + K_d·e_velocity
```
Where:
- e_position = target_position - current_position
- e_velocity = target_velocity - current_velocity

**Velocity Control PI Law:**
For velocity control mode:
```
a_cmd = K_p·e_velocity + K_i·∫e_velocity dt
```

**Differential Drive Conversion:**
For the skid-steer rover, acceleration commands convert to wheel forces:
```
F_left = 0.5·(m·a_x - (2·J·ω_desired)/T)
F_right = 0.5·(m·a_x + (2·J·ω_desired)/T)
```
Where:
- m = vehicle mass (kg)
- J = moment of inertia (kg·m²)
- T = track width (m)
- ω_desired = desired angular acceleration (rad/s²)

**PWM Conversion with Limits:**
```
pwm = 1500 + (force / max_force)·500
pwm_clamped = clamp(pwm, 1100, 1900)
```

**L1 Navigation Stability Analysis:**
The linearized dynamics around the path:
```
Δη̇ = v·Δψ
Δψ̇ = (2·v/L₁²)·Δη
```
Characteristic equation:
```
s² - (2·v²/L₁²) = 0
```
With added damping term K_d·η̇:
```
s² + K_d·s - (2·v²/L₁²) = 0
```
Stability requires:
```
K_d > 0 and K_d² > 8·v²/L₁²
```

**Position Controller Stability:**
The third-order system:
```
ë + K_d·ė + K_p·e + K_i·∫e dt = 0
```
Characteristic equation:
```
s³ + K_d·s² + K_p·s + K_i = 0
```
Routh-Hurwitz stability criteria:
```
K_d > 0, K_p > 0, K_i > 0
K_d·K_p > K_i
```

**MAVLink Message Validation:**
For mission item validation:
```
valid = (command ∈ valid_command_set) ∧
        (frame ∈ {MAV_FRAME_GLOBAL, MAV_FRAME_LOCAL_NED, ...}) ∧
        (parameters within valid_ranges[command]) ∧
        (coordinates within physical_limits)
```

**Trajectory Completion Detection:**
A trajectory is complete when:
```
||position_error|| < position_tolerance ∧
||velocity_error|| < velocity_tolerance ∧
t ≥ trajectory_duration
```
Where position_tolerance = 0.1m, velocity_tolerance = 0.05m/s for the heavy rover.

## C++ Implementation Forensic Breakdown

### Target Heading Trigonometry (mode_auto.cpp)
The `AutoModeController` implements L1 navigation with direct hardware integration for the skid-steer rover.

```cpp
// mode_auto.cpp - L1 Navigation Controller
struct __attribute__((packed, aligned(4))) WaypointData {
    float lat;          // 0x20002000: Latitude (degrees * 1e7)
    float lon;          // 0x20002004: Longitude (degrees * 1e7)
    float alt;          // 0x20002008: Altitude (meters AMSL)
    float acceptance_radius; // 0x2000200C: Acceptance radius (m)
    uint16_t command;   // 0x20002010: MAVLink command ID
    uint8_t frame;      // 0x20002012: MAV_FRAME
    uint8_t current;    // 0x20002013: Current waypoint flag
};

struct __attribute__((packed, aligned(4))) NavState {
    float xtrack_error_mag __attribute__((section(".dtcm"))); // 0x20002100: η
    float look_ahead_distance;      // 0x20002104: L₁
    float desired_heading;          // 0x20002108: ψ_desired (rad)
    float desired_turn_rate;        // 0x2000210C: ω_desired (rad/s)
    float along_track_dist;         // 0x20002110: Along-track distance
    uint8_t wp_reached;             // 0x20002114: Waypoint reached flag
};

struct __attribute__((packed, aligned(4))) L1Gains {
    float K_xtrack;     // 0x20002120: K = 2.0 (curvature gain)
    float K_yaw;        // 0x20002124: Yaw damping gain
    float L1_min;       // 0x20002128: 5.0m
    float L1_max;       // 0x2000212C: 20.0m
    float L1_tau;       // 0x20002130: τ = 2.0s
};

class AutoModeController {
public:
    __attribute__((section(".itcm")))
    void update_navigation(float dt) {
        // 1. Get current position from EKF (DMA buffer at 0x2000A000)
        volatile float* ekf_state = (volatile float*)0x2000A000;
        float pos_north = ekf_state[0];  // x in NED
        float pos_east = ekf_state[1];   // y in NED
        float pos_down = ekf_state[2];   // z in NED (negative altitude)
        
        // 2. Get current waypoints
        WaypointData* wp_current = (WaypointData*)0x20002000;
        WaypointData* wp_next = (WaypointData*)0x20002020;
        
        // 3. Convert waypoints to local NED (simplified - assumes small area)
        float wp1_north = wp_current->lat * 1.0e-7f * 111319.0f;
        float wp1_east = wp_current->lon * 1.0e-7f * 111319.0f;
        float wp2_north = wp_next->lat * 1.0e-7f * 111319.0f;
        float wp2_east = wp_next->lon * 1.0e-7f * 111319.0f;
        
        // 4. Compute path vector and unit vector
        float path_vec_north = wp2_north - wp1_north;
        float path_vec_east = wp2_east - wp1_east;
        float path_length = sqrtf(path_vec_north*path_vec_north + 
                                 path_vec_east*path_vec_east);
        
        if (path_length < 0.001f) {
            nav_state.desired_heading = 0.0f;
            return;
        }
        
        float u_north = path_vec_north / path_length;
        float u_east = path_vec_east / path_length;
        
        // 5. Compute vector from current waypoint to vehicle
        float vec_to_wp_north = pos_north - wp1_north;
        float vec_to_wp_east = pos_east - wp1_east;
        
        // 6. Compute along-track distance (projection)
        nav_state.along_track_dist = vec_to_wp_north * u_north + 
                                    vec_to_wp_east * u_east;
        
        // 7. Compute cross-track error vector
        float along_vec_north = nav_state.along_track_dist * u_north;
        float along_vec_east = nav_state.along_track_dist * u_east;
        
        float cross_vec_north = vec_to_wp_north - along_vec_north;
        float cross_vec_east = vec_to_wp_east - along_vec_east;
        
        // 8. Cross-track error magnitude (η)
        nav_state.xtrack_error_mag = sqrtf(cross_vec_north*cross_vec_north + 
                                          cross_vec_east*cross_vec_east);
        
        // 9. Determine sign of cross-track error (left/right of path)
        float cross_sign = (u_north * cross_vec_east - u_east * cross_vec_north) > 0 ? 1.0f : -1.0f;
        nav_state.xtrack_error_mag *= cross_sign;
        
        // 10. Adapt look-ahead distance based on ground speed
        float ground_speed = sqrtf(ekf_state[3]*ekf_state[3] + 
                                  ekf_state[4]*ekf_state[4]); // vx, vy
        float L1_nominal = ground_speed * l1_gains.L1_tau;
        nav_state.look_ahead_distance = L1_nominal;
        
        // Clamp to min/max
        if (nav_state.look_ahead_distance < l1_gains.L1_min)
            nav_state.look_ahead_distance = l1_gains.L1_min;
        if (nav_state.look_ahead_distance > l1_gains.L1_max)
            nav_state.look_ahead_distance = l1_gains.L1_max;
        
        // 11. Compute desired heading using L1 formula
        float path_heading = atan2f(u_east, u_north);
        float eta_over_L1 = nav_state.xtrack_error_mag / nav_state.look_ahead_distance;
        float correction_angle = atanf(l1_gains.K_xtrack * eta_over_L1);
        
        nav_state.desired_heading = path_heading + correction_angle;
        
        // Normalize to [-π, π]
        while (nav_state.desired_heading > M_PI) nav_state.desired_heading -= 2.0f * M_PI;
        while (nav_state.desired_heading < -M_PI) nav_state.desired_heading += 2.0f * M_PI;
        
        // 12. Compute desired turn rate (Pure Pursuit)
        if (fabsf(nav_state.xtrack_error_mag) > 0.01f) {
            float R = (nav_state.look_ahead_distance * nav_state.look_ahead_distance) / 
                     (2.0f * nav_state.xtrack_error_mag);
            nav_state.desired_turn_rate = ground_speed / R;
        } else {
            nav_state.desired_turn_rate = 0.0f;
        }
        
        // 13. Check if waypoint reached
        float dist_to_wp = sqrtf(vec_to_wp_north*vec_to_wp_north + 
                                vec_to_wp_east*vec_to_wp_east);
        float alt_error = fabsf(pos_down - (-wp_current->alt)); // pos_down is negative
        
        if (dist_to_wp <= wp_current->acceptance_radius && 
            alt_error <= 5.0f) {
            nav_state.wp_reached = 1;
        } else {
            nav_state.wp_reached = 0;
        }
        
        // 14. Convert to wheel forces for skid-steer
        const float mass = 20.0f; // kg
        const float inertia = 5.0f; // kg·m²
        const float track_width = 0.5f; // m
        
        // For auto mode, use desired turn rate to compute differential force
        float desired_yaw_accel = nav_state.desired_turn_rate / dt; // Simplified
        
        // Throttle from RC or mission parameter
        uint32_t throttle_pulse = TIM1->CCR3;
        float throttle = (throttle_pulse - 1000.0f) / 1000.0f;
        float force_sum = throttle * 100.0f; // 100N total max force
        
        float force_diff = (2.0f * inertia * desired_yaw_accel) / track_width;
        
        float left_force = 0.5f * (force_sum - force_diff);
        float right_force = 0.5f * (force_sum + force_diff);
        
        // 15. Convert to PWM and output
        const float max_force = 50.0f; // N per wheel
        uint16_t pwm_left = 1500 + (left_force / max_force) * 500.0f;
        uint16_t pwm_right = 1500 + (right_force / max_force) * 500.0f;
        
        pwm_left = (pwm_left < 1100) ? 1100 : (pwm_left > 1900) ? 1900 : pwm_left;
        pwm_right = (pwm_right < 1100) ? 1100 : (pwm_right > 1900) ? 1900 : pwm_right;
        
        TIM1->CCR1 = pwm_left;
        TIM1->CCR2 = pwm_right;
    }
    
private:
    NavState nav_state __attribute__((section(".dtcm")));
    L1Gains l1_gains __attribute__((section(".dtcm")));
};
```

### MAVLink Mission Item Parsing (commands.cpp)
The `MissionCommandParser` handles MAVLink mission item reception, validation, and execution state management.

```cpp
// commands.cpp - MAVLink Mission Command Parser
struct __attribute__((packed, aligned(4))) MavMissionItem {
    uint16_t command __attribute__((section(".dtcm")));     // 0x20002200: MAV_CMD
    uint8_t frame;          // 0x20002202: MAV_FRAME
    uint8_t current;        // 0x20002203: Current item
    float param1;           // 0x20002204
    float param2;           // 0x20002208
    float param3;           // 0x2000220C
    float param4;           // 0x20002210
    float x;                // 0x20002214: Latitude/ X
    float y;                // 0x20002218: Longitude/ Y
    float z;                // 0x2000221C: Altitude/ Z
};

struct __attribute__((packed, aligned(4))) ExecutionContext {
    uint8_t state __attribute__((section(".dtcm")));        // 0x20002300: State machine state
    uint32_t start_time_ms; // 0x20002304: Command start time
    uint32_t hold_time_ms;  // 0x20002308: Hold time from param1
    float acceptance_radius; // 0x2000230C: From param2
    float pass_radius;      // 0x20002310: From param3
    float desired_yaw;      // 0x20002314: From param4 (radians)
};

class MissionCommandParser {
public:
    __attribute__((section(".itcm")))
    void process_mavlink_message(uint8_t* buffer, uint16_t len) {
        // MAVLink message buffer in DTCM at 0x2000C000
        volatile uint8_t* mavlink_rx_buffer = (volatile uint8_t*)0x2000C000;
        
        // Copy from DMA buffer
        for (int i = 0; i < len; i++) {
            mavlink_rx_buffer[i] = buffer[i];
        }
        
        // Parse MAVLink MISSION_ITEM message (ID #39)
        if (mavlink_rx_buffer[5] == 39) { // message ID at offset 5
            parse_mission_item(mavlink_rx_buffer);
        }
    }
    
    __attribute__((section(".itcm")))
    void update_mission_execution(float dt) {
        switch (exec_ctx.state) {
            case STATE_IDLE:
                // Wait for mission item
                break;
                
            case STATE_PARSING:
                // Validate mission item
                if (validate_mission_item(&current_item)) {
                    exec_ctx.state = STATE_EXECUTING;
                    exec_ctx.start_time_ms = HAL_GetTick();
                    exec_ctx.hold_time_ms = (uint32_t)(current_item.param1 * 1000.0f);
                    exec_ctx.acceptance_radius = current_item.param2;
                    exec_ctx.pass_radius = current_item.param3;
                    exec_ctx.desired_yaw = current_item.param4 * M_PI / 180.0f; // deg to rad
                    
                    // Load waypoint into navigation system
                    WaypointData* wp = (WaypointData*)0x20002000;
                    wp->lat = current_item.x;
                    wp->lon = current_item.y;
                    wp->alt = current_item.z;
                    wp->acceptance_radius = exec_ctx.acceptance_radius;
                    wp->command = current_item.command;
                    wp->frame = current_item.frame;
                    wp->current = 1;
                } else {
                    exec_ctx.state = STATE_IDLE;
                    send_mission_ack(MAV_MISSION_ERROR);
                }
                break;
                
            case STATE_EXECUTING:
                // Check completion conditions based on command type
                if (current_item.command == MAV_CMD_NAV_WAYPOINT) {
                    // Check if waypoint reached via nav_state
                    NavState* nav = (NavState*)0x20002100;
                    if (nav->wp_reached) {
                        exec_ctx.state = STATE_COMPLETING;
                    }
                }
                // Add other command types: MAV_CMD_NAV_LOITER, etc.
                break;
                
            case STATE_COMPLETING:
                // Wait for hold time if specified
                if (HAL_GetTick() - exec_ctx.start_time_ms >= exec_ctx.hold_time_ms) {
                    exec_ctx.state = STATE_NEXT;
                }
                break;
                
            case STATE_NEXT:
                // Request next mission item
                send_mission_request_next();
                exec_ctx.state = STATE_IDLE;
                break;
        }
    }
    
private:
    MavMissionItem current_item __attribute__((section(".dtcm")));
    ExecutionContext exec_ctx __attribute__((section(".dtcm")));
    
    bool validate_mission_item(MavMissionItem* item) {
        // Check command is in valid set
        if (!(item->command == MAV_CMD_NAV_WAYPOINT ||
              item->command == MAV_CMD_NAV_LOITER_UNLIM ||
              item->command == MAV_CMD_NAV_LOITER_TURNS ||
              item->command == MAV_CMD_NAV_RETURN_TO_LAUNCH)) {
            return false;
        }
        
        // Check frame is supported
        if (!(item->frame == MAV_FRAME_GLOBAL ||
              item->frame == MAV_FRAME_GLOBAL_RELATIVE_ALT ||
              item->frame == MAV_FRAME_LOCAL_NED)) {
            return false;
        }
        
        // Check parameter ranges
        if (item->param1 < 0.0f || item->param1 > 3600.0f) return false; // hold time 0-1 hour
        if (item->param2 < 0.0f || item->param2 > 1000.0f) return false; // acceptance radius
        if (item->param3 < -1.0f || item->param3 > 1000.0f) return false; // pass radius
        
        // Check coordinate limits (simplified)
        if (item->x < -90.0f || item->x > 90.0f) return false; // latitude
        if (item->y < -180.0f || item->y > 180.0f) return false; // longitude
        if (item->z < -1000.0f || item->z > 10000.0f) return false; // altitude
        
        return true;
    }
    
    void send_mission_ack(uint8_t result) {
        // Send MAVLink MISSION_ACK message
        uint8_t tx_buffer[20];
        tx_buffer[0] = 0xFE; // STX
        tx_buffer[1] = 17;   // Length
        tx_buffer[2] = 0;    // Sequence
        tx_buffer[3] = 1;    // System ID
        tx_buffer[4] = 1;    // Component ID
        tx_buffer[5] = 47;   // MISSION_ACK ID
        tx_buffer[6] = result; // Result
        tx_buffer[7] = current_item.command & 0xFF;
        tx_buffer[8] = (current_item.command >> 8) & 0xFF;
        
        // Send via UART DMA
        DMA1_Stream5->CR &= ~DMA_SxCR_EN; // Disable DMA
        memcpy((void*)0x2000C800, tx_buffer, 20); // Copy to TX buffer
        DMA1_Stream5->NDTR = 20; // Set number of bytes
        DMA1_Stream5->CR |= DMA_SxCR_EN; // Enable DMA
    }
    
    void send_mission_request_next() {
        // Send MAVLink MISSION_REQUEST message for next item
        uint8_t tx_buffer[20];
        tx_buffer[0] = 0xFE; // STX
        tx_buffer[1] = 4;    // Length
        tx_buffer[5] = 40;   // MISSION_REQUEST ID
        
        // Send via UART DMA
        DMA1_Stream5->CR &= ~DMA_SxCR_EN;
        memcpy((void*)0x2000C800, tx_buffer, 20);
        DMA1_Stream5->NDTR = 20;
        DMA1_Stream5->CR |= DMA_SxCR_EN;
    }
};
```

### Off-Board Guided Velocity Vectors (mode_guided.cpp)
The `GuidedModeController` implements velocity and position control for off-board commanded trajectories.

```cpp
// mode_guided.cpp - Guided Mode Controller
struct __attribute__((packed, aligned(4))) TrajectoryState {
    float position[3] __attribute__((section(".dtcm")));    // 0x20002400: [x, y, z]
    float velocity[3];          // 0x2000240C: [vx, vy, vz]
    float acceleration[3];      // 0x20002418: [ax, ay, az]
    float start_pos[3];         // 0x20002424: Trajectory start
    float end_pos[3];           // 0x20002430: Trajectory end
    float start_vel[3];         // 0x2000243C: Start velocity
    float end_vel[3];           // 0x20002448: End velocity
    float traj_coeffs[4][3];    // 0x20002454: Cubic coefficients [a0-a3][xyz]
    float traj_duration;        // 0x20002484: T (seconds)
    float traj_start_time;      // 0x20002488: Start time
    uint8_t traj_active;        // 0x2000248C: Trajectory active flag
};

class GuidedModeController {
public:
    __attribute__((section(".itcm")))
    void update_guided_navigation(float dt) {
        if (traj_state.traj_active) {
            // 1. Update trajectory time
            float traj_time = (float)(HAL_GetTick() - traj_state.traj_start_time) / 1000.0f;
            
            if (traj_time >= traj_state.traj_duration) {
                // Trajectory complete
                traj_state.traj_active = 0;
                
                // Check completion tolerances
                volatile float* ekf_state = (volatile float*)0x2000A000;
                float pos_error = sqrtf(powf(ekf_state[0] - traj_state.end_pos[0], 2) +
                                       powf(ekf_state[1] - traj_state.end_pos[1], 2));
                float vel_error = sqrtf(powf(ekf_state[3] - traj_state.end_vel[0], 2) +
                                       powf(ekf_state[4] - traj_state.end_vel[1], 2));
                
                if (pos_error < 0.1f && vel_error < 0.05f) {
                    // Successfully reached target
                    send_guided_complete();
                }
                return;
            }
            
            // 2. Compute desired position, velocity, acceleration from cubic polynomial
            for (int axis = 0; axis < 3; axis++) {
                float t = traj_time;
                float t2 = t * t;
                float t3 = t2 * t;
                
                // p(t) = a0 + a1*t + a2*t² + a3*t³
                traj_state.position[axis] = traj_state.traj_coeffs[0][axis] +
                                           traj_state.traj_coeffs[1][axis] * t +
                                           traj_state.traj_coeffs[2][axis] * t2 +
                                           traj_state.traj_coeffs[3][axis] * t3;
                
                // v(t) = a1 + 2*a2*t + 3*a3*t²
                traj_state.velocity[axis] = traj_state.traj_coeffs[1][axis] +
                                           2.0f * traj_state.traj_coeffs[2][axis] * t +
                                           3.0f * traj_state.traj_coeffs[3][axis] * t2;
                
                // a(t) = 2*a2 + 6*a3*t
                traj_state.acceleration[axis] = 2.0f * traj_state.traj_coeffs[2][axis] +
                                               6.0f * traj_state.traj_coeffs[3][axis] * t;
            }
            
            // 3. Compute control using PID position controller
            volatile float* ekf_state = (volatile float*)0x2000A000;
            
            // Position error
            float pos_error_x = traj_state.position[0] - ekf_state[0];
            float pos_error_y = traj_state.position[1] - ekf_state[1];
            
            // Velocity error
            float vel_error_x = traj_state.velocity[0] - ekf_state[3];
            float vel_error_y = traj_state.velocity[1] - ekf_state[4];
            
            // PID gains
            const float Kp_pos = 1.5f;
            const float Ki_pos = 0.1f;
            const float Kd_pos = 0.5f;
            
            // Update integral terms
            static float integral_x = 0.0f, integral_y = 0.0f;
            integral_x += pos_error_x * dt;
            integral_y += pos_error_y * dt;
            
            // Anti-windup
            const float max_integral = 5.0f / Ki_pos;
            integral_x = (integral_x > max_integral) ? max_integral : 
                        (integral_x < -max_integral) ? -max_integral : integral_x;
            integral_y = (integral_y > max_integral) ? max_integral : 
                        (integral_y < -max_integral) ? -max_integral : integral_y;
            
            // PID control law: a_cmd = Kp*e_pos + Ki*∫e_pos + Kd*e_vel
            float accel_cmd_x = Kp_pos * pos_error_x + 
                               Ki_pos * integral_x + 
                               Kd_pos * vel_error_x;
            float accel_cmd_y = Kp_pos * pos_error_y + 
                               Ki_pos * integral_y + 
                               Kd_pos * vel_error_y;
            
            // Add feedforward acceleration from trajectory
            accel_cmd_x += traj_state.acceleration[0];
            accel_cmd_y += traj_state.acceleration[1];
            
            // 4. Convert to wheel forces for skid-steer
            const float mass = 20.0f; // kg
            const float inertia = 5.0f; // kg·m²
            const float track_width = 0.5f; // m
            
            // For guided mode, assume desired yaw rate = 0 (maintain current heading)
            float desired_yaw_accel = 0.0f;
            
            float force_sum_x = mass * accel_cmd_x;
            float force_sum_y = mass * accel_cmd_y; // Limited for skid-steer
            
            // Skid-steer can't directly produce lateral force, convert to yaw torque
            float lateral_force_limit = 0.3f * force_sum_x; // 30% of longitudinal
            if (force_sum_y > lateral_force_limit) force_sum_y = lateral_force_limit;
            if (force_sum_y < -lateral_force_limit) force_sum_y = -lateral_force_limit;
            
            // Convert lateral force to differential torque
            float torque_from_lateral = force_sum_y * (track_width / 2.0f);
            float torque_total = inertia * desired_yaw_accel + torque_from_lateral;
            
            float force_diff = (2.0f * torque_total) / track_width;
            float force_total = sqrtf(force_sum_x*force_sum_x + force_sum_y*force_sum_y);
            
            // Compute wheel forces
            float left_force = 0.5f * (force_total - force_diff);
            float right_force = 0.5f * (force_total + force_diff);
            
            // 5. Convert to PWM and output
            const float max_force = 50.0f; // N per wheel
            uint16_t pwm_left = 1500 + (left_force / max_force) * 500.0f;
            uint16_t pwm_right = 1500 + (right_force / max_force) * 500.0f;
            
            pwm_left = (pwm_left < 1100) ? 1100 : (pwm_left > 1900) ? 1900 : pwm_left;
            pwm_right = (pwm_right < 1100) ? 1100 : (pwm_right > 1900) ? 1900 : pwm_right;
            
            TIM1->CCR1 = pwm_left;
            TIM1->CCR2 = pwm_right;
        }
    }
    
    __attribute__((section(".itcm")))
    void generate_trajectory(float start_pos[3], float end_pos[3], 
                            float start_vel[3], float end_vel[3], 
                            float duration) {
        // Store trajectory parameters
        memcpy(traj_state.start_pos, start_pos, 3 * sizeof(float));
        memcpy(traj_state.end_pos, end_pos, 3 * sizeof(float));
        memcpy(traj_state.start_vel, start_vel, 3 * sizeof(float));
        memcpy(traj_state.end_vel, end_vel, 3 * sizeof(float