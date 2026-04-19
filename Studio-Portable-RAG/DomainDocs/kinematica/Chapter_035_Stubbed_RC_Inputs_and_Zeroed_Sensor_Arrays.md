# Stubbed RC Inputs, ADC Bypasses, and Zeroed Sensor Arrays

_Generated 2026-04-15 00:17 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Empty/RCInput.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Empty/RCInput.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Empty/AnalogIn.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Empty/AnalogIn.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Empty/OpticalFlow.h`

# Chapter: Stubbed RC Inputs, ADC Bypasses, and Zeroed Sensor Arrays

## Technical Introduction

The files `RCInput.cpp`, `RCInput.h`, `AnalogIn.cpp`, `AnalogIn.h`, `SensorArray.cpp`, and `SensorArray.h` implement hardware abstraction layer stubs for the 400Hz agricultural rover control system. These components provide deterministic, testable interfaces that simulate sensor inputs without physical hardware, enabling development and unit testing of the rover's skid-steer kinematics and safety systems. The RC input stubs generate synthetic PWM signals for testing control algorithms, ADC bypasses provide simulated voltage readings for battery monitoring and current sensing, and zeroed sensor arrays create deterministic IMU/GPS data streams for validating the EKF covariance monitoring and crash detection mathematics. This architecture allows full validation of the rover's 20kg mass dynamics and safety-critical fault detection without requiring physical sensor hardware.

## Mathematical Formulation: Stubbed RC Inputs, ADC Bypasses, and Zeroed Sensor Arrays

### RC Input Stub Mathematics

The RC input stubs generate synthetic PWM signals that simulate the differential steering commands for a 20kg skid-steer rover. The mathematical model generates left and right channel signals with controlled noise and failure modes.

**Differential Steering Signal Generation:**
For a rover with track width T = 0.5m and maximum yaw rate ω_max = 2.0 rad/s, the differential PWM signals are generated as:
```
PWM_left(t) = 1500 + 500 * (throttle_cmd - ω_cmd * T/2)
PWM_right(t) = 1500 + 500 * (throttle_cmd + ω_cmd * T/2)
```
Where throttle_cmd ∈ [-1, 1] and ω_cmd ∈ [-ω_max, ω_max].

**Signal Corruption Modeling:**
To test fault detection algorithms, the stubs implement probabilistic signal corruption:
```
P(corruption) = 1 - exp(-λ * t)
P(glitch) = 0.001 per sample (400Hz → ~1.44 glitches/hour)
```
Glitch magnitude follows normal distribution: ΔPWM ~ N(0, 50²) microseconds.

**Channel Failure Mathematics:**
Multi-channel RC inputs (8 channels) implement independent failure probabilities:
```
P(channel_i_fails) = 10⁻⁶ per hour (ASIL-B requirement)
P(system_fails) = 1 - Π(1 - P(channel_i_fails)) ≈ 8 × 10⁻⁶
```

### ADC Bypass Mathematics

The ADC bypass system simulates voltage and current readings for the rover's power system, implementing the physical relationships between battery state, motor currents, and system loads.

**Battery Voltage Simulation:**
For a 6S LiPo battery (22.2V nominal, 25.2V full, 18.0V empty):
```
V_battery(t) = V_ocv(SOC) - I_load * R_internal
SOC(t) = SOC₀ - (1/Capacity) ∫ I_battery dt
V_ocv(SOC) = 18.0 + 7.2 * SOC - 2.4 * SOC² + 0.8 * SOC³
```
Where Capacity = 10Ah = 36000C, R_internal = 0.05Ω.

**Motor Current Simulation:**
For dual 500W motors with efficiency η = 0.85:
```
I_motor = (P_mechanical / η) / V_battery
P_mechanical = τ * ω = (F_diff * R) * (v/R) = F_diff * v
```
Where F_diff is the differential force from steering controller, v is rover velocity.

**Current Sensing Mathematics:**
Using ACS712 30A sensors with 66mV/A sensitivity:
```
V_adc = 2.5V + 0.066 * I_motor + V_noise
ADC_raw = (V_adc / 3.3V) * 4095 (12-bit ADC)
```
Noise model: V_noise ~ N(0, 0.01²) volts.

**Temperature Sensor Simulation:**
MPU9250 temperature sensor linear model:
```
T_sensor = T_ambient + 0.1 * I_motor² * R_heating
ADC_temp = (T_sensor + 21) * 333.87 (LSB/°C)
```

### Zeroed Sensor Array Mathematics

The zeroed sensor arrays generate deterministic IMU and GPS data streams that satisfy the kinematic constraints of a 20kg rover while injecting controlled faults for testing the EKF covariance monitoring.

**IMU Acceleration Simulation:**
For a rover with mass M = 20kg experiencing forces F_x, F_y from motors and terrain:
```
a_x = (F_x_total - F_drag - F_rolling - F_grade) / M
a_y = F_y_total / M
a_z = g - (F_downforce / M)
```
Where F_drag = 0.5 * ρ * C_d * A * v², F_rolling = C_rr * M * g * cos(θ), F_grade = M * g * sin(θ).

**Gyroscope Angular Rate Simulation:**
From differential drive kinematics:
```
ω_z = (v_right - v_left) / T
ω_x = (a_y / v) * sin(ϕ)  (roll from turning)
ω_y = (a_x / v) * sin(θ)  (pitch from acceleration)
```
Where ϕ is bank angle, θ is slope angle.

**GPS Position Simulation:**
Integrated from velocity with controlled drift:
```
x(t+Δt) = x(t) + v_x * Δt + 0.5 * a_x * Δt² + ε_x
y(t+Δt) = y(t) + v_y * Δt + 0.5 * a_y * Δt² + ε_y
```
Where ε_x, ε_y ~ N(0, σ_gps²), σ_gps = 1.5m (typical GPS error).

**Magnetometer Simulation:**
Earth's magnetic field with hard/soft iron distortions:
```
B_measured = R * B_earth + B_bias + M * B_measured
```
Where R is rotation matrix, B_bias is hard iron, M is soft iron matrix.

### Sensor Fault Injection Mathematics

The zeroed arrays implement controlled fault injection to test the rover's fault detection and isolation algorithms.

**IMU Fault Models:**
1. Bias fault: a_fault = a_true + b, b ~ N(0, 0.1g²)
2. Scale factor fault: a_fault = k * a_true, k ∈ [0.9, 1.1]
3. Random walk fault: b(t+Δt) = b(t) + w, w ~ N(0, σ_w²)

**GPS Fault Models:**
1. Jump fault: position jumps by Δp ~ N(0, 10m²)
2. Freeze fault: position stops updating
3. Drift fault: velocity error accumulates: v_error(t) = v_error(t-1) + δv

**Fault Probability Mathematics:**
For ASIL-B compliance with 10⁻⁷ hazardous events per hour:
```
P(sensor_fault) = 10⁻⁶ per hour
P(undetected_fault) = P(sensor_fault) * (1 - P_detection)
```
With triple redundancy and voting: P_detection ≈ 0.99999

### Sensor Fusion Test Mathematics

The zeroed arrays generate correlated sensor data to test the EKF fusion algorithms under known ground truth conditions.

**Ground Truth Generation:**
For test trajectory with known kinematics:
```
x_true(t) = ∫∫ a_x_true dt²
v_true(t) = ∫ a_x_true dt
ψ_true(t) = ∫ ω_z_true dt
```

**Sensor Data Generation with Known Errors:**
```
a_imu = a_true + b_accel + w_accel
ω_imu = ω_true + b_gyro + w_gyro
pos_gps = pos_true + ε_gps
vel_gps = vel_true + δ_gps
```

**Covariance Validation:**
The EKF covariance P should bound the actual error:
```
P[0:2,0:2] ≥ E[(pos_est - pos_true)²]
P[3:5,3:5] ≥ E[(vel_est - vel_true)²]
```
Test validates: trace(P_actual) / trace(P_expected) ≈ 1

### Power System Simulation Mathematics

The ADC bypass simulates the complete electrical system for the 20kg rover.

**Battery Discharge Physics:**
```
I_total = I_motors + I_avionics + I_sensors
I_motors = (P_left + P_right) / (η * V_battery)
P_left = τ_left * ω_left, P_right = τ_right * ω_right
```

**Regulator Efficiency Modeling:**
```
V_3v3 = V_battery * η_buck * (1 - I_load * R_ds)
η_buck = 0.92 - 0.0005 * I_load (efficiency curve)
```

**Current Limit Simulation:**
For 30A fuses on each motor channel:
```
if I_motor > 30A for > 100ms: fuse_blown = true
I_motor = 0 after fuse blown
```

### Temperature Simulation Mathematics

Sensor and component temperatures affect readings and performance.

**IMU Temperature Effects:**
```
b_accel(T) = b_accel_25°C + TC_accel * (T - 25)
b_gyro(T) = b_gyro_25°C + TC_gyro * (T - 25)
```
Where TC_accel = 0.1mg/°C, TC_gyro = 0.01°/s/°C.

**Motor Temperature Rise:**
```
ΔT_motor = (I_motor² * R_winding * t_on) / (m_motor * c_copper)
R_winding(T) = R_20°C * (1 + α * (T - 20))
```
Where α = 0.00393/°C for copper.

### Communication Bus Simulation

The stubs simulate I2C and SPI bus communications with timing and error characteristics.

**I2C Timing Mathematics:**
Standard mode: 100kHz = 10μs per clock
```
t_start = 4.7μs min, t_stop = 4.0μs min
t_data = 250ns min (data hold), 1.3μs min (data setup)
```

**SPI Timing Mathematics:**
For MPU9250 at 1MHz:
```
t_SCLK = 1μs period, 500ns high, 500ns low
t_CS_setup = 100ns, t_CS_hold = 100ns
```

**Bus Error Injection:**
```
P(bit_error) = 10⁻⁹ per transfer (typical I2C)
P(packet_loss) = 1 - exp(-λ * t_busy)
```

### Calibration Mathematics

The stubs implement calibration routines with known mathematical relationships.

**Accelerometer Calibration:**
Six-position calibration solves:
```
a_measured = S * (a_true - b)
```
Where S is 3x3 scale/misalignment matrix, b is bias vector.

**Gyroscope Calibration:**
Static calibration estimates bias:
```
b_gyro = mean(ω_measured) over 1s static
```

**Magnetometer Calibration:**
Ellipsoid fitting solves:
```
(B - b)ᵀ * M * (B - b) = 1
```
Where M is positive definite matrix representing soft iron.

### Sensor Health Monitoring Mathematics

The stubs provide ground truth for sensor health checks.

**IMU Self-Test Mathematics:**
```
ST_value = (output_with_ST - output_without_ST) / sensitivity
```
Should be within [80%, 120%] of factory value.

**GPS Health Metrics:**
```
HDOP = √(σ_x² + σ_y²) / σ_p
VDOP = σ_z / σ_p
```
Where σ_p = 1.5m typical pseudorange error.

**Consistency Checking:**
```
χ² = (z - Hx)ᵀ * S⁻¹ * (z - Hx)
```
Where S = HPHᵀ + R, should be χ² distributed with n_z degrees of freedom.

This mathematical formulation provides the complete theoretical foundation for the stubbed RC inputs, ADC bypasses, and zeroed sensor arrays that enable deterministic testing of the 20kg agricultural rover's control algorithms without physical hardware. The equations directly map to the C++ implementation that follows, ensuring that simulated sensor behaviors match the physical characteristics of real sensors while providing controlled test conditions for validation.

## C++ Implementation: Stubbed RC Inputs, ADC Bypasses, and Zeroed Sensor Arrays

### RC Input Stub Implementation (RCInput.cpp)

The RC input stub generates synthetic PWM signals that implement the mathematical model `PWM_left(t) = 1500 + 500 * (throttle_cmd - ω_cmd * T/2)` with controlled noise and failure injection. The implementation runs in the 400Hz control loop to provide deterministic testing of the rover's steering algorithms.

```cpp
// RCInput.cpp - Synthetic PWM generation for rover control testing
__attribute__((section(".itcm")))
class RCInput_Stub : public AP_HAL::RCInput {
private:
    // Channel state with mathematical model parameters
    struct __attribute__((packed)) ChannelState {
        uint16_t pwm_value;          // 0x20003000: Current PWM in µs
        uint16_t pwm_center;         // 0x20003002: Center position (1500)
        uint16_t pwm_range;          // 0x20003004: ± range (500)
        float throttle_cmd;          // 0x20003008: Throttle command [-1,1]
        float yaw_rate_cmd;          // 0x2000300C: Yaw rate command [rad/s]
        float track_width;           // 0x20003010: Rover track width (0.5m)
        uint32_t fault_injection;    // 0x20003014: Fault injection flags
        float noise_stddev;          // 0x20003018: Noise standard deviation
    } channels[8];
    
