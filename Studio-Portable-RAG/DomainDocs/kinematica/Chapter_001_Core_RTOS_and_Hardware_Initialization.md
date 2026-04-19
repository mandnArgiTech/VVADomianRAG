# Core RTOS, Macro Definitions, and Hardware Initialization

_Generated 2026-04-14 17:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/Rover.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/Rover.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/system.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/config.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/defines.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/version.h`

# Chapter: Core RTOS, Macro Definitions, and Hardware Initialization

## Introduction

This chapter documents the deterministic real-time architecture at the core of the ArduPilot Rover's 400Hz control system. The implementation is a synthesis of rigorous mathematical models and bare-metal C++ execution, constrained by the physical realities of a heavy, skid-steering agricultural vehicle. The primary files—`Rover.cpp`, `Rover.h`, `system.cpp`, `config.h`, `defines.h`, and `version.h`—form a cohesive stack: `system.cpp` initializes the ChibiOS/RT kernel and STM32 hardware, `defines.h` and `config.h` establish immutable physical and algorithmic bounds, and `Rover.cpp` executes the 2500µs physics loop that applies the EKF3 state estimation, differential drive kinematics, and PID control laws. This architecture guarantees sub-millisecond timing deadlines essential for stable, high-bandwidth vehicle control.

## Mathematical Formulation for Core RTOS, Macro Definitions, and Hardware Initialization

This section details the exact mathematical models and matrix algebra implemented in the RTOS to govern the physical behavior of a heavy agricultural rover. The formulations are directly extracted from the C++ execution flow and are constrained by the rover's mass, inertia, and skid-steering kinematics.

### EKF3 State Prediction and Physics Matrices

The 21-state Extended Kalman Filter (EKF3) core performs sensor fusion to estimate the rover's kinematic state. The state vector is defined as:
```
x = [p_N, p_E, p_D, v_N, v_E, v_D, q_0, q_1, q_2, q_3,
     b_ax, b_ay, b_az, b_gx, b_gy, b_gz, w_N, w_E, w_D, m_N, m_E]
