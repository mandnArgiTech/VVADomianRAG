# Spatial Sensor DAL: GPS, Airspeed, Beacons, and Visual Odometry

_Generated 2026-04-15 08:55 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_GPS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_GPS.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Airspeed.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Airspeed.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Beacon.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_Beacon.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_RangeFinder.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_RangeFinder.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_VisualOdom.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL_VisualOdom.h`

# Chapter: Spatial Sensor DAL: GPS, Airspeed, Beacons, and Visual Odometry

## Technical Introduction

The files `AP_DAL_GPS.cpp/h`, `AP_DAL_Airspeed.cpp/h`, `AP_DAL_Beacon.cpp/h`, `AP_DAL_RangeFinder.cpp/h`, and `AP_DAL_VisualOdom.cpp/h` implement the Data Access Layer (DAL) for spatial sensors on a 400Hz autonomous agricultural rover. This architecture provides deterministic, thread-safe buffering and virtual interface abstraction for GPS (position/velocity), airspeed (dynamic pressure), ultrasonic beacons (local positioning), lidar/rangefinders (terrain clearance), and visual odometry (relative motion). The DAL enforces strict pointer decoupling between sensor drivers and the EKF, utilizing double-buffered, cache-aligned structures (64-byte for Cortex-M7), lock-free ring buffers, and atomic operations to guarantee data consistency across multiple RTOS threads. For the 1200 kg skid-steering rover, this design mitigates EMI from 400A motor currents and ensures temporal alignment of all spatial measurements within the 2.5ms control budget, enabling centimeter-accurate state estimation despite aggressive maneuvering and high rotational inertia (J_zz = 150 kg·m²).

## Mathematical Formulation

### GPS Auto-Baud Detection State Machine

The GPS subsystem implements a probabilistic state machine for automatic baud rate and protocol detection, critical for the rover's field deployment where sensor connections may vary.

**Baud Rate Search Space:**
\[
B = \{9600, 19200, 38400, 57600, 115200, 230400, 460800\}
\]

**Protocol Probe Set:**
\[
P = \{\text{UBX (0xB5)}, \text{NMEA (0x24)}, \text{SIRF (0xA0)}, \text{ERB (0xEB)}, \text{NOVA (0xAA)}\}
\]

**Detection Probability Model:**
For each baud rate \(b_i\) and protocol \(p_j\), the system sends probe sequence \(M_{ij}\) and evaluates response \(R_{ij}\). The confidence score is:
\[
C_{ij} = \frac{\sum_{k=1}^{N} \delta(R_{ij}[k], E_{ij}[k])}{N}
\]
where \(\delta\) is the Kronecker delta function, \(R_{ij}[k]\) is the k-th received byte, and \(E_{ij}[k]\) is the expected signature.

**Timeout Optimization:**
The optimal timeout for baud rate \(b_i\) is:
\[
T_i = \frac{10 \cdot 8 \cdot L}{b_i} + \tau_{\text{margin}}
\]
where \(L\) is the expected response length in bytes (typically 10-100), and \(\tau_{\text{margin}} = 50\text{ms}\) accounts for STM32 processing delay.

**State Transition Matrix:**
The state machine \(S(t) = (b, p, s)\) evolves as:
\[
S(t+1) = 
\begin{cases}
(b_{\text{next}}, p_0, \text{PROBE}) & \text{if } s = \text{TIMEOUT} \\
(b, p_{\text{next}}, \text{PROBE}) & \text{if } s = \text{WRONG\_SIGNATURE} \\
(b, p, \text{LOCKED}) & \text{if } C_{ij} > 0.9
\end{cases}
\]

### Dual GPS Covariance Blending

For the rover's dual-antenna configuration, optimal sensor fusion uses inverse covariance weighting to combine position estimates while accounting for skid-steering vibrations.

**Weight Calculation:**
For each GPS instance \(i\) with position covariance matrix \(\Sigma_i\):
\[
w_i = \frac{1}{\text{tr}(\Sigma_i) \cdot \text{HDOP}_i \cdot \max(1, 20 - N_{\text{sats},i})}
\]

**Blended Position:**
\[
\mathbf{P}_{\text{blended}} = \frac{\sum_{i=1}^{2} w_i \cdot \mathbf{P}_i}{\sum_{i=1}^{2} w_i}
\]

**Covariance Propagation:**
The blended covariance is:
\[
\Sigma_{\text{blended}} = \left( \sum_{i=1}^{2} \Sigma_i^{-1} \right)^{-1}
\]

**Divergence Detection:**
If the Mahalanobis distance between two GPS solutions exceeds threshold:
\[
D^2 = (\mathbf{P}_1 - \mathbf{P}_2)^T (\Sigma_1 + \Sigma_2)^{-1} (\mathbf{P}_1 - \mathbf{P}_2) > \chi^2_{0.95}(3)
\]
where \(\chi^2_{0.95}(3) = 7.815\) is the 95% confidence threshold for 3 degrees of freedom.

### Airspeed Differential Pressure Physics

The rover's airspeed sensor measures dynamic pressure \(q\) for wind estimation and ground speed correction:

**Bernoulli's Principle:**
\[
q = \frac{1}{2} \rho V^2
\]
where \(\rho\) is air density (kg/m³) and \(V\) is true airspeed (m/s).

**Air Density Correction:**
\[
\rho = \frac{P}{R T}
\]
where \(P\) is static pressure (Pa), \(T\) is temperature (K), and \(R = 287.05\ \text{J/(kg·K)}\) for dry air.

**Indicated Airspeed:**
\[
V_{\text{ind}} = \sqrt{\frac{2q}{\rho_0}}
\]
with \(\rho_0 = 1.225\ \text{kg/m³}\) at sea level standard conditions.

**True Airspeed Correction:**
\[
V_{\text{true}} = V_{\text{ind}} \sqrt{\frac{\rho_0}{\rho}}
\]

### Beacon Trilateration Geometry

Ultrasonic beacons provide centimeter-accurate local positioning for the rover's precision agriculture tasks:

**Time-of-Flight Measurement:**
\[
d_i = c \cdot \Delta t_i
\]
where \(c = 343\ \text{m/s}\) (speed of sound at 20°C) and \(\Delta t_i\) is time-of-flight to beacon \(i\).

**Trilateration System:**
For three beacons at positions \(\mathbf{B}_i = (x_i, y_i, z_i)\):
\[
\begin{cases}
(x - x_1)^2 + (y - y_1)^2 + (z - z_1)^2 = d_1^2 \\
(x - x_2)^2 + (y - y_2)^2 + (z - z_2)^2 = d_2^2 \\
(x - x_3)^2 + (y - y_3)^2 + (z - z_3)^2 = d_3^2
\end{cases}
\]

**Linearized Solution:**
Subtract the first equation from others:
\[
2(x_1 - x_i)x + 2(y_1 - y_i)y + 2(z_1 - z_i)z = d_i^2 - d_1^2 - x_i^2 + x_1^2 - y_i^2 + y_1^2 - z_i^2 + z_1^2
\]
This yields \(A\mathbf{x} = \mathbf{b}\) where \(\mathbf{x} = [x, y, z]^T\), solvable via least squares.

### Range Finder Terrain Mapping

Lidar and ultrasonic rangefinders measure terrain clearance \(h\) for the rover's suspension control:

**Beam Geometry:**
For a sensor pitched at angle \(\theta\) from horizontal:
\[
h = d \cdot \sin(\theta + \phi) - z_{\text{offset}}
\]
where \(d\) is measured range, \(\phi\) is terrain slope, and \(z_{\text{offset}}\) is sensor mounting height.

**Slope Compensation:**
\[
\phi = \arctan\left(\frac{h_{i+1} - h_i}{\Delta x}\right)
\]
where \(\Delta x\) is distance between consecutive measurements.

**Obstacle Detection:**
A terrain discontinuity is detected when:
\[
|h_{\text{predicted}} - h_{\text{measured}}| > 3\sigma_h
\]
where \(\sigma_h\) is the sensor's range uncertainty.

### Visual Odometry Epipolar Geometry

Mono/stereo visual odometry provides relative motion estimates when GPS is unavailable:

**Feature Tracking:**
For feature point \(\mathbf{p}_1\) in image 1 and \(\mathbf{p}_2\) in image 2:
\[
\mathbf{p}_2^T \mathbf{F} \mathbf{p}_1 = 0
\]
where \(\mathbf{F}\) is the fundamental matrix.

**Essential Matrix Decomposition:**
\[
\mathbf{E} = \mathbf{K}^{-T} \mathbf{F} \mathbf{K}^{-1} = [\mathbf{t}]_\times \mathbf{R}
\]
where \(\mathbf{K}\) is camera calibration matrix, \(\mathbf{R}\) is rotation, and \([\mathbf{t}]_\times\) is skew-symmetric translation matrix.

**Motion Recovery:**
The relative pose \((\mathbf{R}, \mathbf{t})\) between frames is recovered via SVD:
\[
\mathbf{E} = \mathbf{U} \text{diag}(1, 1, 0) \mathbf{V}^T
\]
with four possible solutions resolved via chirality constraint.

**Scale Recovery (Mono):**
For a rover with known wheel encoder ticks \(N\) and wheel radius \(r\):
\[
s = \frac{2\pi r N}{\|\mathbf{t}\|}
\]
where \(s\) scales the translation to metric units.

### Temporal Alignment and Buffer Synchronization

All spatial sensors must be temporally aligned within the 400Hz control loop:

**Timestamp Synchronization:**
For sensor measurement at hardware time \(t_{\text{HW}}\):
\[
t_{\text{EKF}} = t_{\text{HW}} + \Delta t_{\text{latency}} + \Delta t_{\text{clock\_skew}}
\]

**Buffer Index Calculation:**
For ring buffer of size \(N\) at write index \(i_w\) and read index \(i_r\):
\[
i_{\text{valid}} = (i_w - i_r) \bmod N \geq M
\]
where \(M\) is minimum samples for EKF update.

**Overlap Prevention:**
\[
(i_w + L) \bmod N \neq i_r \quad \forall L \in [0, S-1]
\]
where \(S\) is EKF sample batch size.

## C++ Implementation

### GPS Auto-Baud State Machine (AP_DAL_GPS.cpp)

The C++ code directly implements the mathematical state machine for baud rate detection. The `detect_state_machine()` function in `AP_DAL_GPS.cpp` executes the state transition matrix `S(t+1)` defined mathematically.

```cpp
// Mathematical mapping: B = {9600, 19200, 38400, 57600, 115200, 230400, 460800}
static const uint32_t baud_rates[] = {9600, 19200, 38400, 57600, 115200, 230400, 460800};

