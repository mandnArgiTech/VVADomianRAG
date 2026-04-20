# Software-In-The-Loop (SITL), Physics Models, and JSON Backends

_Generated 2026-04-20 03:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/SITL/SITL.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/SITL/SIM_Rover.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/SITL/SIM_Multicopter.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/SITL/SIM_Plane.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_SITL/HAL_SITL_Class.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_SITL/SITL_State.cpp`

# Software-In-The-Loop (SITL), Physics Models, and JSON Backends

## Technical Introduction

The ArduPilot SITL architecture provides a high-fidelity simulation environment for testing autonomous vehicle algorithms without hardware. Six core files implement this system: `SITL.cpp` orchestrates the main simulation loop and JSON/TCP communication with external physics engines like Gazebo and AirSim. `SIM_Rover.cpp` implements skid-steer kinematics `V_left = (2V - ω × track_width)/(2 × wheel_radius)` and Dugoff's tire model `F_x = μ × F_z × (1 - exp(-κ/s)) × tanh(5κ)` for heavy agricultural rovers (mass: 750 kg, inertia: 300 kg·m²). `SIM_Multicopter.cpp` and `SIM_Plane.cpp` provide comparative vehicle models with Newton-Euler dynamics `m × dv/dt = Σ T_i × R_b²w × e_z - m × g × e_z - D × v`. `HAL_SITL_Class.cpp` provides hardware abstraction layer emulation, mapping simulation states to ArduPilot's hardware interface. `SITL_State.cpp` implements mathematical sensor noise models `a_measured = a_true + b_a + η_a + s_a × a_true` and GPS glitch injection `pos_measured += Δpos_glitch × exp(-(t - t_glitch)²/(2τ²))`. Together, these files enable deterministic 400Hz simulation with realistic sensor errors, vehicle dynamics, and external physics engine integration through JSON/TCP protocols.

## Mathematical Formulation

### Kinematic Emulation Formulation

#### Rover Dynamics Model

**Skid-Steer Kinematics for Heavy Agricultural Rover:**
```
// Differential drive equations for 750 kg rover with track_width = 1.5m, wheel_radius = 0.4m
V_left = (2V - ω × track_width) / (2 × wheel_radius)
V_right = (2V + ω × track_width) / (2 × wheel_radius)

where: V = forward velocity (m/s) - typically 0-2 m/s for agricultural operations
       ω = yaw rate (rad/s) - limited by max angular acceleration α_max = τ_max/I_z = 5 rad/s²
       track_width = 1.2-1.8m (distance between wheel centers)
       wheel_radius = 0.3-0.5m (typical agricultural tire)

// Inverse kinematics for control:
V = (V_left × wheel_radius + V_right × wheel_radius) / 2
ω = (V_right × wheel_radius - V_left × wheel_radius) / track_width
```

**Friction Model (Dugoff's Tire Model) for Agricultural Terrain:**
```
// Longitudinal force with soil compaction effects
F_x = μ × F_z × (1 - exp(-κ/s)) × tanh(5κ) × C_soil
where: μ = friction coefficient (0.3-0.8 for agricultural terrain)
       F_z = vertical load = m × g / 2 = (750 × 9.81)/2 = 3678.75 N per wheel
       κ = longitudinal slip ratio = (ω × r - V)/max(|ω × r|, |V|, 0.1)
       s = saturation factor = 0.3 for loose soil
       C_soil = soil compaction factor = 1.0 - 0.2 × (moisture_content - 0.3)

// Lateral force with skid-steer slip angle
F_y = μ × F_z × (1 - exp(-α/s)) × sin(2α) × C_camber
where: α = slip angle = atan2(V_y, V_x) for each wheel
       C_camber = camber correction factor = 0.9-1.1
