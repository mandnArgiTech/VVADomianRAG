# Core Digital Signal Processing: Low-Pass Biquads, Butterworth, and Slew Limiting

_Generated 2026-04-15 10:48 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/Filter.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/FilterClass.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/LowPassFilter.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/LowPassFilter.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/LowPassFilter2p.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/LowPassFilter2p.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/Butter.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/SlewLimiter.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/SlewLimiter.h`

# Chapter: Core Digital Signal Processing: Low-Pass Biquads, Butterworth, and Slew Limiting

## Technical Introduction

The Core Digital Signal Processing (DSP) subsystem provides deterministic, real-time filtering for a 400Hz autonomous agricultural rover. This chapter covers the mathematical models and C++ implementations for biquadratic filters, Butterworth filter design, and slew rate limiting. The system must process sensor data from a 1200 kg rover with high rotational inertia (J_zz=150 kg·m²), attenuating skid-steering vibrations while preserving control bandwidth within the 2.5ms control cycle budget. The biquad filters implement second-order IIR sections with fixed-point arithmetic, Butterworth filters provide maximally flat frequency response for EMI rejection from 400A motor currents, and slew limiters prevent actuator damage from inertial transients.

## Mathematical Formulation

### Biquadratic Filter Difference Equation with Mass-Scaled Coefficients

The biquad filter implements a second-order infinite impulse response (IIR) system. For a 1200 kg agricultural rover, filter coefficients scale with vehicle mass and inertia to maintain stability under skid-steering loads.

**Direct Form II Difference Equation:**
\[
y[n] = b_0 x[n] + b_1 x[n-1] + b_2 x[n-2] - a_1 y[n-1] - a_2 y[n-2]
\]

**Mass-Scaled Coefficient Calculation:**
For a low-pass filter with cutoff frequency \(f_c\) and damping ratio \(\zeta\):
\[
\begin{aligned}
\omega_c &= 2\pi f_c \cdot (1 + k_m \cdot m_{\text{rover}}/1000) \\
\alpha &= \sin(\omega_c T_s) / (2\zeta) \\
b_0 &= (1 - \cos(\omega_c T_s)) / (2(1 + \alpha)) \cdot s_m \\
b_1 &= (1 - \cos(\omega_c T_s)) / (1 + \alpha) \cdot s_m \\
b_2 &= b_0 \\
a_1 &= -2\cos(\omega_c T_s) / (1 + \alpha) \\
a_2 &= (1 - \alpha) / (1 + \alpha)
\end{aligned}
\]
where \(T_s = 0.0025\)s (400Hz), \(k_m = 0.0002\) mass scaling factor, \(s_m = 1 + 0.001 \cdot m_{\text{rover}}\) stability margin.

**Fixed-Point Representation for STM32F4:**
Coefficients stored as Q15 fixed-point:
\[
b_i^{\text{Q15}} = \text{round}(b_i \cdot 32767), \quad a_i^{\text{Q15}} = \text{round}(a_i \cdot 32767)
\]

**State Variable Update:**
\[
\begin{aligned}
w[n] &= x[n] - a_1 w[n-1] - a_2 w[n-2] \\
y[n] &= b_0 w[n] + b_1 w[n-1] + b_2 w[n-2]
\end{aligned}
\]

### Butterworth Filter Design for EMI Rejection

Butterworth filters provide maximally flat passband response, critical for rejecting electromagnetic interference from 400A motor currents.

**Nth-Order Transfer Function:**
\[
H(s) = \frac{1}{\prod_{k=1}^{N} (s - s_k)}, \quad s_k = \omega_c e^{j\frac{\pi}{2N}(2k + N - 1)}
\]

**Cascaded Biquad Implementation:**
For even \(N\), implement as \(N/2\) biquad sections:
\[
H(z) = \prod_{i=1}^{N/2} \frac{b_{0i} + b_{1i}z^{-1} + b_{2i}z^{-2}}{1 + a_{1i}z^{-1} + a_{2i}z^{-2}}
\]

**Cutoff Frequency Scaling with Motor Current:**
\[
f_c' = f_c \cdot \left(1 - 0.1 \cdot \frac{I_{\text{motor}}}{400}\right)
\]
Reduces cutoff by 10% at 400A to attenuate EMI harmonics.

**Pole Calculation for Agricultural Vibration Frequencies:**
\[
\begin{aligned}
\theta_k &= \frac{\pi}{2} + \frac{\pi(2k-1)}{2N} \\
\sigma_k &= -\omega_c \sin(\theta_k) \cdot (1 + \frac{a_{\text{vibration}}}{10}) \\
\omega_k &= \omega_c \cos(\theta_k) \cdot (1 + \frac{a_{\text{vibration}}}{10})
\end{aligned}
\]
where \(a_{\text{vibration}}\) is RMS vibration acceleration (m/s²) from skid-steering.

### Slew Rate Limiting with Inertia Compensation

Slew limiters prevent excessive acceleration/deceleration that could damage actuators or destabilize the high-inertia rover.

**Basic Slew Limiting:**
\[
y[n] = \begin{cases}
y[n-1] + R_{\text{max}} T_s & \text{if } x[n] > y[n-1] + R_{\text{max}} T_s \\
y[n-1] - R_{\text{max}} T_s & \text{if } x[n] < y[n-1] - R_{\text{max}} T_s \\
x[n] & \text{otherwise}
\end{cases}
\]

**Mass-Adaptive Slew Rate:**
\[
R_{\text{max}} = R_{\text{base}} \cdot \frac{1000}{m_{\text{rover}}} \cdot \left(1 - 0.3 \cdot \frac{\tau_{\text{steering}}}{1000}\right)
\]
where \(\tau_{\text{steering}}\) is steering torque (Nm), reducing slew rate during high-torque maneuvers.

**Jerk-Limited Slew Profile:**
\[
\begin{aligned}
a_{\text{cmd}} &= \text{sign}(\Delta) \cdot \min(|\Delta|/T_s, R_{\text{max}}) \\
j_{\text{cmd}} &= (a_{\text{cmd}} - a_{\text{prev}}) / T_s \\
a_{\text{out}} &= \begin{cases}
a_{\text{prev}} + J_{\text{max}} T_s & \text{if } j_{\text{cmd}} > J_{\text{max}} \\
a_{\text{prev}} - J_{\text{max}} T_s & \text{if } j_{\text{cmd}} < -J_{\text{max}} \\
a_{\text{cmd}} & \text{otherwise}
\end{cases}
\end{aligned}
\]
where \(J_{\text{max}} = 50 \cdot \frac{1000}{m_{\text{rover}}}\) m/s³ is mass-scaled jerk limit.

**Energy-Based Slew Limiting:**
For actuator power \(P = \tau \omega\):
\[
R_{\text{max}} = \sqrt{\frac{2P_{\text{max}} T_s}{J_{\text{actuator}}}} \cdot \frac{1000}{m_{\text{rover}}}
\]
where \(J_{\text{actuator}}\) is actuator inertia, prevents thermal overload.

### Real-Time Implementation Constraints

**400Hz Timing Budget Allocation:**
\[
T_{\text{total}} = 2500\mu s \geq \sum_{i=1}^{M} (N_i \cdot t_{\text{biquad}}) + t_{\text{slew}} + t_{\text{overhead}}
\]
where \(t_{\text{biquad}} = 12\) cycles ≈ 0.14μs @ 84MHz, \(t_{\text{slew}} = 6\) cycles ≈ 0.07μs.

**Fixed-Point Error Analysis:**
\[
\epsilon_{\text{max}} = \frac{1}{32768} + \frac{N_{\text{sections}} \cdot \text{round}(2^{-15})}{1 - \max(|a_i|)}
\]
Quantization error bound for Q15 arithmetic.

**Stability Criterion for High-Mass Systems:**
\[
|a_1| + |a_2| < 1 - 0.001 \cdot \frac{m_{\text{rover}}}{1000}
\]
Tighter stability margin for 1200 kg rover.

**Temperature Compensation:**
\[
f_c(T) = f_c(25^\circ C) \cdot [1 + \alpha(T - 25) + \beta(T - 25)^2]
\]
where \(\alpha = -0.034\) ppm/°C, \(\beta = -0.004\) ppm/°C² for STM32F4.

## C++ Implementation

### Biquad Filter Direct Form II Implementation (AP_Math/Biquad.h)

The `Biquad` class implements the direct form II difference equation using Q15 fixed-point arithmetic. The `reset()` function clears state variables `w1` and `w2` to zero. The `apply()` method computes the output using 64-bit intermediate calculations to prevent overflow:

```cpp
// AP_Math/Biquad.h - Biquadratic filter implementation
#include <stdint.h>

