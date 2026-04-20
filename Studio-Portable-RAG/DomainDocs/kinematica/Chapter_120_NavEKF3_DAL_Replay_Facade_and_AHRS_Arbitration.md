# NavEKF3, Data Acquisition Logging (DAL), and AHRS Arbitration

_Generated 2026-04-20 02:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_NavEKF3/AP_NavEKF3_core.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_InertialSensor.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_Backend.cpp`

# **Chapter: NavEKF3, Data Acquisition Logging (DAL), and AHRS Arbitration**

This chapter documents the core estimation, logging, and fault-tolerance systems within the ArduPilot 400Hz autonomous vehicle architecture. The implementation is specifically engineered for the demanding operational profile of a heavy agricultural rover: the requirement for robust, drift-free state estimation despite violent vibrations and sensor dropouts during skid-steer turns, the absolute need for post-mortem deterministic replay of field failures for root-cause analysis, and the management of triple-redundant estimator cores to ensure continuous operation. The core files—`AP_NavEKF3.cpp`, `AP_NavEKF3_core.cpp`, `AP_DAL.cpp`, `AP_DAL_InertialSensor.cpp`, `AP_AHRS.cpp`, and `AP_AHRS_Backend.cpp`—form a tightly integrated pipeline. This pipeline ingests raw sensor data via a deterministic logging facade (DAL), processes it through three independent 24-state Extended Kalman Filters (EKF3), and arbitrates between them to produce a single, fault-tolerant attitude, velocity, and position estimate. The system guarantees bit-exact reproducibility of any flight through deterministic replay, while the arbitration logic ensures seamless failover between estimator cores, maintaining sub-degree attitude and centimeter-level position accuracy even during partial sensor failures.

---

### **Mathematical Formulation of NavEKF3, Data Acquisition Logging (DAL), and AHRS Arbitration**

This section details the exact algebraic and matrix mathematics governing the 24-state Extended Kalman Filter (EKF3), the deterministic logging and replay system, and the multi-core attitude and heading reference system (AHRS) arbitration. The formulation directly addresses the physical realities of a heavy agricultural rover: the need for robust state estimation despite sensor dropouts, the requirement for post-mortem deterministic replay of field failures, and the management of three independent EKF cores to ensure continuous operation during high-vibration skid-steer maneuvers.

#### **1. EKF3 24-State Model and Prediction**

The rover's state is represented by a 24-element vector `x` and its associated covariance matrix `P ∈ ℝ²⁴ˣ²⁴`. The state indices are:

```
0: q0 (Quaternion scalar)
1: q1 (Quaternion vector i)
2: q2 (Quaternion vector j)
3: q3 (Quaternion vector k)
4: V_N (North velocity, m/s)
5: V_E (East velocity, m/s)
6: V_D (Down velocity, m/s)
7: P_N (North position, m)
8: P_E (East position, m)
9: P_D (Down position, m)
10: bg_x (Gyro bias X, rad/s)
11: bg_y (Gyro bias Y, rad/s)
12: bg_z (Gyro bias Z, rad/s)
13: ba_x (Accel bias X, m/s²)
14: ba_y (Accel bias Y, m/s²)
15: ba_z (Accel bias Z, m/s²)
16: m_N (Earth magnetic field North, μT)
17: m_E (Earth magnetic field East, μT)
18: m_D (Earth magnetic field Down, μT)
19: w_N (North wind velocity, m/s)
20: w_E (East wind velocity, m/s)
21: Δh (Barometer height bias, m)
22: κ (Airspeed scale factor)
23: δ (Body magnetic declination, rad)
```

**Quaternion Propagation (Attitude Prediction):**
Given gyro measurement `ω = [ω_x, ω_y, ω_z]ᵀ` with bias `b_g` removed (`ω_corrected = ω - b_g`), the discrete-time update over interval `Δt = 0.0025 s` (400 Hz) uses the quaternion derivative matrix `Ω(ω)`:

```
Ω(ω) = 0.5 × [[0,    -ω_x, -ω_y, -ω_z],
              [ω_x,    0,    ω_z, -ω_y],
              [ω_y,  -ω_z,    0,   ω_x],
              [ω_z,   ω_y,  -ω_x,   0 ]]
