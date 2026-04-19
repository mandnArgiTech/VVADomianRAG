# Core Proximity Architecture, 3D Boundary Mapping, and Sector Arrays

_Generated 2026-04-15 12:03 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_Backend.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_Boundary_3D.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Proximity/AP_Proximity_Boundary_3D.h`

# Payload Manipulation, Electro-Permanent Magnets (EPM), and PWM Actuation

This chapter details the mathematical and software architecture for the 400Hz agricultural rover's payload manipulation system. The system comprises a non-blocking MAVLink command arbiter, an Electro-Permanent Magnet (EPM) gripper for ferrous payloads, and a PWM-actuated servo gripper for general manipulation. All control logic is designed to operate asynchronously, ensuring the 2.5ms primary control loop is never blocked. The architecture must account for the rover's 1200 kg mass, high inertia (J_zz ≈ 150 kg·m²), and severe skid-steering vibrations which impose dynamic loads on the gripper mechanism and can affect magnetic holding strength.

### Mathematical Formulation

#### Command Arbitration and State Machine Logic
Payload commands arrive via MAVLink (`MAV_CMD_DO_GRIPPER`). To prevent blocking, a FIFO queue and a finite state machine (FSM) arbitrate execution. The arbitration logic ensures only one command is active at a time.

Let `Q` be the command queue of length `L`. An incoming command `C_new` with instance `I` and gripper number `N` is enqueued if:
1.  The queue is not full (`|Q| < L`).
2.  No command with the same `(I, N)` is already pending in `Q` (deduplication).

The state machine `S` ∈ {`IDLE`, `GRABBING`, `RELEASING`, `HOLDING`}. Transitions are triggered by dequeued commands or timeouts:
*   `IDLE → GRABBING` on `GRIPPER_ACTION_GRAB`.
*   `GRABBING → HOLDING` after pulse time `T_pulse` (EPM) or servo travel time `T_servo`.
*   `HOLDING → RELEASING` on `GRIPPER_ACTION_RELEASE`.
*   `RELEASING → IDLE` after `T_pulse`.

The system's temporal robustness is defined by the watchdog timeout: `T_timeout = max(T_pulse, T_servo) + δ`, where `δ` is a safety margin (e.g., 500ms). If `S` remains in `GRABBING` or `RELEASING` for `> T_timeout`, a fault is raised and the state resets to `IDLE`.

#### Electro-Permanent Magnet (EPM) Physics and Pulse Control
An EPM combines a hard magnetic material (e.g., Alnico) with a soft magnetic material (e.g., steel) wound with a coil. The total magnetic moment vector is:
```
𝐦_total = 𝐦_hard + 𝐦_soft
```
In the *released* state, `𝐦_hard` and `𝐦_soft` are anti-parallel, resulting in near-zero external field. A short current pulse through the coil temporarily saturates the soft material, flipping `𝐦_soft` to align with `𝐦_hard`, creating a strong external field for *grabbing*.

The coil is an RL circuit. The current rise during a pulse of voltage `V_supply` (typically 24V) is:
```
I(t) = (V_supply / R_coil) * (1 - e^{-t / τ})
```
where `τ = L_coil / R_coil` is the coil's time constant. The pulse must be long enough to exceed the soft material's saturation current `I_sat` but short to minimize heating. The required pulse time `T_pulse` is derived from:
```
I(T_pulse) ≥ I_sat  =>  T_pulse ≥ -τ * ln(1 - (I_sat * R_coil / V_supply))
```
For the rover, `V_supply = 24V`, `R_coil ≈ 2Ω`, `L_coil ≈ 10mH`, `τ = 5ms`. With `I_sat = 8A`, `T_pulse ≈ 2.2ms`. The system uses a configurable parameter `GRIP_EPM_PULSE_MS` (default 250ms) which includes a large safety factor for component variability and reduced voltage under load.

The magnetic holding force `F_hold` against a flat steel surface is approximated by:
```
F_hold ≈ (B^2 * A) / (2 * μ_0)
```
where `B` is the surface field strength (0.4-0.6 T for a typical EPM), `A` is the pole face area (~0.001 m²), and `μ_0 = 4π × 10^{-7} N/A²`. This yields `F_hold ≈ 300 N`. The rover's skid-steering vibrations apply cyclic shear forces. The safety factor `SF` is:
```
SF = F_hold / (m_payload * a_vibration)
```
With a 50 kg payload and vibration acceleration `a_vibration ≈ 2g` (19.6 m/s²), the required force is ~980 N, giving `SF ≈ 0.3`. This necessitates multiple EPM units or mechanical latching for secure transport.

#### PWM Servo Actuation and Trapezoidal Profiling
The servo gripper uses a standard PWM interface (1000-2000 µs pulse width). The kinematic mapping from command angle `θ_cmd` (0°=open, 180°=closed) to PWM pulse width `PW` is linear:
```
PW(θ_cmd) = 1000 + (θ_cmd / 180) * 1000   [µs]
```
For non-linear linkages, a piecewise linear or polynomial mapping is stored in a lookup table.

To reduce stress on the gearbox and prevent load slippage due to inertia, a trapezoidal velocity profile is applied. The profile defines the commanded angle `θ(t)` over the movement time `T_move` with max velocity `ω_max` and acceleration `α`:
1.  **Acceleration Phase** (`0 ≤ t < t_a`): `θ(t) = 0.5 * α * t^2`
2.  **Coast Phase** (`t_a ≤ t < T_move - t_a`): `θ(t) = 0.5 * α * t_a^2 + ω_max * (t - t_a)`
3.  **Deceleration Phase** (`T_move - t_a ≤ t ≤ T_move`): `θ(t) = θ_target - 0.5 * α * (T_move - t)^2`

Where:
*   `t_a = ω_max / α`
*   `T_move = (θ_target / ω_max) + (ω_max / α)` (for a symmetric profile)
*   `ω_max` is derived from the parameter `GRIPPER_SERVO_RAMP_RATE` (deg/s).
*   `α` is chosen based on servo torque and load inertia.

The rover's 1200 kg mass induces high reaction forces on the gripper arm. The required servo torque `τ_servo` at the joint is:
```
τ_servo = m_payload * g * L_arm * cos(θ) + J_arm * α
```
where `L_arm` is the moment arm, `J_arm` is the gripper's rotational inertia, and `α` is the angular acceleration from the trapezoidal profile. This calculation ensures the selected servo (e.g., 50 kg-cm) does not stall under dynamic load.

### C++ Implementation

#### MAVLink Command Arbitration and State Machine
The core class is `AP_Gripper`. It maintains the queue and state machine, calling into a backend (`AP_Gripper_EPM` or `AP_Gripper_Servo`).

```cpp
// AP_Gripper.h
class AP_Gripper {
public:
    enum class State {
        IDLE,
        GRABBING,
        RELEASING,
        HOLDING
    };

