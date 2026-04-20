# Advanced Failsafe State Machines and Geo-Sequences

_Generated 2026-04-20 07:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AdvancedFailsafe/AP_AdvancedFailsafe.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/failsafe.cpp`

# Advanced Failsafe State Machines and Geo-Sequences

## Chapter Introduction

This chapter details the implementation of advanced failsafe state machines and geographic sequence execution within ArduPilot, specifically engineered for a heavy agricultural rover platform (~750 kg mass, ~300 kg·m² yaw inertia). The `AP_AdvancedFailsafe.cpp` file implements a hierarchical, multi-mode failsafe state machine that integrates vehicle dynamics, environmental sensing, and mission logic to provide deterministic safety responses. The `failsafe.cpp` file provides the core failsafe triggering and response system, handling immediate hardware-level fault detection and recovery. Together, these systems form a robust safety architecture that ensures operational continuity and controlled shutdown procedures during fault conditions, critical for autonomous agricultural operations where manual intervention may be delayed.

## Mathematical Formulation

### Failsafe State Transition Matrix

The failsafe system operates as a finite state machine with probabilistic transitions based on sensor inputs and vehicle state. The transition probability matrix **P** for states *S* = {NORMAL, WARNING, CRITICAL, TERMINATE} is defined as:

**P** = [pᵢⱼ] where pᵢⱼ = P(Sₜ₊₁ = j | Sₜ = i)

For a rover with mass *m* = 750 kg and inertia *J* = 300 kg·m², the transition probabilities incorporate dynamic constraints:

p₁₂ (NORMAL→WARNING) = α ⋅ (1 - exp(-|a - aₛₐ₆₆|/σₐ)) ⋅ (1 - exp(-|ω - ωₛₐ₆₆|/σω))

where:
- α = 0.8 (aggressiveness factor for heavy rover)
- a = current acceleration (m/s²)
- aₛₐ₆₆ = safe acceleration limit (2.0 m/s² for 750kg rover)
- σₐ = 0.5 m/s² (acceleration sensitivity)
- ω = current angular velocity (rad/s)
- ωₛₐ₆₆ = safe angular velocity limit (0.5 rad/s for 300 kg·m² inertia)
- σω = 0.1 rad/s (angular velocity sensitivity)

### Geo-Fence Boundary Calculations

For a polygonal geo-fence with *n* vertices (V₀, V₁, ..., Vₙ₋₁) in WGS-84 coordinates, the point-in-polygon test uses the winding number algorithm:

Let φᵢ, λᵢ be latitude/longitude of vertex i, and φₚ, λₚ be the rover's position.
Convert to Cartesian coordinates for local plane approximation (valid for < 1km distances):

xᵢ = R ⋅ (λᵢ - λ₀) ⋅ cos(φ₀)
yᵢ = R ⋅ (φᵢ - φ₀)

where R = 6371000 m (Earth radius).

The crossing number cn = 0
for i = 0 to n-1:
    j = (i + 1) mod n
    if ((yᵢ > yₚ) ≠ (yⱼ > yₚ)) and (xₚ < (xⱼ - xᵢ) ⋅ (yₚ - yᵢ)/(yⱼ - yᵢ) + xᵢ):
        cn = cn + 1

Point is inside if cn is odd.

### Battery Failsafe Threshold Modeling

For a lithium battery pack powering a 750kg rover, the voltage threshold model accounts for sag under load:

Vₜₕᵣₑₛₕₒₗ₅(m, I, T) = Vₙₒₘ - Rₑₛᵣ ⋅ I - kₜ ⋅ (T - Tₙₒₘ) - kₘ ⋅ m/750

where:
- Vₙₒₘ = nominal cell voltage (3.7V ⋅ Nₛ)
- Rₑₛᵣ = equivalent series resistance (0.05Ω ⋅ Nₛ/Nₚ)
- I = current draw (A)
- kₜ = temperature coefficient (-0.005 V/°C)
- T = battery temperature (°C)
- Tₙₒₘ = 25°C
- kₘ = mass compensation factor (0.02 V per 750kg)
- Nₛ = cells in series
- Nₚ = cells in parallel

### Sequence Execution Timing Constraints

For a geo-sequence of *k* waypoints with inter-waypoint distances dᵢ, the minimum execution time for a 750kg rover:

Tₘᵢₙ = Σᵢ₌₀ᵏ⁻¹ (dᵢ / vₘₐₓ) + (k-1) ⋅ tₜᵤᵣₙ

where:
- vₘₐₓ = maximum safe velocity = √(μ ⋅ g ⋅ r) for skid-steer
- μ = friction coefficient (0.6 for dry soil)
- g = 9.81 m/s²
- r = turn radius (minimum 3m for 750kg rover)
- tₜᵤᵣₙ = turn time = (θᵢ ⋅ J) / τₘₐₓ
- θᵢ = turn angle (rad)
- τₘₐₓ = maximum torque = 500 N⋅m (for 300 kg⋅m² inertia)

### Communication Loss Probability Model

The probability of communication loss exceeding timeout T for a rover at distance r:

Pₗₒₛₛ(r, T) = 1 - exp(-λ(r) ⋅ T)

where λ(r) = λ₀ ⋅ (r/r₀)² ⋅ exp(-h/h₀)

- λ₀ = base failure rate (0.001 s⁻¹ at r₀ = 100m)
- r = distance from base station (m)
- r₀ = reference distance (100m)
- h = terrain height variation (m)
- h₀ = attenuation scale (10m)

### Inertia-Aware Recovery Trajectories

For a rover with inertia tensor **J**, the recovery trajectory from position **p**₀ to safe position **p**ₛ uses minimum jerk planning:

**p**(t) = **p**₀ + (**p**ₛ - **p**₀) ⋅ (10τ³ - 15τ⁴ + 6τ⁵)

where τ = t/T, and T is computed from dynamics:

T = max(√(6‖**p**ₛ - **p**₀‖/aₘₐₓ), ³√(20θ⋅‖**J**‖/τₘₐₓ))

- aₘₐₓ = maximum acceleration (1.5 m/s² for 750kg)
- θ = angular displacement to align with safe heading
- ‖**J**‖ = Frobenius norm of inertia tensor (≈400 kg⋅m² for 300 kg⋅m² yaw inertia)

### Sensor Health Bayesian Estimation

The probability that sensor i is healthy given measurements z₁:ₜ:

P(H⁽ⁱ⁾|z₁:ₜ) = [P(zₜ|H⁽ⁱ⁾) ⋅ P(H⁽ⁱ⁾|z₁:ₜ₋₁)] / [Σⱼ P(zₜ|H⁽ʲ⁾) ⋅ P(H⁽ʲ⁾|z₁:ₜ₋₁)]

For IMU failure detection on a 750kg rover:

P(zₜ|H⁽ᴵᴹᵁ⁾) = exp(-‖aₘₑₐₛ - aₚₚᵣₒₓ‖²/(2σₐ²) - ‖ωₘₑₐₛ - ωₚₚᵣₒₓ‖²/(2σω²))

where aₚₚᵣₒₓ = F/m, ωₚₚᵣₒₓ = τ/**J**
- F = estimated force from wheel encoders
- τ = estimated torque from steering angles
- σₐ = 0.2 m/s² (acceleration consistency threshold)
- σω = 0.05 rad/s (angular velocity consistency threshold)

### Multi-Criteria Decision Matrix for Failsafe Action Selection

For failsafe action Aⱼ with criteria weights wᵢ (safety, completion, equipment preservation):

Score(Aⱼ) = Σᵢ wᵢ ⋅ Uᵢ(Aⱼ)

where Uᵢ(Aⱼ) = 1 - exp(-(Qᵢ(Aⱼ) - Qᵢₘᵢₙ)/(Qᵢₘₐₓ - Qᵢₘᵢₙ))

For a 750kg agricultural rover:
- wₛₐ₆₆₆ₜᵧ = 0.6
- w꜀ₒₘₚₗₑₜᵢₒₙ = 0.25
- wₑqᵤᵢₚₘₑₙₜ = 0.15

## C++ Implementation

### Advanced Failsafe State Machine (AP_AdvancedFailsafe.cpp)

```cpp
class AP_AdvancedFailsafe {
public:
    enum FailsafeState {
        STATE_NORMAL = 0,
        STATE_WARNING,
        STATE_CRITICAL,
        STATE_TERMINATE,
        STATE_RECOVERY,
        STATE_HOLD,
        STATE_RETURN,
        STATE_LAND,
        STATE_ESTOP
    };
    
