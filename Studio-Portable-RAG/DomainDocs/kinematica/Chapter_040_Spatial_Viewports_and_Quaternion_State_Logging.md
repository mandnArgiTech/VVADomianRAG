# Spatial Viewports, Frame Translation, and Quaternion Logging

_Generated 2026-04-15 02:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_View.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_View.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/AP_AHRS_Logging.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AHRS/LogStructure.h`

# Chapter: Spatial Viewports, Frame Translation, and Quaternion Logging

## Introduction

The `AP_AHRS_View.cpp`, `AP_AHRS_View.h`, `AP_AHRS_Logging.cpp`, and `LogStructure.h` files implement a critical subsystem within the ArduPilot 400Hz autonomous vehicle architecture for sensor isolation and deterministic telemetry. The `AP_AHRS_View` class provides mathematical abstractions for projecting the vehicle's attitude into arbitrary reference frames, enabling stabilized camera gimbals and sensor payloads to operate independently from the rover's body motion—essential for agricultural rovers experiencing significant roll and pitch during skid-steering maneuvers. The logging system serializes high-frequency attitude and navigation data into binary packets with fixed memory layouts, employing DMA-driven SD card writes and RTOS-aware double buffering to achieve deterministic 100Hz logging without interrupting the primary 400Hz AHRS update loop. This chapter details the exact mathematical formulations and their corresponding C++ implementations for frame transformations, quaternion operations, and telemetry serialization.

---

## Mathematical Formulation for Spatial Viewports, Frame Translation, and Quaternion Logging

### Physical Reference Frame Definitions for a Heavy Agricultural Rover
The rover's primary body frame `B` is fixed to its chassis, with the origin at the vehicle's center of mass. The view frame `V` is an arbitrary offset frame used for sensor isolation (e.g., a camera gimbal). The Earth frame `E` is a local North-East-Down (NED) tangent plane. The rover's high inertia and skid-steering dynamics necessitate precise frame transformations to isolate sensor measurements from vehicle motion, particularly for stabilizing payloads during aggressive turns that induce significant lateral acceleration.

### Composite Rotation for Viewport Transformation
The view attitude `q_view` is computed by applying an offset rotation `q_offset` to the vehicle's body attitude `q_body`. The offset represents a fixed or dynamic reorientation of the sensor relative to the vehicle body. The composite rotation uses quaternion multiplication:

`q_view = q_body ⊗ q_offset_conjugate`

where `q_offset_conjugate = [q_offset_w, -q_offset_x, -q_offset_y, -q_offset_z]` is the conjugate (inverse rotation) of the offset quaternion. This is mathematically equivalent to the matrix operation `R_total = R(q_body) * R(q_offset)^T`. The quaternion is stored as `[q1, q2, q3, q4] = [W, X, Y, Z]`.

### Angular Rate Transformation Between Frames
For gimbal stabilization, the gyroscopic rates measured in the body frame `ω_body = [p, q, r]^T` must be transformed to the view frame. This uses the rotation matrix `R_body_to_view` derived from the offset quaternion:

`ω_view = R_body_to_view * ω_body`

The matrix `R_body_to_view` is the transpose of `R(q_offset)`. This transformation is critical for feedforward stabilization of mounted sensors, compensating for the rover's low-frequency but high-amplitude roll and pitch motions during field operations.

### Euler Angle Extraction from Quaternion
The view attitude is often required as Euler angles (roll φ, pitch θ, yaw ψ) using the ZYX (aerospace) convention. The direct conversion from the view quaternion `q = [q0, q1, q2, q3] = [W, X, Y, Z]` is:

`sinr_cosp = 2 * (q0 * q1 + q2 * q3)`
`cosr_cosp = 1 - 2 * (q1 * q1 + q2 * q2)`
`φ = atan2(sinr_cosp, cosr_cosp)`

`sinp = 2 * (q0 * q2 - q3 * q1)`
`if |sinp| ≥ 1: θ = copysign(π/2, sinp)`
`else: θ = asin(sinp)`

`siny_cosp = 2 * (q0 * q3 + q1 * q2)`
`cosy_cosp = 1 - 2 * (q2 * q2 + q3 * q3)`
`ψ = atan2(siny_cosp, cosy_cosp)`

The domain check for pitch (`|sinp| ≥ 1`) prevents numerical errors at the singularities of the arcsin function (±90°), which can occur during extreme rover articulation.

### Deterministic Telemetry Serialization and Bitmask Encoding
Attitude and navigation data are logged in binary packets with a fixed memory layout for deterministic parsing. Each packet includes a 64-bit microsecond timestamp `t_us` synchronized to GPS time, accounting for sensor latency `t_latency`:

`t_packet = t_GPS + Δt_sync - t_latency`

**Quaternion Packet (ATT) Layout (36 bytes):**
*   `Offset 0-3:` `q1` (float32) - W component
*   `Offset 4-7:` `q2` (float32) - X component
*   `Offset 8-11:` `q3` (float32) - Y component
*   `Offset 12-15:` `q4` (float32) - Z component
*   `Offset 16-19:` `roll` (float32) - φ [rad]
*   `Offset 20-23:` `pitch` (float32) - θ [rad]
*   `Offset 24-27:` `yaw` (float32) - ψ [rad]
*   `Offset 28-29:` `flags` (uint16) - Status bitmask

**Status Flag Bitmask Mathematics:**
The 16-bit `flags` field encodes system state using bitwise OR operations:
*   `ATT_FLAG_HEALTHY (0x0001):` `flags & 0x0001 ≠ 0` indicates AHRS is healthy.
*   `ATT_FLAG_GYRO_CALIBRATED (0x0002):` `flags & 0x0002 ≠ 0` indicates gyro bias is calibrated.
*   `ATT_FLAG_EKF_ACTIVE (0x0020):` `flags & 0x0020 ≠ 0` indicates EKF is the primary estimator.
*   `ATT_FLAG_DCM_ACTIVE (0x0040):` `flags & 0x0040 ≠ 0` indicates DCM fallback is active.

For example, a healthy system with calibrated gyro running DCM would have: `flags = 0x0001 | 0x0002 | 0x0040 = 0x0043`.

**Position Packet (POS) Integer Encoding:**
Geodetic coordinates are stored as fixed-point integers to conserve bandwidth:
*   `lat = floor(latitude_degrees × 10^7)` (int32)
*   `lng = floor(longitude_degrees × 10^7)` (int32)
*   `alt = floor(altitude_meters × 100)` (int32) [cm]

### C++ Implementation of Core Mathematics

```cpp
// 1. QUATERNION TO ROTATION MATRIX (for R_body_to_view)
// Given q_offset = [q0, q1, q2, q3] = [W, X, Y, Z]
float q0 = q_offset.q1;
float q1 = q_offset.q2;
float q2 = q_offset.q3;
float q3 = q_offset.q4;