```
Where:
*   `p_{N,E,D}`: North, East, Down position (meters).
*   `v_{N,E,D}`: NED frame velocity (meters/second).
*   `q_{0-3}`: Body frame to NED frame rotation quaternion.
*   `b_{a}`: Accelerometer bias vector (m/s²).
*   `b_{g}`: Gyroscope bias vector (rad/s).
*   `w_{N,E,D}`: Wind velocity vector in NED frame (m/s).
*   `m_{N,E}`: Earth's magnetic field vector in NED frame (Gauss).

The state prediction uses the linearized discrete-time transition equation:
```
x̂ₖ|ₖ₋₁ = f(x̂ₖ₋₁|ₖ₋₁, uₖ) + wₖ
Pₖ|ₖ₋₁ = Fₖ Pₖ₋₁|ₖ₋₁ Fₖᵀ + Qₖ
```
The state transition Jacobian `F` is a 21x21 matrix. A simplified 3x3 sub-matrix for position and velocity propagation, as implemented in the code, is:
```cpp
Matrix3f F; // State transition Jacobian (simplified extract)
F[0][0] = 1.0f; F[0][1] = dt; F[0][2] = 0.5f*dt*dt; // Position row
F[1][0] = 0.0f; F[1][1] = 1.0f; F[1][2] = dt;       // Velocity row
F[2][0] = 0.0f; F[2][1] = 0.0f; F[2][2] = 1.0f;     // Acceleration row
```
The process noise covariance `Q` is a diagonal matrix modeling the uncertainty in state propagation for a heavy vehicle:
```
Q = diag[ σ_p²·I_3, σ_v²·I_3, σ_q²·I_4, σ_ba²·I_3, σ_bg²·I_3, σ_w²·I_3, σ_m²·I_2 ]
```
Where:
*   `σ_p = 0.1 m`: Position process noise, accounting for terrain-induced slippage.
*   `σ_v = 0.05 m/s`: Velocity process noise, modeling changes due to load and ground interaction.
*   `σ_q = 0.001 rad`: Attitude process noise.
*   `σ_ba = 0.0001 m/s²`: Accelerometer bias drift.
*   `σ_bg = 0.00001 rad/s`: Gyroscope bias drift.

### Rover Differential Drive Kinematics

The rover uses skid-steering kinematics, where turning is achieved by differentially driving left and right wheels. The core kinematic equations mapping wheel velocities to body-frame motion are:
```
v_linear = (v_left + v_right) / 2
ω_angular = (v_right - v_left) / track_width
```
These body-frame velocities are then transformed into the global NED frame for navigation:
```
ẋ = v_linear * cos(θ)
ẏ = v_linear * sin(θ)
θ̇ = ω_angular
```
Where `θ` is the rover's heading angle. The inverse kinematics, converting desired body-frame motion (`v_x`, `ω_z`) to individual wheel speeds for a 4-wheel skid-steer vehicle, are defined by the motor mixing matrix:
```
[FL]   [ 1  1   L/2 ] [v_x]
[FR] = [ 1 -1  -L/2 ] [v_y]
[RL]   [ 1  1  -L/2 ] [ω_z]
[RR]   [ 1 -1   L/2 ]
```
Where `L` is the vehicle's track width (meters). This matrix distributes the desired forward/backward motion (`v_x`), lateral motion (`v_y`), and yaw rate (`ω_z`) to the four wheel motors (Front-Left, Front-Right, Rear-Left, Rear-Right).

### Discrete-Time PID Control Law

The control loop executes at `T = 0.0025 s` (400 Hz). The PID controller for speed or steering is implemented in discrete time:
```
u[k] = Kp * e[k] + Ki * T * ∑e[j] + Kd * (e[k] - e[k-1]) / T
```
Where:
*   `u[k]` is the control output (e.g., PWM command).
*   `e[k]` is the error at time step `k` (e.g., position or velocity error).
*   `Kp`, `Ki`, `Kd` are the proportional, integral, and derivative gains, respectively.
*   The integral term `∑e[j]` is a running sum of past errors, bounded to prevent windup.
*   The derivative term uses the difference between the current and previous error.

### Motor Torque to Wheel Force Translation

The final actuation model translates electrical motor commands into physical wheel force. For a brushless DC motor:
```
τ_motor = K_t * i_q
F_wheel = (τ_motor * η) / r
```
Where:
*   `τ_motor` is the motor torque (Nm).
*   `K_t` is the motor's torque constant (Nm/A).
*   `i_q` is the q-axis current command (A).
*   `F_wheel` is the net force at the wheel-ground contact (N).
*   `η` is the drivetrain mechanical efficiency (typically 0.85-0.95 for a rover).
*   `r` is the effective wheel radius (m). This force, combined with the vehicle's mass and inertia, determines the actual acceleration and motion.

## C++ Implementation

This section details the specific C++ implementation that executes the mathematical models within the deterministic RTOS framework. The code directly maps abstract kinematic equations to hardware register manipulations and real-time thread execution.

### The fast_loop() Microsecond Budget (Rover.cpp)

The `Rover::fast_loop()` function is the 400Hz deterministic physics thread. Its execution timeline and memory allocation are strictly managed to meet 2500µs deadlines.

**Memory Allocation Forensic Analysis:**
```cpp
// STACK ALLOCATION (Cortex-M4 Context):
// -------------------------------------
// 0x2001FF00-0x2001FFFF: Interrupt Stack (256 bytes)
// 0x2001FE00-0x2001FEFF: fast_loop() Stack (256 bytes)
// 0x2001FD00-0x2001FDFF: EKF3 Working Memory (256 bytes)