```

The state transition matrix for the quaternion is `Φ_q = I₄ + Ω(ω) × Δt`. The quaternion update is:
```
q_{k+1} = Φ_q × q_k
q_{k+1} = q_{k+1} / ||q_{k+1}|| (renormalized)
```

**Velocity and Position Propagation:**
The acceleration in the body frame `a_b`, after bias correction (`a_corrected = a - b_a`), is rotated to the NED frame using the rotation matrix `R_b^n(q)` derived from the quaternion. The velocity derivative includes Coriolis terms due to the rover's rotating body frame and gravity:

```
a_ned = R_b^n(q) × a_corrected
Coriolis = ω × v_ned = [ω_y×v_D - ω_z×v_E, ω_z×v_N - ω_x×v_D, ω_x×v_E - ω_y×v_N]ᵀ
dv/dt = a_ned - Coriolis - g   (where g = [0, 0, 9.80665]ᵀ m/s²)
v_{k+1} = v_k + dv/dt × Δt
p_{k+1} = p_k + v_k × Δt
```

**Covariance Prediction:**
The full state transition matrix `Φ ∈ ℝ²⁴ˣ²⁴` is computed by linearizing the dynamics around the current state. The process noise covariance `Q ∈ ℝ²⁴ˣ²⁴` models uncertainties in gyro/accel noise and bias random walk. The covariance prediction is:
```
P_{k+1|k} = Φ × P_{k|k} × Φᵀ + Q
```

#### **2. Measurement Update: GPS Fusion**

The GPS provides a 6-element measurement vector `z = [p_N, p_E, p_D, v_N, v_E, v_D]ᵀ` with covariance `R_gps ∈ ℝ⁶ˣ⁶`.

**Measurement Model and Innovation:**
The predicted measurement is simply the corresponding state elements:
```
h(x) = [x[7], x[8], x[9], x[4], x[5], x[6]]ᵀ
Innovation: y = z - h(x)
```

**Kalman Update Equations:**
The measurement Jacobian `H ∈ ℝ⁶ˣ²⁴` is sparse:
```
H(0,7)=1, H(1,8)=1, H(2,9)=1, H(3,4)=1, H(4,5)=1, H(5,6)=1, all others 0.
```

The innovation covariance, Kalman gain, and state/covariance update are:
```
S = H × P × Hᵀ + R_gps
K = P × Hᵀ × S⁻¹
x_{k|k} = x_{k|k-1} + K × y
P_{k|k} = (I₂₄ - K × H) × P_{k|k-1}   (Joseph form for stability)
```

**Normalized Innovation Squared (NIS):** A fault detection metric:
```
NIS = yᵀ × S⁻¹ × y
```
Under nominal conditions, NIS follows a chi-square distribution with 6 degrees of freedom. A threshold (e.g., NIS > 10) indicates a potential GPS fault.

#### **3. Multi-Core AHRS Arbitration**

Three independent EKF3 cores run in parallel. A health score `score_k` for core `k` is computed as a weighted sum of three metrics:

**Health Score Components:**
1.  **Innovation Score:** Based on the root-sum-square (RSS) of normalized innovations across all measurements.
    ```
    RSS = sqrt( Σ_i (innovation_i² / variance_i) )
    innovation_score = max(0, (10.0 - RSS) / 10.0)
    ```
2.  **Timeliness Score:** Penalizes cores with stale updates.
    ```
    timeliness = max(0, (1000 - Δt_ms) / 1000), where Δt_ms is time since last healthy update.
    ```
3.  **Sensor Count Score:** Rewards cores with more healthy sensors (gyro, accel, mag, baro, GPS).
    ```
    sensor_score = (number_of_healthy_sensors) / 5.0
    ```

**Composite Score:**
```
score_k = 0.6 × innovation_score + 0.3 × timeliness + 0.1 × sensor_score
```
The primary core is selected as the one with the highest score. A core switch is triggered only if a backup core's score exceeds the primary's score by a hysteresis margin (e.g., 15%) to prevent chattering.

#### **4. Core State Fusion via Covariance Intersection**

When multiple cores are healthy (`score > 0.5`), their estimates are fused to produce a more robust output. For `N` cores with state estimates `x_i` and covariances `P_i`, the fused estimate `x_fused` and `P_fused` are computed using Covariance Intersection.

**Covariance Intersection Algorithm:**
The fused covariance and state are given by:
```
P_fused⁻¹ = Σ_{i=1}^{N} w_i × P_i⁻¹
x_fused = P_fused × Σ_{i=1}^{N} w_i × P_i⁻¹ × x_i
```
The weights `w_i` (summing to 1) are chosen to minimize the trace of `P_fused`. An iterative method solves for optimal weights.

**Quaternion Fusion via SLERP:**
For attitude, quaternions `q_i` are fused using spherical linear interpolation (SLERP) weighted by the inverse of their angular variance (derived from the attitude sub-block of `P_i`). Given two quaternions `q_a` and `q_b`:
```
dot = q_a · q_b
θ = acos(clamp(dot, -1, 1))
q_fused = [ sin((1-w)θ) × q_a + sin(wθ) × q_b ] / sin(θ)
```
For `N > 2`, the fusion proceeds sequentially.

#### **5. Data Acquisition Logging (DAL) Deterministic Replay**

The DAL ensures bit-exact reproducibility by logging all sensor inputs and EKF states to a memory-mapped ring buffer in SRAM3, which is periodically flushed to storage.

**Registry Entry Structure:**
Each log entry contains a header with signature (`0x44414C21`), type ID, instance, timestamp (ns), size, and a CRC32 checksum, followed by the raw data payload.

**CRC32 Checksum:**
The CRC32 polynomial `0x04C11DB7` (IEEE 802.3) is used to detect data corruption. The checksum is computed over the entire entry header (with CRC field zeroed) and the payload.

**Deterministic Replay Guarantee:**
During replay, the logged entries are fed to the EKF in the exact same order and with the same timestamps as during the flight. Because the EKF's state update equations are deterministic functions of the input sequence and initial state, the replayed state trajectory `x_replay(t)` will be bit-identical to the in-flight state `x_flight(t)`, allowing precise debugging.

**Mathematical Representation of Replay:**
Let `S(t)` be the sensor data vector at time `t`, and `EKF(S, x₀)` be the function mapping a sensor sequence `S` and initial state `x₀` to the estimated state trajectory. The logging system records `S_log = {S(t₀), S(t₁), ..., S(tₙ)}`. The replay guarantees:
```
x_replay(t) = EKF(S_log, x₀) = x_flight(t)   (bit-for-bit equality)
```
This holds because all floating-point operations are deterministic on the same hardware, and the DAL ensures `S_log` is identical.

#### **6. Integration with Rover Dynamics**

The EKF's velocity and position states are used directly for skid-steer control. The estimated gyro bias `b_g` is critical for the heavy rover, as low-frequency drift can cause significant heading error over time, affecting row-following accuracy. The estimated accelerometer bias `b_a` compensates for mounting misalignment and scale factor errors that are exacerbated by the rover's high mass and vibration. The AHRS arbitration ensures that a single sensor fault (e.g., a magnetometer saturated by motor current) does not corrupt the attitude estimate, allowing the rover to maintain operation using the remaining healthy EKF cores.

---

### **C++ Implementation: RTOS Threading and Deterministic Replay**

This section details the specific C++ classes, RTOS threading, and hardware memory management that implement the triple-redundant EKF3, the Data Acquisition Logger (DAL), and the AHRS arbitration system for the heavy rover.

#### **Multi-Core EKF3 Execution and RTOS Scheduling**

Three independent EKF3 core instances run in parallel, each with its own 24-state vector and covariance matrix. They are scheduled as separate RTOS tasks to ensure temporal isolation and fault containment.

**EKF3 Core Thread Definition:**
Each core runs in its own thread at 400 Hz, synchronized by a semaphore from the IMU data ready interrupt.

```cpp
// EKF Core Thread function (Priority 9, 400Hz)
void ekf3_core_thread(void const *argument) {
    uint8_t core_id = (uint8_t)(uintptr_t)argument; // 0, 1, or 2
    NavEKF3_core &core = *_ekf3_cores[core_id];
    
    for(;;) {
        // Wait for IMU data ready semaphore (triggered at 400Hz)
        osSemaphoreWait(_imu_semaphore, osWaitForever);
        
        // Get IMU data via DAL facade
        Vector3f gyro, accel;
        uint64_t timestamp_ns;
        AP_DAL::get_singleton()->read_sensor(TYPEID_GYRO_DATA, core_id, &gyro, sizeof(gyro), &timestamp_ns);
        AP_DAL::get_singleton()->read_sensor(TYPEID_ACCEL_DATA, core_id, &accel, sizeof(accel), &timestamp_ns);
        
        // Prediction step (state propagation)
        core.predictState(gyro, accel, timestamp_ns);
        
        // Check for available GPS data (non-blocking)
        Vector3f gps_pos, gps_vel;
        Matrix3f gps_cov;
        if (AP_DAL::get_singleton()->read_sensor(TYPEID_GPS_DATA, 0, &gps_pos, sizeof(gps_pos), nullptr)) {
            // Measurement update
            core.fuseGPS(gps_pos, gps_vel, gps_cov);
        }
        
        // Write updated state to DAL for arbitration/fusion
        Vector24f state_vec = core.getStateVector();
        AP_DAL::get_singleton()->write_sensor(TYPEID_EKF_STATE, core_id, &state_vec, sizeof(state_vec));
    }
}
```

**State Prediction Implementation (`predictState`):** This method implements the quaternion, velocity, and position propagation equations. The `EKF24_State` struct holds the 24-state vector `x[24]` and covariance `P[24][24]`.

```cpp
void NavEKF3_core::predictState(const Vector3f &gyro, const Vector3f &accel, uint64_t timestamp_ns) {
    // Remove estimated biases: ω_corrected = ω_measured - b_g
    Vector3f gyro_corrected = gyro - Vector3f(x[IX_GYRO_BIAS_X], x[IX_GYRO_BIAS_Y], x[IX_GYRO_BIAS_Z]);
    Vector3f accel_corrected = accel - Vector3f(x[IX_ACCEL_BIAS_X], x[IX_ACCEL_BIAS_Y], x[IX_ACCEL_BIAS_Z]);
    
    // Quaternion propagation matrix Ω(ω) = 0.5 * [[0, -ωᵀ]; [ω, -[ω]×]]
    Matrix4f Omega;
    Omega[0][0] = 0.0f;           Omega[0][1] = -gyro_corrected.x; Omega[0][2] = -gyro_corrected.y; Omega[0][3] = -gyro_corrected.z;
    Omega[1][0] = gyro_corrected.x; Omega[1][1] = 0.0f;            Omega[1][2] = gyro_corrected.z;  Omega[1][3] = -gyro_corrected.y;
    Omega[2][0] = gyro_corrected.y; Omega[2][1] = -gyro_corrected.z; Omega[2][2] = 0.0f;            Omega[2][3] = gyro_corrected.x;
    Omega[3][0] = gyro_corrected.z; Omega[3][1] = gyro_corrected.y;  Omega[3][2] = -gyro_corrected.x; Omega[3][3] = 0.0f;
    
    // Discrete-time transition: Φ_q = I + Ω * Δt
    float dt = (timestamp_ns - _last_predict_ns) * 1e-9f;
    Matrix4f Phi_q = Matrix4f::identity() + 0.5f * Omega * dt;
    
    // Update quaternion: q_{k+1} = Φ_q * q_k
    Vector4f q_prev(x[IX_QUAT0], x[IX_QUAT1], x[IX_QUAT2], x[IX_QUAT3]);
    Vector4f q_next = Phi_q * q_prev;
    q_next.normalize();
    x[IX_QUAT0] = q_next[0]; x[IX_QUAT1] = q_next[1]; x[IX_QUAT2] = q_next[2]; x[IX_QUAT3] = q_next[3];
    
    // Rotation matrix from body to NED
    Matrix3f R_b_n = quaternion_to_rotation(q_next);
    
    // Velocity update: dv/dt = R_b_n * a_b - g - ω × v
    Vector3f accel_ned = R_b_n * accel_corrected;
    Vector3f coriolis = gyro_corrected % Vector3f(x[IX_VELN], x[IX_VELE], x[IX_VELD]); // cross product
    Vector3f gravity(0.0f, 0.0f, 9.80665f);
    
    x[IX_VELN] += (accel_ned.x - coriolis.x) * dt;
    x[IX_VELE] += (accel_ned.y - coriolis.y) * dt;
    x[IX_VELD] += (accel_ned.z - gravity.z - coriolis.z) * dt;
    
    // Position update
    x[IX_POSN] += x[IX_VELN] * dt;
    x[IX_POSE] += x[IX_VELE] * dt;
    x[IX_POSD] += x[IX_VELD] * dt;
    
    // Covariance prediction: P_{k+1|k} = Φ * P_{k|k} * Φᵀ + Q
    // (Full Φ matrix calculation omitted for brevity, includes linearized dynamics)
    _last_predict_ns = timestamp_ns;
}
```

**GPS Measurement Update (`fuseGPS`):** Implements the Kalman update with the sparse measurement Jacobian `H`.

```cpp
void NavEKF3_core::fuseGPS(const Vector3f &gps_pos, const Vector3f &gps_vel, const Matrix3f &gps_cov) {
    // Measurement vector z = [pos_N, pos_E, pos_D, vel_N, vel_E, vel_D]ᵀ
    Vector6f z;
    z[0]=gps_pos.x; z[1]=gps_pos.y; z[2]=gps_pos.z;
    z[3]=gps_vel.x; z[4]=gps_vel.y; z[5]=gps_vel.z;
    
    // Predicted measurement h(x)
    Vector6f h;
    h[0]=x[IX_POSN]; h[1]=x[IX_POSE]; h[2]=x[IX_POSD];
    h[3]=x[IX_VELN]; h[4]=x[IX_VELE]; h[5]=x[IX_VELD];
    
    // Innovation y = z - h(x)
    Vector6f y = z - h;
    
    // Measurement Jacobian H (6x24, sparse)
    Matrix6x24f H;
    H.zero();
    H(0, IX_POSN) = 1.0f;
    H(1, IX_POSE) = 1.0f;
    H(2, IX_POSD) = 1.0f;
    H(3, IX_VELN) = 1.0f;
    H(4, IX_VELE) = 1.0f;
    H(5, IX_VELD) = 1.0f;
    
    // Innovation covariance S = H*P*Hᵀ + R
    Matrix6f S = H * matrix_from_array(P) * H.transposed();
    S(0,0)+=gps_cov(0,0); S(1,1)+=gps_cov(1,1); S(2,2)+=gps_cov(2,2);
    S(3,3)+=gps_cov(0,0); S(4,4)+=gps_cov(1,1); S(5,5)+=gps_cov(2,2); // Simplified
    
    // Kalman gain K = P*Hᵀ*S⁻¹
    Matrix24x6f K = matrix_from_array(P) * H.transposed() * S.inverse();
    
    // State update: x = x + K*y
    Vector24f x_vec = vector_from_array(x);
    x_vec += K * y;
    vector_to_array(x_vec, x);
    
    // Covariance update (Joseph form): P = (I - K*H)*P*(I - K*H)ᵀ + K*R*Kᵀ
    Matrix24f I = Matrix24f::identity();
    Matrix24f I_KH = I - K * H;
    matrix_to_array(I_KH * matrix_from_array(P) * I_KH.transposed() + K * gps_cov * K.transposed(), P);
    
    // NIS for fault detection
    float nis = y.dot(S.inverse() * y);
    if (nis > 10.0f) _gps_fault_count++;
}
```

#### **AHRS Arbitration and Core Fusion**

The `AP_AHRS` class manages the three EKF cores, calculates health scores, and fuses their outputs.

**Health Score Calculation (`_update_core_health`):** Implements the weighted scoring function `score = 0.6*innovation_score + 0.3*timeliness + 0.1*sensor_score`.

```cpp
void AP_AHRS::_update_core_health(uint8_t core_idx, uint32_t now_ms) {
    NavEKF3 &core = *_ekf3_cores[core_idx];
    
    // Get innovation variances and calculate RSS of normalized innovations
    float innov_var[6];
    core.getInnovationVariances(innov_var);
    float rss = 0.0f;
    for (uint8_t i=0; i<6; i++) {
        if (innov_var[i] > 0.0f) {
            float innov = core.getInnovation(i);
            rss += (innov * innov) / innov_var[i]; // NIS component
        }
    }
    rss = sqrtf(rss);
    float innovation_score = (rss < 10.0f) ? (10.0f - rss) / 10.0f : 0.0f;
    
    // Timeliness score
    uint32_t dt_ms = now_ms - _core_health[core_idx].last_update_ms;
    float timeliness = (dt_ms < 1000) ? (1000.0f - dt_ms) / 1000.0f : 0.0f;
    
    // Sensor count score
    uint8_t healthy_sensors = 0;
    if (core.gyroHealthy()) healthy_sensors++;
    if (core.accelHealthy()) healthy_sensors++;
    if (core.magHealthy()) healthy_sensors++;
    if (core.baroHealthy()) healthy_sensors++;
    if (core.gpsHealthy()) healthy_sensors++;
    float sensor_score = healthy_sensors / 5.0f;
    
    // Composite score
    _core_health[core_idx].score = 0.6f*innovation_score + 0.3f*timeliness + 0.1f*sensor_score;
    _core_health[core_idx].innovation_rss = rss;
    _core_health[core_idx].healthy_sensors = healthy_sensors;
}
```

**Core Fusion via Covariance Intersection (`_fuse_core_states`):** Implements the equations `P_fused⁻¹ = Σ w_i * P_i⁻¹` and `x_fused = P_fused * Σ w_i * P_i⁻¹ * x_i`.

```cpp
void AP_AHRS::_fuse_core_states() {
    // Collect healthy cores (score > 0.5)
    uint8_t healthy_idx[3], healthy_count = 0;
    for (uint8_t i=0; i<3; i++) {
        if (_core_health[i].score > 0.5f) healthy_idx[healthy_count++] = i;
    }
    if (healthy_count < 2) return;
    
    // Get quaternions and covariances (attitude sub-block)
    Quaternion quat[3];
    Matrix3f cov[3]; // Attitude covariance from each core
    for (uint8_t i=0; i<healthy_count; i++) {
        uint8_t idx = healthy_idx[i];
        _ekf3_cores[idx]->getQuaternion(quat[i]);
        _ekf3_cores[idx]->getCovariance(cov[i]); // Returns 3x3 attitude block
    }
    
    // Covariance Intersection weight optimization
    float w[3] = {0.33f, 0.33f, 0.34f};
    for (uint8_t iter=0; iter<10; iter++) {
        Matrix3f P_inv_sum;
        P_inv_sum.zero();
        for (uint8_t i=0; i<healthy_count; i++) {
            P_inv_sum += w[i] * cov[i].inverse();
        }
        _fused_state.cov_fused = P_inv_sum.inverse();
        
        // Update weights: w_i ∝ 1/(1 + trace(P_fused - P_i)/trace(P_i))
        float total = 0.0f;
        for (uint8_t i=0; i<healthy_count; i++) {
            Matrix3f P_diff = _fused_state.cov_fused - cov[i];
            w[i] = 1.0f / (1.0f + P_diff.trace() / cov[i].trace());
            total += w[i];
        }
        for (uint8_t i=0; i<healthy_count; i++) w[i] /= total;
    }
    
    // Fuse quaternions using SLERP with weights w[i]
    _fused_state.quat_fused = quat[0];
    for (uint8_t i=1; i<healthy_count; i++) {
        float dot = _fused_state.quat_fused.dot(quat[i]);
        if (dot < 0.0f) { quat[i] = -quat[i]; dot = -dot; }
        dot = constrain_float(dot, -1.0f, 1.0f);
        float theta = acosf(dot);
        float sin_theta = sinf(theta);
        if (fabsf(sin_theta) < 1e-6f) {
            // Linear interpolation
            _fused_state.quat_fused = _fused_state.quat_fused*(1.0f-w[i]) + quat[i]*w[i];
            _fused_state.quat_fused.normalize();
        } else {
            // SLERP
            float ratio_a = sinf((1.0f-w[i])*theta)/sin_theta;
            float ratio_b = sinf(w[i]*theta)/sin_theta;
            _fused_state.quat_fused = _fused_state.quat_fused*ratio_a + quat[i]*ratio_b;
        }
    }
}
```

**Core Switching Logic (`_trigger_core_switch`):** Implements the hysteresis rule: switch if `score_backup > 1.15 * score_primary`.

```cpp
void AP_AHRS::_trigger_core_switch() {
    uint8_t best_backup = 0;
    float best_score = 0.0f;
    for (uint8_t i=0; i<3; i++) {
        if (i != _primary_core_idx && _core_health[i].score > best_score) {
            best_score = _core_health[i].score;
            best_backup = i;
        }
    }
    // 15% hysteresis margin
    if (best_score > (_core_health[_primary_core_idx].score * 1.15f)) {
        _backup_core_idx = best_backup;
        _arb_state = ARB_SWITCH;
    }
}
```

#### **Data Acquisition Logger (DAL) Implementation**

The `AP_DAL` singleton provides a unified interface for sensor data logging and deterministic replay.

**Registry Write (`write_sensor`):** Writes a timestamped, CRC-protected entry to the ring buffer in SRAM3.

```cpp
void AP_DAL::write_sensor(uint16_t type_id, uint16_t instance, const void *data, uint32_t size) {
    // Calculate total entry size
    uint32_t total_size = sizeof(DAL_registry_entry) + size;
    
    // Handle ring buffer wrap
    if (_registry.current_offset + total_size > DAL_REGISTRY_SIZE) {
        _registry.current_offset = 0;
        _registry.wrap_count++;
    }
    
    // Write entry header
    DAL_registry_entry *entry = (DAL_registry_entry*)(_registry.base_ptr + _registry.current_offset);
    entry->signature = 0x44414C21; // "DAL!"
    entry->offset = _registry.current_offset;
    entry->size = size;
    entry->type_id = type_id;
    entry->instance = instance;
    entry->timestamp_ns = AP_HAL::micros64() * 1000ULL;
    memcpy(entry->data, data, size);
    
    // Compute CRC32 over header (with crc32=0) and data
    entry->crc32 = 0;
    entry->crc32 = crc32_calculate(entry, sizeof(DAL_registry_entry) - 4 + size);
    
    // Update cache and advance pointer
    _update_cache(type_id, instance, entry->data, size, entry->timestamp_ns);
    _registry.current_offset += total_size;
}
```

**Registry Read (`read_sensor`):** Searches the ring buffer in reverse chronological order for the latest matching entry.

```cpp
bool AP_DAL::read_sensor(uint16_t type_id, uint16_t instance, void *buffer, uint32_t buffer_size, uint64_t *timestamp_ns) {
    // First check cache (LRU)
    SensorCache *cache = _find_in_cache(type_id, instance);
    if (cache && buffer_size >= cache->size) {
        memcpy(buffer, cache->data_ptr, cache->size);
        if (timestamp_ns) *timestamp_ns = cache->timestamp_ns;
        _move_to_head(cache); // Mark as recently used
        return true;
    }
    
    // Linear search through registry (most recent first)
    uint32_t offset = _registry.current_offset;
    for (uint32_t wraps=0; wraps <= _registry.wrap_count; wraps++) {
        while (offset >= sizeof(DAL_registry_entry)) {
            offset -= sizeof(DAL_registry_entry);
            DAL_registry_entry *entry = (DAL_registry_entry*)(_registry.base_ptr + offset);
            
            if (entry->signature != 0x44414C21) continue; // Corrupted
            
            // Verify CRC
            uint32_t saved_crc = entry->crc32;
            entry->crc32 = 0;
            uint32_t calc_crc = crc32_calculate(entry, sizeof(DAL_registry_entry) - 4 + entry->size);
            entry->crc32 = saved_crc;
            if (calc_crc != saved_crc) continue;
            
            if (entry->type_id == type_id && entry->instance == instance) {
                if (buffer_size >= entry->size) {
                    memcpy(buffer, entry->data, entry->size);
                    if (timestamp_ns) *timestamp_ns = entry->timestamp_ns;
                    _update_cache(type_id, instance, entry->data, entry->size, entry->timestamp_ns);
                    return true;
                }
            }
            offset -= entry->size; // Move to previous entry
        }
        offset = DAL_REGISTRY_SIZE; // Wrap to end
    }
    return false;
}
```

**CRC32 Implementation:** Uses the polynomial `0x04C11DB7` (IEEE) for error detection.

```cpp
uint32_t AP_DAL::crc32_calculate(const void *data, uint32_t len) {
    uint32_t crc = 0xFFFFFFFF;
    const uint8_t *bytes = (const uint8_t*)data;
    for (uint32_t i=0; i<len; i++) {
        crc ^= (bytes[i] << 24);
        for (uint8_t bit=0; bit<8; bit++) {
            if (crc & 0x80000000) {
                crc = (crc << 1) ^ 0x04C11DB7;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}
```

#### **Hardware Memory Configuration**

The DAL registry resides in SRAM3 (128KB), configured as cacheable write-through memory via the Memory Protection Unit (MPU).

```cpp
void dal_mpu_init() {
    // Configure SRAM3 (0x20040000-0x2005FFFF) as Normal memory, cacheable
    MPU->RNR = 5;
    MPU->RBAR = 0x20040000 & MPU_RBAR_ADDR_Msk;
    MPU->RASR = (0x01 << MPU_RASR_TEX_Pos) |  // TEX=001
                (0x01 << MPU_RASR_S_Pos)   |  // Shareable
                (0x01 << MPU_RASR_C_Pos)   |  // Cacheable
                (0x01 << MPU_RASR_B_Pos)   |  // Bufferable
                (MPU_RASR_SIZE_128KB << MPU_RASR_SIZE_Pos) |
                (0x03 << MPU_RASR_AP_Pos)  |  // Full access
                (0x01 << MPU_RASR_ENABLE_Pos);
    MPU->CTRL = MPU_CTRL_ENABLE_Msk | MPU_CTRL_PRIVDEFENA_Msk;
}
```

#### **RTOS Thread Architecture**

The system uses four primary RTOS threads:

1.  **IMU Thread (Priority 10):** Samples gyro/accel at 8 kHz, writes to DAL, and releases the `_imu_semaphore`.
2.  **EKF3 Core Threads (Priority 9):** Three instances (`ekf3_core_thread`), each waiting on the semaphore, running prediction/update at 400 Hz.
3.  **AHRS Arbitration Thread (Priority 8):** Runs `update_arbitration()` at 100 Hz, fuses core outputs, and manages core switching.
4.  **DAL Logging Thread (Priority 5):** Periodically flushes the SRAM3 ring buffer to SD card when logging is active.

The semaphore ensures synchronous execution: the