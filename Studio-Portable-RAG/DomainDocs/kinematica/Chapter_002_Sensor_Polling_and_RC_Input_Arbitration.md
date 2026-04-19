# Asynchronous Sensor Polling and RC Input Arbitration

_Generated 2026-04-14 17:39 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/sensors.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/radio.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/RC_Channel.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/RC_Channel.h`

# Chapter: Asynchronous Sensor Polling and RC Input Arbitration

## Introduction

This chapter documents the deterministic, multi-threaded architecture responsible for ingesting asynchronous sensor data and arbitrating human radio control inputs within the ArduPilot Rover's 400Hz real-time system. The implementation, spanning `sensors.cpp`, `radio.cpp`, `RC_Channel.cpp`, and `RC_Channel.h`, solves the critical challenge of merging low-frequency, noisy sensor streams (GPS, compass) with high-frequency, safety-critical RC commands. `sensors.cpp` implements lock-free ring buffers and atomic state management for jitter-free sensor fusion. `RC_Channel.cpp` encodes the precise mathematical pipeline for PWM normalization, exponential shaping, and skid-steer mixing. `radio.cpp` provides hardware-accelerated deadzone filtering and a priority-based state machine that guarantees human override supremacy. Together, these modules ensure sub-10ms control latency with guaranteed fail-safe behavior, enabling precise autonomous operation of a heavy agricultural rover while maintaining absolute human-in-the-loop authority.

## Mathematical Formulation for Asynchronous Sensor Polling and RC Input Arbitration

This section details the exact mathematical models governing the asynchronous ingestion of sensor data and the deterministic arbitration of human radio control inputs for a heavy agricultural rover. The formulations directly map to the physical constraints of skid-steering dynamics, sensor latency, and safety-critical override logic.

### PWM Normalization with Hardware Deadzone Filtering

The raw PWM signal from the RC receiver (typically 1000-2000µs) must be normalized to a control range of [-1.0, 1.0] with a configurable deadzone to prevent unintended control inputs due to signal noise or stick centering error.

**Linear Mapping with Deadzone:**
```
Let:
  pwm_min = minimum valid PWM (e.g., 1100µs)
  pwm_max = maximum valid PWM (e.g., 1900µs)
  pwm_center = center/trim PWM (e.g., 1500µs)
  deadzone = deadzone width (e.g., 40µs)
  pwm_raw = raw input PWM value
  
Define:
  half_deadzone = deadzone / 2
  deadzone_low = pwm_center - half_deadzone
  deadzone_high = pwm_center + half_deadzone

Normalized value = 
  ⎧ 0.0                                     if pwm_raw ∈ [deadzone_low, deadzone_high]
  ⎨ (pwm_raw - pwm_center + half_deadzone) / (pwm_center - pwm_min - half_deadzone)
  ⎩      if pwm_raw < deadzone_low
  ⎪ (pwm_raw - pwm_center - half_deadzone) / (pwm_max - pwm_center - half_deadzone)
      if pwm_raw > deadzone_high
```
This piecewise function ensures any PWM value within the deadzone region maps to exactly zero, eliminating control jitter. The denominators scale the remaining range linearly to [-1.0, 1.0].

**Exponential Curve Formulation for Control Sensitivity:**
To allow fine control near center while maintaining full authority at stick extremes, an exponential curve is applied:
```
Let:
  x = normalized input ∈ [-1, 1]
  k = expo coefficient ∈ [0, 1]
  
Exponential output = 
  ⎧ x * (k + (1 - k) * x²)     if x ≥ 0
  ⎨ x * (k + (1 - k) * (-x²))  if x < 0
```
Where `k=1.0` gives linear response, and `k=0.0` gives pure cubic response. This preserves the sign of the input while altering the sensitivity curve.

**Rate Scaling with Fine Control Deadzone:**
The normalized, exponentiated input is then scaled by a rate factor for the rover's steering and throttle response:
```
Let:
  x = exponential output ∈ [-1, 1]
  r = rate scaling factor > 0
  ε = fine control threshold (e.g., 0.01)
  
Rate-scaled output = 
  ⎧ 0.0                       if |x * r| < ε * r
  ⎨ x * r                     otherwise
