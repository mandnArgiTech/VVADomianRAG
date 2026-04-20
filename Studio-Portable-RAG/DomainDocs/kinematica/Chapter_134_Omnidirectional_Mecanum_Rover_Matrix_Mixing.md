# Omnidirectional Mecanum Rover Matrix Mixing

_Generated 2026-04-20 04:37 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AR_Motors/AP_MotorsUGV.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AR_WPNav/AR_WPNav.cpp`

# Omnidirectional Mecanum Rover Matrix Mixing

This chapter details the C++ implementation of omnidirectional motion control for a heavy agricultural rover (mass ~750 kg, inertia ~300 kg·m²) equipped with Mecanum wheels within the ArduPilot framework. The system enables true holonomic movement—simultaneous translation in any direction and rotation about the vertical axis—through precise matrix-based wheel speed coordination. The implementation in `AP_MotorsUGV_Mecanum.cpp` directly maps kinematic equations to a mixing matrix that transforms desired body-frame velocity commands into individual wheel motor speeds, while `AR_WPNav.cpp` provides the high-level navigation commands that drive this mixing system. The architecture must account for the rover's significant dynamic coupling and wheel load distribution while maintaining deterministic 400Hz real-time performance.

### Mecanum Wheel Kinematics Formulation

**Chassis Velocity to Wheel Velocity Transformation**

For a four-wheel Mecanum rover with wheels at 45° angles, the kinematic relationship between chassis velocities and wheel velocities is defined by the inverse Jacobian matrix:

```
[ω₁]   [1  -1  -(L_x + L_y)] [v_x]
[ω₂] = [1   1   (L_x + L_y)] [v_y]
[ω₃]   [1   1  -(L_x + L_y)] [ω_z]
[ω₄]   [1  -1   (L_x + L_y)]

where:
  ω_i = angular velocity of wheel i (rad/s)
  v_x = chassis longitudinal velocity (m/s)
  v_y = chassis lateral velocity (m/s)  
  ω_z = chassis yaw rate (rad/s)
  L_x = half wheelbase in x-direction (m)
  L_y = half track width in y-direction (m)
```

**Inverse Kinematics for Heavy Rover**

For a 750 kg agricultural rover with wheelbase 2.0 m and track width 1.5 m:

```
L_x = 1.0 m (half of 2.0 m wheelbase)
L_y = 0.75 m (half of 1.5 m track width)

Transformation matrix M:
M = [1  -1  -1.75]
    [1   1   1.75]
    [1   1  -1.75]
    [1  -1   1.75]

Wheel velocities: ω = M × [v_x, v_y, ω_z]ᵀ
```

**Motor Torque Requirements**

The required motor torque for each wheel considering the rover's mass:

```
τ_i = (m/4) × r × α_i + μ × (m/4) × g × r + I_w × α_i

where:
  τ_i = torque for wheel i (N·m)
  m = 750 kg (rover mass)
  r = 0.4 m (wheel radius)
  α_i = angular acceleration of wheel i (rad/s²)
  μ = 0.05 (rolling resistance coefficient)
  g = 9.81 m/s²
  I_w = 0.5 × m_w × r² (wheel inertia, m_w = 15 kg per wheel)
```

**Velocity Normalization and Saturation**

To prevent wheel saturation with high-inertia loads:

```
ω_max = min(τ_max / (r × F_max), v_max / r)

where:
  τ_max = 20 N·m (motor torque limit)
  F_max = μ × (m/4) × g = 0.05 × 187.5 × 9.81 ≈ 92 N
  v_max = 2.0 m/s (maximum chassis velocity)

Normalization factor: k = min(1, ω_max / max(|ω_i|))
Normalized velocities: ω_i' = k × ω_i
```

**Power Distribution Optimization**

For efficient power use with heavy payloads:

```
P_total = Σ(τ_i × ω_i)
P_max = 4 × V_batt × I_max × η

where:
  V_batt = 48V (battery voltage)
  I_max = 50A (motor current limit)
  η = 0.85 (motor efficiency)