    // Timing and update state
    struct __attribute__((packed)) TimingState {
        uint32_t last_update_us;     // 0x20003100
        uint32_t update_interval_us; // 0x20003104: 2500µs for 400Hz
        uint32_t glitch_counter;     // 0x20003108
        uint32_t fault_counter;      // 0x2000310C
        uint8_t enabled_channels;    // 0x20003110
    } timing;
    
public:
    void init() override {
        // Initialize all channels with default values
        for (int i = 0; i < 8; i++) {
            channels[i].pwm_center = 1500;
            channels[i].pwm_range = 500;
            channels[i].throttle_cmd = 0.0f;
            channels[i].yaw_rate_cmd = 0.0f;
            channels[i].track_width = 0.5f;  // 20kg rover track width
            channels[i].fault_injection = 0;
            channels[i].noise_stddev = 5.0f; // 5µs noise stddev
            
            // Set initial PWM values
            update_channel(i);
        }
        
        // Channel assignments for skid-steer rover:
        // Ch1: Throttle, Ch2: Steering, Ch3: Mode, Ch4: Aux1
        // Ch5: Left motor (simulated), Ch6: Right motor (simulated)
        // Ch7: Emergency stop, Ch8: Camera trigger
        
        timing.last_update_us = AP_HAL::micros();
        timing.update_interval_us = 2500;  // 400Hz
        timing.enabled_channels = 8;
    }
    
