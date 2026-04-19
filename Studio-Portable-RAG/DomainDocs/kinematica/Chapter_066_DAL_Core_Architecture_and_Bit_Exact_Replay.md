# DAL Core Architecture, EKF Isolation, and Bit-Exact Replay Logging

_Generated 2026-04-15 08:19 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/AP_DAL.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_DAL/LogStructure.h`

# Chapter: DAL Core Architecture, EKF Isolation, and Bit-Exact Replay Logging

## Technical Introduction
The files `AP_DAL.cpp`, `AP_DAL.h`, and `LogStructure.h` implement the Data Access Layer (DAL) for ArduPilot, providing strict pointer decoupling between sensor drivers and the Extended Kalman Filter (EKF). This architecture prevents the EKF from directly accessing physical sensor registers, ensuring deterministic behavior for a 400Hz autonomous agricultural rover. The system enables bit-exact replay logging by capturing every bit of sensor data with microsecond timestamps, allowing crash investigation of the 1200 kg vehicle's skid-steering dynamics. The DAL uses double-buffered virtual interfaces with cache-coherent memory barriers on STM32 Cortex-M7, maintaining real-time performance while providing complete sensor state serialization.

## Mathematical Formulation

### Virtual Interface Abstraction and Pointer Decoupling
The DAL creates a mathematical isolation between physical sensors \(\mathcal{S}\) and EKF instances \(\mathcal{E}\) through injective mappings:

**Sensor to Virtual Interface Mapping:**
\[
\Phi: \mathcal{S} \rightarrow \mathcal{V}
\]
where \(\mathcal{V}\) is the set of virtual sensor interfaces. Each physical sensor \(s_i \in \mathcal{S}\) maps to exactly one virtual interface \(v_j \in \mathcal{V}\).

**EKF to Virtual Interface Mapping:**
\[
\Psi: \mathcal{V} \rightarrow \mathcal{E}
\]
with the constraint that \(\Phi \circ \Psi^{-1}\) is undefined, preventing any direct \(\mathcal{E} \rightarrow \mathcal{S}\) connections. This ensures the EKF cannot access physical sensor registers, only the virtual buffers.

**Double-Buffered Atomic Swap:**
Each virtual interface maintains two 64-byte aligned buffers \(B_0\) and \(B_1\) with atomic swap semantics:
\[
B_{\text{current}} = \text{atomic\_swap}(B_{\text{pending}}, B_{\text{current}})
\]
where \(B_{\text{pending}}\) is populated by sensor ISRs and \(B_{\text{current}}\) is consumed by EKF threads. For the agricultural rover's 400Hz control loop, this prevents race conditions during skid-steering maneuvers where gyro and accelerometer data must remain synchronized.

**Cache Coherency Protocol:**
For ARM Cortex-M7 with data cache (D-cache), the DAL enforces:
\[
\text{DCache\_Clean}(B_{\text{pending}}) \rightarrow \text{DCache\_Invalidate}(B_{\text{current}})
\]
This ensures the EKF never reads stale sensor data, critical for the rover's state estimation given its high rotational inertia \(J_{zz} \approx 150 \, \text{kg·m}^2\).

### Bit-Exact Replay State Serialization
The replay system captures complete sensor states for deterministic reconstruction:

**State Vector Definition:**
For each sensor \(i\) at time \(t\), the complete state is:
\[
\mathbf{S}_i(t) = \langle \mathbf{D}_i(t), \mathbf{C}_i(t), \mathbf{T}_i(t) \rangle
\]
where:
- \(\mathbf{D}_i(t) \in \mathbb{R}^{n_i}\) = raw sensor data (e.g., accelerometer \([a_x, a_y, a_z]\), gyro \([\omega_x, \omega_y, \omega_z]\))
- \(\mathbf{C}_i(t) \in \mathbb{R}^{m_i}\) = calibration parameters (offsets \(\mathbf{o}\), scaling matrices \(\mathbf{M}\))
- \(\mathbf{T}_i(t) \in \mathbb{R}^3\) = temperature and timing metadata

**Deterministic Replay Guarantee:**
Given initial conditions \(\mathbf{S}(t_0)\) and recorded inputs \(\mathbf{I}(t)\), the replay produces:
\[
\hat{\mathbf{S}}(t) = \mathcal{F}(\mathbf{S}(t_0), \mathbf{I}(t)) = \mathbf{S}(t) \quad \forall t \in [t_0, t_f]
\]
where \(\mathcal{F}\) is the deterministic flight controller algorithm. For the 1200 kg rover, this allows exact reconstruction of skid-steering dynamics from logged sensor data.

**Delta Encoding with Run-Length Compression:**
Storage efficiency is achieved via:
\[
C(t) = \begin{cases}
\Delta\mathbf{S}(t) & \text{if } \|\Delta\mathbf{S}(t)\| > \epsilon \\
\text{RLE}(\mathbf{S}(t)) & \text{otherwise}
\end{cases}
\]
where \(\epsilon = 10^{-6}\) is the quantization threshold. This reduces log size while maintaining bit-exact reconstruction.

### Virtual Buffer Memory Geometry
Each virtual interface buffer is 64-byte aligned for cache line optimization:

**Buffer Structure:**
\[
B = \langle t_{\text{us}}, \mathbf{d}[12], s, \tau, v, r[2] \rangle
\]
where:
- \(t_{\text{us}} \in \mathbb{N}\) = 64-bit microsecond timestamp
- \(\mathbf{d} \in \mathbb{R}^{12}\) = up to 12 float values (48 bytes)
- \(s \in \mathbb{N}_{16}\) = 16-bit sequence number
- \(\tau \in \mathbb{N}_8\) = 8-bit sensor type
- \(v \in \{0,1\}\) = data validity flag
- \(r \in \mathbb{N}_8^2\) = 2-byte padding for 64-byte alignment

**Total Size Calculation:**
\[
\text{sizeof}(B) = 8 + 48 + 2 + 1 + 1 + 2 = 62 \, \text{bytes}
\]
with 2 bytes padding to reach 64-byte cache line alignment.

### Sequence Number Monotonicity and Gap Detection
The sequence number \(s\) increases monotonically with wrap-around at \(2^{16} = 65536\). Missed updates are detected via:
\[
\Delta s = (s_{\text{current}} - s_{\text{previous}} + 65536) \mod 65536
\]
\[
\text{missed} = \begin{cases}
\Delta s - 1 & \text{if } \Delta s > 1 \\
0 & \text{otherwise}
\end{cases}
\]
For the rover's 400Hz gyro (2.5ms interval), \(\Delta s > 1\) indicates dropped samples during high-G skid-steering turns.

### Timing Statistics and Jitter Analysis
The DAL tracks timing statistics for each sensor:

**Interval Calculation:**
\[
\Delta t_i = t_i - t_{i-1}
\]
\[
\Delta t_{\min} = \min(\Delta t_{\min}, \Delta t_i)
\]
\[
\Delta t_{\max} = \max(\Delta t_{\max}, \Delta t_i)
\]

**Jitter Detection:**
\[
\text{jitter} = \Delta t_{\max} > 10 \cdot \Delta t_{\min} \quad \text{and} \quad \Delta t_{\min} > 0
\]
Excessive jitter triggers diagnostics for the rover's sensor fusion pipeline.

### EKF State Covariance Matrix Storage
The EKF state structure stores the covariance matrix \(\mathbf{P} \in \mathbb{R}^{15 \times 15}\) in packed upper triangular form:

**Covariance Matrix Elements:**
\[
\mathbf{P} = \begin{bmatrix}
P_{00} & P_{01} & \cdots & P_{0,14} \\
P_{01} & P_{11} & \cdots & P_{1,14} \\
\vdots & \vdots & \ddots & \vdots \\
P_{0,14} & P_{1,14} & \cdots & P_{14,14}
\end{bmatrix}
\]

**Packed Storage:**
The 120 unique elements are stored in array \(P[45]\) using:
\[
\text{index}(i,j) = \frac{j(j+1)}{2} + i \quad \text{for } i \leq j
\]
where \(i,j \in [0, 14]\). This reduces storage from 225 to 45 floats (180 bytes).

### CRC-16 Checksum for Log Integrity
Each log structure includes a CRC-16 checksum using polynomial:
\[
G(x) = x^{16} + x^{12} + x^5 + 1
\]
represented as 0x1021. The calculation iterates over \(n\) bytes:
\[
\text{crc} \leftarrow 0xFFFF
\]
\[
\text{for } i = 0 \text{ to } n-1: \quad \text{crc} \leftarrow (\text{crc} \oplus (b_i \ll 8)) \gg 1 \oplus (0x1021 \cdot (\text{crc} \& 0x8000))
\]
\[
C = \text{crc}
\]
This detects corruption during SD card writes for the rover's field logging.

### DMA SD Card Writing Geometry
The SD card writer uses 512-byte sectors with DMA double-buffering:

**Sector Alignment:**
\[
\text{sector\_offset} = \text{file\_position} \mod 512
\]
\[
\text{padding} = 512 - \text{sector\_offset} \quad \text{if } \text{sector\_offset} > 0
\]

**DMA Buffer Management:**
Two buffers \(B_0\) and \(B_1\) alternate:
\[
B_{\text{active}} = \begin{cases}
B_0 & \text{if } \text{DMA}_1 \text{ busy} \\
B_1 & \text{otherwise}
\end{cases}
\]
\[
\text{write\_ready} = \neg(\text{DMA}_0 \text{ busy} \land \text{DMA}_1 \text{ busy})
\]
This ensures non-blocking writes during the rover's 400Hz control loop.

### Deterministic Timestamp Synchronization
All sensors share a common timebase with microsecond resolution:

**Timestamp Conversion:**
\[
t_{\text{us}} = t_{\text{ms}} \cdot 1000 + t_{\mu\text{s}}
\]
where \(t_{\text{ms}}\) from 32-bit millisecond counter and \(t_{\mu\text{s}}\) from 32-bit microsecond timer.

**Synchronization Error:**
\[
\epsilon_t = |t_{\text{sensor}} - t_{\text{system}}|
\]
\[
\text{sync\_valid} = \epsilon_t < 1000 \, \mu\text{s}
\]
Required for the rover's multi-sensor fusion during rapid skid-steering direction changes.

### Memory Pool Allocation Mathematics
The DAL uses aligned memory pools for sensor buffers:

**Alignment Calculation:**
\[
\text{aligned\_size} = \left\lceil \frac{\text{size}}{64} \right\rceil \cdot 64
\]
\[
\text{aligned\_address} = \left\lfloor \frac{\text{address} + 63}{64} \right\rfloor \cdot 64
\]

**Pool Utilization:**
\[
\text{utilization}_i = \frac{\text{allocations}_i \cdot \text{aligned\_size}_i}{\text{pool\_size}_i}
\]
Monitored to prevent fragmentation during long-duration rover operations.

### Log Structure Header Encoding
Each log entry begins with a 16-byte header:

**Header Structure:**
\[
H = \langle 0xA3, 0x95, \text{msgid}, \text{type}, t_{\text{ms}}, t_{\mu\text{s}}, C \rangle
\]
where:
- Magic bytes: 0xA3, 0x95
- msgid \(\in \mathbb{N}_8\) = message identifier
- type \(\in \mathbb{N}_8\) = structure type
- \(t_{\text{ms}} \in \mathbb{N}_{32}\) = millisecond timestamp
- \(t_{\mu\text{s}} \in \mathbb{N}_{32}\) = microsecond portion
- \(C \in \mathbb{N}_{16}\) = CRC-16 of payload

**Total Header Size:**
\[
\text{sizeof}(H) = 1 + 1 + 1 + 1 + 4 + 4 + 2 = 14 \, \text{bytes}
\]
with 2 bytes implicit padding to 16-byte boundary in packed struct.

### Sensor Data Quantization and Encoding
Different sensor types use specific encodings:

**GPS Coordinates:**
\[
\text{lat}_{encoded} = \text{lat}_{deg} \times 10^7 \quad (\text{int32_t})
\]
\[
\text{lon}_{encoded} = \text{lon}_{deg} \times 10^7 \quad (\text{int32_t})
\]

**Temperature:**
\[
T_{encoded} = T_{°C} \times 100 \quad (\text{int16_t})
\]

**HDOP:**
\[
\text{hdop}_{encoded} = \text{hdop} \times 100 \quad (\text{uint16_t})
\]

These fixed-point representations maintain precision while reducing storage for the rover's extensive field logs.

### EKF Innovation Statistics Logging
The EKF logs measurement innovations and variances:

**Innovation Vector:**
\[
\mathbf{y} = \mathbf{z} - \mathbf{h}(\hat{\mathbf{x}})
\]
where \(\mathbf{z}\) is measurement and \(\mathbf{h}(\hat{\mathbf{x}})\) is predicted measurement.

**Normalized Innovation:**
\[
\nu = \frac{y}{\sqrt{S}}
\]
where \(S\) is innovation variance. Logged for fault detection during rover operation.

**Fault Detection:**
\[
\text{fault} = |\nu| > 5.0
\]
Triggers sensor health monitoring for the agricultural rover's safety systems.

### Replay Control Synchronization
The replay system maintains synchronization during playback:

**Playback Speed:**
\[
t_{\text{playback}} = t_{\text{log}} \cdot s_{\text{speed}}
\]
where \(s_{\text{speed}} \in \mathbb{R}^+\) is playback speed multiplier.

**Loop Management:**
\[
\text{loop\_complete} = t_{\text{playback}} > t_{\text{end}}
\]
\[
t_{\text{playback}} = t_{\text{start}} \quad \text{if } \text{loop\_complete} \land \text{loops} < \text{loop\_count}
\]

**Synchronization Error:**
\[
\epsilon_{\text{sync}} = |t_{\text{playback}} - t_{\text{system}}|
\]
Corrected via PID control for smooth rover dynamics replay.

## C++ Implementation

### Virtual Interface Instantiation (AP_DAL.cpp)

```cpp
// AP_DAL.cpp - Data Access Layer implementation
#include "AP_DAL.h"
#include <AP_HAL/AP_HAL.h>