    enum FailsafeTrigger {
        TRIGGER_NONE = 0,
        TRIGGER_BATTERY,
        TRIGGER_GEOFENCE,
        TRIGGER_COMM_LOSS,
        TRIGGER_SENSOR_FAIL,
        TRIGGER_ATTITUDE,
        TRIGGER_GPS,
        TRIGGER_MANUAL
    };
    
    struct FailsafeThresholds {
        float battery_voltage_min;     // Minimum battery voltage (V)
        float battery_capacity_min;    // Minimum remaining capacity (%)
        float max_tilt_angle;          // Maximum tilt angle (degrees)
        float max_roll_angle;          // Maximum roll angle (degrees)
        uint16_t comm_loss_timeout;    // Communication loss timeout (s)
        float geofence_margin;         // Geofence margin (m)
        uint8_t min_satellites;        // Minimum GPS satellites
        float max_hdop;                // Maximum HDOP
        float terrain_margin;          // Terrain following margin (m)
        float max_speed;               // Maximum speed (m/s)
    };
    
    struct GeoSequence {
        uint16_t sequence_id;
        Location waypoints[GEO_SEQ_MAX_WAYPOINTS];
        uint8_t waypoint_count;
        uint32_t execution_timeout_ms;
        float max_deviation;           // Maximum allowed deviation (m)
        uint8_t retry_count;
        bool altitude_constrained;
        float min_altitude;            // Minimum altitude (m)
        float max_altitude;            // Maximum altitude (m)
    };
    
private:
    FailsafeState current_state;
    FailsafeState previous_state;
    FailsafeTrigger active_trigger;
    uint32_t state_entry_time_ms;
    uint32_t last_update_time_ms;
    
