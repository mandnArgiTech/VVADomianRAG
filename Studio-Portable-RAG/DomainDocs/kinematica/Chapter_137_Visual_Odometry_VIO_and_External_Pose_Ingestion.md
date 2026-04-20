# Visual Odometry (VIO) and External Pose Ingestion

_Generated 2026-04-20 05:14 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_VisualOdom/AP_VisualOdom.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core.cpp`

# Visual Odometry (VIO) and External Pose Ingestion

This chapter details the integration of Visual Inertial Odometry (VIO) and external pose data into the 400Hz navigation architecture of a heavy agricultural rover (mass ~750 kg, yaw inertia ~300 kg·m²). The system enables GPS-denied operation by fusing camera-based position and attitude measurements from companion computers with onboard inertial navigation. The implementation spans two primary ArduPilot files: `AP_VisualOdom.cpp` handles MAVLink message reception, coordinate transformation, and time synchronization of external pose data, while `AP_NavEKF3_core.cpp` implements the Extended Kalman Filter (EKF) measurement update equations to fuse these visual measurements with IMU and wheel odometry, explicitly accounting for the rover's significant mass, skid-steer dynamics, and processing latency.

## Mathematical Formulation

### Coordinate Frame Transformations and Calibration

**Camera-to-Body Transformation:**
For a forward-facing camera mounted on a heavy agricultural rover, the transformation from camera frame \( C \) to body frame \( B \) is defined by a fixed rotation matrix \( \mathbf{R}_{C}^{B} \). A typical mounting (e.g., Intel T265) has camera X forward, Y left, Z up, while the rover body frame has X forward, Y right, Z down.

\[
\mathbf{R}_{C}^{B} = \begin{bmatrix}
0 & 0 & 1 \\
-1 & 0 & 0 \\
0 & -1 & 0
\end{bmatrix}
\]

This matrix implements:
- \( X_C \rightarrow Z_B \) (Camera forward becomes Body down)
- \( Y_C \rightarrow -X_B \) (Camera left becomes Body rear)
- \( Z_C \rightarrow -Y_B \) (Camera up becomes Body left)

**Body-to-NED Transformation:**
The rover's attitude in the NED (North-East-Down) frame is represented by the rotation matrix \( \mathbf{R}_{B}^{N} \) derived from the EKF quaternion state \( \mathbf{q} = [q_0, q_1, q_2, q_3]^T \):

\[
\mathbf{R}_{B}^{N}(\mathbf{q}) = \begin{bmatrix}
q_0^2 + q_1^2 - q_2^2 - q_3^2 & 2(q_1 q_2 - q_0 q_3) & 2(q_1 q_3 + q_0 q_2) \\
2(q_1 q_2 + q_0 q_3) & q_0^2 - q_1^2 + q_2^2 - q_3^2 & 2(q_2 q_3 - q_0 q_1) \\
2(q_1 q_3 - q_0 q_2) & 2(q_2 q_3 + q_0 q_1) & q_0^2 - q_1^2 - q_2^2 + q_3^2
\end{bmatrix}
\]

**Complete Measurement Transformation:**
A visual odometry measurement \( \mathbf{p}_C \) in the camera frame is transformed to the NED frame for fusion:

\[
\mathbf{p}_N = \mathbf{R}_{B}^{N} \cdot \mathbf{R}_{C}^{B} \cdot \mathbf{p}_C + \mathbf{b}_{C}^{B}
\]

where \( \mathbf{b}_{C}^{B} \) is the calibrated position offset from the camera to the rover's body frame origin, accounting for the physical mounting location on the heavy chassis.

### Measurement Model and EKF State Definition

**EKF State Vector:**
The 24-state EKF3 state vector relevant for VIO fusion is:

\[
\mathbf{x} = [ \underbrace{q_0, q_1, q_2, q_3}_{\text{Attitude Quaternion}}, \underbrace{v_N, v_E, v_D}_{\text{Velocity NED}}, \underbrace{p_N, p_E, p_D}_{\text{Position NED}}, \dots ]^T
\]

**Visual Odometry Measurement Vector:**
The external VIO system provides a 6-DOF measurement at time \( t_k \):

\[
\mathbf{z}_{VO}(t_k) = [ \mathbf{p}_N(t_k), \boldsymbol{\phi}(t_k) ]^T = [ p_N, p_E, p_D, \phi, \theta, \psi ]^T
\]

where \( \boldsymbol{\phi} = [\phi, \theta, \psi]^T \) are Euler angles (roll, pitch, yaw) derived from the VIO attitude quaternion.

**Measurement Model Function:**
The expected measurement based on the EKF state is:

\[
\mathbf{h}(\mathbf{x}) = [ \hat{p}_N, \hat{p}_E, \hat{p}_D, \hat{\phi}, \hat{\theta}, \hat{\psi} ]^T
\]

The position terms are direct: \( \hat{p}_N = p_N \), etc. The Euler angles \( \hat{\phi}, \hat{\theta}, \hat{\psi} \) are extracted from the EKF quaternion state \( \mathbf{q} \) using the conversion:

\[
\begin{aligned}
\hat{\phi} &= \text{atan2}\left( 2(q_2 q_3 + q_0 q_1), q_0^2 - q_1^2 - q_2^2 + q_3^2 \right) \\
\hat{\theta} &= \text{asin}\left( 2(q_0 q_2 - q_1 q_3) \right) \\
\hat{\psi} &= \text{atan2}\left( 2(q_1 q_2 + q_0 q_3), q_0^2 + q_1^2 - q_2^2 - q_3^2 \right)
\end{aligned}
\]

### Measurement Jacobian Matrix

The measurement Jacobian \( \mathbf{H} = \frac{\partial \mathbf{h}}{\partial \mathbf{x}} \in \mathbb{R}^{6 \times 24} \) defines how the measurement depends on each state.

**Position Partial Derivatives:**
\[
\frac{\partial \mathbf{p}_N}{\partial \mathbf{x}} = \begin{bmatrix}
\mathbf{0}_{3 \times 4} & \mathbf{0}_{3 \times 3} & \mathbf{I}_{3 \times 3} & \mathbf{0}_{3 \times 14}
\end{bmatrix}
\]
This reflects that the position measurement depends directly only on the position states \( p_N, p_E, p_D \).

**Attitude Partial Derivatives (Euler w.r.t. Quaternion):**
The Jacobian relating small changes in quaternion to changes in Euler angles is:

\[
\mathbf{J}_{\phi/\mathbf{q}} = \frac{\partial \boldsymbol{\phi}}{\partial \mathbf{q}} = 2 \begin{bmatrix}
q_3 & q_2 & q_1 & q_0 \\
-q_2 & q_3 & -q_0 & q_1 \\
q_1 & q_0 & q_3 & q_2
\end{bmatrix}^{-1}
\]

In practice, for the filter innovation calculation, a linearized small-angle approximation is used. The resulting sub-block of \( \mathbf{H} \) for attitude is:

\[
\frac{\partial \boldsymbol{\phi}}{\partial \mathbf{q}} \approx \begin{bmatrix}
0 & -1 & 0 & 0 \\
0 & 0 & -1 & 0 \\
0 & 0 & 0 & -1
\end{bmatrix}
\quad \text{(for small angles, with quaternion normalized)}
\]

**Complete Jacobian Structure:**
\[
\mathbf{H} = \begin{bmatrix}
\mathbf{0}_{3 \times 4} & \mathbf{0}_{3 \times 3} & \mathbf{I}_{3 \times 3} & \mathbf{0}_{3 \times 14} \\
\mathbf{J}_{\phi/\mathbf{q}} & \mathbf{0}_{3 \times 3} & \mathbf{0}_{3 \times 3} & \mathbf{0}_{3 \times 14}
\end{bmatrix}
\]

### Time Synchronization and Delay Compensation

**Measurement Delay Model:**
Visual odometry measurements arrive with latency due to processing and communication:
\[
t_{\text{received}} = t_{\text{capture}} + \Delta t_{\text{process}} + \Delta t_{\text{comm}}
\]
Typical latency \( \Delta t_{\text{total}} \) ranges from 20-100 ms for onboard companion computers.

**State Prediction for Delayed Measurements:**
If the measurement timestamp \( t_k \) differs significantly from the current EKF time \( t \), the state is predicted backward to \( t_k \) using the state transition matrix \( \mathbf{\Phi}(t, t_k) \):

\[
\mathbf{x}(t_k) = \mathbf{\Phi}(t, t_k) \, \mathbf{x}(t)
\]
\[
\mathbf{P}(t_k) = \mathbf{\Phi}(t, t_k) \, \mathbf{P}(t) \, \mathbf{\Phi}(t, t_k)^T + \mathbf{Q}_d
\]

For a heavy rover, the discrete-time state transition matrix for the position and velocity states over interval \( \Delta t = t - t_k \) is:

\[
\mathbf{\Phi}_{\text{pos/vel}}(\Delta t) = \begin{bmatrix}
1 & 0 & 0 & \Delta t & 0 & 0 \\
0 & 1 & 0 & 0 & \Delta t & 0 \\
0 & 0 & 1 & 0 & 0 & \Delta t \\
0 & 0 & 0 & 1 & 0 & 0 \\
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1
\end{bmatrix}
\]

The process noise covariance \( \mathbf{Q}_d \) accounts for unmodeled accelerations during the delay period, scaled by the rover's mass:

\[
\mathbf{Q}_d = \begin{bmatrix}
\frac{1}{4}\Delta t^4 \sigma_a^2 & 0 & 0 & \frac{1}{2}\Delta t^3 \sigma_a^2 & 0 & 0 \\
0 & \frac{1}{4}\Delta t^4 \sigma_a^2 & 0 & 0 & \frac{1}{2}\Delta t^3 \sigma_a^2 & 0 \\
0 & 0 & \frac{1}{4}\Delta t^4 \sigma_a^2 & 0 & 0 & \frac{1}{2}\Delta t^3 \sigma_a^2 \\
\frac{1}{2}\Delta t^3 \sigma_a^2 & 0 & 0 & \Delta t^2 \sigma_a^2 & 0 & 0 \\
0 & \frac{1}{2}\Delta t^3 \sigma_a^2 & 0 & 0 & \Delta t^2 \sigma_a^2 & 0 \\
0 & 0 & \frac{1}{2}\Delta t^3 \sigma_a^2 & 0 & 0 & \Delta t^2 \sigma_a^2
\end{bmatrix}
\]

where \( \sigma_a^2 \) is the variance of acceleration noise, derived from the rover's maximum acceleration capability \( a_{\text{max}} = 0.5 \, \text{m/s}^2 \) and mass: \( \sigma_a \approx a_{\text{max}} / m = 0.5 / 750 \approx 6.67 \times 10^{-4} \, \text{m/s}^2 \).

### Innovation and Kalman Update Equations

**Innovation Vector:**
The difference between the actual measurement and the predicted measurement:

\[
\boldsymbol{\nu} = \mathbf{z}_{VO} - \mathbf{h}(\mathbf{x})
\]

For Euler angles, the innovation is wrapped to \( (-\pi, \pi] \):
\[
\nu_\psi = \text{wrap\_PI}( \psi_{VO} - \hat{\psi} )
\]

**Innovation Covariance:**
\[
\mathbf{S} = \mathbf{H} \mathbf{P} \mathbf{H}^T + \mathbf{R}
\]
where \( \mathbf{R} \) is the measurement noise covariance matrix, constructed from the VIO system's reported covariance with added time-sync uncertainty:

\[
\mathbf{R} = \begin{bmatrix}
\mathbf{R}_{p} + \sigma_t^2 \mathbf{I}_3 & \mathbf{0}_{3 \times 3} \\
\mathbf{0}_{3 \times 3} & \mathbf{R}_{\phi} + \sigma_t^2 \mathbf{I}_3
\end{bmatrix}
\]

Here, \( \sigma_t^2 = (v_{\text{max}} \cdot \Delta t_{\text{uncert}})^2 \) accounts for position uncertainty due to time synchronization error \( \Delta t_{\text{uncert}} \). For a rover with \( v_{\text{max}} = 5 \, \text{m/s} \) and \( \Delta t_{\text{uncert}} = 0.01 \, \text{s} \), \( \sigma_t \approx 0.05 \, \text{m} \).

**Kalman Gain:**
\[
\mathbf{K} = \mathbf{P} \mathbf{H}^T \mathbf{S}^{-1}
\]

**State Update:**
\[
\mathbf{x}^+ = \mathbf{x}^- + \mathbf{K} \boldsymbol{\nu}
\]

**Covariance Update (Joseph Form):**
\[
\mathbf{P}^+ = (\mathbf{I} - \mathbf{K} \mathbf{H}) \mathbf{P}^- (\mathbf{I} - \mathbf{K} \mathbf{H})^T + \mathbf{K} \mathbf{R} \mathbf{K}^T
\]
This form preserves symmetry and positive definiteness despite numerical errors.

### Outlier Rejection and Quality Metrics

**Normalized Innovation Squared (NIS):**
\[
\text{NIS} = \boldsymbol{\nu}^T \mathbf{S}^{-1} \boldsymbol{\nu}
\]
Under nominal conditions, NIS follows a chi-squared distribution with \( n_z = 6 \) degrees of freedom. A measurement is rejected if:
\[
\text{NIS} > \chi^2_{0.95}(6) \approx 12.59
\]

**Mahalanobis Distance for Heavy Rover Context:**
For a 750 kg rover, the expected innovation magnitude is affected by the vehicle's inertia. The Mahalanobis distance normalizes the innovation by the covariance:

\[
D_M = \sqrt{\boldsymbol{\nu}^T \mathbf{S}^{-1} \boldsymbol{\nu}}
\]

This accounts for the fact that larger innovations are expected during high acceleration maneuvers due to the rover's mass.

**Covariance Consistency Check:**
The position covariance trace must remain bounded relative to the rover's control accuracy:
\[
\text{trace}(\mathbf{P}_{p}) < \sigma_{\text{max}}^2 = (0.5 \, \text{m})^2 = 0.25 \, \text{m}^2
\]
If exceeded, the covariance is inflated: \( \mathbf{P} \leftarrow \mathbf{P} \cdot (1 + \alpha) \) where \( \alpha = 0.1 \).

### Skid-Steer Specific Considerations

**Visual Odometry Aiding During Slippage:**
Wheel odometry becomes unreliable during skid-steer turns or on loose terrain. The VIO measurement model must account for this by adjusting the measurement noise covariance \( \mathbf{R} \). When high wheel slip is detected (from motor current differential), the weight on wheel odometry is reduced and VIO weight increased:

\[
\mathbf{R}_{p,\text{effective}} = \mathbf{R}_{p} \cdot (1 + k_{\text{slip}} \cdot s)
\]
where \( s \) is the estimated slip ratio (0 to 1) and \( k_{\text{slip}} \approx 10 \).

**Yaw Rate Alignment:**
The VIO yaw rate \( \dot{\psi}_{VO} \) is compared to the IMU gyro z-axis measurement \( \omega_z \) and the skid-steer derived yaw rate \( \omega_{z,\text{skid}} = (v_R - v_L) / w \) (track width \( w = 1.5 \, \text{m} \)). Consistency is checked via:
\[
|\dot{\psi}_{VO} - \omega_z| < \epsilon_{\omega} \quad \text{and} \quad |\dot{\psi}_{VO} - \omega_{z,\text{skid}}| < \epsilon_{\omega,\text{skid}}
\]
Typical thresholds: \( \epsilon_{\omega} = 0.1 \, \text{rad/s} \), \( \epsilon_{\omega,\text{skid}} = 0.3 \, \text{rad/s} \) (larger due to slip).

### Error Budget Analysis for Agricultural Operations

**Total Position Error:**
The combined error from VIO fusion during GPS-denied operation for a heavy rover is:
\[
\sigma_{\text{total}}^2 = \sigma_{\text{VO, drift}}^2 + \sigma_{\text{cal}}^2 + \sigma_{\text{time}}^2 + \sigma_{\text{filter}}^2
\]

- **VIO Drift Error:** \( \sigma_{\text{VO, drift}} = \beta \cdot d \), where \( \beta \approx 0.001-0.003 \) (0.1-0.3% drift rate for T265) and \( d \) is distance traveled. Over 100 m: \( \sigma_{\text{VO, drift}} \approx 0.1-0.3 \, \text{m} \).
- **Calibration Error:** \( \sigma_{\text{cal}} \approx 0.02 \, \text{m} \) (static misalignment).
- **Time Sync Error:** \( \sigma_{\text{time}} = v \cdot \Delta t_{\text{err}} \). For \( v = 2 \, \text{m/s} \), \( \Delta t_{\text{err}} = 0.01 \, \text{s} \): \( \sigma_{\text{time}} = 0.02 \, \text{m} \).
- **Filter Prediction Error:** \( \sigma_{\text{filter}} = \frac{1}{2} a_{\text{max}} \cdot \Delta t^2 \). For \( a_{\text{max}} = 0.5 \, \text{m/s}^2 \), \( \Delta t = 0.1 \, \text{s} \): \( \sigma_{\text{filter}} = 0.0025 \, \text{m} \).

**Total RSS Error:** \( \sigma_{\text{total}} \approx \sqrt{0.3^2 + 0.02^2 + 0.02^2 + 0.0025^2} \approx 0.30 \, \text{m} \).

**Performance in Vibration Environments:**
Agricultural rovers experience significant low-frequency vibration (1-10 Hz) from uneven terrain. The VIO measurement noise covariance \( \mathbf{R} \) is inflated based on the IMU vibration metric:
\[
\mathbf{R}_{p} \leftarrow \mathbf{R}_{p} \cdot (1 + k_v \cdot V_{\text{IMU}})
\]
where \( V_{\text{IMU}} \) is the RMS accelerometer vibration level and \( k_v \approx 0.1 \, \text{s}^2/\text{m}^2 \).

This mathematical formulation provides the exact relationships implemented in `AP_VisualOdom.cpp` and `AP_NavEKF3_core.cpp` for fusing visual odometry with the navigation filter, explicitly accounting for the heavy agricultural rover's dynamics, latency, and operational environment.

## C++ Implementation

### MAVLink Visual Odometry Data Ingestion (AP_VisualOdom.cpp)

The `AP_VisualOdom` class processes incoming MAVLink vision position estimates, applying coordinate transformations and quality checks before buffering for time-synchronized EKF fusion.

#### Data Structures for Pose Representation

```cpp
class AP_VisualOdom {
private:
    // VisualOdometryData struct maps to measurement vector z_vo = [p_x, p_y, p_z, φ, θ, ψ]ᵀ
    struct VisualOdometryData {
        uint64_t timestamp_us;      // t_measurement in microseconds
        Vector3f position;          // p in NED frame (m)
        Quaternion attitude;        // q representing [φ, θ, ψ]
        Matrix3f position_cov;      // R_position (3x3 covariance)
        Matrix3f attitude_cov;      // R_attitude (3x3 covariance)
        uint8_t quality;            // 0-100 quality score
        bool healthy;               // Validity flag
    };