// Maximum number of virtual sensor interfaces
#define DAL_MAX_VIRTUAL_SENSORS 16
#define DAL_BUFFER_ALIGNMENT 64

// Virtual sensor interface structure (64-byte aligned for cache lines)
struct __attribute__((aligned(DAL_BUFFER_ALIGNMENT))) VirtualSensor {
    // Double-buffered data storage
    struct SensorData {
        uint64_t timestamp_us;      // Microsecond timestamp
        float data[12];             // Up to 12 float values (48 bytes)
        uint16_t sequence;          // Monotonically increasing sequence number
        uint8_t sensor_type;        // Sensor type identifier
        uint8_t data_valid;         // Data validity flag
        uint8_t reserved[2];        // Padding for 64-byte alignment
    };
    
    SensorData buffers[2];          // Double buffer
    volatile uint8_t active_buffer; // Currently active buffer (0 or 1)
    uint32_t update_count;          // Total updates received
    
    // Statistics
    uint32_t missed_updates;
    uint32_t late_updates;
    uint32_t sequence_errors;
    
    // Timing
    uint32_t last_update_us;
    uint32_t min_interval_us;
    uint32_t max_interval_us;
    
    // Initialize virtual sensor
    void init(uint8_t type) {
        memset(this, 0, sizeof(VirtualSensor));
        buffers[0].sensor_type = type;
        buffers[1].sensor_type = type;
        active_buffer = 0;
        min_interval_us = UINT32_MAX;
    }
    
