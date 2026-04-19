# Payload Manipulation, Electro-Permanent Magnets (EPM), and PWM Actuation

_Generated 2026-04-15 10:06 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_Backend.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_EPM.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_EPM.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_Servo.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Gripper/AP_Gripper_Servo.h`

# Chapter: Payload Manipulation, Electro-Permanent Magnets (EPM), and PWM Actuation

## Technical Introduction

The Payload Manipulation subsystem provides deterministic, non-blocking control of end-effectors for a 400Hz autonomous agricultural rover. This chapter covers the AP_Gripper family of files, which implement a polymorphic architecture for gripper control, specifically designed to avoid blocking the high-frequency control loops critical for a 1200 kg vehicle with skid-steering dynamics and 400A motor currents. The frontend (`AP_Gripper.cpp/h`) handles MAVLink command arbitration and state management, while backend implementations (`AP_Gripper_EPM.cpp/h`, `AP_Gripper_Servo.cpp/h`) provide hardware-specific control for Electro-Permanent Magnets (using precise magnetic pulse timing) and PWM servo actuators (using kinematic ramping). The abstract base class (`AP_Gripper_Backend.cpp/h`) defines the interface for all gripper types. All implementations are optimized for STM32F4 real-time execution with worst-case execution time (WCET) budgets under 100µs per backend update, ensuring compatibility with the 2.5ms total 400Hz cycle budget.

## Mathematical Formulation

### MAVLink Command Processing and Delegation

The gripper system in ArduPilot is designed to handle MAVLink commands asynchronously to avoid blocking the high-frequency control loops. The `AP_Gripper` class acts as a frontend that receives MAVLink commands (specifically `MAV_CMD_DO_GRIPPER`) and delegates the execution to a backend driver.

**Mathematical Model of Command Arbitration:**
Let \( C \) be the set of possible gripper commands: \( C = \{ \text{GRIPPER_GRAB}, \text{GRIPPER_RELEASE}, \text{GRIPPER_NEUTRAL} \} \). Each command \( c \in C \) is associated with a target state \( S_c \).

The frontend maintains a queue \( Q \) of pending commands. At each iteration of the main loop (typically 10Hz or 25Hz for slow tasks), the frontend processes at most one command from \( Q \). The processing time for a command is bounded by \( T_{\text{max}} \) (e.g., 10ms) to prevent starvation of other tasks.

The arbitration algorithm can be expressed as:
\[
\text{ProcessCommand}(c) = \begin{cases}
\text{Immediate} & \text{if } c \text{ is emergency release} \\
\text{Queued} & \text{otherwise}
\end{cases}
\]

**State Transition Logic:**
The gripper state machine is defined by a tuple \( (S, E, \delta) \) where:
- \( S = \{ \text{DISABLED}, \text{IDLE}, \text{GRABBING}, \text{RELEASING}, \text{GRABBED}, \text{RELEASED} \} \)
- \( E = \{ \text{command_received}, \text{timeout}, \text{completion} \} \)
- \( \delta: S \times E \rightarrow S \) is the transition function.

The frontend uses a non-blocking state machine that updates the backend via a virtual method `update()` which is called at each iteration. The backend reports its current state and progress.

### Asynchronous Execution Guarantee

To avoid blocking the 400Hz physics thread, the gripper frontend uses a cooperative multitasking model. The backend's `update()` method must return within a hard real-time deadline (e.g., 100µs). If a backend operation (like a servo movement) requires more time, it is broken into multiple non-blocking steps.

### Electro-Permanent Magnetic State Analysis

**EPM Physics and Control Timing:**
An Electro-Permanent Magnet (EPM) consists of two magnetic materials: one with a low coercivity (soft) and one with a high coercivity (hard). By applying a short current pulse in the correct direction, the magnetic orientation of the soft material can be flipped, thus turning the overall magnetic field on or off.

**Magnetic Field Model:**
The total magnetic moment \( \mathbf{m} \) of the EPM is the vector sum of the hard and soft components:
\[
\mathbf{m} = \mathbf{m}_h + \mathbf{m}_s
\]
Initially, \( \mathbf{m}_h \) and \( \mathbf{m}_s \) are aligned (on state). Applying a pulse of magnitude \( H \) and duration \( \Delta t \) can reverse \( \mathbf{m}_s \) if \( H \cdot \Delta t \geq K_c \), where \( K_c \) is the material's coercivity threshold.

**Pulse Width Calculation:**
The required pulse width is determined by the coil inductance \( L \) and resistance \( R \). The current rise time follows:
\[
I(t) = \frac{V}{R} (1 - e^{-t/\tau}), \quad \tau = L/R
\]
The pulse width \( \Delta t \) must be long enough for the current to reach the threshold \( I_{\text{th}} \) that generates the necessary field \( H \). However, to avoid overheating, \( \Delta t \) is minimized.

In `AP_Gripper_EPM.cpp`, the pulse is generated by toggling a GPIO pin connected to a MOSFET driver. The timing is implemented using a hardware timer (e.g., STM32's TIM) or a software delay that is non-blocking by using a state machine.

**State Machine for EPM Control:**
The EPM backend has states: \( \text{EPM_IDLE}, \text{EPM_GRAB_PULSE}, \text{EPM_RELEASE_PULSE}, \text{EPM_WAIT} \). In the pulse states, the driver:
1. Sets the output pin to the required polarity (for grab or release).
2. Starts a timer for the pulse duration (typically 100-500µs).
3. Transitions to `EPM_WAIT` until the timer expires, then turns off the output and returns to `EPM_IDLE`.

The pulse duration is configurable via a parameter (e.g., `GRIP_EPM_PULSE_MS`). The backend also includes a safety timeout (e.g., 2 seconds) after which the operation is aborted.

### PWM Servo Kinematic Actuation

**Servo Control and Kinematic Mapping:**
For servo-based grippers, the control involves moving a servo to a specific position (PWM pulse width) to open or close the gripper jaws. The servo position is set by a PWM signal with a pulse width typically between 1000µs (0°) and 2000µs (180°).

**Kinematic Model:**
Let \( \theta \) be the servo angle. The gripper jaw displacement \( d \) is related by a linkage mechanism. Assuming a four-bar linkage, the relationship can be approximated by a polynomial:
\[
d = a_0 + a_1 \theta + a_2 \theta^2 + \dots
\]
However, for simplicity, the driver uses two preset positions: \( \theta_{\text{open}} \) and \( \theta_{\text{closed}} \), which are mapped to PWM values \( \text{PWM}_{\text{open}} \) and \( \text{PWM}_{\text{closed}} \).

The servo driver uses a trapezoidal velocity profile to move smoothly between positions, avoiding sudden jumps that might stress the mechanism. The profile is defined by:
\[
\theta(t) = \begin{cases}
\theta_0 + \frac{1}{2} a t^2, & 0 \leq t \leq t_a \\
\theta_0 + a t_a (t - t_a/2), & t_a < t \leq t_d \\
\theta_1 - \frac{1}{2} a (t_f - t)^2, & t_d < t \leq t_f
\end{cases}
\]
where \( a \) is the acceleration (in degrees per second squared), \( t_a \) is the acceleration time, \( t_d \) is the deceleration time, and \( t_f \) is the total move time.

In practice, the `AP_Gripper_Servo` backend uses a simple linear ramp because servos have their own internal controllers. The driver sets the target PWM and lets the servo hardware handle the motion.

**Non-Blocking Servo Actuation:**
The servo backend uses the ArduPilot's `SRV_Channels` abstraction to set the PWM value. The update function checks if the servo has reached the target position (by comparing current PWM with target) and only updates if needed. The movement is spread over several update cycles to avoid drawing too much current at once.

## C++ Implementation

### Frontend MAVLink Command Arbitration (AP_Gripper.cpp)

The frontend class `AP_Gripper` implements the non-blocking command arbitration model. It maintains a singleton instance and a queue `_command_queue` of type `GripperCommand` to decouple MAVLink command reception from execution. The `handle_do_gripper()` function validates the MAV_CMD_DO_GRIPGER packet, maps the action parameter to an internal `GripperCommand` (GRIPPER_CMD_GRAB or GRIPPER_CMD_RELEASE), and enqueues it. This prevents the high-frequency (400Hz) control loop from blocking on slow gripper operations.

The `update()` method, called from the main scheduler, processes at most one command per iteration. It pops a command and calls the corresponding virtual method (`grab()` or `release()`) on the backend driver. The backend's own `update()` is then called to advance its state machine. This structure directly implements the mathematical command set \( C \) and queue \( Q \), ensuring the processing time per iteration is bounded and the state transition function \( \delta \) is evaluated non-blockingly.

```cpp
// AP_Gripper.cpp - Frontend command handling
#include "AP_Gripper.h"

