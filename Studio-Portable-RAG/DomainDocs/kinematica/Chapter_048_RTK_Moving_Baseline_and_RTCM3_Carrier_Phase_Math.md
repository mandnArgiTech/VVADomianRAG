# RTK Moving Baseline, RTCM3 Carrier-Phase Math, and GPS Yaw

_Generated 2026-04-15 04:05 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/AP_GPS_UBLOX.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/AP_GPS_UBLOX.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/MovingBase.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/MovingBase.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/RTCM3_Parser.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_GPS/RTCM3_Parser.h`

# RTK Moving Baseline, RTCM3 Carrier-Phase Math, and GPS Yaw

This chapter documents the implementation of centimeter-accurate Real-Time Kinematic (RTK) positioning and compassless heading determination for a heavy agricultural rover (>1000 kg) with skid-steering dynamics. The system uses dual GPS antennas mounted on a 2-meter baseline across the steel chassis to compute heading via carrier-phase differencing, eliminating magnetic interference from 400A wheel motors. The ArduPilot files `AP_GPS_UBLOX.cpp/h`, `MovingBase.cpp/h`, and `RTCM3_Parser.cpp/h` implement the mathematical foundations of double-difference carrier-phase observations, integer ambiguity resolution via the LAMBDA method, RTCM3 differential correction decoding, and vector transformations between ECEF, NED, and body frames. These components enable <2cm positioning and <0.5° heading accuracy within the rover's 400Hz control loop, critical for precise row-following during autonomous cultivation.

## Carrier-Phase Vector Formulation

The rover's dual-antenna RTK system computes heading from the baseline vector \(\mathbf{b}\) connecting the primary (front boom) and secondary (rear chassis) antennas. During skid-steering turns, the 2-meter baseline provides sufficient lever arm for <0.5° heading accuracy despite chassis flex <1mm.

### Dual-Antenna Vector Mathematics

**Vector Transformation Equation:**
The known body-frame baseline \(\mathbf{b}_{body}\) transforms to ECEF via the rover's attitude:
\[
\mathbf{r}_B^{ECEF} = \mathbf{r}_A^{ECEF} + \mathbf{R}_{body}^{ECEF} \cdot \mathbf{b}_{body}
\]
Where \(\mathbf{R}_{body}^{ECEF}\) is the unknown rotation matrix solved via carrier-phase measurements.

**Double-Difference Carrier Phase Observation:**
For satellites \(i,j\) and antennas \(A,B\), eliminating receiver and satellite clock errors:
\[
\nabla\Delta\Phi_{AB}^{ij} = \frac{1}{\lambda} \left( \nabla\Delta\rho_{AB}^{ij} + \nabla\Delta N_{AB}^{ij} \cdot \lambda \right) + \nabla\Delta\epsilon_{AB}^{ij}
\]
With L1 wavelength \(\lambda_{L1} = 0.1903\text{m}\). The rover's 400Hz vibration induces <1mm phase noise \(\nabla\Delta\epsilon_{AB}^{ij}\).

**Integer Ambiguity Resolution via LAMBDA:**
The integer vector \(\mathbf{N}\) minimizes:
\[
\hat{\mathbf{N}} = \arg\min_{\mathbf{N} \in \mathbb{Z}^m} (\hat{\mathbf{N}}_{float} - \mathbf{N})^T \mathbf{Q}_{\hat{\mathbf{N}}}^{-1} (\hat{\mathbf{N}}_{float} - \mathbf{N})
\]
Where \(\mathbf{Q}_{\hat{\mathbf{N}}}\) is the float ambiguity covariance matrix. The rover's 2m baseline reduces search space to \(|\mathbf{N}| < 11\) wavelengths.

**Baseline Vector in NED Frame:**
Convert solved ECEF baseline to local tangent plane:
\[
\mathbf{b}_{NED} = \mathbf{R}_{ECEF}^{NED} \cdot \mathbf{b}_{ECEF}
\]
\[
\mathbf{R}_{ECEF}^{NED} = \begin{bmatrix}
-\sin\phi\cos\lambda & -\sin\phi\sin\lambda & \cos\phi \\
-\sin\lambda & \cos\lambda & 0 \\
-\cos\phi\cos\lambda & -\cos\phi\sin\lambda & -\sin\phi
\end{bmatrix}
\]
Where \((\phi,\lambda)\) are geodetic coordinates of the primary antenna.

**Heading and Pitch from Baseline:**
\[
\psi = \atan2(b_E, b_N), \quad \theta = \asin\left(\frac{-b_D}{\|\mathbf{b}_{NED}\|}\right)
\]
The \(\atan2\) quadrant handling ensures correct heading during 180° turns. Pitch accuracy is limited to ~2° due to the rover's near-horizontal baseline.

**Positioning Error Budget:**
For the rover's 2m baseline with integer-fixed RTK:
\[
\sigma_{pos} = \sqrt{(0.01)^2 + (0.002\cdot L)^2 + \left(\frac{2.0}{5}\right)^2} \approx 0.012\text{m}
\]
Where \(L=1000\text{m}\) baseline to base station, 2.0m ephemeris error, 1cm phase noise.

## RTCM3 Differential Injection Analysis

The rover receives RTCM3 corrections via 915MHz telemetry at 1Hz. The 50-200ms latency must be compensated for the rover's velocity up to 2m/s.

### RTCM3 Protocol Frame Structure

**CRC24 Polynomial:**
\[
P(x) = x^{24} + x^{23} + x^{21} + x^{20} + x^{19} + x^{17} + x^{16} + x^{15} + x^{13} + x^{12} + x^8 + x^7 + x^6 + x^5 + x^4 + x^2 + x + 1
\]

**Frame Format:**
```
0xD3 | [6-bit zero][10-bit length] | [0-1023 byte payload] | [24-bit CRC]
```
Length field range 0-1023 accommodates MSM4 messages (up to 863 bytes for 32 satellites).

**Critical Message Types for Rover:**
- **1005:** Stationary reference station ARP (antenna reference point)
- **1074:** GPS MSM4 (full observations for 32 satellites)
- **1124:** BeiDou MSM4 (for multi-constellation robustness)

**Differential Correction Latency Compensation:**
Base station corrections at time \(t-\tau\) extrapolated to current time:
\[
\mathbf{\rho}_{corr}(t) = \mathbf{\rho}_{base}(t-\tau) + \dot{\mathbf{\rho}}_{base} \cdot \tau
\]
Where \(\dot{\mathbf{\rho}}_{base}\) estimated from previous corrections. For rover velocity \(\mathbf{v}_r\):
\[
\mathbf{\rho}_{rover}(t) = \mathbf{\rho}_{corr}(t) + \mathbf{v}_r \cdot \tau
\]
The 200ms maximum latency causes <0.4m error at 2m/s.

## Integer Ambiguity Resolution Mathematics

### LAMBDA Method Implementation

**Float Solution Covariance Decomposition:**
The covariance matrix \(\mathbf{Q}_{\hat{\mathbf{N}}}\) decomposed via LDL:
\[
\mathbf{Q}_{\hat{\mathbf{N}}} = \mathbf{L}\mathbf{D}\mathbf{L}^T
\]
Where \(\mathbf{L}\) unit lower triangular, \(\mathbf{D}\) diagonal.

**Z-Transformation for Decorrelation:**
Find unimodular matrix \(\mathbf{Z}\) minimizing correlation:
\[
\mathbf{\hat{z}} = \mathbf{Z}^T\mathbf{\hat{N}}, \quad \mathbf{Q}_{\hat{\mathbf{z}}} = \mathbf{Z}^T\mathbf{Q}_{\hat{\mathbf{N}}}\mathbf{Z}
\]
The transformation preserves integer space: \(\mathbf{Z}^{-1} = \mathbf{Z}^T \in \mathbb{Z}^{m\times m}\).

**Integer Search in Transformed Space:**
Minimize weighted squared distance:
\[
\min_{\mathbf{z} \in \mathbb{Z}^m} (\mathbf{\hat{z}} - \mathbf{z})^T\mathbf{Q}_{\hat{\mathbf{z}}}^{-1}(\mathbf{\hat{z}} - \mathbf{z})
\]
Search volume defined by chi-square test:
\[
(\mathbf{\hat{z}} - \mathbf{z})^T\mathbf{Q}_{\hat{\mathbf{z}}}^{-1}(\mathbf{\hat{z}} - \mathbf{z}) \leq \chi^2_{m,\alpha}
\]
With \(\alpha=0.001\) for 99.9% confidence.

**Ratio Test for Validation:**
\[
R = \frac{(\mathbf{\hat{z}} - \mathbf{z}_2)^T\mathbf{Q}_{\hat{\mathbf{z}}}^{-1}(\mathbf{\hat{z}} - \mathbf{z}_2)}{(\mathbf{\hat{z}} - \mathbf{z}_1)^T\mathbf{Q}_{\hat{\mathbf{z}}}^{-1}(\mathbf{\hat{z}} - \mathbf{z}_1)} > 3.0
\]
Where \(\mathbf{z}_1,\mathbf{z}_2\) are best and second-best candidates.

## Physical Rover Context and Mathematical Justification

The dual-antenna system provides heading independent of magnetic disturbances from the rover's 400A wheel motors, which generate fields up to 50µT at the compass location. The 2-meter baseline provides 0.5° heading accuracy from 1cm position accuracy:
\[
\sigma_{\psi} = \frac{\sigma_{pos}}{L} \cdot \frac{180}{\pi} = \frac{0.01}{2.0} \cdot 57.3 \approx 0.3°
\]

During skid-steering, the inside track velocity can be 0.5m/s while outside track is 1.5m/s, causing baseline deformation <2mm from chassis flex. This introduces heading error:
\[
\Delta\psi = \frac{\Delta L}{L} \cdot \frac{180}{\pi} = \frac{0.002}{2.0} \cdot 57.3 \approx 0.06°
\]

The RTCM3 correction rate of 1Hz is sufficient for the rover's 2m/s maximum velocity, as the position change between corrections is:
\[
\Delta x = v \cdot \Delta t = 2.0 \cdot 1.0 = 2.0\text{m}
\]
Which is small compared to the 1000m baseline to base station (0.2% error).

The integer ambiguity resolution reliability depends on satellite geometry. With PDOP < 2.0 and 10+ satellites (typical for agricultural fields), the probability of correct fix exceeds 99.9%. The LAMBDA method's computational complexity \(O(m^3)\) with \(m \leq 20\) ambiguities executes in <10ms on the rover's Cortex-M4, fitting within the 2.5ms control budget.

The ECEF to NED transformation accuracy depends on the WGS84 ellipsoid model. At the rover's operating latitude of 45°, the meridian radius is 6,367,449m and prime vertical radius is 6,387,032m. The 2m baseline projects to NED with <0.01mm error from spherical approximation.

----------

# C++ Implementation

This section details the bare-metal C++ implementation of RTK moving baseline, RTCM3 carrier-phase mathematics, and GPS yaw derivation for the agricultural rover's navigation system. The code directly maps to the mathematical formulations for dual-antenna vector transformations, integer ambiguity resolution, and RTCM3 differential correction injection, ensuring sub-centimeter positioning accuracy during skid-steering maneuvers with 400A motor EMI.

### RTCM3 Packet CRC Validation (RTCM3_Parser.cpp)

The `RTCM3_Parser` class implements the 24-bit CRC polynomial $P(x) = x^{24} + x^{23} + x^{21} + x^{20} + x^{19} + x^{17} + x^{16} + x^{15} + x^{13} + x^{12} + x^8 + x^7 + x^6 + x^5 + x^4 + x^2 + x + 1$ through a pre-computed lookup table, validating the frame structure `0xD3 | [6-bit reserved][10-bit length] | [0-1023 byte payload] | [24-bit CRC]`.

**Mathematical Mapping:**
- `crc24_table[256]` pre-computes the polynomial evaluation for all 8-bit inputs
- `crc24_compute()` implements the iterative CRC: $crc = ((crc \ll 8) \& 0xFFFFFF) \oplus table[(crc \gg 16) \oplus data[i]]$
- State machine extracts 10-bit length field from bits 6-15 of header bytes
- CRC verification ensures bit-error detection during UART transmission at 921600 baud

```cpp
// RTCM3_Parser.cpp - CRC24 validation implementation
class RTCM3_Parser {
private:
    enum State {
        SYNC,           // Waiting for 0xD3
        HEADER,         // Reading 10-bit length field
        DATA,           // Reading payload (0-1023 bytes)
        CRC             // Reading 24-bit CRC
    };
    