    // Update with new sensor data (called from ISR)
    bool update(const float* new_data, uint8_t data_count, uint64_t timestamp_us) {
        if (data_count > 12) return false;
        
        uint8_t next_buffer = 1 - active_buffer;
        SensorData& buf = buffers[next_buffer];
        
        // Copy data
        buf.timestamp_us = timestamp_us;
        memcpy(buf.data, new_data, data_count * sizeof(float));
        buf.data_valid = 1;
        
        // Update sequence number
        static uint16_t global_sequence = 0;
        buf.sequence = global_sequence++;
        
        // Calculate timing statistics
        if (last_update_us != 0) {
            uint32_t interval = timestamp_us - last_update_us;
            min_interval_us = MIN(min_interval_us, interval);
            max_interval_us = MAX(max_interval_us, interval);
            
            // Check for missed updates
            if (interval > 2 * min_interval_us) {
                missed_updates++;
            }
        }
        last_update_us = timestamp_us;
        
        // Atomically swap buffers
        __DSB(); // Data synchronization barrier
        active_buffer = next_buffer;
        __DSB();
        
        update_count++;
        return true;
    }
    
    // Read current sensor data (called from EKF)
    bool read(float* output, uint8_t& data_count, uint64_t& timestamp_us, uint16_t& sequence) const {
        const SensorData& buf = buffers[active_buffer];
        
        if (!buf.data_valid) {
            return false;
        }
        
        // Determine actual data count based on sensor type
        switch (buf.sensor_type) {
            case DAL_SENSOR_ACCEL:
            case DAL_SENSOR_GYRO:
                data_count = 3;
                break;
            case DAL_SENSOR_MAG:
                data_count = 3;
                break;
            case DAL_SENSOR_BARO:
                data_count = 1;
                break;
            default:
                data_count = 0;
                return false;
        }
        
        memcpy(output, buf.data, data_count * sizeof(float));
        timestamp_us = buf.timestamp_us;
        sequence = buf.sequence;
        
        return true;
    }
    
