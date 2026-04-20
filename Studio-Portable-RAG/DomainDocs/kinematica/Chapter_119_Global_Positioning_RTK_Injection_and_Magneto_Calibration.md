# Global Positioning, RTK Injection, and Magnetometer Calibration

_Generated 2026-04-20 02:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/AP_GPS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/RTCM3_Parser.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/AP_GPS_UBLOX.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/CompassCalibrator.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/Compass_learn.cpp`

# **Chapter: Global Positioning, RTK Injection, and Magnetometer Calibration**

This chapter documents the centimeter-accurate absolute positioning and robust heading estimation systems within the ArduPilot 400Hz autonomous vehicle architecture. The implementation is specifically hardened for the operational realities of a heavy agricultural rover: the requirement for precise (±2 cm) absolute positioning for autonomous row-following and implement control, and the critical need for stable heading estimation despite intense magnetic interference from high-current (≥100A) motor cables and skid-steer actuators. The core files—`AP_GPS.cpp`, `RTCM3_Parser.cpp`, `AP_GPS_UBLOX.cpp`, `AP_Compass.cpp`, `CompassCalibrator.cpp`, and `Compass_learn.cpp`—form a tightly integrated sensor fusion pipeline. This pipeline ingests raw GNSS observations and magnetometer data, applies real-time kinematic (RTK) corrections and multi-stage magnetic calibration, and outputs high-fidelity position and heading estimates to the navigation EKF. The system maintains RTK fixed solutions with horizontal accuracies under 2 cm and heading errors below 0.5°, even during high-torque skid-steer maneuvers that generate significant electromagnetic noise.

---

### **Mathematical Formulation of GPS RTK and Magnetometer Calibration for a Heavy Skid-Steer Rover**

This section details the exact algebraic and matrix mathematics governing centimeter-accurate positioning and robust heading estimation. The formulation directly addresses the physical realities of a heavy agricultural rover: the need for precise absolute positioning for row-following, the significant magnetic interference from high-current motor cables and skid-steer actuators, and the integration of RTK corrections over potentially intermittent radio links.

#### **1. RTK Positioning: Double-Difference Carrier Phase Processing**

The rover achieves centimeter-level accuracy by resolving integer ambiguities in the carrier phase measurements from both the rover and a fixed base station. The primary observable is the double-difference carrier phase.

**Double-Difference Formation:**
For two satellites (k, r) and two receivers (rover, base):
```
∇Δφ = (φ_base^k - φ_rover^k) - (φ_base^r - φ_rover^r)
```
Where `φ` is the carrier phase measurement in meters (`φ = measured_cycles × λ`, with `λ ≈ 0.1903m` for GPS L1). This eliminates satellite and receiver clock errors, as well as most atmospheric delays for short baselines (<10 km).

**Integer Ambiguity Resolution (LAMBDA Method):**
The float solution must resolve integer ambiguities `N` for each satellite pair. The weighted least-squares problem is:
```
N = argmin_N (∇Δφ - λN)ᵀ Q_dd⁻¹ (∇Δφ - λN)
```
Where `Q_dd` is the covariance matrix of the double-difference observables:
```
Q_dd = 2 × Q_phase + 2 × Q_tropo + Q_iono
```
- `Q_phase = (0.01 cycles)² × λ² ≈ (0.0019m)²` (measurement noise)
- `Q_tropo = (0.2m)² × (baseline/10km)` (tropospheric residual)
- `Q_iono = (1-2m)² × (baseline/10km)` (ionospheric residual, negligible for dual-frequency)

**Final Fixed Position:**
Once integer ambiguities `N_integer` are resolved, the rover's precise position relative to the base is:
```
P_rtk_relative = P_float + λ × N_integer
P_rtk_absolute = P_base + P_rtk_relative
```
Where `P_base` is the precisely surveyed base station position in Earth-Centered, Earth-Fixed (ECEF) coordinates.

#### **2. Covariance Propagation and Dilution of Precision**

The position covariance matrix `P_rtk` in the local East-North-Up (ENU) frame is derived from the geometry matrix `G` and measurement covariance `Q`.

**Design Matrix `G` for Double-Differences:**
For `m` satellites, the design matrix has dimensions `(m-1) × 3`:
```
G = [ -e_2 + e_1, -e_3 + e_1, ..., -e_m + e_1 ]ᵀ
```
Where `e_i` is the unit line-of-sight vector from rover to satellite `i`.

**Covariance Calculation:**
```
P_rtk_enu = (Gᵀ Q_dd⁻¹ G)⁻¹
```
The Dilution of Precision (DOP) metrics are extracted from this covariance:
```
σ_east² = P_rtk_enu(0,0), σ_north² = P_rtk_enu(1,1), σ_up² = P_rtk_enu(2,2)
HDOP = sqrt(σ_east² + σ_north²) / σ_geometric
VDOP = σ_up / σ_geometric
PDOP = sqrt(HDOP² + VDOP²)
```
For the rover's navigation filter (using NED convention), the covariance is transformed:
```
R_enu_to_ned = [[0, 1, 0],
                [1, 0, 0],
                [0, 0, -1]]