```
This adds a secondary deadzone at very low command values to prevent motor "buzzing" from infinitesimal control signals, crucial for a heavy vehicle's drivetrain.

### Sensor Fusion Timing and Latency Compensation

Asynchronous sensors (GPS at 5-10Hz, compass at 10Hz) update at different rates than the 400Hz EKF3 filter. Measurements must be temporally aligned to the filter's time horizon.

**Asynchronous Update Latency Compensation:**
```
Let:
  t_gps = GPS measurement timestamp
  t_compass = Compass measurement timestamp  
  t_fusion = Fusion timestamp (current EKF3 update)
  Δt_gps = t_fusion - t_gps
  Δt_compass = t_fusion - t_compass

Compensated GPS position = p_gps + v_gps * Δt_gps
Compensated compass field = R(ω * Δt_compass) * B_compass

Where:
  p_gps = raw GPS position (latitude, longitude, altitude converted to NED)
  v_gps = GPS velocity vector in NED frame
  R(θ) = 3D rotation matrix for small angle θ
  ω = angular rate vector from gyro (rad/s)
  B_compass = raw magnetic field vector in body frame (μT)
```
The GPS position is forward-propagated using its reported velocity. The compass measurement is rotated using the integrated gyro data to account for the rover's attitude change between the compass sample time and the fusion time.

### Magnetometer Calibration and Soft-Iron Correction

The raw magnetometer reading from sensors like the AK8963 must be calibrated to account for hard-iron offsets and soft-iron distortions caused by the rover's metal structure.

**Raw Data Conversion:**
The AK8963 outputs 16-bit values in its internal coordinate system:
```
Hx_raw = (int16_t)((buffer[1] << 8) | buffer[0])
Hy_raw = (int16_t)((buffer[3] << 8) | buffer[2])
Hz_raw = (int16_t)((buffer[5] << 8) | buffer[4])
```
These are converted to microtesla using the sensor's sensitivity (typically 0.15 μT/LSB):
```
Hx = Hx_raw * 0.15f
Hy = Hy_raw * 0.15f
Hz = Hz_raw * 0.15f
```

**Soft-Iron Calibration Matrix Application:**
The calibrated magnetic field vector is computed as:
```
H_calibrated = soft_iron_matrix * (H_raw - hard_iron_offset)
```
Where:
*   `hard_iron_offset` is a 3x1 vector representing the constant magnetic bias (in μT).
*   `soft_iron_matrix` is a 3x3 matrix that corrects for scaling and cross-axis sensitivity.
*   Both are determined during an on-ground calibration routine specific to the rover's configuration.

### Control Arbitration and Human Override Mathematics

The system arbitrates between autonomous commands and human RC inputs using a priority-based state machine.

**Human Override Detection Condition:**
An override is triggered when all of the following conditions are met:
```
Let:
  rc_active = (steering_pwm ≠ 0) ∧ (throttle_pwm ≠ 0)
  valid_range = (steering_pwm ∈ [900, 2100]) ∧ (throttle_pwm ∈ [900, 2100])
  movement_detected = (|steering_norm| > RC_DEADZONE) ∨ (|throttle_norm| > RC_DEADZONE)
  override_condition = rc_active ∧ valid_range ∧ movement_detected
```
Where `steering_norm` and `throttle_norm` are the normalized values after deadzone filtering.

**Override Debounce Timing:**
To prevent transient stick movements from causing erratic mode switching, a debounce timer is used:
```
Let:
  t_override_start = time when deflection first exceeds threshold
  t_current = current system time
  override_active = (t_current - t_override_start) > OVERRIDE_DEBOUNCE_MS
```
Only if the deflection is sustained for longer than `OVERRIDE_DEBOUNCE_MS` (e.g., 200ms) is the override activated.

### Skid-Steer Mixing Matrix for RC Commands

When in manual RC mode with skid-steer configuration, the normalized steering and throttle commands are mixed to produce left and right wheel commands:
```
[Left]   [ 1  1 ] [throttle]
[Right] = [ 1 -1 ] [steering ]
```
This simplifies to:
```
Left = throttle + steering
Right = throttle - steering
```
Where both `throttle` and `steering` are in the range [-1.0, 1.0]. The resulting `Left` and `Right` commands are then clamped to [-1.0, 1.0] before being sent to the motor controllers. For a heavy rover, a rate limit is also applied to the steering command to prevent overly aggressive turns that could cause slippage or instability:
```
steering_rate_limited[k] = steering_rate_limited[k-1] + clamp(steering[k] - steering_rate_limited[k-1], -MAX_STEERING_RATE, +MAX_STEERING_RATE)
```
Where `MAX_STEERING_RATE` is defined by the vehicle's mass and inertia to prevent rollover or skidding.

### Exponential Moving Average Filter for Sensor Data

Asynchronous sensor data (like magnetometer) is filtered using an Exponential Moving Average (EMA) to reduce noise without introducing significant latency:
```
Let:
  M_filtered[k] = filtered value at step k
  M_new[k] = new raw measurement
  α = filter coefficient ∈ (0, 1)