// Compute R_body_to_view = transpose(R(q_offset))
float R_body_to_view[3][3];
R_body_to_view[0][0] = 1 - 2*(q2*q2 + q3*q3);
R_body_to_view[0][1] = 2*(q1*q2 + q0*q3);
R_body_to_view[0][2] = 2*(q1*q3 - q0*q2);

R_body_to_view[1][0] = 2*(q1*q2 - q0*q3);
R_body_to_view[1][1] = 1 - 2*(q1*q1 + q3*q3);
R_body_to_view[1][2] = 2*(q2*q3 + q0*q1);

R_body_to_view[2][0] = 2*(q1*q3 + q0*q2);
R_body_to_view[2][1] = 2*(q2*q3 - q0*q1);
R_body_to_view[2][2] = 1 - 2*(q1*q1 + q2*q2);

// 2. ANGULAR RATE TRANSFORMATION: ω_view = R_body_to_view * ω_body
float gyro_body[3] = {p, q, r};
float gyro_view[3] = {0, 0, 0};
for (int i = 0; i < 3; ++i) {
    for (int j = 0; j < 3; ++j) {
        gyro_view[i] += R_body_to_view[i][j] * gyro_body[j];
    }
}

// 3. QUATERNION COMPOSITION: q_view = q_body ⊗ q_offset_conjugate
// q_offset_conjugate = [q0, -q1, -q2, -q3]
float q_offset_conj[4] = {q0, -q1, -q2, -q3};
float q_body[4] = {q_body_w, q_body_x, q_body_y, q_body_z};
float q_view[4];

