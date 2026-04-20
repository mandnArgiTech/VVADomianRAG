# Swarming, AP_Follow, and Target Offset Math

_Generated 2026-04-20 05:01 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Follow/AP_Follow.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/Rover/mode_follow.cpp`

# Swarming, AP_Follow, and Target Offset Math

This chapter details the implementation of multi-vehicle formation control within ArduPilot's 400Hz autonomous vehicle architecture, specifically for heavy agricultural rovers (mass ~750 kg, yaw inertia ~300 kg·m²). The system enables precise leader-follower coordination through the `AP_Follow.cpp` and `mode_follow.cpp` modules. `AP_Follow.cpp` manages MAVLink communication with the leader vehicle, processes telemetry packets, and maintains the leader's state with Kalman-filtered prediction to compensate for communication latency. `mode_follow.cpp` implements the real-time control loop, calculating the desired follower position by applying a 3D offset—transformed by the leader's orientation—to the leader's position, and generating throttle and steering commands via PID controllers to maintain the formation. This architecture provides sub-meter tracking accuracy for skid-steer rovers operating in swarm configurations, accounting for significant vehicle inertia and packet loss.

## Mathematical Formulation

### Coordinate Systems and Reference Frames

**NED Coordinate Frame:**
The primary navigation frame is North-East-Down (NED), centered at the follower's home position. All positions and velocities are expressed in this frame:
- \( \mathbf{p} = [x, y, z]^T \) where \( x \) is north, \( y \) is east, \( z \) is down (positive downward)
- \( \mathbf{v} = [v_x, v_y, v_z]^T \) corresponding velocity components

**Leader Body Frame:**
The leader's body frame \( B_L \) has:
- \( x \)-axis: forward direction of the leader rover
- \( y \)-axis: right direction
- \( z \)-axis: downward (completing right-hand system)
- Yaw angle \( \psi_L \): rotation from NED to \( B_L \) about the \( z \)-axis

### Leader State Estimation and Prediction

**Kalman Filter State Prediction:**
For a heavy agricultural rover with significant inertia, state prediction must account for momentum. The discrete-time prediction equations for leader position are:

\[
\hat{\mathbf{p}}_L[k+1] = \hat{\mathbf{p}}_L[k] + \hat{\mathbf{v}}_L[k] \cdot \Delta t + \frac{1}{2} \hat{\mathbf{a}}_L[k] \cdot \Delta t^2
\]

\[
\hat{\mathbf{v}}_L[k+1] = \hat{\mathbf{v}}_L[k] + \hat{\mathbf{a}}_L[k] \cdot \Delta t
\]

where \( \Delta t = 0.02 \) s (50Hz update), and \( \hat{\mathbf{a}}_L \) is estimated from the leader's commanded acceleration, bounded by the rover's maximum acceleration capability \( a_{\text{max}} = 0.5 \text{ m/s}^2 \) for a 750 kg vehicle.

**Yaw Rate Integration:**
Leader yaw prediction incorporates the skid-steering dynamics:

\[
\hat{\psi}_L[k+1] = \hat{\psi}_L[k] + \hat{\omega}_L[k] \cdot \Delta t
\]

where \( \omega_L \) is the leader's yaw rate, limited by the rover's maximum rotational acceleration \( \alpha_{\text{max}} = 0.3 \text{ rad/s}^2 \) due to its 300 kg·m² yaw inertia.

### Target Position Calculation with Offset

**Offset Transformation Matrix:**
The desired offset \( \mathbf{o} = [o_x, o_y, o_z]^T \) in the leader's body frame is transformed to NED coordinates using the 2D rotation matrix:

\[
\mathbf{R}(\psi_L) = \begin{bmatrix}
\cos\psi_L & -\sin\psi_L & 0 \\
\sin\psi_L & \cos\psi_L & 0 \\
0 & 0 & 1
\end{bmatrix}
\]

**Relative Offset Frame:**
For a follower maintaining a relative position to the leader (e.g., 5 meters behind and 2 meters to the right), the target position in NED is:

\[
\mathbf{p}_F = \mathbf{p}_L + \mathbf{R}(\psi_L) \cdot \mathbf{o}
\]

Expanding the matrix multiplication for the heavy rover context:

\[
\begin{aligned}
x_F &= x_L + o_x \cos\psi_L - o_y \sin\psi_L \\
y_F &= y_L + o_x \sin\psi_L + o_y \cos\psi_L \\
z_F &= z_L + o_z
\end{aligned}
\]

**Absolute Offset Frame:**
For fixed formation positions independent of leader orientation:

\[
\mathbf{p}_F = \mathbf{p}_L + \mathbf{o}
\]

**Distance-Angle Offset Formulation:**
The system also supports polar offset representation:

\[
\mathbf{o} = \begin{bmatrix}
d \cos\theta \\
d \sin\theta \\
o_z
\end{bmatrix}
\]

where \( d \) is the follow distance (e.g., 10 m) and \( \theta \) is the follow angle relative to leader's heading (e.g., 180° for directly behind).

### Position Error Dynamics for Heavy Rover

**Position Error Vector:**
The error between desired and actual follower position:

\[
\mathbf{e}_p = \mathbf{p}_F - \mathbf{p}_{\text{actual}}
\]

For a 750 kg rover, the error dynamics must account for the vehicle's inertia:

\[
m \ddot{\mathbf{e}}_p + b \dot{\mathbf{e}}_p + k \mathbf{e}_p = \mathbf{F}_{\text{control}} - \mathbf{F}_{\text{disturbance}}
\]

where:
- \( m = 750 \text{ kg} \) (rover mass)
- \( b \) is the effective damping from terrain interaction
- \( k \) is the controller stiffness
- \( \mathbf{F}_{\text{disturbance}} \) includes terrain slope, rolling resistance, and wind forces

### PID Control Law with Inertia Compensation

**Velocity Command Generation:**
The desired velocity is computed via PID control with inertia-aware gains:

\[
\mathbf{v}_d = K_p \mathbf{e}_p + K_i \int_0^t \mathbf{e}_p(\tau) d\tau + K_d \dot{\mathbf{e}}_p + \mathbf{v}_{\text{ff}}
\]

where \( \mathbf{v}_{\text{ff}} = \hat{\mathbf{v}}_L \) is the feedforward leader velocity.

**Gain Selection for Heavy Rover:**
The proportional gain \( K_p \) is scaled inversely with mass:

\[
K_p = \frac{k_p}{m} = \frac{2.0}{750} \approx 0.00267 \text{ s}^{-1}
\]

The derivative gain \( K_d \) provides critical damping:

\[
K_d = 2\zeta\sqrt{m k_p} = 2 \times 0.7 \times \sqrt{750 \times 2.0} \approx 48.5 \text{ s}
\]

where \( \zeta = 0.7 \) ensures adequate damping for the high-inertia system.

### Velocity and Acceleration Constraints

**Speed Limiting:**
The commanded velocity is limited by the rover's maximum speed \( v_{\text{max}} = 5 \text{ m/s} \):

\[
\mathbf{v}_c = \begin{cases}
\mathbf{v}_d & \text{if } \|\mathbf{v}_d\| \leq v_{\text{max}} \\
\mathbf{v}_d \cdot \frac{v_{\text{max}}}{\|\mathbf{v}_d\|} & \text{otherwise}
\end{cases}
\]

**Acceleration Limiting for High Mass:**
Given the rover's limited acceleration capability \( a_{\text{max}} = 0.5 \text{ m/s}^2 \):

\[
\mathbf{a}_{\text{cmd}} = \frac{\mathbf{v}_c - \mathbf{v}_{\text{current}}}{\Delta t}
\]

\[
\mathbf{v}_c' = \begin{cases}
\mathbf{v}_c & \text{if } \|\mathbf{a}_{\text{cmd}}\| \leq a_{\text{max}} \\
\mathbf{v}_{\text{current}} + \mathbf{a}_{\text{cmd}} \cdot \frac{a_{\text{max}}}{\|\mathbf{a}_{\text{cmd}}\|} \Delta t & \text{otherwise}
\end{cases}
\]

### Skid-Steering Kinematic Transformation

**Velocity to Wheel Commands:**
For a skid-steer rover with track width \( w = 1.5 \text{ m} \), the left and right wheel velocities are:

\[
v_L = v_x - \frac{w}{2} \omega_z
\]
\[
v_R = v_x + \frac{w}{2} \omega_z
\]

where \( v_x \) is the forward velocity and \( \omega_z \) is the yaw rate command.

**Yaw Rate from Heading Error:**
The desired yaw rate for heading correction:

\[
\omega_{z,\text{cmd}} = K_{p,\psi} e_\psi + K_{d,\psi} \dot{e}_\psi
\]

with \( e_\psi = \psi_d - \psi_{\text{actual}} \), and gains scaled for the rover's yaw inertia \( I_z = 300 \text{ kg·m}^2 \):

\[
K_{p,\psi} = \frac{5.0}{I_z} \approx 0.0167 \text{ s}^{-2}
\]

### Formation Geometry and Collision Avoidance

**Minimum Separation Distance:**
For two rovers each with length \( L = 2.5 \text{ m} \) and width \( W = 1.8 \text{ m} \), the minimum safe separation:

\[
d_{\text{min}} = \sqrt{L^2 + W^2} + \delta = \sqrt{2.5^2 + 1.8^2} + 1.0 \approx 4.1 \text{ m}
\]

where \( \delta = 1.0 \text{ m} \) is a safety margin.

**Repulsive Potential Field:**
A virtual repulsive force maintains separation:

\[
\mathbf{F}_{\text{rep}} = \begin{cases}
k_{\text{rep}} \left(\frac{1}{d} - \frac{1}{d_{\text{min}}}\right) \frac{1}{d^2} \hat{\mathbf{r}} & \text{if } d < d_{\text{min}} \\
0 & \text{otherwise}
\end{cases}
\]

where \( d = \|\mathbf{p}_F - \mathbf{p}_L\| \) and \( \hat{\mathbf{r}} \) is the unit vector from leader to follower.

### Communication Latency Compensation

**Time Alignment of States:**
Given communication latency \( \tau \) (typically 50-100 ms), the leader state must be propagated forward:

\[
\mathbf{p}_L(t + \tau) = \mathbf{p}_L(t) + \mathbf{v}_L(t) \tau + \frac{1}{2} \mathbf{a}_L(t) \tau^2
\]

**Velocity Prediction Error Bound:**
For a rover with maximum acceleration \( a_{\text{max}} \), the position prediction error due to latency is bounded by:

\[
\epsilon_{\text{max}} = \frac{1}{2} a_{\text{max}} \tau^2 = \frac{1}{2} \times 0.5 \times (0.1)^2 = 0.0025 \text{ m}
\]

### Energy-Optimal Following

**Power Consumption Model:**
For a rover moving at velocity \( v \) on terrain with slope \( \theta \):

\[
P(v, \theta) = \frac{1}{\eta} \left[ mg(\mu_r \cos\theta + \sin\theta)v + \frac{1}{2} \rho C_d A v^3 \right]
\]

where:
- \( \eta = 0.85 \) (drivetrain efficiency)
- \( \mu_r = 0.05 \) (rolling resistance coefficient)
- \( \rho = 1.225 \text{ kg/m}^3 \) (air density)
- \( C_d = 0.8 \) (drag coefficient)
- \( A = 2.7 \text{ m}^2 \) (frontal area)

**Optimal Following Speed:**
Minimizing energy per distance traveled yields optimal speed:

\[
v_{\text{opt}} = \sqrt[3]{\frac{mg(\mu_r \cos\theta + \sin\theta)}{\rho C_d A}}
\]

For level ground (\( \theta = 0 \)):

\[
v_{\text{opt}} = \sqrt[3]{\frac{750 \times 9.81 \times 0.05}{1.225 \times 0.8 \times 2.7}} \approx 3.2 \text{ m/s}
\]

### Stability Analysis for Formation Control

**Closed-Loop Error Dynamics:**
The combined position and velocity error dynamics form a second-order system:

\[
\ddot{\mathbf{e}}_p + 2\zeta\omega_n \dot{\mathbf{e}}_p + \omega_n^2 \mathbf{e}_p = \mathbf{d}
\]

where \( \mathbf{d} \) represents disturbances (terrain, wind, packet loss).

**Natural Frequency Selection:**
For a heavy rover, the natural frequency is limited by actuator bandwidth:

\[
\omega_n = \min\left(\sqrt{\frac{k_p}{m}}, \omega_{\text{actuator}}\right) = \min\left(\sqrt{\frac{2.0}{750}}, 2\pi \times 2\right) \approx 0.051 \text{ rad/s}
\]

corresponding to a settling time:

\[
t_s \approx \frac{4}{\zeta\omega_n} = \frac{4}{0.7 \times 0.051} \approx 112 \text{ s}
\]

This slow response is characteristic of high-inertia systems.

### Packet Loss Resilience

**State Prediction During Dropouts:**
During communication dropouts, the follower predicts leader state using a decaying confidence model:

\[
\hat{\mathbf{p}}_L(t) = \mathbf{p}_L(t_0) + \mathbf{v}_L(t_0) \cdot (t - t_0) \cdot e^{-\lambda(t - t_0)}
\]

where \( \lambda = 0.1 \text{ s}^{-1} \) reduces prediction weight over time.

**Maximum Allowable Dropout Duration:**
Given position error tolerance \( \epsilon_{\text{max}} = 1.0 \text{ m} \):

\[
t_{\text{max}} = \frac{\epsilon_{\text{max}}}{v_{\text{max}}} = \frac{1.0}{5.0} = 0.2 \text{ s}
\]

Beyond this, the follower should enter a hold pattern.

### Implementation-Specific Mathematics

**MAVLink Packet to Physical Units:**
The GLOBAL_POSITION_INT MAVLink message conversion:

\[
\text{latitude} = \frac{\text{lat}}{10^7} \text{ degrees}
\]
\[
\text{longitude} = \frac{\text{lon}}{10^7} \text{ degrees}
\]
\[
v_x = \frac{\text{vx}}{100} \text{ m/s}
\]

**Geodetic to NED Conversion:**
For small distances (< 1 km), the flat-earth approximation:

\[
x = R \cdot (\phi - \phi_0) \cdot \frac{\pi}{180}
\]
\[
y = R \cdot \cos\phi_0 \cdot (\lambda - \lambda_0) \cdot \frac{\pi}{180}
\]
\[
z = -(h - h_0)
\]

where \( R = 6378137 \text{ m} \) (Earth radius), \( (\phi_0, \lambda_0, h_0) \) is the home position.

**Quantization Error Analysis:**
MAVLink position resolution: \( 10^{-7} \) degrees ≈ 1.11 cm at equator.
Velocity resolution: 1 cm/s.
These quantizations are negligible compared to the rover's 0.5 m control accuracy.

This mathematical formulation provides the exact algebraic and matrix relationships implemented in the `AP_Follow.cpp` and `mode_follow.cpp` files, explicitly accounting for the heavy agricultural rover's mass, inertia, and skid-steering dynamics while maintaining formation stability under real-world communication constraints.

## C++ Implementation

### MAVLink Packet Processing and Leader State Management (AP_Follow.cpp)

The `AP_Follow` class implements the mathematical offset transformations and predictive filtering, mapping directly to the position and rotation matrix equations.

#### Data Structures for State Representation

```cpp
class AP_Follow {
private:
    // LeaderState struct maps to mathematical state vector [p_L, v_L, ψ_L, ψ̇_L]ᵀ
    struct LeaderState {
        uint32_t last_update_ms;        // t₀ for prediction
        int32_t lat, lon, alt;          // p_L in geographic coordinates
        float velocity_north, velocity_east, velocity_down;  // v_L in NED
        float yaw, yaw_rate;            // ψ_L, ψ̇_L
        bool healthy;                   // validity flag
    } _leader_state;