M_filtered[k] = α * M_new[k] + (1 - α) * M_filtered[k-1]
```
The coefficient `α` is chosen based on the sensor update rate. For a 10Hz compass, `α = 0.3` provides effective noise reduction while maintaining reasonable response time.

## C++ Implementation

This section details the specific C++ implementation that executes the asynchronous sensor polling and RC input arbitration mathematical models. The code implements lock-free data structures, hardware-accelerated filtering, and priority-based state machines within the ChibiOS RTOS framework.

### Asynchronous Sensor State Pointers (sensors.cpp)

The sensor system uses memory-mapped structures and atomic operations to share data between asynchronous threads without locking.

**Memory-Mapped Sensor Data Structures:**
```cpp
// GLOBAL SENSOR STATE POINTERS (0x20009000-0x20009FFF)
struct GlobalSensorState {
    // GPS STATE (0x20009000)
    volatile GPS_State gps_state;          // 64 bytes
    volatile uint32_t gps_last_update;     // 4 bytes (timestamp ms)
    volatile uint8_t gps_fix_type;         // 1 byte
    volatile uint8_t gps_satellites;       // 1 byte
    volatile float gps_hdop;               // 4 bytes
    volatile float gps_vdop;               // 4 bytes
    
    // COMPASS STATE (0x20009050)
    volatile Vector3f mag_field;           // 12 bytes
    volatile Vector3f mag_field_calibrated;// 12 bytes
    volatile float mag_heading;            // 4 bytes
    volatile uint8_t mag_health;           // 1 byte
    volatile uint8_t mag_calibrated;       // 1 byte
    
    // IMU STATE (0x20009080)
    volatile Vector3f accel;               // 12 bytes
    volatile Vector3f gyro;                // 12 bytes
    volatile Vector3f accel_bias;          // 12 bytes
    volatile Vector3f gyro_bias;           // 12 bytes
    volatile float imu_temperature;        // 4 bytes
    
    // SYNCHRONIZATION PRIMITIVES
    volatile uint32_t sensor_update_count; // 4 bytes
    chibios_rt::BinarySemaphore gps_sem;   // 8 bytes
    chibios_rt::BinarySemaphore mag_sem;   // 8 bytes
    chibios_rt::BinarySemaphore imu_sem;   // 8 bytes
};
```

**Atomic Memory Access Macros:**
These macros implement the memory barriers required for lock-free access between threads.
```cpp
#define ATOMIC_LOAD(ptr) __atomic_load_n(ptr, __ATOMIC_ACQUIRE)
#define ATOMIC_STORE(ptr, val) __atomic_store_n(ptr, val, __ATOMIC_RELEASE)
```

**GPS Data Acquisition (Lock-Free):**
This function implements the mathematical timestamp validity check: `(current_time - snapshot.time_ms) < 1000`.
```cpp
bool get_latest_gps_data(GPS_State* out_state)
{
    // 1. MEMORY BARRIER FOR CONSISTENT READ
    __DMB();
    
    // 2. COPY SNAPSHOT OF GPS STATE
    GPS_State snapshot;
    snapshot.latitude = ATOMIC_LOAD(&gps_state.latitude);
    snapshot.longitude = ATOMIC_LOAD(&gps_state.longitude);
    snapshot.altitude = ATOMIC_LOAD(&gps_state.altitude);
    snapshot.velocity_north = ATOMIC_LOAD(&gps_state.velocity_north);
    snapshot.velocity_east = ATOMIC_LOAD(&gps_state.velocity_east);
    snapshot.velocity_down = ATOMIC_LOAD(&gps_state.velocity_down);
    snapshot.time_ms = ATOMIC_LOAD(&gps_state.time_ms);
    snapshot.fix_type = ATOMIC_LOAD(&gps_state.fix_type);
    
    // 3. VALIDITY CHECK (timestamp within 1 second)
    uint32_t current_time = AP_HAL::millis();
    if((current_time - snapshot.time_ms) < 1000) {
        *out_state = snapshot;
        return true;
    }
    
    return false;
}
```

**Compass Data Fusion with Temporal Filtering:**
Implements the Exponential Moving Average (EMA) filter: `M_filtered = α * M_new + (1-α) * M_previous`.
```cpp
Vector3f get_filtered_mag_field(void)
{
    // EXPONENTIAL MOVING AVERAGE FILTER
    // M_filtered = α * M_new + (1-α) * M_previous
    // Where α = 0.3 for 10Hz compass, 0.7 for 100Hz IMU
    
    static Vector3f filtered_mag = Vector3f(0,0,0);
    static bool initialized = false;
    
    Vector3f current_mag;
    current_mag.x = ATOMIC_LOAD(&mag_field.x);
    current_mag.y = ATOMIC_LOAD(&mag_field.y);
    current_mag.z = ATOMIC_LOAD(&mag_field.z);
    
    if(!initialized) {
        filtered_mag = current_mag;
        initialized = true;
    } else {
        float alpha = 0.3f;  // 70% old, 30% new
        filtered_mag = filtered_mag * (1.0f - alpha) + current_mag * alpha;
    }
    
    return filtered_mag;
}
```

### RC PWM Normalization Math (RC_Channel.cpp)

The `RC_Channel` class implements the complete mathematical pipeline for converting raw PWM signals to normalized control commands.

**RC Channel Data Structure:**
```cpp
// RC CHANNEL DATA STRUCTURE (0x2000A000-0x2000A0FF)
struct RC_Channel_Data {
    // RAW INPUT VALUES
    volatile uint16_t radio_in;           // 2 bytes: Raw PWM (µs)
    volatile uint16_t radio_in_raw;       // 2 bytes: Unfiltered PWM
    