```

**Aerodynamic Drag for Box-Shaped Agricultural Rover:**
```
F_drag = 0.5 × ρ × C_d × A × V² + F_rolling
where: ρ = air density (1.225 kg/m³ at sea level)
       C_d = drag coefficient (0.8-1.2 for box-shaped rover with implements)
       A = frontal area = width × height = 1.8m × 1.5m = 2.7 m²
       V = velocity (m/s)
       F_rolling = μ_r × m × g = 0.1 × 750 × 9.81 = 735.75 N (rolling resistance)

// Total resistive force at 2 m/s:
F_drag_total = 0.5 × 1.225 × 1.0 × 2.7 × 4 + 735.75 = 6.615 + 735.75 = 742.365 N
```

#### Multicopter Dynamics Model (for comparison)

**Motor Thrust and Torque Scaling with Rover Mass:**
```
T_i = k_T × ω_i² × (m/5.0)  // Thrust scaled by mass ratio (5kg reference multicopter)
Q_i = k_Q × ω_i² × (I_z/0.1) // Torque scaled by inertia ratio

where: k_T = thrust coefficient (0.0001 N/(rad/s)² typical)
       k_Q = torque coefficient (2.5e-6 Nm/(rad/s)² typical)
       ω_i = motor angular velocity (rad/s)
       m = 750 kg (rover mass)
       I_z = 300 kg·m² (rover yaw inertia)
```

**Rigid Body Dynamics (Newton-Euler) for High-Mass Vehicle:**
```
// Linear dynamics with high inertia
m × dv/dt = Σ T_i × R_b²w × e_z - m × g × e_z - D × v - F_terrain
where: m = 750 kg (vehicle mass)
       D = diagonal drag coefficient matrix = diag(50, 50, 20) N/(m/s) for rover
       F_terrain = terrain resistance force = k_terrain × V²

// Angular dynamics with large inertia tensor
I × dω/dt = Σ (r_i × (R_b²w × T_i × e_z) + Q_i × (-1)^i × e_z) - ω × (I × ω) - D_rot × ω
where: I = inertia tensor = diag(400, 400, 300) kg·m² for 750 kg rover
       D_rot = rotational damping = diag(10, 10, 15) Nm/(rad/s)
```

### Sensor Noise and External Physics Analysis

#### IMU Noise Models for Agricultural Vibration

**Accelerometer Noise with Vibration Spectrum:**
```
a_measured = a_true + b_a + η_a + s_a × a_true + T_a × Δtemp + V_vib × sin(2πf_vib × t)
where: b_a = bias (random walk: db_a/dt = η_b, η_b ~ N(0, σ_b²), σ_b = 0.01 m/s²/√Hz)
       η_a = white noise ~ N(0, σ_a²), σ_a = 0.05 m/s² (agricultural vibration)
       s_a = scale factor error (100-500 ppm for MEMS)
       T_a = temperature coefficient (0.1 mg/°C)
       V_vib = vibration amplitude = 0.1-0.5 m/s² depending on terrain
       f_vib = vibration frequency = 5-20 Hz (wheel rotation and engine)

// Power spectral density for agricultural vibration:
PSD(f) = P_0 × (f/f_0)^{-2} for f > f_0
where P_0 = 0.001 (m/s²)²/Hz, f_0 = 1 Hz
```

**Gyroscope Noise with Vehicle Rotation:**
```
ω_measured = ω_true + b_g + η_g + s_g × ω_true + T_g × Δtemp + ω_g × η_rw + ω_vib
where: b_g = bias (random walk: db_g/dt = η_bg, η_bg ~ N(0, σ_bg²), σ_bg = 0.01 °/s/√Hz)
       η_g = white noise ~ N(0, σ_g²), σ_g = 0.1 °/s
       η_rw = rate random walk ~ N(0, σ_rw²), σ_rw = 0.001 °/s/√Hz
       ω_vib = vibration-induced angular rate = A_vib × sin(2πf_vib × t)
       A_vib = 0.05-0.2 rad/s for uneven terrain