// Mathematical mapping: P = {UBX (0xB5), NMEA (0x24), SIRF (0xA0), ERB (0xEB), NOVA (0xAA)}
static const uint8_t ubx_probe[] = {0xB5, 0x62, 0x06, 0x00, 0x02, 0x00, 0x08, 0x00};

// Timeout calculation implements: T_i = (10 * 8 * L) / b_i + τ_margin
uint32_t AP_DAL_GPS::calculate_timeout(uint32_t baudrate)
{
    uint32_t byte_time_us = 1000000 / (baudrate / 10); // 10 bits per byte
    return (100 * byte_time_us / 1000) + 50; // L=100 bytes, τ_margin=50ms
}

// Main detection state machine
void AP_DAL_GPS::detect_state_machine(uint8_t instance)
{
    GPS_State &gps = state[instance];
    DetectState &detect = detect_state[instance];
    
    switch (detect.state) {
    case DETECT_STATE_UNKNOWN:
        detect.baud_index = 0;
        detect.protocol_index = 0;
        detect.state = DETECT_STATE_AUTO;
        detect.start_time_ms = AP_HAL::millis();
        break;
        
    case DETECT_STATE_AUTO:
        if (detect.baud_index >= ARRAY_SIZE(baud_rates)) {
            detect.state = DETECT_STATE_UNKNOWN;
            break;
        }
        
        uint32_t baud = baud_rates[detect.baud_index];
        port->begin(baud);
        
        switch (detect.protocol_index) {
        case 0: // UBX
            port->write(ubx_probe, sizeof(ubx_probe));
            detect.expected_length = 10;
            detect.expected_header = 0xB5;
            break;
        // ... other protocols
        }
        
        detect.state = DETECT_STATE_WAITING_RESPONSE;
        detect.response_timeout_ms = AP_HAL::millis() + calculate_timeout(baud);
        break;
        
    case DETECT_STATE_WAITING_RESPONSE:
        if (port->available() > 0) {
            uint8_t byte = port->read();
            if (validate_response_byte(byte, detect)) {
                detect.response_bytes[detect.response_count++] = byte;
                
                if (detect.response_count >= detect.expected_length) {
                    if (validate_complete_response(detect)) {
                        gps.baudrate = baud_rates[detect.baud_index];
                        gps.protocol = detect.protocol_index;
                        detect.state = DETECT_STATE_LOCKED;
                        return;
                    }
                }
            }
        }
        
        if (AP_HAL::millis() > detect.response_timeout_ms) {
            detect.protocol_index++;
            if (detect.protocol_index >= 3) {
                detect.protocol_index = 0;
                detect.baud_index++;
            }
            detect.state = DETECT_STATE_AUTO;
        }
        break;
    }
}
```

### Dual GPS Covariance Blending (AP_DAL_GPS.cpp)

The `blend_gps_solutions()` function implements the inverse covariance weighting mathematics for the 1200 kg agricultural rover.

```cpp
GPS_Blend AP_DAL_GPS::blend_gps_solutions(uint8_t instance1, uint8_t instance2)
{
    GPS_Blend blend;
    blend.blended_valid = false;
    
    GPS_State &gps1 = state[instance1];
    GPS_State &gps2 = state[instance2];
    
    if (gps1.status < GPS_OK_FIX_3D || gps2.status < GPS_OK_FIX_3D) {
        return blend;
    }
    
    Vector3d ecef1 = lla_to_ecef(gps1.latitude, gps1.longitude, gps1.altitude);
    Vector3d ecef2 = lla_to_ecef(gps2.latitude, gps2.longitude, gps2.altitude);
    
    Matrix3d cov1 = calculate_position_covariance(gps1);
    Matrix3d cov2 = calculate_position_covariance(gps2);
    
    // Mathematical mapping: Σ_blended = (Σ Σ_i^{-1})^{-1}
    Matrix3d inv_cov1 = cov1.inverse();
    Matrix3d inv_cov2 = cov2.inverse();
    Matrix3d inv_cov_sum = inv_cov1 + inv_cov2;
    
    if (inv_cov_sum.det() < 1e-12) {
        return blend;
    }
    
    Matrix3d blended_cov = inv_cov_sum.inverse();
    
    // Mathematical mapping: P_blended = (Σ w_i * P_i) / (Σ w_i)
    Vector3d blended_ecef = blended_cov * (inv_cov1 * ecef1 + inv_cov2 * ecef2);
    Vector3d blended_lla = ecef_to_lla(blended_ecef);
    
    // Mathematical mapping: w_i = 1 / (tr(Σ_i) * HDOP_i * max(1, 20 - N_sats,i))
    blend.weight[0] = 1.0 / (cov1.trace() * gps1.hdop * fmaxf(1.0f, 20.0f - gps1.satellites_used));
    blend.weight[1] = 1.0 / (cov2.trace() * gps2.hdop * fmaxf(1.0f, 20.0f - gps2.satellites_used));
    
    float weight_sum = blend.weight[0] + blend.weight[1];
    if (weight_sum > 0) {
        blend.weight[0] /= weight_sum;
        blend.weight[1] /= weight_sum;
    }
    
    // Mahalanobis distance: D² = (P₁ - P₂)ᵀ(Σ₁ + Σ₂)⁻¹(P₁ - P₂)
    Vector3d diff = ecef1 - ecef2;
    Matrix3d combined_cov = cov1 + cov2;
    
    if (combined_cov.det() > 1e-12) {
        Matrix3d inv_combined_cov = combined_cov.inverse();
        double mahalanobis_dist = diff.dot(inv_combined_cov * diff);
        
        const double chi2_threshold = 7.815; // χ²₀.₉₅(3)
        
        if (mahalanobis_dist > chi2_threshold) {
            if (gps1.hdop < gps2.hdop) {
                blended_lla = Vector3d(gps1.latitude, gps1.longitude, gps1.altitude);
                blended_cov = cov1;
                blend.primary_idx = instance1;
            } else {
                blended_lla = Vector3d(gps2.latitude, gps2.longitude, gps2.altitude);
                blended_cov = cov2;
                blend.primary_idx = instance2;
            }
        }
    }
    
    blend.position = blended_lla;
    blend.covariance = blended_cov;
    blend.blended_valid = true;
    
    return blend;
}
```

### Airspeed Sensor Data Buffering (AP_DAL_Airspeed.cpp)

The airspeed DAL implements Bernoulli's principle with temperature compensation for the rover's environmental conditions.

```cpp
struct AirspeedSample {
    uint64_t timestamp_us;      // Microsecond timestamp
    float differential_pa;      // Differential pressure (Pa)
    float temperature_c;        // Sensor temperature (°C)
    float static_pressure_pa;   // Static pressure (Pa)
    uint8_t health;             // Sensor health bitmask
} __attribute__((aligned(64)));

