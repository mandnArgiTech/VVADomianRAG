# Advanced Targeting, Human-Following, and Simple Mode

_Generated 2026-04-14 19:06 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_follow.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_steering.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_loiter.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_simple.cpp`

# C++ Implementation

### Target Velocity Projection Algebra (mode_follow.cpp)

The `FollowModeController` implements the lead-angle intercept solution. The `TargetState` and `InterceptState` reside in DTCM for deterministic access. The `calculate_intercept_point()` function solves the quadratic `a·t² + b·t + c = 0` derived from `||Pₜ - Pᵣ + Vₜ·t||² = (Vᵣ·t)²`.

```cpp
__attribute__((section(".dtcm")))
struct TargetState {
    float position_north;  // 0x20008000
    float position_east;   // +0x04
    float velocity_north;  // +0x08
    float velocity_east;   // +0x0C
    uint32_t timestamp_us; // +0x10
};

__attribute__((section(".dtcm")))
struct InterceptState {
    float intercept_time;  // 0x20008100
    float lead_angle_rad;  // +0x04
    float nav_accel_north; // +0x08
    float nav_accel_east;  // +0x0C
};

__attribute__((section(".itcm")))
void FollowModeController::calculate_intercept_point(const TargetState* tgt, const float* rover_pos, const float* rover_vel, InterceptState* out) {
    float dp_n = tgt->position_north - rover_pos[0];
    float dp_e = tgt->position_east - rover_pos[1];
    float dv_n = tgt->velocity_north - rover_vel[0];
    float dv_e = tgt->velocity_east - rover_vel[1];
    
    float a = dv_n*dv_n + dv_e*dv_e - V_R_MAX*V_R_MAX;
    float b = 2.0f*(dp_n*dv_n + dp_e*dv_e);
    float c = dp_n*dp_n + dp_e*dp_e;
    
    float discriminant = b*b - 4.0f*a*c;
    if (discriminant < 0.0f || fabsf(a) < 1e-6f) {
        out->intercept_time = -1.0f;
        return;
    }
    
    float sqrt_disc = sqrtf(discriminant);
    float t1 = (-b + sqrt_disc) / (2.0f*a);
    float t2 = (-b - sqrt_disc) / (2.0f*a);
    out->intercept_time = (t1 > 0.0f && t2 > 0.0f) ? fminf(t1, t2) : fmaxf(t1, t2);
    
    if (out->intercept_time > 0.0f) {
        float future_tgt_n = tgt->position_north + tgt->velocity_north * out->intercept_time;
        float future_tgt_e = tgt->position_east + tgt->velocity_east * out->intercept_time;
        float los_n = future_tgt_n - rover_pos[0];
        float los_e = future_tgt_e - rover_pos[1];
        float los_range = sqrtf(los_n*los_n + los_e*los_e);
        
        float v_rel_n = tgt->velocity_north - rover_vel[0];
        float v_rel_e = tgt->velocity_east - rover_vel[1];
        float cross_product = los_n*v_rel_e - los_e*v_rel_n;
        float dot_product = los_n*v_rel_n + los_e*v_rel_e;
        
        out->lead_angle_rad = asinf(cross_product / (los_range * V_R_MAX));
        float los_rate = cross_product / (los_range*los_range);
        out->nav_accel_north = NAV_CONSTANT * V_R_MAX * los_rate * (-los_e/los_range);
        out->nav_accel_east = NAV_CONSTANT * V_R_MAX * los_rate * (los_n/los_range);
    }
}
```

### Body-to-NED Frame Rotation (mode_simple.cpp)

The `SimpleModeController` transforms RC inputs from body frame to NED using a 2D rotation matrix `R(ψ) = [[cosψ, -sinψ], [sinψ, cosψ]]`. The `transform_rc_to_ned_frame()` function applies this transformation to normalized RC commands.

```cpp
__attribute__((section(".dtcm")))
struct RCState {
    float normalized[4];  // [throttle, yaw, pitch, roll] normalized to [-1,1]
    uint32_t last_update;
};

__attribute__((section(".dtcm")))
struct TransformState {
    float ned_force_north;  // 0x20009000
    float ned_force_east;   // +0x04
    float body_heading_rad; // +0x08 from EKF
};

