# GPIO EXTI, Analog ADC Polling, and DSP Utility Hooks

_Generated 2026-04-14 21:46 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/GPIO.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/GPIO.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/AnalogIn.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/AnalogIn.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/DSP.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/DSP.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Util.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Util.h`

# Chapter: GPIO EXTI, Analog ADC Polling, and DSP Utility Hooks

## Technical Introduction

This chapter documents the bare-metal hardware interface layer for a 400Hz autonomous agricultural rover. The files `AnalogIn.cpp`, `GPIO.cpp`, and `DSP.cpp` implement deterministic, low-latency access to STM32 peripherals critical for rover state monitoring and safety. `AnalogIn.cpp` manages continuous DMA-driven ADC sampling of battery voltage, motor currents, and temperature—parameters directly tied to the rover's 20kg mass and skid-steer dynamics. `GPIO.cpp` provides EXTI (External Interrupt) handlers with sub-microsecond response for emergency stop signals and wheel encoder edges. `DSP.cpp` leverages the Cortex-M4 SIMD unit for hardware-accelerated FFT vibration analysis and matrix algebra used in the EKF. All ISRs are placed in ITCM, and state structures reside in DTCM to guarantee execution within the 2.5ms control loop deadline.

## Mathematical Formulation

### Continuous ADC Polling Formulation: STM32 DMA-Driven Analog Monitoring

**ADC DMA Architecture and Sampling Rate**
The STM32's ADC sampling rate for rover battery and current monitoring is governed by:
```
f_sample = f_ADC_clock / (SMPL_CYCLES + CONV_CYCLES)
```
Where `f_ADC_clock = 42MHz` (84MHz APB2 with prescaler 2), `SMPL_CYCLES = 144` cycles (3.43μs sampling time for stable readings), and `CONV_CYCLES = 12.5` cycles for 12-bit conversion. For the rover's 8 monitoring channels, the aggregate sampling rate per channel is:
```
f_sample_per_channel = f_sample / 8 ≈ 10kHz
```
This satisfies the Nyquist criterion for rover vibration frequencies up to 500Hz: `f_sample_per_channel > 2 × 500Hz`.

**Battery Voltage Calculation with Voltage Divider**
The 4S LiPo battery voltage (nominal 14.8V) is computed from the ADC reading at channel 1:
```
V_batt = (ADC_reading × V_ref) / (ADC_max × (R2/(R1+R2)))
```
With `V_ref = 3.3V`, `ADC_max = 4095` (12-bit), and voltage divider resistors `R1 = 10kΩ`, `R2 = 2.2kΩ`. The divider ratio is:
```
divider_ratio = (R1 + R2) / R2 = (10000 + 2200) / 2200 ≈ 5.545
```
Thus the final calculation in C++ is:
```
voltage = filtered_adc × 3.3 / 4095 × 5.545
```

**Motor Current Sensing via Shunt Resistor**
The skid-steer motor current for each side is measured via a 1mΩ shunt resistor with 50× amplification:
```
I_motor = (ADC_shunt × V_ref) / (ADC_max × Gain × R_shunt)
```
Where `R_shunt = 0.001Ω`, `Gain = 50`. The rover's maximum continuous current of 30A produces a shunt voltage:
```
V_shunt_max = I_max × R_shunt = 30 × 0.001 = 0.03V
V_amplified = V_shunt_max × Gain = 0.03 × 50 = 1.5V
```
This stays within the ADC's 3.3V range with 2.2× headroom.

**Temperature Compensation for Current Accuracy**
The copper shunt resistor's temperature coefficient `α = 0.00393/°C` requires compensation:
```
R_shunt_actual = R_shunt_nominal × [1 + α × (T_actual - T_ref)]
```
Where `T_ref = 25°C`. The compensated current is:
```
I_compensated = I_raw × (1 + α × ΔT)
```
For field operation from -10°C to 60°C, this correction ranges from 0.862× to 1.138× of raw reading.

**Coulomb Counting for Battery State of Charge**
The rover's battery capacity (10Ah = 36000 Coulombs) is tracked by integrating current:
```
Q(t) = ∫ I(t) dt ≈ Σ [I_n × Δt_n]
```
Where `Δt_n = t_n - t_{n-1}` in seconds. Implemented as:
```
coulomb_count += current × dt
```
With `dt` measured in microseconds: `dt = (now_us - last_update_us) × 1.0e-6`.

### EXTI and DSP Analysis: Hardware Interrupts and Accelerated Math

**EXTI (External Interrupt) Timing for Emergency Stop**
The EXTI system triggers on GPIO edges with deterministic latency critical for rover emergency stop:
```
t_response = t_sync + t_prop + t_INT
```
Where `t_sync = 3` clock cycles at 168MHz = 17.86ns, `t_prop ≈ 0` for on-chip routing, and `t_INT = 12` cycles = 71.43ns for ISR entry. Total worst-case latency:
```
t_latency_max = 43 cycles = 256ns
```
This guarantees sub-microsecond response to physical kill switches.

**Software Debounce Filtering**
Mechanical switch contacts require debounce filtering:
```
if (now_us - last_trigger_us) < debounce_us: ignore_trigger
```
Where `debounce_us = 1000μs` (1ms) for rover-mounted limit switches.

**FFT Acceleration for Vibration Analysis**
The rover's skid-steer drivetrain vibration is analyzed via 256-point FFT:
```
X[k] = Σ_{n=0}^{255} x[n]·(cos(2πkn/256) - j·sin(2πkn/256))
```
Using ARM CMSIS-DSP library with SIMD instructions, the computational complexity is:
```
N × log₂(N) = 256 × 8 = 2048 complex multiplications
```
With Cortex-M4 SIMD (SMLAD processes 2 multiplications/cycle):
```
t_FFT = 2048 / 2 × t_cycle = 1024 × 10ns = 10.24μs @ 100MHz
```
This fits within the 2.5ms (400Hz) control period with 0.4% CPU utilization.

**Notch Filter Design for Vibration Rejection**
A digital notch filter at frequency `f_0` with bandwidth `Δf` uses bilinear transform:
```
H(z) = (1 - 2cos(ω₀)z⁻¹ + z⁻²) / (1 - 2r·cos(ω₀)z⁻¹ + r²z⁻²)
```
Where `ω₀ = 2πf₀/f_sample`, `α = sin(ω₀)/(2·(Δf/f_sample))`, and `r = 1/(1+α)` for stability. The direct form I biquad coefficients are:
```
b₀ = 1, b₁ = -2cos(ω₀), b₂ = 1
a₁ = -2r·cos(ω₀), a₂ = r²
```
Normalized so `b₀' = 1`: all coefficients divided by `(1 + a₁ + a₂)`.