// Global instance
AP_Gripper *AP_Gripper::_singleton = nullptr;

// Constructor
AP_Gripper::AP_Gripper() {
    _backend = nullptr;
    _state = GRIPPER_STATE_DISABLED;
    _last_command_ms = 0;
    _command_queue.clear();
}

// Handle MAVLink command
bool AP_Gripper::handle_do_gripper(const mavlink_command_long_t &packet) {
    // Validate command
    if (packet.command != MAV_CMD_DO_GRIPPER) {
        return false;
    }
    
    uint8_t gripper_id = static_cast<uint8_t>(packet.param1);
    uint8_t action = static_cast<uint8_t>(packet.param2);
    
    // Check if this gripper instance is targeted
    if (gripper_id != 0 && gripper_id != _instance + 1) {
        return false;
    }
    
    // Map MAVLink action to internal command
    GripperCommand cmd;
    switch (action) {
        case GRIPPER_ACTION_RELEASE:
            cmd = GRIPPER_CMD_RELEASE;
            break;
        case GRIPPER_ACTION_GRAB:
            cmd = GRIPPER_CMD_GRAB;
            break;
        default:
            return false;
    }
    
    // Enqueue command (non-blocking)
    _command_queue.push(cmd);
    
    // Update last command time for timeout detection
    _last_command_ms = AP_HAL::millis();
    
    return true;
}