__attribute__((section(".itcm")))
void SimpleModeController::transform_rc_to_ned_frame(const RCState* rc, const TransformState* tf, float* force_north, float* force_east) {
    float deadband = 0.05f;
    float fwd = fabsf(rc->normalized[0]) > deadband ? rc->normalized[0] : 0.0f;
    float right = fabsf(rc->normalized[1]) > deadband ? rc->normalized[1] : 0.0f;
    
    float cos_psi = cosf(tf->body_heading_rad);
    float sin_psi = sinf(tf->body_heading_rad);
    
    *force_north = MAX_FORCE * (fwd*cos_psi - right*sin_psi);
    *force_east = MAX_FORCE * (fwd*sin_psi + right*cos_psi);
}

__attribute__((section(".itcm")))
void SimpleModeController::calculate_wheel_commands(float force_north, float force_east, float heading_rad, float* left_pwm, float* right_pwm) {
    float cos_psi = cosf(heading_rad);
    float sin_psi = sinf(heading_rad);
    
    float F_forward = force_north*cos_psi + force_east*sin_psi;
    float F_right = -force_north*sin_psi + force_east*cos_psi;
    
    float tau_z = (F_right * TRACK_WIDTH) / 2.0f;
    float F_left_wheel = 0.5f*F_forward - tau_z/TRACK_WIDTH;
    float F_right_wheel = 0.5f*F_forward + tau_z/TRACK_WIDTH;
    
    *left_pwm = 1500.0f + (F_left_wheel / MAX_WHEEL_FORCE) * 500.0f;
    *right_pwm = 1500.0f + (F_right_wheel / MAX_WHEEL_FORCE) * 500.0f;
    
    *left_pwm = fmaxf(1100.0f, fminf(1900.0f, *left_pwm));
    *right_pwm = fmaxf(1100.0f, fminf(1900.0f, *right_pwm));
}
```

### Loiter Radius PID Control (mode_loiter.cpp)

The `LoiterModeController` maintains circular motion via PID control on radial error `e = R_desired - R_current`. The tangent vector `T = [-R_y, R_x]` defines the instantaneous velocity direction for counter-clockwise loiter.

```cpp
__attribute__((section(".dtcm")))
struct LoiterState {
    float center_north;     // 0x2000A000
    float center_east;      // +0x04
    float desired_radius;   // +0x08
    float current_radius;   // +0x0C
    float tangent_north;    // +0x10
    float tangent_east;     // +0x14
};

__attribute__((section(".dtcm")))
struct RadiusController {
    float integral_error;   // 0x2000A100
    float prev_error;       // +0x04
    float kp, ki, kd;       // +0x08, +0x0C, +0x10
};

