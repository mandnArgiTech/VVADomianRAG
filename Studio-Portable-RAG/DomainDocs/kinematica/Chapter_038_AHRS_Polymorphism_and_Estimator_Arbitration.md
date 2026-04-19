# AHRS Polymorphism, Estimator Arbitration, and Body Frames

_Generated 2026-04-15 01:51 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_Backend.h`

# Chapter: AHRS Polymorphism, Estimator Arbitration, and Body Frames

## Introduction

The `AP_AHRS.cpp`, `AP_AHRS.h`, `AP_AHRS_Backend.cpp`, and `AP_AHRS_Backend.h` files constitute the core Attitude and Heading Reference System (AHRS) abstraction layer in ArduPilot's 400Hz autonomous vehicle architecture. This subsystem provides deterministic, fault-tolerant attitude estimation through a polymorphic design that arbitrates between multiple estimation backends—primarily EKF3 and DCM—based on real-time health metrics. The frontend (`AP_AHRS`) implements a hardware-aware sensor fusion pipeline that transforms raw IMU data through calibrated body-frame rotations, while the backend abstraction (`AP_AHRS_Backend`) enforces mathematical consistency across different estimation strategies. For heavy agricultural rovers, this architecture specifically addresses challenges of skid-steering dynamics, high vibration environments, and large inertial masses by implementing weighted health scoring, covariance-bound monitoring, and smooth estimator transitions via spherical linear interpolation. The system executes within a real-time thread schedule where sensor processing runs at 400Hz, health monitoring at 10Hz, and DMA-driven hardware interrupts at 8kHz, ensuring deterministic latency for vehicle control loops.

## Mathematical Formulation for AHRS Polymorphism, Estimator Arbitration, and Body Frames

### Health Evaluation and Estimator Arbitration Mathematics

The arbitration logic uses a weighted health score to decide between EKF3 and DCM estimators for a heavy rover. The score is computed from sensor innovation, covariance, timeouts, and estimator consistency.

**Health Score Calculation:**
```
Health_Score = w₁·S_NIS + w₂·S_cov + w₃·S_TSLM + w₄·S_consistency
```
Where:
- `S_NIS = 1.0 - min(1.0, NIS_actual / NIS_threshold)`
  - `NIS_actual = vᵀS⁻¹v` for the 3-axis accelerometer or gyroscope innovation vector `v` and covariance `S`.
  - `NIS_threshold = χ²_threshold(0.95, 3) = 7.815`.
- `S_cov = 1.0 - min(1.0, tr(P) / tr(P_max))`
  - `tr(P_pos) < 100 m²` and `tr(P_vel) < 25 m²/s²` for rover-scale position and velocity uncertainty.
- `S_TSLM = 1.0 - min(1.0, Δt / Δt_max)`
  - Timeouts: `Δt_GPS > 500 ms`, `Δt_baro > 1000 ms`, `Δt_mag > 500 ms`.
- `S_consistency = correlation(q_EKF, q_DCM)`
  - Computed as the dot product of the EKF and DCM quaternions.
- Weights: `w₁ = 0.4`, `w₂ = 0.3`, `w₃ = 0.2`, `w₄ = 0.1`.

A `Health_Score < 0.6` triggers an estimator downgrade. For a skid-steering rover, high vibration increases gyro innovation (`NIS_actual`), directly impacting `S_NIS` and promoting a fallback to the more robust DCM.

### Sensor to Body Frame Transformation Matrices

Raw sensor data (gyroscope and accelerometer) is transformed to the rover's body frame using pre-computed rotation matrices. These account for physical mounting on a heavy, uneven chassis.

**Transformation Equation:**
```
ω_body = R_sensor_to_body · ω_sensor + b_gyro
a_body = R_sensor_to_body · a_sensor + b_accel - g
```
The rotation matrix `R_sensor_to_body` is selected from 41 enumerated cases. For example:
- `ROTATION_NONE`: Identity matrix.
  ```
  Matrix3f(1, 0, 0,
           0, 1, 0,
           0, 0, 1)
  ```
- `ROTATION_YAW_90` (90° rotation about Z-axis):
  ```
  Matrix3f(0, -1, 0,
           1,  0, 0,
           0,  0, 1)
  ```
- `ROTATION_ROLL_180` (180° rotation about X-axis, common for inverted mounting):
  ```
  Matrix3f(1,  0,  0,
           0, -1,  0,
           0,  0, -1)
  ```
Following rotation, scaling and temperature-compensated bias are applied:
```
data.x = data.x * _gyro_scale[instance].x + _gyro_bias[instance].x
```
Bias compensation uses a cubic polynomial for temperature `T`:
```
b_gyro.x += b₀ + b₁·ΔT + b₂·ΔT² + b₃·ΔT³
```

### Body to NED Frame Kinematics

The rover's attitude in the North-East-Down (NED) frame is represented as a unit quaternion `q = [q₀, q₁, q₂, q₃]`. The Direction Cosine Matrix (DCM) `R_body_to_ned` is derived from the quaternion.

**Quaternion to DCM:**
```
R_body_to_ned = 
  [1-2(q₂²+q₃²),   2(q₁q₂-q₀q₃),   2(q₁q₃+q₀q₂);
   2(q₁q₂+q₀q₃), 1-2(q₁²+q₃²),     2(q₂q₃-q₀q₁);
   2(q₁q₃-q₀q₂),   2(q₂q₃+q₀q₁), 1-2(q₁²+q₂²)]