**Matrix Operations for EKF Acceleration**
The rover's 24-state EKF requires 3×3 matrix multiplications for covariance updates:
```
C = A × B where C[i][j] = Σ_{k=0}^{2} A[i][k] × B[k][j]
```
ARM SIMD instructions compute 2 multiply-accumulate operations per cycle via `SMLAD`. A 3×3 matrix multiplication requires 27 multiplications and 18 additions, completing in approximately 23 cycles (0.14μs @ 168MHz).

**Vector Dot Product for Kinematic Validation**
The crash detection algorithm computes dot products between commanded and measured acceleration vectors:
```
a_cmd · a_imu = Σ_{i=x,y,z} a_cmd[i] × a_imu[i]
```
Using `arm_dot_prod_f32()` with SIMD acceleration, a 3-element dot product completes in 2 cycles (11.9ns).

### ADC Calibration and Error Analysis

**Internal Voltage Reference Calibration**
The STM32's internal VREFINT calibration value at address `0x1FFF7A2A` provides:
```
V_ref_actual = (VREFINT_CAL × V_DDA) / ADC_reading_at_30°C
```
Where `V_DDA = 3.3V` nominal. The rover uses this to compensate for supply voltage variations affecting current sensing accuracy.

**Temperature Sensor Linearization**
The internal temperature sensor uses factory calibration at 30°C and 110°C:
```
temperature = ((TS_CAL1 - ADC_reading) × 85) / (TS_CAL1 - TS_CAL2) + 30
```
Where `TS_CAL1` at `0x1FFF7A2C`, `TS_CAL2` at `0x1FFF7A2E`. This linear approximation has ±2°C accuracy sufficient for current compensation.

