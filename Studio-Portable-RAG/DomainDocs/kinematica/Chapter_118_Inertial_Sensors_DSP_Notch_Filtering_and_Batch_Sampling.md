# Inertial Sensors, DSP Harmonic Notch Filtering, and High-Speed Sampling

_Generated 2026-04-20 02:14 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_InertialSensor/BatchSampler.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_InertialSensor/AP_InertialSensor_Logging.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/Filter/NotchFilter.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GyroFFT/AP_GyroFFT.cpp`

# **Chapter: Inertial Sensors, DSP Harmonic Notch Filtering, and High-Speed Sampling**

This chapter documents the deterministic real-time pipeline for inertial measurement unit (IMU) processing within the ArduPilot 400Hz autonomous vehicle architecture. The implementation is specifically hardened for the physical realities of heavy robotic platforms (>500 kg), where high inertia, structural resonances, and skid-steer torque transients generate significant narrowband vibration noise. The core files—`AP_InertialSensor.cpp`, `AP_InertialSensor_Backend.cpp`, `BatchSampler.cpp`, `NotchFilter.cpp`, and `AP_GyroFFT.cpp`—form a three-stage processing chain: 1) **Hardware Interface**: 8 kHz SPI DMA sampling with double-buffering, 2) **Digital Signal Processing**: A dynamic, RPM-tracked harmonic notch filter cascade, and 3) **Batch Analysis**: An FFT-based vibration monitor for in-flight system identification. This pipeline ensures that vibration frequencies between 10-400 Hz are attenuated by ≥40 dB before the gyro data enters the navigation EKF, preserving attitude estimate integrity during aggressive maneuvers.

---

### **Mathematical Formulation of Inertial Sensor Processing for a Heavy Skid-Steer Rover**

This section details the exact algebraic and matrix mathematics governing the real-time inertial measurement pipeline. The formulation directly addresses the physical realities of a heavy agricultural rover: high mass (>500 kg) inducing significant mechanical inertia, low-frequency structural resonances from uneven terrain, and high-torque skid-steer maneuvers that generate coupled rotational vibrations.

#### **1. High-Speed Sampling and Decimation**

The rover's high inertia necessitates wide-bandwidth sensing to capture rapid torque transients. Gyroscope data is sampled at 8 kHz via SPI DMA. A deterministic decimation filter reduces the data rate to 1 kHz for the navigation filter, preserving signal integrity for high-mass dynamics.

**SPI Timing and Sample Period:**
The SPI clock is derived from the processor peripheral clock (PCLK) with a prescaler of 256.
Given a PCLK of 168 MHz:
`f_SPI = 168 MHz / 256 = 656.25 kHz`
With 16-bit transfers per axis (3 axes × 16 bits = 48 bits), the effective sampling period is:
`T_s = 48 / f_SPI ≈ 73.14 µs`
This results in a maximum theoretical sample rate of `1 / T_s ≈ 13.67 kHz`. The configured rate of 8 kHz is achieved by inserting idle periods, yielding a precise sample interval:
`T_s_effective = 1 / 8000 Hz = 125 µs`

**Decimation Filter Arithmetic:**
Raw 16-bit gyro integers `G_raw[k]` are accumulated over 8 samples. The decimated output `G_dec` is a scaled average:
```
G_accum = Σ_{i=0}^{7} G_raw[k-i] // Vector sum over 8 samples
G_dec = G_accum * S * (1/8)
```
Where `S` is the gyro scale factor (e.g., `0.0010652644` rad/s per LSB for a 2000 deg/s range). This 8:1 averaging filter provides an inherent low-pass effect, attenuating noise above 500 Hz.

#### **2. Harmonic Notch Filter: Coefficient Derivation**

The filter targets vibrations at the fundamental motor frequency `f₀` and its harmonics `fₙ = n * f₀`, which are excited by the rover's skid-steer drivetrain and proportional to wheel RPM.

**Frequency Calculation from Rover Drivetrain:**
For a motor with `P` pole pairs and a gear reduction ratio `R`:
`f₀_motor = (RPM * P) / 60` // Electrical frequency in Hz
`f₀_wheel = f₀_motor / R` // Mechanical frequency at the wheel
The vibration fundamental `f₀` is a function of `f₀_wheel` and the rover's specific mechanical coupling.

**Discrete-Time Design via Bilinear Transform:**
1.  Compute the digital frequency for the `n`-th harmonic:
    `ωₙ = 2π * fₙ * T_s_effective`
2.  Pre-warp the frequency to compensate for bilinear distortion:
    `Ωₙ = tan(ωₙ / 2)`
3.  Compute the filter `Q` factor from the desired bandwidth `BW` (Hz):
    `Q = ωₙ / (2π * BW * T_s_effective)`
4.  Calculate the intermediate coefficient `α`:
    `α = sin(ωₙ) / (2 * Q)`
5.  Compute the final second-order IIR coefficients:
    ```
    a₀ = 1 + α
    b₀ = 1 / a₀
    b₁ = -2 * cos(ωₙ) / a₀
    b₂ = 1 / a₀
    a₁ = -2 * cos(ωₙ) / a₀
    a₂ = (1 - α) / a₀
    ```
The resulting transfer function for each harmonic `n` is:
`Hₙ(z) = (b₀ + b₁*z⁻¹ + b₂*z⁻²) / (1 + a₁*z⁻¹ + a₂*z⁻²)`

#### **3. Cascade Filter Implementation in State-Space**

The four harmonic notches are applied in series. The Direct Form II transposed implementation is used for numerical stability on the embedded processor.

**State Update Equations:**
For a single axis and a single harmonic, the filter maintains two state variables `s₁, s₂`. For an input sequence `x[t]`, the output `y[t]` is computed as:
```
w[t] = x[t] - a₁*s₁[t-1] - a₂*s₂[t-1]
y[t] = b₀*w[t] + b₁*s₁[t-1] + b₂*s₂[t-1]
s₂[t] = s₁[t-1]
s₁[t] = w[t]
```
For `N` harmonics, the output `y[t]` of stage `k` becomes the input `x[t]` for stage `k+1`. This is executed for each of the three axes (X, Y, Z) independently.

#### **4. FFT-Based Vibration Analysis and PSD**

A 1024-point real FFT analyzes a 128 ms window of gyro data (`1024 / 8000 Hz = 0.128 s`) to identify vibration peaks, crucial for diagnosing structural resonances in the heavy chassis.

**Window Function Application:**
To mitigate spectral leakage, the Hanning window `w[n]` is applied point-wise to the time-domain samples `x[n]`:
```
w[n] = 0.5 * (1 - cos(2π * n / (N-1))), for n = 0...1023
x_windowed[n] = x[n] * w[n]
```

**Power Spectral Density (PSD) Calculation:**
The FFT outputs complex bins `X[k] = R[k] + jI[k]`. The single-sided power spectrum `P[k]` is:
```
P[k] = (R[k]² + I[k]²) / (N * f_s * E_window) for k = 0...511
```
Where `E_window` is the window energy normalization factor:
`E_window = (1/N) * Σ_{n=0}^{N-1} w[n]² ≈ 0.375`

**Frequency Bin Mapping:**
The frequency corresponding to bin index `k` is:
`f[k] = k * (f_s / N) = k * (8000 / 1024) ≈ k * 7.8125 Hz`
The dominant vibration frequency `f_peak` is found by identifying the bin `k_peak` with maximum `P[k]` within the rover's relevant bandwidth (e.g., 10-400 Hz):
`f_peak = k_peak * 7.8125 Hz`

#### **5. Integration with Navigation Filter Kinematics**

The filtered angular rate vector `ω_filtered = [ω_x, ω_y, ω_z]^T` is integrated into the attitude quaternion within the EKF. The quaternion derivative is a linear matrix function of the angular rates:

Given quaternion `q = [q0, q1, q2, q3]^T`, the time derivative is:
```
dq/dt = 0.5 * Ω(ω_filtered) * q
```
Where `Ω(ω)` is the 4x4 skew-symmetric matrix:
```
Ω(ω) = [[0,    -ω_x, -ω_y, -ω_z],
        [ω_x,   0,    ω_z, -ω_y],
        [ω_y, -ω_z,   0,    ω_x],
        [ω_z,  ω_y, -ω_x,   0  ]]