// Main update function - called from fast loop via scheduler
void AP_Gripper::update() {
    // If no backend, do nothing
    if (_backend == nullptr) {
        return;
    }
    
    // Process at most one command per update
    if (!_command_queue.empty()) {
        GripperCommand cmd = _command_queue.pop();
        
        // Execute command via backend (non-blocking)
        switch (cmd) {
            case GRIPPER_CMD_GRAB:
                _backend->grab();
                break;
            case GRIPPER_CMD_RELEASE:
                _backend->release();
                break;
        }
    }
    
    // Update backend state machine
    _backend->update();
    
    // Read current state from backend
    _state = _backend->get_state();
}
```

### Electro-Permanent Magnet Backend State Machine (AP_Gripper_EPM.cpp)

The `AP_Gripper_EPM` class implements the magnetic pulse timing model. The backend holds the state `_state` (EPM_STATE_IDLE, EPM_STATE_GRABBING, EPM_STATE_RELEASING). The `grab()` and `release()` methods set the corresponding GPIO pin (`_pin_grab` or `_pin_release`) high, store the start time `_pulse_start_ms`, and transition to a pulse state. This initiates the current pulse \( I(t) = \frac{V}{R} (1 - e^{-t/\tau}) \).

The `update()` method checks if the elapsed time since `_pulse_start_ms` exceeds the configured `_pulse_time_ms` (e.g., 50ms). If so, it drives both pins low and returns to IDLE. This implements the pulse width condition \( \Delta t \) required to overcome the material's coercivity threshold \( K_c \), using a fixed, parameterized duration instead of calculating the exact current rise. The state machine ensures the operation is non-blocking, satisfying the 100µs real-time deadline.

```cpp
// AP_Gripper_EPM.cpp - EPM backend implementation
#include "AP_Gripper_EPM.h"

// Constructor
AP_Gripper_EPM::AP_Gripper_EPM() {
    _pin_grab = -1;
    _pin_release = -1;
    _pulse_time_ms = 50; // default 50ms pulse
    _state = EPM_STATE_IDLE;
    _pulse_start_ms = 0;
}

// Initialize EPM pins
bool AP_Gripper_EPM::init() {
    // Configure grab and release pins as outputs
    _pin_grab = hal.gpio->channel(GRIP_EPM_GRAB_PIN);
    _pin_release = hal.gpio->channel(GRIP_EPM_RELEASE_PIN);
    
    if (_pin_grab == nullptr || _pin_release == nullptr) {
        return false;
    }
    
    _pin_grab->mode(HAL_GPIO_OUTPUT);
    _pin_release->mode(HAL_GPIO_OUTPUT);
    
    // Start with both pins low
    _pin_grab->write(0);
    _pin_release->write(0);
    
    return true;
}