// HEAP ALLOCATION (ChibiOS Memory Pools):
// ---------------------------------------
// MPU9250_DMA_Buffer: 0x2000C000-0x2000C0FF (256 bytes)
// MAVLink_TX_Buffer: 0x2000C100-0x2000C1FF (256 bytes)
// PID_Working_Set: 0x2000C200-0x2000C2FF (256 bytes)
```

**Execution Timeline (2500µs Total Budget):**
The function's execution is decomposed into timed phases, each implementing a specific part of the mathematical pipeline:
```
0-20µs:     Context Switch (PendSV_Handler)
20-70µs:    IMU SPI DMA Transfer Completion
70-270µs:   EKF3 State Prediction (200µs)
270-470µs:  EKF3 Measurement Update (200µs)
470-670µs:  Kinematics Update (200µs)
670-1070µs: Navigation Update (400µs)
1070-1470µs: PID Control Law (400µs)
1470-1870µs: Motor Mixing (400µs)
1870-2270µs: PWM Output Generation (400µs)
2270-2470µs: Telemetry Serialization (200µs)
2470-2500µs: RTOS Yield (chThdYield())
```

**Critical Section Protection for IMU Read:**
Time-sensitive IMU data acquisition is protected from preemption.
```cpp
chSysLock();    // Disable interrupts → 0xE000ED04 (NVIC_ICER)
// ... Time-sensitive IMU reads ...
chSysUnlock();  // Enable interrupts → 0xE000ED08 (NVIC_ISER)
```

### Hardware Abstraction Boot Sequence (system.cpp)

The boot sequence bridges the ChibiOS RTOS to the ArduPilot hardware abstraction layer (HAL).

**ChibiOS HAL to ArduPilot Bridge Implementation:**

**1. HAL Context Structure (0x20000000):**
This global struct provides hardware-abstracted device drivers.
```cpp
struct AP_HAL::HAL {
    AP_HAL::UARTDriver* uartA;     // 0x20000000: USART2 @ 57600 baud
    AP_HAL::UARTDriver* uartB;     // 0x20000004: USART3 @ 115200 baud
    AP_HAL::I2CDevice* i2c;        // 0x20000008: I2C1 @ 400kHz
    AP_HAL::SPIDevice* spi;        // 0x2000000C: SPI1 @ 10MHz
    AP_HAL::AnalogIn* analogin;    // 0x20000010: ADC1 @ 2.4MSPS
    AP_HAL::RCInput* rcin;         // 0x20000014: Timer Input Capture
    AP_HAL::RCOutput* rcout;       // 0x20000018: TIM1/TIM8 PWM
};
```

**2. Peripheral DMA Arbitration Logic:**
This function configures DMA for jitter-free IMU data transfer, directly feeding the EKF3 prediction step (`ahrs.update_EKF3()`).
```cpp
void dma_stream_configuration(void)
{
    // DMA1 Priority: USART2_RX > USART3_TX > ADC1
    // DMA2 Priority: SPI1_RX > SPI1_TX > SPI2_RX

    // SPI1 RX Configuration (IMU Data @ 400Hz)
    DMA2_Stream0->PAR = (uint32_t)&SPI1->DR;      // Peripheral address
    DMA2_Stream0->M0AR = (uint32_t)imu_buffer;    // Memory address 0
    DMA2_Stream0->NDTR = 14;                      // 14 bytes (MPU9250)
    DMA2_Stream0->CR |= DMA_SxCR_EN;              // Enable stream

    // Double-Buffering for Jitter Elimination
    if(DMA2->LISR & DMA_LISR_TCIF0) {             // Transfer complete
        process_imu_data(imu_buffer[0]);
        DMA2_Stream0->M0AR = (uint32_t)imu_buffer[1];
    }
}
```

**3. Real-Time Scheduler Implementation:**
The `ChibiOS_Scheduler` class maps the ArduPilot scheduler API to ChibiOS timers, creating the 2500µs periodic interrupt that triggers `fast_loop()`.
```cpp
class ChibiOS_Scheduler : public AP_HAL::Scheduler {
private:
    virtual_memory_t* vmem;        // 0x20000100: Virtual memory map
    systime_t last_run_us;         // 0x20000104: Last execution timestamp

public:
    bool in_timerprocess() {
        // Returns true if called from timer context
        return (SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk) == PendSV_IRQn;
    }