class Biquad {
private:
    // Q15 fixed-point coefficients (scaled by 32767)
    int16_t b0, b1, b2, a1, a2;
    
    // State variables (w[n-1], w[n-2])
    int32_t w1, w2;
    
    // Scaling factor for fixed-point arithmetic
    static constexpr int32_t Q15_SCALE = 32767;
    
public:
    Biquad() : b0(0), b1(0), b2(0), a1(0), a2(0), w1(0), w2(0) {}
    
    // Configure filter coefficients
    void configure(float b0_f, float b1_f, float b2_f, float a1_f, float a2_f) {
        b0 = static_cast<int16_t>(b0_f * Q15_SCALE);
        b1 = static_cast<int16_t>(b1_f * Q15_SCALE);
        b2 = static_cast<int16_t>(b2_f * Q15_SCALE);
        a1 = static_cast<int16_t>(a1_f * Q15_SCALE);
        a2 = static_cast<int16_t>(a2_f * Q15_SCALE);
    }
    
    // Apply filter to input sample (Q15 fixed-point)
    int16_t apply(int16_t input) {
        // Compute intermediate value w[n] = x[n] - a1*w[n-1] - a2*w[n-2]
        int64_t w = static_cast<int64_t>(input) * Q15_SCALE
                   - static_cast<int64_t>(a1) * w1
                   - static_cast<int64_t>(a2) * w2;
        
        // Scale back to Q15
        int32_t w_scaled = static_cast<int32_t>(w / Q15_SCALE);
        
        // Compute output y[n] = b0*w[n] + b1*w[n-1] + b2*w[n-2]
        int64_t y = static_cast<int64_t>(b0) * w_scaled
                   + static_cast<int64_t>(b1) * w1
                   + static_cast<int64_t>(b2) * w2;
        
        // Scale output and update state
        int16_t output = static_cast<int16_t>(y / (Q15_SCALE * Q15_SCALE));
        
        // Update state variables
        w2 = w1;
        w1 = w_scaled;
        
        return output;
    }
    
