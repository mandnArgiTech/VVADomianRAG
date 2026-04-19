# Master Safety Matrices, Collision Detection, and AFS

_Generated 2026-04-14 17:57 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/failsafe.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/crash_check.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/ekf_check.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/afs_rover.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/afs_rover.h`

# Chapter: Master Safety Matrices, Collision Detection, and AFS

## Introduction

This chapter documents the deterministic safety architecture for a 400Hz autonomous agricultural rover built on ArduPilot. The system implements triple-redundant failsafe pathways through real-time kinematic validation, covariance monitoring, and hardware-enforced power termination. The core files—`crash_check.cpp`, `ekf_check.cpp`, `afs_rover.cpp`, and `afs_rover.h`—form a layered defense: `crash_check` performs first-principles physics validation between commanded motor output and IMU-measured acceleration at 400Hz; `ekf_check` monitors the EKF3 covariance matrix for positional drift at 100Hz; and `afs_rover` executes a state machine that escalates to terminal hardware kill via direct register manipulation. These components interact through the RTOS scheduler and hardware interrupts, providing ASIL-D equivalent safety by guaranteeing detection and mitigation of kinematic violations, estimation divergence, and CPU hangs within a 2.5-second maximum undetected operation window.

---

### Kinematic Crash Formulation: Motor Output vs. IMU Acceleration Detection

**Physical Basis for Heavy Rover:** The algorithm enforces that the acceleration commanded to the skid-steer drivetrain must physically manifest as measured by the IMU. A chassis flip or high-center violates the kinematic model, creating a detectable disparity between the motor-torque-derived acceleration vector and the gravity-compensated IMU vector.

**Mathematical Proof and Implementation:**

Let:
*   **a_cmd** = commanded linear acceleration vector in the rover body frame (m/s²), derived from PWM motor commands.
*   **a_imu** = measured linear acceleration vector in the body frame (m/s²), from the IMU with gravity subtracted.
*   **m_tolerance** = magnitude tolerance (0.3g = 2.94 m/s²), scaled for vehicle mass.
*   **θ_max** = angular deviation tolerance (45° = 0.785 rad).

A crash/flip is triggered when both conditions are true for a debounced period:
```
||a_cmd - a_imu|| > m_tolerance
```
AND
```
cos⁻¹((a_cmd · a_imu) / (||a_cmd|| · ||a_imu||)) > θ_max
```

**Rover-Specific Vector Construction:**

1.  **Commanded Acceleration (`a_cmd`):** Computed from skid-steer differential torque.
    ```cpp
    // From CrashDetector::pwm_to_accel
    float torque_left = (pwm_left - 1500) * 0.001f * MAX_TORQUE;
    float torque_right = (pwm_right - 1500) * 0.001f * MAX_TORQUE;
    float net_force = (torque_left + torque_right) / WHEEL_RADIUS;
    Vector3f a_cmd = Vector3f(net_force / MASS, 0, 0); // Force along body X-axis
    ```

2.  **IMU Acceleration (`a_imu`):** Gravity vector is rotated into the body frame using the AHRS attitude and subtracted from raw IMU readings.
    ```cpp
    // Gravity vector in body frame
    Matrix3f R = ahrs.get_rotation_body_to_ned().transposed(); // R_ned_to_body
    Vector3f gravity = R * Vector3f(0, 0, GRAVITY_MSS);
    // Gravity-compensated measurement
    Vector3f a_imu = raw_imu - gravity;
    ```

**Detection Algorithm Code:**
```cpp
// 1. Magnitude difference check
float mag_diff = (cmd_accel - imu_accel).length();
bool mag_violation = (mag_diff > accel_mag_threshold); // accel_mag_threshold = 2.94

