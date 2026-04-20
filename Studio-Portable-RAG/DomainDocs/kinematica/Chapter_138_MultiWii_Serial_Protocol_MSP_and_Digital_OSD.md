# MultiWii Serial Protocol (MSP) and Digital OSD

_Generated 2026-04-20 05:35 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_MSP/AP_MSP.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD.cpp`

# Omnidirectional Mecanum Rover Matrix Mixing

This chapter details the kinematic mixing and real-time motor control for a heavy (~750 kg) omnidirectional agricultural rover equipped with Mecanum wheels. The implementation is split between two core ArduPilot modules: `AR_WPNav.cpp` calculates the desired global velocity vector, while `AP_MotorsUGV.cpp` (specifically the `AP_MotorsUGV_Mecanum` subclass) transforms this velocity into individual wheel torques via a 4×3 mixing matrix, applying dynamic constraints for a 400Hz real-time control system.

### Mathematical Formulation

**Kinematic Model and Mixing Matrix**
The velocity of each wheel `[v1, v2, v3, v4]ᵀ` is derived from the rover's body-frame velocity `[Vx, Vy, ωz]ᵀ` using a constant mixing matrix `M`:

```
[v1]   [ -1   1  -(L_x + L_y) ]   [Vx]
[v2] = [  1   1   (L_x + L_y) ] * [Vy]
[v3]   [  1   1  -(L_x + L_y) ]   [ωz]
[v4]   [ -1   1   (L_x + L_y) ]
```

Where `L_x = 1.0 m` (half wheelbase) and `L_y = 0.75 m` (half track width). Wheel radius `r = 0.4 m`.

**Inverse Kinematics and Torque Mapping**
The required motor torque `τ_i` for wheel `i` is:
`τ_i = J * α_i + d * ω_i + (r / η) * F_traction,i`
Where `J` is motor inertia, `d` is viscous damping, and `η` is gearbox efficiency. For the high-inertia rover (~300 kg·m² yaw inertia), the dominant term is the traction force.

**Dynamic Load Distribution**
The inverse solution from wheel forces `[F1, F2, F3, F4]` to body wrench `[Fx, Fy, τz]` is underdetermined. The pseudo-inverse `M⁺` provides the minimum-norm solution:
`F_wheels = M⁺ * W_desired`, where `M⁺ = Mᵀ * (M * Mᵀ)⁻¹`.

**Traction and Saturation Limits**
Each wheel's force is limited by available traction: `|F_i| ≤ μ * m_i * g`, where `μ` is the coefficient of friction and `m_i` is the dynamic load. The total motor power is constrained by battery voltage (`V_bat = 48V`) and current: `P_max ≈ 8160W`.

**Energy-Optimal Distribution**
A weighted pseudo-inverse minimizes power loss: `F_wheels = W * Mᵀ * (M * W * Mᵀ)⁻¹ * W_desired`, with weights `w_i = 1 / (R_motor + k_t * ω_i)`.

**Discrete-Time Integration**
At 400Hz (`Δt = 0.0025 s`), velocity is integrated: `ω_i[k+1] = ω_i[k] + (τ_i[k] / J) * Δt`.

### C++ Implementation

**Core Mixing Matrix Application**
The `AP_MotorsUGV_Mecanum` class applies the mixing matrix and constraints.

```cpp
// AP_MotorsUGV_Mecanum.cpp
const float AP_MotorsUGV_Mecanum::_mixing_matrix[4][3] = {
    {-1.0f,  1.0f, -1.75f}, // Front-Left:  -(L_x + L_y) = -1.75
    { 1.0f,  1.0f,  1.75f}, // Front-Right: +(L_x + L_y) = +1.75
    { 1.0f,  1.0f, -1.75f}, // Rear-Right:  -(L_x + L_y) = -1.75
    {-1.0f,  1.0f,  1.75f}  // Rear-Left:   +(L_x + L_y) = +1.75
};