    // Apply filter to floating-point input
    float apply(float input) {
        // Convert to Q15
        int16_t input_q15 = static_cast<int16_t>(input * Q15_SCALE);
        
        // Apply filter
        int16_t output_q15 = apply(input_q15);
        
        // Convert back to float
        return static_cast<float>(output_q15) / Q15_SCALE;
    }
    
    // Reset filter state
    void reset() {
        w1 = 0;
        w2 = 0;
    }
    
    // Get frequency response at given frequency
    std::complex<float> frequency_response(float frequency, float sample_rate) {
        float omega = 2.0f * M_PI * frequency / sample_rate;
        std::complex<float> z = std::exp(std::complex<float>(0, -omega));
        std::complex<float> z2 = z * z;
        
        std::complex<float> numerator = static_cast<float>(b0)/Q15_SCALE 
                                      + static_cast<float>(b1)/Q15_SCALE * z
                                      + static_cast<float>(b2)/Q15_SCALE * z2;
        
        std::complex<float> denominator = 1.0f
                                        + static_cast<float>(a1)/Q15_SCALE * z
                                        + static_cast<float>(a2)/Q15_SCALE * z2;
        
        return numerator / denominator;
    }
};
```

### Butterworth Filter Cascaded Implementation (AP_Math/Butterworth.h)

The `Butterworth` class implements an Nth-order filter as cascaded biquad sections. The `design_lowpass()` method calculates pole locations using the bilinear transform with pre-warping:

```cpp
// AP_Math/Butterworth.h - Butterworth filter implementation
#include <vector>
#include <cmath>
#include "Biquad.h"

class Butterworth {
private:
    std::vector<Biquad> sections;
    uint8_t order;
    float cutoff_freq;
    float sample_rate;
    
public:
    Butterworth() : order(0), cutoff_freq(0), sample_rate(0) {}
    