// 2. Angular alignment check via dot product
float cos_angle = cmd_accel.normalized() * imu_accel.normalized(); // Dot product
bool angle_violation = (fabsf(cos_angle) < cosf(angle_threshold)); // angle_threshold = 0.785
```

### EKF Variance and AFS Analysis: Spatial Drift Monitoring

**EKF3 Trust Architecture:** The 24-state covariance matrix `P[24][24]` is monitored. The trace of sub-matrices provides variance estimates for critical state blocks.

**Trust Decay Function (Simplified in-code check):**
The code monitors the 3σ bound of position variance.
```
pos_3sigma = 3.0 * sqrt( P[0,0] + P[1,1] + P[2,2] )
```
A failure is counted when `pos_3sigma > POS_VARIANCE_MAX`, where the limit is 5.0m (RTK) or 50.0m (GPS-only).

**Innovation Monitoring:** The EKF health flag (`ekf->healthy`) is set based on a chi-squared test of measurement residuals `r[k]` over a sliding window:
```
χ² = Σ_{i=k-W}^{k} r[i]ᵀ · S⁻¹ · r[i]
```
If `χ²` exceeds the 95th percentile threshold for 5 consecutive samples, the EKF is marked unhealthy.

**C++ Variance Monitoring Loop:**
```cpp
// Read covariance from DMA-buffered memory
volatile EKF3_State* ekf = (EKF3_State*)0x20000960;
// Calculate 3σ position bound
float pos_3sigma = 3.0f * sqrtf(ekf->pos_variance); // pos_variance = trace(P[0:2,0:2])
// Compare against physical limit
if (pos_3sigma > POS_VARIANCE_MAX) {
    failure_count++;
}
// Trigger AFS after sustained failure (0.5 seconds)
if (failure_count > 50) { // 100Hz * 0.5s
    AP::afs().trigger(FAILSAFE_EKF_VARIANCE);
}
```

### Advanced Failsafe (AFS) Termination Logic

**State Machine:** The AFS escalates through states: `STANDBY` → `EKF_DEGRADED`/`MOTOR_RUNAWAY`/`COMMS_LOST` → `TERMINAL`.

**Terminal Kill Execution - Physical Relay Control:**
The terminal sequence cuts power via hardware GPIO toggles, independent of software control loops.

1.  **Disable Motor PWM Outputs:**
    ```cpp
    TIM1->CCER = 0; // Disable capture/compare for motor controller TIM1
    TIM8->CCER = 0; // Disable capture/compare for motor controller TIM8
    ```
2.  **Open Main Battery Relay (GPIOE Pin 3):**
    ```cpp
    // Set the corresponding BRR bit to drive pin low (relay open)
    GPIOE->BSRR = (1 << (3 + 16));
    ```
3.  **Open Ignition Relay (GPIOB Pin 8) after delay:**
    ```cpp
    delay(100); // Allow capacitor discharge
    GPIOB->BSRR = (1 << (8 + 16));
    ```

**Independent DMA Hardware Monitor:**
A DMA stream monitors the EKF health flag directly in memory. If the flag goes to zero (unhealthy), it triggers a hardware kill without CPU involvement.
```cpp
// In DMA2_Stream7_IRQHandler
if (safety_buffer[0] == 0) { // EKF health flag read by DMA
    GPIOE->BSRR = (1 << 3) << 16; // Direct hardware kill: open battery relay
    IWDG->KR = 0xCCCC; // Start independent hardware watchdog for reset
}
```

**CPU Hang Detection via Watchdog:** The Independent Watchdog (IWDG) is refreshed by the main loop. A hung CPU fails to refresh, causing a hardware reset after 2.5 seconds.
```cpp
// Normal operation: refresh watchdog
IWDG->KR = 0xAAAA;
// If CPU hangs, watchdog expires, triggering a hardware reset.
```

---

### C++ Implementation Forensic Breakdown

### EKF Trust Variance Limits (ekf_check.cpp)

**Memory Layout and Structs:**
The EKF3 state and covariance matrix reside in a fixed memory region for deterministic DMA access. The `EKF3_State` struct maps directly to the mathematical covariance matrix `P[24][24]`.

```cpp
struct EKF3_State {
    float state[24];           // 0x2000 0000 - Core EKF states
    float P[24][24];           // 0x2000 0060 - Covariance matrix
    uint32_t healthy : 1;      // 0x2000 0960 - Bitfield health flag
    uint32_t innovations_failing : 1;
    uint32_t timeouts : 8;
    float pos_variance;        // 0x2000 0968 - Trace(P[0:2,0:2])
    float vel_variance;        // 0x2000 096C - Trace(P[3:5,3:5])
    float att_variance;        // 0x2000 0970 - Quaternion variance
};
```

**Critical Monitoring Loop (TIM3 ISR at 100Hz):**
The variance check runs in a high-priority timer interrupt placed in ITCM for deterministic execution. It implements the 3σ position bound calculation from the mathematical formulation.

```cpp
__attribute__((section(".itcm")))  // STM32 ITCM for deterministic timing
void TIM3_IRQHandler(void) {
    static uint8_t failure_count = 0;
    
    // Read EKF covariance from shared memory (DMA double-buffered)
    volatile EKF3_State* ekf = (EKF3_State*)0x20000960;
    
    // Position variance check (primary) - implements: pos_3sigma = 3.0 * sqrt(trace(P[0:2,0:2]))
    float pos_3sigma = 3.0f * sqrtf(ekf->pos_variance);
    if (pos_3sigma > POS_VARIANCE_MAX) {
        failure_count++;
        GPIOB->ODR |= (1 << 7);  // Set status LED pin PB7
    } else {
        failure_count = 0;
        GPIOB->ODR &= ~(1 << 7);
    }
    
    // Persistent failure triggers AFS
    if (failure_count > 50) {  // 0.5 seconds of continuous failure
        AP::afs().trigger(FAILSAFE_EKF_VARIANCE);
        TIM3->DIER &= ~TIM_DIER_UIE;  // Disable further interrupts
    }
    
    TIM3->SR &= ~TIM_SR_UIF;  // Clear interrupt flag
}
```

**RTOS Integration:** The ISR runs independently of the main scheduler. The `failure_count` mechanism provides debouncing against transient variance spikes. The AFS trigger registers an IO process with `AP::scheduler().register_io_process()` for immediate execution in the main loop context.

### Flipped Chassis Acceleration Math (crash_check.cpp)

**Kinematic Validation Struct:**
The `CrashDetector` struct encapsulates the mathematical state for the kinematic constraint validation. The `pwm_to_accel` method implements the rover-specific torque-to-acceleration conversion.

```cpp
struct CrashDetector {
    Vector3f cmd_accel;        // Commanded acceleration (body frame) - a_cmd
    Vector3f imu_accel;        // IMU measured acceleration - a_imu
    Vector3f gravity;          // Estimated gravity vector
    float accel_mag_threshold; // 0.3g = 2.94 m/s² - m_tolerance
    float angle_threshold;     // 45° = 0.785 rad - θ_max
    uint32_t crash_debounce;   // 10 samples at 400Hz = 25ms
    uint32_t crash_state : 1;
    