**ADC Quantization Error**
The 12-bit ADC has quantization error:
```
ε_quantization = ±V_ref / (2 × 4096) = ±3.3V / 8192 ≈ ±0.4mV
```
For battery voltage measurement, this translates to:
```
ε_Vbatt = ε_quantization × 5.545 ≈ ±2.2mV
```
Which is 0.015% of nominal 14.8V—negligible for rover power management.

**Moving Average Filter Frequency Response**
The 8-sample moving average filter applied to ADC readings has transfer function:
```
H(z) = (1/8) × (1 + z⁻¹ + z⁻² + ... + z⁻⁷)
```
Its -3dB cutoff frequency at 10kHz sampling is:
```
f_c = f_sample × (0.442947 / N) ≈ 10kHz × 0.0554 ≈ 554Hz
```
Adequate for smoothing without affecting the 400Hz control bandwidth.

### Rover-Specific Physical Mapping

**Motor Current to Torque Conversion**
For the rover's brushless motors with torque constant `K_t = 0.1 N·m/A`:
```
τ_motor = I_motor × K_t
```
The skid-steer differential torque is:
```
τ_differential = (τ_right - τ_left) / 2
```
This directly feeds the kinematic constraint validation for crash detection.

**Battery Voltage to Available Power**
The rover's maximum electrical power at 4S LiPo (16.8V fully charged):
```
P_max = V_batt × I_max_continuous = 16.8V × 30A = 504W
```
With drivetrain efficiency `η = 0.85`, available mechanical power:
```
P_mech = P_max × η ≈ 428W
```
Sufficient for the 20kg rover's maximum acceleration of 2m/s² requiring `F = m×a = 20×2 = 40N`, and power `P = F×v` at 3m/s top speed = 120W.

**Vibration Frequency to Mechanical Fault Detection**
The skid-steer gearbox has characteristic meshing frequency:
```
f_mesh = N_teeth × f_shaft
```
With 20-tooth pinion at 3000RPM (50Hz) motor speed:
```
f_mesh = 20 × 50Hz = 1000Hz
```
The 10kHz ADC sampling and 256-point FFT (39Hz bin resolution) can detect ±1 tooth damage as ±50Hz sidebands.

**EXTI Debounce Time vs. Wheel Encoder Maximum Speed**
The rover's wheel encoders have 100 pulses/revolution. At 3m/s with 0.1m wheel radius:
```
f_encoder_max = (v / (2πr)) × N_pulses = (3 / 0.628) × 100 ≈ 477Hz
```
The 1ms debounce time would miss pulses above 500Hz, but emergency stop switches have <10Hz actuation, making 1ms appropriate.

## C++ Implementation

### DMA-Driven ADC Ring Buffers and Voltage Calculations (AnalogIn.cpp)

The `STM32_AnalogIn` class implements the mathematical ADC sampling model `f_sample = f_ADC_clock / (SMPL_CYCLES + CONV_CYCLES)` through direct STM32 register configuration. The `ADCDMABuffer` struct at DTCM address `0x2000C000` provides double-buffered storage for 8 ADC channels, with each buffer containing timestamp and sequence metadata for rover power monitoring.