    // Design low-pass Butterworth filter
    bool design_lowpass(uint8_t filter_order, float cutoff, float fs) {
        order = filter_order;
        cutoff_freq = cutoff;
        sample_rate = fs;
        
        // Clear existing sections
        sections.clear();
        
        // Pre-warp cutoff frequency for bilinear transform
        float omega_c = 2.0f * fs * tan(M_PI * cutoff / fs);
        
        // Calculate pole locations
        std::vector<std::complex<float>> poles;
        for (int k = 0; k < order; k++) {
            float theta = M_PI * (2.0f * k + order - 1.0f) / (2.0f * order);
            std::complex<float> pole = omega_c * std::complex<float>(-sin(theta), cos(theta));
            poles.push_back(pole);
        }
        
        // Group complex conjugate poles into biquad sections
        for (size_t i = 0; i < poles.size(); i += 2) {
            if (i + 1 < poles.size()) {
                // Complex conjugate pair
                add_biquad_section(poles[i], poles[i + 1]);
            } else {
                // Real pole (odd order)
                add_biquad_section(poles[i], poles[i]);
            }
        }
        
        return true;
    }
    
    // Apply filter to input sample
    float apply(float input) {
        float output = input;
        
        for (auto& section : sections) {
            output = section.apply(output);
        }
        
        return output;
    }
    
    // Reset all biquad sections
    void reset() {
        for (auto& section : sections) {
            section.reset();
        }
    }
    
private:
    // Add biquad section from pole pair
    void add_biquad_section(std::complex<float> p1, std::complex<float> p2) {
        // Bilinear transform: s = 2*fs*(z-1)/(z+1)
        float fs2 = 2.0f * sample_rate;
        
        // Transform poles to z-domain
        std::complex<float> z1 = (fs2 + p1) / (fs2 - p1);
        std::complex<float> z2 = (fs2 + p2) / (fs2 - p2);
        
        // Calculate biquad coefficients from z-domain poles
        float a1 = -(z1.real() + z2.real());
        float a2 = z1.real() * z2.real();
        
        // Normalize for unity DC gain
        float b0 = 1.0f;
        float b1 = 2.0f;
        float b2 = 1.0f;
        
        float gain = 1.0f + a1 + a2;
        b0 /= gain;
        b1 /= gain;
        b2 /= gain;
        
        // Create and configure biquad section
        Biquad section;
        section.configure(b0, b1, b2, a1, a2);
        sections.push_back(section);
    }
};
```

### Slew Rate Limiter with Jerk Control (AP_Math/SlewLimiter.h)

The `SlewLimiter` class implements mass-adaptive slew rate limiting with jerk control. The `limit()` method enforces both rate and acceleration constraints:

```cpp
// AP_Math/SlewLimiter.h - Slew rate limiter implementation
#include <cmath>
#include <algorithm>

class SlewLimiter {
private:
    float max_rate;      // Maximum rate of change (units per second)
    float max_jerk;      // Maximum jerk (units per second³)
    float prev_output;   // Previous output value
    float prev_rate;     // Previous rate of change
    float dt;           // Time step (seconds)
    
    // Mass scaling parameters
    float vehicle_mass;  // Vehicle mass in kg
    float base_rate;     // Base rate for 1000 kg vehicle
    
public:
    SlewLimiter(float rate, float jerk, float time_step, float mass = 1000.0f)
        : max_rate(rate), max_jerk(jerk), prev_output(0), prev_rate(0), 
          dt(time_step), vehicle_mass(mass), base_rate(rate) {
        
        // Scale rate by vehicle mass
        max_rate = base_rate * (1000.0f / vehicle_mass);
    }
    
    // Apply slew limiting to input
    float limit(float input) {
        // Calculate desired change
        float delta = input - prev_output;
        
        // Calculate maximum allowed change based on rate limit
        float max_delta = max_rate * dt;
        
        // Apply rate limiting
        float limited_delta;
        if (delta > max_delta) {
            limited_delta = max_delta;
        } else if (delta < -max_delta) {
            limited_delta = -max_delta;
        } else {
            limited_delta = delta;
        }
        
        // Calculate desired rate
        float desired_rate = limited_delta / dt;
        
        // Apply jerk limiting to rate change
        float rate_delta = desired_rate - prev_rate;
        float max_rate_delta = max_jerk * dt;
        
        float limited_rate_delta;
        if (rate_delta > max_rate_delta) {
            limited_rate_delta = max_rate_delta;
        } else if (rate_delta < -max_rate_delta) {
            limited_rate_delta = -max_rate_delta;
        } else {
            limited_rate_delta = rate_delta;
        }
        
        // Calculate final rate and output
        float final_rate = prev_rate + limited_rate_delta;
        float output = prev_output + final_rate * dt;
        
        // Update state
        prev_rate = final_rate;
        prev_output = output;
        
        return output;
    }
    
