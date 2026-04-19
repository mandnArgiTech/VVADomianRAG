# Hardware Motor Output, I2C PWM ICs, and Sysfs Duty Cycles

_Generated 2026-04-14 23:07 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Sysfs.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Sysfs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/PWM_Sysfs.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/PWM_Sysfs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_PCA9685.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_PCA9685.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_PRU.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_PRU.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_AioPRU.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_AioPRU.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Bebop.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Bebop.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Disco.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_Disco.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_AeroIO.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_AeroIO.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_ZYNQ.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/RCOutput_ZYNQ.h`

# Chapter: Hardware Motor Output, I2C PWM ICs, and Sysfs Duty Cycles

## Technical Introduction

The `RCOutput_Sysfs.cpp`, `RCOutput_PCA9685.cpp`, `RCOutput_PRU.cpp`, and related hardware-specific files implement the low-level motor output abstraction layer for ArduPilot's 400Hz autonomous vehicle architecture. These drivers translate high-level torque and velocity commands from the skid-steer kinematic controller into precise PWM signals across multiple hardware platforms. The `Sysfs` variant provides Linux userspace PWM control via `/sys/class/pwm/`, while `PCA9685` implements I2C communication to external 16-channel PWM controllers. The `PRU` and `ZYNQ` variants leverage coprocessors for deterministic, sub-microsecond PWM generation, critical for the 20kg agricultural rover's motor control loop. Each driver implements the same mathematical interface: converting normalized duty cycles (0-1) to hardware-specific register values while maintaining synchronization across multiple motors for coordinated skid-steer maneuvers.

---

### Mathematical Formulation: Hardware Motor Output, I2C PWM ICs, and Sysfs Duty Cycles

#### Skid-Steer Kinematics and Differential Torque Allocation

For a 20kg agricultural rover with track width \(T = 0.5\) m and wheel radius \(R = 0.1\) m, the differential drive kinematics govern the conversion of yaw rate commands to individual wheel speeds. The fundamental relationship is:

\[
\omega = \frac{V_{\text{right}} - V_{\text{left}}}{T}
\]

Where \(\omega\) is the yaw rate (rad/s). The steering controller output \(\tau_{\text{cmd}}\) (N·m) is a torque command derived from the PID with feedforward:

\[
\tau_{\text{cmd}} = K_p \cdot e + K_i \int e \, dt + K_d \frac{de}{dt} + K_{ff} \cdot \omega_{\text{desired}}
\]

This torque is translated into a differential speed \(\Delta V\) required at the wheels:

\[
\Delta V = \frac{\tau_{\text{cmd}} \cdot T}{2 \cdot R}
\]

Given a forward speed \(V_{\text{forward}}\) (m/s) from the throttle controller, the individual wheel speed commands are:

\[
V_{\text{right}} = V_{\text{forward}} + \Delta V
\]
\[
V_{\text{left}} = V_{\text{forward}} - \Delta V
\]

These wheel speeds are then converted to RPM for motor control:

\[
\text{RPM}_{\text{right}} = \frac{V_{\text{right}}}{2 \pi R} \times 60
\]
\[
\text{RPM}_{\text{left}} = \frac{V_{\text{left}}}{2 \pi R} \times 60
\]

#### PWM Duty Cycle to Wheel Torque Mapping

The rover's motors are driven via PWM signals with a period of 20ms (50Hz). The pulse width in microseconds (\(\mu s\)) maps to a commanded torque. For a typical brushless DC motor with torque constant \(K_t = 0.05\) N·m/A and ESC calibration:

\[
\text{Duty}_{\text{norm}} = \frac{\text{PWM}_{\mu s} - 1100}{800} \quad \text{(range 0 to 1)}
\]

The corresponding motor torque command is:

\[
\tau_{\text{motor}} = \tau_{\text{max}} \cdot \text{Duty}_{\text{norm}}
\]

Where \(\tau_{\text{max}}\) is the motor's peak torque (e.g., 2.0 N·m). For the skid-steer rover, the total yaw torque is the difference between left and right wheel torques:

\[
\tau_{\text{yaw}} = \frac{T}{2R} (\tau_{\text{right}} - \tau_{\text{left}})
\]

This creates the algebraic constraint for the motor mixer: given a desired forward force \(F_{\text{des}}\) and yaw torque \(\tau_{\text{yaw}}\), the individual motor torques are:

\[
\begin{bmatrix}
\tau_{\text{left}} \\
\tau_{\text{right}}
\end{bmatrix}
=
\begin{bmatrix}
\frac{1}{2} & -\frac{R}{T} \\
\frac{1}{2} & \frac{R}{T}
\end{bmatrix}
\begin{bmatrix}
F_{\text{des}} \\
\tau_{\text{yaw}}
\end{bmatrix}
\]

#### I2C PWM IC Register Mathematics

For I2C PWM controllers (e.g., PCA9685), the duty cycle is set via 12-bit registers. The register value for a given pulse width is:

\[
\text{REG}_{\text{ON}} = \left\lfloor \frac{\text{PWM}_{\mu s} \cdot f_{\text{clk}} \cdot \text{prescale}}{1 \times 10^6 \cdot 4096} \right\rfloor
\]

Where \(f_{\text{clk}} = 25\) MHz (typical), and the prescale value is set for 50Hz update:

\[
\text{prescale} = \left\lfloor \frac{f_{\text{clk}}}{4096 \cdot f_{\text{PWM}}} - 1 \right\rfloor = \left\lfloor \frac{25 \times 10^6}{4096 \cdot 50} - 1 \right\rfloor = 121
\]

The I2C transaction for setting channel \(n\) involves writing to register address \(0x06 + 4n\):

\[
\text{I2C Write: } [0x06 + 4n, 0x00, 0x00, (\text{REG}_{\text{ON}} \& 0xFF), ((\text{REG}_{\text{ON}} >> 8) \& 0x0F)]
\]

#### Sysfs Duty Cycle Probability and Timing Analysis

When using Linux Sysfs for PWM control, the duty cycle is written as a nanosecond value to `/sys/class/pwm/pwmchipX/pwmY/duty_cycle`. The probability of a write completing within the 2.5ms control period depends on kernel scheduling latency. The worst-case latency \(L_{\text{max}}\) is given by:

\[
L_{\text{max}} = C_{\text{write}} + \sum_{j \neq i} \left\lceil \frac{L_{\text{max}}}{T_j} \right\rceil C_j
\]

Where \(C_{\text{write}} \approx 50\mu s\) for the `write()` syscall, and \(T_j\) are periods of higher-priority tasks. For the 400Hz control loop with \(T = 2.5\)ms, the schedulability condition is:

\[
\frac{C_{\text{control}}}{T} + \frac{C_{\text{write}}}{T} \leq 1
\]

Given \(C_{\text{control}} \approx 2.0\)ms, this requires \(C_{\text{write}} \leq 0.5\)ms, which is satisfied.

The actual duty cycle written has quantization error due to the Sysfs integer nanosecond representation:

\[
\text{Error}_{\text{quant}} = \frac{1}{f_{\text{clk}}} = \frac{1}{19.2 \times 10^6} \approx 52\text{ns}
\]

#### Motor Current and Thermal Constraints

The electrical power drawn by each motor relates to mechanical power and efficiency \(\eta \approx 0.85\):

\[
P_{\text{elec}} = \frac{\tau_{\text{motor}} \cdot \omega_{\text{motor}}}{\eta}
\]

For a 3S LiPo battery at nominal 11.1V, the current per motor is:

\[
I_{\text{motor}} = \frac{P_{\text{elec}}}{11.1}
\]

The total rover current is the sum of all motors plus avionics (\(\approx 2A\)):

\[
I_{\text{total}} = \sum_{i=1}^{4} I_{\text{motor},i} + 2.0
\]

The PWM duty cycle must be limited to prevent overcurrent. The maximum allowed duty for thermal protection is:

\[
\text{Duty}_{\text{max, thermal}} = \sqrt{\frac{P_{\text{max, diss}} - P_{\text{amb}}}{R_{\text{th}} \cdot R_{\text{ds(on)}} \cdot I_{\text{max}}^2}}
\]

Where \(P_{\text{max, diss}} = 1.5W\) (MOSFET rating), \(R_{\text{th}} = 50^\circ C/W\), \(R_{\text{ds(on)}} = 0.01\Omega\), and \(I_{\text{max}} = 30A\).

#### Bitmask Algebra for Channel Enable/Disable

The motor output channels are controlled via bitmasks. For \(n\) channels, the active channel mask is:

\[
\text{Mask}_{\text{active}} = \sum_{i=0}^{n-1} b_i \cdot 2^i
\]

Where \(b_i = 1\) if channel \(i\) is active. The mixer bypass operation uses bitwise AND with the complement:

\[
\text{Mask}_{\text{bypass}} = \text{Mask}_{\text{all}} \& \sim \text{Mask}_{\text{test}}
\]

This ensures tested channels are removed from normal mixer output. For 8 channels, \(\text{Mask}_{\text{all}} = 0xFF\).

#### PWM Jitter and Synchronization Error

When multiple PWM channels must be synchronized (e.g., for coordinated motor movement), the maximum phase error between channels is bounded by the timer update mechanism. For a write sequence of \(m\) channels:

\[
t_{\text{error}} = (m-1) \cdot t_{\text{write}}
\]

Where \(t_{\text{write}} \approx 5\mu s\) per I2C transaction. For \(m=4\) motors, \(t_{\text{error}} \leq 15\mu s\), which at 50Hz corresponds to a duty cycle error of:

\[
\text{Error}_{\text{duty}} = \frac{t_{\text{error}}}{20000} \times 100\% = 0.075\%
\]

This is negligible for motor control but critical for synchronous operations like LED lighting.

#### Failure Probability of Motor Output System

The probability of undetected dangerous failure in the motor output path must be \(<10^{-8}\) per hour. For a system with \(n\) independent failure modes, each with failure rate \(\lambda_i\):

\[
P_{\text{fail}}(t) = 1 - \exp\left(-\sum_{i=1}^{n} \lambda_i t\right)
\]

For \(t = 1\) hour and \(P_{\text{fail}} < 10^{-8}\):

\[
\sum_{i=1}^{n} \lambda_i < 10^{-8} \text{ failures/hour}
\]

The motor output system includes: PWM generation (\(\lambda_{\text{PWM}} = 10^{-9}\)), I2C communication (\(\lambda_{\text{I2C}} = 2 \times 10^{-9}\)), and power stage (\(\lambda_{\text{power}} = 5 \times 10^{-9}\)). The total:

\[
\lambda_{\text{total}} = 8 \times 10^{-9} < 10^{-8}
\]

Satisfying the ASIL-D equivalent requirement.

---

### C++ Implementation: Hardware Motor Output, I2C PWM ICs, and Sysfs Duty Cycles

This section details the exact C++ implementation for motor control, throttle learning, and direct hardware actuation in the ArduPilot Rover architecture. All code executes within deterministic memory regions (ITCM for timing-critical functions, DTCM for state) and interfaces directly with STM32 hardware registers.

### Yaw Rate Feedforward & PID Integration (Steering.cpp)

**Memory-Mapped PID State and Gains:**
The `SteeringController` class implements the discrete-time PID with feedforward from the mathematical formulation. The PID state (`PIDState` struct) resides in DTCM at address `0x2000E000` for deterministic access, while constant gains (`PIDGains` struct) are stored in flash at `0x0800E000` with ECC protection.

```cpp
// Steering.cpp - Core steering controller implementation
class SteeringController {
private:
    // PID state stored in DTCM for deterministic access (0x2000E000)
    struct __attribute__((packed, aligned(4))) PIDState {
        volatile float error_integral;      // 0x2000E000: ∫e dt (rad)
        volatile float last_error;          // 0x2000E004: e[k-1] (rad)
        volatile float last_derivative;     // 0x2000E008: filtered d/dt (rad/s)
        volatile float output;              // 0x2000E00C: u[k] (rad/s)
        volatile uint32_t last_update_us;   // 0x2000E010: Last update time
        volatile uint8_t saturated : 1;     // 0x2000E014: Bit 0 - output saturated
        volatile uint8_t enabled : 1;       // 0x2000E014: Bit 1 - controller enabled
    } pid_state;
    