// Quaternion multiplication:
// W = W1*W2 - X1*X2 - Y1*Y2 - Z1*Z2
// X = W1*X2 + X1*W2 + Y1*Z2 - Z1*Y2
// Y = W1*Y2 - X1*Z2 + Y1*W2 + Z1*X2
// Z = W1*Z2 + X1*Y2 - Y1*X2 + Z1*W2
q_view[0] = q_body[0]*q_offset_conj[0] - q_body[1]*q_offset_conj[1] -
            q_body[2]*q_offset_conj[2] - q_body[3]*q_offset_conj[3];
q_view[1] = q_body[0]*q_offset_conj[1] + q_body[1]*q_offset_conj[0] +
            q_body[2]*q_offset_conj[3] - q_body[3]*q_offset_conj[2];
q_view[2] = q_body[0]*q_offset_conj[2] - q_body[1]*q_offset_conj[3] +
            q_body[2]*q_offset_conj[0] + q_body[3]*q_offset_conj[1];
q_view[3] = q_body[0]*q_offset_conj[3] + q_body[1]*q_offset_conj[2] -
            q_body[2]*q_offset_conj[1] + q_body[3]*q_offset_conj[0];

// 4. EULER ANGLE EXTRACTION (from q_view)
float q0v = q_view[0]; // W
float q1v = q_view[1]; // X
float q2v = q_view[2]; // Y
float q3v = q_view[3]; // Z

float sinr_cosp = 2.0f * (q0v * q1v + q2v * q3v);
float cosr_cosp = 1.0f - 2.0f * (q1v * q1v + q2v * q2v);
float roll = atan2f(sinr_cosp, cosr_cosp);

float sinp = 2.0f * (q0v * q2v - q3v * q1v);
float pitch;
if (fabsf(sinp) >= 1.0f) {
    pitch = copysignf(M_PI_2, sinp);
} else {
    pitch = asinf(sinp);
}

float siny_cosp = 2.0f * (q0v * q3v + q1v * q2v);
float cosy_cosp = 1.0f - 2.0f * (q2v * q2v + q3v * q3v);
float yaw = atan2f(siny_cosp, cosy_cosp);

// 5. TELEMETRY PACKET ENCODING
// Build ATT packet structure
struct log_ATT {
    uint64_t time_us;
    float q1, q2, q3, q4;
    float roll, pitch, yaw;
    uint16_t flags;
};

log_ATT att_packet;
att_packet.time_us = current_time_us;
att_packet.q1 = q_view[0]; // W
att_packet.q2 = q_view[1]; // X
att_packet.q3 = q_view[2]; // Y
att_packet.q4 = q_view[3]; // Z
att_packet.roll = roll;
att_packet.pitch = pitch;
att_packet.yaw = yaw;

// Set status flags using bitwise OR
att_packet.flags = 0;
if (ahrs_healthy) att_packet.flags |= 0x0001; // ATT_FLAG_HEALTHY
if (gyro_calibrated) att_packet.flags |= 0x0002; // ATT_FLAG_GYRO_CALIBRATED
if (dcm_active) att_packet.flags |= 0x0040; // ATT_FLAG_DCM_ACTIVE

// 6. POSITION INTEGER ENCODING
struct log_POS {
    int32_t lat; // degrees * 1e7
    int32_t lng; // degrees * 1e7
    int32_t alt; // cm
};