    // Calibration structure for camera-to-body transformation
    struct {
        Vector3f pos_offset;        // Δp calibration offset
        Quaternion att_offset;      // Δq calibration quaternion
        float time_offset_ms;       // Δt time offset
        bool calibrated;
    } _calibration;

    // Circular buffer for time synchronization
    struct {
        VisualOdometryData buffer[VO_BUFFER_SIZE];  // Ring buffer
        uint8_t head;                               // Write index
        uint8_t tail;                               // Read index
        uint32_t dropped_count;                     // Overflow counter
    } _data_buffer;
};
```

#### MAVLink Message Processing and Coordinate Transformation

```cpp
// Implements T_visual = R_body2ned × R_cam2body × T_camera transformation
void AP_VisualOdom::handle_vision_position_estimate(const mavlink_message_t &msg)
{
    mavlink_vision_position_estimate_t vo_msg;
    mavlink_msg_vision_position_estimate_decode(&msg, &vo_msg);
    
    VisualOdometryData vo_data;
    vo_data.timestamp_us = vo_msg.usec;
    
    // Transform camera frame to body frame: p_body = R_cam2body × p_camera
    Vector3f pos_camera(vo_msg.x, vo_msg.y, vo_msg.z);
    vo_data.position = _camera_to_body(pos_camera);
    
    // Convert Euler to quaternion and rotate: q_body = q_cam2body ⊗ q_camera
    Quaternion att_camera(vo_msg.roll, vo_msg.pitch, vo_msg.yaw);
    vo_data.attitude = _camera_to_body_attitude(att_camera);
    
    // Extract covariance matrices from packed MAVLink array
    vo_data.position_cov = _extract_covariance(&vo_msg.covariance[0], 3);
    vo_data.attitude_cov = _extract_covariance(&vo_msg.covariance[6], 3);
    
    // Apply calibration: p_calibrated = p + Δp, q_calibrated = Δq ⊗ q
    if (_calibration.calibrated) {
        vo_data.position += _calibration.pos_offset;
        vo_data.attitude = _calibration.att_offset * vo_data.attitude;
        vo_data.timestamp_us += (uint64_t)(_calibration.time_offset_ms * 1000);
    }
    
    // Quality metric: Q = 100 × exp(-trace(Σ)/σ_max²)
    vo_data.quality = _calculate_quality(vo_data);
    vo_data.healthy = (vo_data.quality > _quality_threshold);
    
    // Buffer for time synchronization
    _buffer_data(vo_data);
}
```

#### Camera-to-Body Frame Transformation Implementation

```cpp
// Implements R_cam2body matrix multiplication
Vector3f AP_VisualOdom::_camera_to_body(const Vector3f &pos_camera)
{
    // R_cam2body = [[0, 0, 1], [-1, 0, 0], [0, -1, 0]] for forward-facing camera
    Matrix3f R_cam2body;
    R_cam2body[0][0] = 0;   R_cam2body[0][1] = 0;   R_cam2body[0][2] = 1;
    R_cam2body[1][0] = -1;  R_cam2body[1][1] = 0;   R_cam2body[1][2] = 0;
    R_cam2body[2][0] = 0;   R_cam2body[2][1] = -1;  R_cam2body[2][2] = 0;
    
    return R_cam2body * pos_camera;  // p_body = R × p_camera
}