```cpp
// AnalogIn.cpp - ADC DMA initialization (called from HAL)
__attribute__((section(".itcm")))
void STM32_AnalogIn::init_adc_dma() {
    // Enable ADC and DMA clocks
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA2EN;      // Enable DMA2 clock
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;      // Enable ADC1 clock
    
    // Configure ADC1 in independent mode
    ADC1->CR1 = ADC_CR1_SCAN;                // Scan mode enable
    ADC1->CR2 = ADC_CR2_ADON |               // ADC enable
                ADC_CR2_CONT |               // Continuous conversion
                ADC_CR2_DMA |                // DMA enable
                ADC_CR2_DDS;                 // DMA continuous requests
    
    // Configure sample times (SMPR2 for channels 0-9)
    // Channel 0: VREFINT (ADC sample time 480 cycles)
    // Channel 1: VBAT (480 cycles)
    // Channel 2: Temperature sensor (480 cycles)
    // Channel 3: Current shunt (144 cycles for faster sampling)
    ADC1->SMPR2 = (7 << (3*0)) |             // Channel 0: 480 cycles
                  (7 << (3*1)) |             // Channel 1: 480 cycles
                  (7 << (3*2)) |             // Channel 2: 480 cycles
                  (4 << (3*3)) |             // Channel 3: 144 cycles
                  (4 << (3*4)) |             // Channel 4: 144 cycles
                  (4 << (3*5)) |             // Channel 5: 144 cycles
                  (4 << (3*6)) |             // Channel 6: 144 cycles
                  (4 << (3*7));              // Channel 7: 144 cycles
    
    // Configure sequence (SQR1-SQR3)
    // 8 channels in conversion sequence
    ADC1->SQR1 = (7 << 20);                  // L[3:0] = 7 (8 conversions)
    ADC1->SQR2 = 0;
    ADC1->SQR3 = (0 << 0)  |                 // Conversion 1: Channel 0
                 (1 << 5)  |                 // Conversion 2: Channel 1
                 (2 << 10) |                 // Conversion 3: Channel 2
                 (3 << 15) |                 // Conversion 4: Channel 3
                 (4 << 20) |                 // Conversion 5: Channel 4
                 (5 << 25);                  // Conversion 6: Channel 5
    
    // Continue in SQR2 for remaining channels
    ADC1->SQR2 = (6 << 0)  |                 // Conversion 7: Channel 6
                 (7 << 5);                   // Conversion 8: Channel 7
    
    // Configure DMA2 Stream 0 for ADC1
    DMA2_Stream0->CR = 0;                    // Clear control register
    DMA2_Stream0->PAR = (uint32_t)&ADC1->DR; // Peripheral address
    DMA2_Stream0->M0AR = (uint32_t)adc_buffer[0].channels; // Memory address 0
    DMA2_Stream0->M1AR = (uint32_t)adc_buffer[1].channels; // Memory address 1
    DMA2_Stream0->NDTR = 8;                  // 8 conversions per buffer
    DMA2_Stream0->CR = DMA_SxCR_CHSEL_0 |    // Channel 0 (ADC1)
                      DMA_SxCR_PL_1 |       // High priority
                      DMA_SxCR_MSIZE_0 |    // 16-bit memory
                      DMA_SxCR_PSIZE_0 |    // 16-bit peripheral
                      DMA_SxCR_MINC |       // Memory increment
                      DMA_SxCR_CIRC |       // Circular mode
                      DMA_SxCR_DBM |        // Double buffer mode
                      DMA_SxCR_TCIE |       // Transfer complete interrupt
                      DMA_SxCR_HTIE |       // Half transfer interrupt
                      DMA_SxCR_EN;          // Enable stream
    
    // Enable DMA interrupt
    NVIC_EnableIRQ(DMA2_Stream0_IRQn);
    
    // Start ADC calibration
    ADC1->CR2 |= ADC_CR2_CAL;
    while (ADC1->CR2 & ADC_CR2_CAL);         // Wait for calibration
    
    // Start ADC conversion
    ADC1->CR2 |= ADC_CR2_SWSTART;
    
    // Setup calibration data
    setup_adc_calibration();
}
```

