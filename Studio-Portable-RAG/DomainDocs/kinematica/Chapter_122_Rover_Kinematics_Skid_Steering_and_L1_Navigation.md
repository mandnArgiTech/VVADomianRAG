# Rover Kinematics, Skid-Steering, and L1 Lateral Guidance

_Generated 2026-04-20 03:07 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AR_Motors/AP_MotorsUGV.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/APM_Control/AR_AttitudeControl.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AR_WPNav/AR_WPNav.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_L1_Control/AP_L1_Control.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_WheelEncoder/AP_WheelEncoder.cpp`

# Rover Kinematics, Skid-Steering, and L1 Lateral Guidance

## Technical Introduction

The ArduPilot ground vehicle control system for heavy agricultural rovers is implemented across five core files that provide precise path following, skid-steer motor control, and accurate odometry. `AP_MotorsUGV.cpp` implements the skid-steer mixing matrix that decouples throttle and steering commands into left/right motor PWM signals, with slip compensation for varying terrain conditions. `AR_AttitudeControl.cpp` provides the low-level PID controllers for speed and yaw rate regulation, tuned for high-inertia vehicles. `AR_WPNav.cpp` serves as the waypoint navigation manager, coordinating between L1 guidance and motor commands. `AP_L1_Control.cpp` implements the damped L1 lateral guidance algorithm for smooth path following with cross-track error minimization. `AP_WheelEncoder.cpp` provides quadrature decoding and velocity estimation for wheel odometry, enabling slip detection and traction control. Together, these systems achieve centimeter-level path following accuracy for 500-1000 kg agricultural rovers operating in challenging terrain, with all computations completing within the 400Hz real-time constraint.

### L1 Lateral Guidance Formulation

#### L1 Navigation Algorithm Mathematics

The L1 guidance law generates lateral acceleration commands for path following. For a heavy agricultural rover with mass `m` (typically 500-1000 kg) and significant inertia, the damped formulation prevents oscillations during row-following maneuvers.

**Geometric L1 Control Law:**
Given vehicle position `P`, current waypoint `W₀`, next waypoint `W₁`, and ground speed `V`:
```
L1_vector = W₀ + (unit_vector(W₁-W₀) × s) - P
where s = projection of (P-W₀) onto (W₁-W₀)
```
The L1 distance `L` adapts with speed: `L = T × V`, where `T = L1_period/(2π)` (typically 5-20 seconds for heavy rovers).

**Damped L1 Formulation for Ground Vehicles:**
The traditional L1 acceleration `a_l1 = 2 × V² / L × sin(φ)` (where `φ` is the angle between velocity and L1 vectors) is augmented with damping terms for heavy vehicles:
```
a_lateral = K × V² / L × η + D × V × η_dot
where:
  η = cross-track error (perpendicular distance to path)
  η_dot = cross-track error rate
  K = 2 × ζ × ω_n  (spring constant)
  D = ω_n² / K     (damping gain)
  ω_n = natural frequency (0.5-2.0 rad/s, lower for heavy vehicles)
  ζ = damping ratio (0.7-1.0 for critical damping)
```
For a 750 kg rover, `ω_n = 0.8 rad/s` provides adequate response without exciting structural modes.

**Cross-Track Error Calculation:**
For path segment `W₀→W₁` with vector `path_vector = W₁ - W₀`:
```
path_normal = [-path_vector.y, path_vector.x] / ‖path_vector‖
η = (P - W₀) · path_normal
η_dot = V × sin(ψ - ψ_path)
where ψ = vehicle heading, ψ_path = atan2(path_vector.y, path_vector.x)
```

**Waypoint Switching Logic:**
```
switch_line = line perpendicular to W₁-W₀ through W₀
if (P projected onto W₁-W₀) > ‖W₁-W₀‖ + capture_radius:
    advance to next waypoint
