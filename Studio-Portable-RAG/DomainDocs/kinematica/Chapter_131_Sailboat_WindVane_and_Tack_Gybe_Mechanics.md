# Autonomous Sailboats, WindVane Telemetry, and Tack/Gybe Mechanics

_Generated 2026-04-20 04:13 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/sailboat.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_WindVane/AP_WindVane.cpp`

# Autonomous Sailboats, WindVane Telemetry, and Tack/Gybe Mechanics

This chapter details the implementation of autonomous wind-powered navigation within the ArduPilot framework, focusing on two core files: `AP_WindVane.cpp` and `sailboat.cpp`. These modules transform a heavy agricultural rover platform (mass 750 kg, inertia 300 kg·m²) into a capable autonomous sailboat by implementing real-time wind triangle mathematics, sail aerodynamic force models, and state machines for tack/gybe maneuvers. The system maintains the deterministic 400Hz architecture while adapting to the unique constraints of wind propulsion, replacing wheel traction with sail lift and accounting for hydrodynamic forces.

### Wind Vector Calculation and Calibration (AP_WindVane.cpp)

The `AP_WindVane` class implements the vector wind triangle mathematics through direct translation of the coordinate transformation equations into C++ matrix operations. The `update_wind_estimate()` method executes the fundamental wind triangle equation `VT = VA - VB` (True Wind = Apparent Wind - Boat Velocity) at 10Hz, using sensor data from the wind vane and anemometer.

**Mathematical Implementation in C++:**

The code directly maps to the wind triangle formulation through these key operations:

```cpp
// Wind triangle equation: VT = VA - VB
Vector2f true_wind_ned = apparent_wind_ned - boat_velocity_ned;

// Apparent wind in body frame (implements: VA_x = -|VA| × cos(ψ_A), VA_y = -|VA| × sin(ψ_A))
Vector2f apparent_wind_body;
apparent_wind_body.x = -filtered_speed * cosf(apparent_dir_body);
apparent_wind_body.y = -filtered_speed * sinf(apparent_dir_body);

// Body to NED rotation matrix (implements R_b2n = [[cosψ, -sinψ], [sinψ, cosψ]])
Matrix2f R_body_to_ned;
R_body_to_ned.a.x = cosf(boat_heading);
R_body_to_ned.a.y = -sinf(boat_heading);
R_body_to_ned.b.x = sinf(boat_heading);
R_body_to_ned.b.y = cosf(boat_heading);

// Transform apparent wind to NED frame: VA_ned = R_b2n × VA_body
Vector2f apparent_wind_ned = R_body_to_ned * apparent_wind_body;

// Boat velocity from GPS (implements: VB_north = V_gps × cos(ψ_boat), VB_east = V_gps × sin(ψ_boat))
Vector2f boat_velocity_ned(boat_speed * cosf(boat_heading),
                          boat_speed * sinf(boat_heading));
```

**Sensor Calibration and Filtering:**

The `Calibration` struct stores correction parameters that implement the mathematical corrections for sensor misalignment. The low-pass filtering implements the mathematical formulation `VT_filtered[n] = α × VT_raw[n] + (1-α) × VT_filtered[n-1]` using ArduPilot's `LowPassFilter2p` class:

```cpp
// Apply correction matrix for sensor misalignment (2x2 matrix multiplication)
Vector2f corrected_apparent = _calibration.correction_matrix * _wind_state.apparent_wind_ned;

// Recalculate true wind with corrected apparent wind
_wind_state.true_wind_ned = corrected_apparent - boat_velocity_ned;

// Low-pass filtering implementation (1Hz cutoff for direction, 2Hz for speed)
float filtered_direction = _filters.direction_filter.apply(corrected_direction);
float filtered_speed = _filters.speed_filter.apply(corrected_speed);
```

**Hardware Interface Implementation:**

The wind vane analog input uses STM32 ADC registers to implement voltage-to-direction conversion, while the anemometer uses TIM3 input capture for frequency measurement:

```cpp
// Voltage to direction conversion: direction = (voltage / voltage_range) × 2π
float direction = (voltage / _sensors.vane_voltage_range) * 2.0f * M_PI;

// ADC read implementation (12-bit resolution, 3.3V reference)
uint16_t adc_value = ADC1->DR;
float voltage = (adc_value / 4095.0f) * 3.3f;

// Anemometer frequency to speed conversion: speed = frequency_hz / calibration_factor
uint32_t period_ticks = capture2 - capture1;
float period_us = period_ticks * (1.0f / 84.0f);  // 84MHz timer
float frequency_hz = 1e6f / period_us;
float speed = frequency_hz / _anemometer_calibration_factor;
```

### Sailboat State Machine and Sail Control (sailboat.cpp)

The `Sailboat` class extends the standard `Rover` class with sail-specific control logic, implementing the tacking decision mathematics through a deterministic state machine. The system runs at the rover's native 400Hz frequency but with sail-specific overrides to the motor commands.

**Sail Trim Optimization Implementation:**

The `_calculate_optimal_trim()` method implements the mathematical sail trim curves through piecewise linear functions:

```cpp
// For upwind sailing (wind angle 30-90°): trim_factor = 1.0f - (|apparent_wind_angle| / (π/2))
if (fabsf(apparent_wind_angle) < M_PI/2) {
    float trim_factor = 1.0f - (fabsf(apparent_wind_angle) / (M_PI/2));
    _sail.sail_trim_optimal = _trim_upwind_min + trim_factor * (_trim_upwind_max - _trim_upwind_min);
} 
// For downwind sailing: trim_factor = downwind_angle / (π/2)
else {
    float downwind_angle = fabsf(apparent_wind_angle) - M_PI/2;
    float trim_factor = downwind_angle / (M_PI/2);
    _sail.sail_trim_optimal = _trim_downwind_min + trim_factor * (_trim_downwind_max - _trim_downwind_min);
}
```

**Tacking State Machine Mathematics:**

The tacking logic implements the optimal tacking angle mathematics through the `_calculate_tack_angle()` method:

```cpp
// Port tack option: port_tack_heading = wind_direction - optimal_upwind_angle
float port_tack_heading = wind_direction - _wind_nav.optimal_upwind_angle;