```

#### GPS Error Models for Field Operations

**Position and Velocity Errors with Agricultural Multipath:**
```
pos_measured = pos_true + η_pos + b_pos + s_pos × t + M_multipath(t)
where: η_pos ~ N(0, σ_pos²), σ_pos = 1.0m CEP (circular error probable)
       b_pos = bias (slow drift: 1-10 mm/s) = b_0 + k_drift × t
       s_pos = scale factor error = 1-5 ppm
       M_multipath(t) = multipath error = Σ A_i × sin(2πf_i × t + φ_i)
       A_i = 0.5-2.0m (amplitude from nearby structures)
       f_i = 0.1-1.0 Hz (multipath frequency)

vel_measured = vel_true + η_vel + b_vel + M_multipath_vel(t)
where: η_vel ~ N(0, σ_vel²), σ_vel = 0.1 m/s
       b_vel = velocity bias = 0.01-0.05 m/s
```

**Glitch Injection Model for Testing Robustness:**
```
if (rand() < p_glitch):
    pos_measured += Δpos_glitch × exp(-(t - t_glitch)²/(2τ²)) × C_terrain
    where: p_glitch = glitch probability per second = 0.001 (1 per 1000 seconds)
           Δpos_glitch = glitch magnitude = 5-20m (simulating satellite constellation change)
           τ = glitch time constant = 0.5-2.0s
           C_terrain = terrain factor = 1.0 (open field) to 2.0 (near trees)
```

#### External Physics Engine Interface Mathematics

**JSON Protocol Schema with Timestamp Synchronization:**
```json
{
  "timestamp": 1234567890.123,  // Unix time with microseconds
  "vehicle_state": {
    "position": [x, y, z],      // NED coordinates (m)
    "velocity": [vx, vy, vz],   // NED velocity (m/s)
    "orientation": [qw, qx, qy, qz],  // Unit quaternion
    "angular_velocity": [ωx, ωy, ωz], // Body frame (rad/s)
    "mass": 750.0,              // Vehicle mass (kg)
    "inertia": [400, 400, 300]  // [Ixx, Iyy, Izz] (kg·m²)
  },
  "sensor_data": {
    "imu": {
      "accel": [ax, ay, az],    // Body frame (m/s²)
      "gyro": [gx, gy, gz],     // Body frame (rad/s)
      "temperature": 25.5       // °C
    },
    "gps": {
      "position": [lat, lon, alt],  // WGS84 (deg, deg, m)
      "velocity": [vn, ve, vd],     // NED (m/s)
      "hdop": 1.2,                  // Horizontal dilution
      "vdop": 1.8,                  // Vertical dilution
      "satellites": 8               // Visible satellites
    }
  },
  "actuators": [pwm1, pwm2, ..., pwm8],  // PWM values (1000-2000μs)
  "terrain_params": {
    "friction": 0.6,             // Current friction coefficient
    "slope": 0.05,               // Terrain slope (rad)
    "roughness": 0.1             // Surface roughness (m RMS)
  }
}
```

**Frame Synchronization Mathematics:**
```
// Time synchronization between SITL and external engine
t_sync = t_sitl + Δt_latency + Δt_clock
where: Δt_latency = network_latency + processing_delay
       network_latency = 1-10ms (TCP/IP)
       processing_delay = 1-5ms (physics engine)
       Δt_clock = clock_drift × t_elapsed
       clock_drift = 1-10 ppm (typical oscillator)

// Adaptive frame rate control
if (Δt_error > ε_max):
    frame_rate = frame_rate × (1 - α × sign(Δt_error))
where: Δt_error = |t_sim - t_wall| / t_wall
       ε_max = 0.01 (1% tolerance)
       α = 0.1 (adaptation rate)
