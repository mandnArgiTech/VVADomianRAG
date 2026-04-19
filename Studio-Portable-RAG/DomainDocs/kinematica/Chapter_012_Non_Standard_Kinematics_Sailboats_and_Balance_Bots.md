# Non-Standard Kinematics: Sailboat Wind Vectors and Inverted Pendulums

_Generated 2026-04-14 19:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/sailboat.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/sailboat.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/balance_bot.cpp`

# Chapter: Non-Standard Kinematics: Sailboat Wind Vectors and Inverted Pendulums

## Technical Introduction

Within the ArduPilot rover firmware for a 400Hz autonomous 20kg agricultural skid-steer platform, the files `sailboat.cpp`, `sailboat.h`, and `balance_bot.cpp` implement specialized control modes that transcend standard wheeled vehicle kinematics. These modules encode two distinct non-standard physical models: aerodynamic sailboat navigation and inverted pendulum stabilization.

`SailboatWindModel` (in `sailboat.cpp`) performs real-time apparent wind vector transformation and optimal sail angle calculation, enabling a rover to navigate using wind power. It implements the vector mathematics `V_apparent = V_true - V_vessel` at 10Hz, with DTCM-allocated state structures and DMA-driven anemometer input. The associated `SailboatTackingController` executes upwind tacking maneuvers using a state machine that respects the rover's no-go zone (`ψ_true ± 45°`) and skid-steer turn rate limits.

`BalanceBotController` (in `balance_bot.cpp`) implements a 400Hz Linear Quadratic Regulator (LQR) for inverted pendulum stabilization. It solves the state-space equation `ẋ = A·x + B·u` in real-time, with the Riccati solution pre-computed for the rover's specific mass (5.0kg payload), center-of-mass height (0.3m), and motor torque limits (10.0 N·m). The controller runs in the ITCM section from a TIM2 interrupt at NVIC priority 0, ensuring deterministic response for balancing dynamics.

Both systems adapt their native physics to the rover's skid-steer constraints: sailboat tacking generates differential wheel commands via `V_left = V_forward - (T/2)*ω_desired`, while balance bot LQR outputs convert to symmetric wheel torques. The implementations leverage the rover's EKF for state estimation, DTCM for fast state access, and direct hardware register manipulation for PWM generation to meet real-time requirements.

## Mathematical Formulation: Non-Standard Kinematics for a 20kg Agricultural Rover

This section details the exact physical mathematics and matrix algebra implemented in ArduPilot's specialty vehicle modes for a 20kg skid-steer agricultural rover. The formulations explicitly connect aerodynamic sailboat control and inverted pendulum dynamics to the rover's physical parameters: mass distribution, rotational inertia, and skid-steer constraints.

### Apparent Wind Vector Transformation: Sailboat Aerodynamic Control

#### True to Apparent Wind Vector Mathematics

For a moving vessel, the apparent wind vector experienced by the sail is computed via vector subtraction in the North-East-Down (NED) frame:

```
V_apparent = V_true - V_vessel
```

**Component Decomposition:**
```
V_true_N = V_true_mag * cos(ψ_true)
V_true_E = V_true_mag * sin(ψ_true)

V_vessel_N = V_vessel_mag * cos(ψ_vessel)
V_vessel_E = V_vessel_mag * sin(ψ_vessel)

V_apparent_N = V_true_N - V_vessel_N
V_apparent_E = V_true_E - V_vessel_E
```

**Magnitude and Direction:**
```
ψ_apparent = atan2(V_apparent_E, V_apparent_N)
V_apparent_mag = √(V_apparent_N² + V_apparent_E²)
```

**Rover-Specific Adaptation:** For a 20kg rover with skid-steer dynamics, vessel velocity `V_vessel_mag` is limited to 5.0 m/s (rover maximum speed), and the transformation accounts for the rover's high rotational inertia (J = 5.0 kg·m²) affecting heading rate changes during tacking maneuvers.

#### Optimal Sail Angle Piecewise Function

The sail angle relative to apparent wind follows a piecewise function based on apparent wind angle α (degrees):

```
γ_sail = 
  if α < 30°: 15° (close-hauled, minimum angle)
  if 30° ≤ α ≤ 90°: 0.5 * α (linear interpolation)
  if 90° < α ≤ 150°: 45° + 0.2 * (α - 90°) (broad reach)
  if α > 150°: 60° (running)