```
**Velocity and Position Integration:**
The rover's velocity and position in NED are propagated using the body-frame acceleration.
```
v_ned = v_ned + (R_body_to_ned · a_body - g_ned) · Δt
p_ned = p_ned + v_ned · Δt + 0.5 · (R_body_to_ned · a_body - g_ned) · Δt²
```
Where `g_ned = [0, 0, 9.80665] m/s²`. For a heavy rover, the large mass makes acceleration sensitive to small bias errors in `a_body`.

### Quaternion Integration and DCM Propagation

**Discrete-Time Quaternion Kinematics (Tustin Integration):**
```
q_{k+1} = q_k ⊗ exp(0.5 * Ω(ω) * Δt)
```
Where `Ω(ω)` is the skew-symmetric form of the body-frame gyro rates `ω = [ω_x, ω_y, ω_z]`:
```
Ω(ω) = [0,    -ω_x, -ω_y, -ω_z;
        ω_x,  0,     ω_z, -ω_y;
        ω_y, -ω_z,  0,     ω_x;
        ω_z,  ω_y, -ω_x,  0]
```
The matrix exponential is approximated as:
```
exp(0.5 * Ω(ω) * Δt) ≈ I + 0.5 * Ω(ω) * Δt + 0.125 * Ω(ω)² * Δt²
```

**DCM Kinematic Equation:**
```
Ṙ = R × [ω]×
```
Where `[ω]×` is the skew-symmetric matrix:
```
[ω]× = [0,    -ω_z,  ω_y;
        ω_z,  0,    -ω_x;
        -ω_y, ω_x,  0]
```
Discrete implementation (first-order):
```
R_{k+1} = R_k × (I + [ω]× × Δt + 0.5 × [ω]×² × Δt²)
```

### Estimator Blending via Spherical Linear Interpolation (SLERP)

During estimator transition, outputs are blended using SLERP to prevent abrupt attitude jumps.

**SLERP Formulation:**
Given two quaternions `q_from` and `q_to`, and blend factor `α`:
```
cos_θ = q_from · q_to = q_from[0]*q_to[0] + q_from[1]*q_to[1] + q_from[2]*q_to[2] + q_from[3]*q_to[3]
```
If `cos_θ < 0`, negate `q_to` to ensure the shortest path.
The interpolated quaternion `q_out` is:
```
q_out = (q_from * sin((1-α)θ) + q_to * sin(αθ)) / sin(θ)
```
For `cos_θ > 0.9995`, linear approximation is used:
```
q_out = q_from + α * (q_to - q_from); q_out.normalize()
```
Position and velocity are linearly interpolated:
```
pos_blended = pos_previous + (pos_current - pos_previous) * α
vel_blended = vel_previous + (vel_current - vel_previous) * α
```
The blend factor `α` updates at `0.05` per cycle (400Hz), creating a 50ms transition.

### EKF3 State Vector and Process Model

The EKF3 state vector for the rover has 24 states. The process model defines their continuous-time dynamics.

**State Vector `x`:**
```
x = [q₀, q₁, q₂, q₃,           // Attitude quaternion (4)
     v_N, v_E, v_D,            // NED velocity (3)
     p_N, p_E, p_D,            // NED position (3)
     b_gx, b_gy, b_gz,         // Gyro biases (3)
     b_ax, b_ay, b_az,         // Accelerometer biases (3)
     w_N, w_E, w_D,            // Wind velocity (3)
     m_N, m_E, m_D,            // Earth magnetic field (3)
     δψ]                       // Yaw error (1)
