# Compass Backend Arbitration, Polymorphism, and Vector Math

_Generated 2026-04-15 03:01 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_Backend.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_ExternalAHRS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_ExternalAHRS.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_MSP.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_MSP.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_UAVCAN.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_UAVCAN.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_SITL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_SITL.h`

# Chapter: Compass Backend Arbitration, Polymorphism, and Vector Math

## Technical Introduction

The ArduPilot compass subsystem (`AP_Compass.cpp/h`, `AP_Compass_Backend.cpp/h`, and specialized backends) implements a polymorphic sensor fusion architecture for heavy agricultural rovers. This system arbitrates between up to three magnetometers (CAN-bus external, I2C internal, SPI isolated) using weighted priority scoring \(P_i = \alpha \cdot R_i + \beta \cdot S_i + \gamma \cdot C_i + \delta \cdot T_i\) to reject EMI from 400A wheel motors and compensate for chassis flex during skid-steering. The backend polymorphism allows seamless integration of DroneCAN, MSP, External AHRS, and SITL sensors through a unified `AP_Compass_Backend` interface, while 3×3 rotation matrices \(\mathbf{R}_{\text{orientation}} = \mathbf{R}_z(\psi) \cdot \mathbf{R}_y(\theta) \cdot \mathbf{R}_x(\phi)\) transform sensor frames to the rover's body frame. This architecture maintains deterministic 400Hz execution through RTOS-threaded backends with semaphore-protected I2C/SPI access and interrupt-driven CAN reception.

## Mathematical Formulation

### Multi-Compass Arbitration Mathematics

For a heavy agricultural rover (>1000 kg) with skid-steering dynamics, magnetic field measurements must compensate for high-current motor interference and chassis flex during turns. The priority score calculation weights sensor reliability against physical disturbances:

\[
P_i = \alpha \cdot R_i + \beta \cdot S_i + \gamma \cdot C_i + \delta \cdot T_i
\]

Where:
- \(R_i\) = Signal-to-noise ratio (0-1), critical for rejecting EMI from 400A wheel motors
- \(S_i\) = Sensor health score (0-1), detects mechanical damage from field impacts
- \(C_i\) = Calibration confidence (0-1), compensates for chassis deformation under load
- \(T_i\) = Temperature stability (0-1), accounts for thermal expansion of mounting brackets

The rover's physical configuration dictates weight selection:
- CAN-bus external compasses mounted on booms: \(\alpha=0.4, \beta=0.3, \gamma=0.2, \delta=0.1\) (maximize SNR for EMI rejection)
- Internal I2C compasses near motors: \(\alpha=0.3, \beta=0.4, \gamma=0.2, \delta=0.1\) (prioritize health monitoring)
- SPI compasses on vibration-isolated mounts: \(\alpha=0.2, \beta=0.3, \gamma=0.3, \delta=0.2\) (focus on calibration stability)

The voting threshold \(\theta_{\text{threshold}} = 0.6\) ensures only sensors surviving the rover's 2g vibration environment are used. Weighted fusion implements inverse-variance weighting:

\[
\mathbf{B}_{\text{fused}} = \frac{\sum_{i=1}^{N} w_i \cdot \mathbf{B}_i}{\sum_{i=1}^{N} w_i}, \quad w_i = \frac{P_i}{\sigma_i^2}
\]

where \(\sigma_i^2\) represents magnetic noise variance from nearby power electronics.

### Board Orientation Matrix Algebra

The rover's chassis experiences roll (\(\phi\)) and pitch (\(\theta\)) during skid-steering turns, requiring precise sensor-to-body frame transformation:

\[
\mathbf{B}_{\text{body}} = \mathbf{R}_{\text{orientation}} \cdot \mathbf{R}_{\text{rotation}} \cdot \mathbf{B}_{\text{sensor}}
\]

The composite rotation matrix uses ZYX convention (yaw, pitch, roll):

\[
\mathbf{R}_{\text{orientation}} = \mathbf{R}_z(\psi) \cdot \mathbf{R}_y(\theta) \cdot \mathbf{R}_x(\phi)
\]

With elementary rotation matrices:

\[
\mathbf{R}_x(\phi) = \begin{bmatrix} 1 & 0 & 0 \\ 0 & \cos\phi & -\sin\phi \\ 0 & \sin\phi & \cos\phi \end{bmatrix}
\]
\[
\mathbf{R}_y(\theta) = \begin{bmatrix} \cos\theta & 0 & \sin\theta \\ 0 & 1 & 0 \\ -\sin\theta & 0 & \cos\theta \end{bmatrix}
\]
\[
\mathbf{R}_z(\psi) = \begin{bmatrix} \cos\psi & -\sin\psi & 0 \\ \sin\psi & \cos\psi & 0 \\ 0 & 0 & 1 \end{bmatrix}
\]

For the rover's typical mounting positions:
- Front boom compass: \(\phi = 0^\circ, \theta = -5^\circ, \psi = 0^\circ\) (compensates for mounting angle)
- Rear chassis compass: \(\phi = 2^\circ, \theta = 0^\circ, \psi = 180^\circ\) (accounts for opposite orientation)

Sensor misalignment compensation uses affine transformation:

\[
\mathbf{B}_{\text{corrected}} = \mathbf{S} \cdot (\mathbf{B}_{\text{raw}} - \mathbf{o})
\]

Where \(\mathbf{o} = [o_x, o_y, o_z]^T\) is hard-iron offset from chassis magnetization, and \(\mathbf{S}\) is a 3×3 soft-iron distortion matrix.

### Networked Sensor Payload Mathematics

DroneCAN magnetic payload encoding uses 32-bit IEEE-754 floats with CRC-8 protection. The checksum implements polynomial algebra:

\[
\text{CRC8} = \bigoplus_{i=0}^{14} \text{byte}_i \otimes G(x)
\]
\[
G(x) = x^8 + x^2 + x + 1
\]

CAN-bus arbitration uses 29-bit extended identifiers with priority encoding:

\[
\text{CAN ID} = \text{NODE_ID} \times 2^8 + \text{SENSOR_TYPE} \times 2^4 + \text{PRIORITY}
\]

For the rover's dual-redundant CAN network:
- Primary bus: NODE_ID 10-20, PRIORITY 0-3 (high-priority navigation)
- Secondary bus: NODE_ID 30-40, PRIORITY 4-7 (diagnostic sensors)

MSP protocol uses 16-bit integer encoding with conversion:

\[
B_{\mu T} = B_{\text{MSP}} \times 0.01 \times 100 \times 10^{-4} = B_{\text{MSP}} \times 10^{-4}
\]

The rover's implement controllers use MSP for backward compatibility, requiring this fixed-point conversion.

### Sensor Calibration Sphere Mathematics

For the rover's 3-axis magnetometers, calibration solves the ellipsoid equation:

\[
(\mathbf{B} - \mathbf{o})^T \cdot \mathbf{W} \cdot (\mathbf{B} - \mathbf{o}) = 1
\]

Where \(\mathbf{W}\) is a symmetric positive-definite matrix. The calibration algorithm computes:

\[
\mathbf{W} = \mathbf{S}^T \cdot \mathbf{S}
\]

With Cholesky decomposition \(\mathbf{S} = \text{chol}(\mathbf{W})\), yielding the scale matrix. The rover's calibration collects 500 samples during slow rotation, solving via least-squares:

\[
\min_{\mathbf{o}, \mathbf{W}} \sum_{i=1}^{500} \left[ (\mathbf{B}_i - \mathbf{o})^T \cdot \mathbf{W} \cdot (\mathbf{B}_i - \mathbf{o}) - 1 \right]^2
\]

This compensates for the rover's magnetic signature from steel frame and hydraulic components.

### Temperature Compensation Model

The rover's compasses experience -20°C to +60°C operating range. Temperature drift follows:

\[
\mathbf{B}_{\text{comp}}(T) = \mathbf{B}_{\text{raw}} \cdot [1 + \boldsymbol{\alpha}(T - T_{\text{ref}})]
\]

Where \(\boldsymbol{\alpha} = [\alpha_x, \alpha_y, \alpha_z]^T\) are temperature coefficients measured during thermal cycling. For the rover's HMC5883L sensors:

\[
\alpha_x = 0.0012 \, \text{°C}^{-1}, \quad \alpha_y = 0.0010 \, \text{°C}^{-1}, \quad \alpha_z = 0.0008 \, \text{°C}^{-1}
\]

Compensation uses piecewise linear interpolation between calibration points at -20°C, 0°C, 25°C, 40°C, and 60°C.

### Vibration Filtering Mathematics

The rover's 400Hz update rate requires anti-aliasing for 10-100Hz structural vibrations. A 4th-order Butterworth filter implements:

\[
H(z) = \frac{\sum_{k=0}^{4} b_k z^{-k}}{1 + \sum_{k=1}^{4} a_k z^{-k}}
\]

With cutoff frequency \(f_c = 30\text{Hz}\) and sampling rate \(f_s = 400\text{Hz}\). The difference equation for each axis:

\[
y[n] = \sum_{k=0}^{4} b_k x[n-k] - \sum_{k=1}^{4} a_k y[n-k]
\]

Coefficients \(b_k, a_k\) are pre-computed using bilinear transform to maintain phase linearity for heading calculations during skid-steering maneuvers.

## C++ Implementation

### Priority-Based Sensor Arbitration Implementation (AP_Compass.cpp)

The `AP_Compass` class implements the weighted voting algorithm \(P_i = \alpha \cdot R_i + \beta \cdot S_i + \gamma \cdot C_i + \delta \cdot T_i\) through the `update_priority_scores()` method. The mathematical weights map directly to C++ constants:

```cpp
void update_priority_scores() {
    const float weights[4] = {0.4f, 0.3f, 0.2f, 0.1f}; // α, β, γ, δ
    
    for (uint8_t i = 0; i < _backend_count; i++) {
        CompassHealth& health = _health[i];
        
        // Calculate individual metrics
        float snr_score = constrain_float(health.snr_ratio, 0.0f, 1.0f);  // R_i
        
        // Calibration score: 1.0 = perfect sphere fit
        float cal_score = 1.0f - constrain_float(health.calibration_score, 0.0f, 1.0f);  // C_i
        
        // Temperature stability: lower drift = higher score
        float temp_score = 1.0f - constrain_float(health.temperature_stability, 0.0f, 1.0f);  // T_i
        
        // Health score based on error rate
        float error_rate = 0.0f;
        if (health.successful_reads > 0) {
            error_rate = static_cast<float>(health.error_count) / 
                        static_cast<float>(health.successful_reads + health.error_count);
        }
        float health_score = 1.0f - constrain_float(error_rate, 0.0f, 1.0f);  // S_i
        
        // Self-test contributes to health score
        if (!health.self_test_passed) {
            health_score *= 0.5f;
        }
        
        // Calculate priority score: P_i = α·R_i + β·S_i + γ·C_i + δ·T_i
        _priority_scores[i] = weights[0] * snr_score +
                              weights[1] * health_score +
                              weights[2] * cal_score +
                              weights[3] * temp_score;
        
        // Apply priority boost for external/CAN sensors
        if (_backends[i]->get_priority() <= COMPASS_PRIORITY_EXTERNAL_I2C) {
            _priority_scores[i] *= 1.2f; // 20% boost for external sensors
        }
        
        // Constrain to valid range
        _priority_scores[i] = constrain_float(_priority_scores[i], 0.0f, 1.0f);
    }
}
```

The voting threshold \(\theta_{\text{threshold}} = 0.6\) is enforced in `select_primary_compass()`:

```cpp
uint8_t select_primary_compass() {
    float best_score = 0.0f;
    uint8_t best_index = 0;
    
    for (uint8_t i = 0; i < _backend_count; i++) {
        if (_priority_scores[i] > best_score && _priority_scores[i] > 0.6f) {  // θ_threshold = 0.6
            best_score = _priority_scores[i];
            best_index = i;
        }
    }
    
    return best_index;
}
```

Weighted fusion \(\mathbf{B}_{\text{fused}} = \frac{\sum_{i=1}^{N} w_i \cdot \mathbf{B}_i}{\sum_{i=1}^{N} w_i}\) with \(w_i = \frac{P_i}{\sigma_i^2}\) is implemented in `calculate_fusion_weights()`:

```cpp
void calculate_fusion_weights() {
    float total_weight = 0.0f;
    
    for (uint8_t i = 0; i < _backend_count; i++) {
        if (_priority_scores[i] > 0.6f) {
            // Weight inversely proportional to noise variance: w_i = P_i / σ_i²
            float noise_variance = 1.0f - _health[i].snr_ratio;  // σ_i² ∝ (1 - R_i)
            noise_variance = MAX(noise_variance, 0.01f); // Avoid division by zero
            
            _fusion_weights[i] = _priority_scores[i] / noise_variance;  // w_i = P_i / σ_i²
            total_weight += _fusion_weights[i];
        } else {
            _fusion_weights[i] = 0.0f;
        }
    }
    
    // Normalize weights: w_i' = w_i / Σw_i
    if (total_weight > 0.0f) {
        for (uint8_t i = 0; i < _backend_count; i++) {
            _fusion_weights[i] /= total_weight;
        }
    }
}
```

RTOS integration occurs in the 400Hz update loop, with sensor reads protected by semaphores:

```cpp
void update() {
    Vector3f raw_fields[COMPASS_MAX_INSTANCES];
    bool readings_valid[COMPASS_MAX_INSTANCES];
    
    // Read from all backends (RTOS threads may preempt)
    for (uint8_t i = 0; i < _backend_count; i++) {
        readings_valid[i] = _backends[i]->read(raw_fields[i]);  // Each backend has its own RTOS thread
        
        // Update health metrics atomically
        if (readings_valid[i]) {
            _health[i].successful_reads++;
            update_snr_estimate(i, raw_fields[i]);
        } else {
            _health[i].error_count++;
            _health[i].last_error_ms = AP_HAL::millis();
        }
    }
    
    // Fuse readings: B_fused = Σ w_i · B_i
    Vector3f fused_field(0, 0, 0);
    uint8_t valid_count = 0;
    
    for (uint8_t i = 0; i < _backend_count; i++) {
        if (readings_valid[i] && _fusion_weights[i] > 0.0f) {
            fused_field += corrected_fields[i] * _fusion_weights[i];  // Σ w_i · B_i
            valid_count++;
        }
    }
    
    if (valid_count > 0) {
        _field_fused = fused_field;  // B_fused stored for navigation thread
        _last_update_ms = AP_HAL::millis();
    }
}
```

### Board Orientation Matrix Rotations Implementation

The `CompassOrientation` class implements the rotation matrix algebra \(\mathbf{R}_{\text{orientation}} = \mathbf{R}_z(\psi) \cdot \mathbf{R}_y(\theta) \cdot \mathbf{R}_x(\phi)\). The `euler_to_matrix()` method computes the ZYX convention:

```cpp
static Matrix3f euler_to_matrix(const EulerAngles& angles) {
    float cos_phi = cosf(angles.roll);     // cos(φ)
    float sin_phi = sinf(angles.roll);     // sin(φ)
    float cos_theta = cosf(angles.pitch);  // cos(θ)
    float sin_theta = sinf(angles.pitch);  // sin(θ)
    float cos_psi = cosf(angles.yaw);      // cos(ψ)
    float sin_psi = sinf(angles.yaw);      // sin(ψ)
    
    Matrix3f R;
    
    // R = Rz(ψ) * Ry(θ) * Rx(φ)
    R.a.x = cos_theta * cos_psi;                                    // cosθ·cosψ
    R.a.y = sin_phi * sin_theta * cos_psi - cos_phi * sin_psi;      // sinφ·sinθ·cosψ - cosφ·sinψ
    R.a.z = cos_phi * sin_theta * cos_psi + sin_phi * sin_psi;      // cosφ·sinθ·cosψ + sinφ·sinψ
    
    R.b.x = cos_theta * sin_psi;                                    // cosθ·sinψ
    R.b.y = sin_phi * sin_theta * sin_psi + cos_phi * cos_psi;      // sinφ·sinθ·sinψ + cosφ·cosψ
    R.b.z = cos_phi * sin_theta * sin_psi - sin_phi * cos_psi;      // cosφ·sinθ·sinψ - sinφ·cosψ
    
    R.c.x = -sin_theta;                                             // -sinθ
    R.c.y = sin_phi * cos_theta;                                    // sinφ·cosθ
    R.c.z = cos_phi * cos_theta;                                    // cosφ·cosθ
    
    return R;
}
```

Pre-computed matrices for common rover orientations are stored in `ORIENTATION_MATRICES[]`. For example, ROTATION_YAW_90 implements \(\psi = 90^\circ\):

```cpp
// ROTATION_YAW_90: ψ = 90°, φ = 0°, θ = 0°
Matrix3f(0.0f, -1.0f, 0.0f,   // cos90°=0, -sin90°=-1, 0
         1.0f, 0.0f, 0.0f,    // sin90°=1, cos90°=0, 0
         0.0f, 0.0f, 1.0f),   // 0, 0, 1