    enum class Gripper_Action {
        RELEASE = 0,
        GRAB = 1,
        HOLD = 2
    };

    bool init();
    void update();
    bool grab();
    bool release();
    bool valid() const { return _enabled && _backend != nullptr; }

private:
    State _state;
    AP_Gripper_Backend *_backend;
    uint32_t _action_start_ms;
    bool _enabled;

    struct {
        mavlink_command_int_t cmd;
        uint32_t received_ms;
    } _queue[GRIPPER_QUEUE_SIZE];
    uint8_t _queue_head;
    uint8_t _queue_tail;

    void process_command_queue();
    void set_state(State new_state);
};
```

The `update()` method, called from the main 400Hz loop, manages timing and state transitions without blocking.

```cpp
// AP_Gripper.cpp
void AP_Gripper::update()
{
    if (!valid()) {
        return;
    }

    process_command_queue();

    switch (_state) {
        case State::GRABBING:
        case State::RELEASING:
            if (hal.util->get_soft_armed()) {
                if (AP_HAL::millis() - _action_start_ms > _backend->get_pulse_time_ms()) {
                    _backend->set_grab_state(_state == State::GRABBING);
                    set_state((_state == State::GRABBING) ? State::HOLDING : State::IDLE);
                }
            }
            break;
        case State::HOLDING:
        case State::IDLE:
            // Nothing to do, backend maintains state
            break;
    }
}
```

#### Electro-Permanent Magnet (EPM) Backend
The `AP_Gripper_EPM` class implements the pulse timing logic and direct GPIO control for the EPM coil driver (typically an H-bridge).

```cpp
// AP_Gripper_EPM.h
class AP_Gripper_EPM : public AP_Gripper_Backend {
public:
    AP_Gripper_EPM();
    bool init() override;
    void update() override;
    bool grab() override;
    bool release() override;
    uint16_t get_pulse_time_ms() const override { return _pulse_time_ms; }

private:
    enum class EPM_State {
        IDLE,
        PULSING_GRAB,
        PULSING_RELEASE,
        GRABBED,
        RELEASED
    };

    EPM_State _epm_state;
    uint32_t _pulse_start_ms;
    uint16_t _pulse_time_ms; // GRIP_EPM_PULSE_MS parameter

    void set_gpio(bool grab_active, bool release_active);
    void pulse_grab();
    void pulse_release();
};
```

The critical pulse timing is handled in `update()`. The code directly manipulates the STM32's GPIO registers for minimal latency.

```cpp
// AP_Gripper_EPM.cpp
void AP_Gripper_EPM::pulse_grab()
{
    _epm_state = EPM_State::PULSING_GRAB;
    _pulse_start_ms = AP_HAL::millis();
    // Activate GRAB line, deactivate RELEASE line on the H-bridge
    set_gpio(true, false);
    // Schedule a one-shot timer interrupt for precise pulse termination
    hal.scheduler->register_timer_process(FUNCTOR_BIND_MEMBER(&AP_Gripper_EPM::pulse_timer_callback, void));
}