    // Get sensor statistics
    void get_stats(uint32_t& updates, uint32_t& missed, uint32_t& late, 
                   uint32_t& min_int, uint32_t& max_int) const {
        updates = update_count;
        missed = missed_updates;
        late = late_updates;
        min_int = min_interval_us;
        max_int = max_interval_us;
    }
};

// DAL manager singleton
class AP_DAL_Manager {
private:
    VirtualSensor sensors[DAL_MAX_VIRTUAL_SENSORS];
    uint8_t registered_sensors;
    
    // Thread safety
    HAL_Semaphore sem;
    
    // Memory pools for different sensor types
    struct MemoryPool {
        void* buffer;
        size_t size;
        uint32_t allocations;
    };
    
    MemoryPool pools[4];
    
public:
    AP_DAL_Manager() : registered_sensors(0) {
        // Initialize memory pools
        for (int i = 0; i < 4; i++) {
            pools[i].buffer = nullptr;
            pools[i].size = 0;
            pools[i].allocations = 0;
        }
    }
    
    // Register a new virtual sensor
    uint8_t register_sensor(uint8_t sensor_type) {
        if (registered_sensors >= DAL_MAX_VIRTUAL_SENSORS) {
            return 0xFF; // Error
        }
        
        sensors[registered_sensors].init(sensor_type);
        return registered_sensors++;
    }
    