```

**Wind Speed Compensation:** For the rover's sail implementation, additional efficiency optimization reduces sail angle at higher winds:
```
if V_apparent_mag > 10.0 m/s:
    reduction = (V_apparent_mag - 10.0) * 0.5
    γ_sail = MAX(γ_sail - reduction, 10.0)
```

#### Tacking Decision Matrix Logic

Tacking initiation uses angular boundary checking with the rover's no-go zone defined as:

```
no_go_min = ψ_true ± 45° (dead zone)
```

The tack decision function evaluates:
```
if (ψ_desired - ψ_true) crosses no_go_min boundary:
    initiate_tack()
```

**Path Projection Check:** For large heading changes (>90°), intermediate headings are tested:
```
for i = 1 to 10:
    test_heading = current_heading + heading_error * (i / 10.0)
    test_rel_wind = normalize_angle(test_heading - ψ_true)
    if |test_rel_wind| < 45°:
        tack_required = true
```

### Inverted Pendulum Dynamics: Balance Bot Control

#### Linearized Equation of Motion

The balance bot is modeled as an inverted pendulum with point mass m = 5.0kg at height h = 0.3m, wheel radius r = 0.1m, and motor torque τ:

```
I * θ̈ = m * g * h * sin(θ) - m * h * ẍ * cos(θ) - τ
```

Where:
- θ = pitch angle from vertical (radians)
- x = horizontal position (meters)
- I = m * h² = 5.0 * (0.3)² = 0.45 kg·m² (moment of inertia)
- g = 9.80665 m/s²

#### State Space Representation

State vector: `x = [θ, θ̇, x, ẋ]ᵀ`
Control input: `u = τ` (motor torque)

System matrix A (4×4):
```
A = [[0, 1, 0, 0],
     [(m*g*h)/I, 0, 0, 0],
     [0, 0, 0, 1],
     [-(m*h)/I, 0, 0, 0]]
```

With rover values:
```
A[1][0] = (5.0 * 9.80665 * 0.3) / 0.45 = 32.6888 rad/s²
A[3][0] = -(5.0 * 0.3) / 0.45 = -3.3333 m/(rad·s²)
```

Control matrix B (4×1):
```
B = [0, -1/I, 0, r/I]ᵀ = [0, -2.2222, 0, 0.2222]ᵀ
```

#### Linear Quadratic Regulator (LQR) Control Law

Optimal control: `u = -K * x`
Where gain matrix K is computed from the algebraic Riccati equation:

```
Aᵀ*P + P*A - P*B*R⁻¹*Bᵀ*P + Q = 0
K = R⁻¹*Bᵀ*P
```

**Cost Matrices for Rover:** Weighted for pitch dominance over position:
```
Q = diag([1000.0, 100.0, 10.0, 1.0])  // State penalties
R = 0.1                               // Control effort penalty
```

**Gravity Compensation:** Added to LQR output for the rover's mass:
```
τ_gravity = m * g * h * sin(θ) = 5.0 * 9.80665 * 0.3 * sin(θ) = 14.710 * sin(θ) N·m
u_total = u_lqr + τ_gravity
```

#### Complementary Filter for Pitch Estimation

Fuses accelerometer and gyroscope data with rover-specific coefficients:

```
// Accelerometer pitch (valid when not accelerating)
θ_accel = atan2(-a_x, √(a_y² + a_z²))

// Gyro pitch integration (with bias removal)
θ_gyro = θ_gyro_prev + (ω_y - bias) * Δt

// Complementary filter (α = 0.98 for rover dynamics)
θ_filtered = α * (θ_filtered_prev + ω_y * Δt) + (1 - α) * θ_accel
```

**Bias Estimation:** When |√(a_x² + a_y² + a_z²) - 9.80665| < 0.5 m/s²:
```
bias = 0.999 * bias + 0.001 * ω_y
```

#### Motor Torque to PWM Conversion

For the rover's skid-steer configuration with equal torque on both wheels:

```
τ_per_wheel = u_total / 2.0

// Torque to current (Kt = 0.1 N·m/A for rover motors)
I_command = τ_per_wheel / 0.1

// Current limiting based on bus voltage (R_motor = 0.5Ω)
I_max = (V_bus / 0.5) * 0.8
I_command = CLAMP(I_command, -I_max, I_max)