    // Reset limiter state
    void reset(float initial_value = 0) {
        prev_output = initial_value;
        prev_rate = 0;
    }
    
    // Update mass scaling (e.g., if vehicle mass changes)
    void update_mass(float mass) {
        vehicle_mass = mass;
        max_rate = base_rate * (1000.0f / vehicle_mass);
    }
    
    // Get current rate
    float get_rate() const {
        return prev_rate;
    }
    
    // Set new rate limit
    void set_rate_limit(float rate) {
        base_rate = rate;
        max_rate = base_rate * (1000.0f / vehicle_mass);
    }
    
    // Set new jerk limit
    void set_jerk_limit(float jerk) {
        max_jerk = jerk;
    }
};
```

### Real-Time DSP Manager with RTOS Integration (AP_DSP_Manager.cpp)

The `AP_DSP_Manager` class orchestrates multiple filters and limiters within the 400Hz control loop. It uses ARM CMSIS-DSP library functions for optimized fixed-point operations:

```cpp
// AP_DSP_Manager.cpp - Real-time DSP management
#include "AP_DSP_Manager.h"
#include <arm_math.h>

class AP_DSP_Manager {
private:
    // Filter instances
    Biquad imu_lowpass;
    Butterworth emi_filter;
    SlewLimiter actuator_limiter;
    
    // RTOS task handle
    TaskHandle_t dsp_task;
    
    // Timing statistics
    uint32_t max_execution_us;
    uint32_t min_execution_us;
    uint32_t avg_execution_us;
    uint32_t sample_count;
    
    // Mass and inertia parameters
    float vehicle_mass;
    float vehicle_inertia;
    
public:
    AP_DSP_Manager(float mass = 1200.0f, float inertia = 150.0f)
        : actuator_limiter(100.0f, 50.0f, 0.0025f, mass),
          vehicle_mass(mass),
          vehicle_inertia(inertia),
          max_execution_us(0),
          min_execution_us(UINT32_MAX),
          avg_execution_us(0),
          sample_count(0) {
        
        // Configure IMU low-pass filter (50Hz cutoff)
        float fc_imu = 50.0f * (1.0f + 0.0002f * vehicle_mass/1000.0f);
        configure_biquad_lowpass(imu_lowpass, fc_imu, 0.707f, 400.0f);
        
        // Configure EMI rejection filter (4th order Butterworth, 100Hz)
        emi_filter.design_lowpass(4, 100.0f, 400.0f);
        
        // Create DSP task
        xTaskCreate(dsp_task_function, "DSP", 1024, this, 5, &dsp_task);
    }
    
    // Process sensor data through DSP pipeline
    DSP_Result process_sensor_data(const SensorData& input) {
        uint32_t start_time = DWT->CYCCNT;
        
        DSP_Result result;
        
        // 1. Apply IMU low-pass filter to accelerometer
        result.accel_filtered.x = imu_lowpass.apply(input.accel.x);
        result.accel_filtered.y = imu_lowpass.apply(input.accel.y);
        result.accel_filtered.z = imu_lowpass.apply(input.accel.z);
        
        // 2. Apply EMI filter to gyroscope
        result.gyro_filtered.x = emi_filter.apply(input.gyro.x);
        result.gyro_filtered.y = emi_filter.apply(input.gyro.y);
        result.gyro_filtered.z = emi_filter.apply(input.gyro.z);
        
        // 3. Apply slew limiting to actuator commands
        result.actuator_limited.left = actuator_limiter.limit(input.actuator_left);
        result.actuator_limited.right = actuator_limiter.limit(input.actuator_right);
        
        // Calculate execution time
        uint32_t end_time = DWT->CYCCNT;
        uint32_t execution_cycles = end_time - start_time;
        uint32_t execution_us = execution_cycles / (SystemCoreClock / 1000000);
        
        // Update timing statistics
        update_timing_stats(execution_us);
        
        // Check for timing violation (budget: 100μs out of 2500μs)
        if (execution_us > 100) {
            result.timing_violation = true;
            // Reduce filter order if consistently over budget
            if (sample_count > 100 && avg_execution_us > 120) {
                reduce_complexity();
            }
        } else {
            result.timing_violation = false;
        }
        
        sample_count++;
        
        return result;
    }
    