// Starboard tack option: starboard_tack_heading = wind_direction + optimal_upwind_angle
float starboard_tack_heading = wind_direction + _wind_nav.optimal_upwind_angle;

// Choose tack that minimizes heading error: argmin(|desired_course - tack_heading|)
float port_error = fabsf(wrap_PI(desired_course - port_tack_heading));
float starboard_error = fabsf(wrap_PI(desired_course - starboard_tack_heading));

if (port_error < starboard_error) {
    return port_tack_heading;
} else {
    return starboard_tack_heading;
}
```

**Sail Force Aerodynamic Model:**

The `_calculate_sail_force()` method implements the aerodynamic lift and drag equations directly:

```cpp
// Dynamic pressure: q = 0.5 × ρ × VA²
float q = 0.5f * 1.225f * apparent_wind_speed * apparent_wind_speed;

// Effective sail area (adjusted for reefing)
float A_effective = _sail_area_reference * _sail.sail_area_factor;

// Lift force: FL = q × CL(α) × A
float FL = q * CL * A_effective;

// Drag force: FD = q × CD(α) × A
float FD = q * CD * A_effective;

// Project onto boat forward direction: forward_force = FL × sin(ψ_A) - FD × cos(ψ_A)
float forward_force = FL * sinf(apparent_wind_angle) - FD * cosf(apparent_wind_angle);
```

The lift coefficient calculation implements the mathematical piecewise function:

```cpp
// Lift coefficient piecewise function (matches mathematical formulation)
float alpha_deg = fabsf(alpha * 180.0f / M_PI);

if (alpha_deg < 15.0f) {
    return 0.8f * (alpha_deg / 15.0f);  // Linear increase to 0.8 at 15°
} else if (alpha_deg < 45.0f) {
    return 0.8f + 0.2f * ((alpha_deg - 15.0f) / 30.0f);  // Increase to 1.0 at 45°
} else {
    // Stall region: decrease from 1.0 to 0.5 at 90°
    return 1.0f - 0.5f * ((alpha_deg - 45.0f) / 45.0f);
}
```

**Motor-Sail Hybrid Control Implementation:**

For the high-mass rover, motor assist provides additional torque during tacking maneuvers:

```cpp
// Blend sail and motor power: total_throttle = sail_force + motor_throttle × motor_assist_gain
if (_motor_sail.motor_assist_enabled) {
    float total_throttle = sail_force + _motor_sail.motor_assist_throttle * _motor_assist_gain;
    _motors.set_throttle(total_throttle);
} else {
    // Pure sail power - zero throttle to motors
    _motors.set_throttle(0.0f);
}
```

**Leeway Correction Implementation:**

The system implements sideslip compensation based on sail force:

```cpp
// Leeway angle: leeway_angle = sail_force × leeway_coefficient
float leeway_angle = sail_force * _leeway_coefficient;
leeway_angle = constrain_float(leeway_angle, -_max_leeway_angle, _max_leeway_angle);

// Apply as rudder correction: corrected_steering = current_steering - leeway_angle
float corrected_steering = current_steering - leeway_angle;
_motors.set_steering(corrected_steering);
```

**Sail Servo PWM Generation:**

The sail control system converts trim angles to PWM signals using the rover's existing servo infrastructure:

```cpp
// Convert sail trim angle to servo PWM: 1500μs center ±500μs for full travel
float normalized_trim = _sail.sail_trim_current / _max_sail_angle;
normalized_trim = constrain_float(normalized_trim, -1.0f, 1.0f);
_sail.sail_servo_pwm = 1500 + (uint16_t)(normalized_trim * 500.0f);

// Write to servo output using STM32 TIM2
_write_servo_pwm(SAIL_SERVO_CHANNEL, _sail.sail_servo_pwm);
```

**RTOS Execution and Timing:**

The sailboat control system maintains the rover's 400Hz main loop while adding wind-specific processing:
- Wind estimation updates at 10Hz (`AP_WindVane::update_wind_estimate()`)
- Sail trim calculation runs at 10Hz
- Tacking state machine executes at 10Hz with 30-second timeout protection
- Motor-sail blending occurs at 400Hz in the main control loop
- Sail servo updates at 50Hz (standard PWM refresh rate)

The state machine ensures deterministic behavior during tacking maneuvers, with the `TackingState` struct tracking progress and providing fallback to motor assist after three failed attempts. The system respects the rover's high inertia (300 kg·m²) through wider tacking angles and longer maneuver times compared to conventional sailboats.