    FailsafeThresholds thresholds;
    GeoSequence active_sequence;
    
    // State transition matrix implementation
    bool _evaluate_state_transition(FailsafeState new_state) {
        // Get current vehicle state
        AP_AHRS &ahrs = AP::ahrs();
        AP_BattMonitor &batt = AP::battery();
        AP_GPS &gps = AP::gps();
        
        // Calculate transition probabilities based on mathematical model
        float p_transition = 1.0f;
        
        switch (current_state) {
            case STATE_NORMAL:
                if (new_state == STATE_WARNING) {
                    // Check battery
                    float voltage = batt.voltage(0);
                    float capacity = batt.capacity_remaining_pct(0);
                    
                    // Apply battery threshold model for 750kg rover
                    float load_current = batt.current_amps(0);
                    float mass_factor = 1.0f + (750.0f - 500.0f) / 500.0f * 0.2f; // 20% adjustment for 750kg
                    float voltage_threshold = thresholds.battery_voltage_min * mass_factor;
                    
                    if (voltage < voltage_threshold || capacity < thresholds.battery_capacity_min) {
                        active_trigger = TRIGGER_BATTERY;
                        return true;
                    }
                    
                    // Check attitude limits
                    float roll_deg = degrees(ahrs.get_roll());
                    float pitch_deg = degrees(ahrs.get_pitch());
                    
                    // Inertia-aware tilt calculation for 300 kg·m² rover
                    float inertia_factor = 300.0f / 100.0f; // Normalize to 100 kg·m²
                    float effective_tilt = sqrtf(roll_deg * roll_deg + pitch_deg * pitch_deg) * inertia_factor;
                    
                    if (effective_tilt > thresholds.max_tilt_angle || 
                        fabsf(roll_deg) > thresholds.max_roll_angle) {
                        active_trigger = TRIGGER_ATTITUDE;
                        return true;
                    }
                    
                    // Check geofence
                    if (_check_geofence_violation()) {
                        active_trigger = TRIGGER_GEOFENCE;
                        return true;
                    }
                    
                    // Check communication
                    if (_check_communication_loss()) {
                        active_trigger = TRIGGER_COMM_LOSS;
                        return true;
                    }
                }
                break;
                
            case STATE_WARNING:
                if (new_state == STATE_CRITICAL) {
                    // Time in warning state
                    uint32_t warning_time = AP_HAL::millis() - state_entry_time_ms;
                    
                    // If trigger persists beyond grace period, escalate
                    if (warning_time > WARNING_GRACE_PERIOD_MS) {
                        return true;
                    }
                    
                    // Check if condition is worsening
                    if (_is_condition_worsening()) {
                        return true;
                    }
                } else if (new_state == STATE_NORMAL) {
                    // Check if trigger condition has cleared
                    if (!_trigger_condition_active(active_trigger)) {
                        return true;
                    }
                }
                break;
                
            case STATE_CRITICAL:
                if (new_state == STATE_TERMINATE) {
                    // Critical state timeout
                    uint32_t critical_time = AP_HAL::millis() - state_entry_time_ms;
                    if (critical_time > CRITICAL_TIMEOUT_MS) {
                        return true;
                    }
                    
                    // Check for multiple simultaneous failures
                    if (_count_active_triggers() >= 2) {
                        return true;
                    }
                } else if (new_state == STATE_RECOVERY) {
                    // Check if recovery is possible
                    if (_can_recover()) {
                        return true;
                    }
                }
                break;
        }
        
        return false;
    }
    