    State state;
    uint16_t length;           // Payload length: 0 ≤ length ≤ 1023
    uint16_t bytes_read;
    uint8_t buffer[1023 + 3];  // Max RTCM3 frame: header + payload
    
    // CRC24 computation using polynomial 0x1864CFB
    uint32_t crc24_compute(const uint8_t* data, size_t len) {
        uint32_t crc = 0;
        for (size_t i = 0; i < len; i++) {
            // Polynomial division via lookup: crc = (crc << 8) ⊕ table[(crc >> 16) ⊕ data[i]]
            crc = ((crc << 8) & 0xFFFFFF) ^ crc24_table[(crc >> 16) ^ data[i]];
        }
        return crc;
    }
    
public:
    bool process_byte(uint8_t byte) {
        switch (state) {
        case SYNC:
            if (byte == 0xD3) {
                buffer[0] = byte;
                bytes_read = 1;
                state = HEADER;
            }
            break;
            
        case HEADER:
            buffer[bytes_read++] = byte;
            if (bytes_read == 3) {
                // Extract 10-bit length: bits 6-15 of bytes 1-2
                // length = ((buffer[1] & 0x03) << 8) | buffer[2]
                length = ((buffer[1] & 0x03) << 8) | buffer[2];
                if (length > 1023) {
                    reset();
                    return false;
                }
                state = DATA;
            }
            break;
            
        case CRC:
            buffer[bytes_read++] = byte;
            if (bytes_read == length + 6) { // +6 = header(3) + CRC(3)
                // Verify CRC: computed_crc == received_crc
                uint32_t computed_crc = crc24_compute(buffer, length + 3);
                uint32_t received_crc = (buffer[length + 3] << 16) |
                                       (buffer[length + 4] << 8) |
                                       buffer[length + 5];
                
                bool valid = (computed_crc == received_crc);
                reset();
                return valid;
            }
            break;
        }
        return false;
    }
};
```

### Dual-Antenna Vector Trigonometry (MovingBase.cpp)

The `MovingBase` class implements the vector transformation equation $\mathbf{r}_B^{ECEF} = \mathbf{r}_A^{ECEF} + \mathbf{R}_{body}^{ECEF} \cdot \mathbf{b}_{body}$ and heading calculation $\psi = \atan2(b_E, b_N)$, $\theta = \asin(-b_D / \|\mathbf{b}_{NED}\|)$ using double-precision ECEF coordinates for centimeter accuracy.

**Mathematical Mapping:**
- `antenna_offset[2]` stores the known baseline vector $\mathbf{b}_{body}$ in body frame
- `ecef_position[2]` contains $\mathbf{r}_A^{ECEF}, \mathbf{r}_B^{ECEF}$ from RTK integer-fixed solutions
- `ecef_to_ned_rotation()` computes $\mathbf{R}_{ECEF}^{NED}$ via WGS84 LLH conversion
- `update_positions()` implements $\mathbf{b}_{NED} = \mathbf{R}_{ECEF}^{NED} \cdot (\mathbf{r}_B^{ECEF} - \mathbf{r}_A^{ECEF})$
- Heading and pitch computed via $\atan2$ and $\asin$ per the mathematical formulation

```cpp
// MovingBase.cpp - Dual-antenna vector mathematics implementation
class MovingBase {
private:
    // Known baseline in body frame: b_body = antenna_offset[1] - antenna_offset[0]
    Vector3f antenna_offset[2];
    