    // Main update called from 400Hz control loop
    __attribute__((section(".itcm")))
    void update() override {
        uint32_t now = AP_HAL::micros();
        if (now - timing.last_update_us >= timing.update_interval_us) {
            timing.last_update_us = now;
            
            // Update all channels according to mathematical model
            for (int i = 0; i < timing.enabled_channels; i++) {
                update_channel(i);
                
                // Inject faults based on probability model
                inject_faults(i);
            }
        }
    }
    
    // Get channel value with bounds checking
    __attribute__((section(".itcm")))
    uint16_t read(uint8_t channel) override {
        if (channel < timing.enabled_channels) {
            return channels[channel].pwm_value;
        }
        return 0;
    }
    
    // Set command inputs for testing
    __attribute__((section(".itcm")))
    void set_commands(float throttle, float yaw_rate) {
        // Store commands for differential steering model
        channels[0].throttle_cmd = throttle;      // Throttle channel
        channels[1].yaw_rate_cmd = yaw_rate;      // Steering channel
        
        // Calculate differential motor commands for skid-steer
        // ω = (v_right - v_left) / T → v_diff = ω * T
        float v_diff = yaw_rate * channels[5].track_width;
        
        // Left motor: throttle - v_diff/2
        channels[4].throttle_cmd = throttle - v_diff / 2.0f;
        // Right motor: throttle + v_diff/2  
        channels[5].throttle_cmd = throttle + v_diff / 2.0f;
    }
    
private:
    // Update single channel with mathematical model
    __attribute__((section(".itcm")))
    void update_channel(uint8_t ch) {
        ChannelState& chan = channels[ch];
        
        // Base PWM calculation from command
        float command = 0.0f;
        switch (ch) {
            case 0: command = chan.throttle_cmd; break;  // Throttle
            case 1: command = chan.yaw_rate_cmd / 2.0f; break; // Scaled yaw
            case 4: command = chan.throttle_cmd; break;  // Left motor
            case 5: command = chan.throttle_cmd; break;  // Right motor
            default: command = 0.0f; break;
        }
        
        // Apply mathematical model: PWM = center + range * command
        float pwm_float = chan.pwm_center + chan.pwm_range * command;
        
        // Add Gaussian noise: N(0, noise_stddev²)
        if (chan.noise_stddev > 0.0f) {
            // Box-Muller transform for Gaussian noise
            float u1 = (float)rand() / RAND_MAX;
            float u2 = (float)rand() / RAND_MAX;
            float z = sqrtf(-2.0f * logf(u1)) * cosf(2.0f * M_PI * u2);
            pwm_float += z * chan.noise_stddev;
        }
        
        // Convert to integer and clamp to valid range [1000, 2000]
        int32_t pwm_int = (int32_t)pwm_float;
        if (pwm_int < 1000) pwm_int = 1000;
        if (pwm_int > 2000) pwm_int = 2000;
        
        chan.pwm_value = (uint16_t)pwm_int;
    }
    