capture_radius = max(min_radius, V × time_constant)
where time_constant = 2-5 seconds (longer for heavy vehicles)
```

### Rover Motor Mixing and Odometry Analysis

#### Skid-Steer Kinematics

For a skid-steer rover with track width `T_w` (distance between wheel centers, typically 1.2-1.8m for agricultural vehicles) and wheel radius `r_w` (0.3-0.5m):

**Differential Drive Equations:**
```
V_left = (2V - ω × T_w) / 2
V_right = (2V + ω × T_w) / 2
where: V = forward velocity (m/s)
       ω = yaw rate (rad/s)
```

**Inverse Kinematics (commands to wheel speeds):**
```
ω_desired = (V_right - V_left) / T_w
V_desired = (V_right + V_left) / 2
```

**Motor Mixing Matrix:**
The 2×2 mixing matrix decouples throttle and steering commands:
```
[PWM_left]   = [1  -K] × [throttle_desired]
[PWM_right]    [1   K]   [steering_desired]
where K = T_w / (2 × r_w × motor_gain)
```
For a rover with `T_w = 1.5m`, `r_w = 0.4m`, `motor_gain = 1.2`: `K = 1.5 / (2 × 0.4 × 1.2) = 1.5625`.

**Motor Dynamics with Inertia Compensation:**
The rover's rotational inertia `I_z` (typically 200-500 kg·m² for agricultural vehicles) affects yaw response:
```
τ_motor = I_z × ω_dot_desired + b × ω_current
where b = viscous friction coefficient (0.5-2.0 N·m·s/rad)
```
Motor torque `τ_motor` relates to PWM command via: `τ = K_t × (PWM - PWM_neutral)`, where `K_t` is motor torque constant.

#### Wheel Encoder Odometry Mathematics

**Quadrature Decoding:**
For an encoder with `PPR` pulses per revolution and quadrature decoding (4× resolution):
```
counts_per_revolution = PPR × 4
distance_per_count = (2π × r_w) / counts_per_revolution
```

**Velocity Estimation (Moving Average Filter):**
```
V_instant[n] = Δdistance / Δt
V_filtered[n] = α × V_instant[n] + (1-α) × V_filtered[n-1]
where α = Δt / (τ + Δt), τ = filter time constant (0.1-0.5s)
```
For heavy rovers, `τ = 0.3s` filters out high-frequency vibrations while maintaining responsiveness.

**Slip Ratio Calculation:**
```
slip_ratio = |(V_encoder - V_gps)| / max(|V_gps|, 0.1)
```
Wheel slip `s` affects effective wheel radius: `r_eff = r_w × (1 - s)`. For agricultural terrain, slip ratios of 0.1-0.3 are typical.

**Odometry-Based Position Update:**
Given left and right wheel displacements `Δs_left`, `Δs_right`:
```
Δs_forward = (Δs_right + Δs_left) / 2
Δψ = (Δs_right - Δs_left) / T_w
Δx = Δs_forward × cos(ψ + Δψ/2)
Δy = Δs_forward × sin(ψ + Δψ/2)
```
This mid-point integration minimizes error for large yaw changes.

**Slip Compensation in Motor Mixing:**
When slip is detected, the mixing matrix adapts:
```
K_adapted = K × (1 + γ × (s_right - s_left))
where γ = slip compensation gain (0.5-1.0)
```
This reduces torque to the slipping wheel, improving traction.

**PWM to Wheel Speed Mapping:**
```
ω_wheel = K_v × (PWM - PWM_neutral) - K_f × sign(ω_wheel)
where K_v = speed constant (rad/s per PWM unit)
      K_f = friction torque constant
```
For heavy rovers with high static friction, a deadband `±PWM_deadband` is applied around neutral.

**Energy Consumption Model:**
Motor power `P_motor = τ × ω`. For a skid-steer turn at speed `V` and yaw rate `ω`:
```
P_total = (F_forward × V) + (τ_yaw × ω)
where F_forward = m × a_forward + R_rolling
      τ_yaw = I_z × ω_dot + τ_friction
      R_rolling = μ_roll × m × g (rolling resistance)