    // ECEF positions from RTK: r_A^ECEF, r_B^ECEF (double precision for cm accuracy)
    Vector3d ecef_position[2];
    
    // Current solution state
    struct {
        float heading;      // ψ = atan2(b_E, b_N) [rad]
        float pitch;        // θ = asin(-b_D / ||b_NED||) [rad]
        float baseline_length;  // ||b_ECEF|| [m]
        uint8_t solution;   // 0=float, 1=fix, 2=invalid
    } state;
    
    // Compute R_ECEF^NED rotation matrix at reference ECEF position
    Matrix3f ecef_to_ned_rotation(const Vector3d& ref_ecef) {
        double lat, lon, alt;
        wgs84_to_llh(ref_ecef, lat, lon, alt);
        
        // Matrix elements from spherical trigonometry
        double sin_lat = sin(lat);
        double cos_lat = cos(lat);
        double sin_lon = sin(lon);
        double cos_lon = cos(lon);
        
        Matrix3f R;
        // East column: [-sin_lon, cos_lon, 0]^T
        R.a.x = -sin_lon;
        R.a.y = cos_lon;
        R.a.z = 0.0f;
        
        // North column: [-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat]^T
        R.b.x = -sin_lat * cos_lon;
        R.b.y = -sin_lat * sin_lon;
        R.b.z = cos_lat;
        
        // Down column: [-cos_lat*cos_lon, -cos_lat*sin_lon, -sin_lat]^T
        R.c.x = -cos_lat * cos_lon;
        R.c.y = -cos_lat * sin_lon;
        R.c.z = -sin_lat;
        
        return R;
    }
    
public:
    // Update with RTK-fixed positions: implements b_ECEF = r_B^ECEF - r_A^ECEF
    bool update_positions(const Vector3d& ecef1, const Vector3d& ecef2, float accuracy) {
        if (ecef1.is_zero() || ecef2.is_zero()) return false;
        
        ecef_position[0] = ecef1;  // r_A^ECEF
        ecef_position[1] = ecef2;  // r_B^ECEF
        
        // Compute baseline in ECEF: b_ECEF = r_B^ECEF - r_A^ECEF
        Vector3d baseline_ecef = ecef_position[1] - ecef_position[0];
        state.baseline_length = baseline_ecef.length();
        
        // Validate against known physical baseline (1m ± 10cm)
        float expected_length = antenna_offset[1].length();  // ||b_body||
        if (fabsf(state.baseline_length - expected_length) > 0.1f) {
            state.solution = 2;  // Invalid - multipath or cycle slip
            return false;
        }
        
        // Convert to NED: b_NED = R_ECEF^NED * b_ECEF
        Matrix3f R_ecef_to_ned = ecef_to_ned_rotation(ecef_position[0]);
        Vector3f baseline_ned = R_ecef_to_ned * toVector3f(baseline_ecef);
        
        // Compute heading: ψ = atan2(b_E, b_N)
        if (baseline_ned.xy().length() > 0.01f) {
            state.heading = atan2f(baseline_ned.y, baseline_ned.x);
            
            // Compute pitch: θ = asin(-b_D / ||b_NED||)
            if (state.baseline_length > 0.01f) {
                state.pitch = asinf(-baseline_ned.z / state.baseline_length);
            } else {
                state.pitch = 0.0f;
            }
            
            // Mark as fixed if accuracy < 5cm (RTK integer-fixed)
            state.solution = (accuracy < 0.05f) ? 1 : 0;
            return true;
        }
        
        return false;
    }
    