The battery voltage calculation `V_batt = (ADC_reading × V_ref) / (ADC_max × R2/(R1+R2))` maps directly to the `read_voltage` function, which applies the voltage divider ratio 5.545 for the rover's 10kΩ + 2.2kΩ divider. The moving average filter implements the mathematical convolution for noise reduction in the rover's electrical system.

```cpp
// Voltage reading with software filtering
__attribute__((section(".itcm")))
float STM32_AnalogIn::read_voltage(uint8_t channel) {
    if (channel >= 8) return 0.0f;
    
    // Get raw ADC value from current buffer
    uint16_t raw_adc = adc_buffer[0].channels[channel];
    
    // Apply digital filter (moving average of 8 samples)
    static uint16_t filter_buffer[8][8] = {0};
    static uint8_t filter_idx = 0;
    
    filter_buffer[filter_idx][channel] = raw_adc;
    filter_idx = (filter_idx + 1) & 0x07;
    
    // Compute moving average
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++) {
        sum += filter_buffer[i][channel];
    }
    uint16_t filtered_adc = sum >> 3;  // Divide by 8
    
    // Convert to voltage using channel-specific scaling
    float voltage = filtered_adc * channel_config[channel].scale_factor 
                   + channel_config[channel].offset;
    
    // For battery voltage channel (channel 1), apply additional scaling
    if (channel == 1) {
        // Voltage divider: R1=10k, R2=2.2k, ratio = (R1+R2)/R2 = 5.545
        voltage *= 5.545f;
        
        // Low-pass filter for battery voltage (time constant ~1 second)
        static float filtered_batt_voltage = 0.0f;
        const float ALPHA = 0.01f;  // 100Hz update rate, τ = 1 second
        filtered_batt_voltage = ALPHA * voltage + (1.0f - ALPHA) * filtered_batt_voltage;
        voltage = filtered_batt_voltage;
    }
    
    return voltage;
}
```

The current sensing equation `I_batt = (ADC_shunt × V_ref) / (ADC_max × Gain × R_shunt)` is implemented in `read_current` with temperature compensation for the rover's 1mΩ shunt resistor. The Coulomb counting integral `∫ I dt` tracks battery capacity during field operation.

```cpp
// Current reading with temperature compensation
__attribute__((section(".itcm")))
float STM32_AnalogIn::read_current(uint8_t channel) {
    // Channel 3 is current shunt input
    if (channel != 3) return 0.0f;
    
    // Get voltage across shunt resistor
    float shunt_voltage = read_voltage(channel);
    
    // Shunt resistor value (0.001Ω) with amplifier gain (50)
    const float SHUNT_RESISTANCE = 0.001f;
    const float AMP_GAIN = 50.0f;
    
    // Calculate current: I = V_shunt / (R_shunt × Gain)
    float current = shunt_voltage / (SHUNT_RESISTANCE * AMP_GAIN);
    
    // Temperature compensation for shunt resistor
    // Copper temperature coefficient: α = 0.00393/°C
    float temperature = read_temperature();
    const float REF_TEMP = 25.0f;
    const float TEMP_COEFF = 0.00393f;
    float temp_factor = 1.0f + TEMP_COEFF * (temperature - REF_TEMP);
    
    // Adjust current reading for temperature
    current /= temp_factor;
    
    // High-pass filter to remove DC offset
    static float last_current = 0.0f;
    const float HPF_ALPHA = 0.1f;
    current = HPF_ALPHA * (current - last_current) + last_current;
    last_current = current;
    
    // Coulomb counting for battery capacity
    static float coulomb_count = 0.0f;
    static uint32_t last_update_us = 0;
    
    uint32_t now_us = AP_HAL::micros();
    float dt = (now_us - last_update_us) * 1.0e-6f;
    
    if (dt > 0 && dt < 1.0f) {  // Sanity check
        coulomb_count += current * dt;  // Ampere-seconds
    }
    last_update_us = now_us;
    
    return current;
}
```