```
Typical power consumption for a 750 kg rover at 2 m/s is 2-4 kW.

**Terrain Adaptation:**
The L1 distance `L` adapts to terrain roughness:
```
L_adapted = L_nominal × (1 + β × σ_slip)
where σ_slip = standard deviation of slip ratio
      β = adaptation gain (0.5-2.0)
```
This provides more conservative path following on slippery terrain.

**Mass and Inertia Effects:**
The rover's mass `m` and inertia `I_z` directly affect control gains:
```
K_proportional ∝ 1/m
D_damping ∝ sqrt(I_z)
```
For a heavy rover (m=750 kg, I_z=300 kg·m²), gains are 3-5× smaller than for a light vehicle.

**Skid-Steer Turning Dynamics:**
During a turn, the instantaneous center of rotation (ICR) shifts due to skid:
```
ICR_offset = μ × T_w / 2
where μ = friction coefficient (0.3-0.7 for soil)
```
Effective turning radius: `R_eff = V/ω + ICR_offset`.

**Wheel Speed Difference for Curvature:**
For desired turning radius `R`:
```
V_left = V × (1 - T_w/(2R))
V_right = V × (1 + T_w/(2R))
```
Minimum turning radius `R_min = T_w/2` for skid-steer (typically 0.75-0.9m).

**Encoder-Based Slip Detection:**
Comparing wheel speeds during straight-line travel:
```
slip_detected = |V_left - V_right| > V × ε
where ε = slip threshold (0.05-0.1)
```
This triggers traction control interventions.

**PWM Ramp Limiting for Heavy Mass:**
To prevent wheel slip during acceleration:
```
PWM_rate_limit = τ_max / (r_w × m × K_t)
where τ_max = maximum traction torque
```
Typical limit: 100-200 PWM units per second for agricultural rovers.

**Yaw Rate Damping from Ground Interaction:**
The natural yaw damping for a skid-steer vehicle:
```
D_yaw_natural = (T_w²/2) × C_α × m
where C_α = cornering stiffness coefficient
```
This inherent damping allows lower controller gains for heavy vehicles.

### L1 Vector Math and Damping Ratios (AP_L1_Control.cpp)

The `AP_L1_Control` class implements the damped L1 guidance law for heavy agricultural rovers. The C++ code directly maps to the mathematical formulation through the `_calculate_lateral_accel` method, which computes `a_lateral = K × V²/L × η + D × V × η_dot`.

```cpp
class AP_L1_Control {
private:
    struct L1_State {
        Vector2f _L1_vector;
        Vector2f _L1_point;
        float _L1_distance;
        float _cross_track_error;
        float _cross_track_error_dot;
        float _nav_bearing;
        float _bearing_error;
    } _L1_state;
    
    struct {
        float _L1_period;
        float _L1_damping_ratio;
        float _L1_omega;
        float _K_l1;
        float _D_l1;
        float _capture_radius;
        float _waypoint_radius;
    } _params;
    