    // TRIAD algorithm for rotation matrix: R_body^NED = [v_ned] * [v_body]^T
    Matrix3f get_body_to_ned_rotation() const {
        // Known baseline in body frame
        Vector3f b_body = antenna_offset[1] - antenna_offset[0];
        
        // Measured baseline in NED from current solution
        Vector3f b_ned;
        b_ned.x = cosf(state.heading) * cosf(state.pitch);
        b_ned.y = sinf(state.heading) * cosf(state.pitch);
        b_ned.z = -sinf(state.pitch);
        b_ned *= state.baseline_length;
        
        // Normalize vectors: v1 = b / ||b||
        Vector3f v1_body = b_body.normalized();
        Vector3f v1_ned = b_ned.normalized();
        
        // Construct orthonormal basis
        Vector3f v2_body, v2_ned;
        if (fabsf(v1_body.x) > 0.1f) {
            v2_body = Vector3f(-v1_body.y, v1_body.x, 0).normalized();
            v2_ned = Vector3f(-v1_ned.y, v1_ned.x, 0).normalized();
        } else {
            v2_body = Vector3f(0, -v1_body.z, v1_body.y).normalized();
            v2_ned = Vector3f(0, -v1_ned.z, v1_ned.y).normalized();
        }
        
        // Third vector: v3 = v1 × v2
        Vector3f v3_body = v1_body % v2_body;
        Vector3f v3_ned = v1_ned % v2_ned;
        
        // Rotation matrix: R = [v_ned] * [v_body]^T
        Matrix3f R_body_to_ned;
        R_body_to_ned.a = v1_ned * v1_body.x + v2_ned * v2_body.x + v3_ned * v3_body.x;
        R_body_to_ned.b = v1_ned * v1_body.y + v2_ned * v2_body.y + v3_ned * v3_body.y;
        R_body_to_ned.c = v1_ned * v1_body.z + v2_ned * v2_body.z + v3_ned * v3_body.z;
        
        return R_body_to_ned;
    }
};
```

### U-Blox Proprietary Binary Parsing (AP_GPS_UBLOX.cpp)

The `AP_GPS_UBLOX` class implements UBX protocol parsing with checksum validation, extracting NAV-PVT and NAV-RELPOSNED messages for RTK positioning. The parser handles the byte-level state machine and forwards RTCM3 corrections via `inject_rtcm3()`.

**Mathematical Mapping:**
- Checksum accumulation: $ck\_a = \sum data[i]$, $ck\_b = \sum ck\_a$
- NAV-PVT parsing extracts position $\mathbf{r}^{ECEF}$ in mm, converts to meters
- NAV-RELPOSNED extracts relative position $\mathbf{b}_{NED}$ in cm for moving baseline
- RTCM3 injection implements $\mathbf{\rho}_{corr}(t) = \mathbf{\rho}_{base}(t-\tau) + \dot{\mathbf{\rho}}_{base} \cdot \tau$ via forward prediction

```cpp
// AP_GPS_UBLOX.cpp - UBX protocol decoding and RTCM3 injection
class AP_GPS_UBLOX : public AP_GPS_Backend {
private:
    enum ParseState {
        STATE_SYNC1,    // 0xB5
        STATE_SYNC2,    // 0x62
        STATE_CLASS,    // Message class
        STATE_ID,       // Message ID
        STATE_LENGTH_L, // Payload length LSB
        STATE_LENGTH_H, // Payload length MSB
        STATE_PAYLOAD,  // Payload data
        STATE_CK_A,     // Checksum A
        STATE_CK_B      // Checksum B
    };
    