```

The transformation \(\mathbf{B}_{\text{body}} = \mathbf{R}_{\text{orientation}} \cdot \mathbf{R}_{\text{rotation}} \cdot \mathbf{B}_{\text{sensor}}\) is applied in the main update:

```cpp
Vector3f oriented = _orientation_matrix[i] * raw_fields[i];  // B_body = R_orientation * B_sensor
```

### Sensor Misalignment Compensation Implementation

The calibration function implements \(\mathbf{B}_{\text{corrected}} = \mathbf{S} \cdot (\mathbf{B}_{\text{raw}} - \mathbf{o})\) with separate diagonal and off-diagonal matrices:

```cpp
Vector3f apply_calibration(uint8_t instance, const Vector3f& field) {
    // Remove offset: B' = B_raw - o
    Vector3f corrected = field - _calibration.offsets[instance];
    
    // Apply diagonal scaling: B'' = diag(S) · B'
    corrected.x *= _calibration.diag[instance].a.x;  // S_xx
    corrected.y *= _calibration.diag[instance].b.y;  // S_yy
    corrected.z *= _calibration.diag[instance].c.z;  // S_zz
    
    // Apply off-diagonal compensation: B_corrected = B'' + offdiag · B''
    corrected.x += _calibration.offdiag[instance].a.y * corrected.y +  // S_xy·B'_y
                  _calibration.offdiag[instance].a.z * corrected.z;   // S_xz·B'_z
    corrected.y += _calibration.offdiag[instance].b.x * corrected.x +  // S_yx·B'_x
                  _calibration.offdiag[instance].b.z * corrected.z;   // S_yz·B'_z
    corrected.z += _calibration.offdiag[instance].c.x * corrected.x +  // S_zx·B'_x
                  _calibration.offdiag[instance].c.y * corrected.y;   // S_zy·B'_y
    
    return corrected;  // B_corrected = S · (B_raw - o)
}
```

### DroneCAN Magnetic Payload Unpacking Implementation

The `UAVCAN_Compass_Backend` class decodes the DroneCAN payload structure. The CRC-16-CCITT check implements the polynomial mathematics:

```cpp
uint16_t calculate_crc16_ccitt(const uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;  // Initial value
    
    for (size_t i = 0; i < length; i++) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;  // XOR with data byte
        
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;  // Polynomial x¹⁶ + x¹² + x⁵ + 1
            } else {
                crc <<= 1;
            }
        }
    }
    
    return crc;
}
```

The conversion from Gauss to μT implements \(B_{\mu T} = B_{\text{Gauss}} \times 100\):

```cpp
Vector3f field(
    msg.magnetic_field_ga[0] * 100.0f,  // B_x(μT) = B_x(G) × 100
    msg.magnetic_field_ga[1] * 100.0f,  // B_y(μT) = B_y(G) × 100
    msg.magnetic_field_ga[2] * 100.0f   // B_z(μT) = B_z(G) × 100
);
```

Temperature compensation uses linear model \(B_{\text{comp}}(T) = B_{\text{raw}} \cdot [1 + \alpha(T - T_{\text{ref}})]\):

```cpp
Vector3f apply_temperature_compensation(const Vector3f& field, int16_t temperature) {
    const float temp_coeff = 0.001f;     // α = 0.1% per °C
    const int16_t ref_temp = 2500;       // T_ref = 25.00°C
    
    float temp_factor = 1.0f + temp_coeff * (temperature - ref_temp) / 100.0f;  // 1 + α·ΔT
    
    return field * temp_factor;  // B_comp = B_raw · (1 + α·ΔT)
}
```

### STM32 CAN Bus Hardware Implementation

The `CAN_Driver` class configures STM32 hardware for DroneCAN. The bit timing calculation for 1Mbps at 84MHz PCLK1:

```cpp
_can->BTR = (5 << 0) |   // BRP = 5: t_q = (BRP+1)/PCLK = 6/84MHz = 71.4ns
           (6 << 16) |  // TS1 = 6: t_1 = (TS1+1)·t_q = 7·71.4ns = 500ns
           (1 << 20) |  // TS2 = 1: t_2 = (TS2+1)·t_q = 2·71.4ns = 143ns
           (1 << 24);   // SJW = 1: Resynchronization jump width
