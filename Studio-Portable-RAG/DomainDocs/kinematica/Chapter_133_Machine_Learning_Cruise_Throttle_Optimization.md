# Machine Learning and Cruise Throttle Optimization

_Generated 2026-04-20 04:27 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/cruise_learn.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/APM_Control/AR_AttitudeControl.cpp`

# Machine Learning and Cruise Throttle Optimization

This chapter details the C++ implementation of an onboard self-learning system for cruise throttle optimization within the ArduPilot framework. The system enables a heavy agricultural rover (mass ~750 kg) to autonomously adapt its throttle control to varying payloads, terrain conditions, and vehicle wear by implementing Recursive Least Squares (RLS) parameter estimation and physics-based longitudinal dynamics models. The implementation in `cruise_learn.cpp` and `AR_AttitudeControl.cpp` directly maps the mathematical formulations of vehicle dynamics to real-time adaptive control algorithms.

### Cruise Learning State Machine (cruise_learn.cpp)

The `CruiseLearn` class implements the RLS parameter estimation algorithm and vehicle dynamics model from the mathematical formulation. The `LearnState` struct contains the RLS parameters `theta = [K_T, F_offset]ᵀ` and covariance matrix `P`, while the `CircularBuffer` structures store time-series data for system identification.

**RLS Parameter Estimation Implementation:**
The `_update_rls_parameters()` method directly implements the RLS update equations:

```cpp
// Regression vector: φ = [throttle, 1]ᵀ (matches mathematical formulation)
Vector2f phi(throttle, 1.0f);

// Prediction error: e = v_measured - φᵀ·θ
float prediction = phi.dot(_state.theta);
float error = speed - prediction;

// Kalman gain: K = P × φ / (λ + φᵀ × P × φ)
Vector2f K = _state.P * phi;
float denominator = _state.lambda + phi.dot(K);
K /= denominator;

// Parameter update: θ = θ + K × e
_state.theta += K * error;

// Covariance update: P = (I - K × φᵀ) × P / λ
Matrix2f I = Matrix2f::identity();
Matrix2f K_phi_outer = K.outer_product(phi);
_state.P = (I - K_phi_outer) * _state.P / _state.lambda;
```

**Vehicle Dynamics Model Implementation:**
The `get_learned_throttle()` method solves the longitudinal dynamics equations:

```cpp
// Required force: F_required = m × a + F_resist (from F = ma + F_resist)
float F_required = _state.conditions.current_mass * desired_accel + F_resist;

// Throttle calculation: throttle = (F_required - F_offset) / K_T
float throttle = (F_required - _state.theta.y) / _state.theta.x;
```

The resistance force calculation implements the exact mathematical model:

```cpp
// Rolling resistance: F_roll = μ_roll × m × g × cos(θ)
float F_roll = _state.conditions.rolling_coeff * 
              _state.conditions.current_mass * 
              9.80665f * cosf(incline_angle);

// Aerodynamic drag: F_aero = 0.5 × ρ × C_d × A × v²
float F_aero = 0.5f * 1.225f * _state.conditions.aero_coeff * 
              speed * speed;

// Grade resistance: F_grade = m × g × sin(θ)
float F_grade = _state.conditions.current_mass * 9.80665f * 
               sinf(incline_angle);
```

**Mass Estimation Algorithm:**
The `_update_mass_estimation()` method implements Newton's second law:

```cpp
// Acceleration from finite difference: a = (v2 - v1) / Δt
float acceleration = (speed2 - speed1) / dt;

// Force from throttle model: F = K_T × throttle + F_offset
float force = _state.theta.x * throttle + _state.theta.y;

// Mass estimation: m = F / a (when |a| > threshold)
if (fabsf(acceleration) > 0.1f) {
    float mass_estimate = force / acceleration;
    // Low-pass filter for stability
    _state.conditions.current_mass = 
        _state.conditions.current_mass * (1.0f - alpha) + 
        mass_estimate * alpha;
}
```

**Rolling Resistance Estimation:**
The system identifies rolling resistance during constant-speed operation:

```cpp
// When acceleration ≈ 0: F_total = F_roll + F_aero
float F_total = _state.theta.x * avg_throttle + _state.theta.y;
float F_roll_est = F_total - F_aero;