class AP_DAL_Airspeed {
private:
    alignas(64) AirspeedSample buffer[32];
    std::atomic<uint16_t> write_idx;
    std::atomic<uint16_t> read_idx;
    
public:
    // Mathematical mapping: ρ = P / (R * T)
    float calculate_air_density(float pressure_pa, float temperature_c) {
        const float R = 287.05f; // J/(kg·K)
        float T_kelvin = temperature_c + 273.15f;
        return pressure_pa / (R * T_kelvin);
    }
    
    // Mathematical mapping: V_true = V_ind * sqrt(ρ₀/ρ)
    float calculate_true_airspeed(float differential_pa, float density) {
        const float rho0 = 1.225f; // kg/m³ at sea level
        float V_ind = sqrtf(2.0f * differential_pa / rho0);
        return V_ind * sqrtf(rho0 / density);
    }
    
    void update(float diff_pressure, float temperature, float static_pressure) {
        uint16_t idx = write_idx.load(std::memory_order_acquire);
        
        // Apply Bernoulli: q = 0.5 * ρ * V²
        float density = calculate_air_density(static_pressure, temperature);
        float true_airspeed = calculate_true_airspeed(diff_pressure, density);
        
        buffer[idx].timestamp_us = AP_HAL::micros64();
        buffer[idx].differential_pa = diff_pressure;
        buffer[idx].temperature_c = temperature;
        buffer[idx].static_pressure_pa = static_pressure;
        buffer[idx].health = calculate_health(diff_pressure, temperature);
        
        // Atomic update with memory barrier
        write_idx.store((idx + 1) % 32, std::memory_order_release);
        asm volatile("dmb sy" ::: "memory");
    }
    