// PWM conversion (1500 ± 500µs linear mapping)
duty = I_command / I_max
pwm_value = 1500 + duty * 500
```

#### Stability Proofs for Rover Implementation

##### Sailboat Upwind Navigation Stability

Velocity Made Good (VMG) optimization for the rover's sail configuration:

```
VMG = V * cos(β)
```

Where β is angle between rover heading and true wind. The equilibrium condition for stable upwind navigation:

```
F_sail * cos(γ_sail) = F_rolling_resistance + F_incline
F_sail * sin(γ_sail) = m * g * h_CoM * sin(φ_heel)
```

With rover parameters (m=20kg, μ_rolling=0.1, h_CoM=0.2m), the maximum sustainable sail force before skid is:

```
F_sail_max = μ_rolling * m * g / sin(γ_sail) = 0.1 * 20 * 9.80665 / sin(γ_sail)
```

##### Balance Bot LQR Stability Proof

Closed-loop dynamics: `ẋ = (A - B·K)·x`

Lyapunov function: `V(x) = xᵀ·P·x` where P solves the Riccati equation.

Derivative: `Ḃ(x) = xᵀ[(A-BK)ᵀ·P + P·(A-BK)]x = -xᵀ(Q + Kᵀ·R·K)x < 0 ∀ x ≠ 0`

**Rover Recovery Limit:** Maximum recoverable pitch angle:

```
θ_max = asin(τ_max / (m * g * h))
```

With rover motor τ_max = 10.0 N·m:
```
θ_max = asin(10.0 / (5.0 * 9.80665 * 0.3)) = asin(10.0 / 14.710) = 0.760 rad (43.5°)
```

The rover can recover from pitch angles up to 43.5° given its motor torque limits and mass distribution.

##### Skid-Steer Adaptation for Specialty Modes

For both sailboat and balance bot modes on the skid-steer rover, wheel velocity commands are derived from:

```
V_left = V_forward - (T/2) * ω_desired
V_right = V_forward + (T/2) * ω_desired
```

Where T = 0.5m (rover track width). This ensures the specialty control laws generate physically realizable skid-steer commands within the rover's dynamic constraints (V_max = 5.0 m/s, ω_max = 1.57 rad/s).

## C++ Implementation

### True vs Apparent Wind Trigonometry (sailboat.cpp)

The sailboat wind vector mathematics are implemented in `SailboatWindModel` class with DTCM-allocated state structures for deterministic 10Hz execution. The mathematical vector transformation `V_apparent = V_true - V_vessel` maps directly to the `update_wind_calculations()` function in ITCM memory.

**Wind State Structure in DTCM:**
```cpp
struct __attribute__((packed, aligned(4))) WindState {
    float true_wind_speed;       // 0x2000 B000: V_true_mag
    float true_wind_dir;         // 0x2000 B004: ψ_true
    float apparent_wind_speed;   // 0x2000 B008: V_apparent_mag
    float apparent_wind_dir;     // 0x2000 B00C: ψ_apparent
    float vessel_speed;          // 0x2000 B010: V_vessel_mag
    float vessel_heading;        // 0x2000 B014: ψ_vessel
    float sail_angle_setpoint;   // 0x2000 B018: γ_sail
    float rudder_angle_setpoint; // 0x2000 B01C: δ_rudder
    uint32_t last_update_us;     // 0x2000 B020: timestamp
    uint8_t wind_valid : 1;      // 0x2000 B024: validity flag
    uint8_t tacking_state : 2;   // bits 1-2: state machine
} wind_state;
```

**Vector Transformation Implementation:**
The mathematical component decomposition `V_true_N = V_true_mag * cos(ψ_true)` maps to:
```cpp
Vector2f vessel_vector(wind_state.vessel_speed * cosf(wind_state.vessel_heading),
                      wind_state.vessel_speed * sinf(wind_state.vessel_heading));