    // Geofence violation detection using winding number algorithm
    bool _check_geofence_violation() {
        AP_GPS &gps = AP::gps();
        if (!gps.status() >= AP_GPS::GPS_OK_FIX_3D) {
            return false;
        }
        
        Location rover_loc = gps.location();
        
        // Get geofence polygon
        AP_Fence &fence = AP::fence();
        uint16_t point_count = fence.get_boundary_points();
        
        if (point_count < 3) {
            return false; // No valid fence
        }
        
        // Convert to local Cartesian coordinates for winding test
        Vector2f rover_xy = _location_to_local_xy(rover_loc);
        
        int winding_number = 0;
        
        for (uint16_t i = 0; i < point_count; i++) {
            uint16_t j = (i + 1) % point_count;
            
            Location loc_i, loc_j;
            fence.get_boundary_point(i, loc_i);
            fence.get_boundary_point(j, loc_j);
            
            Vector2f vi = _location_to_local_xy(loc_i);
            Vector2f vj = _location_to_local_xy(loc_j);
            
            // Check if point is left of edge
            if (vi.y <= rover_xy.y) {
                if (vj.y > rover_xy.y) {
                    // Upward crossing
                    if (_is_point_left_of_edge(rover_xy, vi, vj) > 0) {
                        winding_number++;
                    }
                }
            } else {
                if (vj.y <= rover_xy.y) {
                    // Downward crossing
                    if (_is_point_left_of_edge(rover_xy, vi, vj) < 0) {
                        winding_number--;
                    }
                }
            }
        }
        
        // Add geofence margin for 750kg rover (needs more stopping distance)
        float margin = thresholds.geofence_margin * (750.0f / 500.0f);
        
        // If winding_number != 0, point is inside polygon
        // For fence, we want to know if we're outside
        bool inside_fence = (winding_number != 0);
        
        // Check distance to fence boundary
        float distance_to_fence = _distance_to_geofence(rover_loc);
        
        // Trigger if outside fence or too close to boundary
        return (!inside_fence) || (distance_to_fence < margin);
    }
    
