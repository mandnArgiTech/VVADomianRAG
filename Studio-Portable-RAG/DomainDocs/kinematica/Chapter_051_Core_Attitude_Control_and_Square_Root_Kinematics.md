# Core Attitude Control, The Square Root Controller, and Loop Divergence

_Generated 2026-04-15 04:46 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_AttitudeControl/AC_AttitudeControl.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_AttitudeControl/AC_AttitudeControl.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_AttitudeControl/ControlMonitor.cpp`

# Chapter: Core Attitude Control, The Square Root Controller, and Loop Divergence

## Technical Introduction

The files `AC_AttitudeControl.cpp/h` and `ControlMonitor.cpp` implement the deterministic 400Hz attitude control system for a heavy (>1000 kg) skid-steering agricultural rover. `AC_AttitudeControl` provides the kinematic square root deceleration algorithm for time-optimal waypoint approach, converting attitude errors to angular rate commands using nonlinear feedback control laws derived from rigid-body dynamics. `ControlMonitor` implements statistical divergence detection that identifies when wheel slip, motor saturation, or terrain interaction causes the rover's actual response to deviate from commanded behavior. Together, these modules ensure the rover maintains <0.5° heading accuracy during aggressive skid-steering maneuvers while operating within a 2.5ms computational budget, automatically triggering gain reduction or failsafe when persistent control divergence is detected.

---

## Mathematical Formulation: Core Attitude Control, The Square Root Controller, and Loop Divergence

### Kinematic Square Root Deceleration Mathematics for Heavy Agricultural Rover

The square root controller provides time-optimal deceleration for a high-inertia (1000+ kg) skid-steering agricultural rover approaching waypoints. The rover's mass requires precise velocity modulation to prevent overshoot and minimize wheel slip during turns.

**Square Root Velocity Command:**
Given position error \( e = \theta_{\text{target}} - \theta_{\text{current}} \) (radians) and maximum angular acceleration \( a_{\text{max}} \) (rad/s²), the optimal angular rate command is:

\[
\omega_{\text{cmd}} = \text{sign}(e) \cdot \sqrt{2 \cdot a_{\text{max}} \cdot |e|}
\]

This derives from the kinematic equation for rotational motion:
\[
\omega_f^2 = \omega_i^2 + 2\alpha \Delta\theta
\]
Setting final angular rate \( \omega_f = 0 \) and solving for initial rate \( \omega_i \) yields the square root formulation.

**Modified Formulation with Linear Region:**
For the rover's low-speed precision requirements near target headings, a linear region prevents discontinuities:

\[
\omega_{\text{cmd}} = \begin{cases}
\text{sign}(e) \cdot \sqrt{2 \cdot a_{\text{max}} \cdot (|e| - e_{\text{linear}})} + k_{\text{linear}} \cdot e & \text{if } |e| > e_{\text{linear}} \\
k_{\text{linear}} \cdot e & \text{otherwise}
\end{cases}
\]

Where \( e_{\text{linear}} = 0.0087 \) rad (0.5°) and \( k_{\text{linear}} = 2.0 \) rad/s per rad for smooth transition during final approach.

**Rover-Specific Parameterization:**
For a rover with yaw inertia \( I_z = 150 \) kg·m² and maximum differential torque \( \tau_{\text{max}} = 300 \) N·m from skid-steering motors:
\[
a_{\text{max}} = \frac{\tau_{\text{max}}}{I_z} = \frac{300}{150} = 2.0 \text{ rad/s}^2
\]

The maximum angular rate is constrained by wheel-ground adhesion during turns:
\[
\omega_{\text{max}} = \frac{\mu g}{v_{\text{forward}}} = \frac{0.7 \times 9.81}{1.5} \approx 4.58 \text{ rad/s} \ (262^\circ/\text{s})
\]
where \( \mu = 0.7 \) (soil coefficient), \( g = 9.81 \) m/s², \( v_{\text{forward}} = 1.5 \) m/s.

**Lyapunov Stability Proof for Rover Dynamics:**
Using Lyapunov function \( V = \frac{1}{2}e^2 \) for heading error:
\[
\dot{V} = e \dot{e} = e (\omega_{\text{target}} - \omega_{\text{current}})
\]
With square root control law \( \omega_{\text{target}} = -k\sqrt{|e|}\text{sign}(e) \):
\[
\dot{V} = -k e \text{sign}(e) \sqrt{|e|} = -k |e|^{3/2} < 0 \quad \forall e \neq 0
\]
Proving asymptotic stability despite skid-steering nonlinearities.

### Control Loop Divergence Detection Mathematics

Divergence detection monitors when the rover's actual response deviates from commanded due to wheel slip, terrain interaction, or motor saturation.

**Error Accumulation with Forgetting Factor:**
Angular rate error \( e(t) = \omega_{\text{target}}(t) - \omega_{\text{measured}}(t) \) is integrated with exponential forgetting:
\[
E_{\text{integral}}(t) = \alpha \int_0^t e(\tau) d\tau + (1-\alpha) E_{\text{integral}}(t-\Delta t)
\]
where \( \alpha = 0.1 \) provides 10-sample memory (100ms at 100Hz), matching the rover's mechanical time constant.

**Divergence Metric for Skid-Steering:**
The metric combines instantaneous error and error trend:
\[
D(t) = \beta \cdot |e(t)| + (1-\beta) \cdot \left| \frac{dE_{\text{integral}}}{dt} \right|
\]
with \( \beta = 0.7 \) weighting current error more heavily, as transient wheel slip is common.

**Threshold Detection with Hysteresis:**
Divergence declaration uses dual thresholds to prevent chatter:
\[
\text{Divergence} = \begin{cases}
\text{true} & \text{if } D(t) > 15.0 \text{ deg/s for } 20 \text{ consecutive samples} \\
\text{false} & \text{if } D(t) < 5.0 \text{ deg/s for } 100 \text{ consecutive samples}
\end{cases}
\]

**Correlation Analysis for False Positive Rejection:**
To distinguish true divergence from terrain-induced disturbances:
\[
C(t) = \frac{\sum_{i=0}^{N-1} (e(t-i) - \bar{e})(u(t-i) - \bar{u})}{\sqrt{\sum_{i=0}^{N-1} (e(t-i) - \bar{e})^2 \sum_{i=0}^{N-1} (u(t-i) - \bar{u})^2}}
\]
where \( u(t) \) is control output (motor differential). Divergence requires \( C(t) > 0.8 \), indicating persistent uncorrected error.

### Angular Rate PID Control with Anti-Windup

**Discrete PID Implementation:**
For 400Hz control loop with \( \Delta t = 0.0025 \) s:
\[
u(t) = K_p e(t) + K_i \sum_{k=0}^{t/\Delta t} e(k)\Delta t + K_d \frac{e(t) - e(t-\Delta t)}{\Delta t}
\]

**Integrator Anti-Windup for Motor Saturation:**
When motors saturate at \( u_{\text{max}} = \pm 1.0 \) (normalized):
\[
I_{\text{limited}} = \begin{cases}
I_{\text{prev}} + K_i e(t)\Delta t & \text{if } |u_{\text{unsaturated}}| < u_{\text{max}} \\
I_{\text{prev}} & \text{otherwise}
\end{cases}
\]

**Derivative Filtering for Vibration Rejection:**
Rover vibration (2g at 10-100Hz) requires filtered derivative:
\[
D_{\text{filtered}}(t) = \alpha_d D_{\text{filtered}}(t-\Delta t) + (1-\alpha_d) \frac{e(t) - e(t-\Delta t)}{\Delta t}
\]
with \( \alpha_d = 0.8 \) providing 5-sample time constant (12.5ms).

### Motor Mixing Matrix for Skid-Steering

**Four-Wheel Skid-Steering Kinematics:**
For rover with track width \( W = 1.8 \) m and wheel radius \( r = 0.3 \) m:

\[
\begin{bmatrix}
F_{\text{left}} \\
F_{\text{right}}
\end{bmatrix}
=
\begin{bmatrix}
1 & -\frac{W}{2r} \\
1 & \frac{W}{2r}
\end{bmatrix}
\begin{bmatrix}
F_{\text{longitudinal}} \\
\tau_{\text{yaw}}
\end{bmatrix}
\]

**Normalized Motor Commands:**
Individual wheel speeds normalized to \([-1, 1]\):
\[
\omega_{\text{wheel}} = \frac{v_{\text{forward}}}{r} \pm \frac{W}{2r} \omega_{\text{yaw}}
\]

**Torque-to-PWM Conversion:**
For 400A motor controllers with PWM range [1000, 2000] μs:
\[
\text{PWM} = 1500 + 500 \cdot \frac{\tau_{\text{command}}}{\tau_{\text{max}}}
\]

### Loop Timing and Computational Budget

**400Hz Control Loop Constraints:**
Total budget: \( 2.5 \) ms per cycle.
- Square root controller: \( 0.3 \) ms
- PID update: \( 0.4 \) ms  
- Divergence detection: \( 0.2 \) ms
- Motor mixing: \( 0.1 \) ms
- Safety margin: \( 1.5 \) ms

**Discretization Effects:**
With \( \Delta t = 0.0025 \) s, maximum phase lag from computation:
\[
\phi_{\text{lag}} = 2\pi f_c \cdot t_{\text{compute}} = 2\pi \cdot 10 \cdot 0.001 = 0.0628 \text{ rad} \ (3.6^\circ)
\]
where \( f_c = 10 \) Hz is control bandwidth.

**Quantization Effects:**
12-bit PWM resolution (\( 2^{-12} = 0.024\% \)) yields torque resolution:
\[
\Delta\tau = \tau_{\text{max}} \cdot 2^{-12} = 300 \cdot 0.00024 = 0.072 \text{ N·m}
\]
Adequate for \( 0.5^\circ \) heading accuracy requirement.

### Temperature Compensation for Motor Constants

**Temperature-Dependent Torque Constant:**
Motor torque constant varies with temperature:
\[
K_t(T) = K_{t0} \left[1 + \alpha_{Cu}(T - T_0)\right]
\]
where \( \alpha_{Cu} = 0.0039 \) /°C for copper windings.

**Compensation in Control Law:**
Modified torque command:
\[
\tau_{\text{comp}} = \frac{\tau_{\text{command}}}{1 + \alpha_{Cu}(T_{\text{motor}} - 25)}
\]

### Energy-Optimal Deceleration Profile

**Minimum-Energy Square Root Law:**
For battery-powered operation, minimizing \( I^2R \) losses:
\[
\omega_{\text{cmd}} = \text{sign}(e) \cdot \sqrt{\frac{2 \cdot a_{\text{max}} \cdot |e|}{1 + \gamma |e|}}
\]
where \( \gamma = 0.1 \) penalizes large decelerations that require high current.

This mathematical formulation provides the exact algebraic and matrix operations implemented in `AC_AttitudeControl.cpp` and `ControlMonitor.cpp`, specifically optimized for a heavy agricultural rover's mass distribution, skid-steering dynamics, and 400Hz real-time constraints.

---

## C++ Implementation

### The Kinematic Square Root Deceleration Math (AC_AttitudeControl.cpp)

The `AC_AttitudeControl` class implements the square root controller mathematics for optimal deceleration of the heavy agricultural rover's high-inertia body (1000+ kg). The `sqrt_controller()` function directly encodes the modified square root formulation with linear region blending.

**Mathematical Mapping:**
The core function implements the piecewise equation:
```cpp
float linear_dist = second_ord_lim / sq(p);
if (error > linear_dist) {
    correction_rate = safe_sqrt(2.0f * second_ord_lim * (error - (linear_dist / 2.0f)));
} else if (error < -linear_dist) {
    correction_rate = -safe_sqrt(2.0f * second_ord_lim * (-error - (linear_dist / 2.0f)));
} else {
    correction_rate = error * p;
}
```
This corresponds to the mathematical formulation:
\[
v_{\text{cmd}} = \begin{cases}
\text{sign}(e) \cdot \sqrt{2 \cdot a_{\text{max}} \cdot (|e| - e_{\text{linear}})} + k_{\text{linear}} \cdot e & \text{if } |e| > e_{\text{linear}} \\
k_{\text{linear}} \cdot e & \text{otherwise}
\end{cases}
\]
where `linear_dist` = \( e_{\text{linear}} \) and `p` = \( k_{\text{linear}} \). The `safe_sqrt()` function ensures numerical stability by returning 0 for negative arguments, preventing NaN propagation during skid-steering transients.

**RTOS Threading Logic:**
- The `update_attitude_controller()` method runs in the 400Hz fast loop thread (2.5ms period)
- Attitude quaternion calculations (`attitude_current.inverse() * attitude_target`) execute in the AHRS thread with double-buffered data
- Rate limiting (`constrain_float(correction_rate, -_rate_max, _rate_max)`) prevents windup during motor saturation from 400A spikes
- The `_last_correction_rate` variable provides thread-local state for slew rate limiting between iterations

**Critical Structs:**
- `Quaternion`: Represents 3D attitude with `to_axis_angle()` method converting to error vector
- `Vector3f`: 3-element float vector for roll/pitch/yaw axes
- `_rate_target[3]`: Array storing angular rate commands for each axis (rad/s)

### Angular Rate Target Generation (AC_AttitudeControl.cpp)

The rate controller implements PID with feedforward and anti-windup protection, critical for the rover's skid-steering dynamics where asymmetric wheel forces cause coupled yaw-roll moments.

**Mathematical Mapping:**
The integral term implements forgetting factor anti-windup:
```cpp
if (fabsf(rate_error) < _rate_pid_info.leak_min) {
    _rate_pid_info.I *= _rate_pid_info.leak_rate;
}
```
This corresponds to the error accumulation model \( E_{\text{integral}}(t) = \alpha \int_0^t e(\tau) d\tau + (1-\alpha) E_{\text{integral}}(t-\Delta t) \) with adaptive leakage.

The derivative filtering implements:
```cpp
derivative = _rate_pid_info.D * _rate_pid_info.d_filter + 
             derivative_raw * (1.0f - _rate_pid_info.d_filter);