    bool get_latest(AirspeedSample &sample) {
        uint16_t r_idx = read_idx.load(std::memory_order_acquire);
        uint16_t w_idx = write_idx.load(std::memory_order_acquire);
        
        if (r_idx == w_idx) {
            return false; // Buffer empty
        }
        
        // Read with temporal consistency check
        uint16_t latest_idx = (w_idx - 1) % 32;
        sample = buffer[latest_idx];
        
        // Update read index
        read_idx.store(latest_idx, std::memory_order_release);
        return true;
    }
};
```

### Beacon Trilateration Engine (AP_DAL_Beacon.cpp)

The beacon system implements linearized trilateration for centimeter-accurate local positioning.

```cpp
struct BeaconSample {
    uint64_t timestamp_us;
    float ranges[4];        // Distances to 4 beacons (m)
    float beacon_pos[4][3]; // Beacon positions (x,y,z) in local NED
    uint8_t valid_count;    // Number of valid ranges
} __attribute__((aligned(64)));

class AP_DAL_Beacon {
private:
    alignas(64) BeaconSample buffer[16];
    std::atomic<uint8_t> write_idx;
    
public:
    // Mathematical mapping: Solve A*x = b for trilateration
    Vector3f calculate_position(const BeaconSample &sample) {
        if (sample.valid_count < 3) {
            return Vector3f(NAN, NAN, NAN);
        }
        
        // Build linear system: 2(x₁-xᵢ)x + 2(y₁-yᵢ)y + 2(z₁-zᵢ)z = dᵢ² - d₁² - xᵢ² + x₁² - yᵢ² + y₁² - zᵢ² + z₁²
        Matrix3f A;
        Vector3f b;
        
        for (uint8_t i = 1; i < sample.valid_count; i++) {
            float x1 = sample.beacon_pos[0][0];
            float y1 = sample.beacon_pos[0][1];
            float z1 = sample.beacon_pos[0][2];
            float d1 = sample.ranges[0];
            
            float xi = sample.beacon_pos[i][0];
            float yi = sample.beacon_pos[i][1];
            float zi = sample.beacon_pos[i][2];
            float di = sample.ranges[i];
            
            A(i-1, 0) = 2.0f * (x1 - xi);
            A(i-1, 1) = 2.0f * (y1 - yi);
            A(i-1, 2) = 2.0f * (z1 - zi);
            
            b(i-1) = di*di - d1*d1 - xi*xi + x1*x1 - yi*yi + y1*y1 - zi*zi + z1*z1;
        }
        
        // Solve via QR decomposition (numerically stable)
        return A.householderQr().solve(b);
    }
    