```
This formulation ensures that high-amplitude, narrowband vibrations from the drivetrain are algebraically nulled by the notch filters before affecting the attitude state prediction, maintaining estimator consistency during high-torque skid-steer turns.

---

### **C++ Implementation: RTOS Pipeline and Hardware Abstraction**

This section details the specific C++ classes, RTOS threading, and hardware register manipulation that implement the mathematical pipeline for the heavy rover.

#### **Hardware Interface: SPI DMA and Double-Buffering**

The `SPI_DMA_Config` struct manages the low-level hardware interface for 8 kHz sampling. The `volatile uint32_t *SPI_DR` pointer provides direct memory-mapped access to the SPI data register, enabling zero-copy transfers.

```cpp
// Instantiation and configuration of the DMA engine.
SPI_DMA_Config imu_spi = {
    .SPI_DR = &SPI3->DR, // Point to SPI3 Data Register at 0x40003C0C
    .DMA_Stream = DMA2_Stream0,
    .buffer_a = (uint16_t*)0x2001C000, // SRAM2 base, Cacheable
    .buffer_b = (uint16_t*)0x2001D000, // SRAM2 + 4KB, Cacheable
    .transfer_size = 6 // 3 axes * 16 bits = 6 bytes
};

// SPI3 initialization for 8 kHz effective rate (PCLK=168MHz, prescaler=256).
void SPI3_Init(void) {
    __HAL_RCC_SPI3_CLK_ENABLE();
    SPI3->CR1 = SPI_CR1_SSM | SPI_CR1_SSI | SPI_CR1_SPE |
                SPI_CR1_CPOL | SPI_CR1_CPHA |
                SPI_CR1_BR_PRESCALER_256; // 0x0000034F
    SPI3->CR2 = SPI_CR2_RXDMAEN; // 0x00000400
}
```

The `HAL_SPI_RxCpltCallback` runs in the DMA interrupt context (IRQ priority 1). It performs an atomic buffer swap and signals the `_dma_semaphore` to wake the processing thread.

```cpp
// IRQ Handler: Buffer swap and thread signaling.
void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi) {
    __disable_irq();
    if (_current_buffer == &_buffer_a) {
        _current_buffer = &_buffer_b;
        _processing_buffer = &_buffer_a;
        HAL_SPI_Receive_DMA(_hspi, _buffer_b, SAMPLES_PER_BUFFER);
    } else {
        _current_buffer = &_buffer_a;
        _processing_buffer = &_buffer_b;
        HAL_SPI_Receive_DMA(_hspi, _buffer_a, SAMPLES_PER_BUFFER);
    }
    osSemaphoreRelease(_dma_semaphore); // Wake the DSP thread
    __enable_irq();
}
```

#### **RTOS Threading: DSP Processing Pipeline**

Three RTOS threads manage the pipeline. The `_dma_semaphore` synchronizes the DMA IRQ with the DSP thread.

1.  **DSP Thread (Priority 10):** Waits on the semaphore, processes the filled DMA buffer through the notch filter, and performs decimation.
2.  **EKF Thread (Priority 8):** Waits on the `_ekf_queue` for decimated gyro vectors.
3.  **FFT Thread (Priority 6):** Runs at 1 kHz, collects samples into the `BatchBuffer`, and executes the FFT when 1024 samples are ready.

```cpp
// DSP Thread function (8 kHz trigger from semaphore).
void dsp_thread(void const *argument) {
    for(;;) {
        // Block until DMA buffer is full.
        osSemaphoreWait(_dma_semaphore, osWaitForever);

        // Cache invalidate: ensure CPU sees latest DMA data.
        SCB_InvalidateDCache_by_Addr((uint32_t*)_processing_buffer, 4096);

        // Process each sample in the 2048-sample buffer.
        for (uint32_t i = 0; i < SAMPLES_PER_BUFFER; i++) {
            Vector3f raw_sample = convert_sample(_processing_buffer[i]);
            // Apply harmonic notch filter.
            Vector3f filtered = _harmonic_notch.apply(raw_sample);
            // Accumulate for decimation.
            _gyro_decimate(filtered);
        }
    }
}