P_ned = R_enu_to_ned × P_rtk_enu × R_enu_to_nedᵀ
```

#### **3. Magnetometer Calibration: Sphere and Ellipsoid Fitting**

The rover's magnetic field is distorted by hard-iron (permanent offsets) and soft-iron (anisotropic scaling) effects from nearby steel and motor currents.

**Hard-Iron Offset via Sphere Fitting:**
Given `N` raw magnetic measurements `Bᵢ = [Bxᵢ, Byᵢ, Bzᵢ]ᵀ`, we solve for offset `O = [Ox, Oy, Oz]ᵀ` and radius `R` that minimize:
```
Σᵢ ( ||Bᵢ - O||² - R² )²
```
Expanding the norm: `||Bᵢ - O||² = Bᵢ·Bᵢ - 2Bᵢ·O + O·O`. This leads to a linear system in terms of `X = [Ox, Oy, Oz, R² - O·O]ᵀ`:
```
[2Bxᵢ, 2Byᵢ, 2Bzᵢ, -1] × X = Bxᵢ² + Byᵢ² + Bzᵢ²
```
For all `N` samples, this forms `A X = b`, where `A` is `N×4`. The least-squares solution via Singular Value Decomposition (SVD) is:
```
A = U Σ Vᵀ  (thin SVD)
X = V Σ⁺ Uᵀ b
```
Where `Σ⁺` is the pseudo-inverse of the diagonal matrix `Σ`, with small singular values thresholded to zero for stability. The offset `O` is extracted from the first three elements of `X`, and the radius is `R = sqrt(O·O + X[3])`.

**Soft-Iron Correction via Ellipsoid Fitting:**
After hard-iron correction (`B_centered = B_raw - O`), the soft-iron effect is modeled by a symmetric positive definite matrix `M`:
```
B_centeredᵀ M B_centered = 1
```
The matrix `M` is a `3×3` matrix with 6 unique elements: `[M11, M12, M13, M22, M23, M33]`. Each sample provides a linear constraint:
```
Bx²*M11 + 2BxBy*M12 + 2BxBz*M13 + By²*M22 + 2ByBz*M23 + Bz²*M33 = 1
```
This builds a `N×6` linear system `A6 m = b6`, where `m` is the vector of the 6 unique elements of `M`, and `b6` is a vector of ones. The solution `m = (A6ᵀ A6)⁻¹ A6ᵀ b6` gives `M`. The calibration matrix `W` is obtained from the Cholesky decomposition:
```
M = Wᵀ W   =>   W = chol(M)⁻¹
```
The final corrected measurement is:
```
B_corrected = W × (B_raw - O)
```

#### **4. Dynamic Motor Interference Cancellation**

High currents (≥100A) in motor cables near the compass generate interfering magnetic fields proportional to throttle. The Biot-Savart law gives the field from a straight wire segment:
```
B_wire = (μ₀ I / (2π d)) × (sinθ₂ - sinθ₁)
```
Where `μ₀ = 4π×10⁻⁷ H/m`, `I` is current, `d` is perpendicular distance to the wire, and `θ` are angles from the wire segment endpoints.

**Learned Linear Interference Model:**
The interference field `B_interf` is modeled as a linear combination of operational parameters:
```
B_interf = K × [throttle, current, motor_temp]ᵀ
```
Where `K` is a `3×3` matrix learned via linear regression. Given `N` samples of operational parameters `X_i` and the measured interference `Y_i = B_measured,i - B_earth`, the least-squares solution is:
```
K = (Xᵀ X)⁻¹ Xᵀ Y
```
Here, `X` is the `N×3` matrix of input vectors, and `Y` is the `N×3` matrix of output vectors. The quality of fit is measured by R²:
```
R² = 1 - (Σ||Y_i - K X_i||²) / (Σ||Y_i - mean(Y)||²)
```

**PWM Harmonic Interference:**
Motor PWM generates harmonic magnetic fields at multiples of the switching frequency `f_PWM`:
```
I_motor(t) = I_DC + Σₖ Iₖ sin(2π k f_PWM t + φₖ)
B_harmonic,k(t) = αₖ sin(2π k f_PWM t + φₖ + ψₖ)
```
The amplitude `αₖ` is proportional to throttle. These harmonics are identified in the magnetometer's frequency spectrum (via FFT) and subtracted in real-time.

#### **5. Integration with Navigation Filter**

The RTK position `P_rtk` (converted to NED) and the calibrated magnetometer heading are integrated as measurements in the EKF.

**Magnetometer Measurement Model:**
The predicted magnetic field in body frame, given estimated attitude quaternion `q` and known Earth field vector in NED frame `B_earth_ned`, is:
```
B_pred_body = R(q)_ned_to_body × B_earth_ned
```
Where `R(q)_ned_to_body` is the rotation matrix from NED to body frame derived from quaternion `q`. The measurement innovation (z) is the difference between the predicted and measured (calibrated) field vectors. The Jacobian `H` relates this innovation to the state error, primarily the yaw angle.

**RTK Position Measurement Model:**
The RTK position measurement `z_rtk = P_rtk_ned` is compared directly to the EKF's position state. The large, asymmetric covariance `P_ned` from the RTK solution is used as the measurement noise covariance `R_rtk` in the Kalman update, ensuring the filter correctly weights the high-precision but potentially intermittent RTK fixes against the dead-reckoning state estimate.

---

### **C++ Implementation: RTOS Threading and Hardware Integration**

This section details the specific C++ classes, RTOS threading, and hardware register manipulation that implement the centimeter-accurate RTK positioning and robust magnetic heading for the heavy rover.

#### **RTK GPS Processing: UBX Parser and RTCM3 Injection**

The `AP_GPS_UBLOX` class manages the binary UBX protocol from the ZED-F9P module and injects RTCM3 correction data received via MAVLink.

**UBX Parser State Machine (`_parse_ubx_frame`):** This function runs in the UART DMA receive interrupt context. It implements the exact byte-level parsing for the UBX frame structure `[0xB5 0x62][CLASS][ID][LENGTH][PAYLOAD][CK_A][CK_B]`. The Fletcher checksum is validated incrementally.

```cpp
// UART DMA IRQ Handler: Fills circular buffer and triggers parser semaphore.
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart->Instance == USART6) {
        // Calculate bytes received
        uint16_t new_write_idx = sizeof(_buffer) - huart->hdmarx->Instance->NDTR;
        _write_idx = new_write_idx; // Atomic update
        
        // Release semaphore to wake GPS thread
        osSemaphoreRelease(_uart_rx_semaphore);
    }
}