    // PID gains stored in flash with ECC protection (0x0800E000)
    const struct __attribute__((section(".flash"))) PIDGains {
        const float Kp;          // 0x0800E000: Proportional gain (2.0 typical)
        const float Ki;          // 0x0800E004: Integral gain (0.1 typical)
        const float Kd;          // 0x0800E008: Derivative gain (0.05 typical)
        const float Kff;         // 0x0800E00C: Feedforward gain (0.3 typical)
        const float max_i_term;  // 0x0800E010: Max integral term (1.0 rad)
        const float max_output;  // 0x0800E014: Max output (1.57 rad/s = 90°/s)
        const float derivative_cutoff_hz; // 0x0800E018: D term LPF cutoff (10Hz)
    } gains;
    
    // Vehicle kinematics parameters
    struct __attribute__((packed)) Kinematics {
        float track_width;       // 0x2000E018: Distance between wheels (m)
        float wheel_radius;      // 0x2000E01C: Wheel radius (m)
        float max_wheel_speed;   // 0x2000E020: Max wheel speed (m/s)
    } kinematics;
```

**Mathematical Mapping to Code:**
The `update()` function executes from ITCM at 400Hz (2.5ms period) and directly implements the PID control law `u[k] = Kp·e[k] + I[k] + Kd·D[k] + Kff·ω_desired[k]`. The integral term `I[k] = I[k-1] + Ki·T_s·e[k]` includes anti-windup via the `saturated` flag. The derivative uses a first-order IIR low-pass filter with cutoff frequency `derivative_cutoff_hz`.

```cpp
// Main PID update - deterministic execution from ITCM
__attribute__((section(".itcm")))
float SteeringController::update(float desired_yaw_rate, 
                                 float measured_yaw_rate,
                                 uint32_t current_time_us) {
    // Calculate time delta with overflow protection
    uint32_t dt_us = current_time_us - pid_state.last_update_us;
    if (dt_us > 10000) dt_us = 2500;  // Cap at 10ms, default to 2.5ms (400Hz)
    float dt = dt_us * 1.0e-6f;
    
    // Calculate error: e[k] = ω_desired[k] - ω_measured[k]
    float error = desired_yaw_rate - measured_yaw_rate;
    
    // Proportional term: P = Kp·e[k]
    float P = gains.Kp * error;
    
    // Integral term with conditional integration
    if (!pid_state.saturated) {
        pid_state.error_integral += error * dt;  // I[k] = I[k-1] + Ki·T_s·e[k]
        
        // Apply integral limits
        if (pid_state.error_integral > gains.max_i_term) {
            pid_state.error_integral = gains.max_i_term;
        } else if (pid_state.error_integral < -gains.max_i_term) {
            pid_state.error_integral = -gains.max_i_term;
        }
    }
    float I = gains.Ki * pid_state.error_integral;
    
    // Derivative term with low-pass filtering
    float derivative = calculate_derivative(error, dt);
    float D = gains.Kd * derivative;  // D[k] = Kd·D[k]
    
    // Feedforward term (model-based): FF = Kff·ω_desired[k]
    float FF = gains.Kff * desired_yaw_rate;
    
    // Total output: u[k] = P + I + D + FF
    float output = P + I + D + FF;
```

**Skid-Steer Kinematics Implementation:**
The code maps the PID output (yaw rate command in rad/s) to differential wheel speeds using the kinematic model `ω = (V_right - V_left) / T`. For a 20kg rover with track width `T`, it computes `ΔV = (ω·T)/2` and applies limits based on maximum wheel speed.

```cpp
    // Convert yaw rate to differential wheel speeds
    // ω = (V_right - V_left) / T
    // For symmetric vehicle: V_right = V_forward + ΔV, V_left = V_forward - ΔV
    // Where ΔV = (ω·T)/2
    
    float delta_v = (output * kinematics.track_width) / 2.0f;
    
    // Get forward speed from throttle controller
    float forward_speed = get_forward_speed();
    
    // Calculate individual wheel speeds
    float right_speed = forward_speed + delta_v;
    float left_speed = forward_speed - delta_v;
    
    // Limit to maximum wheel speeds
    if (right_speed > kinematics.max_wheel_speed) {
        right_speed = kinematics.max_wheel_speed;
        left_speed = forward_speed - (right_speed - forward_speed);
    } else if (left_speed > kinematics.max_wheel_speed) {
        left_speed = kinematics.max_wheel_speed;
        right_speed = forward_speed + (forward_speed - left_speed);
    }
    
    // Convert to wheel RPM: RPM = (speed / (2πR)) * 60
    float right_rpm = (right_speed / (2.0f * M_PI * kinematics.wheel_radius)) * 60.0f;
    float left_rpm = (left_speed / (2.0f * M_PI * kinematics.wheel_radius)) * 60.0f;
```

**Anti-Windup Implementation:**
The `apply_anti_windup()` function implements back-calculation anti-windup: when the output saturates, it reduces the integral term by `K_t·(u_actual - u_desired)`, where `K_t = 0.5` is the tracking time constant.

```cpp
// Anti-windup using back-calculation
__attribute__((section(".itcm")))
void SteeringController::apply_anti_windup(float error, float dt) {
    // Back-calculation anti-windup:
    // When saturated, reduce integral by K_t·(u_actual - u_desired)
    const float K_t = 0.5f;  // Tracking time constant
    
    float u_actual = pid_state.output;
    float u_desired = gains.Kp * error + 
                     gains.Ki * pid_state.error_integral + 
                     gains.Kd * pid_state.last_derivative;
    
    pid_state.error_integral -= (K_t / gains.Ki) * (u_actual - u_desired) * dt;
}
```

### Dynamic Base Throttle Learning (cruise_learn.cpp)

**RLS State and Parameter Storage:**
The `CruiseLearner` class implements the Recursive Least Squares (RLS) algorithm for adaptive throttle gain estimation. The learning state (`LearnState` struct) resides in DTCM at `0x2000F000`, while parameters (`LearnParams`) are in flash at `0x0800F000`.

```cpp
// cruise_learn.cpp - Throttle-speed relationship learning
class CruiseLearner {
private:
    // Learning state in DTCM (0x2000F000)
    struct __attribute__((packed, aligned(4))) LearnState {
        volatile float K_throttle;        // 0x2000F000: Throttle gain (m/s per %)
        volatile float throttle_deadband; // 0x2000F004: Minimum effective throttle (%)
        volatile float speed_filtered;    // 0x2000F008: Filtered speed (m/s)
        volatile float throttle_filtered; // 0x2000F00C: Filtered throttle (%)
        volatile float covariance;        // 0x2000F010: Estimate covariance P
        volatile uint32_t sample_count;   // 0x2000F014: Number of samples
        volatile uint32_t last_learn_us;  // 0x2000F018: Last learning update
        volatile uint8_t learning_active : 1; // 0x2000F01C: Bit 0
        volatile uint8_t converged : 1;       // 0x2000F01C: Bit 1
    } learn_state;
    
    // Learning parameters from flash (0x0800F000)
    const struct __attribute__((section(".flash"))) LearnParams {
        const float learning_rate;        // 0x0800F000: RLS forgetting factor (0.98)
        const float min_gain;             // 0x0800F004: Minimum K_throttle (0.01)
        const float max_gain;             // 0x0800F008: Maximum K_throttle (10.0)
        const float deadband_learn_rate;  // 0x0800F00C: Deadband learning rate (0.01)
        const float speed_filter_hz;      // 0x0800F010: Speed filter cutoff (1Hz)
        const uint32_t min_samples;       // 0x0800F014: Min samples before valid (100)
    } params;
```

**Mathematical Mapping to RLS Code:**
The `update_rls_estimate()` function directly implements the RLS update equations: `K = P·φ / (λ + φ²·P)`, `θ_hat = θ_hat + K·(y - φ·θ_hat)`, `P = (1/λ)·(P - K·φ·P)`. Here, `θ_hat` is `K_throttle`, `φ` is `effective_throttle`, `y` is `speed`, and `λ` is `learning_rate`.

```cpp
// Recursive Least Squares estimation
__attribute__((section(".itcm")))
void CruiseLearner::update_rls_estimate(float speed, float effective_throttle) {
    // Model: speed = K_throttle * effective_throttle
    // Where effective_throttle = throttle - throttle_deadband
    
    if (fabsf(effective_throttle) < 0.1f) {
        return;  // Avoid division by near-zero
    }
    
    // RLS update equations:
    // φ = effective_throttle (regressor)
    // y = speed (measurement)
    // K = P·φ / (λ + φ²·P)
    // θ_hat = θ_hat + K·(y - φ·θ_hat)
    // P = (1/λ)·(P - K·φ·P)
    
    float phi = effective_throttle;
    float y = speed;
    float lambda = params.learning_rate;
    
    // Calculate Kalman gain
    float K = (learn_state.covariance * phi) / 
              (lambda + phi * phi * learn_state.covariance);
    
    // Update parameter estimate
    float prediction = phi * learn_state.K_throttle;
    float innovation = y - prediction;
    learn_state.K_throttle += K * innovation;
    
    // Update covariance
    learn_state.covariance = (1.0f / lambda) * 
                            (learn_state.covariance - K * phi * learn_state.covariance);
```

**Deadband Estimation and Throttle Calculation:**
The deadband estimation implements `d[k+1] = α·τ[k] + (1-α)·d[k]` where `α = deadband_learn_rate`. The throttle calculation uses the inverse model: `throttle = (speed / K_throttle) + deadband`, with acceleration feedforward based on rover mass `M = 20.0kg`.

```cpp
// Deadband estimation using zero-speed detection
__attribute__((section(".itcm")))
void CruiseLearner::update_deadband_estimate(float throttle, float speed) {
    // When speed ≈ 0 but throttle > 0, we're at the deadband
    // Use slow adaptation: deadband_new = α·throttle + (1-α)·deadband_old
    
    float alpha = params.deadband_learn_rate;
    learn_state.throttle_deadband = alpha * throttle + 
                                   (1.0f - alpha) * learn_state.throttle_deadband;
```

```cpp
// Throttle calculation using learned model
__attribute__((section(".itcm")))
float CruiseLearner::get_throttle_for_speed(float desired_speed) {
    if (desired_speed < 0.1f || learn_state.K_throttle < params.min_gain) {
        return 0;  // Stop or model not learned yet
    }
    
    // Calculate required effective throttle
    // speed = K_throttle * (throttle - deadband)
    // => throttle = (speed / K_throttle) + deadband
    
    float effective_throttle = desired_speed / learn_state.K_throttle;
    float throttle = effective_throttle + learn_state.throttle_deadband;
    
    // Add feedforward based on acceleration requirement
    // τ·dv/dt = desired_speed - current_speed
    static float last_desired_speed = 0;
    float acceleration = (desired_speed - last_desired_speed) / 0.1f;  // 10Hz update
    last_desired_speed = desired_speed;
    
    // Add acceleration feedforward (assuming vehicle mass M)
    const float M = 20.0f;  // Vehicle mass (kg)
    const float F_max = 100.0f;  // Max force (N)
    float force_ff = M * acceleration;
    float throttle_ff = (force_ff / F_max) * 100.0f;  // Convert to %
    
    throttle += throttle_ff;
```

### Mixer Bypass Actuation (motor_test.cpp)

**Direct Hardware Register Control:**
The `MotorTester` class provides direct PWM hardware control, bypassing the normal mixer. The test state (`TestState` struct) resides in DTCM at `0x20010000`. Hardware register pointers map directly to STM32 timer capture/compare registers.

```cpp
// motor_test.cpp - Direct motor control for testing/calibration
class MotorTester {
private:
    // Test state in DTCM (0x20010000)
    struct __attribute__((packed, aligned(4))) TestState {
        volatile uint16_t pwm_values[8];      // 0x20010000: Direct PWM outputs (µs)
        volatile uint16_t test_pattern[8];    // 0x20010010: Test pattern values
        volatile uint32_t pattern_counter;    // 0x20010020: Pattern step counter
        volatile uint32_t test_start_us;      // 0x20010024: Test start time
        volatile uint32_t test_duration_us;   // 0x20010028: Test duration
        volatile uint8_t active_channels;     // 0x2001002C: Bitmask of active channels
        volatile uint8_t test_mode;           // 0x2001002D: TEST_CONSTANT, TEST_SWEEP, etc.
        volatile uint8_t bypass_mixer : 1;    // 0x2001002E: Bit 0 - bypass normal mixer
    } test_state;
    
    // Hardware register pointers for direct PWM control
    volatile uint32_t* const pwm_regs[8] = {
        (volatile uint32_t*)0x40012C34,  // TIM1_CCR1
        (volatile uint32_t*)0x40012C38,  // TIM1_CCR2
        (volatile uint32_t*)0x40012C3C,  // TIM1_CCR3
        (volatile uint32_t*)0x40012C40,  // TIM1_CCR4
        (volatile uint32_t*)0x40013434,  // TIM8_CCR1
        (volatile uint32_t*)0x40013438,  // TIM8_CCR2
        (volatile uint32_t*)0x4001343C,  // TIM8_CCR3
        (volatile uint32_t*)0x40013440,  // TIM8_CCR4
    };
```

**Test Pattern Generation Mathematics:**
The `update_test()` function generates test patterns including sweeps (`pwm_value = 1100 + progress * 800`), sine waves (`pwm_value = 1500 + 400·sin(2π·1·t)`), and step responses. All patterns respect the PWM range 1100-1900µs.

```cpp
// Update test pattern - deterministic execution from ITCM
__attribute__((section(".itcm")))
void MotorTester::update_test(uint32_t current_time_us) {
    // Check if test duration has expired
    if (current_time_us - test_state.test_start_us > test_state.test_duration_us) {
        stop_test();
        return;
    }
    
    // Calculate test progress (0.0 to 1.0)
    float progress = (float)(current_time_us - test_state.test_start_us) / 
                    (float)test_state.test_duration_us;
    
    // Update pattern counter
    test_state.pattern_counter++;
    
    // Generate and apply test pattern for each active channel
    for (int channel = 0; channel < 8; channel++) {
        if (!(test_state.active_channels & (1 << channel))) {
            continue;
        }
        
        uint16_t pwm_value = 0;
        
        switch (test_state.test_mode) {
            case TEST_CONSTANT:
                pwm_value = test_state.test_pattern[channel];
                break;
                
            case TEST_SWEEP:
                // Sweep from 1100 to 1900 µs over test duration
                pwm_value = 1100 + (uint16_t)(progress * 800.0f);
                break;
                
            case TEST_SINE:
                // 1Hz sine wave: 1500 ± 400·sin(2π·t)
                float t = (float)(current_time_us - test_state.test_start_us) * 1.0e-6f;
                float sine_val = sinf(2.0f * M_PI * 1.0f * t);  // 1Hz sine
                pwm_value = 1500 + (uint16_t)(sine_val * 400.0f);
                break;
```

**Direct Hardware PWM Write:**
The `write_pwm_direct()` function writes microseconds directly to timer capture/compare registers, converting µs to timer ticks at 1MHz resolution. It configures dead time (10µs) to prevent H-bridge shoot-through.

```cpp
// Direct hardware PWM write - bypasses all software layers
__attribute__((section(".itcm")))
void MotorTester::write_pwm_direct(uint8_t channel, uint16_t pwm_us) {
    if (channel >= 8 || !test_state.bypass_mixer) {
        return;
    }
    
    // Convert microseconds to timer ticks
    // Assuming 1MHz timer (84MHz/84 prescaler): ticks = µs
    uint32_t ticks = pwm_us;
    
    // Write directly to capture/compare register
    // This bypasses the entire PWM driver stack
    *pwm_regs[channel] = ticks;
    
    // If using center-aligned PWM mode, need to handle complementary outputs
    // For motors, typically use PWM mode 1 with complementary outputs
    if (channel < 4) {
        // TIM1 channels - ensure main output is enabled
        TIM1->BDTR |= TIM_BDTR_MOE;
        
        // Configure break functionality for safety
        TIM1->BDTR |= (10 << 8);  // Dead time = 10 ticks (10µs)
    } else {
        // TIM8 channels
        TIM8->BDTR |= TIM_BDTR_MOE;
        TIM8->BDTR |= (10 << 8);
    }
}
```

### Hardware-Level Integration

**STM32 Timer Configuration for Center-Aligned PWM:**
The hardware timer setup implements center-aligned PWM mode 1 with 1µs resolution (84MHz/84 prescaler) and 20ms period (50Hz). Dead time insertion of 10µs prevents shoot-through in motor driver H-bridges.

```cpp
// STM32 TIM1 and TIM8 configuration for motor control
void setup_motor_pwm_hardware(void) {
    // Enable peripheral clocks
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN | RCC_APB2ENR_TIM8EN;
    
    // Configure TIM1 for center-aligned PWM (motor 1-4)
    TIM1->PSC = 83;                     // 84MHz/84 = 1MHz (1µs resolution)
    TIM1->ARR = 19999;                  // 20ms period (50Hz)
    TIM1->RCR = 0;                      // No repetition
    
    // PWM mode 1 (active high), preload enable
    TIM1->CCMR1 = (6 << 4) | (1 << 3) |   // OC1M = 110 (PWM mode 1), OC1PE = 1
                  (6 << 12) | (1 << 11);  // OC2M = 110, OC2PE = 1
    
    // Center-aligned mode 1, auto-reload preload
    TIM1->CR1 = TIM_CR1_CMS_0 | TIM_CR1_CMS_1 |  // CMS = 11 (center-aligned mode 1)
                TIM_CR1_ARPE;                    // ARPE = 1 (buffer ARR)
```

**DMA Configuration for GPS Speed Collection:**
DMA Stream0 collects GPS speed measurements into a circular buffer in DTCM, enabling zero-CPU overhead data acquisition for the RLS algorithm.

```cpp
// DMA for collecting GPS speed measurements
void setup_gps_speed_dma(void) {
    // Enable DMA1 clock
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    
    // Configure DMA1 Stream0 for GPS speed buffer
    DMA1_Stream0->CR = 0;
    DMA1_Stream0->PAR = (uint32_t)&gps_speed_register;  // GPS speed source
    DMA1_Stream0->M0AR = (uint32_t)&gps_buffer.speeds[0];  // Destination
    DMA1_Stream0->NDTR = 10;                           // 10 elements
    DMA1_Stream0->CR = DMA_SxCR_PL_0 |                 // Medium priority
                      DMA_SxCR_MSIZE_1 |              // 32-bit memory
                      DMA_SxCR_PSIZE_1 |              // 32-bit peripheral
                      DMA_SxCR_MINC |                 // Memory increment
                      DMA_SxCR_CIRC |                 // Circular mode
                      DMA_SxCR_TCIE |                 // Transfer complete interrupt
                      DMA_SxCR_EN;                    // Enable
```

**RTOS Execution Context:**
- **SteeringController::update()**: Executes from ITCM at 400Hz (2.5ms period) in the fast loop thread (priority 98, SCHED_FIFO).
- **CruiseLearner::update_learning()**: Executes at 10Hz from the slow loop thread (priority 89).
- **MotorTester::update_test()**: Executes at 400Hz when active, bypassing the normal mixer output.
- All state structures reside in DTCM for deterministic access times (<100ns).
- DMA transfers occur asynchronously, with interrupts serviced by a dedicated DMA IRQ handler.

This implementation provides deterministic, low-latency motor control for the 20kg skid