```

The apparent wind calculation `ψ_apparent = atan2(V_apparent_E, V_apparent_N)` becomes:
```cpp
wind_state.apparent_wind_dir = atan2f(aw_ned.y, aw_ned.x);
wind_state.apparent_wind_speed = aw_ned.length();
```

**Optimal Sail Angle Piecewise Function:**
The mathematical piecewise function for `γ_sail` based on apparent wind angle `α` is implemented as:
```cpp
float SailboatWindModel::calculate_optimal_sail_angle(float apparent_wind_angle) {
    float alpha_deg = fabsf(apparent_wind_angle * 180.0f / M_PI);
    float sail_angle_deg;
    
    if (alpha_deg < 30.0f) {
        sail_angle_deg = 15.0f;                    // Close-hauled
    } else if (alpha_deg <= 90.0f) {
        sail_angle_deg = 0.5f * alpha_deg;         // Linear interpolation
    } else if (alpha_deg <= 150.0f) {
        sail_angle_deg = 45.0f + 0.2f * (alpha_deg - 90.0f); // Broad reach
    } else {
        sail_angle_deg = 60.0f;                    // Running
    }
    
    return sail_angle_deg * M_PI / 180.0f;
}
```

**RTOS Execution Context:**
The `update_wind_calculations()` function runs at 10Hz from TIM4 ISR with NVIC priority 2, placed in ITCM section for deterministic execution. DMA2 Stream0 transfers anemometer data to `anemometer_buffer[4]` in DTCM at 100Hz.

### Upwind Tacking Matrix Logic (sailboat.cpp)

The tacking decision logic implements the mathematical no-go zone condition `no_go_min = ψ_true ± 45°` through a state machine with DTCM-stored navigation parameters.

**Tacking State Structure:**
```cpp
struct __attribute__((packed)) TackingState {
    float tack_angle;           // 0x2000 B100: ψ_desired after tack
    float tack_start_heading;   // 0x2000 B104: ψ_vessel at initiation
    float tack_progress;        // 0x2000 B108: 0→1 completion
    uint32_t tack_start_us;     // 0x2000 B10C: start timestamp
    uint8_t state;              // 0x2000 B110: IDLE/TURNING/COMPLETING
    uint8_t tack_direction;     // 0x2000 B111: 0=port, 1=starboard
} tacking_state;
```

**No-Go Zone Detection:**
The mathematical condition `if (ψ_desired - ψ_true) crosses no_go_min boundary` maps to:
```cpp
bool SailboatTackingController::check_tack_required(float desired_heading, float true_wind_dir) {
    float rel_wind_angle = normalize_angle(desired_heading - true_wind_dir);
    float no_go_half_angle = nav_params.no_go_angle * M_PI / 180.0f;
    
    if (fabsf(rel_wind_angle) < no_go_half_angle) {
        return true;  // Desired heading in no-go zone
    }
    return false;
}
```

**Tack Execution Mathematics:**
The 90° tack angle change `ψ_tack = ψ_current ± 90°` is implemented as:
```cpp
if (wind_rel > 0) {
    tacking_state.tack_direction = 0;  // Port
    tacking_state.tack_angle = current_heading - nav_params.tack_angle_change;
} else {
    tacking_state.tack_direction = 1;  // Starboard
    tacking_state.tack_angle = current_heading + nav_params.tack_angle_change;
}
```

**Smooth Tack Progression:**
The sigmoid-like progression uses the mathematical function:
```cpp
float smooth_progress = 0.5f - 0.5f * cosf(progress * M_PI);
float heading_during_tack = tacking_state.tack_start_heading + 
                           (tacking_state.tack_angle - tacking_state.tack_start_heading) * 
                           smooth_progress;
```

**RTOS Threading:**
- `check_tack_required()`: Called at 5Hz from navigation thread (priority 3)
- `update_tacking()`: Called at 20Hz from TIM3 ISR (priority 1) during active tack
- Sail feathering adjustments run synchronously with tack progression

### Pitch Acceleration PID Output (balance_bot.cpp)

The inverted pendulum LQR control implements the state-space mathematics `ẋ = A·x + B·u` with DTCM storage for 400Hz deterministic execution.

**Pendulum State Structure:**
```cpp
struct __attribute__((packed)) PendulumState {
    float pitch_angle;          // 0x2000 C000: θ (radians)
    float pitch_rate;           // 0x2000 C004: θ̇ (rad/s)
    float position;             // 0x2000 C008: x (meters)
    float velocity;             // 0x2000 C00C: ẋ (m/s)
    float wheel_angle_left;     // 0x2000 C010: φ_left
    float wheel_angle_right;    // 0x2000 C014: φ_right
    float wheel_speed_left;     // 0x2000 C018: ω_left
    float wheel_speed_right;    // 0x2000 C01C: ω_right
} pendulum_state;
```

**LQR Gain Storage:**
```cpp
struct __attribute__((packed)) LQRState {
    float K[4];                 // 0x2000 C020: [K1, K2, K3, K4]
    float Q[4];                 // 0x2000 C030: [q1, q2, q3, q4]
    float R;                    // 0x2000 C040: control penalty
    Matrix4f P;                 // 0x2000 C044: Riccati solution
    float u_optimal;            // 0x2000 C084: τ_command
} lqr_state;
```

**State-Space Implementation:**
The mathematical state vector `x = [θ, θ̇, x, ẋ]ᵀ` maps directly to:
```cpp
float theta = pendulum_state.pitch_angle;
float theta_dot = pendulum_state.pitch_rate;
float x = pendulum_state.position;
float x_dot = pendulum_state.velocity;
```

**LQR Control Law:**
The optimal control `u = -K·x` is implemented as:
```cpp
float u = -(lqr_state.K[0] * theta + 
           lqr_state.K[1] * theta_dot + 
           lqr_state.K[2] * x + 
           lqr_state.K[3] * x_dot);