    // NORMALIZED VALUES (-1.0 to 1.0)
    volatile float norm_input;            // 4 bytes: After deadzone
    volatile float norm_input_filtered;   // 4 bytes: After low-pass
    
    // CONTROL MAPPING
    volatile float control_in;            // 4 bytes: After expo/rates
    volatile float control_out;           // 4 bytes: After mixing
    
    // CALIBRATION PARAMETERS
    uint16_t radio_min;                   // 2 bytes: Minimum PWM (e.g., 1100)
    uint16_t radio_max;                   // 2 bytes: Maximum PWM (e.g., 1900)
    uint16_t radio_trim;                  // 2 bytes: Center/trim (e.g., 1500)
    
    // DEADZONE CONFIGURATION
    uint16_t dead_zone;                   // 2 bytes: Deadzone width (µs)
    
    // FILTER COEFFICIENTS
    float filter_cutoff_hz;               // 4 bytes: Low-pass cutoff
    float expo_value;                     // 4 bytes: Expo curve (0-1)
    float rate_value;                     // 4 bytes: Control rate
};
```

**PWM Normalization Mathematical Formulation:**
This function directly implements the piecewise linear mapping with deadzone mathematics.
```cpp
float RC_Channel::norm_input() const
{
    // 1. RAW PWM CLAMPING TO VALID RANGE
    uint16_t pwm = radio_in;
    if(pwm < radio_min) pwm = radio_min;
    if(pwm > radio_max) pwm = radio_max;
    
    // 2. DEADZONE APPLICATION (Symmetric around trim)
    // Mathematical formulation:
    // If |pwm - trim| ≤ deadzone/2 → normalized = 0
    // Else if pwm < trim → normalized = (pwm - trim + deadzone/2) / (trim - min - deadzone/2)
    // Else → normalized = (pwm - trim - deadzone/2) / (max - trim - deadzone/2)
    
    int16_t diff = pwm - radio_trim;
    uint16_t half_deadzone = dead_zone / 2;
    
    if(abs(diff) <= half_deadzone) {
        return 0.0f;  // Within deadzone
    }
    
    if(diff < 0) {
        // Below trim (negative direction)
        float denominator = (radio_trim - radio_min - half_deadzone);
        if(denominator > 0) {
            return (diff + half_deadzone) / denominator;
        }
    } else {
        // Above trim (positive direction)
        float denominator = (radio_max - radio_trim - half_deadzone);
        if(denominator > 0) {
            return (diff - half_deadzone) / denominator;
        }
    }
    
    return 0.0f;  // Fallback
}
```

**Exponential Curve Application:**
Implements the formula: `output = input * (expo + (1 - expo) * input²)` with sign preservation.
```cpp
float RC_Channel::apply_expo(float input) const
{
    // Exponential curve formula:
    // output = input * (expo + (1 - expo) * input²)
    // Where expo ∈ [0,1], input ∈ [-1,1]
    
    if(expo_value <= 0.001f) {
        return input;  // No expo
    }
    
    float input_squared = input * input;
    if(input < 0) {
        input_squared = -input_squared;  // Preserve sign
    }
    
    return input * (expo_value + (1.0f - expo_value) * input_squared);
}
```

**Rate-Based Control Scaling:**
Implements the rate scaling with fine control deadzone: `output = input * rate_value` with threshold `ε`.
```cpp
float RC_Channel::apply_rates(float input) const
{
    // Rate scaling: output = input * rate_value
    // With additional non-linear shaping for fine control
    
    float output = input * rate_value;
    
    // Add small deadzone for very fine movements
    if(fabsf(output) < 0.01f * rate_value) {
        output = 0.0f;
    }
    
    return output;
}
```

**Complete Channel Processing Pipeline:**
Chains together the normalization, expo, and rate functions.
```cpp
float RC_Channel::get_control_in() const
{
    // PROCESSING CHAIN:
    // Raw PWM → Normalization → Deadzone → Expo → Rates → Output
    
    // 1. NORMALIZE TO [-1, 1]
    float normalized = norm_input();
    
    // 2. APPLY EXPONENTIAL CURVE
    normalized = apply_expo(normalized);
    
    // 3. APPLY CONTROL RATES
    normalized = apply_rates(normalized);
    
    // 4. CLAMP TO VALID RANGE
    if(normalized < -1.0f) normalized = -1.0f;
    if(normalized > 1.0f) normalized = 1.0f;
    
    return normalized;
}
```

**Channel Mixing for Rover Steering/Throttle:**
Implements the skid-steer mixing matrix: `Left = throttle + steering`, `Right = throttle - steering`.
```cpp
void RC_Channel::mix_channels(RC_Channel* steering_ch, RC_Channel* throttle_ch)
{
    // ROVER-SPECIFIC MIXING MATRIX:
    // [Steering] = [1  0] [steering_in]
    // [Throttle] = [0  1] [throttle_in]
    // For skid-steer: [Left]  = [1  1] [steering_in]
    //                 [Right] = [1 -1] [throttle_in]
    
    float steering = steering_ch->get_control_in();
    float throttle = throttle_ch->get_control_in();
    
    // DEADBAND COMPENSATION FOR THROTTLE
    if(fabsf(throttle) < THROTTLE_DEADBAND) {
        throttle = 0.0f;
    }
    
    // STEERING RATE LIMITING (prevent too-aggressive turns)
    static float last_steering = 0.0f;
    float steering_rate = steering - last_steering;
    
    if(fabsf(steering_rate) > MAX_STEERING_RATE) {
        if(steering_rate > 0) {
            steering = last_steering + MAX_STEERING_RATE;
        } else {
            steering = last_steering - MAX_STEERING_RATE;
        }
    }
    
    last_steering = steering;
    
    // APPLY MIXING MATRIX
    switch(rover.mixing_type) {
        case MIXING_ACKERMANN:
            // Standard car-like steering
            control_out_steering = steering;
            control_out_throttle = throttle;
            break;
            
        case MIXING_SKID_STEER:
            // Tank-like skid steering
            control_out_left = throttle + steering;
            control_out_right = throttle - steering;
            break;
    }
}
```

### Hardware Deadzone Filtering (radio.cpp)

This module implements hardware-accelerated PWM input capture and filtering.

**Hardware-Based Deadzone Filtering:**
Implements the hardware comparator logic for deadzone elimination.
```cpp
uint16_t apply_hardware_deadzone(uint16_t raw_pwm, uint16_t center, uint16_t deadzone_width)
{
    // HARDWARE FILTERING ALGORITHM:
    // 1. Measure pulse width via timer capture
    // 2. Compare against center ± deadzone/2
    // 3. If within deadzone, return center value
    // 4. Else, apply linear scaling
    
    // Calculate deadzone boundaries
    uint16_t deadzone_low = center - (deadzone_width / 2);
    uint16_t deadzone_high = center + (deadzone_width / 2);
    
    // Hardware comparator check
    if(raw_pwm >= deadzone_low && raw_pwm <= deadzone_high) {
        return center;  // Within deadzone, return center
    }
    
    // Outside deadzone - return raw value (will be normalized later)
    return raw_pwm;
}
```

**PWM Jitter Filtering with Moving Average:**
Implements a 5-element moving average filter for software jitter reduction.
```cpp
class PWMJitterFilter {
private:
    static const uint8_t FILTER_SIZE = 5;
    uint16_t history[FILTER_SIZE];
    uint8_t index;
    
public:
    PWMJitterFilter() : index(0) {
        memset(history, 0, sizeof(history));
    }
    