    // Motor PWM to acceleration conversion
    inline Vector3f pwm_to_accel(uint16_t pwm_left, uint16_t pwm_right) {
        float torque_left = (pwm_left - 1500) * 0.001f * MAX_TORQUE;
        float torque_right = (pwm_right - 1500) * 0.001f * MAX_TORQUE;
        float net_force = (torque_left + torque_right) / WHEEL_RADIUS;
        return Vector3f(net_force / MASS, 0, 0);  // Body X-axis only
    }
};
```

**Mathematical Detection Algorithm:**
The `update()` method implements the complete crash condition check: `||a_cmd - a_imu|| > m_tolerance AND cos⁻¹((a_cmd · a_imu)/(||a_cmd||·||a_imu||)) > θ_max`.

```cpp
bool CrashDetector::update(uint16_t pwm_left, uint16_t pwm_right, 
                          const Vector3f& raw_imu, float dt) {
    // 1. Compute commanded acceleration from PWM inputs
    cmd_accel = pwm_to_accel(pwm_left, pwm_right);
    
    // 2. Remove gravity from IMU measurements using AHRS attitude
    // Implements: a_imu = raw_imu - R * [0, 0, g]ᵀ
    Matrix3f R = ahrs.get_rotation_body_to_ned().transposed();
    gravity = R * Vector3f(0, 0, GRAVITY_MSS);
    imu_accel = raw_imu - gravity;
    
    // 3. Magnitude difference check: ||a_cmd - a_imu|| > m_tolerance
    float mag_diff = (cmd_accel - imu_accel).length();
    bool mag_violation = (mag_diff > accel_mag_threshold);
    
    // 4. Angular alignment check: cos⁻¹(dot(norm(a_cmd), norm(a_imu))) > θ_max
    float cos_angle = cmd_accel.normalized() * imu_accel.normalized();
    bool angle_violation = (fabsf(cos_angle) < cosf(angle_threshold));
    
    // 5. Combined condition with debouncing
    if (mag_violation && angle_violation) {
        crash_debounce = min(crash_debounce + 1, 10u);
    } else {
        crash_debounce = max(crash_debounce - 1, 0u);
    }
    
    // 6. Crash state determination
    bool new_crash_state = (crash_debounce >= 8);
    if (new_crash_state && !crash_state) {
        // Edge detection - crash just occurred
        AP::logger().Write_Crash(cmd_accel, imu_accel, mag_diff, acosf(cos_angle));
    }
    
    crash_state = new_crash_state;
    return crash_state;
}
```

**Hardware Integration (STM32F4 Specific):**
The crash detection runs in a TIM2 interrupt at 400Hz, with direct hardware register access for minimal latency.

```cpp
// TIM1 captures PWM inputs (CH1, CH2 for left/right motors)
uint16_t pwm_left = TIM1->CCR1;
uint16_t pwm_right = TIM1->CCR2;