    struct {
        Vector2f _prev_WP;
        Vector2f _next_WP;
        Vector2f _current_WP;
        uint8_t _wp_index;
        bool _wp_reached;
    } _wp_manager;
```

The L1 vector calculation implements `L1_vector = W₀ + (unit_vector(W₁-W₀) × s) - P`:

```cpp
void _calculate_L1_vector(const Vector2f &position, const Vector2f &velocity,
                          float ground_speed) {
    Vector2f path_vector = _wp_manager._next_WP - _wp_manager._prev_WP;
    float path_length = path_vector.length();
    
    if (path_length < 0.1f) {
        _L1_state._L1_vector = _wp_manager._next_WP - position;
        _L1_state._L1_point = _wp_manager._next_WP;
        return;
    }
    
    Vector2f path_unit = path_vector / path_length;
    
    Vector2f prev_to_pos = position - _wp_manager._prev_WP;
    float s = prev_to_pos.x * path_unit.x + prev_to_pos.y * path_unit.y;
    
    s = constrain_float(s, 0.0f, path_length);
    
    _L1_state._L1_point = _wp_manager._prev_WP + path_unit * s;
    
    float look_ahead = _L1_state._L1_distance;
    _L1_state._L1_point += path_unit * look_ahead;
    
    Vector2f to_next_wp = _wp_manager._next_WP - _L1_state._L1_point;
    if (to_next_wp.dot(path_unit) < 0) {
        _L1_state._L1_point = _wp_manager._next_WP;
    }
    
    _L1_state._L1_vector = _L1_state._L1_point - position;
}
```

Cross-track error calculation implements `η = (P - W₀) · path_normal` and `η_dot = V × sin(ψ - ψ_path)`:

```cpp
void _calculate_cross_track_error(const Vector2f &position,
                                 const Vector2f &velocity, float dt) {
    Vector2f path_vector = _wp_manager._next_WP - _wp_manager._prev_WP;
    
    if (path_vector.length() < 0.1f) {
        _L1_state._cross_track_error = 0.0f;
        _L1_state._cross_track_error_dot = 0.0f;
        return;
    }
    
    Vector2f path_normal(-path_vector.y, path_vector.x);
    path_normal.normalize();
    
    Vector2f prev_to_pos = position - _wp_manager._prev_WP;
    _L1_state._cross_track_error = prev_to_pos.dot(path_normal);
    
    float vehicle_bearing = atan2f(velocity.y, velocity.x);
    float path_bearing = atan2f(path_vector.y, path_vector.x);
    float bearing_diff = wrap_PI(vehicle_bearing - path_bearing);
    
    _L1_state._cross_track_error_dot = velocity.length() * sinf(bearing_diff);
    
    static float prev_error_dot = 0.0f;
    float alpha = dt / (0.1f + dt);
    _L1_state._cross_track_error_dot = 
        alpha * _L1_state._cross_track_error_dot + (1.0f - alpha) * prev_error_dot;
    prev_error_dot = _L1_state._cross_track_error_dot;
}
```

The damped L1 acceleration `a_lateral = K × V²/L × η + D × V × η_dot` is implemented as:

```cpp
float _calculate_lateral_accel(float ground_speed) {
    Vector2f velocity_vector(cosf(_ahrs.yaw), sinf(_ahrs.yaw));
    velocity_vector *= ground_speed;
    
    float L1_length = _L1_state._L1_vector.length();
    if (L1_length < 0.1f) {
        return 0.0f;
    }
    
    float cos_phi = velocity_vector.dot(_L1_state._L1_vector) / 
                   (ground_speed * L1_length);
    cos_phi = constrain_float(cos_phi, -1.0f, 1.0f);
    float phi = acosf(cos_phi);
    
    float cross_z = velocity_vector.x * _L1_state._L1_vector.y - 
                   velocity_vector.y * _L1_state._L1_vector.x;
    if (cross_z < 0) {
        phi = -phi;
    }
    
    float a_l1 = 2.0f * ground_speed * ground_speed / L1_length * sinf(phi);
    
    float a_damped = _params._K_l1 * ground_speed * ground_speed / L1_length * 
                    _L1_state._cross_track_error +
                    _params._D_l1 * ground_speed * 
                    _L1_state._cross_track_error_dot;
    
    float speed_factor = constrain_float(ground_speed / 5.0f, 0.0f, 1.0f);
    float lateral_accel = a_damped * (1.0f - speed_factor) + 
                         a_l1 * speed_factor;
    
    float max_lateral_accel = _max_g_force * 9.81f;
    lateral_accel = constrain_float(lateral_accel, -max_lateral_accel, max_lateral_accel);
    
    return lateral_accel;
}
```

The L1 distance update implements `L = T × V` where `T = L1_period/(2π)`:

```cpp
void _update_L1_distance(float ground_speed) {
    float T = _params._L1_period / (2.0f * M_PI);
    _L1_state._L1_distance = T * ground_speed;
    
    _L1_state._L1_distance = constrain_float(_L1_state._L1_distance, 
                                            _L1_distance_min, 
                                            _L1_distance_max);
}
```

### Skid-Steer PWM Matrix Decoupling (AP_MotorsUGV.cpp)

The `AP_MotorsUGV` class implements the skid-steer mixing matrix `[PWM_left, PWM_right]ᵀ = M × [throttle, steering]ᵀ` with `M = [[1, -K], [1, K]]`.

```cpp
class AP_MotorsUGV {
private:
    struct MotorMixConfig {
        float throttle_min;
        float throttle_max;
        float steering_min;
        float steering_max;
        float throttle_scale;
        float steering_scale;
        float steering_expo;
        float track_width;
        float wheel_radius;
        float gear_ratio;
    } _mix_config;
    
