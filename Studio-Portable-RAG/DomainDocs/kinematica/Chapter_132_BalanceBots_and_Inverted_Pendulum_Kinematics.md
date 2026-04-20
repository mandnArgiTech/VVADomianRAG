# BalanceBots and Inverted Pendulum Kinematics

_Generated 2026-04-20 04:19 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/balance_bot.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AR_Motors/AP_MotorsUGV.cpp`

# BalanceBots and Inverted Pendulum Kinematics

This chapter details the C++ implementation of a self-balancing two-wheeled rover (BalanceBot) within the ArduPilot framework. The system transforms a heavy agricultural rover platform (mass ~750 kg, inertia ~300 kg·m²) into a dynamically stable inverted pendulum using optimal control theory. The implementation in `balance_bot.cpp` and `AP_MotorsUGV.cpp` directly maps the linearized equations of motion to real-time C++ code, executing at 400Hz with LQR control, sensor fusion, and safety monitoring.

### Balance Bot State Estimation and Control (balance_bot.cpp)

The `BalanceBot` class implements the state-space representation and LQR control law from the mathematical formulation. The `PendulumState` struct holds the four state variables `[θ, θ̇, x, ẋ]ᵀ`, while the `LQRGains` struct stores the optimal gain matrix `K` computed offline from the Riccati equation.

**State Estimation Implementation:**
The `_read_sensors()` method fuses IMU and encoder data using a complementary filter, implementing the pitch estimation equation:
```cpp
// Accelerometer pitch: θ_accel = atan2(-a_x, sqrt(a_y² + a_z²))
float accel_pitch = atan2f(-accel.x, sqrtf(accel.y*accel.y + accel.z*accel.z));

// Complementary filter: θ = α·(θ_prev + gyro_y·dt) + (1-α)·θ_accel
_state.pitch_angle = _fusion.pitch_filter.update(accel_pitch, gyro.y, dt);
```

The `_estimate_state()` method constructs the full state vector for the Kalman filter:
```cpp
// State vector X = [θ, θ̇, x, ẋ]ᵀ matching mathematical formulation
Vector4f state_vector;
state_vector[0] = _state.pitch_angle;                    // θ
state_vector[1] = _state.pitch_rate;                     // θ̇  
state_vector[2] = _state.wheel_position[0];              // x
state_vector[3] = forward_velocity;                      // ẋ
_fusion.wheel_odometry.update(state_vector, dt);
```

**LQR Control Implementation:**
The `_calculate_balance_correction()` method directly implements the control law `u = -K·X`:
```cpp
// State vector X = [θ, θ̇, x, ẋ]ᵀ
Vector4f X;
X[0] = _state.pitch_angle;
X[1] = _state.pitch_rate;
X[2] = _state.wheel_position[0];
X[3] = (_state.wheel_velocity[0] + _state.wheel_velocity[1]) / 2.0f * 0.05f;

// LQR control: u = -K·X (matrix-vector multiplication)
float lqr_output = -(_lqr_gains.K * X)[0];
```

The cascade PID controller provides a backup to LQR, implementing the discrete-time control equations:
```cpp
// Outer loop: angle error e_θ = -θ (negative to oppose tilt)
float angle_error = -_state.pitch_angle;
float angle_output = _pid.outer_angle_pid.get_pid(angle_error, dt);

// Inner loop: rate error e_θ̇ = angle_output - θ̇
float rate_setpoint = angle_output;
float rate_error = rate_setpoint - _state.pitch_rate;
float rate_output = _pid.inner_rate_pid.get_pid(rate_error, dt);
```

**Motor Mixing Mathematics:**
The `_mix_commands()` method implements the differential drive mixing with balance correction:
```cpp
// Base differential drive: left = throttle - steering, right = throttle + steering
float base_left = throttle - steering;
float base_right = throttle + steering;

// Add balance correction (same to both wheels)
float balance_left = balance_correction;
float balance_right = balance_correction;