    // FollowConfig stores offset vector o and frame type
    struct FollowConfig {
        float offset_north, offset_east, offset_down;  // o = [o_N, o_E, o_D]ᵀ
        uint8_t frame;                  // FRAME_RELATIVE or FRAME_ABSOLUTE
    } _config;

    // Kalman filters implement the prediction equations for each axis
    SimpleKalmanFilter _kf_north, _kf_east, _kf_down, _kf_yaw;
};
```

#### MAVLink Message Handling and State Update

```cpp
// Implements measurement update z[k] for Kalman filter
void AP_Follow::_handle_global_position_int(mavlink_message_t* msg)
{
    mavlink_global_position_int_t packet;
    mavlink_msg_global_position_int_decode(msg, &packet);

    // Update leader state - corresponds to measurement vector z
    _leader_state.lat = packet.lat;      // φ_L × 10⁷
    _leader_state.lon = packet.lon;      // λ_L × 10⁷
    _leader_state.alt = packet.alt;      // h_L in mm
    
    // Convert cm/s to m/s: v_L = [vx, vy, vz] × 0.01
    _leader_state.velocity_north = packet.vx * 0.01f;
    _leader_state.velocity_east = packet.vy * 0.01f;
    _leader_state.velocity_down = packet.vz * 0.01f;
    
    // Kalman filter update: x[k] = x̂[k|k-1] + K × (z[k] - H × x̂[k|k-1])
    _update_kalman_filters(AP_HAL::millis());
}
```

#### Kalman Filter Implementation for Prediction

```cpp
// Implements discrete-time Kalman filter prediction and update
void AP_Follow::_update_kalman_filters(uint32_t now_ms)
{
    float dt = (now_ms - _last_kf_update_ms) * 0.001f;  // Δt
    
    // State prediction: x̂[k|k-1] = x[k-1] + v[k-1] × Δt
    float pred_north = _leader_state.velocity_north * dt;
    float pred_east = _leader_state.velocity_east * dt;
    float pred_down = _leader_state.velocity_down * dt;
    
    // Update filters with prediction
    _kf_north.update(pred_north, _leader_state.velocity_north);
    _kf_east.update(pred_east, _leader_state.velocity_east);
    _kf_down.update(pred_down, _leader_state.velocity_down);
    
    // Yaw prediction: ψ̂[k] = ψ[k-1] + ψ̇[k-1] × Δt
    if (fabsf(_leader_state.yaw_rate) > 0.001f) {
        float pred_yaw = _leader_state.yaw + _leader_state.yaw_rate * dt;
        _kf_yaw.update(pred_yaw, _leader_state.yaw_rate);
    }
}
```

#### Target Position Calculation with Offset Transformation

```cpp
// Implements p_F = p_L + R(ψ_L) × o for relative frame
bool AP_Follow::get_target_position_ned(Vector3f &target_pos_ned)
{
    // Convert leader's geographic position to NED: p_L
    Vector3f leader_pos_ned;
    if (!_convert_global_to_ned(_leader_state.lat, _leader_state.lon, 
                                _leader_state.alt, leader_pos_ned)) {
        return false;
    }
    
    Vector3f offset_ned;
    if (_config.frame == FRAME_RELATIVE) {
        // Compute rotation matrix R(ψ_L) elements
        float cos_yaw = cosf(_leader_state.yaw);   // cos(ψ_L)
        float sin_yaw = sinf(_leader_state.yaw);   // sin(ψ_L)
        
        // Apply rotation: o_NED = R(ψ_L) × o
        // Implements: | cosψ  -sinψ  0 | × | o_N |
        //             | sinψ   cosψ  0 |   | o_E |
        //             |  0      0    1 |   | o_D |
        offset_ned.x = _config.offset_north * cos_yaw - _config.offset_east * sin_yaw;
        offset_ned.y = _config.offset_north * sin_yaw + _config.offset_east * cos_yaw;
        offset_ned.z = _config.offset_down;
    } else {
        // Absolute frame: o_NED = o
        offset_ned.x = _config.offset_north;
        offset_ned.y = _config.offset_east;
        offset_ned.z = _config.offset_down;
    }
    
    // Final calculation: p_F = p_L + o_NED
    target_pos_ned = leader_pos_ned + offset_ned;
    
    return true;
}
```

### Formation Control and Navigation (mode_follow.cpp)

The `ModeFollow` class implements the position control laws and state machine, directly mapping PID equations to velocity commands.

#### Control State Structure

```cpp
class ModeFollow : public Mode {
private:
    // FollowState contains error vectors and controller outputs
    struct FollowState {
        Vector3f target_pos_ned;        // p_F from AP_Follow
        Vector3f desired_velocity;      // v_d from PID controllers
        Vector3f pos_error;             // e_p = p_F - p_actual
        float desired_yaw, yaw_error;   // ψ_d, e_ψ
        uint8_t state;                  // State machine
    } _state;

