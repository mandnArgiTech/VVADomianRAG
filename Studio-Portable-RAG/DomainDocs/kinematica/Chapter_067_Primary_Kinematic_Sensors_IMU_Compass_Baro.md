# Primary Kinematic Sensor DAL: IMU, Compass, and Barometer Data Buffering

_Generated 2026-04-15 08:38 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_InertialSensor.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_InertialSensor.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Compass.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Compass.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Baro.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Baro.h`

# Chapter: Primary Kinematic Sensor DAL: IMU, Compass, and Barometer Data Buffering

## Technical Introduction
The files `AP_DAL_InertialSensor.cpp`, `AP_DAL_Compass.cpp`, and `AP_DAL_Baro.cpp` implement the Data Access Layer (DAL) for primary kinematic sensors in ArduPilot. This system provides deterministic buffering of IMU delta-velocity/delta-angle data with temporal consistency guarantees, atomic snapshotting of magnetic field vectors with temperature compensation, and barometric pressure filtering with health monitoring. For a 400Hz autonomous agricultural rover, this ensures the Extended Kalman Filter (EKF) receives synchronized sensor data despite the vehicle's 1200 kg mass, high rotational inertia, and skid-steering dynamics that cause significant vibration and EMI from 400A motor currents. The implementation uses lock-free ring buffers, hardware CRC validation, and cache-aligned memory structures on STM32 Cortex-M7 to maintain real-time performance.

## Mathematical Formulation

### Delta-Velocity/Delta-Angle Temporal Consistency Mathematics
The DAL implements deterministic buffering for IMU data with EKF-aligned temporal windows. For each IMU sample interval Δtᵢ at 800Hz (Δtᵢ = 1.25ms), the delta-velocity and delta-angle are computed:

\[
\Delta\mathbf{v}_i = \int_{t_i}^{t_i+\Delta t_i} \mathbf{a}(t) \, dt \approx \mathbf{a}_i \cdot \Delta t_i + \frac{1}{2} \mathbf{j}_i \cdot \Delta t_i^2
\]

\[
\Delta\boldsymbol{\theta}_i = \int_{t_i}^{t_i+\Delta t_i} \boldsymbol{\omega}(t) \, dt \approx \boldsymbol{\omega}_i \cdot \Delta t_i + \frac{1}{2} \boldsymbol{\alpha}_i \cdot \Delta t_i^2
\]

For the EKF running at 200Hz (ΔT = 5ms), the DAL integrates all IMU samples within each window Wₖ:

\[
\Delta\mathbf{V}_k = \sum_{i \in W_k} \Delta\mathbf{v}_i \quad \text{where } W_k = \{i : t_i \in [t_k, t_k + \Delta T]\}
\]

\[
\Delta\boldsymbol{\Theta}_k = \sum_{i \in W_k} \Delta\boldsymbol{\theta}_i
\]

Coning and sculling compensation for the rover's high-rate IMUs (800Hz) during skid-steering maneuvers:

\[
\Delta\boldsymbol{\Theta}_k^{\text{corrected}} = \Delta\boldsymbol{\Theta}_k + \frac{1}{12} \sum_{i \in W_k} (\Delta\boldsymbol{\theta}_{i-1} \times \Delta\boldsymbol{\theta}_i)
\]

\[
\Delta\mathbf{V}_k^{\text{corrected}} = \Delta\mathbf{V}_k + \frac{1}{2} \sum_{i \in W_k} (\Delta\boldsymbol{\theta}_i \times \Delta\mathbf{v}_i)
\]

### Buffer Synchronization Protocol
The ring buffer index calculation for microsecond timestamp alignment:

\[
\text{idx}(t) = \left\lfloor \frac{t - t_{\text{base}}}{1\mu s} \right\rfloor \mod B
\]

Overlap prevention condition with ε = 10μs tolerance for timestamp jitter:

\[
\forall k, \max(t_i \in W_k) - \min(t_i \in W_k) \leq \Delta T + \epsilon
\]

### Sensor Health Bitmask Algebra
Compass health bitmask with weighted failure modes:

\[
H_m = \sum_{b=0}^{31} w_b \cdot 2^b
\]

where w₀ = 1.0 (I2C/SPI error), w₁ = 0.8 (self-test failure), w₂ = 0.6 (magnetic saturation), w₃ = 0.4 (temperature out of range).

Barometer health metric based on pressure variance:

\[
H_b = 1 - \frac{\sigma_p}{\sigma_{p,\text{max}}} - \frac{|T - T_{\text{nom}}|}{T_{\text{range}}}
\]

EKF measurement covariance scaling for unhealthy sensors:

\[
\mathbf{R}_k = \mathbf{R}_{\text{nom}} \cdot \left(1 + 10.0 \cdot (1 - H_k)\right)
\]

### Temperature-Compensated Magnetic Field
Temperature compensation for compass readings:

\[
\mathbf{B}_{\text{comp}}(T) = \mathbf{B}_{\text{raw}} \cdot (1 + \beta(T - T_{\text{ref}})) + \mathbf{O}(T)
\]

where β = [0.001, 0.001, 0.001] °C⁻¹ is the temperature coefficient vector and O(T) is temperature-dependent offset.

### Barometric Altitude Calculation
Barometric formula for altitude calculation:

\[
h = \frac{T_0}{L} \cdot \left(1 - \left(\frac{P}{P_0}\right)^{\frac{R \cdot L}{g \cdot M}}\right)
\]

where T₀ = 288.15K, L = 0.0065 K/m, g = 9.80665 m/s², M = 0.0289644 kg/mol, R = 8.31447 J/(mol·K).

### Kalman Filter for Barometric Altitude
State transition matrix for altitude/velocity:

\[
\mathbf{F} = \begin{bmatrix} 1 & \Delta t \\ 0 & 1 \end{bmatrix}
\]

Process noise covariance with acceleration noise σₐ = 0.1 m/s²:

\[
\mathbf{Q} = \begin{bmatrix} \frac{1}{4}\Delta t^4 \sigma_a^2 & \frac{1}{2}\Delta t^3 \sigma_a^2 \\ \frac{1}{2}\Delta t^3 \sigma_a^2 & \Delta t^2 \sigma_a^2 \end{bmatrix}
\]

Kalman gain calculation:

\[
\mathbf{K} = \mathbf{P} \mathbf{H}^T (\mathbf{H} \mathbf{P} \mathbf{H}^T + R)^{-1}
\]

where H = [1 0] and R is measurement noise from pressure variance.

### IMU Sample Structure Geometry
64-byte cache-aligned IMU sample structure:

\[
S_{\text{IMU}} = \langle t_{\text{ns}}, \Delta\mathbf{v}, \Delta\boldsymbol{\theta}, n, T_{\text{ADC}}, i, q, \Delta t, C_{\text{CRC32}} \rangle
\]

Total size: 8 + 12 + 12 + 4 + 2 + 1 + 1 + 4 + 4 = 48 bytes + 16 padding = 64 bytes.

### Pressure Variance Calculation
Running variance over 100-sample history:

\[
\sigma_p^2 = \frac{1}{n} \sum_{i=1}^n p_i^2 - \left(\frac{1}{n} \sum_{i=1}^n p_i\right)^2
\]

Threshold: σₚ² > 100 Pa² triggers high noise health flag.

### Temperature Conversion Formulas
Sensor-specific temperature conversions:
- MPU6000: \( T = 25 + \frac{T_{\text{ADC}} - 521}{340} \) °C
- ICM20689: \( T = 25 + \frac{T_{\text{ADC}} - 25}{326.8} \) °C
- HMC5883L: \( T = 25 + \frac{T_{\text{ADC}} - 32768}{2048} \) °C

### CRC-16/CRC-32 Integrity Checks
CRC-16-CCITT polynomial: \( G(x) = x^{16} + x^{12} + x^5 + 1 \) (0x1021)
CRC-32 polynomial: \( G(x) = x^{32} + x^{26} + x^{23} + x^{22} + x^{16} + x^{12} + x^{11} + x^{10} + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1 \) (0x04C11DB7)

### Memory Map Geometry
STM32 SRAM layout for DAL structures:
- IMU ring buffer control: 64 bytes per instance at 0x20000100
- IMU sample buffers: 2KB per instance (32 samples × 64 bytes)
- Compass atomic variables: 32 bytes per instance at 0x20001A00
- Barometer atomic variables: 32 bytes per instance at 0x20001A40

### Hardware Synchronization Primitives
ARM Cortex-M atomic compare-and-swap:

\[
\text{CAS}(p, e, d) = \begin{cases}
\text{true} & \text{if } \text{LDREX}(p) = e \land \text{STREX}(p, d) = 0 \\
\text{false} & \text{otherwise}
\end{cases}
\]

Data Memory Barrier: `DMB` instruction ensures memory ordering.

## C++ Implementation

### Delta-Velocity Temporal Caching with Coning Compensation (AP_DAL_InertialSensor.cpp)

The `IMURingBuffer` class implements the mathematical temporal windowing:

```cpp
bool get_integrated_window(uint64_t window_start_ns, 
                           uint64_t window_end_ns,
                           Vector3f& integrated_delta_vel,
                           Vector3f& integrated_delta_ang,
                           uint32_t& total_samples) {
    // Integrate all samples within time window
    while (idx != current_head) {
        const IMUSample& sample = buffer[idx];
        
        // Check if sample falls within EKF window
        if (sample.timestamp_ns >= window_start_ns && 
            sample.timestamp_ns < window_end_ns) {
            
            // Apply coning/sculling compensation if multiple sub-samples
            if (sample.sample_count > 1) {
                Vector3f corrected_dv = sample.delta_velocity;
                Vector3f corrected_da = sample.delta_angle;
                
                // Simplified coning compensation (Bortz equation)
                if (total_samples > 0) {
                    Vector3f prev_da = buffer[(idx-1)%BUFFER_SIZE].delta_angle;
                    corrected_da += (prev_da.cross(sample.delta_angle)) / 12.0f;
                }
                
                integrated_delta_vel += corrected_dv;
                integrated_delta_ang += corrected_da;
            } else {
                integrated_delta_vel += sample.delta_velocity;
                integrated_delta_ang += sample.delta_angle;
            }
            
            total_samples += sample.sample_count;
            found_samples = true;
        }
        
        // Stop if we've passed the window
        if (sample.timestamp_ns >= window_end_ns) {
            break;
        }
        
        idx = (idx + 1) % BUFFER_SIZE;
    }
}
```

This implements the coning compensation equation:

\[
\Delta\boldsymbol{\Theta}_k^{\text{corrected}} = \Delta\boldsymbol{\Theta}_k + \frac{1}{12} \sum_{i \in W_k} (\Delta\boldsymbol{\theta}_{i-1} \times \Delta\boldsymbol{\theta}_i)
\]

The `push_sample()` method uses ARM memory barriers (`dmb sy`) to implement the atomic buffer swap:

```cpp
// Copy sample with compiler barrier
buffer[current_head] = sample;
memory_barrier();

