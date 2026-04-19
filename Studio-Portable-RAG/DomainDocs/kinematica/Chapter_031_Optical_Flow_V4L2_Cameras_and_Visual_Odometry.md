# Optical Flow Sensors, V4L2 Cameras, and Visual Odometry

_Generated 2026-04-14 23:33 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/CameraSensor.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/CameraSensor.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/CameraSensor_Mt9v117.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/CameraSensor_Mt9v117.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/CameraSensor_Mt9v117_Patches.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/VideoIn.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/VideoIn.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/OpticalFlow_Onboard.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_Linux/OpticalFlow_Onboard.h`

# Optical Flow Sensors, V4L2 Cameras, and Visual Odometry

## Technical Introduction

The `CameraSensor.cpp`, `CameraSensor_Mt9v117.cpp`, `VideoIn.cpp`, and `OpticalFlow_Onboard.cpp` files implement the visual perception pipeline for ArduPilot's Linux-based autonomous agricultural rover. These drivers provide low-latency, deterministic image acquisition and optical flow computation essential for terrain-relative navigation when GPS is unavailable or unreliable.

For the 20kg skid-steer rover with 400Hz control loops, these files provide:
- **V4L2 Camera Interface**: Linux Video4Linux2 kernel API for deterministic frame capture from MT9V117 global shutter sensors
- **Onboard Optical Flow**: ARM NEON-accelerated Lucas-Kanade feature tracking for velocity estimation
- **Visual Odometry Integration**: Frame-to-frame motion estimation fused with IMU data for drift-corrected positioning
- **Sensor-Specific Calibration**: MT9V117 register patching for optimal exposure and gain control in varying agricultural lighting

The system ensures sub-pixel optical flow accuracy at 100Hz update rates, enabling centimeter-level velocity estimation during aggressive maneuvers over uneven terrain. The visual odometry pipeline provides backup positioning when the rover operates under tree canopies or near structures that degrade GPS signals.

## Mathematical Formulation: Optical Flow Sensors, V4L2 Cameras, and Visual Odometry

### Skid-Steer Kinematics and Visual Motion Constraints

For a differential drive rover with wheel separation \( T = 0.5 \) m and wheel radius \( R = 0.1 \) m, the relationship between measured optical flow and vehicle motion must account for both translation and rotation. The camera is mounted at height \( h = 0.5 \) m above ground with pitch angle \( \theta = -30^\circ \) downward.

The observed optical flow field for a pure translation \( \mathbf{v} = [v_x, v_y]^T \) at ground plane \( z = 0 \) is:

\[
\begin{bmatrix} u \\ v \end{bmatrix} = \frac{1}{h/\cos\theta} \begin{bmatrix} f & 0 & -x \\ 0 & f & -y \end{bmatrix} \begin{bmatrix} v_x \\ v_y \\ 0 \end{bmatrix}
\]

Where \( f = 250 \) pixels is the focal length, and \( (x, y) \) are image coordinates relative to principal point.

For pure rotation about the yaw axis with rate \( \dot{\psi} \):

\[
\begin{bmatrix} u \\ v \end{bmatrix}_{\text{rot}} = \dot{\psi} \begin{bmatrix} -y \\ x \end{bmatrix}
\]

The total optical flow is the superposition:

\[
\mathbf{f}_{\text{total}} = \mathbf{f}_{\text{trans}} + \mathbf{f}_{\text{rot}}
\]

### Lucas-Kanade Optical Flow Mathematics

The Lucas-Kanade algorithm assumes constant flow in a local window \( W \) of size \( 15 \times 15 \) pixels. For each feature point \( \mathbf{x} = [x, y]^T \), we solve:

\[
\begin{bmatrix} \sum_{W} I_x^2 & \sum_{W} I_x I_y \\ \sum_{W} I_x I_y & \sum_{W} I_y^2 \end{bmatrix} \begin{bmatrix} u \\ v \end{bmatrix} = - \begin{bmatrix} \sum_{W} I_x I_t \\ \sum_{W} I_y I_t \end{bmatrix}
\]

Where:
- \( I_x, I_y \) = spatial image gradients computed via 5-tap Sobel filter
- \( I_t \) = temporal gradient between consecutive frames
- The sums are over the window \( W \)

The system is solved via Cholesky decomposition:

\[
\mathbf{A} = \begin{bmatrix} A_{xx} & A_{xy} \\ A_{xy} & A_{yy} \end{bmatrix}, \quad \mathbf{b} = \begin{bmatrix} b_x \\ b_y \end{bmatrix}
\]
\[
u = \frac{A_{yy} b_x - A_{xy} b_y}{A_{xx} A_{yy} - A_{xy}^2}, \quad v = \frac{A_{xx} b_y - A_{xy} b_x}{A_{xx} A_{yy} - A_{xy}^2}
\]

### MT9V117 Sensor Register Mathematics

The MT9V117 CMOS sensor uses I²C register programming for exposure and gain control. Key registers:

- **0x03: COARSE_INTEGRATION_TIME**: Exposure time in line periods
  \[
  t_{\text{exp}} = (\text{REG}_{03} + 1) \times t_{\text{line}}
  \]
  Where \( t_{\text{line}} = \frac{H_{\text{total}}}{f_{\text{pclk}}} \), with \( H_{\text{total}} = 784 \) pixels, \( f_{\text{pclk}} = 27 \) MHz

- **0x0A: ANALOG_GAIN**: Analog gain in dB
  \[
  G_{\text{analog}} = 10^{\frac{\text{REG}_{0A} \times 0.3}{20}}
  \]

- **0x0B: DIGITAL_GAIN**: Digital gain multiplier
  \[
  G_{\text{digital}} = \frac{\text{REG}_{0B}}{32.0}
  \]

Total gain: \( G_{\text{total}} = G_{\text{analog}} \times G_{\text{digital}} \)

### V4L2 Buffer Management Mathematics

The Video4Linux2 memory-mapped buffer system uses DMA for zero-copy frame transfer. For \( N = 4 \) buffers of resolution \( 752 \times 480 \) at 10-bit depth:

\[
\text{Buffer size} = W \times H \times \frac{\text{bpp}}{8} = 752 \times 480 \times \frac{10}{8} = 451,200 \ \text{bytes}
\]

Total memory: \( 4 \times 451,200 = 1,804,800 \) bytes

The DMA engine cycles through buffers with timing:
\[
t_{\text{frame}} = \frac{1}{f_{\text{fps}}} = \frac{1}{100} = 10 \ \text{ms}
\]

Buffer swap latency: \( t_{\text{swap}} \approx 50 \ \mu\text{s} \) via `VIDIOC_DQBUF`/`VIDIOC_QBUF` ioctls

### Visual Odometry Motion Estimation

For two consecutive frames with feature correspondences \( \mathbf{x}_i \leftrightarrow \mathbf{x}'_i \), the essential matrix constraint:

\[
\mathbf{x}'_i^T \mathbf{E} \mathbf{x}_i = 0
\]

Where \( \mathbf{E} = [\mathbf{t}]_\times \mathbf{R} \), with rotation \( \mathbf{R} \) and translation \( \mathbf{t} \).

For planar motion (rover on ground), the homography model is more appropriate:

\[
\mathbf{x}'_i = \mathbf{H} \mathbf{x}_i, \quad \mathbf{H} = \mathbf{R} - \frac{\mathbf{t} \mathbf{n}^T}{d}
\]

Where \( \mathbf{n} = [0, 0, 1]^T \) is ground plane normal, \( d = h/\cos\theta \) is camera height.

The 3-DOF motion (yaw \( \psi \), forward \( t_x \), lateral \( t_y \)) is extracted via SVD of \( \mathbf{H} \).

### ARM NEON Optimization Mathematics

The optical flow computation uses ARM NEON SIMD for 4-pixel parallel processing. Gradient calculations:

\[
\begin{bmatrix} I_x \\ I_y \end{bmatrix} = \frac{1}{12} \begin{bmatrix} -1 & 0 & 1 \\ -1 & 0 & 1 \end{bmatrix} * I \quad \text{(5-tap optimized)}
\]

NEON implementation processes 8 pixels simultaneously:
```neon
// Load 8 pixels: [p0 p1 p2 p3 p4 p5 p6 p7]
int16x8_t pixels = vld1q_s16(image_ptr);
// Compute I_x: [-p0 + p4] for each of 4 parallel computations
int16x8_t I_x = vsubq_s16(vld1q_s16(ptr+4), vld1q_s16(ptr));
```

The window sum accumulation uses pairwise addition:
\[
\sum_{W} I_x^2 = \text{vpaddl}(\text{vmul}(I_x, I_x))
\]

### Exposure Control Algorithm

Automatic exposure control maintains optimal image contrast. The cost function:

\[
C(E) = \alpha \cdot \text{Var}(I) - \beta \cdot \text{Sat}(I) - \gamma \cdot |E - E_{\text{target}}|
\]

Where:
- \(\text{Var}(I)\) = image variance (maximize)
- \(\text{Sat}(I)\) = percentage of saturated pixels (minimize)
- \(E_{\text{target}}\) = target exposure for 50% gray value

Gradient descent update:
\[
E_{k+1} = E_k + \eta \cdot \frac{\partial C}{\partial E}
\]

### Optical Flow Quality Metrics

Feature tracking quality is assessed via:

1. **Eigenvalue ratio**: \( \lambda_{\min} / \lambda_{\max} > 0.1 \)
2. **Residual error**: \( \epsilon = \sum_W |I(\mathbf{x} + \mathbf{f}) - I'(\mathbf{x})|^2 \)
3. **Consistency check**: Forward-backward error \( \|\mathbf{f} + \mathbf{f}'\| < 0.5 \) pixels

Features failing any check are rejected.

### Timing and Latency Analysis

Total pipeline latency for 100Hz optical flow:

\[
t_{\text{total}} = t_{\text{exposure}} + t_{\text{readout}} + t_{\text{DMA}} + t_{\text{processing}}
\]

Where:
- \( t_{\text{exposure}} = 2 \) ms (adjustable)
- \( t_{\text{readout}} = \frac{480 \times 784}{27 \times 10^6} = 13.9 \) ms
- \( t_{\text{DMA}} = 0.05 \) ms
- \( t_{\text{processing}} = 3 \) ms (NEON optimized)

Total: \( t_{\text{total}} \approx 19 \) ms, allowing 100Hz operation with 1ms margin.

### Error Propagation and Uncertainty

Optical flow velocity uncertainty propagates from pixel noise:

\[
\sigma_v = \frac{h}{f \cos\theta} \cdot \sigma_{\text{flow}}
\]

With \( \sigma_{\text{flow}} = 0.1 \) pixels (sub-pixel accuracy), \( h = 0.5 \) m, \( f = 250 \) pixels, \( \theta = 30^\circ \):

\[
\sigma_v = \frac{0.5}{250 \cdot \cos(30^\circ)} \cdot 0.1 = 0.023 \ \text{m/s}
\]

This provides 2.3 cm/s velocity resolution, sufficient for rover control.

### Memory Bandwidth Requirements

For 752×480 Y10 format (10-bit packed) at 100Hz:

\[
\text{Bandwidth} = W \times H \times \frac{10}{8} \times f_{\text{fps}} = 752 \times 480 \times 1.25 \times 100 = 45.12 \ \text{MB/s}
\]

The 32-bit AXI bus at 200MHz provides 800 MB/s theoretical bandwidth, leaving ample margin.

### Power Consumption Model

Camera subsystem power:

\[
P_{\text{total}} = P_{\text{sensor}} + P_{\text{IF}} + P_{\text{processing}}
\]

Where:
- \( P_{\text{sensor}} = 150 \) mW (MT9V117 at 100Hz)
- \( P_{\text{IF}} = 50 \) mW (MIPI CSI-2 interface)
- \( P_{\text{processing}} = 300 \) mW (ARM Cortex-A53 at 1.2GHz)

Total: \( P_{\text{total}} = 500 \) mW, acceptable for rover power budget.

### Calibration Mathematics

Camera intrinsic calibration (Brown-Conrady model):

\[
\mathbf{x}_{\text{distorted}} = \mathbf{x} (1 + k_1 r^2 + k_2 r^4 + k_3 r^6) + \begin{bmatrix} 2p_1 xy + p_2(r^2 + 2x^2) \\ p_1(r^2 + 2y^2) + 2p_2 xy \end{bmatrix}
\]

Where \( r^2 = x^2 + y^2 \), with \( k_1, k_2, k_3 \) radial and \( p_1, p_2 \) tangential coefficients.

Extrinsic calibration (camera to body):

\[
\mathbf{T}_b^c = \begin{bmatrix} \mathbf{R}_b^c & \mathbf{t}_b^c \\ \mathbf{0} & 1 \end{bmatrix}
\]

Measured via checkerboard pattern at known rover positions.

### Multi-Sensor Fusion

Optical flow velocity \( \mathbf{v}_{\text{flow}} \) fused with IMU velocity \( \mathbf{v}_{\text{imu}} \) via complementary filter:

\[
\mathbf{v}_{\text{fused}} = \alpha \cdot \mathbf{v}_{\text{flow}} + (1 - \alpha) \cdot \mathbf{v}_{\text{imu}}
\]

Where \( \alpha = 0.7 \) when flow quality is high, decreasing to 0.1 during low-texture conditions.

Covariance intersection for uncertainty-aware fusion:

\[
\mathbf{P}^{-1} = \omega \mathbf{P}_{\text{flow}}^{-1} + (1 - \omega) \mathbf{P}_{\text{imu}}^{-1}
\]
\[
\mathbf{x} = \mathbf{P} [\omega \mathbf{P}_{\text{flow}}^{-1} \mathbf{x}_{\text{flow}} + (1 - \omega) \mathbf{P}_{\text{imu}}^{-1} \mathbf{x}_{\text{imu}}]
\]

## C++ Implementation: Optical Flow Sensors, V4L2 Cameras, and Visual Odometry

This section details the exact C++ implementation for visual perception in the ArduPilot Rover architecture. The code interfaces with MT9V117 global shutter cameras via V4L2, computes optical flow using ARM NEON optimizations, and integrates visual odometry with IMU data for robust terrain-relative navigation.

### V4L2 Camera Interface and Buffer Management (VideoIn.cpp)

**V4L2 Device Data Structures and Memory Mapping:**
The `VideoIn` class implements the Linux Video4Linux2 API using the `V4L2Buffer` struct to manage DMA buffers. Each buffer is memory-mapped via `mmap()` for zero-copy access, with timing managed through `struct timeval` timestamps for deterministic frame capture.

```cpp
// VideoIn.cpp - V4L2 camera interface implementation
class VideoIn {
private:
    // V4L2 buffer management structure
    struct V4L2Buffer {
        void* start;              // Mapped buffer address
        size_t length;            // Buffer size in bytes
        uint32_t offset;          // mmap offset
        int fd;                   // File descriptor for this buffer
        struct timeval timestamp; // Frame capture timestamp
        uint32_t sequence;        // Frame sequence number
    };
    