Optimization constraint: P_total ≤ P_max ≈ 8160W
```

### C++ Implementation

### Mecanum Mixing Matrix Implementation (AP_MotorsUGV_Mecanum.cpp)

The `AP_MotorsUGV_Mecanum` class implements the 4×3 transformation matrix for omnidirectional control. The `MecanumConfig` struct stores geometric parameters specific to the heavy agricultural rover.

**Matrix Transformation Implementation:**

```cpp
// Mecanum mixing matrix for 45° wheel configuration
Matrix4x3f _mixing_matrix = {
    { 1.0f, -1.0f, -(_config.lx + _config.ly) },  // Front-left
    { 1.0f,  1.0f,  (_config.lx + _config.ly) },  // Front-right
    { 1.0f,  1.0f, -(_config.lx + _config.ly) },  // Rear-left
    { 1.0f, -1.0f,  (_config.lx + _config.ly) }   // Rear-right
};

// Convert chassis velocities to wheel velocities
Vector4f wheel_velocities = _mixing_matrix * Vector3f(vx, vy, wz);
```

**Torque-Limited Velocity Calculation:**

```cpp
// Calculate required torque for each wheel
for (uint8_t i = 0; i < 4; i++) {
    // Angular acceleration: α = (ω_desired - ω_current) / Δt
    float alpha = (wheel_velocities[i] - _wheel_state[i].current_velocity) / dt;
    
    // Torque calculation: τ = (m/4)×r×α + μ×(m/4)×g×r + I_w×α
    float mass_term = (_vehicle_mass / 4.0f) * _wheel_radius * alpha;
    float friction_term = _rolling_coeff * (_vehicle_mass / 4.0f) * 9.81f * _wheel_radius;
    float inertia_term = _wheel_inertia * alpha;
    
    float required_torque = fabsf(mass_term + friction_term + inertia_term);
    
    // Check torque limits
    if (required_torque > _max_motor_torque) {
        // Scale down velocities to stay within torque limits
        float scale_factor = _max_motor_torque / required_torque;
        wheel_velocities[i] = _wheel_state[i].current_velocity + 
                             (wheel_velocities[i] - _wheel_state[i].current_velocity) * scale_factor;
    }
}
```

**Power-Constrained Normalization:**

```cpp
// Calculate total power requirement
float total_power = 0.0f;
for (uint8_t i = 0; i < 4; i++) {
    float current = _calculate_motor_current(wheel_velocities[i]);
    total_power += current * _battery_voltage;
}