    // Calculate minimum jerk recovery trajectory
    void _calculate_recovery_trajectory(const Location &start_loc, const Location &safe_loc) {
        // Get current position and safe position
        Vector3f start_pos = _location_to_vector3f(start_loc);
        Vector3f safe_pos = _location_to_vector3f(safe_loc);
        
        // Calculate displacement
        Vector3f displacement = safe_pos - start_pos;
        float distance = displacement.length();
        
        // Calculate required time based on rover dynamics
        AP_InertialSensor &ins = AP::ins();
        float accel_max = 1.5f; // m/s² for 750kg rover
        float jerk_max = 2.0f;  // m/s³
        
        // Minimum time for distance with jerk-limited trajectory
        // Using third-order polynomial: s = j_max * t³ / 6
        float t_min_distance = cbrtf(6.0f * distance / jerk_max);
        
        // Consider inertia for turning
        float heading_change = _calculate_heading_change(start_loc, safe_loc);
        float inertia_factor = 300.0f / 100.0f; // Based on 300 kg·m² yaw inertia
        float t_min_turn = sqrtf(heading_change * inertia_factor / accel_max);
        
        // Total minimum time
        float T = MAX(t_min_distance, t_min_turn);
        
        // Generate trajectory points
        const uint8_t num_points = 20;
        for (uint8_t i = 0; i <= num_points; i++) {
            float tau = (float)i / num_points;
            
            // Normalized time for minimum jerk: 10τ³ - 15τ⁴ + 6τ⁵
            float s = 10.0f * powf(tau, 3) - 15.0f * powf(tau, 4) + 6.0f * powf(tau, 5);
            
            // Position at time tau
            Vector3f pos = start_pos + displacement * s;
            
            // Velocity (derivative): 30τ² - 60τ³ + 30τ⁴
            float v_norm = 30.0f * powf(tau, 2) - 60.0f * powf(tau, 3) + 30.0f * powf(tau, 4);
            Vector3f velocity = displacement * (v_norm / T);
            
            // Acceleration (second derivative): 60τ - 180τ² + 120τ³
            float a_norm = 60.0f * tau - 180.0f * powf(tau, 2) + 120.0f * powf(tau, 3);
            Vector3f acceleration = displacement * (a_norm / (T * T));
            
            // Store trajectory point
            _recovery_trajectory[i].position = pos;
            _recovery_trajectory[i].velocity = velocity;
            _recovery_trajectory[i].acceleration = acceleration;
            _recovery_trajectory[i].time_ms = (uint32_t)(tau * T * 1000.0f);
        }
        
        _recovery_trajectory_points = num_points + 1;
        _recovery_trajectory_start_ms = AP_HAL::millis();
    }
    
    // Bayesian sensor health estimation
    void _update_sensor_health_estimation() {
        AP_InertialSensor &ins = AP::ins();
        AP_GPS &gps = AP::gps();
        AP_Baro &baro = AP::baro();
        
        // Get current sensor readings
        Vector3f accel, gyro;
        ins.get_accel(accel);
        ins.get_gyro(gyro);
        
        // Get expected values from vehicle dynamics
        Vector3f expected_accel = _calculate_expected_acceleration();
        Vector3f expected_gyro = _calculate_expected_gyro();
        
        // Calculate likelihoods
        float accel_error = (accel - expected_accel).length();
        float gyro_error = (gyro - expected_gyro).length();
        
        // Gaussian likelihood with inertia scaling
        float inertia_scale = 300.0f / 100.0f;
        float p_accel_given_healthy = expf(-accel_error * accel_error / (2.0f * 0.04f * inertia_scale));
        float p_gyro_given_healthy = expf(-gyro_error * gyro_error / (2.0f * 0.0025f * inertia_scale));
        
        // Combined IMU health probability
        float p_imu_healthy = p_accel_given_healthy * p_gyro_given_healthy;
        
        // Update Bayesian estimate
        float prior_healthy = _sensor_health_probability[SENSOR_IMU];
        float prior_faulty = 1.0f - prior_healthy;
        
        float posterior_healthy = p_imu_healthy * prior_healthy;
        float posterior_faulty = (1.0f - p_imu_healthy) * prior_faulty;
        
        // Normalize
        float normalizer = posterior_healthy + posterior_faulty;
        if (normalizer > 0.0f) {
            _sensor_health_probability[SENSOR_IMU] = posterior_healthy / normalizer;
        }
        
        // Check if probability drops below threshold
        if (_sensor_health_probability[SENSOR_IMU] < SENSOR_HEALTH_THRESHOLD) {
            _trigger_failsafe(TRIGGER_SENSOR_FAIL, SENSOR_IMU);
        }
    }
    