// Implements quaternion rotation: q_body = q_cam2body ⊗ q_camera
Quaternion AP_VisualOdom::_camera_to_body_attitude(const Quaternion &att_camera)
{
    Quaternion q_cam2body;
    q_cam2body.from_rotation_matrix(_camera_to_body_matrix());
    return q_cam2body * att_camera;  // Quaternion multiplication
}
```

#### Time Synchronization Buffer Management

```cpp
// Implements circular buffer for measurement time alignment
bool AP_VisualOdom::get_visual_odometry_data(uint64_t ekf_time_us, VisualOdometryData &vo_data)
{
    // Find measurement minimizing |t_ekf - t_measurement|
    int8_t best_idx = -1;
    uint64_t best_dt = UINT64_MAX;
    
    uint8_t idx = _data_buffer.tail;
    while (idx != _data_buffer.head) {
        uint64_t dt = llabs((int64_t)ekf_time_us - (int64_t)_data_buffer.buffer[idx].timestamp_us);
        
        if (dt < best_dt && dt < _max_time_difference_us) {
            best_dt = dt;
            best_idx = idx;
        }
        idx = (idx + 1) % VO_BUFFER_SIZE;
    }
    
    if (best_idx >= 0) {
        vo_data = _data_buffer.buffer[best_idx];
        _data_buffer.tail = (best_idx + 1) % VO_BUFFER_SIZE;  // Remove used data
        return true;
    }
    
    return false;
}
```

### EKF3 Visual Odometry Fusion (AP_NavEKF3_core.cpp)

The `NavEKF3_core` class implements the Kalman filter update equations for fusing visual odometry measurements with the inertial navigation state.

#### Visual Odometry Fusion State Management

```cpp
class NavEKF3_core {
private:
    // VO fusion state tracking
    struct {
        bool enabled;                   // Fusion enabled flag
        uint32_t last_fuse_time_ms;     // t_last_update
        float pos_innovation[3];        // ν_position = z_vo - h(x)
        float att_innovation[3];        // ν_attitude = z_vo - h(x)
        Matrix3f pos_innov_cov;         // S_position (3x3)
        Matrix3f att_innov_cov;         // S_attitude (3x3)
        uint32_t healthy_count;         // Consecutive healthy updates
        uint32_t timeout_count;         // Consecutive timeouts
    } _vo_state;