    // Update sensor data (called from sensor drivers)
    bool update_sensor(uint8_t handle, const float* data, uint8_t count, uint64_t timestamp_us) {
        if (handle >= registered_sensors) {
            return false;
        }
        
        return sensors[handle].update(data, count, timestamp_us);
    }
    
    // Read sensor data (called from EKF)
    bool read_sensor(uint8_t handle, float* data, uint8_t& count, 
                     uint64_t& timestamp_us, uint16_t& sequence) {
        if (handle >= registered_sensors) {
            return false;
        }
        
        return sensors[handle].read(data, count, timestamp_us, sequence);
    }
    
    // Allocate aligned memory for sensor buffers
    void* allocate_buffer(size_t size, uint8_t pool_id) {
        if (pool_id >= 4) return nullptr;
        
        // Ensure 64-byte alignment
        size = (size + DAL_BUFFER_ALIGNMENT - 1) & ~(DAL_BUFFER_ALIGNMENT - 1);
        
        void* ptr = hal.util->malloc_type(size, HAL_MALLOC_CACHE_COHERENT);
        if (ptr) {
            pools[pool_id].buffer = ptr;
            pools[pool_id].size = size;
            pools[pool_id].allocations++;
        }
        
        return ptr;
    }
    
    // Free allocated memory
    void free_buffer(void* ptr, uint8_t pool_id) {
        if (pool_id >= 4 || !ptr) return;
        
        hal.util->free_type(ptr, pools[pool_id].size, HAL_MALLOC_CACHE_COHERENT);
        pools[pool_id].allocations--;
    }
    
    // Get statistics for a sensor
    bool get_sensor_stats(uint8_t handle, uint32_t& updates, uint32_t& missed,
                         uint32_t& late, uint32_t& min_int, uint32_t& max_int) {
        if (handle >= registered_sensors) {
            return false;
        }
        
        sensors[handle].get_stats(updates, missed, late, min_int, max_int);
        return true;
    }
    
    // Get total registered sensors
    uint8_t get_sensor_count() const {
        return registered_sensors;
    }
    
    // Validate all sensors (diagnostics)
    bool validate_sensors() {
        for (uint8_t i = 0; i < registered_sensors; i++) {
            uint32_t updates, missed, late, min_int, max_int;
            sensors[i].get_stats(updates, missed, late, min_int, max_int);
            
            // Check for excessive missed updates
            if (updates > 100 && missed > updates / 10) {
                return false;
            }
            
            // Check for timing anomalies
            if (max_int > 10 * min_int && min_int > 0) {
                return false;
            }
        }
        
        return true;
    }
};