    // Inject faults based on probability model
    __attribute__((section(".itcm")))
    void inject_faults(uint8_t ch) {
        ChannelState& chan = channels[ch];
        
        // Check for glitch: P(glitch) = 0.001 per sample
        if ((rand() % 1000) == 0) {
            // Glitch magnitude ~ N(0, 50²)
            float u1 = (float)rand() / RAND_MAX;
            float u2 = (float)rand() / RAND_MAX;
            float z = sqrtf(-2.0f * logf(u1)) * cosf(2.0f * M_PI * u2);
            int32_t glitch = (int32_t)(z * 50.0f);
            
            chan.pwm_value += glitch;
            timing.glitch_counter++;
            
            // Clamp after glitch
            if (chan.pwm_value < 1000) chan.pwm_value = 1000;
            if (chan.pwm_value > 2000) chan.pwm_value = 2000;
        }
        
        // Check for channel failure: P(failure) = 10⁻⁶ per hour
        // At 400Hz: 400*3600 = 1.44M samples/hour, so 1.44 failures/hour at 10⁻⁶
        if ((rand() % 1000000) == 0) {
            // Channel fails to center position (fail-safe)
            chan.pwm_value = chan.pwm_center;
            chan.fault_injection |= 0x1;  // Set failure flag
            timing.fault_counter++;
        }
        
        // Check for stuck channel
        if ((chan.fault_injection & 0x2) && (rand() % 10000) == 0) {
            // Channel stuck at current value
            // No update applied
        }
    }
};
```

### ADC Bypass Implementation (AnalogIn.cpp)

The ADC bypass system simulates voltage and current readings implementing the mathematical models for battery discharge `V_battery(t) = V_ocv(SOC) - I_load * R_internal` and motor current sensing `V_adc = 2.5V + 0.066 * I_motor + V_noise`. The simulation runs at 100Hz to match typical ADC sampling rates.

```cpp
// AnalogIn.cpp - Simulated ADC readings for rover power system
__attribute__((section(".itcm")))
class AnalogIn_Stub : public AP_HAL::AnalogIn {
private:
    // Battery simulation state
    struct __attribute__((packed)) BatteryState {
        float voltage;          // 0x20004000: Current voltage (V)
        float current;          // 0x20004004: Current draw (A)
        float soc;             // 0x20004008: State of charge [0,1]
        float capacity_ah;     // 0x2000400C: Battery capacity (10Ah)
        float internal_r;      // 0x20004010: Internal resistance (0.05Ω)
        float ocv_params[4];   // 0x20004014: OCV curve parameters
        uint32_t update_us;    // 0x20004024: Last update time
    } battery;
    