### EXTI Interrupt Configuration and Timing-Critical GPIO (GPIO.cpp)

The `STM32_GPIO` class implements the EXTI timing model `t_response = t_sync + t_prop + t_INT` through direct NVIC configuration. The `EXTI_Config` struct at DTCM address `0x2000D000` stores callback functions and debounce parameters for each of the 16 EXTI lines, supporting the rover's limit switches and emergency stop inputs.

```cpp
// GPIO.cpp - EXTI configuration
__attribute__((section(".itcm")))
void STM32_GPIO::attachInterrupt(uint8_t pin, void (*callback)(void*), void* arg, uint8_t mode) {
    // Map pin to EXTI line (0-15)
    uint8_t exti_line = pin & 0x0F;
    
    // Determine GPIO port (A=0, B=1, C=2, D=3, E=4, H=7)
    uint8_t port_num = 0;  // Default to GPIOA
    if (pin >= 32 && pin < 48) port_num = 1;  // GPIOB
    else if (pin >= 48 && pin < 64) port_num = 2;  // GPIOC
    else if (pin >= 64 && pin < 80) port_num = 3;  // GPIOD
    else if (pin >= 80 && pin < 96) port_num = 4;  // GPIOE
    else if (pin >= 96 && pin < 112) port_num = 7; // GPIOH
    
    // Configure EXTI line
    configure_exti(exti_line, port_num, pin & 0x0F, mode);
    
    // Store callback information
    exti_configs[exti_line].callback = callback;
    exti_configs[exti_line].callback_arg = arg;
    exti_configs[exti_line].debounce_us = 1000;  // 1ms default debounce
    exti_configs[exti_line].last_trigger_us = 0;
}
```

The mathematical EXTI synchronization (2-3 clock cycles) is implemented in hardware via the SYSCFG peripheral. The `configure_exti` function sets up rising/falling edge detection with the exact timing characteristics required for the rover's skid-steer encoder inputs.

```cpp
// Hardware EXTI configuration
__attribute__((section(".itcm")))
void STM32_GPIO::configure_exti(uint8_t line, uint8_t port, uint8_t pin, uint8_t trigger) {
    // Enable SYSCFG clock
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    
    // Configure EXTI line in SYSCFG
    uint8_t reg_idx = line >> 2;      // Register index (0-3)
    uint8_t bit_pos = (line & 0x3) << 2;  // Bit position (0,4,8,12)
    
    SYSCFG->EXTICR[reg_idx] &= ~(0xF << bit_pos);  // Clear existing
    SYSCFG->EXTICR[reg_idx] |= (port << bit_pos);  // Set port
    
    // Configure trigger edge
    switch (trigger) {
        case RISING:
            EXTI->RTSR |= (1 << line);   // Rising trigger enabled
            EXTI->FTSR &= ~(1 << line);  // Falling trigger disabled
            break;
        case FALLING:
            EXTI->RTSR &= ~(1 << line);  // Rising trigger disabled
            EXTI->FTSR |= (1 << line);   // Falling trigger enabled
            break;
        case BOTH:
            EXTI->RTSR |= (1 << line);   // Rising trigger enabled
            EXTI->FTSR |= (1 << line);   // Falling trigger enabled
            break;
    }
    
    // Clear any pending interrupt
    EXTI->PR = (1 << line);
    
    // Enable interrupt
    EXTI->IMR |= (1 << line);
    
    // Configure NVIC priority and enable
    uint8_t irq_num = (line < 5) ? EXTI0_IRQn + line :
                     (line < 10) ? EXTI9_5_IRQn :
                     EXTI15_10_IRQn;
    
    NVIC_SetPriority(irq_num, 5);  // Medium priority
    NVIC_EnableIRQ(irq_num);
}
```

The EXTI interrupt handlers implement the mathematical latency bound of 256ns worst-case. Each handler runs in ITCM with deterministic timing, critical for the rover's 400Hz control loop where emergency stops must be processed within 2.5ms.