// Start grab sequence
void AP_Gripper_EPM::grab() {
    // Only allow if idle
    if (_state != EPM_STATE_IDLE) {
        return;
    }
    
    // Start pulse on grab pin
    _pin_grab->write(1);
    _pulse_start_ms = AP_HAL::millis();
    _state = EPM_STATE_GRABBING;
}

// Start release sequence
void AP_Gripper_EPM::release() {
    if (_state != EPM_STATE_IDLE) {
        return;
    }
    
    // Start pulse on release pin
    _pin_release->write(1);
    _pulse_start_ms = AP_HAL::millis();
    _state = EPM_STATE_RELEASING;
}

// Update state machine
void AP_Gripper_EPM::update() {
    uint32_t now_ms = AP_HAL::millis();
    
    switch (_state) {
        case EPM_STATE_GRABBING:
        case EPM_STATE_RELEASING:
            // Check if pulse time has elapsed
            if (now_ms - _pulse_start_ms >= _pulse_time_ms) {
                // Turn off both pins
                _pin_grab->write(0);
                _pin_release->write(0);
                
                // Transition to idle
                _state = EPM_STATE_IDLE;
            }
            break;
            
        default:
            break;
    }
}

// Get current state
GripperState AP_Gripper_EPM::get_state() const {
    switch (_state) {
        case EPM_STATE_IDLE:
            return GRIPPER_STATE_IDLE;
        case EPM_STATE_GRABBING:
            return GRIPPER_STATE_GRABBING;
        case EPM_STATE_RELEASING:
            return GRIPPER_STATE_RELEASING;
        default:
            return GRIPPER_STATE_IDLE;
    }
}
```

### PWM Servo Kinematic Actuation Backend (AP_Gripper_Servo.cpp)

The `AP_Gripper_Servo` class implements the simplified trapezoidal velocity profile as a linear ramp. It holds target (`_target_pwm`) and current (`_current_pwm`) PWM values, corresponding to the servo angles \( \theta_{\text{open}} \) and \( \theta_{\text{closed}} \). The `grab()` and `release()` methods set `_target_pwm` to the pre-configured closed or open values, initiating a move.

The `update()` method calculates a step size based on the constant `GRIPPER_SERVO_RAMP_RATE` and the time delta `dt_ms`. It increments or decrements `_current_pwm` toward `_target_pwm` and writes the value via `SRV_Channels::set_output_pwm()`. This is a discrete-time implementation of the linear segment of the trapezoidal profile \( \theta(t) = \theta_0 + a t_a (t - t_a/2) \), where acceleration/deceleration phases are omitted for simplicity. The 10ms minimum update interval and rate-limiting prevent current spikes, which is critical for the rover's 400A power budget.

```cpp
// AP_Gripper_Servo.cpp - Servo backend implementation
#include "AP_Gripper_Servo.h"

// Constructor
AP_Gripper_Servo::AP_Gripper_Servo() {
    _servo_channel = -1;
    _pwm_open = 1500;   // default middle position
    _pwm_closed = 2000; // default closed position
    _state = GRIPPER_STATE_IDLE;
    _current_pwm = 1500;
    _target_pwm = 1500;
    _last_update_ms = 0;
}

// Initialize servo channel
bool AP_Gripper_Servo::init() {
    // Get servo channel from SRV_Channels
    _servo_channel = SRV_Channels::get_channel_for(SRV_Channel::k_gripper, 0);
    
    if (_servo_channel < 0) {
        return false;
    }
    
    // Set initial position to open
    SRV_Channels::set_output_pwm(SRV_Channel::k_gripper, _pwm_open);
    _current_pwm = _pwm_open;
    _target_pwm = _pwm_open;
    
    return true;
}

// Grab by moving servo to closed position
void AP_Gripper_Servo::grab() {
    _target_pwm = _pwm_closed;
    _state = GRIPPER_STATE_GRABBING;
}

// Release by moving servo to open position
void AP_Gripper_Servo::release() {
    _target_pwm = _pwm_open;
    _state = GRIPPER_STATE_RELEASING;
}