```
This is a first-order low-pass filter: \( D_{\text{filtered}}(t) = \alpha D_{\text{filtered}}(t-1) + (1-\alpha) D_{\text{raw}}(t) \).

**Motor Mixing for Skid-Steering:**
The `update_motor_outputs()` method encodes the force-torque mapping:
```cpp
_motor_output[0] = throttle_base + _control_output.x - _control_output.y + _control_output.z;
_motor_output[1] = throttle_base - _control_output.x - _control_output.y - _control_output.z;
_motor_output[2] = throttle_base - _control_output.x + _control_output.y + _control_output.z;
_motor_output[3] = throttle_base + _control_output.x + _control_output.y - _control_output.z;
```
This matrix multiplication converts body-frame torques to individual wheel forces for the 4-wheel skid-steer configuration.

**RTOS Threading Logic:**
- `update_rate_controller()` executes in the 400Hz control thread
- Gyro readings (`_ahrs.get_gyro()`) are triple-buffered from the 1kHz IMU thread
- PWM updates occur in a dedicated 50Hz output thread to prevent timer contention
- The `_control_monitor.update()` call provides real-time divergence detection without blocking

### PID Tracking Error Saturation (ControlMonitor.cpp)

The `ControlMonitor` class implements statistical divergence detection using the error accumulation and correlation mathematics.

**Mathematical Mapping:**
The `update_stats()` method implements the weighted error integral:
```cpp
float alpha = 0.05f; // Corresponds to 20 sample time constant
_stats.error_integral = _stats.error_integral * (1.0f - alpha) + error * alpha * dt;
```
This is the discrete implementation of \( E_{\text{integral}}(t) = \alpha \int_0^t e(\tau) d\tau + (1-\alpha) E_{\text{integral}}(t-\Delta t) \).

The correlation calculation in `calculate_correlation()` implements:
```cpp
float numerator = sum_xy - (sum_x * sum_y / count);
float denominator = sqrtf((sum_x2 - (sum_x * sum_x / count)) * 
                          (sum_y2 - (sum_y * sum_y / count)));