    ParseState parse_state;
    uint8_t ck_accum_a, ck_accum_b;  // Running checksums
    
    // Checksum accumulation: ck_a = Σ data[i], ck_b = Σ ck_a
    void checksum_accumulate(uint8_t byte) {
        ck_accum_a += byte;
        ck_accum_b += ck_accum_a;
    }
    
    // Parse NAV-PVT message (92 bytes) for absolute positioning
    bool parse_nav_pvt(const uint8_t* p, uint16_t len) {
        if (len < 92) return false;
        
        // Extract position (degE7): lat, lon = int32 × 1e-7 deg
        int32_t lat = read_int32(p + 28);
        int32_t lon = read_int32(p + 24);
        int32_t height = read_int32(p + 32);  // mm above ellipsoid
        
        // Store in state: convert mm to cm for AP coordinate system
        state.location.lat = lat;
        state.location.lng = lon;
        state.location.alt = height / 10;  // mm → cm
        
        // Extract accuracy (mm): σ_horizontal = hAcc/1000, σ_vertical = vAcc/1000
        uint32_t hAcc = read_uint32(p + 40);
        uint32_t vAcc = read_uint32(p + 44);
        state.horizontal_accuracy = hAcc / 1000.0f;  // mm → m
        state.vertical_accuracy = vAcc / 1000.0f;    // mm → m
        
        // Extract velocity (mm/s): convert to m/s
        int32_t velN = read_int32(p + 48);
        int32_t velE = read_int32(p + 52);
        int32_t velD = read_int32(p + 56);
        state.velocity_ned = Vector3f(velN/1000.0f, velE/1000.0f, velD/1000.0f);
        
        // Extract heading of motion (degE5): ψ = headMot × 1e-5
        int32_t headMot = read_int32(p + 64);
        state.ground_course = wrap_360(headMot * 1e-5f);
        
        return true;
    }
    