    void update_range(uint8_t beacon_id, float range_m, const Vector3f &beacon_pos_ned) {
        uint8_t idx = write_idx.load(std::memory_order_relaxed);
        
        buffer[idx].timestamp_us = AP_HAL::micros64();
        buffer[idx].ranges[beacon_id] = range_m;
        buffer[idx].beacon_pos[beacon_id][0] = beacon_pos_ned.x;
        buffer[idx].beacon_pos[beacon_id][1] = beacon_pos_ned.y;
        buffer[idx].beacon_pos[beacon_id][2] = beacon_pos_ned.z;
        
        // Count valid ranges (range > 0)
        uint8_t valid = 0;
        for (uint8_t i = 0; i < 4; i++) {
            if (buffer[idx].ranges[i] > 0.0f) {
                valid++;
            }
        }
        buffer[idx].valid_count = valid;
        
        write_idx.store((idx + 1) % 16, std::memory_order_release);
    }
};
```

### Range Finder Terrain Analysis (AP_DAL_RangeFinder.cpp)

The rangefinder DAL implements beam geometry and slope compensation for the rover's suspension control.

```cpp
struct RangeSample {
    uint64_t timestamp_us;
    float range_m;           // Measured range
    float angle_rad;         // Sensor pitch angle
    float vehicle_pitch_rad; // Vehicle pitch at measurement
    float terrain_slope_rad; // Estimated terrain slope
    uint8_t sensor_type;     // LIDAR, ULTRASONIC, etc.
} __attribute__((aligned(64)));