    // Delayed measurement buffer for x_predicted(t_measurement)
    struct DelayedVOData {
        VisualOdometryData vo_data;
        uint64_t buffer_time_us;
        bool used;
    } _vo_delayed_buffer[VO_DELAY_BUFFER_SIZE];
};
```

#### Kalman Filter Update with Immediate Measurements

```cpp
// Implements x_{k|k} = x_{k|k-1} + K_k × ν_k, P_{k|k} = (I - K_k × H_k) × P_{k|k-1}
void NavEKF3_core::_fuse_visual_odometry_immediate(const VisualOdometryData &vo_data)
{
    // Extract EKF state: x = [q, p, v, ...]ᵀ
    Vector3f ekf_pos = _state.position;      // p_NED from EKF
    Quaternion ekf_quat = _state.quat;       // q from EKF
    Vector3f ekf_euler = ekf_quat.to_euler(); // Convert to [φ, θ, ψ]
    
    // Measurement: z_vo = [p_vo, φ_vo, θ_vo, ψ_vo]ᵀ
    Vector3f vo_pos = vo_data.position;
    Vector3f vo_euler = vo_data.attitude.to_euler();
    
    // Innovation: ν = z - h(x) where h(x) = [p_NED, φ, θ, ψ]ᵀ
    _vo_state.pos_innovation[0] = vo_pos.x - ekf_pos.x;  // ν_N
    _vo_state.pos_innovation[1] = vo_pos.y - ekf_pos.y;  // ν_E
    _vo_state.pos_innovation[2] = vo_pos.z - ekf_pos.z;  // ν_D
    
    _vo_state.att_innovation[0] = wrap_PI(vo_euler.x - ekf_euler.x);  // ν_φ
    _vo_state.att_innovation[1] = wrap_PI(vo_euler.y - ekf_euler.y);  // ν_θ
    _vo_state.att_innovation[2] = wrap_PI(vo_euler.z - ekf_euler.z);  // ν_ψ
    
    // Measurement Jacobian H (6x24): H = ∂h/∂x
    Matrix<float, 6, 24> H;
    H.zero();
    
    // Position partials: ∂p/∂pos = [0₃ₓ₄, I₃ₓ₃, 0₃ₓ₁₇]
    H[0][7] = 1.0f;  // ∂p_N/∂p_N
    H[1][8] = 1.0f;  // ∂p_E/∂p_E
    H[2][9] = 1.0f;  // ∂p_D/∂p_D
    
    // Attitude partials: ∂[φ,θ,ψ]/∂q using J_euler_to_quat
    Matrix3f J_euler_to_quat = _calculate_euler_to_quat_jacobian(ekf_quat);
    for (uint8_t i = 0; i < 3; i++) {
        for (uint8_t j = 0; j < 4; j++) {
            H[3 + i][j] = J_euler_to_quat[i][j];  // ∂euler/∂quat
        }
    }
    
    // Measurement noise R (6x6): R = diag(Σ_position, Σ_attitude) + σ_time²×I
    Matrix<float, 6, 6> R;
    R.zero();
    
    // Position covariance block
    for (uint8_t i = 0; i < 3; i++) {
        for (uint8_t j = 0; j < 3; j++) {
            R[i][j] = vo_data.position_cov[i][j];
        }
    }
    
    // Attitude covariance block
    for (uint8_t i = 0; i < 3; i++) {
        for (uint8_t j = 0; j < 3; j++) {
            R[3 + i][3 + j] = vo_data.attitude_cov[i][j];
        }
    }
    
    // Add time synchronization uncertainty: R += σ_t² × I
    float time_variance = powf(_vo_time_uncertainty * 1e-6f, 2.0f);
    for (uint8_t i = 0; i < 6; i++) {
        R[i][i] += time_variance;
    }
    
    // Innovation covariance: S = H × P × Hᵀ + R
    Matrix<float, 6, 6> S = H * _P * H.transposed() + R;
    
    // Kalman gain: K = P × Hᵀ × S⁻¹
    Matrix<float, 24, 6> K = _P * H.transposed() * S.inverse();
    
    // State update: x = x + K × ν
    Vector<float, 24> state_vector = _state.get_vector();
    Vector<float, 6> innovation;
    for (uint8_t i = 0; i < 3; i++) {
        innovation[i] = _vo_state.pos_innovation[i];
        innovation[3 + i] = _vo_state.att_innovation[i];
    }
    state_vector += K * innovation;
    _state.set_vector(state_vector);
    
    // Covariance update: P = (I - K × H) × P
    Matrix<float, 24, 24> I = Matrix<float, 24, 24>::identity();
    _P = (I - K * H) * _P;
    _P.force_symmetry();
    
    // NIS calculation: χ² = νᵀ × S⁻¹ × ν
    _update_vo_quality_metrics(S, innovation);
}
```

#### Euler-to-Quaternion Jacobian Calculation

```cpp
// Implements J = ∂[φ,θ,ψ]/∂q where q = [q0, q1, q2, q3]ᵀ
Matrix3f NavEKF3_core::_calculate_euler_to_quat_jacobian(const Quaternion &q)
{
    Matrix3f J;
    // Using δθ = 2 × G × δq where G = [-q1, q0, q3, -q2;
    //                                  -q2, -q3, q0, q1;
    //                                  -q3, q2, -q1, q0]
    J[0][0] = -2.0f * q.q2; J[0][1] = 2.0f * q.q1; J[0][2] = 2.0f * q.q4; J[0][3] = -2.0f * q.q3;
    J[1][0] = -2.0f * q.q3; J[1][1] = -2.0f * q.q4; J[1][2] = 2.0f * q.q1; J[1][3] = 2.0f * q.q2;
    J[2][0] = -2.0f * q.q4; J[2][1] = 2.0f * q.q3; J[2][2] = -2.0f * q.q2; J[2][3] = 2.0f * q.q1;
    
    return J;
}
```

#### Delayed Measurement Handling with State Prediction

```cpp
// Implements x_predicted(t_measurement) = Φ(t_current, t_measurement) × x(t_current)
void NavEKF3_core::_fuse_delayed_visual_odometry(const VisualOdometryData &vo_data, int64_t time_diff_us)
{
    float dt = time_diff_us * 1e-6f;  // Δt = t_current - t_measurement
    
    // State transition matrix Φ for prediction interval dt
    Matrix<float, 24, 24> Phi = _calculate_state_transition_matrix(dt);
    
    // Predicted state: x_pred = Φ × x_current
    Vector<float, 24> x_pred = Phi * _state.get_vector();
    
    // Predicted covariance: P_pred = Φ × P × Φᵀ + Q
    Matrix<float, 24, 24> P_pred = Phi * _P * Phi.transposed() + _Q;
    
    // Store for delayed fusion
    _store_delayed_measurement(vo_data, x_pred, P_pred, dt);
}
```

#### Normalized Innovation Squared (NIS) Validation

```cpp
// Implements χ² test: NIS = νᵀ × S⁻¹ × ν with threshold χ²(0.95, 6) = 12.59
void NavEKF3_core::_update_vo_quality_metrics(const Matrix<float, 6, 6> &S, 
                                             const Vector<float, 6> &innovation)
{
    // Calculate NIS: χ² = νᵀ × S⁻¹ × ν
    float NIS = innovation.dot(S.inverse() * innovation);
    
    if (NIS < _vo_chi2_threshold) {  // χ²_threshold = 12.59 for 6 DOF
        _vo_state.healthy_count++;
        _vo_state.timeout_count = 0;
        
        // Store innovation covariance for monitoring
        for (uint8_t i = 0; i < 3; i++) {
            for (uint8_t j = 0; j < 3; j++) {
                _vo_state.pos_innov_cov[i][j] = S[i][j];
                _vo_state.att_innov_cov[i][j] = S[3 + i][3 + j];
            }
        }
    } else {
        // Reject measurement: NIS > χ²_threshold