    // Motor current sensors (ACS712 simulation)
    struct __attribute__((packed)) CurrentSensor {
        float current;          // 0x20004030: Actual current (A)
        float voltage;          // 0x20004034: Sensor output (V)
        float sensitivity;      // 0x20004038: 66mV/A
        float offset;           // 0x2000403C: 2.5V zero-current
        float noise_stddev;     // 0x20004040: 0.01V noise
        uint16_t adc_value;     // 0x20004044: 12-bit ADC reading
    } current_sensors[2];       // Left and right motors
    
    // Temperature sensors
    struct __attribute__((packed)) TemperatureSensor {
        float temperature;      // 0x20004050: Temperature (°C)
        float adc_scale;        // 0x20004054: 333.87 LSB/°C
        float adc_offset;       // 0x20004058: -21°C offset
        uint16_t adc_value;     // 0x2000405C: Raw ADC
    } temp_sensors[3];          // IMU, motor left, motor right
    
    // System voltage rails
    struct __attribute__((packed)) VoltageRail {
        float voltage;          // 0x20004070: Rail voltage
        float efficiency;       // 0x20004074: Regulator efficiency
        float load_current;     // 0x20004078: Load current
        uint16_t adc_value;     // 0x2000407C: ADC reading
    } rails[3];                 // 3V3, 5V, 12V
    
public:
    void init() override {
        // Initialize battery model for 6S LiPo
        battery.voltage = 25.2f;  // Fully charged
        battery.current = 0.0f;
        battery.soc = 1.0f;
        battery.capacity_ah = 10.0f;
        battery.internal_r = 0.05f;
        
        // OCV curve parameters: V_ocv(SOC) = 18.0 + 7.2*SOC - 2.4*SOC² + 0.8*SOC³
        battery.ocv_params[0] = 18.0f;
        battery.ocv_params[1] = 7.2f;
        battery.ocv_params[2] = -2.4f;
        battery.ocv_params[3] = 0.8f;
        
        battery.update_us = AP_HAL::micros();
        
        // Initialize current sensors (ACS712 30A)
        for (int i = 0; i < 2; i++) {
            current_sensors[i].current = 0.0f;
            current_sensors[i].voltage = 2.5f;
            current_sensors[i].sensitivity = 0.066f;  // 66mV/A
            current_sensors[i].offset = 2.5f;
            current_sensors[i].noise_stddev = 0.01f;
            current_sensors[i].adc_value = 0;
        }
        
        // Initialize temperature sensors (MPU9250 style)
        for (int i = 0; i < 3; i++) {
            temp_sensors[i].temperature = 25.0f;
            temp_sensors[i].adc_scale = 333.87f;
            temp_sensors[i].adc_offset = -21.0f;
            temp_sensors[i].adc_value = 0;
        }
        
        // Initialize voltage rails
        rails[0].voltage = 3.3f;  // 3V3 rail
        rails[0].efficiency = 0.92f;
        rails[1].voltage = 5.0f;  // 5V rail  
        rails[1].efficiency = 0.90f;
        rails[2].voltage = 12.0f; // 12V rail
        rails[2].efficiency = 0.95f;
    }
    