```

### Physics Simulation Mathematics

#### Numerical Integration Methods

**Runge-Kutta 4th Order for High-Fidelity Simulation:**
```
// For state vector x = [position, velocity, orientation, angular_velocity]
k1 = dt × f(t, x)
k2 = dt × f(t + dt/2, x + k1/2)
k3 = dt × f(t + dt/2, x + k2/2)
k4 = dt × f(t + dt, x + k3)
x_next = x + (k1 + 2×k2 + 2×k3 + k4)/6

where f(t, x) represents the vehicle dynamics equations
dt = time step = 0.001s (1ms) for 1000Hz physics update
```

**Constraint Stabilization for Ground Contact:**
```
// Ground penetration correction
if (z < z_ground):
    F_contact = k_ground × (z_ground - z) - d_ground × vz
    where: k_ground = 10000 N/m (ground stiffness)
           d_ground = 1000 N·s/m (ground damping)
           z_ground = terrain_height(x, y)
```

#### Energy Conservation Verification

**Total Energy Calculation for Validation:**
```
E_total = E_kinetic + E_potential + E_rotational
E_kinetic = 0.5 × m × V·V
E_potential = m × g × h
E_rotational = 0.5 × ω·(I × ω)

// Energy error per time step
ΔE = |E_total(t+dt) - E_total(t) - W_external| / E_total(t)
where W_external = work done by external forces
Constraint: ΔE < 1e-6 per time step for numerical stability
```

#### Sensor Data Generation Mathematics

**IMU Data Generation with Proper Kinematics:**
```
// True acceleration in body frame (excluding gravity)
a_true_body = R_w2b × (dV/dt) - [0, 0, g]  // Remove gravity
where R_w2b = rotation matrix from world to body
      dV/dt = linear acceleration in world frame

// True angular velocity in body frame
ω_true_body = angular velocity from quaternion derivative
q_dot = 0.5 × q × [0, ω_x, ω_y, ω_z]
```

**GPS Data Generation with Earth Curvature:**
```
// Convert NED to WGS84 with curvature correction
lat = lat0 + (y / R_earth) × (180/π)
lon = lon0 + (x / (R_earth × cos(lat0 × π/180))) × (180/π)
alt = alt0 - z

where: R_earth = 6378137 m (Earth radius)
       [lat0, lon0, alt0] = origin coordinates
```

### Network Protocol Optimization Mathematics

**Message Compression and Bandwidth Calculation:**
```
// Original message size
size_original = sizeof(VehicleState) + sizeof(SensorData) = 256 + 128 = 384 bytes

// Delta encoding compression
size_delta = sizeof(Δstate) + sizeof(Δsensor) = 64 + 32 = 96 bytes
where Δstate = state(t) - state(t-1)
      Δsensor = sensor(t) - sensor(t)

// With zlib compression (typical 2:1 ratio)
size_compressed = size_delta / 2 = 48 bytes

// Bandwidth requirements at 100Hz
bandwidth = 100 × 48 = 4800 bytes/s = 38.4 Kbps

// With 8:1 compression (achievable for delta encoding)
bandwidth_min = 100 × 12 = 1200 bytes/s = 9.6 Kbps
```

**Latency Compensation with Prediction:**
```
// Predict state at time of reception
t_transmit = t_current
t_receive = t_transmit + latency
state_predicted = state(t_current) + derivative × latency

where: latency = 0.005-0.020s (5-20ms typical)
       derivative = [velocity, acceleration, angular_velocity, angular_acceleration]
```

### Error Injection and Fault Testing Mathematics

**Systematic Error Injection for Robustness Testing:**
```
// Bias injection with ramp profile
bias_injected = b0 × (1 - exp(-t/τ_ramp)) × sin(2πf_bias × t)
where: b0 = maximum bias magnitude
       τ_ramp = 1-10s (ramp time constant)
       f_bias = 0.001-0.1 Hz (bias oscillation frequency)

// Scale factor error injection
scale_injected = 1.0 + s0 × (1 + 0.1 × sin(2πf_scale × t))
where: s0 = 0.001-0.01 (1-10% error)
       f_scale = 0.01-0.1 Hz