    // Camera configuration parameters
    struct CameraConfig {
        uint32_t width;           // Image width (752 pixels)
        uint32_t height;          // Image height (480 pixels)
        uint32_t format;          // V4L2_PIX_FMT_Y10 (10-bit grayscale)
        uint32_t fps;             // Frame rate (100 Hz)
        uint32_t buffer_count;    // Number of DMA buffers (4)
        uint32_t exposure_us;     // Exposure time in microseconds
        uint32_t analog_gain;     // Analog gain setting
    } config;
    
    // DMA buffer array
    V4L2Buffer buffers[4];
    uint8_t current_buffer;
    
    // V4L2 device handle
    int v4l2_fd;
    
    // Timing statistics
    struct TimingStats {
        uint64_t frame_interval_us;  // Actual frame interval
        uint64_t max_latency_us;     // Maximum buffer swap latency
        uint32_t frame_count;        // Total frames captured
        uint32_t dropped_frames;     // Dropped frame count
    } stats;
```

**Mathematical Mapping to V4L2 Configuration:**
The `configure_camera()` function sets up the sensor using the V4L2 API, calculating buffer sizes based on the formula `size = width × height × (bpp / 8)`. For 752×480 Y10 format (10-bit packed):

```cpp
// VideoIn.cpp - Camera configuration
bool VideoIn::configure_camera() {
    struct v4l2_format fmt = {0};
    fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    fmt.fmt.pix.width = config.width;
    fmt.fmt.pix.height = config.height;
    fmt.fmt.pix.pixelformat = V4L2_PIX_FMT_Y10;
    fmt.fmt.pix.field = V4L2_FIELD_NONE;
    
    // Calculate bytes per line with 10-bit packing
    // Y10 stores 4 pixels in 5 bytes: (10 bits × 4) / 8 = 5 bytes
    fmt.fmt.pix.bytesperline = (config.width * 10 + 7) / 8;
    fmt.fmt.pix.sizeimage = fmt.fmt.pix.bytesperline * config.height;
    
    if (ioctl(v4l2_fd, VIDIOC_S_FMT, &fmt) < 0) {
        return false;
    }
    
    // Set frame rate: interval = 1/fps in seconds
    struct v4l2_streamparm parm = {0};
    parm.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    parm.parm.capture.timeperframe.numerator = 1;
    parm.parm.capture.timeperframe.denominator = config.fps;  // 100 Hz
    
    if (ioctl(v4l2_fd, VIDIOC_S_PARM, &parm) < 0) {
        return false;
    }
    
    // Request DMA buffers
    struct v4l2_requestbuffers req = {0};
    req.count = config.buffer_count;
    req.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    req.memory = V4L2_MEMORY_MMAP;
    
    if (ioctl(v4l2_fd, VIDIOC_REQBUFS, &req) < 0) {
        return false;
    }
    
    return true;
}
```

**Buffer Management and Timing Mathematics:**
The `capture_frame()` function implements deterministic frame capture with latency tracking. It uses `VIDIOC_DQBUF` to dequeue a filled buffer and `VIDIOC_QBUF` to requeue it, measuring the time delta between frames to validate 100Hz operation.

```cpp
// VideoIn.cpp - Frame capture with timing
bool VideoIn::capture_frame(uint8_t** frame_data, uint64_t* timestamp_us) {
    struct v4l2_buffer buf = {0};
    buf.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
    buf.memory = V4L2_MEMORY_MMAP;
    
    // Dequeue filled buffer (blocking with timeout)
    if (ioctl(v4l2_fd, VIDIOC_DQBUF, &buf) < 0) {
        stats.dropped_frames++;
        return false;
    }
    
    // Calculate frame interval
    static uint64_t last_capture_us = 0;
    uint64_t current_us = buf.timestamp.tv_sec * 1000000ULL + buf.timestamp.tv_usec;
    
    if (last_capture_us > 0) {
        stats.frame_interval_us = current_us - last_capture_us;
        if (stats.frame_interval_us > stats.max_latency_us) {
            stats.max_latency_us = stats.frame_interval_us;
        }
    }
    last_capture_us = current_us;
    
    // Return frame data
    *frame_data = static_cast<uint8_t*>(buffers[buf.index].start);
    *timestamp_us = current_us;
    
    // Requeue buffer for next capture
    if (ioctl(v4l2_fd, VIDIOC_QBUF, &buf) < 0) {
        return false;
    }
    
    stats.frame_count++;
    current_buffer = buf.index;
    
    return true;
}
```

### MT9V117 Sensor Register Programming (CameraSensor_Mt9v117.cpp)

**I²C Register Programming for Exposure Control:**
The `MT9V117_Sensor` class implements the exposure and gain control mathematics through I²C register writes. The `set_exposure()` function calculates the register value based on desired exposure time in microseconds.

```cpp
// CameraSensor_Mt9v117.cpp - MT9V117 sensor control
class MT9V117_Sensor : public CameraSensor {
private:
    // Sensor register definitions
    struct SensorRegisters {
        uint16_t coarse_integration_time;  // 0x03
        uint16_t analog_gain;              // 0x0A
        uint16_t digital_gain;             // 0x0B
        uint16_t frame_length_lines;       // 0x05
        uint16_t line_length_pck;          // 0x06
    } regs;
    