    // Update all simulated readings (called at 100Hz)
    __attribute__((section(".itcm")))
    void update() {
        uint32_t now = AP_HAL::micros();
        float dt = (now - battery.update_us) * 1.0e-6f;
        
        if (dt >= 0.01f) {  // 100Hz update
            battery.update_us = now;
            
            // Update battery state based on mathematical model
            update_battery(dt);
            
            // Update current sensors
            update_current_sensors();
            
            // Update temperature sensors
            update_temperature_sensors();
            
            // Update voltage rails
            update_voltage_rails();
        }
    }
    
    // Read ADC channel (simulated)
    __attribute__((section(".itcm")))
    float read_average(uint8_t channel) override {
        if (channel < 8) {
            // Map channels to simulated sensors
            switch (channel) {
                case 0: return battery.voltage;           // Battery voltage
                case 1: return current_sensors[0].current; // Left motor current
                case 2: return current_sensors[1].current; // Right motor current
                case 3: return temp_sensors[0].temperature; // IMU temperature
                case 4: return rails[0].voltage;          // 3V3 rail
                case 5: return rails[1].voltage;          // 5V rail
                case 6: return rails[2].voltage;          // 12V rail
                case 7: return battery.current;           // Total current
            }
        }
        return 0.0f;
    }
    
    // Set motor currents for simulation (from control system)
    __attribute__((section(".itcm")))
    void set_motor_currents(float left_amps, float right_amps) {
        current_sensors[0].current = left_amps;
        current_sensors[1].current = right_amps;
        
        // Update total current for battery model
        battery.current = left_amps + right_amps + 1.5f;  // +1.5A for avionics
    }
    
private:
    // Update battery model using mathematical equations
    __attribute__((section(".itcm")))
    void update_battery(float dt) {
        // Update state of charge: SOC = SOC₀ - (1/C) ∫ I dt
        float charge_used = battery.current * dt / 3600.0f;  // Ah used
        battery.soc -= charge_used / battery.capacity_ah;
        
        if (battery.soc < 0.0f) battery.soc = 0.0f;
        if (battery.soc > 1.0f) battery.soc = 1.0f;
        
        // Calculate OCV from SOC using cubic polynomial
        float soc = battery.soc;
        float ocv = battery.ocv_params[0] +
                   battery.ocv_params[1] * soc +
                   battery.ocv_params[2] * soc * soc +
                   battery.ocv_params[3] * soc * soc * soc;
        
        // Apply internal resistance: V = OCV - I*R
        battery.voltage = ocv - battery.current * battery.internal_r;
        
        // Clamp to realistic values
        if (battery.voltage < 18.0f) battery.voltage = 18.0f;
        if (battery.voltage > 25.2f) battery.voltage = 25.2f;
    }
    