```

**Monte Carlo Simulation Parameters:**
```
// Parameter distributions for statistical testing
m ~ N(750, 25²) kg          // Mass with 3.3% variation
I_xx ~ N(400, 20²) kg·m²    // Roll inertia with 5% variation
I_yy ~ N(400, 20²) kg·m²    // Pitch inertia
I_zz ~ N(300, 15²) kg·m²    // Yaw inertia
μ ~ U(0.3, 0.8)             // Friction coefficient uniform distribution
C_d ~ N(1.0, 0.1²)          // Drag coefficient normal distribution

// Sample size for statistical significance
N_samples = (z_score × σ / ε)²
where: z_score = 1.96 for 95% confidence
       σ = parameter standard deviation
       ε = allowable error (e.g., 0.01 for 1%)
```

### Real-Time Performance Mathematics

**Frame Timing and Jitter Analysis:**
```
// Frame time statistics
t_frame = t_process + t_network + t_wait
where: t_process = 0.001-0.005s (1-5ms physics computation)
       t_network = 0.001-0.010s (1-10ms network transfer)
       t_wait = max(0, 1/frame_rate - (t_process + t_network))

// Jitter calculation
jitter = std_dev(t_frame) / mean(t_frame)
Constraint: jitter < 0.1 (10%) for real-time performance

// Buffer sizing for network variability
buffer_size = 2 × std_dev(latency) × frame_rate + 1
where std_dev(latency) = 0.002-0.005s (2-5ms typical)
```

**CPU Load Prediction for SITL Host:**
```
CPU_load = (t_physics + t_sensors + t_network) × frame_rate
where: t_physics = 0.001s (1ms for 750kg rover dynamics)
       t_sensors = 0.0002s (0.2ms for sensor noise generation)
       t_network = 0.0005s (0.5ms for JSON serialization)
       frame_rate = 100-400 Hz

At 400Hz: CPU_load = (0.001 + 0.0002 + 0.0005) × 400 = 0.68 (68%)
Safety margin: CPU_load < 0.8 (80%) for real-time guarantee
```

## C++ Implementation

### Aerodynamic and Friction Physics Emulation (SIM_Rover.cpp)

The `SIM_Rover` class implements the mathematical skid-steer kinematics `V_left = (2V - ω × track_width) / (2 × wheel_radius)` and Dugoff's tire model `F_x = μ × F_z × (1 - exp(-κ/s)) × tanh(5κ)` for a heavy agricultural rover.

```cpp
class SIM_Rover : public Aircraft {
private:
    // Vehicle parameters - maps to mathematical constants
    struct {
        float mass;              // Vehicle mass (kg) = m in Newton-Euler equations
        float inertia[3];        // [Ixx, Iyy, Izz] (kg·m²) = I in τ = I × α + ω × (I × ω)
        float wheel_radius;      // Wheel radius (m) = r in V = ω × r
        float track_width;       // Distance between wheels (m) = T_w in skid-steer equations
        float drag_coeff;        // Aerodynamic drag coefficient = C_d in F_drag = 0.5 × ρ × C_d × A × V²
        float frontal_area;      // Frontal area (m²) = A in drag equation
        float friction_coeff;    // Ground friction coefficient = μ in Dugoff's model
        float rolling_resistance;// Rolling resistance coefficient
    } _params;
    
    // Vehicle state - tracks mathematical state variables
    struct {
        Vector3f position;       // NED position (m) = [x, y, z] in dynamics equations
        Vector3f velocity;       // NED velocity (m/s) = v in m × dv/dt = ΣF
        Quaternion attitude;     // Vehicle attitude = q in q̇ = 0.5 × q × ω
        Vector3f angular_vel;    // Body angular velocity (rad/s) = ω in I × dω/dt = Στ
        float wheel_speed[2];    // [left, right] wheel speeds (rad/s) = ω_left, ω_right
        float motor_thrust[2];   // [left, right] motor thrust (N) = T_left, T_right
    } _state;
    