__attribute__((section(".itcm")))
void LoiterModeController::maintain_radius_pid(LoiterState* ls, RadiusController* ctrl, const float* rover_pos, float dt) {
    float dx = rover_pos[0] - ls->center_north;
    float dy = rover_pos[1] - ls->center_east;
    ls->current_radius = sqrtf(dx*dx + dy*dy);
    
    float error = ls->desired_radius - ls->current_radius;
    ctrl->integral_error += error * dt;
    ctrl->integral_error = fmaxf(-INTEGRAL_LIMIT, fminf(INTEGRAL_LIMIT, ctrl->integral_error));
    
    float derivative = (error - ctrl->prev_error) / dt;
    ctrl->prev_error = error;
    
    float radial_force = ctrl->kp*error + ctrl->ki*ctrl->integral_error + ctrl->kd*derivative;
    
    float radial_dir_n = dx / ls->current_radius;
    float radial_dir_e = dy / ls->current_radius;
    
    ls->tangent_north = -dy;
    ls->tangent_east = dx;
    float tangent_mag = sqrtf(ls->tangent_north*ls->tangent_north + ls->tangent_east*ls->tangent_east);
    if (tangent_mag > 1e-6f) {
        ls->tangent_north /= tangent_mag;
        ls->tangent_east /= tangent_mag;
    }
    
    float tangent_force = DESIRED_TANGENT_VEL * VELOCITY_GAIN;
    float total_force_n = tangent_force*ls->tangent_north + radial_force*radial_dir_n;
    float total_force_e = tangent_force*ls->tangent_east + radial_force*radial_dir_e;
    
    float force_mag = sqrtf(total_force_n*total_force_n + total_force_e*total_force_e);
    if (force_mag > MAX_FORCE) {
        total_force_n = (total_force_n / force_mag) * MAX_FORCE;
        total_force_e = (total_force_e / force_mag) * MAX_FORCE;
    }
    
    volatile float* ekf_state = (float*)0x2000A000;
    ekf_state[6] = total_force_n;
    ekf_state[7] = total_force_e;
}
```

### Real-Time Mode Switching ISR (Hardware Layer)

The `TIM2_IRQHandler` services the PWM input on channel 5 to select between Follow, Simple, and Loiter modes. The ISR reads `TIM2->CCR5`, compares against thresholds, and sets the active mode flag while controlling status LEDs on GPIOE.

```cpp
__attribute__((section(".itcm")))
void TIM2_IRQHandler(void) {
    if (TIM2->SR & TIM_SR_CC5IF) {
        uint32_t capture = TIM2->CCR5;
        volatile uint32_t* mode_flag = (uint32_t*)0x20001000;
        
        if (capture > 1800) {
            *mode_flag = 1; // Follow mode
            GPIOE->BSRR = (1 << 5);  // Blue LED on
            GPIOE->BSRR = (1 << 21) | (1 << 22); // Green/Yellow off
        } else if (capture > 1600) {
            *mode_flag = 2; // Simple mode
            GPIOE->BSRR = (1 << 6);  // Green LED on
            GPIOE->BSRR = (1 << 20) | (1 << 22); // Blue/Yellow off
        } else if (capture > 1400) {
            *mode_flag = 3; // Loiter mode
            GPIOE->BSRR = (1 << 7);  // Yellow LED on
            GPIOE->BSRR = (1 << 20) | (1 << 21); // Blue/Green off
        } else {
            *mode_flag = 0; // Manual/Acro/Hold
            GPIOE->BSRR = (1 << 20) | (1 << 21) | (1 << 22); // All LEDs off
        }
        TIM2->SR &= ~TIM_SR_CC5IF;
    }
}
```

### Timer Configuration for Deterministic Execution

The `setup_mode_timers()` function configures TIM3 for 50Hz Simple mode updates and TIM4 for 10Hz Follow/Loiter updates. Both timers trigger DMA reads from the EKF state buffer at `0x2000A000`.

```cpp
void setup_mode_timers(void) {
    // TIM3 for Simple Mode (50Hz)
    RCC->APB1ENR |= RCC_APB1ENR_TIM3EN;
    TIM3->PSC = 8399; // 84MHz / (8399+1) = 10kHz
    TIM3->ARR = 199;  // 10kHz / 200 = 50Hz
    TIM3->DIER |= TIM_DIER_UIE;
    NVIC_EnableIRQ(TIM3_IRQn);
    NVIC_SetPriority(TIM3_IRQn, 2);
    TIM3->CR1 |= TIM_CR1_CEN;
    
    // TIM4 for Follow/Loiter Modes (10Hz)
    RCC->APB1ENR |= RCC_APB1ENR_TIM4EN;
    TIM4->PSC = 8399;
    TIM4->ARR = 999;  // 10kHz / 1000 = 10Hz
    TIM4->DIER |= TIM_DIER_UIE;
    NVIC_EnableIRQ(TIM4_IRQn);
    NVIC_SetPriority(TIM4_IRQn, 3);
    TIM4->CR1 |= TIM_CR1_CEN;
    
    // DMA1 Stream1 for EKF state transfer to DTCM
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    DMA1_Stream1->CR &= ~DMA_SxCR_EN;
    DMA1_Stream1->PAR = (uint32_t)&(IMU_DATA_REG);
    DMA1_Stream1->M0AR = 0x2000A000; // DTCM destination
    DMA1_Stream1->NDTR = 16; // 16 floats (x,y,z, vx,vy,vz, ax,ay,az, q0,q1,q2,q3, ωx,ωy,ωz)
    DMA1_Stream1->CR = DMA_SxCR_CHSEL_0 | DMA_SxCR_MINC | DMA_SxCR_PINC |
                       DMA_SxCR_MSIZE_1 | DMA_SxCR_PSIZE_1 | DMA_SxCR_CIRC |
                       DMA_SxCR_DIR_0 | DMA_SxCR_TCIE;
    DMA1_Stream1->CR |= DMA_SxCR_EN;
}
```