```

**Gravity Compensation:**
The pendulum physics `τ_gravity = m·g·h·sin(θ)` adds:
```cpp
const float mass = 5.0f;
const float height = 0.3f;
const float g = 9.80665f;
float tau_gravity = mass * g * height * sinf(theta);
u += tau_gravity;
```

**Riccati Solver Implementation:**
The algebraic Riccati equation `Aᵀ·P + P·A - P·B·R⁻¹·Bᵀ·P + Q = 0` is solved iteratively:
```cpp
for (int iter = 0; iter < max_iter; iter++) {
    Matrix4f P_next = Q + A_T * P * A - 
                     A_T * P * B * (1.0f / (r + B_T * P * B)) * B_T * P * A;
    
    // Convergence check
    if (diff < tolerance) break;
    P = P_next;
}
```

**Complementary Filter Mathematics:**
The pitch estimation implements `θ_filtered = α·(θ_gyro) + (1-α)·θ_accel`:
```cpp
filter_state.pitch_filtered = alpha * (filter_state.pitch_filtered + pitch_rate_gyro * dt) + 
                             (1.0f - alpha) * filter_state.pitch_accel;
```

**Motor Torque Physics:**
The current-to-torque relationship `τ = K_t·I` maps to:
```cpp
const float Kt = 0.1f;  // Torque constant (N·m/A)
float current_command = torque_per_wheel / Kt;
```

**RTOS Execution Schedule:**
- `update_balance_control()`: 400Hz TIM2 ISR, NVIC priority 0 (highest), ITCM section
- `estimate_pitch_angle()`: 400Hz synchronous with control update
- `calculate_riccati_solution()`: One-time execution at initialization
- PWM updates: Direct register writes to TIM1->CCR1/CCR2 at 16kHz

### Hardware Integration Layer

**Sailboat Servo Control:**
TIM8 generates 50Hz PWM for sail servo with 1500µs center:
```cpp
TIM8->PSC = 83;                     // 84MHz/84 = 1MHz
TIM8->ARR = 19999;                  // 20ms period (50Hz)
TIM8->CCR1 = 1500;                  // Center position (γ_sail = 0)
```

**Balance Bot Motor Control:**
TIM1 generates 16kHz PWM for motor controllers:
```cpp
TIM1->PSC = 0;                      // 84MHz
TIM1->ARR = 5249;                   // 84MHz/5250 = 16kHz
TIM1->CCR1 = 2624;                  // 50% duty (τ = 0)
```

**Anemometer DMA Interface:**
DMA2 Stream0 transfers wind sensor data to DTCM:
```cpp
DMA2_Stream0->PAR = (uint32_t)&ADC1->DR;
DMA2_Stream0->M0AR = (uint32_t)anemometer_buffer;
DMA2_Stream0->NDTR = 4;             // 4-element buffer
```

**Memory Map:**
- `0x2000B000-0x2000B0FF`: Sailboat wind and tacking states
- `0x2000C000-0x2000C0FF`: Balance bot pendulum and LQR states
- `0x20001000-0x2000100F`: Anemometer DMA buffer
- ITCM section: All `__attribute__((section(".itcm")))` control functions

**Thread Priority Assignment:**
1. TIM2 ISR (400Hz balance control): NVIC priority 0
2. TIM3 ISR (20Hz tacking update): NVIC priority 1  
3. TIM4 ISR (10Hz wind calculations): NVIC priority 2
4. Navigation thread (5Hz tack decisions): RTOS priority 3
5. Logging thread: RTOS priority 4 (lowest)

The C++ implementation directly encodes the mathematical formulations into deterministic real-time code, with DTCM storage for state variables and ITCM placement for time-critical control algorithms, ensuring the 400Hz execution requirement for balance bot stability and 10Hz update for sailboat wind vector calculations.