    // Physics simulation state
    struct {
        float time_step;         // Simulation time step (s) = dt in numerical integration
        uint64_t last_update_us; // Last update timestamp
        bool on_ground;          // Ground contact flag
        Vector3f ground_normal;  // Ground normal vector
        float suspension_comp[4];// Suspension compression (m)
    } _physics;
```

The `update()` method implements the mathematical Newton-Euler equations `m × dv/dt = ΣF` and `I × dω/dt = Στ - ω × (I × ω)`:

```cpp
public:
    // Update physics simulation - implements numerical integration of dynamics equations
    void update(const struct sitl_input &input) override {
        // Calculate time step: dt = (now_us - last_update_us) × 1e-6
        uint64_t now_us = AP_HAL::micros64();
        float dt = (now_us - _physics.last_update_us) * 1e-6f;
        _physics.last_update_us = now_us;
        
        // Convert PWM inputs to motor thrust
        _calculate_motor_thrust(input);
        
        // Calculate wheel-ground interaction (Dugoff's tire model)
        _calculate_ground_forces();
        
        // Calculate aerodynamic forces: F_drag = 0.5 × ρ × C_d × A × V²
        Vector3f aero_force = _calculate_aerodynamic_force();
        
        // Calculate total forces and moments
        Vector3f total_force = _calculate_total_force(aero_force);
        Vector3f total_moment = _calculate_total_moment();
        
        // Update linear dynamics: F = m × a → a = F/m, v += a × dt, p += v × dt
        Vector3f acceleration = total_force / _params.mass;
        _state.velocity += acceleration * dt;
        _state.position += _state.velocity * dt;
        
        // Update angular dynamics: τ = I × α + ω × (I × ω) → α = I⁻¹ × (τ - ω × (I × ω))
        Matrix3f inertia_tensor(_params.inertia[0], 0, 0,
                                0, _params.inertia[1], 0,
                                0, 0, _params.inertia[2]);
        
        Vector3f angular_accel = inertia_tensor.inverse() * 
                                (total_moment - _state.angular_vel.cross(
                                 inertia_tensor * _state.angular_vel));
        
        _state.angular_vel += angular_accel * dt;
        
        // Update attitude: q̇ = 0.5 × q × ω
        Quaternion q_dot = _state.attitude.derivative(_state.angular_vel);
        _state.attitude += q_dot * dt;
        _state.attitude.normalize();
        
        // Update wheel speeds (skid-steer kinematics)
        _update_wheel_speeds(dt);
        
        // Check ground contact
        _update_ground_contact();
    }
```

The `_calculate_ground_forces()` method implements Dugoff's tire model mathematics:

```cpp
private:
    // Calculate ground forces (friction and rolling resistance) - implements Dugoff's model
    void _calculate_ground_forces() {
        if (!_physics.on_ground) {
            return;
        }
        
        // Calculate vertical load: F_z = m × g / 2 (per wheel)
        float normal_force = _params.mass * 9.81f; // N
        
        // Calculate slip ratios: κ = (ω × r - V) / max(|ω × r|, |V|, 0.1)
        float v_longitudinal = _state.velocity.x; // Forward speed in body frame
        float wheel_radius = _params.wheel_radius;
        
        for (int i = 0; i < 2; i++) {
            float wheel_speed = _state.wheel_speed[i];
            float slip_ratio = 0.0f;
            
            if (fabsf(wheel_speed * wheel_radius) > 0.1f) {
                slip_ratio = (wheel_speed * wheel_radius - v_longitudinal) / 
                            fabsf(wheel_speed * wheel_radius);
            }
            
            // Dugoff's tire model (simplified): F_x = μ × F_z × tanh(5κ)
            float friction_force = _params.friction_coeff * normal_force * 
                                  tanh(5.0f * slip_ratio);
            
            // Rolling resistance: F_rolling = μ_r × F_z × sign(V)
            float rolling_force = _params.rolling_resistance * normal_force * 
                                 (v_longitudinal > 0 ? 1 : -1);
            
            // Total longitudinal force
            float total_force = _state.motor_thrust[i] + friction_force + rolling_force;
            
            // Update wheel dynamics: α = τ / I = (F × r) / I
            float wheel_inertia = 0.1f; // kg·m² (simplified)
            float wheel_accel = total_force * wheel_radius / wheel_inertia;
            _state.wheel_speed[i] += wheel_accel * dt;
        }
    }
```

The `_calculate_aerodynamic_force()` method implements the drag equation `F_drag = 0.5 × ρ × C_d × A × V²`:

```cpp
    // Calculate aerodynamic forces - implements F_drag = 0.5 × ρ × C_d × A × V²
    Vector3f _calculate_aerodynamic_force() {
        // Convert velocity to body frame: v_body = R_w2b × v_world
        Matrix3f R_w2b = _state.attitude.rotation_matrix().transposed();
        Vector3f vel_body = R_w2b * _state.velocity;
        
        // Calculate dynamic pressure: q̄ = 0.5 × ρ × ||v||²
        float q_bar = 0.5f * 1.225f * vel_body.length_squared(); // ρ = 1.225 kg/m³
        
        // Drag force (opposite to velocity direction): F_drag = -q̄ × C_d × A × v̂
        Vector3f drag_force = -vel_body.normalized() * 
                             q_bar * _params.drag_coeff * _params.frontal_area;
        
        // Convert back to world frame: F_world = R_b2w × F_body
        Matrix3f R_b2w = _state.attitude.rotation_matrix();
        return R_b2w * drag_force;
    }
```

### Synthetic Sensor Noise and GPS Glitch Injection (SITL_State.cpp)

The `SITL_State` class implements the mathematical noise models `a_measured = a_true + b_a + η_a + s_a × a_true` and glitch injection `pos_measured += Δpos_glitch × exp(-(t - t_glitch)²/(2τ²))`.

```cpp
class SITL_State {
private:
    // Noise generator state - maps to mathematical noise parameters
    struct NoiseGenerator {
        // IMU noise parameters
        struct {
            float accel_sigma;        // Accelerometer white noise σ_a in η_a ~ N(0, σ_a²)
            float gyro_sigma;         // Gyro white noise σ_g in η_g ~ N(0, σ_g²)
            float accel_bias_walk;    // Accelerometer bias random walk σ_b in db_a/dt = η_b
            float gyro_bias_walk;     // Gyro bias random walk σ_bg in db_g/dt = η_bg
            float accel_scale_error;  // Scale factor error s_a in ppm
            float gyro_scale_error;   // Scale factor error s_g in ppm
        } imu;
        