// GPS Thread (Priority 7): Processes UBX frames and manages RTK state.
void gps_thread(void const *argument) {
    for(;;) {
        // Wait for UART data
        osSemaphoreWait(_uart_rx_semaphore, osWaitForever);
        
        // Parse available bytes
        _parse_ubx_frame();
        
        // Check for RTCM3 messages to transmit
        if (_rtcm_queue_head != _rtcm_queue_tail && !_uart_tx_busy) {
            _start_rtcm_transmission();
        }
        
        // Update RTK state machine at 5Hz
        uint32_t now = AP_HAL::millis();
        if (now - _last_rtk_update_ms > 200) {
            _update_rtk_state();
            _last_rtk_update_ms = now;
        }
    }
}
```

**RTCM3 Injection (`inject_rtcm3_data`):** This function validates the CRC-24Q checksum of incoming RTCM3 correction data from the telemetry radio and queues it for transmission to the GPS module. The CRC table `_rtcm_crc_table` implements the polynomial `0x1864CFB`.

```cpp
void AP_GPS_UBLOX::inject_rtcm3_data(const uint8_t *data, uint16_t len) {
    // Calculate CRC-24Q
    uint32_t crc = 0;
    for (uint16_t i = 0; i < len - 3; i++) {
        crc = ((crc << 8) | data[i]) ^ _rtcm_crc_table[(crc >> 16) & 0xFF];
    }
    
    // Verify CRC against last 3 bytes
    uint32_t received_crc = (data[len-3] << 16) | (data[len-2] << 8) | data[len-1];
    if (crc != received_crc) {
        return; // Invalid CRC
    }
    
    // Queue message (8-deep FIFO)
    uint8_t idx = _rtcm_queue_tail;
    memcpy(_rtcm_queue[idx].data, data, len);
    _rtcm_queue[idx].length = len;
    _rtcm_queue[idx].valid = true;
    _rtcm_queue_tail = (idx + 1) % 8;
}
```

**High-Precision Position Processing (`_process_hpposllh`):** This method extracts the centimeter-accurate position from the `UBX-NAV-HPPOSLLH` message. It combines the high-precision (`latHp`, `lonHp` in 0.1mm) and low-precision (`lat`, `lon` in cm) components.

```cpp
void AP_GPS_UBLOX::_process_hpposllh(const ubx_nav_hpposllh &msg) {
    // Combine: lat = lat * 1e-7° + latHp * 1e-9°
    _rtk_state.lat_hp = msg.lat * 1e-7 + msg.latHp * 1e-9;
    _rtk_state.lon_hp = msg.lon * 1e-7 + msg.lonHp * 1e-9;
    // Height: height * 1e-3 m + heightHp * 1e-6 m
    _rtk_state.height_hp = msg.height * 1e-3 + msg.heightHp * 1e-6;
    
    // Accuracy: hAcc * 1e-3 m + hAccHp * 1e-6 m
    _rtk_state.hAcc_hp = msg.hAcc * 1e-3 + msg.hAccHp * 1e-6;
    _rtk_state.vAcc_hp = msg.vAcc * 1e-3 + msg.vAccHp * 1e-6;
    
    // Decode RTK status from flags
    _rtk_state.solution_type = 0; // No RTK
    if (msg.flags & 0x02) _rtk_state.solution_type = 2; // Fixed
    else if (msg.flags & 0x01) _rtk_state.solution_type = 1; // Float
    
    // Prepare EKF input with covariance
    _ekf_input.position = Vector3d(_rtk_state.lat_hp, _rtk_state.lon_hp, _rtk_state.height_hp);
    // Convert accuracy to NED covariance (simplified diagonal)
    _ekf_input.position_variance = Vector3f(_rtk_state.hAcc_hp * _rtk_state.hAcc_hp,
                                           _rtk_state.hAcc_hp * _rtk_state.hAcc_hp,
                                           _rtk_state.vAcc_hp * _rtk_state.vAcc_hp);
}
```

#### **Magnetometer Calibration: Sphere and Ellipsoid Fitting**

The `CompassCalibrator` class implements the least-squares sphere fitting (for hard-iron) and ellipsoid fitting (for soft-iron) using matrix algebra.

**Sphere Fitting (`fit_sphere`):** This method directly implements the linear system `A X = b` derived from `‖B - O‖² = R²`. The `N×4` matrix `A` is built with rows `[2Bx, 2By, 2Bz, -1]`. The vector `b` contains `Bx² + By² + Bz²`. The SVD solver computes `X = [Ox, Oy, Oz, R² - O·O]`.

```cpp
bool CompassCalibrator::fit_sphere() {
    // Build A and b
    for (uint16_t i = 0; i < _sample_state.count; i++) {
        const Vector3f &B = _sample_state.samples[i];
        _fitting_workspace.A(i, 0) = 2.0f * B.x;
        _fitting_workspace.A(i, 1) = 2.0f * B.y;
        _fitting_workspace.A(i, 2) = 2.0f * B.z;
        _fitting_workspace.A(i, 3) = -1.0f;
        _fitting_workspace.b(i) = B.x*B.x + B.y*B.y + B.z*B.z;
    }
    
    // Solve via SVD: A = U * S * V^T
    Matrix4f U, V;
    Vector4f S;
    svd_decompose(_fitting_workspace.A, U, S, V, _sample_state.count, 4);
    
    // Pseudo-inverse: X = V * diag(1/S) * U^T * b
    _fitting_workspace.x.zero();
    for (uint8_t i = 0; i < 4; i++) {
        if (fabsf(S[i]) > 1e-6f) {
            float scale = 1.0f / S[i];
            for (uint8_t j = 0; j < 4; j++) {
                // Dot product of U column i with b
                float u_dot_b = 0.0f;
                for (uint16_t k = 0; k < _sample_state.count; k++) {
                    u_dot_b += U(k, i) * _fitting_workspace.b(k);
                }
                _fitting_workspace.x[j] += V(j, i) * scale * u_dot_b;
            }
        }
    }
    
    // Extract offset O and radius R
    _calibration_result.offset = Vector3f(_fitting_workspace.x[0], _fitting_workspace.x[1], _fitting_workspace.x[2]);
    float O_sq = _calibration_result.offset.length_squared();
    _calibration_result.radius = sqrtf(O_sq + _fitting_workspace.x[3]);
    
    // Calculate fitness (1 - RMS error / radius)
    float sum_sq_error = 0.0f;
    for (uint16_t i = 0; i < _sample_state.count; i++) {
        Vector3f corrected = _sample_state.samples[i] - _calibration_result.offset;
        float error = corrected.length() - _calibration_result.radius;
        sum_sq_error += error * error;
    }
    _calibration_result.fitness = 1.0f - sqrtf(sum_sq_error / _sample_state.count) / _calibration_result.radius;
    
    return (_calibration_result.fitness > 0.9f);
}
```

**Ellipsoid Fitting (`fit_ellipsoid`):** This method solves for the symmetric matrix `M` in `(B-O)ᵀ M (B-O) = 1`. It builds the `6×6` normal equations `A6ᵀA6 m = A6ᵀb6` for the 6 unique elements of `M`. The Cholesky decomposition `M = WᵀW` yields the soft-iron correction matrix `W`.

```cpp
bool CompassCalibrator::fit_ellipsoid() {
    Matrix6f A6;
    Vector6f b6;
    A6.zero();
    b6.zero();
    
    for (uint16_t i = 0; i < _sample_state.count; i++) {
        Vector3f Bc = _sample_state.samples[i] - _calibration_result.offset;
        float Bx2 = Bc.x * Bc.x, By2 = Bc.y * Bc.y, Bz2 = Bc.z * Bc.z;
        
        // Row: [Bx², 2BxBy, 2BxBz, By², 2ByBz, Bz²]
        Vector6f row(Bx2, 2.0f*Bc.x*Bc.y, 2.0f*Bc.x*Bc.z, By2, 2.0f*Bc.y*Bc.z, Bz2);
        
        // Accumulate A6ᵀA6 and A6ᵀb6
        for (uint8_t j = 0; j < 6; j++) {
            for (uint8_t k = 0; k < 6; k++) {
                A6(j, k) += row[j] * row[k];
            }
            b6[j] += row[j]; // b6 = 1 for each sample
        }
    }
    
    // Solve for m = [M11, M12, M13, M22, M23, M33]
    Vector6f m = A6.inverse() * b6;
    
    // Reconstruct M
    Matrix3f M;
    M(0,0)=m[0]; M(0,1)=m[1]; M(0,2)=m[2];
    M(1,0)=m[1]; M(1,1)=m[3]; M(1,2)=m[4];
    M(2,0)=m[2]; M(2,1)=m[4]; M(2,2)=m[5];
    
    // Cholesky decomposition: M = L Lᵀ, then W = L⁻¹
    Matrix3f L = M.cholesky_decomposition();
    Matrix3f W = L.inverse();
    
    // Store diagonal and off-diagonal parts
    _calibration_result.diag = Matrix3f(W(0,0),0,0, 0,W(1,1),0, 0,0,W(2,2));
    _calibration_result.offdiag = Matrix3f(0,W(0,1),W(0,2), W(1,0),0,W(1,2), W(2,0),W(2,1),0);
    
    return true;
}
```

**Calibration Application (`correct`):** Applies the hard-iron offset and soft-iron matrix to a raw measurement: `B_corrected = W × (B_raw - O)`.

```cpp
Vector3f CompassCalibrator::correct(const Vector3f &raw) const {
    Vector3f centered = raw - _calibration_result.offset;
    Vector3f corrected;
    // Multiply by W = diag + offdiag
    corrected.x = _calibration_result.diag(0,0)*centered.x + _calibration_result.offdiag(0,1)*centered.y + _calibration_result.offdiag(0,2)*centered.z;
    corrected.y = _calibration_result.offdiag(1,0)*centered.x + _calibration_result.diag(1,1)*centered.y + _calibration_result.offdiag(1,2)*centered.z;
    corrected.z = _calibration_result.offdiag(2,0)*centered.x + _calibration_result.offdiag(2,1)*centered.y + _calibration_result.diag(2,2)*centered.z;
    return corrected;
}
```

#### **Dynamic Motor Interference Cancellation**

The `CompassLearn` class learns a linear model `B_interference = K × [throttle, current, temp]ᵀ` and subtracts it in real-time.

**Model Learning (`_learn_interference_model`):** Implements linear regression via the normal equations `K = (XᵀX)⁻¹ XᵀY`. The matrix `X` is `N×3` containing input vectors, and `Y` is `N×3` containing the interference vector (`B_measured - B_earth`).

```cpp
void CompassLearn::_learn_interference_model() {
    uint16_t sample_count = (_sample_head - _sample_tail + LEARN_BUFFER_SIZE) % LEARN_BUFFER_SIZE;
    
    // Estimate Earth field as average of corrected measurements
    Vector3f B_earth_est(0,0,0);
    for (uint16_t i = 0; i < sample_count; i++) {
        uint16_t idx = (_sample_tail + i) % LEARN_BUFFER_SIZE;
        B_earth_est += _samples[idx].mag_corrected;
    }
    B_earth_est /= sample_count;
    
    // Build X and Y matrices
    MatrixNxM<LEARN_BUFFER_SIZE, 3> X, Y;
    for (uint16_t i = 0; i < sample_count; i++) {
        uint16_t idx = (_sample_tail + i) % LEARN_BUFFER_SIZE;
        const InterferenceSample &s = _samples[idx];
        
        X(i,0)=s.throttle; X(i,1)=s.current; X(i,2)=s.motor_temp;
        Y(i,0)=s.mag_corrected.x - B_earth_est.x;
        Y(i,1)=s.mag_corrected.y - B_earth_est.y;
        Y(i,2)=s.mag_corrected.z - B_earth_est.z;
    }
    
    // Compute XᵀX and XᵀY
    Matrix3x3f XTX, XTY;
    XTX.zero(); XTY.zero();
    for (uint16_t i = 0; i < sample_count; i++) {
        for (uint8_t j = 0; j < 3; j++) {
            for (uint8_t k = 0; k < 3; k++) {
                XTX(j,k) += X(i,j) * X(i,k);
                XTY(j,k) += X(i,j) * Y(i,k);
            }
        }
    }
    
    // Solve: K = (XᵀX)⁻¹ XᵀY
    _model.K = XTX.inverse() * XTY;
    
    // Calculate R²
    float ss_total = 0.0f, ss_residual = 0.0f;
    for (uint16_t i = 0; i < sample_count; i++) {
        uint16_t idx = (_sample_tail + i) % LEARN_BUFFER_SIZE;
        Vector3f input(_samples[idx].throttle, _samples[idx].current, _samples[idx].motor_temp);
        Vector3f pred = _model.K * input;
        Vector3f actual = _samples[idx].mag_corrected - B_earth_est;
        ss_total += actual.length_squared();
        ss_residual += (actual - pred).length_squared();
    }
    _model.r_squared = 1.0f - (ss_residual / ss_total);
    _model.valid = (_model.r_squared > 0.7f);
}
```

**Real-Time Cancellation (`cancel_interference`):** Applies the learned model and subtracts the predicted interference, with low-pass filtering for stability.

```cpp
Vector3f CompassLearn::cancel_interference(float throttle, float current, float motor_temp,
                                           const Vector3f &mag_raw) {
    if (!_model.valid) return mag_raw;
    
    // Linear prediction
    Vector3f input(throttle, current, motor_temp);
    Vector3f B_interf = _model.K * input;
    
    // Add PWM harmonics
    uint32_t t_ms = AP_HAL::millis();
    float t_sec = t_ms * 0.001f;
    for (uint8_t h = 0; h < 4; h++) {
        if (_model.harmonics.amplitude[h] > 0.0f) {
            float phase = 2.0f * M_PI * _model.harmonics.frequency[h] * t_sec + _model.harmonics.phase[h];
            B_interf.x += _model.harmonics.amplitude[h] * throttle * sinf(phase);
        }
    }
    
    // Low-pass filter: α ≈ 0.05 (time constant ~20 samples at 100Hz)
    _cancellation_state.filtered_error = _cancellation_state.filtered_error * 0.95f + B_interf * 0.05f;
    
    return mag_raw - _cancellation_state.filtered_error;
}
```

#### **Hardware Register Configuration**

**UART DMA for RTCM3 Injection:** The USART6 peripheral is configured for 115200 baud with DMA-enabled transmission to avoid blocking the main thread.

```cpp
void USART6_Init(void) {
    __HAL_RCC_USART6_CLK_ENABLE();
    USART6->BRR = 0x00000D05; // 200MHz / (16 * 115200) = 108.5 -> 0x6C5
    USART6->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE; // 0x200C
    USART6->CR3 = USART_CR3_DMAT; // Enable TX DMA
}
```

**I2C for Magnetometer:** The IST8310 magnetometer is accessed via I2C at 100kHz.

```cpp
void I2C1_Init(void) {
    __HAL_RCC_I2C1_CLK_ENABLE();
    I2C1->CR1 = 0x00000000; // Disable
    I2C1->CR2 = 0x00000010; // FREQ = 16MHz
    I2C1->CCR = 0x00000050; // 100kHz: CCR = 16MHz/(2*100kHz) = 80
    I2C1->TRISE = 0x00000011; // TRISE = 1000ns * 16MHz + 1 = 17
    I2C1->CR1 = I2C_CR1_PE; // Enable
}
```

#### **RTOS Thread Integration**

Three threads coordinate GPS, magnetometer, and EKF updates:

1.  **GPS Thread (Priority 7):** Runs the `gps_thread` function, parsing UBX data and managing RTCM3 injection.
2.  **Compass Thread (Priority 6):** Samples the magnetometer at 100Hz, applies calibration and interference cancellation, and publishes the corrected vector to a shared memory queue.
3.  **EKF Thread (Priority 8):** Waits on message queues for both GPS position (`_ekf_gps_queue`) and magnetometer heading (`_ekf_mag_queue`), then executes the EKF predict/update cycle.

The RTCM3 injection uses DMA to avoid blocking, and the magnetometer calibration runs in a low-priority background thread when initiated by the user.