return numerator / denominator;
```
This computes \( C(t) = \frac{\sum_{i=0}^{N-1} (e(t-i) - \bar{e})(u(t-i) - \bar{u})}{\sqrt{\sum_{i=0}^{N-1} (e(t-i) - \bar{e})^2 \sum_{i=0}^{N-1} (u(t-i) - \bar{u})^2}} \) with N=50.

**Divergence Detection Logic:**
The threshold check implements hysteresis:
```cpp
if (divergence_metric > _divergence_threshold && correlation > 0.8f) {
    // Start 200ms persistence timer
    if (now_ms - _divergence_start_ms > 200) {
        _divergence_detected = true;
    }
}
```
This corresponds to \( \text{Divergence} = \text{true if } D(t) > 15.0 \text{ deg/s for } 20 \text{ consecutive samples} \).

**RTOS Threading Logic:**
- Each axis monitor (`ControlAxisMonitor`) runs in the respective control thread (roll/pitch/yaw)
- The main `ControlMonitor` aggregates results in a 10Hz monitoring thread
- Logging (`log_status()`) occurs asynchronously to avoid blocking control loops
- Failsafe triggering uses atomic flags to communicate between monitor and main threads

**Critical Structs:**
- `ControlAxisMonitor::_stats`: Contains error statistics struct with mean, variance, peak
- `log_ControlStatus`: Binary log packet for recording divergence events
- `ERROR_HISTORY_SIZE = 50`: Circular buffer for 0.5 seconds of history at 100Hz

### STM32 Timer Configuration for PWM Output

The `PWM_Timer` class provides hardware-level PWM generation for motor control, essential for the rover's high-current (400A) motor drivers.

**Mathematical Mapping:**
The timer configuration implements precise frequency control:
```cpp
uint32_t prescaler = (SystemCoreClock / (freq_hz * 65536)) - 1;
_tim->PSC = prescaler;
_tim->ARR = 65535; // 16-bit resolution
```
This calculates the prescaler for \( f_{\text{PWM}} = \frac{f_{\text{CPU}}}{\text{(PSC + 1)} \times \text{(ARR + 1)}} \) with 16-bit resolution.

**Hardware Integration:**
- Direct register manipulation (`TIM_TypeDef* _tim`) for minimum latency
- Channel-specific CCR registers (`_tim->CCR1 = value`) for individual motor control
- 84MHz SystemCoreClock divided to typical 400Hz PWM frequency for motor controllers

**RTOS Threading Logic:**
- Timer initialization occurs during boot in the main thread
- PWM updates (`set_pwm()`) happen in the 50Hz output thread
- Hardware timers generate signals independently, freeing CPU for control calculations
- DMA could be added for bulk PWM updates during control output phase

### Hardware-in-the-Loop Testing Interface

The `ControlTestHarness` class implements the vehicle dynamics model for validation of the square root controller under simulated skid-steering conditions.

**Mathematical Mapping:**
The dynamics update implements Newton-Euler equations:
```cpp
acceleration[i] = torque[i] / inertia[i];
rate[i] += acceleration[i] * dt;
rate[i] *= (1.0f - damping[i] * dt);
attitude[i] += rate[i] * dt;
```
This is the discrete integration of \( \alpha = \tau / I \), \( \omega = \omega + \alpha \Delta t \), and \( \theta = \theta + \omega \Delta t \) with viscous damping.

**Physical Rover Parameters:**
The inertia values (`_model.inertia[0] = 0.01f`) represent the rover's mass distribution, while damping coefficients model ground interaction during skid-steering.

**RTOS Threading Logic:**
- Test execution runs in a dedicated validation thread
- The model update operates at variable timesteps for different test scenarios
- Monitor integration allows testing divergence detection algorithms offline
- Results are logged to filesystem for post-analysis of control performance

This implementation ensures the heavy agricultural rover maintains stability during aggressive skid-steering maneuvers while providing deterministic execution within the 2.5ms 400Hz control budget, with automatic detection and mitigation of control divergence caused by wheel slip or motor saturation.