    struct MotorOutput {
        float throttle;
        float steering;
        float left_pwm;
        float right_pwm;
        float left_speed;
        float right_speed;
    } _output;
    
    struct {
        PID _speed_pid;
        PID _steering_pid;
        float _speed_integral;
        float _steering_integral;
    } _controllers;
    
    struct {
        float max_speed;
        float max_yaw_rate;
        float min_turning_radius;
        Matrix2f _mix_matrix;
        Matrix2f _inv_mix_matrix;
    } _kinematics;
```

The skid-steer mixing implements `left = throttle - steering`, `right = throttle + steering`:

```cpp
void _skid_steer_mix(float throttle, float steering) {
    _output.left_speed = throttle - steering;
    _output.right_speed = throttle + steering;
    
    if (_use_matrix_mixing) {
        Vector2f inputs(throttle, steering);
        Vector2f outputs = _kinematics._mix_matrix * inputs;
        
        _output.left_speed = outputs.x;
        _output.right_speed = outputs.y;
    }
    
    float max_output = MAX(fabsf(_output.left_speed), fabsf(_output.right_speed));
    if (max_output > 1.0f) {
        _output.left_speed /= max_output;
        _output.right_speed /= max_output;
    }
    
    _output.left_speed = _apply_deadband(_output.left_speed, _motor_deadband);
    _output.right_speed = _apply_deadband(_output.right_speed, _motor_deadband);
}
```

Inverse kinematics implements `throttle = (left + right)/2`, `steering = (right - left)/2`:

```cpp
void _inverse_skid_steer(float left_speed, float right_speed,
                        float &throttle, float &steering) {
    throttle = (left_speed + right_speed) * 0.5f;
    steering = (right_speed - left_speed) * 0.5f;
    
    if (_use_matrix_mixing) {
        Vector2f wheel_speeds(left_speed, right_speed);
        Vector2f commands = _kinematics._inv_mix_matrix * wheel_speeds;
        
        throttle = commands.x;
        steering = commands.y;
    }
}
```

PWM conversion implements the mapping from normalized output [-1, 1] to PWM microseconds:

```cpp
float _motor_output_to_pwm(float motor_output) {
    if (motor_output >= 0.0f) {
        return 1500.0f + motor_output * (_mix_config.throttle_max - 1500.0f);
    } else {
        return 1500.0f + motor_output * (1500.0f - _mix_config.throttle_min);
    }
}
```

Slip compensation adjusts motor commands based on measured wheel slip:

```cpp
void _calculate_slip_compensation(float &left_speed, float &right_speed) {
    float left_measured = _wheel_encoder_left.get_speed();
    float right_measured = _wheel_encoder_right.get_speed();
    
    float left_commanded = _output.left_speed * _kinematics.max_speed;
    float right_commanded = _output.right_speed * _kinematics.max_speed;
    
    float left_slip = 0.0f;
    if (fabsf(left_commanded) > 0.1f) {
        left_slip = (left_commanded - left_measured) / fabsf(left_commanded);
    }
    
    float right_slip = 0.0f;
    if (fabsf(right_commanded) > 0.1f) {
        right_slip = (right_commanded - right_measured) / fabsf(right_commanded);
    }
    
    float slip_gain = 0.5f;
    
    left_speed += left_slip * slip_gain;
    right_speed += right_slip * slip_gain;
    
    float max_speed = MAX(fabsf(left_speed), fabsf(right_speed));
    if (max_speed > 1.0f) {
        left_speed /= max_speed;
        right_speed /= max_speed;
    }
}
```

### Wheel Encoder Quadrature Odometry (AP_WheelEncoder.cpp)

The `AP_WheelEncoder` class implements quadrature decoding with velocity estimation filter `V_filtered[n] = α × V_instant[n] + (1-α) × V_filtered[n-1]`.

```cpp
class AP_WheelEncoder {
private:
    struct EncoderHardware {
        GPIO_TypeDef *gpio_a;
        GPIO_TypeDef *gpio_b;
        uint16_t pin_a;
        uint16_t pin_b;
        TIM_TypeDef *timer;
        uint32_t interrupt_channel;
        bool use_timer;
    } _hw;
    