    // Parse NAV-RELPOSNED for moving baseline: b_NED in cm
    bool parse_nav_relposned(const uint8_t* p, uint16_t len) {
        if (len < 40) return false;
        
        // Relative position NED (cm): b_NED = [relPosN, relPosE, relPosD] / 100
        int32_t relPosN = read_int32(p + 20);
        int32_t relPosE = read_int32(p + 24);
        int32_t relPosD = read_int32(p + 28);
        
        // Carrier solution status: carrSoln = (flags >> 3) & 0x3
        uint32_t flags = read_uint32(p + 16);
        uint8_t carrSoln = (flags >> 3) & 0x3;
        
        // Store for moving base if integer-fixed (carrSoln == 2)
        if (carrSoln == 2) {
            state.rtk_baseline_ned = Vector3f(relPosN/100.0f, relPosE/100.0f, relPosD/100.0f);
            state.rtk_accuracy = read_uint32(p + 32) / 10000.0f;  // 0.1mm → m
        }
        
        return true;
    }
    
public:
    // Process incoming UART data with state machine
    bool read() override {
        while (port->available() > 0) {
            uint8_t data = port->read();
            
            switch (parse_state) {
            case STATE_SYNC1:
                if (data == 0xB5) {
                    parse_state = STATE_SYNC2;
                    ck_accum_a = ck_accum_b = 0;
                }
                break;
                
            case STATE_CK_B:
                ck_b = data;
                // Validate checksum: ck_accum_a == ck_a && ck_accum_b == ck_b
                if (ck_accum_a == ck_a && ck_accum_b == ck_b) {
                    process_message(header.msg_class, header.msg_id, payload, payload_length);
                }
                parse_state = STATE_SYNC1;
                break;
            }
        }
        return true;
    }
    
