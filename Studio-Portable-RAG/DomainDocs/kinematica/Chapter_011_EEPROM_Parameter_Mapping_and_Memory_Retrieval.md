# EEPROM Parameter Mapping, Default Trees, and Memory Retrieval

_Generated 2026-04-14 19:44 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/Parameters.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/Parameters.h`

# Chapter: Advanced Targeting, Human-Following, and Simple Mode

## Technical Introduction

This chapter documents the core navigation modes for a 20kg skid-steer agricultural rover within the ArduPilot 400Hz architecture. The system implements three deterministic behaviors: **Follow Mode** for intercepting moving targets using proportional navigation, **Simple Mode** for intuitive RC command transformation via body-to-NED frame rotation, and **Loiter Mode** for precise radius maintenance via PID control. Mode switching occurs via PWM input on TIM2 channel 5, with each controller executing at hardware-scheduled rates (10Hz for Follow/Loiter, 50Hz for Simple) from dedicated DTCM memory regions. The implementation prioritizes real-time performance through ITCM ISR placement and direct EKF state DMA from address `0x2000A000`.

---

## Mathematical Formulation

### Follow Mode: Lead-Angle Intercept & Proportional Navigation

**Intercept Geometry**: For target position \( P_t \), velocity \( V_t \), and rover position \( P_r \) with max speed \( V_{r_{max}} = 5.0 \, \text{m/s} \), solve for time-to-intercept \( t \) from:
\[
\| \mathbf{P}_t - \mathbf{P}_r + \mathbf{V}_t t \|^2 = (V_{r_{max}} t)^2
\]
Expanding yields the quadratic:
\[
a t^2 + b t + c = 0
\]
where:
\[
a = \|\mathbf{V}_t\|^2 - V_{r_{max}}^2, \quad b = 2(\mathbf{P}_t - \mathbf{P}_r) \cdot \mathbf{V}_t, \quad c = \|\mathbf{P}_t - \mathbf{P}_r\|^2
\]

**Proportional Navigation Law**: Commanded acceleration \( \mathbf{a}_{cmd} \) uses navigation constant \( N = 4.0 \), closing velocity \( V_c \), and line-of-sight rate \( \dot{\lambda} \):
\[
\mathbf{a}_{cmd} = N \cdot V_c \cdot \dot{\lambda}
\]
Implementation clamps magnitude to rover's maximum lateral acceleration.

### Simple Mode: Body-to-NED Frame Rotation

**2D Rotation Matrix**: Given rover yaw \( \psi \) from EKF quaternion, transform RC body-frame commands \( [u_{body}, v_{body}]^T \) to NED:
\[
\begin{bmatrix} u_{NED} \\ v_{NED} \end{bmatrix} = \begin{bmatrix} \cos\psi & -\sin\psi \\ \sin\psi & \cos\psi \end{bmatrix} \begin{bmatrix} u_{body} \\ v_{body} \end{bmatrix}
\]

**Differential Drive Kinematics**: For track width \( T = 0.5 \, \text{m} \) and wheel radius \( R_{wheel} = 0.1 \, \text{m} \):
\[
\omega_{left} = \frac{V_{forward} - (T/2) \cdot \omega_{desired}}{R_{wheel}}, \quad \omega_{right} = \frac{V_{forward} + (T/2) \cdot \omega_{desired}}{R_{wheel}}
\]
Wheel forces map to PWM via linear scaling: \( \text{PWM} = 1500 + K_{force} \cdot F \), with deadband of ±5%.

### Loiter Mode: Radius PID Control

**Tangent Vector Control**: For desired radius \( R_d \) and center \( \mathbf{C} \), position error \( \mathbf{e} = \mathbf{P}_r - \mathbf{C} \). Tangent vector for counter-clockwise motion:
\[
\mathbf{T} = [-e_y, e_x]^T
\]
Velocity command:
\[
\mathbf{V}_{cmd} = K_{tangent} \cdot \mathbf{T} + K_p \cdot \mathbf{e}
\]

**PID Stability Criterion**: Using Routh-Hurwitz on the second-order system with gains \( K_p = 10.0 \), \( K_i = 1.25 \), \( K_d = 20.0 \), the characteristic equation:
\[
J s^2 + (D + K_d) s + K_p = 0
\]
requires \( K_p > 0 \), \( (D + K_d) > 0 \), and \( (D + K_d) K_p > J K_i \) for stability, satisfied with \( J = 5.0 \, \text{kg·m}^2 \), \( D = 0.5 \).

---

## C++ Implementation

### Follow Mode Controller (`mode_follow.cpp`)

**Intercept Calculation (ITCM)**:
```cpp
__attribute__((section(".itcm")))
bool calculate_intercept_point(const float* target_pos, const float* target_vel,
                               const float* rover_pos, float V_r_max, float* intercept_point) {
    float a = target_vel[0]*target_vel[0] + target_vel[1]*target_vel[1] - V_r_max*V_r_max;
    float b = 2.0f * ((target_pos[0]-rover_pos[0])*target_vel[0] + 
                      (target_pos[1]-rover_pos[1])*target_vel[1]);
    float c = (target_pos[0]-rover_pos[0])*(target_pos[0]-rover_pos[0]) + 
              (target_pos[1]-rover_pos[1])*(target_pos[1]-rover_pos[1]);
    
    float disc = b*b - 4.0f*a*c;
    if (disc < 0.0f || fabsf(a) < 1e-6f) return false;
    
    float t = (-b - sqrtf(disc)) / (2.0f*a);
    if (t < 0.0f) t = (-b + sqrtf(disc)) / (2.0f*a);
    if (t < 0.0f) return false;
    
    intercept_point[0] = target_pos[0] + target_vel[0]*t;
    intercept_point[1] = target_pos[1] + target_vel[1]*t;
    return true;
}
```

**Proportional Navigation Update**:
```cpp
__attribute__((section(".itcm")))
void FollowModeController::update() {
    // DMA EKF state from 0x2000A000
    float* ekf_state = (float*)0x2000A000;
    float rover_pos[2] = {ekf_state[0], ekf_state[1]};
    float rover_vel[2] = {ekf_state[3], ekf_state[4]};
    
    // Target state from DTCM 0x20008000
    TargetState* target = (TargetState*)0x20008000;
    
    float intercept[2];
    if (calculate_intercept_point(target->position, target->velocity,
                                  rover_pos, 5.0f, intercept)) {
        float los[2] = {intercept[0] - rover_pos[0], intercept[1] - rover_pos[1]};
        float los_norm = sqrtf(los[0]*los[0] + los[1]*los[1]);
        if (los_norm > 0.1f) {
            los[0] /= los_norm; los[1] /= los_norm;
            
            float closing_vel = -(los[0]*rover_vel[0] + los[1]*rover_vel[1]);
            float los_rate = (los[0]*rover_vel[1] - los[1]*rover_vel[0]) / los_norm;
            
            float a_cmd = 4.0f * closing_vel * los_rate;
            // Clamp to max lateral acceleration
            float a_max = 2.0f;
            a_cmd = fmaxf(fminf(a_cmd, a_max), -a_max);
            
            // Store in DTCM intercept state at 0x20008100
            InterceptState* istate = (InterceptState*)0x20008100;
            istate->cmd_accel = a_cmd;
            istate->intercept_point[0] = intercept[0];
            istate->intercept_point[1] = intercept[1];
        }
    }
}
```

### Simple Mode Controller (`mode_simple.cpp`)

**Frame Rotation & PWM Output**:
```cpp
__attribute__((section(".itcm")))
void SimpleModeController::update() {
    // Get yaw from EKF quaternion at 0x2000A000 + 24 bytes
    float* ekf_q = (float*)0x2000A000 + 6; // q0,q1,q2,q3
    float yaw = atan2f(2.0f*(ekf_q[0]*ekf_q[3] + ekf_q[1]*ekf_q[2]),
                       1.0f - 2.0f*(ekf_q[2]*ekf_q[2] + ekf_q[3]*ekf_q[3]));
    
    // RC inputs from PWM capture registers
    float roll_input = (TIM1->CCR1 - 1500.0f) / 500.0f;  // Normalized ±1
    float pitch_input = (TIM1->CCR2 - 1500.0f) / 500.0f;
    
    // Body to NED rotation
    float cos_yaw = cosf(yaw);
    float sin_yaw = sinf(yaw);
    float u_ned = cos_yaw * roll_input - sin_yaw * pitch_input;
    float v_ned = sin_yaw * roll_input + cos_yaw * pitch_input;
    
    // Store in DTCM transform state at 0x20009000
    TransformState* tstate = (TransformState*)0x20009000;
    tstate->ned_velocity[0] = u_ned * 5.0f;  // Scale to m/s
    tstate->ned_velocity[1] = v_ned * 5.0f;
    
    // Convert to differential PWM outputs
    float omega_cmd = v_ned * 1.57f;  // Max turn rate
    float V_forward = u_ned * 5.0f;   // Max speed
    
    float V_left = V_forward - (0.5f / 2.0f) * omega_cmd;
    float V_right = V_forward + (0.5f / 2.0f) * omega_cmd;
    
    // Force to PWM: 1500 center, 0.1 N/μs
    uint16_t pwm_left = 1500 + (uint16_t)(V_left * 100.0f);
    uint16_t pwm_right = 1500 + (uint16_t)(V_right * 100.0f);
    
    // Apply 5% deadband
    if (abs(pwm_left - 1500) < 75) pwm_left = 1500;
    if (abs(pwm_right - 1500) < 75) pwm_right = 1500;
    
    // Direct PWM output to TIM1 channels 3 & 4
    TIM1->CCR3 = pwm_left;
    TIM1->CCR4 = pwm_right;
}
```

### Loiter Mode Controller (`mode_loiter.cpp`)

**PID Radius Control**:
```cpp
__attribute__((section(".itcm")))
void LoiterModeController::update() {
    LoiterState* lstate = (LoiterState*)0x2000A000;
    float* ekf_pos = (float*)0x2000A000;
    
    float dx = ekf_pos[0] - lstate->center_position[0];
    float dy = ekf_pos[1] - lstate->center_position[1];
    float dist = sqrtf(dx*dx + dy*dy);
    
    // Radius error
    float error = dist - lstate->desired_radius;
    
    // PID with anti-windup
    lstate->integral += error * 0.1f;  // dt = 0.1s for 10Hz
    if (lstate->integral > 5.0f) lstate->integral = 5.0f;
    if (lstate->integral < -5.0f) lstate->integral = -5.0f;
    
    float derivative = (error - lstate->last_error) / 0.1f;
    lstate->last_error = error;
    
    float cmd = 10.0f * error + 1.25f * lstate->integral + 20.0f * derivative;
    
    // Tangent vector for CCW motion
    float tangent_x = -dy;
    float tangent_y = dx;
    float tangent_norm = sqrtf(tangent_x*tangent_x + tangent_y*tangent_y);
    if (tangent_norm > 0.01f) {
        tangent_x /= tangent_norm;
        tangent_y /= tangent_norm;
    }
    
    // Velocity command: tangent + radial correction
    float vel_cmd_x = 2.0f * tangent_x + cmd * (dx/dist);
    float vel_cmd_y = 2.0f * tangent_y + cmd * (dy/dist);
    
    // Convert to wheel velocities
    float omega_cmd = (vel_cmd_x * dy - vel_cmd_y * dx) / (dist*dist);
    float V_forward = (vel_cmd_x * dx + vel_cmd_y * dy) / dist;
    
    // Differential drive conversion
    float V_left = V_forward - (0.5f / 2.0f) * omega_cmd;
    float V_right = V_forward + (0.5f / 2.0f) * omega_cmd;
    
    // Update PWM outputs
    uint16_t pwm_left = 1500 + (uint16_t)(V_left * 100.0f);
    uint16_t pwm_right = 1500 + (uint16_t)(V_right * 100.0f);
    
    TIM1->CCR3 = pwm_left;
    TIM1->CCR4 = pwm_right;
}
```

### Hardware Integration & Mode Switching

**Timer Configuration**:
```cpp
void setup_mode_timers() {
    // TIM4: 10Hz for Follow/Loiter modes (84MHz/8400/1000)
    RCC->APB1ENR |= RCC_APB1ENR_TIM4EN;
    TIM4->PSC = 8400 - 1;
    TIM4->ARR = 1000 - 1;
    TIM4->DIER |= TIM_DIER_UIE;
    TIM4->CR1 |= TIM_CR1_CEN;
    NVIC_EnableIRQ(TIM4_IRQn);
    NVIC_SetPriority(TIM4_IRQn, 1);
    
    // TIM3: 50Hz for Simple mode
    TIM3->PSC = 1680 - 1;
    TIM3->ARR = 1000 - 1;
    TIM3->DIER |= TIM_DIER_UIE;
    TIM3->CR1 |= TIM_CR1_CEN;
    NVIC_EnableIRQ(TIM3_IRQn);
    NVIC_SetPriority(TIM3_IRQn, 2);
    
    // DMA for EKF state transfer to DTCM
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    DMA1_Stream1->PAR = (uint32_t)0x2000A000;  // EKF source
    DMA1_Stream1->M0AR = (uint32_t)0x2000A000; // DTCM destination
    DMA1_Stream1->NDTR = 16;  // 16 floats
    DMA1_Stream1->CR = DMA_SxCR_CHSEL_0 | DMA_SxCR_MINC | DMA_SxCR_PINC |
                       DMA_SxCR_MSIZE_1 | DMA_SxCR_PSIZE_1 | DMA_SxCR_CIRC |
                       DMA_SxCR_EN;
}
```

**Mode Selection ISR**:
```cpp
__attribute__((section(".itcm")))
void TIM2_IRQHandler() {
    if (TIM2->SR & TIM_SR_CC5IF) {
        uint16_t pwm_val = TIM2->CCR5;
        uint8_t* mode_flag = (uint8_t*)0x20001000;
        
        // Mode selection logic
        if (pwm_val > 1800) {
            *mode_flag = MODE_FOLLOW;
            GPIOE->BSRR = GPIO_BSRR_BS5;  // Blue LED
        } else if (pwm_val > 1600) {
            *mode_flag = MODE_SIMPLE;
            GPIOE->BSRR = GPIO_BSRR_BS6;  // Green LED
        } else if (pwm_val > 1400) {
            *mode_flag = MODE_LOITER;
            GPIOE->BSRR = GPIO_BSRR_BS7;  // Yellow LED
        } else {
            *mode_flag = MODE_MANUAL;
            GPIOE->BSRR = GPIO_BSRR_BR5 | GPIO_BSRR_BR6 | GPIO_BSRR_BR7;
        }
        TIM2->SR &= ~TIM_SR_CC5IF;
    }
}
```

**Timer ISR Dispatchers**:
```cpp
__attribute__((section(".itcm")))
void TIM4_IRQHandler() {
    uint8_t mode = *(uint8_t*)0x20001000;
    if (mode == MODE_FOLLOW) {
        FollowModeController::instance()->update();
    } else if (mode == MODE_LOITER) {
        LoiterModeController::instance()->update();
    }
    TIM4->SR &= ~TIM_SR_UIF;
}