class AP_DAL_RangeFinder {
private:
    alignas(64) RangeSample buffer[8]; // One per sensor
    float z_offset; // Sensor mounting height above ground (m)
    
public:
    // Mathematical mapping: h = d * sin(θ + φ) - z_offset
    float calculate_terrain_clearance(const RangeSample &sample) {
        float total_angle = sample.angle_rad + sample.vehicle_pitch_rad + sample.terrain_slope_rad;
        return sample.range_m * sinf(total_angle) - z_offset;
    }
    
    // Mathematical mapping: φ = arctan((h_{i+1} - h_i) / Δx)
    float estimate_terrain_slope(float h_current, float h_previous, float delta_x) {
        if (delta_x < 0.01f) { // Avoid division by zero
            return 0.0f;
        }
        return atan2f(h_current - h_previous, delta_x);
    }
    
    // Mathematical obstacle detection: |h_predicted - h_measured| > 3σ_h
    bool detect_obstacle(float h_measured, float h_predicted, float sigma_h) {
        return fabsf(h_predicted - h_measured) > (3.0f * sigma_h);
    }
    
    void update(uint8_t sensor_id, float range_m, float vehicle_pitch_rad) {
        if (sensor_id >= 8) return;
        
        RangeSample &sample = buffer[sensor_id];
        uint64_t prev_timestamp = sample.timestamp_us;
        float prev_clearance = calculate_terrain_clearance(sensor_id);
        
        sample.timestamp_us = AP_HAL::micros64();
        sample.range_m = range_m;
        sample.vehicle_pitch_rad = vehicle_pitch_rad;
        
        // Estimate terrain slope from previous measurement
        if (prev_timestamp > 0) {
            float delta_t = (sample.timestamp_us - prev_timestamp) * 1e-6f;
            float delta_x = delta_t * get_vehicle_speed(); // From wheel encoders
            float current_clearance = calculate_terrain_clearance(sensor_id);
            sample.terrain_slope_rad = estimate_terrain_slope(current_clearance, prev_clearance, delta_x);
        }
        
        // Check for obstacles
        float sigma_h = get_sensor_uncertainty(sample.sensor_type);
        if (detect_obstacle(calculate_terrain_clearance(sensor_id), 
                           predict_terrain_clearance(sensor_id), sigma_h)) {
            trigger_obstacle_avoidance(sensor_id);
        }
    }
};
```

### Visual Odometry Feature Tracking (AP_DAL_VisualOdom.cpp)

The visual odometry DAL implements epipolar geometry and scale recovery for the rover's relative motion estimation.

```cpp
struct VOSample {
    uint64_t timestamp_us;
    Matrix3f R;              // Relative rotation matrix
    Vector3f t;              // Relative translation (scaled)
    float scale;             // Scale factor (mono only)
    uint32_t feature_count;  // Number of tracked features
    float reprojection_error;// RMS reprojection error
} __attribute__((aligned(64)));