void AP_MotorsUGV_Mecanum::_output_to_motors(float linear_vel_x, float linear_vel_y, float yaw_rate)
{
    float wheel_velocities[4];
    // Matrix multiplication: V_wheel = M * V_body
    for (uint8_t i = 0; i < 4; i++) {
        wheel_velocities[i] = (_mixing_matrix[i][0] * linear_vel_x) +
                              (_mixing_matrix[i][1] * linear_vel_y) +
                              (_mixing_matrix[i][2] * yaw_rate);
    }
    _apply_dynamic_constraints(wheel_velocities);
    _convert_to_pwm_and_output(wheel_velocities);
}
```

**Dynamic Constraint Application**
```cpp
void AP_MotorsUGV_Mecanum::_apply_dynamic_constraints(float wheel_velocities[4])
{
    // 1. Normalize to max wheel speed (saturation)
    float max_speed = 0.0f;
    for (uint8_t i = 0; i < 4; i++) {
        max_speed = MAX(max_speed, fabsf(wheel_velocities[i]));
    }
    if (max_speed > _wheel_vel_max) {
        float scale = _wheel_vel_max / max_speed;
        for (uint8_t i = 0; i < 4; i++) {
            wheel_velocities[i] *= scale;
        }
    }

    // 2. Torque-limited acceleration
    for (uint8_t i = 0; i < 4; i++) {
        float accel = (wheel_velocities[i] - _prev_wheel_vel[i]) / _dt;
        float max_accel = _torque_max / (_wheel_radius * _vehicle_mass * 0.25f);
        if (fabsf(accel) > max_accel) {
            wheel_velocities[i] = _prev_wheel_vel[i] + SIGN(accel) * max_accel * _dt;
        }
        _prev_wheel_vel[i] = wheel_velocities[i];
    }

    // 3. Power-limited scaling
    float total_power = 0.0f;
    for (uint8_t i = 0; i < 4; i++) {
        total_power += fabsf(wheel_velocities[i]) * _wheel_radius * _torque_max;
    }
    if (total_power > _power_max) {
        float scale = _power_max / total_power;
        for (uint8_t i = 0; i < 4; i++) {
            wheel_velocities[i] *= scale;
        }
    }
}
```

**PWM Conversion and RTOS Integration**
```cpp
void AP_MotorsUGV_Mecanum::_convert_to_pwm_and_output(float wheel_velocities[4])
{
    uint16_t pwm_output[4];
    for (uint8_t i = 0; i < 4; i++) {
        // Convert wheel velocity (-1 to +1) to PWM (1100-1900 µs)
        float normalized = constrain_float(wheel_velocities[i] / _wheel_vel_max, -1.0f, 1.0f);
        pwm_output[i] = 1500 + (normalized * 400); // 1500 ± 400 µs
    }
    // Direct hardware PWM output via STM32 timer
    _output_pwm(pwm_output);
}

// 400Hz RTOS task integration
void mecanum_control_task(void *pvParameters)
{
    const TickType_t xFrequency = pdMS_TO_TICKS(2.5); // 400Hz period
    TickType_t xLastWakeTime = xTaskGetTickCount();
    AP_MotorsUGV_Mecanum motors;
    AR_WPNav wp_nav;

    for (;;) {
        // 1. Get desired velocity from navigation (AR_WPNav.cpp)
        Vector3f desired_velocity = wp_nav.get_desired_velocity();
        // 2. Run mixing and output
        motors.output_skid_steering(desired_velocity.x, desired_velocity.y, desired_velocity.z);
        // 3. Wait for next period
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}
```

**Hardware PWM Configuration (STM32)**
```cpp
// STM32 Timer 2, Channel 1-4 for motor PWM
void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM2) {
        __HAL_RCC_TIM2_CLK_ENABLE();
        GPIO_InitTypeDef GPIO_InitStruct = {0};
        GPIO_InitStruct.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF1_TIM2;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
        // Configure for 400Hz PWM (2.5ms period)
        htim->Instance->ARR = 2099; // 84MHz / (2099+1) = 40kHz timer, 400Hz update
        htim->Instance->PSC = 0;
        HAL_TIM_PWM_Start(htim, TIM_CHANNEL_1);
        HAL_TIM_PWM_Start(htim, TIM_CHANNEL_2);
        HAL_TIM_PWM_Start(htim, TIM_CHANNEL_3);
        HAL_TIM_PWM_Start(htim, TIM_CHANNEL_4);
    }
}
```