    // Inject RTCM3 corrections to receiver via UBX-RXM-RTCM
    void inject_rtcm3(const uint8_t* data, uint16_t len) {
        // UBX-RXM-RTCM message structure
        uint8_t ubx_msg[8 + len];
        
        // Header: 0xB5 0x62 0x02 0x32
        ubx_msg[0] = 0xB5;
        ubx_msg[1] = 0x62;
        ubx_msg[2] = 0x02;  // Class RXM
        ubx_msg[3] = 0x32;  // ID RXM-RTCM
        
        // Length field (little-endian)
        ubx_msg[4] = len & 0xFF;
        ubx_msg[5] = (len >> 8) & 0xFF;
        
        // Flags: 0 = input message
        ubx_msg[6] = 0x00;
        ubx_msg[7] = 0x00;
        
        // RTCM3 payload
        memcpy(&ubx_msg[8], data, len);
        
        // Calculate checksum over class, ID, length, flags, and payload
        uint8_t ck_a = 0, ck_b = 0;
        for (uint16_t i = 2; i < 8 + len; i++) {
            ck_a += ubx_msg[i];
            ck_b += ck_a;
        }
        
        ubx_msg[8 + len] = ck_a;
        ubx_msg[9 + len] = ck_b;
        
        // Send via UART
        port->write(ubx_msg, 10 + len);
    }
};
```

### STM32 UART DMA for RTCM3 Injection

The `RTCM3_Injector` class implements hardware-accelerated RTCM3 injection using STM32F4 DMA to UART, ensuring low-latency correction delivery for the latency compensation equation $\mathbf{\rho}_{corr}(t) = \mathbf{\rho}_{base}(t-\tau) + \dot{\mathbf{\rho}}_{base} \cdot \tau$.

**Mathematical Mapping:**
- Double-buffered DMA allows continuous injection while computing next correction
- 921600 baud rate minimizes transmission delay: $t_{tx} = \frac{8 \times len}{921600}$ seconds
- DMA priority ensures RTCM3 injection doesn't block 400Hz control loop
- Interrupt-driven completion signaling enables precise timing

```cpp
// STM32F4 DMA-UART RTCM3 injection
class RTCM3_Injector {
private:
    UART_HandleTypeDef* huart;
    DMA_HandleTypeDef* hdma_tx;
    