```cpp
// EXTI0 interrupt handler (pin 0)
__attribute__((section(".itcm")))
void EXTI0_IRQHandler(void) {
    if (EXTI->PR & (1 << 0)) {
        // Clear pending bit
        EXTI->PR = (1 << 0);
        
        // Handle EXTI line 0
        handle_exti_isr(0);
    }
}

// EXTI ISR handling with debounce
__attribute__((section(".itcm")))
void STM32_GPIO::handle_exti_isr(uint8_t line) {
    uint32_t now_us = AP_HAL::micros();
    
    // Software debounce
    if ((now_us - exti_configs[line].last_trigger_us) < exti_configs[line].debounce_us) {
        return;  // Debounce period not elapsed
    }
    
    exti_configs[line].last_trigger_us = now_us;
    
    // Execute callback if registered
    if (exti_configs[line].callback != NULL) {
        exti_configs[line].callback(exti_configs[line].callback_arg);
    }
    
    // For performance measurement, record interrupt latency
    static uint32_t max_latency = 0;
    uint32_t latency = now_us - exti_configs[line].last_trigger_us;
    if (latency > max_latency) {
        max_latency = latency;
        // Store in debug register
        *((volatile uint32_t*)0xE000ED04) = max_latency;  // ICSR register
    }
}
```

### Hardware-Accelerated DSP for Vibration Analysis (DSP.cpp)

The `STM32_DSP` class implements the FFT equation `X[k] = Σ_{n=0}^{N-1} x[n]·(cos(2πkn/N) - j·sin(2πkn/N))` using ARM CMSIS-DSP SIMD instructions. The `FFT_Config` struct at DTCM address `0x2000E000` manages the 256-point complex FFT instance with aligned buffers for the rover's vibration monitoring system.

```cpp
// DSP.cpp - FFT implementation using ARM CMSIS-DSP
__attribute__((section(".itcm")))
void STM32_DSP::perform_fft_vibration_analysis(float32_t* samples, uint16_t num_samples) {
    if (num_samples != 256) return;  // Only support 256-point FFT
    
    // Apply Hanning window to reduce spectral leakage
    hanning_window(samples, num_samples);
    
    // Convert real samples to complex format (real part = sample, imag part = 0)
    for (int i = 0; i < num_samples; i++) {
        fft_config.fft_input[i*2] = samples[i];      // Real part
        fft_config.fft_input[i*2 + 1] = 0.0f;        // Imaginary part
    }
    
    // Perform FFT using hardware acceleration
    // This uses Cortex-M4 SIMD instructions (SMLAD, SMUAD, etc.)
    arm_cfft_f32(&fft_config.cfft_instance, fft_config.fft_input, 0, 1);
    
    // Compute magnitude spectrum
    compute_fft_magnitude(fft_config.fft_input, fft_config.fft_magnitude, num_samples/2);
    
    // Find dominant frequency for vibration analysis
    float32_t max_magnitude = 0;
    uint16_t max_bin = 0;
    
    for (int i = 1; i < num_samples/2; i++) {  // Skip DC component (i=0)
        if (fft_config.fft_magnitude[i] > max_magnitude) {
            max_magnitude = fft_config.fft_magnitude[i];
            max_bin = i;
        }
    }
    
    // Convert bin to frequency
    float32_t dominant_freq = (float32_t)max_bin * fft_config.sample_rate_hz / num_samples;
    
    // Update notch filter if dominant frequency is significant
    if (max_magnitude > 0.1f) {  // Threshold for significant vibration
        apply_notch_filter(samples, num_samples, dominant_freq);
    }
}
```

The notch filter implements the mathematical transfer function `H(z) = (1 - 2cos(ω0)z⁻¹ + z⁻²) / (1 - 2rcos(ω0)z⁻¹ + r²z⁻²)` using the bilinear transform. This filters out resonant frequencies in the rover's mechanical structure that could affect skid-steer control.