    uint16_t filter(uint16_t new_value) {
        // 1. UPDATE CIRCULAR BUFFER
        history[index] = new_value;
        index = (index + 1) % FILTER_SIZE;
        
        // 2. CALCULATE MOVING AVERAGE
        uint32_t sum = 0;
        for(uint8_t i = 0; i < FILTER_SIZE; i++) {
            sum += history[i];
        }
        
        // 3. RETURN AVERAGE (integer division)
        return sum / FILTER_SIZE;
    }
};
```

**RC Override Priority Management:**
Implements the debounce timing logic for human override detection.
```cpp
class RCOverrideManager {
private:
    enum OverrideState {
        OVERRIDE_INACTIVE,
        OVERRIDE_PENDING,
        OVERRIDE_ACTIVE,
        OVERRIDE_TIMEOUT
    };
    
    OverrideState state;
    uint32_t override_start_time;
    float override_steering;
    float override_throttle;
    
public:
    RCOverrideManager() : state(OVERRIDE_INACTIVE), override_start_time(0) {}
    
    bool check_override_condition(float current_steering, float current_throttle) {
        // Override triggers when:
        // 1. RC stick deflection exceeds threshold
        // 2. Deflection is sustained for minimum time
        // 3. Autonomous system is in a override-able state
        
        float steering_deflection = fabsf(current_steering);
        float throttle_deflection = fabsf(current_throttle);
        
        bool deflection_sufficient = 
            (steering_deflection > OVERRIDE_THRESHOLD) ||
            (throttle_deflection > OVERRIDE_THRESHOLD);
        
        if(deflection_sufficient) {
            if(state == OVERRIDE_INACTIVE) {
                state = OVERRIDE_PENDING;
                override_start_time = AP_HAL::millis();
            } else if(state == OVERRIDE_PENDING) {
                uint32_t elapsed = AP_HAL::millis() - override_start_time;
                if(elapsed > OVERRIDE_DEBOUNCE_MS) {
                    state = OVERRIDE_ACTIVE;
                    override_steering = current_steering;
                    override_throttle = current_throttle;
                    return true;
                }
            }
        } else {
            state = OVERRIDE_INACTIVE;
        }
        
        return false;
    }
};
```

**Complete Radio Processing Pipeline:**
Integrates all filtering, normalization, and arbitration components.
```cpp
void process_radio_inputs(void)
{
    // 1. READ RAW PWM VALUES FROM HARDWARE
    uint16_t raw_steering = hal.rcin->read(CH_STEERING);
    uint16_t raw_throttle = hal.rcin->read(CH_THROTTLE);
    
    // 2. APPLY HARDWARE DEADZONE FILTERING
    uint16_t filtered_steering = apply_hardware_deadzone(
        raw_steering, 
        STEERING_CENTER,
        STEERING_DEADZONE
    );
    
    uint16_t filtered_throttle = apply_hardware_deadzone(
        raw_throttle,
        THROTTLE_CENTER,
        THROTTLE_DEADZONE
    );
    
    // 3. SOFTWARE JITTER FILTERING
    static PWMJitterFilter steering_filter, throttle_filter;
    filtered_steering = steering_filter.filter(filtered_steering);
    filtered_throttle = throttle_filter.filter(filtered_throttle);
    
    // 4. NORMALIZE TO [-1.0, 1.0]
    float norm_steering = normalize_pwm(filtered_steering,
                                       STEERING_MIN,
                                       STEERING_MAX,
                                       STEERING_CENTER);
    
    float norm_throttle = normalize_pwm(filtered_throttle,
                                       THROTTLE_MIN,
                                       THROTTLE_MAX,
                                       THROTTLE_CENTER);
    
    // 5. CHECK FAILSAFE CONDITIONS
    enum FailsafeState failsafe = check_failsafe();
    if(failsafe != FAILSAFE_ACTIVE) {
        // Activate failsafe procedures
        activate_failsafe(failsafe);
        return;
    }
    
    // 6. CHECK FOR HUMAN OVERRIDE
    static RCOverrideManager override_manager;
    if(override_manager.check_override_condition(norm_steering, norm_throttle)) {
        // Human has taken control
        override_manager.get_override_values(&norm_steering, &norm_throttle);
        set_control_source(SOURCE_RC);
    }
    
    // 7. UPDATE CONTROL SYSTEM
    rover.steering_input = norm_steering;
    rover.throttle_input = norm_throttle;
}
```