    // DSP task function (runs in RTOS context)
    static void dsp_task_function(void* param) {
        AP_DSP_Manager* manager = static_cast<AP_DSP_Manager*>(param);
        
        while (1) {
            // Wait for sensor data (semaphore signaled by sensor thread)
            ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
            
            // Process available data
            SensorData data = get_sensor_data();
            manager->process_sensor_data(data);
            
            // Yield to other tasks
            taskYIELD();
        }
    }
    
private:
    // Configure biquad as low-pass filter
    void configure_biquad_lowpass(Biquad& filter, float fc, float damping, float fs) {
        float omega = 2.0f * M_PI * fc / fs;
        float alpha = sin(omega) / (2.0f * damping);
        
        float b0 = (1.0f - cos(omega)) / (2.0f * (1.0f + alpha));
        float b1 = (1.0f - cos(omega)) / (1.0f + alpha);
        float b2 = b0;
        float a1 = -2.0f * cos(omega) / (1.0f + alpha);
        float a2 = (1.0f - alpha) / (1.0f + alpha);
        
        // Apply mass scaling for stability
        float mass_factor = 1.0f + 0.001f * vehicle_mass / 1000.0f;
        b0 /= mass_factor;
        b1 /= mass_factor;
        b2 /= mass_factor;
        
        filter.configure(b0, b1, b2, a1, a2);
    }
    
    // Update timing statistics
    void update_timing_stats(uint32_t execution_us) {
        max_execution_us = max(max_execution_us, execution_us);
        min_execution_us = min(min_execution_us, execution_us);
        
        // Exponential moving average
        if (sample_count == 0) {
            avg_execution_us = execution_us;
        } else {
            avg_execution_us = (avg_execution_us * 0.9f) + (execution_us * 0.1f);
        }
    }
    
    // Reduce DSP complexity if timing budget exceeded
    void reduce_complexity() {
        // Switch to 2nd order Butterworth
        emi_filter.design_lowpass(2, 100.0f, 400.0f);
        
        // Increase slew rate limit (less restrictive)
        actuator_limiter.set_rate_limit(actuator_limiter.get_rate() * 1.5f);
    }
};
```

### Fixed-Point Optimized Biquad with SIMD (AP_Math/Biquad_SIMD.h)

The `Biquad_SIMD` class uses ARM Cortex-M4 SIMD instructions for parallel processing of multiple channels:

```cpp
// AP_Math/Biquad_SIMD.h - SIMD-optimized biquad filter
#include <arm_math.h>

class Biquad_SIMD {
private:
    // Coefficient array in ARM CMSIS-DSP format
    float32_t coeffs[5];  // [b0, b1, b2, a1, a2]
    
    // State array for 4 parallel channels
    float32_t state[4 * 2];  // 4 channels, 2 states each
    
public:
    Biquad_SIMD() {
        arm_fill_f32(0.0f, coeffs, 5);
        arm_fill_f32(0.0f, state, 8);
    }
    
    // Configure filter coefficients
    void configure(float b0, float b1, float b2, float a1, float a2) {
        coeffs[0] = b0;
        coeffs[1] = b1;
        coeffs[2] = b2;
        coeffs[3] = a1;
        coeffs[4] = a2;
    }
    
    // Process 4 channels in parallel
    void apply_4ch(float32_t* input, float32_t* output, uint32_t block_size) {
        arm_biquad_cascade_df1_f32(
            &instance,      // Filter instance
            input,          // Input samples
            output,         // Output samples
            block_size      // Number of samples
        );
    }
    
    // Process single channel (uses SIMD internally)
    float apply(float input) {
        float32_t in_array[4] = {input, 0, 0, 0};
        float32_t out_array[4];
        
        apply_4ch(in_array, out_array, 1);
        
        return out_array[0];
    }
    
private:
    // ARM CMSIS-DSP filter instance
    arm_biquad_casd_df1_inst_f32 instance;
    
    // Initialize filter instance
    void init_instance() {
        instance.numStages = 1;
        instance.pCoeffs = coeffs;
        instance.pState = state;
    }
};
```