// Update head pointer
head.store(next_head, std::memory_order_release);
```

### Magnetic Vector Snapshotting with Temperature Compensation (AP_DAL_Compass.cpp)

The `CompassDataManager` implements temperature-compensated magnetic field calculation:

```cpp
// Apply calibration if available
if (compasses[instance].calibrated) {
    Vector3f calibrated = compasses[instance].scale * 
                         (new_sample.field_ut - compasses[instance].bias);
    
    // Apply temperature compensation
    float temp_c = convert_temperature(temperature_raw, sensor_type);
    if (temp_c != 25.0f) {
        Vector3f temp_adjust = temp_coeffs[instance].offset_slope * 
                              (temp_c - temp_coeffs[instance].ref_temp_c);
        calibrated -= temp_adjust;
        
        Matrix3f temp_scale;
        temp_scale.identity();
        temp_scale.a.x += temp_coeffs[instance].scale_slope.x * 
                         (temp_c - temp_coeffs[instance].ref_temp_c);
        temp_scale.b.y += temp_coeffs[instance].scale_slope.y * 
                         (temp_c - temp_coeffs[instance].ref_temp_c);
        temp_scale.c.z += temp_coeffs[instance].scale_slope.z * 
                         (temp_c - temp_coeffs[instance].ref_temp_c);
        
        calibrated = temp_scale * calibrated;
    }
    
    new_sample.field_ut = calibrated;
}
```

This implements the temperature compensation equation:

\[
\mathbf{B}_{\text{comp}}(T) = \mathbf{B}_{\text{raw}} \cdot (1 + \beta(T - T_{\text{ref}})) + \mathbf{O}(T)
\]

The atomic store uses `memory_order_seq_cst` for strict ordering:

```cpp
compasses[instance].current_sample.store(new_sample, std::memory_order_seq_cst);
```

### Barometric Pressure Filtering with Kalman Estimation (AP_DAL_Baro.cpp)

The `BaroDataManager` implements the barometric altitude calculation:

```cpp
float calculate_altitude(float pressure_pa, float temperature_c) {
    float sea_level = sea_level_pressure_pa.load(std::memory_order_relaxed);
    
    const float T0 = 288.15f;
    const float L = 0.0065f;
    const float g = 9.80665f;
    const float M = 0.0289644f;
    const float R = 8.31447f;
    
    float temperature_k = temperature_c + 273.15f;
    float exponent = (R * L) / (g * M);
    
    float altitude = (T0 / L) * 
                    (1.0f - powf(pressure_pa / sea_level, exponent));
    
    return altitude;
}
```

This implements the barometric formula:

\[
h = \frac{T_0}{L} \cdot \left(1 - \left(\frac{P}{P_0}\right)^{\frac{R \cdot L}{g \cdot M}}\right)
\]

The Kalman filter implementation:

```cpp
void update_kalman_filter(uint8_t instance, float altitude_measurement, float dt) {
    // State transition matrix F
    float F[2][2] = {{1.0f, dt}, {0.0f, 1.0f}};
    
    // Process noise covariance Q
    float Q[2][2] = {
        {0.25f * dt * dt * dt * dt, 0.5f * dt * dt * dt},
        {0.5f * dt * dt * dt, dt * dt}
    };
    
    // Measurement noise R (from pressure variance)
    float R = baro.pressure_variance * 0.01f;
    
    // Predict step
    float alt_pred = baro.kf_state.altitude + baro.kf_state.velocity * dt;
    float vel_pred = baro.kf_state.velocity;
    
    // ... Kalman gain calculation and update
}
```

This implements the process noise covariance:

\[
\mathbf{Q} = \begin{bmatrix} \frac{1}{4}\Delta t^4 \sigma_a^2 & \frac{1}{2}\Delta t^3 \sigma_a^2 \\ \frac{1}{2}\Delta t^3 \sigma_a^2 & \Delta t^2 \sigma_a^2 \end{bmatrix}
\]

### Hardware Health Bitmask Implementation

The health flag system implements the weighted bitmask algebra:

```cpp
// Set quality flags based on physical thresholds
sample.quality_flags = 0;
float dv_mag = delta_velocity.length();
float da_mag = delta_angle.length();