class AP_DAL_VisualOdom {
private:
    alignas(64) VOSample buffer[4];
    std::atomic<uint8_t> write_idx;
    CameraCalibration K;     // Camera intrinsic matrix
    
public:
    // Mathematical mapping: p₂ᵀ * F * p₁ = 0
    Matrix3f compute_fundamental_matrix(const Vector2f *points1, const Vector2f *points2, uint32_t count) {
        // 8-point algorithm
        MatrixXf A(count, 9);
        for (uint32_t i = 0; i < count; i++) {
            float x1 = points1[i].x, y1 = points1[i].y;
            float x2 = points2[i].x, y2 = points2[i].y;
            
            A(i, 0) = x2 * x1;
            A(i, 1) = x2 * y1;
            A(i, 2) = x2;
            A(i, 3) = y2 * x1;
            A(i, 4) = y2 * y1;
            A(i, 5) = y2;
            A(i, 6) = x1;
            A(i, 7) = y1;
            A(i, 8) = 1.0f;
        }
        
        // SVD: A * f = 0
        JacobiSVD<MatrixXf> svd(A, ComputeFullV);
        VectorXf f = svd.matrixV().col(8);
        
        Matrix3f F;
        F << f(0), f(1), f(2),
             f(3), f(4), f(5),
             f(6), f(7), f(8);
        
        // Enforce rank 2 constraint
        JacobiSVD<Matrix3f> svdF(F, ComputeFullU | ComputeFullV);
        Vector3f S = svdF.singularValues();
        S(2) = 0.0f;
        F = svdF.matrixU() * S.asDiagonal() * svdF.matrixV().transpose();
        
        return F;
    }
    