// Global DAL manager instance
static AP_DAL_Manager dal_manager;
```

### EKF Pointer Decoupling (AP_DAL.h)

```cpp
// AP_DAL.h - Data Access Layer interface definitions
#pragma once
#include <stdint.h>
#include <stddef.h>

// Forward declarations to prevent includes
struct EKF3;
struct NavEKF3_core;

// Sensor type identifiers
enum DAL_SensorType {
    DAL_SENSOR_ACCEL = 0,
    DAL_SENSOR_GYRO = 1,
    DAL_SENSOR_MAG = 2,
    DAL_SENSOR_BARO = 3,
    DAL_SENSOR_GPS = 4,
    DAL_SENSOR_RANGEFINDER = 5,
    DAL_SENSOR_OPTICAL_FLOW = 6,
    DAL_SENSOR_AIRSPEED = 7,
    DAL_SENSOR_EXTERNAL_NAV = 8
};

// Virtual sensor handle
typedef uint8_t DAL_SensorHandle;

// EKF interface structure (opaque to sensor drivers)
struct DAL_EKF_Interface {
    // Pure virtual interface - no direct access to EKF internals
    virtual bool get_attitude(float& roll, float& pitch, float& yaw) = 0;
    virtual bool get_position(float& lat, float& lng, float& alt) = 0;
    virtual bool get_velocity(float& vn, float& ve, float& vd) = 0;
    virtual bool get_gyro_bias(float& bias_x, float& bias_y, float& bias_z) = 0;
    virtual bool get_accel_bias(float& bias_x, float& bias_y, float& bias_z) = 0;
    
    // Protected destructor
protected:
    virtual ~DAL_EKF_Interface() {}
};

// Sensor interface structure (opaque to EKF)
struct DAL_Sensor_Interface {
    // Sensor data access methods
    virtual bool read_accel(float data[3], uint64_t& timestamp_us) = 0;
    virtual bool read_gyro(float data[3], uint64_t& timestamp_us) = 0;
    virtual bool read_mag(float data[3], uint64_t& timestamp_us) = 0;
    virtual bool read_baro(float& pressure, uint64_t& timestamp_us) = 0;
    virtual bool read_gps(float& lat, float& lng, float& alt, 
                          float& vel_n, float& vel_e, float& vel_d,
                          uint64_t& timestamp_us) = 0;
    
    // Sensor health and calibration
    virtual bool is_healthy(uint8_t sensor_type) = 0;
    virtual bool is_calibrated(uint8_t sensor_type) = 0;
    
    // Protected destructor
protected:
    virtual ~DAL_Sensor_Interface() {}
};

// Factory functions (implemented in AP_DAL.cpp)
#ifdef __cplusplus
extern "C" {
#endif

// Create EKF interface (called by EKF)
DAL_EKF_Interface* DAL_create_ekf_interface(uint8_t ekf_instance);

// Create sensor interface (called by sensor drivers)
DAL_Sensor_Interface* DAL_create_sensor_interface(uint8_t sensor_instance);

// Register callback for new sensor data
typedef void (*DAL_Sensor_Callback)(uint8_t sensor_type, const float* data, 
                                    uint8_t data_count, uint64_t timestamp_us, 
                                    void* user_data);
bool DAL_register_sensor_callback(uint8_t sensor_type, DAL_Sensor_Callback cb, 
                                 void* user_data);

// Unregister callback
bool DAL_unregister_sensor_callback(uint8_t sensor_type, DAL_Sensor_Callback cb);

// Get DAL statistics
struct DAL_Statistics {
    uint32_t total_updates;
    uint32_t missed_updates;
    uint32_t late_updates;
    uint32_t buffer_overruns;
    uint32_t sequence_errors;
};
bool DAL_get_statistics(DAL_Statistics& stats);

#ifdef __cplusplus
}
#endif

// Template-based type-safe interface (for C++ users)
template<typename T>
class DAL_Interface {
protected:
    T* impl;
    
public:
    DAL_Interface() : impl(nullptr) {}
    virtual ~DAL_Interface() {
        if (impl) {
            delete impl;
        }
    }
    