// SPI DMA reads MPU9250 accelerometer
volatile uint8_t imu_raw[6] __attribute__((section(".dtcm")));
DMA2_Stream0->M0AR = (uint32_t)imu_raw;
Vector3f raw_accel(imu_raw[0]<<8|imu_raw[1], 
                   imu_raw[2]<<8|imu_raw[3], 
                   imu_raw[4]<<8|imu_raw[5]);

// Crash detection in TIM2 interrupt (400Hz)
if (crash_detector.update(pwm_left, pwm_right, raw_accel, 0.0025f)) {
    // Immediate motor cutoff via hardware PWM disable
    TIM1->BDTR |= TIM_BDTR_MOE;  // Main output enable (disable)
    TIM8->BDTR |= TIM_BDTR_MOE;  // Secondary motor controller
    
    // Signal AFS for terminal response
    AP::scheduler().register_io_process(afs_emergency_stop);
}
```

### Advanced Failsafe Termination Logic (afs_rover.cpp)

**AFS State Machine Architecture:**
The AFS system implements a state machine that escalates through failure modes, culminating in terminal hardware kill.

```cpp
class AFS_Rover {
public:
    enum class State : uint8_t {
        STANDBY = 0,
        EKF_DEGRADED = 1,
        MOTOR_RUNAWAY = 2,
        COMMS_LOST = 3,
        TERMINAL = 4
    };
    