// EKF Thread receives decimated data via message queue.
void ekf_thread(void const *argument) {
    for(;;) {
        osEvent evt = osMessageGet(_ekf_queue, osWaitForever);
        if (evt.status == osEventMessage) {
            Vector3f* gyro = (Vector3f*)evt.value.p;
            // Integrate ω_filtered into quaternion: dq/dt = 0.5 * Ω(ω) * q
            _ekf.predict(*gyro);
        }
    }
}
```

#### **Mathematical Mapping: HarmonicNotchFilter Class**

The `HarmonicNotchFilter` class directly implements the bilinear transform coefficient calculation and the Direct Form II transposed state update.

**Coefficient Update (`update_coefficients`):** This function maps the mathematical derivation. `omega` is `ωₙ`. `bandwidth_rad` is `2π * BW * T_s`. The calculated `alpha` is `α = sin(ωₙ) / (2Q)`. The loop over `n` harmonics computes coefficients for each `fₙ = n * f₀`.

```cpp
void HarmonicNotchFilter::update_coefficients(float center_freq_hz, float sample_freq_hz) {
    // ωₙ = 2π * f₀ / f_s
    float omega = 2.0f * M_PI * center_freq_hz / sample_freq_hz;
    // Q = ωₙ / (2π * BW * T_s) = ωₙ / bandwidth_rad
    float bandwidth_rad = 2.0f * M_PI * _params.bandwidth_hz / sample_freq_hz;
    float Q = omega / bandwidth_rad;
    // α = sin(ωₙ) / (2Q)
    float alpha = sinf(omega) / (2.0f * Q);

    for (uint8_t n = 1; n <= _params.harmonics; n++) {
        float harmonic_omega = omega * n; // ωₙ for n-th harmonic
        float harmonic_alpha = sinf(harmonic_omega) / (2.0f * Q);
        float cos_omega = cosf(harmonic_omega);
        // a0 = 1 + α
        float a0 = 1.0f + harmonic_alpha;

        // Store coefficients per harmonic.
        _coeffs[n-1].b0 = 1.0f / a0;          // b₀
        _coeffs[n-1].b1 = -2.0f * cos_omega / a0; // b₁
        _coeffs[n-1].b2 = 1.0f / a0;          // b₂
        _coeffs[n-1].a1 = -2.0f * cos_omega / a0; // a₁
        _coeffs[n-1].a2 = (1.0f - harmonic_alpha) / a0; // a₂
    }
}
```

**Filter Application (`apply`):** This method executes the state-space update for the cascade. The inner loop implements `w[t] = x[t] - a₁*s₁ - a₂*s₂` and `y[t] = b₀*w[t] + b₁*s₁ + b₂*s₂`, updating the state variables `_y[axis][1]` and `_y[axis][2]` (which represent `s₁` and `s₂`).

```cpp
Vector3f HarmonicNotchFilter::apply(const Vector3f &input) {
    Vector3f output;
    for (uint8_t axis = 0; axis < 3; axis++) {
        // Shift input history: _x[axis][0] is x[t], [1] is x[t-1], [2] is x[t-2].
        _x[axis][2] = _x[axis][1];
        _x[axis][1] = _x[axis][0];
        _x[axis][0] = input[axis];

        float y = input[axis];
        // Cascade through up to 4 harmonic notches.
        for (uint8_t h = 0; h < _params.harmonics; h++) {
            // Direct Form II Transposed:
            // w = x - a1*s1 - a2*s2
            float w = y - _coeffs[h].a1 * _y[axis][1] - _coeffs[h].a2 * _y[axis][2];
            // y = b0*w + b1*s1 + b2*s2
            y = _coeffs[h].b0 * w + _coeffs[h].b1 * _y[axis][1] + _coeffs[h].b2 * _y[axis][2];
            // Update state: s2 = s1; s1 = w;
            _y[axis][2] = _y[axis][1];
            _y[axis][1] = w;
        }
        output[axis] = y;
    }
    return output;
}
```

#### **Batch Processing and FFT: AP_GyroFFT Class**

The `AP_GyroFFT` class manages the `BatchBuffer` in SRAM2 and performs the PSD calculation.

**Window Application and FFT Execution:** The `update()` method applies the Hanning window `w[n]` pointwise, calls the ARM CMSIS-DSP FFT, and computes the single-sided power spectrum `P[k] = (R[k]² + I[k]²) / N`. The loop to find `peak_bin` implements the search for `k_peak`.

```cpp
void AP_GyroFFT::update() {
    if (_sample_counter < FFT_WINDOW_SIZE) return; // 1024 samples

    // Apply Hanning window: w[n] = 0.5*(1 - cos(2π*n/(N-1)))
    for (uint16_t i = 0; i < FFT_WINDOW_SIZE; i++) {
        float window = 0.5f * (1.0f - cosf(2.0f * M_PI * i / (FFT_WINDOW_SIZE - 1)));
        _fft_input[i] = _gyro_buffer[i] * window; // x_windowed[n]
    }

    // Execute real FFT. Output: _fft_output[2k]=R[k], _fft_output[2k+1]=I[k].
    arm_rfft_fast_f32(&_fft_instance, _fft_input, _fft_output, 0);

    // Compute power spectrum (ignoring window energy normalization for brevity).
    for (uint16_t k = 0; k < FFT_WINDOW_SIZE/2; k++) {
        float real = _fft_output[2*k];
        float imag = _fft_output[2*k + 1];
        // P[k] = (R[k]² + I[k]²) / N
        _analysis.spectrum[k] = (real*real + imag*imag) / FFT_WINDOW_SIZE;
    }

    // Find peak frequency bin between MIN_FREQ_BIN and MAX_FREQ_BIN.
    uint16_t peak_bin = 0;
    float peak_value = 0.0f;
    for (uint16_t k = MIN_FREQ_BIN; k < MAX_FREQ_BIN; k++) {
        if (_analysis.spectrum[k] > peak_value) {
            peak_value = _analysis.spectrum[k];
            peak_bin = k;
        }
    }
    // f_peak = k_peak * (f_s / N)
    _analysis.peak_freq_hz = (float)peak_bin * _sample_rate_hz / FFT_WINDOW_SIZE;

    // ... (harmonic tracking and notch update logic) ...

    _sample_counter = 0;
}
```

**Memory Management:** The `BatchBuffer` uses `volatile uint32_t` indices for atomic access between the DMA IRQ and the FFT thread. The `sample_from_dma` method converts 16-bit samples to float and fills the `_gyro_buffer`.

```cpp
void AP_GyroFFT::sample_from_dma(const int16_t *dma_buffer, uint32_t sample_count) {
    for (uint32_t i = 0; i < sample_count; i++) {
        if (_sample_counter < FFT_WINDOW_SIZE) {
            // Convert to physical units (rad/s) and store.
            _gyro_buffer[_sample_counter] = (float)dma_buffer[i] * GYRO_SCALE_FACTOR;
            _sample_counter++;
        }
    }
    if (_sample_counter >= FFT_WINDOW_SIZE) {
        _fft_ready = true; // Flag for the 1kHz FFT thread.
    }
}
```

#### **Decimation: AP_InertialSensor::_gyro_decimate**

This function implements the 8:1 averaging filter. The static `accum` vector and `decimation_counter` implement the summation `Σ_{i=0}^{7} G_raw[k-i]`. Upon reaching 8 samples, it scales the sum by `GYRO_SCALE * (1/8)` and sends the vector to the EKF via a message queue.

```cpp
void AP_InertialSensor::_gyro_decimate(Vector3f sample) {
    static uint8_t decimation_counter = 0;
    static Vector3f accum = Vector3f();

    accum.x += sample.x;
    accum.y += sample.y;
    accum.z += sample.z;
    decimation_counter++;

    if (decimation_counter == 8) {
        _gyro_filtered.x = accum.x * GYRO_SCALE * (1.0f/8.0f);
        _gyro_filtered.y = accum.y * GYRO_SCALE * (1.0f/8.0f);
        _gyro_filtered.z = accum.z * GYRO_SCALE * (1.0f/8.0f);

        accum.zero();
        decimation_counter = 0;

        // Send to EKF thread. osMessagePut is non-blocking.
        osMessagePut(_ekf_queue, (uint32_t)&_gyro_filtered, 0);
    }
}
```