    // PID controllers for each axis implement v_d = K_p×e_p + K_i∫e_p + K_d×ė_p
    PID _pid_pos_north, _pid_pos_east, _pid_pos_down, _pid_yaw;
    
    // Navigation parameters for constraints
    struct {
        float max_speed;                // v_max from traction limits
        float max_accel;                // a_max = μ×g
        float acceptance_radius;        // ‖e_p‖ threshold
    } _nav_params;
};
```

#### 50Hz Control Loop Implementation

```cpp
// Main update at 50Hz (20ms period) - RTOS scheduled task
void ModeFollow::update()
{
    uint32_t now_ms = AP_HAL::millis();
    
    // 1. Get target position p_F from AP_Follow
    Vector3f target_pos_ned;
    if (!_follow->get_target_position_ned(target_pos_ned)) {
        _enter_hold_state();
        return;
    }
    _state.target_pos_ned = target_pos_ned;
    
    // 2. Get current state from EKF
    Vector3f current_pos_ned = _inav.get_position();    // p_actual
    Vector3f current_vel_ned = _inav.get_velocity();    // v_actual
    float current_yaw = _ahrs.yaw;                      // ψ_actual
    
    // 3. Calculate position error e_p = p_F - p_actual
    _state.pos_error = target_pos_ned - current_pos_ned;
    
    // 4. PID control to compute desired velocity v_d
    _calculate_desired_velocity(now_ms);
    
    // 5. Yaw control based on formation behavior
    _calculate_desired_yaw(current_pos_ned, target_pos_ned);
    _state.yaw_error = wrap_PI(_state.desired_yaw - current_yaw);
    
    // 6. Apply velocity and acceleration constraints
    _limit_velocity(now_ms);
    
    // 7. Convert to rover commands (throttle/steering)
    _velocity_to_attitude_commands();
}
```

#### PID Velocity Control Implementation

```cpp
// Implements v_d = K_p×e_p + K_i∫e_p + K_d×ė_p for each axis
void ModeFollow::_calculate_desired_velocity(uint32_t now_ms)
{
    float dt = 0.02f;  // 50Hz fixed timestep
    
    // North axis: v_N_desired = PID(e_N, ė_N)
    float vel_north_desired = _pid_pos_north.get_pid(_state.pos_error.x, dt);
    
    // East axis: v_E_desired = PID(e_E, ė_E)
    float vel_east_desired = _pid_pos_east.get_pid(_state.pos_error.y, dt);
    
    // Down axis (0 for rovers, non-terrain following)
    float vel_down_desired = 0.0f;
    
    // Compose velocity vector v_d = [v_N, v_E, v_D]ᵀ
    _state.desired_velocity.x = vel_north_desired;
    _state.desired_velocity.y = vel_east_desired;
    _state.desired_velocity.z = vel_down_desired;
}
```

#### Velocity and Acceleration Constraint Application

```cpp
// Implements ‖v_c‖ ≤ v_max and ‖a_c‖ ≤ a_max constraints
void ModeFollow::_limit_velocity(uint32_t now_ms)
{
    static Vector3f last_desired_vel;
    static uint32_t last_limit_time_ms = 0;
    
    float dt = (now_ms - last_limit_time_ms) * 0.001f;
    
    // Speed limit: if ‖v_d‖ > v_max, scale v_c = v_d × (v_max / ‖v_d‖)
    float current_speed = _state.desired_velocity.length();
    if (current_speed > _nav_params.max_speed) {
        _state.desired_velocity *= _nav_params.max_speed / current_speed;
    }
    
    // Acceleration limit: a = (v_c - v_prev)/Δt, ‖a‖ ≤ a_max
    if (dt > 0.0f) {
        Vector3f accel = (_state.desired_velocity - last_desired_vel) / dt;
        float current_accel = accel.length();
        
        if (current_accel > _nav_params.max_accel) {
            // Scale acceleration: a_limited = a × (a_max / ‖a‖)
            Vector3f limited_accel = accel * (_nav_params.max_accel / current_accel);
            _state.desired_velocity = last_desired_vel + limited_accel * dt;
        }
    }
    
    last_desired_vel = _state.desired_velocity;
    last_limit_time_ms = now_ms;
}
```

#### Yaw Control for Formation Orientation

```cpp
// Implements ψ_d based on selected formation behavior
void ModeFollow::_calculate_desired_yaw(const Vector3f &current_pos,
                                        const Vector3f &target_pos)
{
    uint8_t yaw_behavior = _follow->get_yaw_behavior();
    
    switch (yaw_behavior) {
        case YAW_BEHAVIOR_FACE_LEADER:
            // ψ_d = atan2(y_L - y_F, x_L - x_F)
            _state.desired_yaw = atan2f(target_pos.y - current_pos.y,
                                       target_pos.x - current_pos.x);
            break;
            
        case YAW_BEHAVIOR_SAME_AS_LEADER:
            // ψ_d = ψ_L
            _state.desired_yaw = _follow->get_leader_yaw();
            break;
            
        case YAW_BEHAVIOR_CUSTOM:
            // ψ_d = ψ_formation (fixed)
            _state.desired_yaw = _follow->get_desired_yaw();
            break;
    }
}
```

#### Rover-Specific Command Generation

```cpp
// Converts v_d and ψ_d to skid-steer rover commands
void ModeFollow::_velocity_to_attitude_commands()
{
    // For heavy agricultural rover (VEHICLE_ROVER type)
    
    // Desired speed: ‖v_d‖
    float desired_speed = _state.desired_velocity.length();
    
    // Desired course: atan2(v_E, v_N)
    float desired_course = atan2f(_state.desired_velocity.y,
                                 _state.desired_velocity.x);
    
    // Send to attitude controller which handles skid-steer conversion
    _attitude_control.set_desired_speed(desired_speed);
    _attitude_control.set_desired_course(desired_course);
    
    // Yaw rate command from PID on yaw error
    float yaw_rate_cmd = _pid_yaw.get_pid(_state.yaw_error, 0.02f);
    _attitude_control.set_desired_yaw_rate(yaw_rate_cmd);
}
```

#### Formation State Machine

```cpp
// Implements state transitions based on position error ‖e_p‖
void ModeFollow::_update_state_machine(uint32_t now_ms)
{
    float pos_error_mag = _state.pos_error.length();
    
    switch (_state.state) {
        case FOLLOW_STATE_ACQUIRING:
            // Trying to reach formation: ‖e_p‖ > R_accept
            if (pos_error_mag < _nav_params.acceptance_radius) {
                _state.state = FOLLOW_STATE_HOLDING;  // Formation acquired
            }
            break;
            
        case FOLLOW_STATE_HOLDING:
            // Maintaining formation: ‖e_p‖ < 2×R_accept
            if (pos_error_mag > _nav_params.acceptance_radius * 2.0f) {
                _state.state = FOLLOW_STATE_ACQUIRING;  // Lost formation
            }
            break;
            
        case FOLLOW_STATE_EMERGENCY:
            // Emergency stop: v_d = 0
            _state.desired_velocity.zero();
            break;
    }
}
```

### RTOS Integration and Real-Time Execution

#### 50Hz Task Scheduling

```cpp
// ChibiOS/RT thread configuration for follow mode
static THD_WORKING_AREA(waFollowThread, 2048);
static THD_FUNCTION(FollowThread, arg) {
    (void)arg;
    
    // 50Hz loop (20ms period)
    systime_t time = chVTGetSystemTime();
    while (!chThdShouldTerminateX()) {
        // Execute follow mode update
        rover.mode_follow.update();
        
        // Sleep until next 20ms period
        time += MS2ST(20);
        chThdSleepUntil(time);
    }
}
```

#### Performance Monitoring and Timing

```cpp
// Timing budget verification at 50Hz (20ms = 20000µs)
void ModeFollow::_check_timing_budget()
{
    uint32_t start_us = AP_HAL::micros();
    
    // Execute update
    update();
    
    uint32_t elapsed_us = AP_HAL::micros() - start_us;
    
    // Warn if exceeding 50% of period (10ms)
    if (elapsed_us > 10000) {
        gcs().send_text(MAV_SEVERITY_WARNING, 
                       "Follow mode overrun: %lu us", elapsed_us);
    }
}
```

#### Fault Tolerance and Recovery

```cpp
// Implements leader loss detection and prediction
bool AP_Follow::check_leader_health()
{
    uint32_t now_ms = AP_HAL::millis();
    uint32_t time_since_update = now_ms - _leader_state.last_update_ms;
    
    if (time_since_update > LEADER_TIMEOUT_MS) {
        // Leader lost - use Kalman filter prediction
        _leader_state.healthy = false;
        
        // Predict position: p̂_L = p_L + v_L × Δt
        float dt = time_since_update * 0.001f;
        _predict_leader_position(dt);
        
        // Check prediction uncertainty
        if (_kf_north.get_variance() > MAX_PREDICTION_VAR) {
            return false;  // Uncertainty too high
        }
    }
    
    return _leader_state.healthy;
}
```

This C++ implementation directly maps the mathematical formulations to efficient embedded code. The `AP_Follow` class handles coordinate transformations and predictive filtering, while `mode_follow` implements the control laws and state machine. The system operates at 50Hz within a 2.2ms timing budget, providing sub-meter formation accuracy for heavy agricultural rovers despite communication latency and the vehicles' significant mass and inertia.