if (dv_mag > 50.0f || da_mag > 1.0f) {
    sample.quality_flags |= 0x01; // Overrange flag
}
```

For barometer health calculation:

```cpp
// Calculate pressure variance
float sum = 0.0f, sum_sq = 0.0f;
size_t count = 0;
for (size_t i = 0; i < BaroInstance::PRESSURE_HISTORY; i++) {
    if (baros[instance].pressure_history[i] != 0.0f) {
        sum += baros[instance].pressure_history[i];
        sum_sq += baros[instance].pressure_history[i] * 
                 baros[instance].pressure_history[i];
        count++;
    }
}

if (count > 10) {
    float mean = sum / count;
    float variance = (sum_sq / count) - (mean * mean);
    baros[instance].pressure_variance = variance;
    
    // If variance is too high, set health flag
    if (variance > 100.0f) {
        health_flags |= 0x08; // High noise flag
    }
}
```

This implements the pressure variance calculation:

\[
\sigma_p^2 = \frac{1}{n} \sum_{i=1}^n p_i^2 - \left(\frac{1}{n} \sum_{i=1}^n p_i\right)^2
\]

### Hardware Synchronization Primitives

The `HardwareSync` class implements ARM Cortex-M atomic operations:

```cpp
static bool atomic_cas_32(volatile uint32_t* ptr, 
                         uint32_t expected, 
                         uint32_t desired) {
    uint32_t result;
    
    asm volatile (
        "ldrex %0, [%1]\n"      // Load with exclusive monitor
        "cmp   %0, %2\n"        // Compare with expected
        "bne   1f\n"            // Branch if not equal
        "strex %0, %3, [%1]\n"  // Store with exclusive monitor
        "1:\n"
        : "=&r" (result)
        : "r" (ptr), "r" (expected), "r" (desired)
        : "memory", "cc"
    );
    
    return (result == 0); // STREX returns 0 on success
}
```

This implements the atomic compare-and-swap:

\[
\text{CAS}(p, e, d) = \begin{cases}
\text{true} & \text{if } \text{LDREX}(p) = e \land \text{STREX}(p, d) = 0 \\
\text{false} & \text{otherwise}
\end{cases}
\]

### RTOS Threading Model and Real-Time Constraints

The DAL operates within ArduPilot's RTOS with strict priority ordering:

1. **IMU ISRs** (800Hz, highest priority): Call `AP_DAL_InertialSensor::push_imu_data()` with `memory_barrier()`.
2. **Compass Thread** (100Hz): Calls `CompassDataManager::update_compass()` with atomic stores.
3. **Barometer Thread** (50Hz): Calls `BaroDataManager::update_baro()` with Kalman filtering.
4. **EKF Thread** (200Hz): Calls `get_integrated_window()`, `get_compass_data()`, `get_baro_data()`.
5. **Diagnostic Thread** (10Hz): Calls `get_stats()` methods for health monitoring.

The lock-free ring buffers prevent priority inversion during the rover's 400Hz control loop. The 64-byte cache alignment (`ALIGN_64B`, `ALIGN_32B`) ensures optimal DMA transfers and prevents cache thrashing on Cortex-M7.

### CRC Integrity Validation

Hardware CRC-32 for IMU samples:

```cpp
uint32_t calculate_crc32(const void* data, size_t length) {
    CRC->CR = CRC_CR_RESET;
    
    const uint32_t* words = static_cast<const uint32_t*>(data);
    size_t word_count = length / 4;
    
    for (size_t i = 0; i < word_count; i++) {
        CRC->DR = words[i];
    }
    
    // Handle remaining bytes
    if (length % 4 != 0) {
        const uint8_t* bytes = static_cast<const uint8_t*>(data);
        uint32_t last_word = 0;
        for (size_t i = word_count * 4; i < length; i++) {
            last_word |= static_cast<uint32_t>(bytes[i]) << ((i % 4) * 8);
        }
        CRC->DR = last_word;
    }
    
    return CRC->DR;
}
```

CRC-16-CCITT for compass and barometer:

```cpp
uint16_t calculate_crc16(const void* data, size_t length) {
    uint16_t crc = 0xFFFF;
    const uint8_t* bytes = static_cast<const uint8_t*>(data);
    
    for (size_t i = 0; i < length; i++) {
        crc ^= static_cast<uint16_t>(bytes[i]) << 8;
        
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    
    return crc;
}
```

These implement the CRC polynomials: CRC-32 with 0x04C11DB7 and CRC-16-CCITT with 0x1021.

### Memory Map Implementation

The STM32 SRAM layout is statically allocated:

```cpp
// IMU Ring Buffer Control Blocks (64 bytes each)
// Instance 0: 0x20000100
// Instance 1: 0x20000110  
// Instance 2: 0x20000120

// IMU Sample Buffers (6KB total, 2KB per instance)
// Instance 0: 0x20000200 - 0x200009FF (2048 bytes, 32 samples × 64 bytes)
// Instance 1: 0x20000A00 - 0x200011FF
// Instance 2: 0x20001200 - 0x200019FF

// Compass Atomic Variables (64 bytes)
// Instance 0 sample: 0x20001A00 - 0x20001A1F (32 bytes)
// Instance 1 sample: 0x20001A20 - 0x20001A3F (32 bytes)

// Barometer Atomic Variables (64 bytes)
// Instance 0 sample: 0x20001A40 - 0x20001A5F (32 bytes)
// Instance 1 sample: 0x20001A60 - 0x20001A7F (32 bytes)
```

This fixed memory map ensures deterministic access patterns and prevents heap fragmentation during long-duration rover operations.

### Temperature Conversion Implementations

Sensor-specific temperature conversions:

```cpp
float convert_temperature(uint16_t raw, uint8_t sensor_type) {
    switch (sensor_type) {
        case COMPASS_TYPE_HMC5883L:
            return 25.0f + (raw - 0x8000) * 0.125f / 256.0f;
        case COMPASS_TYPE_QMC5883L:
            return raw * 0.01f;
        case COMPASS_TYPE_IST8310:
            return raw * 0.1f;
        default:
            return 25.0f;
    }
}
```

For IMU temperature conversion in `AP_DAL_InertialSensor::push_imu_data()`:

```cpp
switch (imu_types[instance]) {
    case IMU_TYPE_MPU6000:
        sample.temperature_adc = temperature_raw;
        imus[instance].temperature_c = 25.0f + (temperature_raw - 521.0f) / 340.0f;
        break;
    case IMU_TYPE_ICM20689:
        sample.temperature_adc = temperature_raw;
        imus[instance].temperature_c = 25.0f + (temperature_raw - 25.0f) / 326.8f;
        break;
    default:
        imus[instance].temperature_c = 25.0f;
}
```

These implement the temperature conversion formulas for each sensor type.

### Diagnostic Interface and Statistics

The `get_stats()` methods provide runtime diagnostics:

```cpp
struct IMUStats {
    uint32_t drop_count;
    uint32_t error_count;
    float temperature_c;
    uint64_t last_sample_ns;
    bool initialized;
    float buffer_utilization;
};

struct CompassStats {
    uint32_t update_count;
    uint32_t error_count;
    float temperature_c;
    Vector3f current_field;
    uint8_t health_flags;
    bool calibrated;
};

struct BaroStats {
    uint32_t update_count;
    uint32_t error_count;
    float current_altitude;
    float current_temperature;
    float pressure_variance;
    uint8_t health_flags;
};
```

These statistics enable health monitoring of the rover's sensor suite, critical for detecting failures during agricultural operations where the 1200 kg vehicle's high inertia requires reliable state estimation.

### Timing Statistics for EKF Covariance Adjustment

The `get_timing_stats()` method calculates sample intervals:

```cpp
void get_timing_stats(uint64_t& min_interval_ns, 
                     uint64_t& max_interval_ns,
                     float& avg_rate_hz) {
    // ... calculate intervals between samples
    
    avg_rate_hz = (count > 0) ? (1e9f / (total_interval / (float)count)) : 0.0f;
}
```

This provides the EKF with timing statistics to adjust measurement covariance R according to:

\[
\mathbf{R}_k = \mathbf{R}_{\text{nom}} \cdot \left(1 + \alpha \cdot (1 - H_k)\right)
\]

where Hₖ is the health score derived from timing statistics and quality flags.

The DAL architecture ensures deterministic sensor data delivery to the EKF, enabling reliable state estimation for the agricultural rover's skid-steering control despite challenging operating conditions with high vibration, EMI, and thermal variations.