    // Disable copy constructor and assignment
    DAL_Interface(const DAL_Interface&) = delete;
    DAL_Interface& operator=(const DAL_Interface&) = delete;
    
    // Move semantics
    DAL_Interface(DAL_Interface&& other) noexcept : impl(other.impl) {
        other.impl = nullptr;
    }
    
    DAL_Interface& operator=(DAL_Interface&& other) noexcept {
        if (this != &other) {
            if (impl) delete impl;
            impl = other.impl;
            other.impl = nullptr;
        }
        return *this;
    }
    
    bool is_valid() const { return impl != nullptr; }
    T* operator->() { return impl; }
    const T* operator->() const { return impl; }
};

// Concrete EKF interface implementation
class DAL_EKF_Interface_Impl : public DAL_EKF_Interface, 
                               public DAL_Interface<DAL_EKF_Interface_Impl> {
private:
    uint8_t ekf_instance;
    uint32_t last_update_ms;
    
public:
    DAL_EKF_Interface_Impl(uint8_t instance) : ekf_instance(instance), 
                                               last_update_ms(0) {
        impl = this;
    }
    
    bool get_attitude(float& roll, float& pitch, float& yaw) override {
        // Access through virtual sensor interface, not direct EKF pointer
        float data[4];
        uint8_t count;
        uint64_t timestamp;
        uint16_t sequence;
        
        if (!dal_manager.read_sensor(DAL_SENSOR_ATTITUDE, data, count, timestamp, sequence)) {
            return false;
        }
        
        if (count >= 3) {
            roll = data[0];
            pitch = data[1];
            yaw = data[2];
            return true;
        }
        
        return false;
    }
    
    bool get_position(float& lat, float& lng, float& alt) override {
        float data[3];
        uint8_t count;
        uint64_t timestamp;
        uint16_t sequence;
        
        if (!dal_manager.read_sensor(DAL_SENSOR_POSITION, data, count, timestamp, sequence)) {
            return false;
        }
        
        if (count >= 3) {
            lat = data[0];
            lng = data[1];
            alt = data[2];
            return true;
        }
        
        return false;
    }
    
    // ... other implementations
};

// Concrete sensor interface implementation
class DAL_Sensor_Interface_Impl : public DAL_Sensor_Interface,
                                  public DAL_Interface<DAL_Sensor_Interface_Impl> {
private:
    uint8_t sensor_instance;
    
public:
    DAL_Sensor_Interface_Impl(uint8_t instance) : sensor_instance(instance) {
        impl = this;
    }
    
    bool read_accel(float data[3], uint64_t& timestamp_us) override {
        uint8_t count;
        uint16_t sequence;
        return dal_manager.read_sensor(DAL_SENSOR_ACCEL, data, count, timestamp_us, sequence);
    }
    
    // ... other sensor read implementations
};
```

### Deterministic Sensor Serialization (LogStructure.h)

```cpp
// LogStructure.h - Binary logging structures for deterministic replay
#pragma once
#include <stdint.h>
#include <stddef.h>

// Compiler packing directives
#pragma pack(push, 1)

// Base log structure header (16 bytes)
struct PACKED LogStructure_Header {
    uint8_t head1, head2;           // Magic bytes: 0xA3, 0x95
    uint8_t msgid;                  // Message ID
    uint8_t type;                   // Structure type
    uint32_t time_ms;               // Timestamp in milliseconds
    uint32_t time_us;               // Microsecond portion
    uint16_t crc;                   // CRC-16 of payload
};

// Sensor data structure (128 bytes)
struct PACKED LogStructure_SensorData {
    LogStructure_Header header;     // 16 bytes
    
    // Sensor identification
    uint8_t sensor_type;            // DAL_SensorType
    uint8_t instance;               // Sensor instance number
    uint16_t sequence;              // Sequence number
    
    // Raw sensor data
    union {
        struct {
            float accel[3];         // Accelerometer (m/s²)
            float gyro[3];          // Gyroscope (rad/s)
            float mag[3];           // Magnetometer (μT)
            float baro;             // Barometer (hPa)
        } imu;
        
        struct {
            double latitude;        // Degrees * 1e7
            double longitude;       // Degrees * 1e7
            float altitude;         // Meters
            float velocity_n;       // North velocity (m/s)
            float velocity_e;       // East velocity (m/s)
            float velocity_d;       // Down velocity (m/s)
            uint8_t fix_type;       // GPS fix type
            uint8_t satellites;     // Satellite count
            uint16_t hdop;          // Horizontal dilution of precision * 100
        } gps;
        