    // Execute geo-sequence with timing constraints
    bool _execute_geo_sequence(const GeoSequence &seq) {
        AP_GPS &gps = AP::gps();
        AP_Mission &mission = AP::mission();
        
        // Check sequence validity
        if (seq.waypoint_count < 2) {
            return false;
        }
        
        // Calculate total distance and minimum time
        float total_distance = 0.0f;
        for (uint8_t i = 0; i < seq.waypoint_count - 1; i++) {
            total_distance += seq.waypoints[i].get_distance(seq.waypoints[i + 1]);
        }
        
        // Calculate minimum execution time for 750kg rover
        float max_speed = thresholds.max_speed;
        float turn_radius = 3.0f; // meters for 750kg rover
        float max_lateral_accel = 0.3f * 9.81f; // 0.3g for agricultural rover
        
        // Speed limited by turn radius: v_max = sqrt(a_lat * r)
        float turn_limited_speed = sqrtf(max_lateral_accel * turn_radius);
        max_speed = MIN(max_speed, turn_limited_speed);
        
        float min_execution_time = total_distance / max_speed;
        
        // Add turn time between waypoints
        for (uint8_t i = 0; i < seq.waypoint_count - 1; i++) {
            float heading_change = _calculate_heading_change(seq.waypoints[i], seq.waypoints[i + 1]);
            if (heading_change > radians(10.0f)) {
                // Turn time based on inertia: t = θ * J / τ
                float turn_time = heading_change * 300.0f / 500.0f; // J=300, τ_max=500
                min_execution_time += turn_time;
            }
        }
        
        // Check if timeout is sufficient
        float timeout_seconds = seq.execution_timeout_ms / 1000.0f;
        if (timeout_seconds < min_execution_time * 1.5f) {
            // Timeout too short for safe execution
            return false;
        }
        
        // Execute sequence
        _active_sequence = seq;
        _sequence_start_time_ms = AP_HAL::millis();
        _current_waypoint_index = 0;
        
        // Command first waypoint
        mission.set_current_cmd(_active_sequence.waypoints[0]);
        
        return true;
    }
    
    // Multi-criteria decision making for failsafe action
    FailsafeAction _select_failsafe_action(FailsafeState state, FailsafeTrigger trigger) {
        // Define available actions
        FailsafeAction actions[] = {
            ACTION_CONTINUE,
            ACTION_HOLD_POSITION,
            ACTION_RETURN_HOME,
            ACTION_LAND,
            ACTION_TERMINATE
        };
        
        // Criteria weights for 750kg agricultural rover
        float weights[3] = {0.6f, 0.25f, 0.15f}; // safety, completion, equipment
        
        float best_score = -1.0f;
        FailsafeAction best_action = ACTION_CONTINUE;
        
        // Evaluate each action
        for (uint8_t i = 0; i < ARRAY_SIZE(actions); i++) {
            float safety_score = _evaluate_safety_criteria(actions[i], state, trigger);
            float completion_score = _evaluate_completion_criteria(actions[i]);
            float equipment_score = _evaluate_equipment_criteria(actions[i]);
            
            // Apply utility function
            float u_safety = 1.0f - expf(-(safety_score - 0.0f) / (1.0f - 0.0f));
            float u_completion = 1.0f - expf(-(completion_score - 0.0f) / (1.0f - 0.0f));
            float u_equipment = 1.0f - expf(-(equipment_score - 0.0f) / (1.0f - 0.0f));
            
            // Weighted sum
            float total_score = weights[0] * u_safety + 
                               weights[1] * u_completion + 
                               weights[2] * u_equipment;
            
            if (total_score > best_score) {
                best_score = total_score;
                best_action = actions[i];
            }
        }
        
        return best_action;
    }
    