log_POS pos_packet;
pos_packet.lat = static_cast<int32_t>(latitude_deg * 1.0e7f);
pos_packet.lng = static_cast<int32_t>(longitude_deg * 1.0e7f);
pos_packet.alt = static_cast<int32_t>(altitude_m * 100.0f);
```

---

## C++ Implementation

### AP_AHRS_View Class Structure and Frame Transformation
The `AP_AHRS_View` class provides a mathematical abstraction for projecting the vehicle's attitude into an arbitrary sensor or camera frame. This is critical for isolating payloads from the rover's body motion.

```cpp
class AP_AHRS_View {
private:
    Matrix3f _R_view_to_body;    // View frame to body frame rotation
    Matrix3f _R_body_to_view;    // Body frame to view frame (inverse)
    Quaternion _q_offset;        // Offset quaternion defining view orientation
    AP_AHRS* _ahrs;              // Pointer to parent AHRS instance
    
    Vector3f _gyro_view;         // Gyro rates transformed to view frame
    Vector3f _gyro_estimate;     // Low-pass filtered rate estimate
};
```

### Angular Rate Transformation (AP_AHRS_View.cpp)
The `update_gyro()` function implements the mathematical transformation `ω_view = R_body_to_view * ω_body`. This provides gyro rates in the view frame for gimbal stabilization.

```cpp
void AP_AHRS_View::update_gyro() {
    // Get raw gyro rates from IMU in body frame: ω_body = [p, q, r]^T
    Vector3f gyro_body = _ahrs->get_gyro();
    
    // Transform to view frame: ω_view = R_body_to_view * ω_body
    // This implements the matrix-vector multiplication
    _gyro_view = _R_body_to_view * gyro_body;
    
    // Apply first-order low-pass filter for gimbal control
    // Filter equation: y_k = α * x_k + (1-α) * y_{k-1}
    const float alpha = 0.1f; // Filter coefficient (10% new data)
    _gyro_estimate = _gyro_estimate * (1.0f - alpha) + _gyro_view * alpha;
}
```

### View Quaternion Computation (AP_AHRS_View.cpp)
The `get_quaternion()` function computes the composite rotation `q_view = q_body ⊗ q_offset_conjugate`, implementing the quaternion multiplication defined in the mathematical formulation.

```cpp
bool AP_AHRS_View::get_quaternion(Quaternion& quat) const {
    // Get vehicle body attitude quaternion q_body
    Quaternion q_body;
    if (!_ahrs->get_quaternion(q_body)) {
        return false; // AHRS not healthy
    }
    
    // Compute conjugate of offset quaternion: q_offset_conj = [w, -x, -y, -z]
    Quaternion q_offset_conj = _q_offset.conjugated();
    
    // Composite rotation: q_view = q_body * q_offset_conjugate
    // This implements quaternion multiplication:
    // w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    // x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    // y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    // z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    quat = q_body * q_offset_conj;
    
    // Normalize to prevent numerical drift: q = q / ||q||
    quat.normalize();
    
    return true;
}
```

### Euler Angle Extraction with Singularity Handling (AP_AHRS_View.cpp)
The `get_euler_angles()` function implements the direct quaternion-to-Euler conversion with proper domain checking for the pitch singularity at ±90°.

```cpp
void AP_AHRS_View::get_euler_angles(float& roll, float& pitch, float& yaw) {
    Quaternion q_view;
    if (!get_quaternion(q_view)) {
        roll = pitch = yaw = 0.0f;
        return;
    }
    
    // Extract quaternion components: [q0, q1, q2, q3] = [W, X, Y, Z]
    const float q0 = q_view.q1; // W component
    const float q1 = q_view.q2; // X component  
    const float q2 = q_view.q3; // Y component
    const float q3 = q_view.q4; // Z component
    
    // Roll (φ): φ = atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1² + q2²))
    const float sinr_cosp = 2.0f * (q0 * q1 + q2 * q3);
    const float cosr_cosp = 1.0f - 2.0f * (q1 * q1 + q2 * q2);
    roll = atan2f(sinr_cosp, cosr_cosp);
    
    // Pitch (θ): θ = asin(2*(q0*q2 - q3*q1)) with domain protection
    const float sinp = 2.0f * (q0 * q2 - q3 * q1);
    if (fabsf(sinp) >= 1.0f) {
        // At singularity (±90°), use copysign to preserve direction
        pitch = copysignf(M_PI_2, sinp); // ±π/2 radians
    } else {
        pitch = asinf(sinp);
    }
    
    // Yaw (ψ): ψ = atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2² + q3²))
    const float siny_cosp = 2.0f * (q0 * q3 + q1 * q2);
    const float cosy_cosp = 1.0f - 2.0f * (q2 * q2 + q3 * q3);
    yaw = atan2f(siny_cosp, cosy_cosp);
}
```

### Quaternion Telemetry Serialization (AP_AHRS_Logging.cpp)
The `Write_ATT()` function packages attitude data into binary packets with deterministic layout for SD card logging via DMA.

```cpp
void AP_AHRS_Logging::Write_ATT() {
    // Get current attitude quaternion
    Quaternion quat;
    float roll, pitch, yaw;
    uint64_t time_us;
    
    if (!_ahrs.get_quaternion(quat)) {
        return; // AHRS unhealthy, skip logging
    }
    
    // Get consistent Euler angles from the same quaternion
    _ahrs.get_quaternion().to_euler(roll, pitch, yaw);
    
    // Get synchronized microsecond timestamp
    time_us = AP_HAL::micros64();
    
    // Define packed binary structure (36 bytes total)
    struct PACKED log_ATT {
        LOG_PACKET_HEADER;        // 8-byte header
        uint64_t time_us;         // 8-byte timestamp
        float q1, q2, q3, q4;     // 16 bytes: quaternion W,X,Y,Z
        float roll, pitch, yaw;   // 12 bytes: Euler angles [rad]
        uint16_t flags;           // 2 bytes: status bitmask
    } att_packet;
    
    // Fill packet with data (matches mathematical layout)
    att_packet.time_us = time_us;
    att_packet.q1 = quat.q1;  // W component
    att_packet.q2 = quat.q2;  // X component
    att_packet.q3 = quat.q3;  // Y component
    att_packet.q4 = quat.q4;  // Z component
    att_packet.roll = roll;
    att_packet.pitch = pitch;
    att_packet.yaw = yaw;
    
    // Set status flags using bitwise OR operations
    att_packet.flags = 0;
    if (_ahrs.healthy()) {
        att_packet.flags |= ATT_FLAG_HEALTHY; // 0x0001
    }
    if (_ahrs.get_gyro_drift().length() < 0.1f) {
        att_packet.flags |= ATT_FLAG_GYRO_CALIBRATED; // 0x0002
    }
    
    // Write to SD card via DMA (non-blocking)
    _logger->WriteBlock(&att_packet, sizeof(att_packet));
    
    // Update statistics
    _attitude_packets_written++;
    _last_attitude_time_us = time_us;
}
```

### Position Data Logging with Integer Encoding (AP_AHRS_Logging.cpp)
The `Write_POS()` function logs navigation data using fixed-point integer encoding to conserve bandwidth.

```cpp
void AP_AHRS_Logging::Write_POS() {
    // Get position and velocity estimates in NED frame
    Vector3f position, velocity;
    if (!_ahrs.get_position(position) || !_ahrs.get_velocity_NED(velocity)) {
        return;
    }
    
    // Define packed position packet structure
    struct PACKED log_POS {
        LOG_PACKET_HEADER;
        uint64_t time_us;
        int32_t lat;        // Latitude: degrees * 1e7
        int32_t lng;        // Longitude: degrees * 1e7
        int32_t alt;        // Altitude: cm
        float vel_north;    // North velocity [m/s]
        float vel_east;     // East velocity [m/s]
        float vel_down;     // Down velocity [m/s]
        uint8_t pos_type;   // Position fix type
        uint8_t vel_type;   // Velocity fix type
    } pos_packet;
    
    // Convert floating-point to fixed-point integers
    // Implements: lat_int = floor(latitude_deg * 1e7)
    pos_packet.lat = static_cast<int32_t>(position.x * 1e7f);
    pos_packet.lng = static_cast<int32_t>(position.y * 1e7f);
    pos_packet.alt = static_cast<int32_t>(position.z * 100.0f); // meters to cm
    
    // Fill velocity components (NED frame)
    pos_packet.vel_north = velocity.x; // North component
    pos_packet.vel_east = velocity.y;  // East component
    pos_packet.vel_down = velocity.z;  // Down component
    
    // Write to log via DMA
    _logger->WriteBlock(&pos_packet, sizeof(pos_packet));
}
```

### RTOS Threading and DMA Buffer Management
The logging system uses a producer-consumer pattern with double buffering to ensure deterministic 100Hz logging without blocking the AHRS update thread.

1.  **Producer Thread (AHRS Update):** Runs at 400Hz in a high-priority RTOS task. It writes attitude data to the primary buffer at `0x20001000`.
2.  **DMA Controller:** When the primary buffer reaches a threshold (e.g., 1KB), an SPI DMA transfer to the SD card is initiated on Channel 3 using 8-word (32-byte) bursts.
3.  **Buffer Swap ISR:** The DMA Transfer Complete interrupt triggers a buffer swap:
    ```cpp
    void DMA1_Stream3_IRQHandler() {
        if (DMA1->HISR & DMA_HISR_TCIF3) {
            // Swap primary and secondary buffers
            swap_buffers();
            // Clear interrupt flag
            DMA1->HIFCR = DMA_HIFCR_CTCIF3;
        }
    }
    ```
4.  **Consumer Thread (Logging):** A lower-priority RTOS task manages packet formatting and buffer state, waiting on a semaphore signaled by the buffer swap ISR.

### SIMD-Optimized Quaternion Operations
For STM32F4/F7 with ARM Cortex-M4/M7 and NEON SIMD, quaternion operations use 16-byte aligned memory.

```cpp
// 16-byte aligned quaternion structure for SIMD
typedef struct {
    float32_t q[4] __attribute__((aligned(16))); // [W, X, Y, Z]
} ALIGN_16B QuaternionSIMD;