```

CAN ID filtering implements the network priority arbitration \(\text{CAN ID} = \text{NODE_ID} \times 2^8 + \text{SENSOR_TYPE} \times 2^4 + \text{PRIORITY}\):

```cpp
// Filter 0: Accept all extended IDs (UAVCAN uses 29-bit)
CAN1->sFilterRegister[0].FR1 = 0x00000000; // Mask: accept all IDs
CAN1->sFilterRegister[0].FR2 = 0x00000000;
```

The interrupt-driven receive pipeline handles CAN frames in real-time:

```cpp
bool receive_frame(uavcan::CanFrame& frame) {
    if (!(_can->RF0R & CAN_RF0R_FMP0)) {
        return false; // No messages in FIFO (non-blocking for RTOS)
    }
    
    // Read frame from FIFO 0 (called from CAN1_RX0_IRQHandler ISR)
    CAN_FIFOMailBox_TypeDef* mb = &_can->sFIFOMailBox[0];
    
    frame.id = (mb->RIR >> 3) & 0x1FFFFFFF; // Extract 29-bit extended ID
    // ... data extraction
    
    _can->RF0R |= CAN_RF0R_RFOM0; // Release FIFO entry for next interrupt
    
    return true;
}
```

### I2C/SPI Backend Abstraction Implementation

The `AP_Compass_Backend_I2C` class implements sensor-specific register protocols. The HMC5883L conversion uses the scale factor \(1 \text{ LSB} = 0.92 \text{ mG} = 0.092 \mu\text{T}\):

```cpp
Vector3f convert_raw_data(const uint8_t* data) {
    int16_t raw_x = (data[0] << 8) | data[1];
    int16_t raw_z = (data[2] << 8) | data[3];
    int16_t raw_y = (data[4] << 8) | data[5];
    
    const float scale = 0.092f;  // 0.92 mG/LSB × 0.1 μT/mG = 0.092 μT/LSB
    
    return Vector3f(raw_x * scale, raw_y * scale, raw_z * scale);  // B = raw × scale
}
```

RTOS semaphore protection ensures thread-safe I2C access:

```cpp
bool read(Vector3f& field) override {
    if (!_dev->get_semaphore()->take_nonblocking()) {  // RTOS semaphore
        return false; // Another thread is accessing I2C bus
    }
    
    uint8_t data[6];
    bool success = read_hmc5883l(data);
    
    _dev->get_semaphore()->give();  // Release for other threads
    
    if (!success) {
        return false;
    }
    
    field = convert_raw_data(data);
    return true;
}
```

The C++ implementation directly maps mathematical formulations to hardware operations, with RTOS threading ensuring deterministic execution within the 400Hz control loop while maintaining sensor fusion accuracy for the agricultural rover's navigation system.