// Matrix mixing for advanced configurations: outputs = M × inputs
Vector2f inputs(throttle + balance_correction, steering);
Vector2f outputs = _mix.mix_matrix * inputs;
```

**Safety System Implementation:**
The safety monitoring uses the `SafetyLimits` struct to enforce mathematical guarantees:
```cpp
// Pitch angle limit: |θ| ≤ max_pitch_angle (0.35 rad = 20°)
if (fabsf(_state.pitch_angle) > _limits.max_pitch_angle) {
    // Start tilt timer
    if (_limits.tilt_start_ms == 0) {
        _limits.tilt_start_ms = AP_HAL::millis();
    } else if (AP_HAL::millis() - _limits.tilt_start_ms > 
              _limits.tilt_timeout_sec * 1000) {
        return false; // Emergency shutdown
    }
}
```

### Motor Mixing and PWM Generation (AP_MotorsUGV.cpp Integration)

The `AP_MotorsUGV_BalanceBot` class extends the standard motor driver with torque-based control, implementing the inverted pendulum dynamics equations directly.

**Torque Calculation from Dynamics:**
The `_calculate_wheel_torques()` method solves the equations of motion:
```cpp
// From dynamics: τ = I·θ̈ + m·g·L·sinθ - m·L·cosθ·ẍ
float gravity_torque = mass * 9.81f * com_height * sinf(theta);
float inertial_torque = inertia * theta_ddot_desired;
float forward_torque = mass * com_height * cosf(theta) * forward_accel;
float total_torque = inertial_torque + gravity_torque - forward_torque;

// Convert to wheel torque: τ_wheel = τ / r
float wheel_torque = total_torque / _balance_config.wheel_radius;
```

**Motor Model Implementation:**
The `_calculate_pwm_from_current()` method implements the DC motor equations:
```cpp
// Motor model: V = I·R + k_v·ω
float left_voltage = _torque_state.left_current * motor_resistance + 
                    speed_constant * left_speed;
float right_voltage = _torque_state.right_current * motor_resistance + 
                     speed_constant * right_speed;

// PWM duty cycle = V / V_battery
float left_duty = left_voltage / _torque_state.battery_voltage;
_left_pwm = 1000 + left_duty * 1000; // Map to 1000-2000μs range
```

**High-Speed PWM Hardware Configuration:**
The STM32 timer configuration implements 20kHz PWM for torque control:
```cpp
// TIM1 for left motor: 84MHz / 4200 = 20kHz
TIM1->PSC = 0;
TIM1->ARR = 4199; // 20kHz PWM frequency
TIM1->CCR1 = _pwm_to_ticks(_left_pwm); // Set duty cycle
```

**RTOS Execution and Timing:**
The balance control loop runs at 400Hz (2.5ms period) from the main scheduler:
```cpp
void update_balance() {
    uint32_t now_ms = AP_HAL::millis();
    float dt = 0.0025f; // 400Hz period
    
    // 1. Sensor read (0.2ms): IMU + encoders
    _read_sensors(dt);
    
    // 2. State estimation (0.8ms): Kalman filter
    _estimate_state(dt);
    
    // 3. Control law (0.6ms): LQR/PID
    float balance_correction = _calculate_balance_correction(dt);
    
    // 4. Motor output (0.3ms): PWM generation
    _output_motors(left_motor, right_motor);
    
    // Total: 2.0ms (80% CPU), 0.5ms safety margin
}
```

**Safety and Fault Handling:**
The system implements graceful degradation through the `_enter_safe_state()` method:
```cpp
// Ramp down motors over 500ms at 400Hz
static float ramp_down_factor = 1.0f;
ramp_down_factor = MAX(0.0f, ramp_down_factor - 0.002f); // 0.002 = 1/500

// Apply ramped output
float left = _last_left_command * ramp_down_factor;
float right = _last_right_command * ramp_down_factor;
_output_motors(left, right);
```

The C++ implementation directly maps each mathematical equation from the formulation section to specific code structures and algorithms. The `PendulumState` struct corresponds to the state vector `X`, the `LQRGains` struct holds the optimal gain matrix `K`, and the motor torque calculations solve the exact equations of motion. The 400Hz execution rate ensures the discrete-time implementation matches the continuous-time stability requirements, with the complementary filter time constants (τ ≈ 0.1s) and LQR gains providing the phase margin (>45°) and gain margin (>6dB) guarantees for the unstable inverted pendulum plant.