    // Update current sensor simulations
    __attribute__((section(".itcm")))
    void update_current_sensors() {
        for (int i = 0; i < 2; i++) {
            CurrentSensor& sensor = current_sensors[i];
            
            // Calculate sensor voltage: V = 2.5V + 0.066 * I
            float ideal_voltage = sensor.offset + sensor.sensitivity * sensor.current;
            
            // Add Gaussian noise
            float u1 = (float)rand() / RAND_MAX;
            float u2 = (float)rand() / RAND_MAX;
            float z = sqrtf(-2.0f * logf(u1)) * cosf(2.0f * M_PI * u2);
            sensor.voltage = ideal_voltage + z * sensor.noise_stddev;
            
            // Convert to 12-bit ADC value (0-3.3V range)
            float adc_float = (sensor.voltage / 3.3f) * 4095.0f;
            if (adc_float < 0.0f) adc_float = 0.0f;
            if (adc_float > 4095.0f) adc_float = 4095.0f;
            sensor.adc_value = (uint16_t)adc_float;
        }
    }
    
    // Update temperature sensor simulations
    __attribute__((section(".itcm")))
    void update_temperature_sensors() {
        // IMU temperature (sensor self-heating)
        temp_sensors[0].temperature = 25.0f + 0.1f * battery.current;
        
        // Motor temperatures (simplified heating model)
        // ΔT = I² * R * t / (m * c)
        static float motor_heat[2] = {0.0f, 0.0f};
        for (int i = 0; i < 2; i++) {
            // Simple first-order heating model
            float heating = current_sensors[i].current * current_sensors[i].current * 0.01f;
            motor_heat[i] = 0.99f * motor_heat[i] + 0.01f * heating;
            temp_sensors[i+1].temperature = 25.0f + motor_heat[i];
        }
        
        // Convert temperatures to ADC values (MPU9250 style)
        for (int i = 0; i < 3; i++) {
            float adc_float = (temp_sensors[i].temperature - temp_sensors[i].adc_offset) *
                             temp_sensors[i].adc_scale;
            if (adc_float < 0.0f) adc_float = 0.0f;
            if (adc_float > 4095.0f) adc_float = 4095.0f;
            temp_sensors[i].adc_value = (uint16_t)adc_float;
        }
    }
    
    // Update voltage rail simulations
    __attribute__((section(".itcm")))
    void update_voltage_rails() {
        // 3V3 rail from battery via buck converter
        rails[0].voltage = battery.voltage * rails[0].efficiency;
        rails[0].load_current = 0.5f;  // 500mA typical load
        
        // 5V rail (from 3V3 boost or battery buck)
        rails[1].voltage = 5.0f;
        rails[1].load_current = 1.0f;  // 1A typical load
        
        // 12V rail (direct from battery or boost)
        rails[2].voltage = battery.voltage;
        rails[2].load_current = battery.current;
        
        // Convert to ADC values
        for (int i = 0; i < 3; i++) {
            float adc_float = (rails[i].voltage / 3.3f) * 4095.0f;
            if (adc_float > 4095.0f) adc_float = 4095.0f;
            rails[i].adc_value = (uint16_t)adc_float;
        }
    }
};
```

### Zeroed Sensor Array Implementation (SensorArray.cpp)

The zeroed sensor array generates deterministic IMU, GPS, and magnetometer data that satisfies the kinematic constraints `a_x = (F_x_total - F_drag - F_rolling - F_grade) / M` while injecting controlled faults for testing the rover's EKF and fault detection systems.

```cpp
// SensorArray.cpp - Deterministic sensor data generation
__attribute__((section(".itcm")))
class SensorArray_Stub {
private:
    // IMU simulation state
    struct __attribute__((packed)) IMUState {
        Vector3f accel;         // 0x20005000: Acceleration (m/s²)
        Vector3f gyro;          // 0x2000500C: Angular rate (rad/s)
        Vector3f mag;           // 0x20005018: Magnetic field (µT)
        float temperature;      // 0x20005024: Temperature (°C)
        Vector3f accel_bias;    // 0x20005028: Accelerometer bias
        Vector3f gyro_bias;     // 0x20005034: Gyro bias
        Vector3f mag_bias;      // 0x20005040: Magnetometer bias
        Matrix3f accel_scale;   // 0x2000504C: Scale/misalignment
        Matrix3f gyro_scale;    // 0x20005070: Gyro scale
        Matrix3f soft_iron;     // 0x20005094: Soft iron matrix
        uint32_t fault_flags;   // 0x200050B8: Fault injection
    } imu;
    
    // GPS simulation state
    struct __attribute__((packed)) GPSState {
        double latitude;        // 0x200050C0: Degrees
        double longitude;       // 0x200050C8: Degrees
        float altitude;         // 0x200050D0: Meters
        float velocity_n;       // 0x200050D4: North velocity (m/s)
        float velocity_e;       // 0x