    // Timing constants
    const float pixel_clock_hz = 27.0e6f;  // 27 MHz
    const uint16_t h_total = 784;          // Total horizontal pixels
    const uint16_t v_total = 510;          // Total vertical lines
    
    // I²C device handle
    int i2c_fd;
    uint8_t i2c_addr;
    
public:
    bool set_exposure(uint32_t exposure_us);
    bool set_gain(float total_gain);
    
private:
    bool write_register(uint16_t reg, uint16_t value);
    uint16_t read_register(uint16_t reg);
    float calculate_line_time();
};
```

**Exposure Time Calculation:**
The `set_exposure()` function implements the formula `t_exp = (REG_03 + 1) × t_line`, where `t_line = H_total / f_pclk`. It solves for the register value given desired exposure in microseconds.

```cpp
// CameraSensor_Mt9v117.cpp - Exposure setting
bool MT9V117_Sensor::set_exposure(uint32_t exposure_us) {
    // Calculate line time: t_line = H_total / f_pclk
    float line_time_us = (h_total / pixel_clock_hz) * 1.0e6f;  // ~29.04 μs
    
    // Solve for register value: exposure_us = (reg_value + 1) * line_time_us
    uint16_t reg_value = static_cast<uint16_t>((exposure_us / line_time_us) - 1.0f);
    
    // Clamp to valid range (1 to V_total-1)
    if (reg_value < 1) reg_value = 1;
    if (reg_value > v_total - 1) reg_value = v_total - 1;
    
    // Write to sensor
    if (!write_register(0x03, reg_value)) {
        return false;
    }
    
    regs.coarse_integration_time = reg_value;
    
    // Verify by reading back
    uint16_t readback = read_register(0x03);
    if (readback != reg_value) {
        return false;
    }
    
    return true;
}
```

**Gain Control Mathematics:**
The `set_gain()` function implements the analog and digital gain formulas, converting from total gain in linear units to register values.

```cpp
// CameraSensor_Mt9v117.cpp - Gain setting
bool MT9V117_Sensor::set_gain(float total_gain_linear) {
    // Split into analog and digital components
    // Analog gain range: 1x to 8x (0-18 dB in 0.3 dB steps)
    // Digital gain range: 1x to 4x (0x20 to 0x80)
    
    float analog_gain = 1.0f;
    float digital_gain = 1.0f;
    
    if (total_gain_linear <= 8.0f) {
        // Use analog gain only
        analog_gain = total_gain_linear;
        digital_gain = 1.0f;
    } else {
        // Use max analog gain (8x) and supplement with digital
        analog_gain = 8.0f;
        digital_gain = total_gain_linear / 8.0f;
        
        // Clamp digital gain to max 4x
        if (digital_gain > 4.0f) {
            digital_gain = 4.0f;
        }
    }
    
    // Convert analog gain to register value: gain_dB = 20*log10(gain_linear)
    float gain_dB = 20.0f * log10f(analog_gain);
    uint16_t analog_reg = static_cast<uint16_t>(gain_dB / 0.3f);  // 0.3 dB steps
    
    // Convert digital gain to register value: reg = gain * 32
    uint16_t digital_reg = static_cast<uint16_t>(digital_gain * 32.0f);
    
    // Write registers
    if (!write_register(0x0A, analog_reg)) return false;
    if (!write_register(0x0B, digital_reg)) return false;
    
    regs.analog_gain = analog_reg;
    regs.digital_gain = digital_reg;
    
    return true;
}
```

### Optical Flow Computation (OpticalFlow_Onboard.cpp)

**Lucas-Kanade Data Structures and NEON Optimization:**
The `OpticalFlow_Onboard` class implements the Lucas-Kanade algorithm with ARM NEON SIMD optimization. The `FlowState` struct tracks feature points and their flow vectors, while the `PyramidLevel` struct manages image pyramids for large motion handling.

```cpp
// OpticalFlow_Onboard.cpp - Optical flow implementation
class OpticalFlow_Onboard {
private:
    // Feature point structure
    struct FeaturePoint {
        float x, y;           // Sub-pixel location
        float u, v;           // Flow vector (pixels/frame)
        float quality;        // Tracking quality score
        uint32_t age;         // Frames tracked
        uint8_t level;        // Pyramid level
    };
    