// Rolling coefficient: μ_roll = F_roll / (m × g)
float mu_roll_est = F_roll_est / (_state.conditions.current_mass * 9.80665f);
```

### Attitude Control Integration (AR_AttitudeControl.cpp)

The `AR_AttitudeControl` class integrates the learned throttle model with the existing PID control system. The `ThrottleControl` struct manages the hybrid control approach, blending learned feedforward with PID feedback.

**Hybrid Control Implementation:**
The `update_speed_control()` method implements the learning-integrated control:

```cpp
// When learning is active: use learned throttle directly
if (learning_conditions && _throttle_control.learning_active) {
    float learned_throttle = _cruise_learner->get_learned_throttle(
        _throttle_control.desired_speed,
        _throttle_control.current_speed,
        _get_terrain_incline()
    );
    _throttle_control.throttle_output = learned_throttle;
} 
// Fallback: PID with learned feedforward
else {
    // Feedforward from learned model
    _throttle_control.throttle_feedforward = 
        _cruise_learner->get_learned_throttle(
            _throttle_control.desired_speed,
            _throttle_control.current_speed,
            _get_terrain_incline()
        );
    
    // PID feedback: u_fb = K_p × e + K_i × ∫e dt + K_d × de/dt
    _throttle_control.throttle_feedback = 
        _throttle_control.speed_pid.get_pid(speed_error, dt);
    
    // Total: u = u_ff + u_fb
    _throttle_control.throttle_output = 
        _throttle_control.throttle_feedforward + 
        _throttle_control.throttle_feedback;
}
```

**Learning Condition Monitoring:**
The system only updates learning parameters during suitable operating conditions:

```cpp
bool _check_learning_conditions() {
    // Need sufficient speed (> 0.1 m/s)
    if (_throttle_control.current_speed < 0.1f) return false;
    
    // Need stable GPS fix
    if (!_gps.status() >= AP_GPS::GPS_OK_FIX_3D) return false;
    
    // Limit acceleration during learning (< 2 m/s²)
    float acceleration = _inav.get_accel().length();
    if (acceleration > MAX_LEARNING_ACCEL) return false;
    
    // Limit incline during learning (< 15°)
    float incline = _get_terrain_incline();
    if (fabsf(incline) > MAX_LEARNING_INCLINE) return false;
    
    return true;
}
```

**Terrain Incline Estimation:**
The incline estimation uses altitude and distance measurements:

```cpp
float _get_terrain_incline() {
    // Incline = arctan(Δaltitude / Δdistance)
    float altitude_change = baro_alt - last_altitude;
    float distance_traveled = _inav.get_ground_speed() * 0.01f;
    
    if (distance_traveled > 0.1f) {
        float incline = atan2f(altitude_change, distance_traveled);
        return incline;
    }
    return 0.0f;
}
```

**Persistent Parameter Storage:**
The `PersistentParams` struct enables learning retention across power cycles:

```cpp
struct PersistentParams {
    float base_throttle_gain;   // K_T
    float base_throttle_offset; // F_offset
    float mass_estimate;        // m
    uint32_t learning_cycles;
    uint32_t crc32;             // Integrity check
} _persistent;
```

**Performance Monitoring:**
The system tracks learning convergence using covariance matrix analysis:

```cpp
// Confidence metric: confidence = 1 / (1 + trace(P))
float trace_P = _state.P.trace();
_state.stats.confidence = 1.0f / (1.0f + trace_P);

// RMS error tracking
_state.stats.speed_error_rms = sqrtf(
    (_state.stats.speed_error_rms * _state.stats.speed_error_rms * 
     (_state.stats.sample_count - 1) + error * error) / 
    _state.stats.sample_count
);
```

**RTOS Execution Profile:**
The learning system operates at 10Hz while the control loop runs at 100Hz:

```cpp
// CruiseLearn update (10Hz = 100ms period)
void update_learning(float throttle_cmd, float speed_target, 
                    float speed_actual, uint32_t timestamp_ms) {
    // RLS update: ~100 FLOPS
    _update_rls_parameters(dt);
    
    // Mass estimation: ~50 FLOPS  
    _update_mass_estimation();
    
    // Total: ~180 FLOPS per cycle
    // 10Hz × 180 FLOPS = 1,800 FLOPS average
}

// AttitudeControl update (100Hz = 10ms period)  
void update_speed_control(float dt) {
    // Throttle calculation: ~30 FLOPS
    float learned_throttle = _cruise_learner->get_learned_throttle(...);
    
    // PID update: ~20 FLOPS
    _throttle_control.speed_pid.get_pid(speed_error, dt);
    
    // Total: ~50 FLOPS per cycle
    // 100Hz × 50 FLOPS = 5,000 FLOPS average
}
```

**Memory Footprint:**
The complete learning system requires approximately 3.7KB of RAM:
- `CruiseLearn` class: ~2KB
- Circular buffers (100 samples × 4 floats): 1.6KB
- Persistent storage: 128 bytes

The C++ implementation directly maps each mathematical equation from the formulation section. The RLS algorithm updates `theta = [K_T, F_offset]ᵀ` using the exact matrix equations, the force calculations implement the longitudinal dynamics model, and the mass estimation uses Newton's second law. The hybrid control system blends learned feedforward with PID feedback, providing robust performance while continuously adapting to changing vehicle and environmental conditions. The 10Hz learning rate and 100Hz control rate ensure real-time performance within the 400Hz autonomous architecture while maintaining computational efficiency for embedded deployment.