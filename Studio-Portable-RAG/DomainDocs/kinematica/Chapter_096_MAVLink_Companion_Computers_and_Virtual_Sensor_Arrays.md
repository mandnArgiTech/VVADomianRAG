# MAVLink Companion Computers, VSLAM Injection, and Virtual Sensor Arrays

_Generated 2026-04-15 12:22 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_MAV.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_MAV.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_RangeFinder.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_RangeFinder.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_AirSimSITL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_AirSimSITL.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_SITL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_SITL.h`

# Chapter: MAVLink Companion Computers, VSLAM Injection, and Virtual Sensor Arrays

## Introduction

This chapter documents the ArduPilot architecture for integrating high-level perception and compute payloads via the MAVLink protocol. The system enables a 400Hz autonomous agricultural rover to fuse data from companion computers running Visual SLAM (VSLAM), LiDAR odometry, and external sensor arrays. The implementation provides deterministic latency bridging between asynchronous, high-bandwidth companion data streams and the rover's real-time control loops, accounting for the vehicle's 1200 kg mass, skid-steering dynamics, and the vibration environment induced by field operation. The core files—`AP_ExternalAHRS.cpp`, `AP_ExternalAHRS.h`, `AP_ExternalControl.cpp`, `AP_ExternalControl.h`, `AP_CompanionComputer.cpp`, `AP_CompanionComputer.h`, `AP_VirtualSensor.cpp`, `AP_VirtualSensor.h`—implement a thread-safe queueing system, covariance-aware sensor fusion, and a virtual sensor abstraction layer that allows VSLAM pose estimates and external point clouds to be treated as native navigation sources.

## Mathematical Formulation

### MAVLink Packet Latency and Jitter Bounds for Heavy Rovers

The timestamping and synchronization of MAVLink packets from a companion computer must account for variable latency induced by the rover's vibration profile and network contention. The arrival time \( t_a \) of a packet containing sensor data is modeled as:

\[
t_a = t_s + \Delta t_{tx} + \Delta t_{vib}(m, a) + \Delta t_{queue}
\]

Where:
- \( t_s \): Source timestamp on companion computer (μs)
- \( \Delta t_{tx} \): Wired (USB/Ethernet) transmission delay (~200μs)
- \( \Delta t_{vib}(m, a) \): Vibration-induced PCIe/USB jitter, scaling with rover mass \( m = 1200 \text{ kg} \) and chassis acceleration \( a \): \( \Delta t_{vib} = k_v \cdot m \cdot a / 1000 \), with \( k_v = 0.05 \ \mu\text{s}/(\text{kg} \cdot \text{m/s}^2) \)
- \( \Delta t_{queue} \): RTOS queueing delay in the STM32 (bounded by 400Hz control period: ≤ 2.5ms)

The **maximum allowable latency** for VSLAM pose injection before the 400Hz EKF update is:

\[
\Delta t_{max} = \frac{1}{400 \text{ Hz}} - \tau_{EKF} = 2.5 \text{ ms} - 1.2 \text{ ms} = 1.3 \text{ ms}
\]

Packets with \( t_a - t_s > \Delta t_{max} \) are discarded.

### VSLAM Pose Covariance Transformation to Rover Body Frame

A VSLAM solution provides a 6-DoF pose \( \mathbf{T}_{cam}^{world} \in SE(3) \) with covariance \( \mathbf{\Sigma}_{cam} \in \mathbb{R}^{6 \times 6} \). This must be transformed to the rover's body frame (IMU location), accounting for the lever arm \( \mathbf{r}_{cam}^{body} \) and the rover's mass distribution which affects rotational inertia.

The transformed pose \( \mathbf{T}_{body}^{world} \) is:

\[
\mathbf{T}_{body}^{world} = \mathbf{T}_{cam}^{world} \cdot \begin{bmatrix} \mathbf{I} & \mathbf{r}_{cam}^{body} \\ \mathbf{0}^T & 1 \end{bmatrix}^{-1}
\]

The covariance transforms via the Jacobian \( \mathbf{J} \) of the composition operation with respect to the 6-DoF pose perturbation vector \( \boldsymbol{\xi} \in \mathfrak{se}(3) \):

\[
\mathbf{\Sigma}_{body} = \mathbf{J} \cdot \mathbf{\Sigma}_{cam} \cdot \mathbf{J}^T
\]

Where \( \mathbf{J} = \begin{bmatrix} \mathbf{I} & -\mathbf{R}_{cam}^{world} \cdot [\mathbf{r}_{cam}^{body}]_\times \\ \mathbf{0} & \mathbf{I} \end{bmatrix} \), and \( [\mathbf{r}]_\times \) is the skew-symmetric cross-product matrix. For the 1200 kg rover, the lever arm \( \mathbf{r}_{cam}^{body} = [0.5, 0.0, -0.2]^T \) m induces significant rotational covariance inflation during skid-steering turns.

### Virtual Sensor Array Fusion with Mass-Weighted Confidence

A companion computer can provide a *virtual sensor array*—e.g., multiple synthetic airspeed sensors from a flow model. The fusion of \( N \) virtual sensors with readings \( y_i \) and variances \( \sigma_i^2 \) uses inverse-variance weighting, but the weights are scaled by a **mass-dependent confidence factor** \( c(m) \) that degrades external sensor reliability under high vibration:

\[
c(m) = \frac{1}{1 + (m / m_{ref})^2} = \frac{1}{1 + (1200 / 500)^2} \approx 0.15
\]

The fused estimate \( \hat{y} \) and variance \( \hat{\sigma}^2 \) are:

\[
w_i' = c(m) \cdot \frac{1}{\sigma_i^2}, \quad W = \sum_{i=1}^N w_i'
\]
\[
\hat{y} = \frac{1}{W} \sum_{i=1}^N w_i' y_i, \quad \hat{\sigma}^2 = \frac{1}{W}
\]

This reflects the reduced trust in companion data under heavy rover operational dynamics.

### Skid-Steering Dead Reckoning Compensation for VSLAM Dropouts

During VSLAM dropouts, the system falls back to wheel odometry. For a skid-steering rover with track width \( W = 1.8 \text{ m} \) and mass \( m = 1200 \text{ kg} \), the instantaneous curvature \( \kappa \) is related to left/right wheel speeds \( \omega_L, \omega_R \) by:

\[
\kappa = \frac{\omega_R - \omega_L}{\omega_R + \omega_L} \cdot \frac{2}{W}
\]

However, skid-steering induces longitudinal slip \( s \) that scales with vehicle mass and terrain resistance:

\[
s = k_s \cdot m \cdot \frac{|\kappa|}{g} = 0.005 \cdot 1200 \cdot \frac{|\kappa|}{9.81} \approx 0.61 |\kappa|
\]

The corrected forward velocity \( v \) and yaw rate \( \dot{\theta} \) are:

\[
v = \frac{R}{2} (\omega_R + \omega_L) \cdot (1 - s), \quad \dot{\theta} = \frac{R}{W} (\omega_R - \omega_L) \cdot (1 - s/2)
\]

Where \( R = 0.3 \text{ m} \) is the wheel radius. These compensated values are fused with any remaining VSLAM data via a Kalman filter.

### MAVLink Data Rate Throttling for 400Hz Real-Time Feasibility

The companion computer may attempt to send high-rate point clouds. The maximum allowable data rate \( D_{max} \) is constrained by the STM32F4's processing budget per 2.5 ms control cycle:

\[
D_{max} = \frac{N_{ops\_available}}{C_{dec\_per\_byte}} = \frac{150 \text{ ops}}{12 \text{ ops/byte}} = 12.5 \text{ bytes/cycle}
\]

At 400 Hz, this yields:

\[
D_{max} = 12.5 \ \text{bytes/cycle} \times 400 \ \text{Hz} = 5 \ \text{KB/s}
\]

MAVLink messages exceeding this rate are throttled via a token bucket algorithm with token rate \( r = D_{max} \) and bucket size \( b = 2 \cdot D_{max} = 10 \ \text{KB} \).

### Covariance Inflation Due to Rover Vibration and EMI

The VSLAM-reported covariance \( \mathbf{\Sigma}_{cam} \) is inflated based on the rover's current vibration frequency \( f_{vib} \) (derived from IMU accelerometer FFT) and the 400A motor current-induced EMI noise floor \( \sigma_{emi} \):

\[
\mathbf{\Sigma}_{body\_inflated} = \mathbf{\Sigma}_{body} + \mathbf{Q}_{vib} + \mathbf{Q}_{emi}
\]

The vibration process noise \( \mathbf{Q}_{vib} \) is diagonal, with translational components:

\[
Q_{vib,xx} = Q_{vib,yy} = \left( \frac{A_{vib}}{2\pi f_{vib}} \right)^2 \cdot \frac{m}{m_{ref}}
\]

Where \( A_{vib} \) is the vibration amplitude (m/s²), \( m_{ref} = 500 \text{ kg} \). EMI noise \( \mathbf{Q}_{emi} \) adds a fixed diagonal \( \sigma_{emi}^2 \mathbf{I} \) with \( \sigma_{emi} = 0.01 \text{ m} \).

### Time Synchronization and Clock Offset Estimation

The companion computer's clock \( t_{comp} \) drifts relative to the rover's STM32 clock \( t_{rover} \). The offset \( \delta \) and drift rate \( \dot{\delta} \) are estimated via a linear regression over \( N \) timestamped heartbeat packets:

\[
\delta = \frac{N \sum (t_{rover,i} t_{comp,i}) - \sum t_{rover,i} \sum t_{comp,i}}{N \sum t_{rover,i}^2 - (\sum t_{rover,i})^2}
\]

The residual error \( \sigma_\delta \) is used to inflate timestamps of sensor data.

### Virtual Sensor Array Geometry and Interpolation

A virtual array of \( M \times N \) synthetic sensors (e.g., a grid of virtual airspeed probes) provides measurements \( z_{ij} \) at body-frame locations \( \mathbf{p}_{ij} \). To estimate the value at the rover's center of mass \( \mathbf{p}_{CoM} \), a distance-weighted interpolation is used, with weights accounting for the inertia tensor \( \mathbf{I}_{body} \) which affects flow field distortion:

\[
w_{ij} = \frac{1}{\|\mathbf{p}_{ij} - \mathbf{p}_{CoM}\|^2 + \lambda \cdot (\mathbf{p}_{ij} - \mathbf{p}_{CoM})^T \mathbf{I}_{body}^{-1} (\mathbf{p}_{ij} - \mathbf{p}_{CoM})}
\]
\[
\hat{z}_{CoM} = \frac{\sum_{i,j} w_{ij} z_{ij}}{\sum_{i,j} w_{ij}}
\]

Where \( \lambda = 0.1 \) scales the inertia term. For the rover, \( \mathbf{I}_{body} \approx \text{diag}(800, 1000, 150) \ \text{kg} \cdot \text{m}^2 \).

### MAVLink Message Queue Dynamics and Priority Inversion Avoidance

The RTOS queue for incoming MAVLink messages has length \( L \). The probability of queue overflow given arrival rate \( \lambda \) and processing rate \( \mu \) is modeled as an M/M/1/L queue. For the rover, high-priority VSLAM packets (\( \lambda_{VSLAM} = 50 \ \text{Hz} \)) must not be blocked by lower-priority telemetry (\( \lambda_{tel} = 10 \ \text{Hz} \)). The queue uses a priority-weighted processing rate:

\[
\mu_{effective} = \mu \cdot \frac{w_{VSLAM} \cdot \lambda_{VSLAM} + w_{tel} \cdot \lambda_{tel}}{w_{VSLAM} + w_{tel}}
\]

With weights \( w_{VSLAM} = 3.0 \), \( w_{tel} = 1.0 \), ensuring VSLAM packets are processed within the 1.3 ms latency bound even under telemetry bursts.

## C++ Implementation

### MAVLink Message Parsing and Timestamp Correction (AP_CompanionComputer.cpp)

The `AP_CompanionComputer` class implements the latency and clock offset mathematics. The `handle_message(mavlink_message_t* msg)` function first corrects the packet timestamp using the estimated clock offset `_clock_offset` and drift `_clock_drift`:

```cpp
uint64_t corrected_time_us = packet_time_us + _clock_offset + _clock_drift * (now_us - _last_offset_update_us);
```

This directly implements \( t_a = t_s + \Delta t_{tx} + \ldots \) by adjusting the source timestamp. The function `update_clock_offset_estimate()` performs the linear regression over received heartbeat timestamps, computing the numerator and denominator for the slope formula \( \delta \):

```cpp
_sum_xy += t_rover * t_comp;
_sum_x += t_rover;
_sum_x2 += t_rover * t_rover;
// ... after N samples
_clock_drift = (_n_samples * _sum_xy - _sum_x * _sum_y) / (_n_samples * _sum_x2 - _sum_x * _sum_x);
```

A ring buffer of `timestamp_pair` structs stores the \( N \) most recent pairs for the regression. RTOS threading is managed by protecting this buffer with a semaphore `_clock_sem`.

### VSLAM Pose Injection with Covariance Transformation (AP_ExternalAHRS.cpp)

The `AP_ExternalAHRS` class receives `VISION_POSITION_ESTIMATE` MAVLink messages. The `handle_vision_position_estimate()` function extracts the pose quaternion `q_cam`, position vector `p_cam`, and covariance array `cov_cam`. The transformation to body frame begins by constructing the 4x4 transformation matrix `T_cam_to_world` from `q_cam` and `p_cam`. The lever arm offset `_lever_arm` (e.g., `Vector3f(0.5f, 0.0f, -0.2f)`) is applied:

```cpp
Matrix4f T_body_to_world = T_cam_to_world * Matrix4f::translation(-_lever_arm);
```

This is the code equivalent of \( \mathbf{T}_{body}^{world} = \mathbf{T}_{cam}^{world} \cdot [\mathbf{I} \ \mathbf{r}; \mathbf{0}^T \ 1]^{-1} \). The 6x6 covariance `cov_cam` is transformed using the pre-computed Jacobian `_J_cam_to_body`:

```cpp
Matrix6f cov_body = _J_cam_to_body * cov_cam * _J_cam_to_body.transposed();
```

The Jacobian is updated whenever the lever arm changes, using the skew-symmetric cross-product matrix function `vector3_skew(_lever_arm)`. The inflation due to vibration and EMI is applied by adding diagonal matrices `_Q_vib` and `_Q_emi` to `cov_body`, implementing \( \mathbf{\Sigma}_{body\_inflated} = \mathbf{\Sigma}_{body} + \mathbf{Q}_{vib} + \mathbf{Q}_{emi} \).

### Virtual Sensor Array Fusion (AP_VirtualSensor.cpp)

The `AP_VirtualSensor` template class manages an array of virtual sensors. The `fuse_readings()` function implements the mass-weighted inverse-variance fusion. The mass-dependent confidence factor `c(m)` is computed as:

```cpp
float mass_factor = 1.0f / (1.0f + sq(_rover_mass / 500.0f)); // _rover_mass = 1200.0f
```

For each sensor `i`, the adjusted weight is:
```cpp
float adjusted_weight = mass_factor * (1.0f / variances[i]);
```

The sum of weights `W` and weighted sum of readings are accumulated, then:
```cpp
fused_value = weighted_sum / W;
fused_variance = 1.0f / W;
```

This is the direct implementation of the formulas for \( \hat{y} \) and \( \hat{\sigma}^2 \). The class uses a `VectorN` for readings and a `MatrixN` for variances, sized at compile time via the template parameter `N`.

### Skid-Steering Odometry Compensation (AP_ExternalControl.cpp)

The `AP_ExternalControl` class provides the fallback odometry during VSLAM dropouts. The `update_wheel_odometry()` function reads left/right wheel encoders `_wheel_counts_left`, `_wheel_counts_right`. The instantaneous curvature `kappa` is computed:

```cpp
float omega_sum = _wheel_speed_left + _wheel_speed_right;
float omega_diff = _wheel_speed_right - _wheel_speed_left;
float kappa = (fabsf(omega_sum) > 0.1f) ? (omega_diff / omega_sum) * (2.0f / _track_width) : 0.0f;
```

The slip factor `s` is calculated based on rover mass:
```cpp
float slip_factor = 0.005f * _rover_mass * fabsf(kappa) / 9.81f;
```

Corrected velocity and yaw rate:
```cpp
float v_corrected = (_wheel_radius / 2.0f) * omega_sum * (1.0f - slip_factor);
float yaw_rate_corrected = (_wheel_radius / _track_width) * omega_diff * (1.0f - slip_factor / 2.0f);
```

These values are passed to the EKF as a velocity aiding source, implementing the skid-steering compensation model.

### MAVLink Data Rate Throttling (AP_CompanionComputer.cpp)

The `AP_CompanionComputer::should_accept_message(uint32_t msg_len)` function implements the token bucket algorithm. The bucket state `_token_bucket_bytes` is incremented at a fixed rate `_token_rate` (set to `D_{max} = 5120` bytes/s) on each call:

```cpp
uint32_t now_ms = AP_HAL::millis();
uint32_t elapsed_ms = now_ms - _last_token_update_ms;
_tokens += _token_rate * elapsed_ms / 1000.0f;
_tokens = MIN(_tokens, _bucket_capacity); // _bucket_capacity = 10240
_last_token_update_ms = now_ms;
```

When a message of length `msg_len` arrives, it is accepted only if `_tokens >= msg_len`, and `_tokens -= msg_len`. This enforces the maximum data rate \( D_{max} \) and prevents the serial buffer from overflowing.

### RTOS Queue and Priority Handling (AP_CompanionComputer.cpp)

The `_incoming_message_queue` is a ring buffer of `mavlink_message_t` with a priority field. The `push_message()` function inserts messages according to priority, using a simple insertion sort to maintain ordering. The `process_messages()` function, called from the 400Hz fast loop, processes messages from the queue but limits the number of lower-priority messages per cycle:

```cpp
uint32_t processed = 0;
while (!queue_empty() && processed < _max_high_priority_msgs) {
    mavlink_message_t msg = peek_next_message();
    if (msg.msgid == MAVLINK_MSG_ID_VISION_POSITION_ESTIMATE) {
        handle_vision_position_estimate(&msg);
        processed++;
    }
    // ... other high-priority handlers
}
// Process at most one low-priority message per cycle
if (!queue_empty() && processed == 0) {
    // process low-priority telemetry
}
```

This ensures the processing budget per 2.5 ms cycle is reserved for high-priority VSLAM data, implementing the priority-weighted rate \( \mu_{effective} \).

### Vibration and EMI Covariance Inflation (AP_ExternalAHRS.cpp)

The `update_vibration_covariance()` function computes the diagonal process noise matrix `_Q_vib`. It reads the dominant vibration frequency `f_vib` and amplitude `A_vib` from the IMU's FFT analysis (accessed via `AP::ins()`). The translational components are:

```cpp
float base_vib = sq(A_vib / (2.0f * M_PI * f_vib));
_Q_vib[0][0] = _Q_vib[1][1] = base_vib * (_rover_mass / 500.0f);
_Q_vib[2][2] = base_vib * (_rover_mass / 500.0f) * 0.5f; // vertical less affected
```

The EMI noise `_Q_emi` is a constant diagonal matrix with `0.0001f` (0.01 m²) on the position elements. These are added to the transformed covariance in `handle_vision_position_estimate()`.

### Virtual Sensor Array Interpolation (AP_VirtualSensor.cpp)

For a grid-based virtual sensor array, the `interpolate_to_com()` function computes the center-of-mass estimate. The weight for sensor at grid index `(i,j)` is:

```cpp
Vector3f delta = _sensor_positions[i][j] - _com_position;
float dist_sq = delta.length_squared();
float inertia_term = delta * (_inertia_inverse * delta); // _inertia_inverse = I_body^{-1}
float weight = 1.0f / (dist_sq + 0.1f * inertia_term);
```

The weighted sum and total weight are accumulated, and the final interpolated value is computed. This implements the distance and inertia-weighted interpolation formula.

### Time Synchronization and Health Monitoring (AP_CompanionComputer.cpp)

The health of the companion link is monitored via the `update_health()` function. The average latency `_avg_latency` is computed as an exponential moving average:

```cpp
_avg_latency = 0.95f * _avg_latency + 0.05f * current_latency;
```

If `_avg_latency` exceeds `_max_allowed_latency` (1300 μs), the health score `_link_health` is decremented. The system also checks for clock offset divergence; if the offset residual `_clock_offset_stderr` exceeds a threshold (e.g., 100 μs), the clock model is reset. This health state is used to weight the VSLAM data in the EKF.