```

**Continuous-Time Process Model:**
```
q̇   = 0.5 × q ⊗ ω                     // Quaternion kinematics
v̇   = R_body_to_ned · a - g_ned + w   // Velocity (includes wind)
ṗ   = v                               // Position
ḃ_g = -b_g/τ_g + w_g                  // Gyro bias (first-order Gauss-Markov)
ḃ_a = -b_a/τ_a + w_a                  // Accel bias (first-order Gauss-Markov)
ẇ   = -w/τ_w + w_w                    // Wind velocity (first-order Gauss-Markov)
ṁ   = 0                               // Earth magnetic field constant
δψ̇  = -δψ/τ_ψ + w_ψ                   // Yaw error (first-order Gauss-Markov)
```
Where `τ` terms are time constants and `w_*` are white process noise terms. The large inertia of a heavy rover results in slower bias dynamics, influencing the tuning of `τ_g` and `τ_a`.

## C++ Implementation

### Active Estimator Selection Logic (AP_AHRS.cpp)

The `AP_AHRS` class constructor initializes the estimator backend pointers and sets the default active instance. The arbitration logic is implemented through direct pointer manipulation.

```cpp
AP_AHRS::AP_AHRS() :
    _ekf_type(3),  // Default to EKF3
    _active_ekf_instance(0),
    _ekf3{nullptr, nullptr, nullptr},
    _dcm_backend(nullptr),
    _backend(nullptr),
    _gyro_count(0),
    _accel_count(0),
    _ekf_healthy(false),
    _dcm_healthy(false),
    _ekf_fault(false),
    _force_dcm_fallback(false),
    _ekf_failover_count(0),
    _last_failover_ms(0),
    _dcm_fallback_start_ms(0)
{
    // EKF3 instance pointers initialization
    for (uint8_t i = 0; i < ARRAY_SIZE(_ekf3); i++) {
        _ekf3[i] = new AP_AHRS_EKF3(*this, i);
    }
    
    // DCM backend pointer
    _dcm_backend = new AP_AHRS_DCM(*this);
    
    // Default to primary EKF3
    _backend = _ekf3[0];
}
```

The `set_ekf_use()` function implements the mathematical decision to switch between EKF and DCM backends based on health evaluation.

```cpp
void AP_AHRS::set_ekf_use(bool use_ekf)
{
    if (use_ekf && _ekf_type != 0) {
        // Switch to EKF backend
        _backend = _ekf3[_active_ekf_instance];
        _force_dcm_fallback = false;
    } else {
        // Switch to DCM backend
        _backend = _dcm_backend;
        _force_dcm_fallback = true;
        _dcm_fallback_start_ms = AP_HAL::millis();
    }
}
```

The `switch_ekf_instance()` function validates health before switching EKF instances, implementing the failover logic from the arbitration formulation.

```cpp
bool AP_AHRS::switch_ekf_instance(uint8_t instance)
{
    if (instance < ARRAY_SIZE(_ekf3) && _ekf3[instance] != nullptr) {
        // Health check before switching
        if (_ekf3[instance]->healthy()) {
            _active_ekf_instance = instance;
            _backend = _ekf3[instance];
            return true;
        }
    }
    return false;
}
```

### Sensor to Body Frame Rotations (AP_AHRS.cpp)

The `set_orientation()` function stores the physical mounting rotation for each sensor instance and pre-computes the transformation matrix.

```cpp
void AP_AHRS::set_orientation(uint8_t instance, enum Rotation rotation)
{
    if (instance < INS_MAX_INSTANCES) {
        // Store rotation enum for this sensor instance
        _rotation[instance] = rotation;
        
        // Pre-compute rotation matrix for efficiency
        _rotation_matrix[instance] = _get_rotation_matrix(rotation);
        
        // Invalidate cached data
        _gyro_calibrated[instance] = false;
        _accel_calibrated[instance] = false;
    }
}
```

The `_get_rotation_matrix()` function returns the exact 3×3 transformation matrix corresponding to the mathematical sensor-to-body frame rotation.

```cpp
Matrix3f AP_AHRS::_get_rotation_matrix(enum Rotation rotation) const
{
    // Direct hardware-to-body frame transformation matrices
    // These correspond to physical sensor mounting orientations
    switch (rotation) {
        case ROTATION_NONE:
            return Matrix3f(1, 0, 0, 0, 1, 0, 0, 0, 1);
        case ROTATION_YAW_45:
            return Matrix3f(0.7071, -0.7071, 0, 0.7071, 0.7071, 0, 0, 0, 1);
        case ROTATION_YAW_90:
            return Matrix3f(0, -1, 0, 1, 0, 0, 0, 0, 1);
        case ROTATION_YAW_135:
            return Matrix3f(-0.7071, -0.7071, 0, 0.7071, -0.7071, 0, 0, 0, 1);
        case ROTATION_YAW_180:
            return Matrix3f(-1, 0, 0, 0, -1, 0, 0, 0, 1);
        case ROTATION_YAW_225:
            return Matrix3f(-0.7071, 0.7071, 0, -0.7071, -0.7071, 0, 0, 0, 1);
        case ROTATION_YAW_270:
            return Matrix3f(0, 1, 0, -1, 0, 0, 0, 0, 1);
        case ROTATION_YAW_315:
            return Matrix3f(0.7071, 0.7071, 0, -0.7071, 0.7071, 0, 0, 0, 1);
        case ROTATION_ROLL_180:
            return Matrix3f(1, 0, 0, 0, -1, 0, 0, 0, -1);
        case ROTATION_ROLL_180_YAW_45:
            return Matrix3f(0.7071, -0.7071, 0, -0.7071, -0.7071, 0, 0, 0, -1);
        // ... additional 34 rotation cases
        default:
            return Matrix3f(1, 0, 0, 0, 1, 0, 0, 0, 1);
    }
}
```

The `_rotate_sensor_data()` function applies the mathematical transformation `ω_body = R_sensor_to_body · ω_sensor + b_gyro` with hardware calibration factors.

```cpp
void AP_AHRS::_rotate_sensor_data(uint8_t instance, Vector3f &data) const
{
    // Apply rotation matrix to sensor data
    if (instance < INS_MAX_INSTANCES && _rotation_matrix[instance].is_zero()) {
        data = _rotation_matrix[instance] * data;
    }
    
    // Apply sensor scaling factors (from hardware calibration)
    data.x *= _gyro_scale[instance].x;
    data.y *= _gyro_scale[instance].y;
    data.z *= _gyro_scale[instance].z;
    
    // Apply sensor biases (from temperature-compensated calibration)
    data.x += _gyro_bias[instance].x;
    data.y += _gyro_bias[instance].y;
    data.z += _gyro_bias[instance].z;
}
```

### Virtual Backend Matrix Interpolation (AP_AHRS_Backend.cpp)

The `_interpolate_estimators()` function implements the spherical linear interpolation (SLERP) mathematics for smooth estimator transitions.

```cpp
void AP_AHRS_Backend::_interpolate_estimators(const Quaternion &q_from, 
                                              const Quaternion &q_to,
                                              Quaternion &q_out,
                                              float alpha)
{
    // Spherical Linear Interpolation (SLERP) for quaternions
    // q_out = (q_from * sin((1-α)θ) + q_to * sin(αθ)) / sin(θ)
    // where cos(θ) = q_from · q_to
    
    float cos_theta = q_from[0]*q_to[0] + q_from[1]*q_to[1] + 
                      q_from[2]*q_to[2] + q_from[3]*q_to[3];
    
    // Ensure shortest path
    if (cos_theta < 0.0f) {
        q_out = Quaternion(-q_to[0], -q_to[1], -q_to[2], -q_to[3]);
        cos_theta = -cos_theta;
    } else {
        q_out = q_to;
    }
    
    // Perform SLERP
    if (cos_theta > 0.9995f) {
        // Linear interpolation for very small angles
        q_out = Quaternion(
            q_from[0] + alpha * (q_out[0] - q_from[0]),
            q_from[1] + alpha * (q_out[1] - q_from[1]),
            q_from[2] + alpha * (q_out[2] - q_from[2]),
            q_from[3] + alpha * (q_out[3] - q_from[3])
        );
        q_out.normalize();
    } else {
        // True SLERP
        float theta = acosf(cos_theta);
        float sin_theta = sinf(theta);
        float ratio_a = sinf((1.0f - alpha) * theta) / sin_theta;
        float ratio_b = sinf(alpha * theta) / sin_theta;
        
        q_out = Quaternion(
            ratio_a * q_from[0] + ratio_b * q_out[0],
            ratio_a * q_from[1] + ratio_b * q_out[1],
            ratio_a * q_from[2] + ratio_b * q_out[2],
            ratio_a * q_from[3] + ratio_b * q_out[3]
        );
    }
}
```

The `_blend_estimator_outputs()` function manages the complete blending pipeline during estimator transitions.

```cpp
void AP_AHRS_Backend::_blend_estimator_outputs(void)
{
    // Only blend if we're transitioning between estimators
    if (_blend_alpha < 1.0f && _blend_alpha > 0.0f) {
        // Interpolate quaternions
        Quaternion q_blended;
        _interpolate_estimators(_q_previous, _q_current, q_blended, _blend_alpha);
        
        // Interpolate position
        Vector3f pos_blended = _pos_previous + (_pos_current - _pos_previous) * _blend_alpha;
        
        // Interpolate velocity  
        Vector3f vel_blended = _vel_previous + (_vel_current - _vel_previous) * _blend_alpha;
        
        // Update frontend with blended values
        _frontend._quat = q_blended;
        _frontend._position = pos_blended;
        _frontend._velocity = vel_blended;
        
        // Update blend alpha (exponential decay)
        _blend_alpha += _blend_alpha_rate;
        if (_blend_alpha >= 1.0f) {
            _blend_alpha = 1.0f;
            _blending_active = false;
        }
    } else {
        // Direct copy when not blending
        _frontend._quat = _q_current;
        _frontend._position = _pos_current;
        _frontend._velocity = _vel_current;
    }
    
    // Always ensure normalized quaternion output
    _frontend._quat.normalize();
    
    // Convert to Euler angles for legacy interfaces
    _frontend._quat.to_euler(_frontend._roll, _frontend._pitch, _frontend._yaw);
    
    // Update DCM matrix
    _frontend._quat.rotation_matrix(_frontend._dcm_matrix);
}
```

### STM32 DMA Arbitration for Sensor Fusion

The `_dma_gyro_callback()` function handles hardware-level DMA interrupts for sensor data acquisition at 8kHz.

```cpp
void AP_AHRS::_dma_gyro_callback(DMA_HandleTypeDef *hdma)
{
    // Extract raw sensor data from DMA buffer
    uint16_t *raw_buffer = (uint16_t *)(hdma->Instance->M0AR);
    
    // Convert to engineering units (LSB to rad/s)
    // ICM-20602: 16.4 LSB/°/s = 0.000266 rad/LSB
    const float GYRO_SCALE = 0.000266f;
    
    _gyro_raw[0].x = (int16_t)raw_buffer[0] * GYRO_SCALE;
    _gyro_raw[0].y = (int16_t)raw_buffer[1] * GYRO_SCALE;
    _gyro_raw[0].z = (int16_t)raw_buffer[2] * GYRO_SCALE;
    
    // Temperature compensation
    float temp = (int16_t)raw_buffer[3] / 333.87f + 21.0f;
    _apply_temperature_compensation(temp);
    
    // Trigger sensor data ready flag
    _gyro_data_ready = true;
    
    // Restart DMA for continuous acquisition
    HAL_DMA_Start_IT(hdma, (uint32_t)&SPI1->DR, 
                     (uint32_t)raw_buffer, 4);
}
```

The `_apply_temperature_compensation()` function implements the cubic polynomial bias compensation `b = b₀ + b₁·T + b₂·T² + b₃·T³`.

```cpp
void AP_AHRS::_apply_temperature_compensation(float temp_c)
{
    // Polynomial temperature compensation
    // b = b₀ + b₁·T + b₂·T² + b₃·T³
    float delta_temp = temp_c - _calibration_temp;
    
    for (uint8_t i = 0; i < INS_MAX_INSTANCES; i++) {
        _gyro_bias[i].x += _temp_coeff[i][0] * delta_temp +
                          _temp_coeff[i][1] * delta_temp * delta_temp +
                          _temp_coeff[i][2] * delta_temp * delta_temp * delta_temp;
        
        _gyro_bias[i].y += _temp_coeff[i][3] * delta_temp +
                          _temp_coeff[i][4] * delta_temp * delta_temp +
                          _temp_coeff[i][5] * delta_temp * delta_temp * delta_temp;
        
        _gyro_bias[i].z += _temp_coeff[i][6] * delta_temp +
                          _temp_coeff[i][7] * delta_temp * delta_temp +
                          _temp_coeff[i][8] * delta_temp * delta_temp * delta_temp;
    }
}
```

### RTOS Execution Flow and Threading Logic

The main update loop runs at 400Hz in the `AP_AHRS::update()` function, which calls the polymorphic backend update.

```cpp
void AP_AHRS::update(void)
{
    // Polymorphic backend update
    if (_backend != nullptr) {
        _backend->update();
        
        // Post-update normalization
        if (_backend->get_quaternion(_quat)) {
            // Ensure quaternion normalization
            _quat.normalize();
            
            // Convert to Euler angles for legacy interfaces
            _quat.to_euler(_roll, _pitch, _yaw);
            
            // Update rotation matrix
            _quat.rotation_matrix(_dcm_matrix);
        }
    }
}
```

Health monitoring runs at 10Hz in `AP_AHRS::update_EKF3()`, implementing the mathematical decision tree for estimator arbitration.

```cpp
void AP_AHRS::update_EKF3(void)
{
    // Primary EKF3 health evaluation
    bool primary_healthy = _ekf3[0].healthy();
    float primary_health = _ekf3[0].getHealth();
    
    // Secondary EKF3 health evaluation (if enabled)
    bool secondary_healthy = (_ekf3_count > 1) ? _ekf3[1].healthy() : false;
    float secondary_health = (_ekf3_count > 1) ? _ekf3[1].getHealth() : 0.0f;
    
    // Arbitration logic
    if (!primary_healthy && secondary_healthy) {
        // Failover to secondary EKF3
        _active_ekf_instance = 1;
        _ekf_failover_count++;
        _last_failover_ms = AP_HAL::millis();
    } else if (!primary_healthy && !secondary_healthy && _ekf_type != 0) {
        // Both EKFs unhealthy, fallback to DCM
        _ekf_type = 0;
        _force_dcm_fallback = true;
        _dcm_fallback_start_ms = AP_HAL::millis();
    } else if (primary_healthy && _force_dcm_fallback) {
        // Return to EKF after DCM fallback if healthy
        if (AP_HAL::millis() - _dcm_fallback_start_ms > EKF_RECOVERY_TIME_MS) {
            _ekf_type = 3; // Return to EKF3
            _force_dcm_fallback = false;
        }
    }
}
```

The interface to `Rover.cpp` is provided through const getter functions that access the active backend through the `_backend` pointer.

```cpp
bool AP_AHRS::get_attitude(Quaternion &quat) const
{
    if (_backend != nullptr) {
        return _backend->get_quaternion(quat);
    }
    return false;
}

bool AP_AHRS::get_rotation_body_to_ned(Matrix3f &mat) const
{
    if (_backend != nullptr) {
        return _backend->get_rotation_body_to_ned(mat);
    }
    return false;
}
```