// Normalize if exceeding maximum power
if (total_power > _max_power) {
    float power_scale = _max_power / total_power;
    for (uint8_t i = 0; i < 4; i++) {
        wheel_velocities[i] *= power_scale;
    }
}
```

**Wheel Velocity to PWM Conversion:**

```cpp
// Convert wheel velocity to PWM using motor model
uint16_t _velocity_to_pwm(uint8_t wheel_idx, float velocity) {
    // Motor model: V = K_v × ω + I × R
    float back_emf = _motor_kv * velocity;
    float required_voltage = back_emf + (_motor_resistance * _calculate_required_current(velocity));
    
    // Convert to PWM duty cycle
    float duty_cycle = required_voltage / _battery_voltage;
    duty_cycle = constrain_float(duty_cycle, 0.0f, 1.0f);
    
    // Convert to PWM microseconds (1000-2000μs range)
    uint16_t pwm = 1000 + (uint16_t)(duty_cycle * 1000);
    return pwm;
}
```

### Waypoint Navigation Integration (AR_WPNav.cpp)

The `AR_WPNav` class generates the desired chassis velocities that feed into the Mecanum mixing system, implementing path following algorithms optimized for omnidirectional motion.

**Desired Velocity Calculation for Omnidirectional Motion:**

```cpp
// Calculate desired velocity vector for Mecanum rover
Vector3f AR_WPNav::get_desired_velocity_omnidirectional() {
    // Get current position and target waypoint
    Vector3f current_pos = _inav.get_position();
    Vector3f target_pos = _get_current_waypoint();
    
    // Calculate position error
    Vector3f pos_error = target_pos - current_pos;
    
    // For omnidirectional motion, we can move directly toward target
    // without needing to align heading first
    Vector3f desired_velocity;
    
    // Proportional control with velocity limiting
    desired_velocity.x = _constrain_velocity(pos_error.x * _pos_p_gain, _max_velocity);
    desired_velocity.y = _constrain_velocity(pos_error.y * _pos_p_gain, _max_velocity);
    
    // Calculate desired yaw rate to face target (optional)
    float desired_yaw = atan2f(pos_error.y, pos_error.x);
    float yaw_error = wrap_PI(desired_yaw - _ahrs.yaw);
    desired_velocity.z = _constrain_velocity(yaw_error * _yaw_p_gain, _max_yaw_rate);
    
    return desired_velocity;
}
```

**Path Following with Cross-Track Error Correction:**

```cpp
// Calculate cross-track error for curved paths
Vector2f AR_WPNav::_calculate_cross_track_error_omnidirectional(const Vector3f &current_pos) {
    // Get path segment (line between previous and current waypoint)
    Vector3f path_start = _get_previous_waypoint();
    Vector3f path_end = _get_current_waypoint();
    
    // Vector from path start to current position
    Vector3f to_current = current_pos - path_start;
    
    // Path direction vector
    Vector3f path_dir = path_end - path_start;
    float path_length = path_dir.length();
    
    if (path_length < 0.1f) {
        return Vector2f(0, 0); // Path too short
    }
    
    // Project current position onto path
    float t = to_current.dot(path_dir) / (path_length * path_length);
    t = constrain_float(t, 0.0f, 1.0f);
    
    // Closest point on path
    Vector3f closest_point = path_start + path_dir * t;
    
    // Cross-track error vector (perpendicular to path)
    Vector3f cross_track_error = current_pos - closest_point;
    
    // Return lateral and vertical components (z is altitude)
    return Vector2f(cross_track_error.y, cross_track_error.z);
}
```

**Velocity Blending for Smooth Transitions:**

```cpp
// Blend between direct-to-target and path-following velocities
Vector3f AR_WPNav::_blend_omnidirectional_velocities(const Vector3f &direct_velocity,
                                                    const Vector2f &cross_track_error,
                                                    float distance_to_path) {
    Vector3f blended_velocity = direct_velocity;
    
    // Add cross-track correction when far from path
    if (distance_to_path > _cross_track_correction_distance) {
        // Proportional correction with limit
        float correction_gain = MIN(distance_to_path / _max_cross_track_distance, 1.0f);
        blended_velocity.y += cross_track_error.x * _cross_track_p_gain * correction_gain;
        
        // Optional altitude correction
        blended_velocity.z += cross_track_error.y * _altitude_p_gain * correction_gain;
    }
    
    // Limit total velocity magnitude
    float velocity_mag = blended_velocity.xy().length();
    if (velocity_mag > _max_velocity) {
        float scale = _max_velocity / velocity_mag;
        blended_velocity.x *= scale;
        blended_velocity.y *= scale;
    }
    
    return blended_velocity;
}
```

### RTOS Integration and Real-Time Execution

**400Hz Control Loop Implementation:**

```cpp
void AP_MotorsUGV_Mecanum::update() {
    uint32_t now_us = AP_HAL::micros();
    float dt = (now_us - _last_update_us) * 1e-6f;
    
    // Get desired chassis velocities from waypoint navigation
    Vector3f desired_velocity = _wpnav->get_desired_velocity_omnidirectional();
    
    // Apply Mecanum transformation: ω = M × [v_x, v_y, ω_z]ᵀ
    Vector4f wheel_velocities = _mixing_matrix * desired_velocity;
    
    // Apply torque and power constraints for heavy rover
    _apply_dynamic_constraints(wheel_velocities, dt);
    
    // Convert to PWM and output to all four wheels
    for (uint8_t i = 0; i < 4; i++) {
        uint16_t pwm = _velocity_to_pwm(i, wheel_velocities[i]);
        _write_pwm(i, pwm);
    }
    
    _last_update_us = now_us;
}
```

**Hardware PWM Configuration for Mecanum Wheels:**

```cpp
// STM32 Timer configuration for four Mecanum wheel motors
void AP_MotorsUGV_Mecanum::_init_mecanum_pwm() {
    // TIM1 for motors 1-2, TIM2 for motors 3-4
    // Configure for 20kHz PWM (torque control)
    
    // TIM1 Configuration (Motors 1-2)
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
    TIM1->PSC = 0;                      // No prescaler
    TIM1->ARR = 4199;                   // 84MHz/4200 = 20kHz
    TIM1->CCMR1 = TIM_CCMR1_OC1M_2 |    // PWM mode 1 for CH1
                  TIM_CCMR1_OC1M_1 |
                  TIM_CCMR1_OC2M_2 |    // PWM mode 1 for CH2
                  TIM_CCMR1_OC2M_1;
    TIM1->CCER = TIM_CCER_CC1E |        // Enable CH1
                 TIM_CCER_CC2E;         // Enable CH2
    TIM1->BDTR = TIM_BDTR_MOE;          // Main output enable
    TIM1->CR1 = TIM_CR1_CEN;
    
    // TIM2 Configuration (Motors 3-4)
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    TIM2->PSC = 0;
    TIM2->ARR = 4199;
    TIM2->CCMR1 = TIM_CCMR1_OC1M_2 | TIM_CCMR1_OC1M_1;
    TIM2->CCMR2 = TIM_CCMR2_OC3M_2 | TIM_CCMR2_OC3M_1;
    TIM2->CCER = TIM_CCER_CC1E | TIM_CCER_CC3E;
    TIM2->CR1 = TIM_CR1_CEN;
}
```

**Dynamic Constraint Application for Heavy Rover:**

```cpp
void AP_MotorsUGV_Mecanum::_apply_dynamic_constraints(Vector4f &velocities, float dt) {
    // 1. Torque constraints for 750 kg rover
    _apply_torque_constraints(velocities, dt);
    
    // 2. Power constraints (max ~8 kW for four motors)
    _apply_power_constraints(velocities);
    
    // 3. Velocity constraints (mechanical limits)
    _apply_velocity_constraints(velocities);
    
    // 4. Acceleration constraints for stability
    _apply_acceleration_constraints(velocities, dt);
    
    // 5. Load distribution for uneven terrain
    _apply_load_distribution(velocities);
}
```

**Performance Monitoring and Adaptive Control:**

```cpp
struct MecanumPerformance {
    float wheel_slip[4];           // Wheel slip ratios
    float power_distribution[4];   // Power distribution per wheel
    float efficiency;              // Overall system efficiency
    float load_balance;            // Load balance metric (0-1)
};