    // Image pyramid level
    struct PyramidLevel {
        uint16_t* image;      // Current image data
        uint16_t* prev_image; // Previous image data
        int16_t* Ix;          // X gradient
        int16_t* Iy;          // Y gradient
        int16_t* It;          // Temporal gradient
        uint32_t width, height;
        uint32_t stride;
        float scale;          // Scale relative to level 0
    };
    
    // Optical flow configuration
    struct FlowConfig {
        uint32_t max_features;      // Maximum features to track (100)
        uint32_t window_size;       // Lucas-Kanade window (15)
        uint32_t pyramid_levels;    // Number of pyramid levels (3)
        float min_eigenvalue;       // Minimum eigenvalue threshold (0.1)
        float max_error;            // Maximum tracking error (4.0 pixels)
        uint32_t feature_interval;  // Feature detection interval (5 frames)
    } config;
    
    // Feature and pyramid storage
    FeaturePoint features[100];
    PyramidLevel pyramid[3];
    uint32_t feature_count;
    
    // NEON-optimized buffers
    int16x8_t* neon_Ix;      // Aligned for NEON access
    int16x8_t* neon_Iy;
    int16x8_t* neon_It;
```

**Gradient Computation with NEON SIMD:**
The `compute_gradients()` function implements the 5-tap gradient filter using ARM NEON intrinsics for 8-pixel parallel processing. It computes both spatial gradients \( I_x, I_y \) and temporal gradient \( I_t \).

```cpp
// OpticalFlow_Onboard.cpp - NEON gradient computation
void OpticalFlow_Onboard::compute_gradients(PyramidLevel& level) {
    uint32_t width = level.width;
    uint32_t height = level.height;
    uint32_t stride = level.stride;
    
    // 5-tap gradient kernels: [-1, 0, 1] for central difference
    // Optimized weights: [-1, 0, 8, 0, -1] / 12 for 5-tap
    
    for (uint32_t y = 2; y < height - 2; y++) {
        uint16_t* row_ptr = level.image + y * stride;
        int16_t* Ix_ptr = level.Ix + y * stride;
        int16_t* Iy_ptr = level.Iy + y * stride;
        
        for (uint32_t x = 2; x < width - 2; x += 8) {
            // Load 8 pixels with 2-pixel border
            uint16x8_t p0 = vld1q_u16(row_ptr + (y-2)*stride + x);
            uint16x8_t p1 = vld1q_u16(row_ptr + (y-1)*stride + x);
            uint16x8_t p2 = vld1q_u16(row_ptr + y*stride + x);      // Center
            uint16x8_t p3 = vld1q_u16(row_ptr + (y+1)*stride + x);
            uint16x8_t p4 = vld1q_u16(row_ptr + (y+2)*stride + x);
            
            // Convert to 16-bit signed for NEON arithmetic
            int16x8_t s0 = vreinterpretq_s16_u16(p0);
            int16x8_t s1 = vreinterpretq_s16_u16(p1);
            int16x8_t s2 = vreinterpretq_s16_u16(p2);
            int16x8_t s3 = vreinterpretq_s16_u16(p3);
            int16x8_t s4 = vreinterpretq_s16_u16(p4);
            
            // Compute Ix: [-p0 + 8*p2 - p4] / 12
            int16x8_t Ix = vsubq_s16(vsubq_s16(vmulq_n_s16(s2, 8), s0), s4);
            Ix = vshrq_n_s16(Ix, 3);  // Divide by 8 (approx /12)
            
            // Compute Iy: [-p0 + 8*p2 - p4] / 12 for vertical
            // Actually: [-p_left + 8*p_center - p_right] / 12
            // Load horizontal neighbors
            uint16x8_t p_left = vld1q_u16(row_ptr + y*stride + (x-2));
            uint16x8_t p_right = vld1q_u16(row_ptr + y*stride + (x+2));
            int16x8_t s_left = vreinterpretq_s16_u16(p_left);
            int16x8_t s_right = vreinterpretq_s16_u16(p_right);
            
            int16x8_t Iy = vsubq_s16(vsubq_s16(vmulq_n_s16(s2, 8), s_left), s_right);
            Iy = vshrq_n_s16(Iy, 3);
            
            // Store gradients
            vst1q_s16(Ix_ptr + x, Ix);
            vst1q_s16(Iy_ptr + x, Iy);
            
            // Compute temporal gradient It = I_current - I_previous
            uint16x8_t prev = vld1q_u16(level.prev_image + y*stride + x);
            int16x8_t s_prev = vreinterpretq_s16_u16(prev);
            int16x8_t It = vsubq_s16(s2, s_prev);
            
            vst1q_s16(level.It + x, It);
        }
    }
}
```

**Lucas-Kanade Flow Calculation:**
The `compute_flow()` function solves the normal equations \( \mathbf{A} \mathbf{f} = \mathbf{b} \) for each feature point using the accumulated gradient sums over the 15×15 window.

```cpp
// OpticalFlow_Onboard.cpp - Lucas-Kanade flow computation
bool OpticalFlow_Onboard::compute_flow(FeaturePoint& feature, PyramidLevel& level) {
    int x0 = static_cast<int>(feature.x);
    int y0 = static_cast<int>(feature.y);
    
    // Accumulate sums over window
    int32_t Axx = 0, Ayy = 0, Axy = 0;
    int32_t bx = 0, by = 0;
    
    int half_window = config.window_size / 2;
    
    for (int dy = -half_window; dy <= half_window; dy++) {
        int16_t* Ix_row = level.Ix + (y0 + dy) * level.stride;
        int16_t* Iy_row = level.Iy + (y0 + dy) * level.stride;
        int16_t* It_row = level.It + (y0 + dy) * level.stride;
        
        for (int dx = -half_window; dx <= half_window; dx++) {
            int16_t Ix = Ix_row[x0 + dx];
            int16_t Iy = Iy_row[x0 + dx];
            int16_t It = It_row[x0 + dx];
            
            Axx += Ix * Ix;
            Ayy += Iy * Iy;
            Axy += Ix * Iy;
            bx += Ix * It;
            by += Iy * It;
        }
    }
    
    // Check eigenvalue ratio for invertibility
    float det = static_cast<float>(Axx * Ayy - Axy * Axy);
    float trace = static_cast<float>(Axx + Ayy);
    
    if (det < config.min_eigenvalue * trace * trace) {
        return false;  // Poorly conditioned
    }
    
    // Solve 2x2 system: [Axx Axy; Axy Ayy] * [u; v] = [bx; by]
    float inv_det = 1.0f / det;
    float u = static_cast<float>(Ayy * bx - Axy * by) * inv_det;
    float v = static_cast<float>(Axx * by - Axy * bx) * inv_det;
    
    // Check for reasonable flow magnitude
    float flow_mag = sqrtf(u*u + v*v);
    if (flow_mag > level.width / 2) {
        return false;  // Unreasonably large flow
    }
    
    feature.u = u;
    feature.v = v;
    
    // Compute residual error for quality assessment
    feature.quality = compute_residual_error(feature, level);
    
    return true;
}
```

**Velocity Transformation from Optical Flow:**
The `flow_to_velocity()` function converts pixel flow to body-frame velocity using the camera geometry and height above ground.

```cpp
// OpticalFlow_Onboard.cpp - Flow to velocity conversion
void OpticalFlow_Onboard::flow_to_velocity(const FeaturePoint& feature, 
                                          float* vx, float* vy) {
    // Camera parameters
    const float f = 250.0f;      // Focal length in pixels
    const float h = 0.5f;        // Height above ground in meters
    const float theta = -30.0f * M_PI / 180.0f;  // Pitch angle
    
    // Convert from pixel coordinates to normalized coordinates
    float x_n = (feature.x - 376.0f) / f;  // 376 = width/2
    float y_n = (feature.y - 240.0f) / f;  // 240 = height/2
    
    // Remove rotational component if gyro data available
    float u_corrected = feature.u;
    float v_corrected = feature.v;
    
    if (gyro_data_available) {
        // Subtract rotational flow: [u; v]_rot = ψ_dot * [-y; x]
        u_corrected -= (-gyro_yaw_rate * y_n);
        v_corrected -= (gyro_yaw_rate * x_n);
    }
    
    // Compute translational velocity
    // For ground plane: u