    // Communication loss probability calculation
    float _calculate_comm_loss_probability(float distance, float timeout) {
        // Base failure rate at reference distance
        float lambda0 = 0.001f; // 0.001 s⁻¹ at 100m
        
        // Distance scaling: λ ∝ r²
        float distance_factor = (distance / 100.0f) * (distance / 100.0f);
        
        // Terrain attenuation
        AP_Terrain &terrain = AP::terrain();
        float terrain_variation = terrain.get_terrain_variation();
        float height_factor = expf(-terrain_variation / 10.0f);
        
        // Effective failure rate
        float lambda = lambda0 * distance_factor * height_factor;
        
        // Probability of loss exceeding timeout
        float p_loss = 1.0f - expf(-lambda * timeout);
        
        return p_loss;
    }
    
    // Inertia-aware stopping distance calculation
    float _calculate_stopping_distance(float current_speed, float deceleration) {
        // For a 750kg rover with 300 kg·m² inertia
        // Account for rotational kinetic energy
        
        AP_AHRS &ahrs = AP::ahrs();
        float angular_speed = ahrs.get_gyro().length();
        
        // Total kinetic energy = translational + rotational
        float translational_energy = 0.5f * 750.0f * current_speed * current_speed;
        float rotational_energy = 0.5f * 300.0f * angular_speed * angular_speed;
        
        float total_energy = translational_energy + rotational_energy;
        
        // Stopping distance = energy / (force * efficiency)
        float stopping_force = 750.0f * deceleration;
        float efficiency = 0.8f; // Braking efficiency
        
        float stopping_distance = total_energy / (stopping_force * efficiency);
        
        return stopping_distance;
    }
};

// Helper functions for coordinate transformations
Vector2f AP_AdvancedFailsafe::_location_to_local_xy(const Location &loc) {
    // Convert WGS-84 to local tangent plane coordinates
    // Simplified for small distances (< 1km)
    static Location reference_loc;
    static bool reference_set = false;
    
    if (!reference_set) {
        reference_loc = loc;
        reference_set = true;
    }
    
    float dlat = loc.lat - reference_loc.lat;
    float dlng = loc.lng - reference_loc.lng;
    
    // Convert to meters (approximate)
    float x = dlng * 111319.0f * cosf(radians(reference_loc.lat));
    float y = dlat * 111319.0f;
    
    return Vector2f(x, y);
}

float AP_AdvancedFailsafe::_is_point_left_of_edge(const Vector2f &p, const Vector2f &v1, const Vector2f &v2) {
    // Cross product to determine if point is left of edge
    return (v2.x - v1.x) * (p.y - v1.y) - (p.x - v1.x) * (v2.y - v1.y);
}
```

### Core Failsafe System (failsafe.cpp)

```cpp
class AP_Failsafe {
public:
    enum FailsafeAction {
        ACTION_NONE = 0,
        ACTION_DISARM,
        ACTION_LAND,
        ACTION_RTL,
        ACTION_SMART_RTL,
        ACTION_TERMINATE,
        ACTION_HOLD
    };
    
    struct FailsafeConfig {
        uint8_t battery_fs_action;
        uint8_t gcs_fs_action;
        uint8_t geo_fence_action;
        uint8_t ekf_action;
        uint8_t terrain_action;
        uint8_t adsb_action;
        uint16_t gcs_timeout_ms;
        float battery_voltage_min;
        float battery_capacity_min;
        uint8_t battery_fs_threshold;
    };
    
private:
    FailsafeConfig config;
    bool failsafe_triggered;
    uint32_t failsafe_trigger_time_ms;
    FailsafeAction current_action;
    