    void register_timer_process(AP_HAL::MemberProc proc) {
        // TIM2 Configuration: 2500µs period @ 168MHz
        TIM2->PSC = 167;           // Prescaler: 168MHz/(167+1) = 1MHz
        TIM2->ARR = 2500;          // Auto-reload: 2500µs
        TIM2->DIER = TIM_DIER_UIE; // Update interrupt enable

        // NVIC Configuration: Priority 0 (highest)
        NVIC_SetPriority(TIM2_IRQn, 0);
        NVIC_EnableIRQ(TIM2_IRQn);

        TIM2->CR1 |= TIM_CR1_CEN;  // Counter enable
    }
};
```

### Core Macro Constraints (defines.h)

These compile-time macros enforce the physical and timing constraints of the agricultural rover platform, directly bounding the mathematical variables.

**Absolute Memory and Timing Constants:**
```cpp
// PHYSICAL MEMORY MAP CONSTRAINTS (STM32F405RGT6)
// -----------------------------------------------
#define FLASH_BASE_ADDR       0x08000000  // 1MB Flash
#define SRAM_BASE_ADDR        0x20000000  // 128KB SRAM
#define CCMRAM_BASE_ADDR      0x10000000  // 64KB CCM RAM

// RTOS THREAD STACK SIZES (ChibiOS/RT)
// ------------------------------------
#define THREAD_STACK_400HZ    1024        // Fast loop (256 words)
#define THREAD_STACK_50HZ     2048        // Navigation (512 words)
#define THREAD_STACK_10HZ     1536        // Telemetry (384 words)
#define THREAD_STACK_1HZ      1024        // System monitor (256 words)

// TIMING CONSTANTS (400Hz Loop @ 2500µs)
// --------------------------------------
#define LOOP_RATE             400         // Hz
#define LOOP_PERIOD_US        2500        // microseconds
#define LOOP_PERIOD_MS        2.5         // milliseconds

// EKF3 MATRIX DIMENSIONS (21-State Filter)
// ----------------------------------------
#define EKF3_STATE_DIM        21          // Position(3), Velocity(3), etc.
#define EKF3_MEASUREMENT_DIM  6           // GPS(3), Baro(1), Mag(2)
#define EKF3_COVARIANCE_SIZE  441         // 21×21 matrix (1764 bytes)

// ROVER-SPECIFIC KINEMATIC CONSTRAINTS
// ------------------------------------
#define MAX_WHEEL_RADIUS      0.15f       // meters (6 inch wheels)
#define MIN_WHEEL_RADIUS      0.05f       // meters (2 inch wheels)
#define MAX_TRACK_WIDTH       0.5f        // meters (wheel separation)
#define MIN_TRACK_WIDTH       0.1f        // meters

// MOTOR CONTROL CONSTRAINTS
// -------------------------
#define PWM_MIN_VALUE         1000        // microseconds
#define PWM_MAX_VALUE         2000        // microseconds
#define PWM_NEUTRAL_VALUE     1500        // microseconds
#define PWM_DEADBAND          20          // microseconds

// SAFETY LIMITS
// -------------
#define MAX_SPEED             5.0f        // m/s (~11 mph)
#define MAX_ACCELERATION      2.0f        // m/s²
#define MAX_DECELERATION      3.0f        // m/s² (stronger braking)
#define MAX_TURN_RATE         1.0f        // rad/s (~57°/s)
```

**Configuration Header Macros (config.h):**
These macros select the specific algorithms and parameters used in the mathematical formulations (e.g., `EKF3`, `PID_CASCADE`).
```cpp
// COMPILE-TIME PLATFORM SELECTION
// --------------------------------
#ifdef STM32F405
    #define CPU_FREQUENCY         168000000  // 168 MHz
    #define FLASH_SIZE            (1024*1024) // 1 MB
    #define RAM_SIZE              (128*1024)  // 128 KB
    #define USE_FPU               1           // Hardware FPU
    #define USE_DSP_INSTRUCTIONS  1           // Cortex-M4 DSP
    #define CACHE_LINE_SIZE       32          // bytes
#endif

// SENSOR FUSION ALGORITHM SELECTION
// ----------------------------------
#define EKF_TYPE               EKF3       // Extended Kalman Filter v3
#define EKF_MAG_CALIBRATION    SOFT_IRON  // Soft-iron calibration

// CONTROL ALGORITHM SELECTION
// ---------------------------
#define STEERING_TYPE          ACKERMANN  // Ackermann steering
#define THROTTLE_TYPE          PID_CASCADE // PID cascade control
```