        // GPS noise parameters
        struct {
            float horiz_sigma;        // Horizontal position noise σ_pos in η_pos ~ N(0, σ_pos²)
            float vert_sigma;         // Vertical position noise
            float speed_sigma;        // Speed noise σ_vel in η_vel ~ N(0, σ_vel²)
            float drift_rate;         // Position drift rate b_pos in b_pos = b_0 + k_drift × t
            float glitch_prob;        // Glitch probability per second p_glitch
            float glitch_magnitude;   // Maximum glitch magnitude Δpos_glitch
        } gps;
        
        // Random number generators for η ~ N(0, σ²)
        std::default_random_engine rng;
        std::normal_distribution<float> normal_dist;
        std::uniform_real_distribution<float> uniform_dist;
    } _noise;
    
    // Sensor bias states (random walks) - implements ḃ = η random walk
    struct {
        Vector3f accel_bias;          // Accelerometer bias b_a in a_measured = a_true + b_a + ...
        Vector3f gyro_bias;           // Gyro bias b_g in ω_measured = ω_true + b_g + ...
        Vector3f gps_pos_bias;        // GPS position bias b_pos
        Vector3f gps_vel_bias;        // GPS velocity bias b_vel
        uint64_t last_bias_update_us; // Last bias update time for Δt calculation
    } _biases;
    