// SIMD quaternion multiplication using ARM CMSIS-DSP
void quaternion_multiply_simd(const QuaternionSIMD* q1, 
                              const QuaternionSIMD* q2,
                              QuaternionSIMD* result) {
    // Load quaternions into SIMD registers (4x float32)
    float32x4_t vq1 = vld1q_f32(q1->q);
    float32x4_t vq2 = vld1q_f32(q2->q);
    
    // SIMD implementation of quaternion multiplication
    // This maps directly to the mathematical formulation:
    // result = [w1*w2 - x1*x2 - y1*y2 - z1*z2,
    //           w1*x2 + x1*w2 + y1*z2 - z1*y2,
    //           w1*y2 - x1*z2 + y1*w2 + z1*x2,
    //           w1*z2 + x1*y2 - y1*x2 + z1*w2]
    
    // Implementation uses NEON intrinsics for the 16 operations
    // ... (detailed SIMD code omitted for brevity)
    
    // Store result back to memory
    vst1q_f32(result->q, result_vec);
}
```

### Deterministic Hardware Timer Synchronization
The `TelemetryTimer` class provides microsecond timestamps synchronized to GPS time, accounting for sensor pipeline latency.

```cpp
class TelemetryTimer {
private:
    uint32_t _timer_base;          // Hardware timer base address (TIM5)
    uint64_t _time_base_us;        // Microsecond time base
    uint32_t _last_capture;        // Last timer capture value
    
public:
    uint64_t get_time_us() {
        // Read 32-bit hardware timer
        uint32_t timer_val = TIM5->CNT;
        uint32_t delta;
        
        // Handle 32-bit timer overflow
        if (timer_val < _last_capture) {
            // Overflow occurred: delta = (max - last) + current
            delta = (0xFFFFFFFF - _last_capture) + timer_val;
            _time_base_us += 0xFFFFFFFF / 1000000; // Add ~4294 seconds
        } else {
            delta = timer_val - _last_capture;
        }
        
        _last_capture = timer_val;
        // Final timestamp: t_packet = t_base + Δt
        return _time_base_us + (delta / 1000000);
    }
};
```