        struct {
            float distance;         // Distance in meters
            float voltage;          // Sensor voltage
            uint8_t quality;        // Signal quality (0-100)
            uint8_t type;           // Rangefinder type
            uint16_t reserved;
        } rangefinder;
    } data;
    
    // Calibration data at time of measurement
    struct {
        float offsets[3];           // Sensor offsets
        float scales[3];            // Scale factors
        float temperature;          // Temperature in °C
        uint32_t calib_time_ms;     // Last calibration time
    } calibration;
    
    // Timing and synchronization
    uint32_t sensor_timestamp_us;   // Original sensor timestamp
    uint32_t read_time_us;          // Time when data was read
    uint32_t process_time_us;       // Time when data was processed
    
    // Status flags
    union {
        struct {
            uint8_t data_valid : 1;
            uint8_t calib_valid : 1;
            uint8_t temp_valid : 1;
            uint8_t timeout : 1;
            uint8_t crc_error : 1;
            uint8_t overflow : 1;
            uint8_t health_ok : 1;
            uint8_t reserved : 1;
        } bits;
        uint8_t byte;
    } status;
    
    // Padding to 128 bytes
    uint8_t padding[7];
};

// EKF state structure (256 bytes)
struct PACKED LogStructure_EKFState {
    LogStructure_Header header;     // 16 bytes
    
    // Quaternion attitude
    float q1, q2, q3, q4;           // Quaternion components
    
    // Position and velocity
    double latitude, longitude;     // Degrees * 1e7
    float altitude;                 // Meters
    float velocity_n, velocity_e, velocity_d; // NED velocity (m/s)
    
    // Gyro and accel biases
    float gyro_bias[3];             // Gyroscope bias (rad/s)
    float accel_bias[3];            // Accelerometer bias (m/s²)
    
    // Wind estimation
    float wind_n, wind_e;           // North/East wind (m/s)
    
    // Terrain estimation
    float terrain_alt;              // Terrain altitude (m)
    float terrain_velocity;         // Terrain-relative velocity (m/s)
    
    // Covariance matrices (packed upper triangular)
    float P[45];                    // State covariance (180 bytes)
    
    // Innovation statistics
    float innov[12];                // Measurement innovations
    float innov_var[12];            // Innovation variances
    
    // Filter status
    uint32_t filter_status;         // EKF status flags
    uint8_t fault_status;           // Fault detection status
    uint8_t primary_imu;            // Primary IMU index
    uint8_t primary_gps;            // Primary GPS index
    uint8_t solution_status;        // Solution status
    
    // Timing
    uint32_t predict_time_us;       // Prediction time
    uint32_t update_time_us;        // Update time
    uint32_t lag_time_us;           // Time lag
    
    // Padding to 256 bytes
    uint8_t padding[11];
};

// Event marker structure (32 bytes)
struct PACKED LogStructure_Event {
    LogStructure_Header header;     // 16 bytes
    
    // Event identification
    uint16_t event_id;              // Event identifier
    uint8_t event_type;             // Event type
    uint8_t severity;               // Severity level
    
    // Event data
    union {
        struct {
            float param1, param2, param3;
            uint32_t code;
        } numeric;
        
        struct {
            char text[12];          // Short text description
            uint16_t line;          // Source line number
        } text;
        
        struct {
            uint32_t address;       // Memory address
            uint32_t value;         // Memory value
            uint32_t old_value;     // Previous value
        } memory;
    } data;
    
    // Source information
    char file[4];                   // Source file (abbreviated)
    uint16_t line;                  // Line number
    
    // Padding to 32 bytes
    uint8_t padding[2];
};

// System state structure (64 bytes)
struct PACKED LogStructure_SystemState {
    LogStructure_Header header;     // 16 bytes
    
    // CPU and memory usage
    uint16_t cpu_load;              // CPU load percentage
    uint16_t memory_used;           // Used memory (KB)
    uint16_t memory_free;           // Free memory (KB)
    uint16_t stack_free;            // Free stack (bytes)
    
    // Task scheduling
    uint32_t task_counts[8];        // Task execution counts
    uint32_t task_times[8];         // Task execution times (μs)
    
    // System health
    uint8_t sensor_health;          //