    // Glitch injection state - implements glitch model
    struct {
        bool active;                  // Glitch currently active
        uint64_t start_time_us;       // Glitch start time t_glitch
        Vector3f glitch_offset;       // Current glitch offset Δpos_glitch
        float glitch_decay;           // Glitch decay time constant τ
    } _glitch;
```

The `generate_imu_data()` method implements the mathematical IMU noise model:

```cpp
public:
    // Generate noisy IMU measurements - implements a_measured = a_true + b_a + η_a + s_a × a_true
    void generate_imu_data(const Vector3f &true_accel, const Vector3f &true_gyro,
                           Vector3f &measured_accel, Vector3f &measured_gyro,
                           uint64_t timestamp_us) {
        // Calculate time step for random walk updates: Δt = (t - t_last) × 1e-6
        float dt = (timestamp_us - _biases.last_bias_update_us) * 1e-6f;
        _biases.last_bias_update_us = timestamp_us;
        
        // Update bias random walks: Δb = η × √(Δt) × σ (Brownian motion)
        for (int i = 0; i < 3; i++) {
            // Random walk: ḃ = η, where η ~ N(0, σ²) → Δb = η × √(Δt) × σ
            float bias_step = _noise.normal_dist(_noise.rng) * 
                             sqrtf(dt) * _noise.imu.accel_bias_walk;
            _biases.accel_bias[i] += bias_step;
            
            bias_step = _noise.normal_dist(_noise.rng) * 
                       sqrtf(dt) * _noise.imu.gyro_bias_walk;
            _biases.gyro_bias[i] += bias_step;
        }
        
        // Apply scale factor errors: s = 1 + error_ppm × 1e-6
        float accel_scale_error = 1.0f + _noise.imu.accel_scale_error * 1e-6f;
        float gyro_scale_error = 1.0f + _noise.imu.gyro_scale_error * 1e-6f;
        
        // Generate white noise: η ~ N(0, σ²)
        Vector3f accel_noise(_noise.normal_dist(_noise.rng),
                            _noise.normal_dist(_noise.rng),
                            _noise.normal_dist(_noise.rng));
        accel_noise *= _noise.imu.accel_sigma;
        
        Vector3f gyro_noise(_noise.normal_dist(_noise.rng),
                           _noise.normal_dist(_noise.rng),
                           _noise.normal_dist(_noise.rng));
        gyro_noise *= _noise.imu.gyro_sigma;
        
        // Combine all error sources: measured = true × scale + bias + noise
        measured_accel = true_accel * accel_scale_error + 
                        _biases.accel_bias + accel_noise;
        
        measured_gyro = true_gyro * gyro_scale_error + 
                       _biases.gyro_bias + gyro_noise;
        
        // Apply temperature drift (simplified): T_effect = A × sin(2πf × t)
        float temp_effect = sinf(timestamp_us * 1e-6f * 2.0f * M_PI / 3600.0f); // 1 hour cycle
        measured_accel += Vector3f(0.01f, 0.01f, 0.01f) * temp_effect;
        measured_gyro += Vector3f(0.001f, 0.001f, 0.001f) * temp_effect;
    }
```

The `generate_gps_data()` method implements the mathematical GPS error model with glitch injection:

```cpp
    // Generate noisy GPS measurements with glitch injection
    void generate_gps_data(const Vector3f &true_position, const Vector3f &true_velocity,
                           Vector3f &measured_position, Vector3f &measured_velocity,
                           uint64_t timestamp_us) {
        // Update GPS bias drift: b_pos += drift_rate × Δt
        float dt = (timestamp_us - _biases.last_bias_update_us) * 1e-6f;
        
        for (int i = 0; i < 3; i++) {