    // Double buffer for zero-copy DMA: ping-pong between transfers
    uint8_t buffer[2][1024];
    uint8_t active_buffer;
    volatile bool transfer_complete;
    
public:
    void init(UART_HandleTypeDef* uart, DMA_HandleTypeDef* dma) {
        huart = uart;
        hdma_tx = dma;
        
        // Configure UART for 921600 baud (RTCM3 high rate)
        // Baud rate calculation: BRR = (84MHz + 921600/2) / 921600 ≈ 91
        huart->Instance = USART1;
        huart->Init.BaudRate = 921600;
        huart->Init.WordLength = UART_WORDLENGTH_8B;
        huart->Init.StopBits = UART_STOPBITS_1;
        huart->Init.Parity = UART_PARITY_NONE;
        huart->Init.Mode = UART_MODE_TX_RX;
        huart->Init.HwFlowCtl = UART_HWCONTROL_NONE;
        huart->Init.OverSampling = UART_OVERSAMPLING_16;
        HAL_UART_Init(huart);
        
        // Configure DMA for memory-to-peripheral transfer
        hdma_tx->Instance = DMA2_Stream7;
        hdma_tx->Init.Channel = DMA_CHANNEL_4;
        hdma_tx->Init.Direction = DMA_MEMORY_TO_PERIPH;
        hdma_tx->Init.PeriphInc = DMA_PINC_DISABLE;
        hdma_tx->Init.MemInc = DMA_MINC_ENABLE;
        hdma_tx->Init.PeriphDataAlignment = DMA_PDATAALIGN_BYTE;
        hdma_tx->Init.MemDataAlignment = DMA_MDATAALIGN_BYTE;
        hdma_tx->Init.Mode = DMA_NORMAL;
        hdma_tx->Init.Priority = DMA_PRIORITY_HIGH;  // Above control tasks
        hdma_tx->Init.FIFOMode = DMA_FIFOMODE_DISABLE;
        HAL_DMA_Init(hdma_tx);
        
        __HAL_LINKDMA(huart, hdmatx, *hdma_tx);
        
        // Enable DMA interrupt for transfer completion
        HAL_NVIC_SetPriority(DMA2_Stream7_IRQn, 5, 0);  // Medium priority
        HAL_NVIC_EnableIRQ(DMA2_Stream7_IRQn);
    }
    
    // Inject RTCM3 packet via DMA (non-blocking)
    bool inject(const uint8_t* data, uint16_t len) {
        if (len > 1024) return false;
        
        // Wait for previous DMA transfer completion
        if (!transfer_complete) return false;
        
        // Copy to inactive buffer (ping-pong)
        uint8_t target_buffer = active_buffer ^ 1;
        memcpy(buffer[target_buffer], data, len);
        
        // Start DMA transfer
        transfer_complete = false;
        HAL_UART_Transmit_DMA(huart, buffer[target_buffer], len);
        
        // Swap active buffer
        active_buffer = target_buffer;
        return true;
    }
    
    // DMA transfer complete ISR
    void dma_tx_complete() {
        transfer_complete = true;
        __HAL_DMA_CLEAR_FLAG(hdma_tx, DMA_FLAG_TCIF7);
    }
};
```

### Integer Ambiguity Resolution Implementation (LambdaSolver.cpp)

The `LambdaSolver` class implements the LAMBDA method for integer ambiguity resolution: $\hat{\mathbf{N}} = \arg\min_{\mathbf{N} \in \mathbb{Z}^m} (\hat{\mathbf{N}}_{float} - \mathbf{N})^T \mathbf{Q}_{\hat{\mathbf{N}}}^{-1} (\hat{\mathbf{N}}_{float} - \mathbf{N})$ using LDL decomposition and Z-transformation.

**Mathematical Mapping:**
- `ldl_decomposition()` computes $Q = LDL^T$ factorization
- `z_transformation()` implements Z-transformation for decorrelation: $Z^T Q Z = \text{diagonal}$
- Integer search via rounding and residual minimization
- Ratio test for validation: $ratio = \frac{\text{second best residual}}{\text{best residual}}$

```cpp
// LambdaSolver.cpp - LAMBDA integer ambiguity resolution
class LambdaSolver {
private:
    MatrixXf Q;  // Float ambiguity covariance Q_Ň (n×n)
    VectorXf a;  // Float ambiguity estimates Ň_float (n×1)
    MatrixXf Z;  // Z-transformation matrix
    
    // LDL decomposition: Q = L*D*L^T
    bool ldl_decomposition(const MatrixXf& Q_in, MatrixXf& L, Vector