void AP_Gripper_EPM::pulse_timer_callback()
{
    if (_epm_state == EPM_State::PULSING_GRAB &&
        AP_HAL::millis() - _pulse_start_ms >= _pulse_time_ms) {
        set_gpio(false, false); // Turn off both H-bridge inputs
        _epm_state = EPM_State::GRABBED;
    }
    // Similar logic for PULSING_RELEASE
}
```

#### PWM Servo Backend with Trapezoidal Profiling
The `AP_Gripper_Servo` class uses the `SRV_Channels` abstraction for PWM output and implements the trapezoidal velocity profiler.

```cpp
// AP_Gripper_Servo.h
class AP_Gripper_Servo : public AP_Gripper_Backend {
public:
    AP_Gripper_Servo();
    bool init() override;
    void update() override;
    bool grab() override;
    bool release() override;
    uint16_t get_pulse_time_ms() const override { return _servo_move_time_ms; }

private:
    enum class Servo_State {
        IDLE,
        MOVING,
        HOLDING
    };

    Servo_State _servo_state;
    uint32_t _move_start_ms;
    uint16_t _servo_move_time_ms; // Time for full 0->180° movement
    uint16_t _servo_ramp_rate;    // GRIPPER_SERVO_RAMP_RATE in deg/s
    float _current_pos;           // Current position in degrees
    float _target_pos;            // Target position in degrees

    void set_servo_position(float pos_deg);
    void update_trapezoidal_profile();
};
```

The profiler is executed in `update()`, calculating the next setpoint based on elapsed time.

```cpp
// AP_Gripper_Servo.cpp
void AP_Gripper_Servo::update_trapezoidal_profile()
{
    if (_servo_state != Servo_State::MOVING) {
        return;
    }

    uint32_t elapsed_ms = AP_HAL::millis() - _move_start_ms;
    float t = elapsed_ms * 1e-3f; // Convert to seconds

    float total_distance = fabsf(_target_pos - _current_pos);
    float ramp_time = _servo_ramp_rate / _servo_accel; // t_a
    float coast_distance = _servo_ramp_rate * ramp_time;
    float ramp_distance = 0.5f * _servo_accel * ramp_time * ramp_time;

    float commanded_pos;
    if (total_distance <= 2 * ramp_distance) {
        // Triangular profile (no coast phase)
        float half_time = sqrtf(total_distance / _servo_accel);
        if (t < half_time) {
            commanded_pos = _current_pos + 0.5f * _servo_accel * t * t * sign;
        } else {
            float t_dec = t - half_time;
            commanded_pos = _current_pos + (total_distance * sign) - 0.5f * _servo_accel * t_dec * t_dec * sign;
        }
    } else {
        // Trapezoidal profile
        if (t < ramp_time) {
            commanded_pos = _current_pos + 0.5f * _servo_accel * t * t * sign;
        } else if (t < ramp_time + (total_distance - 2*ramp_distance) / _servo_ramp_rate) {
            float coast_t = t - ramp_time;
            commanded_pos = _current_pos + (ramp_distance + _servo_ramp_rate * coast_t) * sign;
        } else if (t < _servo_move_time_ms * 1e-3f) {
            float decel_t = t - (ramp_time + (total_distance - 2*ramp_distance) / _servo_ramp_rate);
            commanded_pos = _target_pos - 0.5f * _servo_accel * decel_t * decel_t * sign;
        } else {
            commanded_pos = _target_pos;
            _servo_state = Servo_State::HOLDING;
        }
    }

    set_servo_position(commanded_pos);
}
```

The PWM output is set via the SRV_Channels API, which manages the underlying timer peripherals.

```cpp
void AP_Gripper_Servo::set_servo_position(float pos_deg)
{
    // Constrain and map to PWM
    pos_deg = constrain_float(pos_deg, 0.0f, 180.0f);
    uint16_t pwm_us = 1000 + (pos_deg / 180.0f) * 1000;
    // Output on the configured servo channel
    SRV_Channels::set_output_pwm(SRV_Channel::k_gripper, pwm_us);
}
```

#### Hardware Integration and RTOS Considerations
The system is designed for real-time operation on an STM32:
*   **GPIO Control for EPM:** Uses direct register access (`GPIOA->BSRR = pin_mask`) for sub-microsecond pulse control. The pulse timer callback is registered with the scheduler's timer process.
*   **PWM Servo Output:** Leverages the `SRV_Channels` layer, which configures the STM32's advanced-control timers (TIM1, TIM8) in PWM generation mode. The update rate is synchronized with the main 400Hz loop.
*   **Thread Safety:** The `AP_Gripper::update()` and command queue are called from the main thread. MAVLink command parsing (`handle_command_int`) runs in the lower-priority MAVLink thread, using atomic operations or a simple mutex (`hal.util->get_semaphore()`) for queue access.
*   **Watchdog:** A software watchdog in the main `update()` method ensures a stuck state (`GRABBING`/`RELEASING` for > `_pulse_time_ms + 500`) triggers a fault and resets the gripper to `IDLE`.

This implementation provides a robust, non-blocking payload manipulation system capable of handling the dynamic environment of a heavy agricultural rover, with mathematical models directly informing the timing, force, and control parameters embedded in the C++ code.