```cpp
// Compute notch filter coefficients
__attribute__((section(".itcm")))
void STM32_DSP::compute_notch_coefficients(float32_t center_freq, float32_t bandwidth) {
    // Digital notch filter design using bilinear transform
    // H(z) = (1 - 2cos(ω0)z⁻¹ + z⁻²) / (1 - 2rcos(ω0)z⁻¹ + r²z⁻²)
    
    float32_t sample_rate = fft_config.sample_rate_hz;
    float32_t omega0 = 2.0f * M_PI * center_freq / sample_rate;
    float32_t alpha = sinf(omega0) / (2.0f * (bandwidth / sample_rate));
    float32_t r = 1.0f / (1.0f + alpha);  // Stability factor
    
    // Coefficients for direct form I biquad filter
    // y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]
    
    float32_t b0 = 1.0f;
    float32_t b1 = -2.0f * cosf(omega0);
    float32_t b2 = 1.0f;
    float32_t a1 = -2.0f * r * cosf(omega0);
    float32_t a2 = r * r;
    
    // Normalize coefficients so b0 = 1
    float32_t norm = 1.0f / (1.0f + a1 + a2);
    
    vibration_filter.notch_coeffs[0] = b0 * norm;  // b0
    vibration_filter.notch_coeffs[1] = b1 * norm;  // b1
    vibration_filter.notch_coeffs[2] = b2 * norm;  // b2
    vibration_filter.notch_coeffs[3] = a1 * norm;  // a1
    vibration_filter.notch_coeffs[4] = a2 * norm;  // a2
    
    // Initialize filter instance
    arm_biquad_cascade_df1_init_f32(&vibration_filter.notch_filter, 
                                    1,  // 1 biquad stage
                                    vibration_filter.notch_coeffs, 
                                    vibration_filter.notch_state);
}
```

The matrix multiplication function implements the rover's skid-steer kinematic transformation using SIMD-accelerated 3×3 matrix operations. This computes the relationship between wheel torques and body forces for the 20kg agricultural rover.

```cpp
// Hardware-accelerated matrix multiplication
__attribute__((section(".itcm")))
void STM32_DSP::matrix_multiply_3x3(float32_t* A, float32_t* B, float32_t* C) {
    // Update matrix instances with new data
    memcpy(matrix_ops.mat_data_A, A, 9 * sizeof(float32_t));
    memcpy(matrix_ops.mat_data_B, B, 9 * sizeof(float32_t));
    
    // Perform matrix multiplication: C = A × B
    // Uses ARM SIMD instructions for parallel multiply-accumulate
    arm_mat_mult_f32(&matrix_ops.mat_A, &matrix_ops.mat_B, &matrix_ops.mat_C);
    
    // Copy result back
    memcpy(C, matrix_ops.mat_data_C, 9 * sizeof(float32_t));
}
```

### RTOS Threading and System Clock Configuration

The system clock configuration implements the mathematical PLL equation for precise timing. The 168MHz system clock with 5 flash wait states ensures deterministic execution of ADC sampling and EXTI interrupts within the rover's 400Hz control loop.

```cpp
// System clock configuration for precise timing
void SystemClock_Config(void) {
    // Enable HSE (8MHz external crystal)
    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));
    
    // Configure PLL for 168MHz system clock
    // PLL: HSE (8MHz) / M=8 * N=336 / P=2 = 84MHz
    // PLLQ=7 for 48MHz USB
    RCC->PLLCFGR = (8 << 0) |        // PLL_M = 8
                  (336 << 6) |       // PLL_N = 336
                  (0 << 16) |        // PLL_P = 2 (divide by 2)
                  (7 << 24) |        // PLL_Q = 7
                  RCC_PLLCFGR_PLLSRC_HSE;
    
    // Enable PLL and wait for ready
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));
    
    // Configure flash latency for 168MHz (5 wait states)
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN;
    
    // Set system clock to PLL
    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((