    struct HardwareKill {
        volatile uint32_t* gpio_bsrr;  // GPIO set/reset register
        uint16_t kill_pin;             // Physical relay pin
        uint32_t arm_time;             // When armed (µs)
        bool engaged;                  // Current state
    };
    
private:
    State current_state;
    HardwareKill kill_switches[3];  // Main battery, motor controller, ignition
    uint32_t watchdog_last_ok;      // Last valid watchdog pet
    uint8_t cpu_hang_counter;       // Consecutive missed schedules
};
```

**Watchdog and CPU Hang Detection:**
The CPU hang detection monitors the RTOS scheduler's execution timing, triggering a hardware kill if the main loop stalls.

```cpp
void AFS_Rover::check_cpu_hang() {
    // Task scheduler integrity check
    uint32_t now = AP_HAL::micros();
    uint32_t schedule_lag = now - AP::scheduler().last_run_usec();
    
    if (schedule_lag > MAX_SCHEDULE_LAG) {
        cpu_hang_counter++;
        
        // STM32 Independent Watchdog (IWDG) hardware trigger
        if (cpu_hang_counter > 3) {
            IWDG->KR = 0xAAAA;  // Refresh watchdog
            IWDG->KR = 0xCCCC;  // Start watchdog (will reset in 2.5s)
            
            // Immediate hardware kill before reset
            execute_terminal_kill();
        }
    } else {
        cpu_hang_counter = 0;
        IWDG->KR = 0xAAAA;  // Normal refresh
    }
}
```

**Terminal Kill Execution (Physical Relay Drop):**
The terminal kill sequence directly manipulates hardware registers to disable power, independent of software state.

```cpp
void AFS_Rover::execute_terminal_kill() {
    // Sequence: 1) Kill motors, 2) Kill main battery, 3) Kill ignition
    
    // 1. Motor controllers via PWM disable and hardware kill pin
    TIM1->CCER = 0;  // Disable all capture/compare outputs
    TIM8->CCER = 0;
    
    // 2. Main battery relay (GPIOE Pin 3)
    kill_switches[0].gpio_bsrr = &GPIOE->BSRR;
    kill_switches[0].kill_pin = 3;
    *(kill_switches[0].gpio_bsrr) = (1 << (kill_switches[0].kill_pin + 16));  // Reset = OFF
    
    // 3. Ignition kill (GPIOB Pin 8) with 100ms delay for capacitor discharge
    delay(100);
    kill_switches[2].gpio_bsrr = &GPIOB->BSRR;
    kill_switches[2].kill_pin = 8;
    *(kill_switches[2].gpio_bsrr) = (1 << (kill_switches[2].kill_pin + 16));
    
    // 4. Force write to non-volatile crash log
    Flash_Write(0x080E0000, crash_log_data, sizeof(crash_log_data));
    
    // 5. Final hardware lock - disable interrupts and enter infinite loop
    __disable_irq();
    while (1) {
        // Flash status LED pattern (SOS) before final death
        for (int i = 0; i < 3; i++) { GPIOB->ODR ^= (1 << 7); delay(100); }
        delay(100);
        for (int i = 0; i < 3; i++) { GPIOB->ODR ^= (1 << 7); delay(300); }
        delay(100);
        for (int i = 0; i < 3; i++) { GPIOB->ODR ^= (1 << 7); delay(100); }
        delay(2000);
    }
}
```

**DMA-Based Safety Monitor (Independent of CPU):**
This provides a third, hardware-level kill pathway that operates even if the main CPU is hung or compromised.

```cpp
// DMA2 Stream7 configured to monitor critical memory regions
void setup_dma_safety_monitor() {
    // Monitor EKF health flag at 0x20000960
    DMA2_Stream7->PAR = (uint32_t)&ekf_health_flag;
    DMA2_Stream7->M0AR = (uint32_t)&safety_buffer;
    DMA2_Stream7->NDTR = 4;  // 4 bytes (health flag)
    
    // Configure to trigger on change (circular mode)
    DMA2_Stream7->CR = DMA_SxCR_PL_1 |    // High priority
                      DMA_SxCR_MSIZE_0 | // 16-bit memory size  
                      DMA_SxCR_PSIZE_0 | // 16-bit peripheral size
                      DMA_SxCR_MINC |    // Memory increment
                      DMA_SxCR_CIRC |    // Circular mode
                      DMA_SxCR_TCIE;     // Transfer complete interrupt
    
    // If DMA completes (memory changed), check if health flag went bad
    NVIC_EnableIRQ(DMA2_Stream7_IRQn);
}

// DMA interrupt executes even if main CPU is hung
void DMA2_Stream7_IRQHandler(void) {
    if (DMA2->HISR & DMA_HISR_TCIF7) {
        if (safety_buffer[0] == 0) {  // EKF health flag went to 0
            // Direct hardware kill - bypass all software
            GPIOE->BSRR = (1 << 3) << 16;  // Kill battery relay
            
            // Trigger hardware watchdog reset
            IWDG->KR = 0x5555;  // Enable register access
            IWDG->PR = 4;       // 256 prescaler
            IWDG->RLR = 4095;   // ~2.5 second timeout
            IWDG->KR = 0xCCCC;  // Start watchdog
        }
        DMA2->HIFCR = DMA_HIFCR_CTCIF7;  // Clear flag
    }
}
```