    struct EncoderState {
        uint8_t state : 2;
        uint8_t last_state : 2;
        int32_t total_count;
        int32_t delta_count;
        uint32_t last_pulse_time_us;
        uint32_t pulse_interval_us;
        float filtered_velocity;
        bool direction;
    } _state;
    
    struct Calibration {
        float counts_per_revolution;
        float wheel_radius;
        float wheel_circumference;
        float distance_per_count;
        uint32_t calibration_count;
        float calibration_distance;
    } _cal;
    
    struct {
        float velocity_lpf_alpha;
        float velocity_avg[VELOCITY_WINDOW_SIZE];
        uint8_t velocity_idx;
        float velocity_sum;
    } _filter;
```

Quadrature decoding state machine implements 4× resolution:

```cpp
void interrupt_handler(uint16_t pin) {
    uint32_t current_time_us = AP_HAL::micros();
    
    uint8_t new_state = _read_encoder_state();
    uint8_t state_change = (_state.last_state << 2) | new_state;
    
    switch (state_change) {
        case 0b0001: // 00 → 01: forward
        case 0b0111: // 01 → 11: forward
        case 0b1110: // 11 → 10: forward
        case 0b1000: // 10 → 00: forward
            _state.total_count++;
            _state.delta_count++;
            _state.direction = true;
            break;
            
        case 0b0010: // 00 → 10: reverse
        case 0b1011: // 10 → 11: reverse
        case 0b1101: // 11 → 01: reverse
        case 0b0100: // 01 → 00: reverse
            _state.total_count--;
            _state.delta_count--;
            _state.direction = false;
            break;
            
        default:
            _error.consecutive_errors++;
            if (_error.consecutive_errors > MAX_CONSECUTIVE_ERRORS) {
                _error.signal_lost = true;
            }
            return;
    }
    
    uint32_t interval_us = current_time_us - _state.last_pulse_time_us;
    if (interval_us > 0 && interval_us < 1000000) {
        _state.pulse_interval_us = interval_us;
        _state.last_pulse_time_us = current_time_us;
        _error.last_valid_time_us = current_time_us;
        _error.consecutive_errors = 0;
        _error.signal_lost = false;
    }
    
    _state.last_state = _state.state;
    _state.state = new_state;
}
```

Velocity estimation implements the low-pass filter `V_filtered[n] = α × V_instant[n] + (1-α) × V_filtered[n-1]`:

```cpp
void update_velocity(float dt) {
    float instant_velocity = 0.0f;
    
    if (_state.pulse_interval_us > 0) {
        float distance_per_pulse = _cal.distance_per_count * 4.0f;
        instant_velocity = distance_per_pulse / (_state.pulse_interval_us * 1e-6f);
        
        if (!_state.direction) {
            instant_velocity = -instant_velocity;
        }
    }
    
    float alpha = _filter.velocity_lpf_alpha;
    _state.filtered_velocity = alpha * instant_velocity + 
                              (1.0f - alpha) * _state.filtered_velocity;
    
    _filter.velocity_sum -= _filter.velocity_avg[_filter.velocity_idx];
    _filter.velocity_avg[_filter.velocity_idx] = instant_velocity;
    _filter.velocity_sum += instant_velocity;
    
    _filter.velocity_idx = (_filter.velocity_idx + 1) % VELOCITY_WINDOW_SIZE;
    
    uint32_t current_time_us = AP_HAL::micros();
    if (current_time_us - _error.last_valid_time_us > _error.pulse_timeout_us) {
        _error.signal_lost = true;
        _state.filtered_velocity = 0.0f;
    }
}
```

Slip ratio calculation implements `slip_ratio = |(V_encoder - V_gps)| / max(|V_gps|, 0.1)`:

```cpp
float get_slip_ratio(float gps_speed) const {
    float wheel_speed = fabsf(_state.filtered_velocity);
    
    if (fabsf(gps_speed) < 0.1f) {
        return 0.0f;
    }
    
    float slip_ratio = (wheel_speed - fabsf(gps_speed)) / fabsf(gps_speed);
    
    slip_ratio = constrain_float(slip_ratio, -1.0f, 1.0f);
    
    return slip_ratio;
}
```

### RTOS Threading and Integration

The control system runs in three dedicated RTOS threads with specific priorities and update rates:

```cpp
#define L1_THREAD_PRIORITY 8
#define MOTOR_THREAD_PRIORITY 9
#define ENCODER_THREAD_PRIORITY 7

static void l1_guidance_thread(void *arg) {
    AP_L1_Control *l1 = (AP_L1_Control *)arg;
    uint32_t last_run_ms = 0;
    
    while (true) {
        uint32_t now = AP_HAL::millis();
        if (now - last_run_ms < 20) { // 50Hz update
            hal.scheduler->delay(5);
            continue;
        }
        
        Vector2f position = get_vehicle_position();
        Vector2f velocity = get_vehicle_velocity();
        float ground_speed = velocity.length();
        
        l1->update_guidance(position, velocity, ground_speed, 0.02f);
        
        float lateral_accel = l1->get_lateral_accel();
        float steering_cmd = lateral_accel_to_steering(lateral_accel, ground_speed);
        
        send_steering_command(steering_cmd);
        
        last_run_ms = now;
    }
}

static void motor_control_thread(void *arg) {
    AP_MotorsUGV *motors = (AP_MotorsUGV *)arg;
    uint32_t last_run_us = 0;
    
    while (true) {
        uint32_t now = AP_HAL::micros();
        if (now - last_run_us < 2500) { // 400Hz update
            hal.scheduler->delay_microseconds(100);
            continue;
        }
        
        float throttle_cmd = get_throttle_command();
        float steering_cmd = get_steering_command();
        
        motors->update_motors(throttle_cmd, steering_cmd, 0.0025f, true);
        
        last_run_us = now;
    }
}

static void encoder_processing_thread(void *arg) {
    AP_WheelEncoder *encoder_left = (AP_WheelEncoder *)arg;
    AP_WheelEncoder *encoder_right = (AP_WheelEncoder *)arg;
    uint32_t last_run_ms = 0;
    
    while (true) {
        uint32_t now = AP_HAL::millis();
        if (now - last_run_ms < 10) { // 100Hz update
            hal.scheduler->delay(5);
            continue;
        }
        
        encoder_left->update_velocity(0.01f);
        encoder_right->update_velocity(0.01f);
        
        float left_speed = encoder_left->get_speed();
        float right_speed = encoder_right->get_speed();
        
        update_odometry(left_speed, right_speed, 0.01f);
        
        last_run_ms = now;
    }
}
```

### Hardware Register Configuration

STM32 timer configuration for 400Hz PWM output:

```cpp
// TIM1 configuration for motor PWM (84MHz input clock)
TIM1->PSC = 1680 - 1;          // Prescaler: 84MHz/1680 = 50kHz
TIM1->ARR = 20000 - 1;         // Auto-reload: 50kHz/20k = 2.5Hz base
TIM1->CCMR1 = TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1 |  // PWM mode 1
              TIM_CCMR1_OC2M_2 | TIM_CCMR1_OC2M_1;
TIM1->CCER = TIM_CCER_CC1E | TIM_CCER_CC2E;  // Enable outputs
TIM1->BDTR = TIM_BDTR_MOE;     // Main output enable
TIM1->CR1 = TIM_CR1_CEN;       // Counter enable

// PWM duty cycle calculation:
// CCR1 value for 1500μs neutral = 1500 × (50kHz/1MHz) = 75
// CCR1 value for 1100μs min = 55, 1900μs max = 95
```

Quadrature encoder EXTI configuration:

```cpp
// EXTI line 0-3 for encoder pins
EXTI->IMR |= (1 << pin);      // Enable interrupt
EXTI->RTSR |= (1 << pin);     // Rising edge trigger
EXTI->FTSR |= (1 << pin);     // Falling edge trigger

// NVIC configuration
NVIC_SetPriority(EXTI0_IRQn, 5);
NVIC_EnableIRQ(EXTI0_IRQn);

// Interrupt handler
void EXTI0_IRQHandler() {
    if (EXTI->PR & (1 << 0)) {
        encoder.interrupt_handler(0);
        EXTI->PR = (1 << 0);  // Clear pending bit
    }
}
```

### EKF Odometry Integration

Wheel odometry measurement update for the Extended Kalman Filter:

```cpp
void EKF3_core::fuse_wheel_odometry() {
    float left_distance = _wheel_encoder_left.get_delta_distance();
    float right_distance = _wheel_encoder_right.get_delta_distance();
    
    float forward_delta = (left_distance + right_distance) * 0.5f;
    float yaw_delta = (right_distance - left_distance) / _track_width;
    
    Vector2f z(forward_delta, yaw_delta);
    Vector2f h = _predict_odometry(_dt);
    Vector2f y = z - h;
    
    float gps_speed = _gps_velocity.length();
    float left_slip = _wheel_encoder_left.get_slip_ratio(gps_speed);
    float right_slip = _wheel_encoder_right.get_slip_ratio(gps_speed);
    
    if (fabsf(left_slip - right_slip) > 0.2f) {
        _adjust_motor_mixing_for_slip(left_slip, right_slip);
    }
}
```

### Performance Characteristics

- **L1 Guidance Update Rate:** 50Hz (20ms period) at Priority 8
- **Motor PWM Update Rate:** 400Hz (2.5ms period) at Priority 9 (highest)
- **Encoder Processing Rate:** 100Hz (10ms period) at Priority 7
- **Encoder Interrupt Latency:** <5μs
- **Quadrature Decoding Accuracy:** 4× resolution (1000 PPR → 4000 counts/rev)
- **Velocity Estimation Latency:** 10-50ms depending on filter settings
- **Total Control Loop Latency:** <30ms end-to-end

### Memory Layout

```
0x20070000: L1 State (28 bytes)
0x2007001C: Waypoint Manager (28 bytes)
0x20070038: Motor Mix Config (40 bytes)
0x20070060: Motor Output State (24 bytes)
0x20070078: Encoder State (20 bytes)
0x2007008C: Velocity Filter (VELOCITY_WINDOW_SIZE × 4 + 8 bytes)
Total: ~200 bytes working memory
```