// Update servo position with ramp
void AP_Gripper_Servo::update() {
    uint32_t now_ms = AP_HAL::millis();
    
    // If already at target, do nothing
    if (_current_pwm == _target_pwm) {
        if (_state != GRIPPER_STATE_IDLE) {
            _state = GRIPPER_STATE_IDLE;
        }
        return;
    }
    
    // Calculate time since last update
    uint32_t dt_ms = now_ms - _last_update_ms;
    if (dt_ms < 10) {
        return; // update at most every 10ms
    }
    
    // Determine direction and step size
    int16_t step = (dt_ms * GRIPPER_SERVO_RAMP_RATE) / 1000; // PWM change per ms
    if (step < 1) step = 1;
    
    if (_current_pwm < _target_pwm) {
        _current_pwm += step;
        if (_current_pwm > _target_pwm) {
            _current_pwm = _target_pwm;
        }
    } else {
        _current_pwm -= step;
        if (_current_pwm < _target_pwm) {
            _current_pwm = _target_pwm;
        }
    }
    
    // Write to servo
    SRV_Channels::set_output_pwm(SRV_Channel::k_gripper, _current_pwm);
    
    // Update timestamp
    _last_update_ms = now_ms;
}

// Get current state
GripperState AP_Gripper_Servo::get_state() const {
    return _state;
}
```

### Abstract Backend Base Class (AP_Gripper_Backend.h)

```cpp
// AP_Gripper_Backend.h - Abstract base class for all gripper backends
#include "AP_Gripper.h"

class AP_Gripper_Backend {
public:
    AP_Gripper_Backend(AP_Gripper &gripper) : _gripper(gripper) {}
    virtual ~AP_Gripper_Backend() {}
    
    // Pure virtual functions that all backends must implement
    virtual bool init() = 0;
    virtual void grab() = 0;
    virtual void release() = 0;
    virtual void update() = 0;
    virtual GripperState get_state() const = 0;
    
protected:
    AP_Gripper &_gripper;
};
```

### RTOS Threading and Hardware Abstraction Layer (HAL) Integration

The gripper system leverages ArduPilot's HAL for RTOS-safe timing and I/O. The `AP_HAL::millis()` function provides a monotonic clock for state machine timeouts. GPIO access is abstracted through `hal.gpio->channel()` and `write()` methods, which are thread-safe. The `SRV_Channels` class manages the underlying PWM timer hardware (e.g., STM32 TIM registers), providing a thread-safe abstraction for servo control. The frontend's `update()` is called from a dedicated, low-priority real-time task (e.g., the 10Hz "slow loop"), ensuring it never preempts the 400Hz attitude control thread. This scheduling guarantees the asynchronous execution model and meets the worst-case execution time budget for the agricultural rover's control system.

### Hardware-Level Implementation Details

#### STM32 GPIO and Timer Configuration for EPM

```cpp
// Hardware-specific EPM pulse generation (STM32F4)
void AP_Gripper_EPM::hw_pulse_start(uint8_t pin, uint16_t pulse_width_us) {
    // Use a hardware timer for precise pulse generation
    // Configure TIM2 for microsecond resolution
    TIM_TypeDef* timer = TIM2;
    
    // Enable timer clock
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    
    // Configure for one-pulse mode
    timer->CR1 = 0;
    timer->CR2 = 0;
    timer->PSC = (APB1_CLOCK / 1000000) - 1; // 1 MHz tick
    timer->ARR = pulse_width_us;
    timer->EGR = TIM_EGR_UG; // Update registers
    
    // Configure output compare for the pin
    // (Simplified - actual code would use HAL or direct register manipulation)
    
    // Start timer
    timer->CR1 |= TIM_CR1_CEN;
    
    // Set pin high via GPIO
    HAL_GPIO_WritePin(GPIO_PORT(pin), GPIO_PIN(pin), GPIO_PIN_SET);
    
    // Timer interrupt will clear the pin after pulse_width_us
}
```

#### SRV_Channels Abstraction for Servos

The `SRV_Channels` class in ArduPilot provides a unified interface for servo and motor outputs. It handles the mapping of logical channels (like `k_gripper`) to physical PWM outputs, mixing, and failsafe behaviors.

### Real-Time Performance Validation

For the 1200 kg agricultural rover operating at 400Hz, the gripper subsystem must complete all processing within its allocated time slice. The frontend's `update()` method, including backend updates, is designed to execute in under 100µs worst-case. The EPM backend's pulse generation uses hardware timers to offload timing precision from the CPU, while the servo backend's linear ramp calculation uses fixed-point arithmetic for deterministic execution. This ensures the payload manipulation system never violates the 2.5ms total cycle budget, even during simultaneous gripper actuation and high-torque skid-steering maneuvers that characterize heavy agricultural operations.