void AP_MotorsUGV_Mecanum::_update_performance_metrics() {
    // Calculate wheel slip: slip = (ω × r - v_actual) / max(ω × r, v_actual)
    for (uint8_t i = 0; i < 4; i++) {
        float wheel_speed = _wheel_state[i].current_velocity * _wheel_radius;
        float chassis_speed = _get_chassis_speed();
        _performance.wheel_slip[i] = fabsf(wheel_speed - chassis_speed) / 
                                    MAX(wheel_speed, chassis_speed);
    }
    
    // Adaptive mixing for slippery conditions
    if (_performance.wheel_slip[0] > 0.1f || _performance.wheel_slip[1] > 0.1f) {
        _adjust_mixing_for_slip();
    }
    
    // Update efficiency metric
    float total_power = 0.0f;
    float useful_power = 0.0f;
    for (uint8_t i = 0; i < 4; i++) {
        total_power += _motor_power[i];
        useful_power += _wheel_state[i].current_velocity * _wheel_torque[i];
    }
    _performance.efficiency = (total_power > 0) ? useful_power / total_power : 0.0f;
}
```

**Waypoint Navigation Timing and Coordination:**

```cpp
// AR_WPNav update at 100Hz, synchronized with 400Hz motor control
void AR_WPNav::update() {
    uint32_t now_ms = AP_HAL::millis();
    float dt = (now_ms - _last_update_ms) * 0.001f;
    
    // Update position and velocity estimates
    _update_position_estimate();
    
    // Calculate desired velocity for omnidirectional motion
    Vector3f desired_velocity = get_desired_velocity_omnidirectional();
    
    // Apply smoothing filter (first-order low-pass)
    _filtered_velocity = _filtered_velocity * 0.7f + desired_velocity * 0.3f;
    
    // Update waypoint state machine
    _update_waypoint_state();
    
    // Check for waypoint completion
    if (_check_waypoint_reached()) {
        _advance_to_next_waypoint();
    }
    
    _last_update_ms = now_ms;
}
```

The C++ implementation directly maps the mathematical matrix transformations to efficient linear algebra operations. The 4×3 mixing matrix in `AP_MotorsUGV_Mecanum.cpp` converts desired chassis velocities from `AR_WPNav.cpp` to individual wheel velocities, with dynamic constraints applied for the heavy agricultural rover's mass (750 kg) and inertia (300 kg·m²). The system operates at 400Hz with torque, power, and velocity constraints ensuring stable omnidirectional motion while managing significant power requirements (up to 8 kW). The waypoint navigation system generates smooth velocity profiles that leverage the Mecanum rover's holonomic capabilities, enabling direct movement toward targets without preliminary heading alignment. Real-time performance monitoring enables adaptive control for varying terrain conditions and payload distributions, maintaining precision while accommodating the unique dynamics of omnidirectional skid-steer motion.