__attribute__((section(".itcm")))
void TIM3_IRQHandler() {
    if (*(uint8_t*)0x20001000 == MODE_SIMPLE) {
        SimpleModeController::instance()->update();
    }
    TIM3->SR &= ~TIM_SR_UIF;
}
```

---

## System Constants & Memory Map

| Constant | Value | Description |
|----------|-------|-------------|
| `V_R_MAX` | 5.0 m/s | Rover maximum velocity |
| `NAV_CONSTANT` | 4.0 | Proportional navigation gain |
| `MAX_FORCE` | 40.0 N | Maximum wheel force |
| `TRACK_WIDTH` | 0.5 m | Distance between wheels |
| `K_p` | 10.0 | Loiter proportional gain |
| `K_i` | 1.25 | Loiter integral gain |
| `K_d` | 20.0 | Loiter derivative gain |

**DTCM Memory Map**:
- `0x20008000`: `TargetState` (16 bytes)
- `0x20008100`: `InterceptState` (12 bytes)
- `0x20009000`: `TransformState` (8 bytes)
- `0x2000A000`: `LoiterState` (24 bytes) + EKF buffer (64 bytes)
- `0x20001000`: Mode flag (1 byte)

**Hardware Configuration**:
- **TIM1**: PWM output (CH3: left wheel, CH4: right wheel)
- **TIM2**: Mode switching via CH5 PWM capture
- **TIM3**: 50Hz Simple mode update
- **TIM4**: 10Hz Follow/Loiter update
- **GPIOE**: LEDs (PE5: Follow, PE6: Simple, PE7: Loiter)
- **DMA1**: Stream1 for EKF state transfer

---

*Note: `mode_steering.cpp` implementation is not included in this chapter as it pertains to the lower-level steering PID kinematics and cruise learning system, which is documented separately in the "Steering PID Kinematics, Cruise Speed Learning, and Actuator Testing" chapter.*