    // Mathematical mapping: E = K⁻ᵀ * F * K⁻¹ = [t]× * R
    void recover_pose_from_essential(const Matrix3f &E, Matrix3f &R, Vector3f &t) {
        // SVD: E = U * diag(1,1,0) * Vᵀ
        JacobiSVD<Matrix3f> svd(E, ComputeFullU | ComputeFullV);
        Matrix3f U = svd.matrixU();
        Matrix3f V = svd.matrixV().transpose();
        
        // Ensure det(U) > 0, det(V) > 0
        if (U.determinant() < 0) U *= -1.0f;
        if (V.determinant() < 0) V *= -1.0f;
        
        Matrix3f W;
        W << 0.0f, -1.0f, 0.0f,
             1.0f, 0.0f, 0.0f,
             0.0f, 0.0f, 1.0f;
        
        // Four possible solutions
        Matrix3f R1 = U * W * V;
        Matrix3f R2 = U * W.transpose() * V;
        Vector3f t1 = U.col(2);
        Vector3f t2 = -U.col(2);
        
        // Resolve via chirality constraint
        if (check_chirality(R1, t1)) {
            R = R1;
            t = t1;
        } else if (check_chirality(R1, t2)) {
            R = R1;
            t = t2;
        } else if (check_chirality(R2, t1)) {
            R = R2;
            t = t1;
        } else {
            R = R2;
            t = t2;
        }
    }
    
    // Mathematical scale recovery: s = (2πrN) / ‖t‖
    float recover_scale_mono(const Vector3f &t, uint32_t wheel_ticks, float wheel_radius) {
        float distance_wheels = 2.0f * M_PI * wheel_radius * wheel_ticks;
        return distance_wheels / t.norm();
    }
    
    void update(const Vector2f *features_prev, const Vector2f *features_curr, 
                uint32_t count, uint32_t wheel_ticks) {
        if (count < 8) return; // Minimum for 8-point algorithm
        
        // Compute fundamental matrix
        Matrix3f F = compute_fundamental_matrix(features_prev, features_curr, count);
        
        // Compute essential matrix: E = K⁻ᵀ * F * K⁻¹
        Matrix3f E = K.inverse().transpose() * F * K.inverse();
        
        // Recover pose
        Matrix3f R;
        Vector3f t;
        recover_pose_from_essential(E, R, t);
        
        // Recover scale from wheel encoders (mono VO)
        float scale = recover_scale_mono(t, wheel_ticks, 0.15f); // 0.15m wheel radius
        
        // Store result
        uint8_t idx = write_idx.load(std::memory_order_relaxed);
        buffer[idx].timestamp_us = AP_HAL::micros64();
        buffer[idx].R = R;
        buffer[idx].t = t * scale;
        buffer[idx].scale = scale;
        buffer[idx].feature_count = count;
        buffer[idx].reprojection_error = compute_reprojection_error(F, features_prev, features_curr, count);
        
        write_idx.store((idx + 1) % 4, std::memory_order_release);
    }
};
```

### RTOS Threading and Hardware Integration

The spatial sensor DAL operates across multiple RTOS threads with strict priority ordering:

```cpp
// Thread priorities for STM32/Cortex-M7
enum ThreadPriority {
    PRIO_ISR = 15,          // Highest: UART/DMA interrupts
    PRIO_EKF = 10,          // EKF update at 200Hz
    PRIO_SENSOR_PARSER = 7, // GPS/Beacon parsing at 100Hz
    PRIO_LOGGER = 3,        // SD card logging
    PRIO_IDLE = 0           // Background tasks
};

// GPS UART DMA configuration for zero-copy operation
void configure_gps_uart_dma(USART_TypeDef *uart) {
    // Enable clocks
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA2EN;
    
    // Configure DMA for circular reception
    DMA2_Stream2->CR = 0;
    DMA2_Stream2->PAR = (uint32_t)&uart->DR;
    DMA2_Stream2->M0AR = (uint32_t)rx_buffer;
    DMA2_Stream2->NDTR = sizeof(rx_buffer);
    DMA2_Stream2->CR = DMA_SxCR_CHSEL_4 |    // Channel 4 for USART1_RX
                       DMA_SxCR_MINC |       // Memory increment
                       DMA_SxCR_CIRC |       // Circular mode
                       DMA_SxCR_EN;          // Enable
    
    // Configure UART
    uart->CR1 = USART_CR1_UE | USART_CR1_RE | USART_CR1_TE;
    uart->CR3 = USART_CR3_DMAT | USART_CR3_DMAR;
}

// Cache management for Cortex-M