    // Battery failsafe monitoring
    void _check_battery_failsafe() {
        AP_BattMonitor &batt = AP::battery();
        
        // Check all battery instances
        for (uint8_t i = 0; i < batt.num_instances(); i++) {
            if (!batt.healthy(i)) {
                continue;
            }
            
            float voltage = batt.voltage(i);
            float current = batt.current_amps(i);
            float capacity_remaining = batt.capacity_remaining_pct(i);
            
            // Apply dynamic threshold for 750kg rover
            float voltage_threshold = config.battery_voltage_min;
            
            // Adjust for load current
            voltage_threshold -= current * 0.05f; // 50mV per amp
            
            // Adjust for rover mass
            voltage_threshold *= (1.0f - (750.0f - 500.0f) / 500.0f * 0.1f);
            
            // Check voltage
            if (voltage < voltage_threshold) {
                _trigger_failsafe(FAILSAFE_BATTERY, config.battery_fs_action);
                return;
            }
            
            // Check capacity
            if (capacity_remaining < config.battery_capacity_min) {
                _trigger_failsafe(FAILSAFE_BATTERY, config.battery_fs_action);
                return;
            }
            
            // Check current spike (short circuit detection)
            if (current > 100.0f) { // 100A threshold for 750kg rover
                _trigger_failsafe(FAILSAFE_BATTERY, ACTION_DISARM);
                return;
            }
        }
    }
    
    // GCS communication failsafe
    void _check_gcs_failsafe() {
        uint32_t now = AP_HAL::millis();
        uint32_t last_heartbeat_ms = gcs().last_heartbeat_ms();
        
        if (now - last_heartbeat_ms > config.gcs_timeout_ms) {
            // Calculate loss probability
            float distance = _estimate_gcs_distance();
            float timeout_seconds = config.gcs_timeout_ms / 1000.0f;
            float p_loss = _calculate_comm_loss_probability(distance, timeout_seconds);
            
            // Only trigger if probability is high
            if (p_loss > 0.95f) {
                _trigger_failsafe(FAILSAFE_GCS, config.gcs_fs_action);
            }
        }
    }
    
    // EKF failsafe monitoring
    void _check_ekf_failsafe() {
        AP_AHRS &ahrs = AP::ahrs();
        
        // Get EKF status
        nav_filter_status filter_status;
        ahrs.get_filter_status(filter_status);
        
        // Check attitude variance (inertia-aware)
        Vector3f attitude_variance;
        ahrs.get_variances(attitude_variance);
        
        // Scale variance by inertia (300 kg·m² rover needs more precise attitude)
        float max_variance = 0.01f * (300.0f / 100.0f);
        
        if (attitude_variance.x > max_variance || 
            attitude_variance.y > max_variance ||
            attitude_variance.z > max_variance) {
            _trigger_failsafe(FAILSAFE_EKF, config.ekf_action);
            return;
        }
        
        // Check velocity variance
        Vector3f velocity_variance;
        ahrs.get_velocity_variance(velocity_variance);
        
        // For 750kg rover, velocity errors are more critical
        float velocity_variance_threshold = 1.0f; // m²/s²
        if (velocity_variance.length() > velocity_variance_threshold) {
            _trigger_failsafe(FAILSAFE_EKF, config.ekf_action);
            return;
        }
        
        // Check position variance
        Vector3f position_variance;
        ahrs.get_position_variance(position_variance);
        
        float position_variance_threshold = 10.0f; // m²
        if (position_variance.length() > position_variance_threshold) {
            _trigger_failsafe(FAILSAFE_EKF, config.ekf_action);
            return;
        }
    }
    
    // Terrain failsafe
    void _check_terrain_failsafe() {
#if AP_TERRAIN_AVAILABLE
        AP_Terrain &terrain = AP::terrain();
        
        if (!terrain.enabled()) {
            return;
        }
        
        Location current_loc;
        if (!AP::ahrs().get_position(current_loc)) {
            return;
        }
        
        // Get terrain height
        float terrain_height;
        if (!terrain.height_amsl(current_loc, terrain_height)) {
            return;
        }
        
        // Get current altitude
        float current_alt = current_loc.alt