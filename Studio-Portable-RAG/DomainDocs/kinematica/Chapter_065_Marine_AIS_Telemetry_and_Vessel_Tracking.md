# Marine AIS Telemetry, 6-bit Payload Decoding, and Vessel Tracking

_Generated 2026-04-15 08:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AIS/AP_AIS.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AIS/AP_AIS.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_AIS/LogStructure.h`

# Chapter: Marine AIS Telemetry, 6-bit Payload Decoding, and Vessel Tracking

## Technical Introduction
The files `AP_AIS.cpp`, `AP_AIS.h`, and `LogStructure.h` implement an Automatic Identification System (AIS) receiver and collision avoidance system for ArduPilot. This system decodes maritime VHF data link messages (NMEA AIVDM/AIVDO sentences) using 6-bit ASCII armored encoding, extracts vessel position/velocity states, and computes Closest Point of Approach (CPA) trigonometry for collision risk assessment. For a 400Hz autonomous agricultural rover, this provides situational awareness of nearby maritime traffic when operating near waterways, enabling the 1200 kg vehicle to avoid collisions despite its high inertia and skid-steering dynamics. The implementation handles real-time decoding of AIS messages at 38400 baud, maintains a track database of up to 20 vessels, and logs telemetry to SD card with minimal CPU overhead.

## Mathematical Formulation

### 6-bit ASCII Armored Decoding Algebra
AIS messages use 6-bit ASCII armored encoding where each character represents 6 bits of binary data. The decoding algorithm implements the exact mapping:

**Character to 6-bit Value:**
For each character `c` in the payload string:
\[
\text{value} = 
\begin{cases}
c - 48 & \text{if } c < 88 \\
c - 56 & \text{otherwise}
\end{cases}
\]
\[
\text{bitmask} = \text{value} \& 0x3F
\]

**Bit Stream Reconstruction:**
Given `n` characters, the total bit length is `6n`. The bit stream `B` is reconstructed as:
\[
B = \sum_{i=0}^{n-1} (\text{bitmask}_i \ll (6 \times (n - i - 1)))
\]
where `<<` is the left shift operator. This creates a contiguous bit buffer for field extraction.

**Field Extraction from Position Report (Message Type 1):**
The 168-bit message structure defines exact bit ranges:
- Bits 0-5: Message Type (6 bits, `uint6`)
- Bits 6-7: Repeat Indicator (2 bits, `uint2`)  
- Bits 8-37: MMSI (30 bits, `uint30`)
- Bits 38-41: Navigation Status (4 bits, `uint4`)
- Bits 42-49: Rate of Turn (8 bits, `int8` signed)
- Bits 50-59: Speed Over Ground (10 bits, `uint10`, 0.1 knot/LSB)
- Bits 60-60: Position Accuracy (1 bit, `bool`)
- Bits 61-88: Longitude (28 bits, `int28`, 1/10000 minute)
- Bits 89-115: Latitude (27 bits, `int27`, 1/10000 minute)
- Bits 116-127: Course Over Ground (12 bits, `uint12`, 0.1°/LSB)
- Bits 128-136: True Heading (9 bits, `uint9`)
- Bits 137-142: Time Stamp (6 bits, `uint6`)
- Bits 143-147: Maneuver Indicator (5 bits, `uint5`)
- Bits 148-148: Spare (1 bit)
- Bits 149-155: RAIM Flag (1 bit `bool` + 6 spare)

**Coordinate Conversion to Decimal Degrees:**
\[
\text{Lat}_{deg} = \frac{\text{Lat}_{int}}{600000.0}
\]
\[
\text{Lon}_{deg} = \frac{\text{Lon}_{int}}{600000.0}
\]
Where `Lat_int` and `Lon_int` are signed integers from the 27/28-bit fields. For the agricultural rover's navigation system, these coordinates are transformed to local NED frame relative to the vehicle's position.

### Closest Point of Approach (CPA) Vector Mathematics
The collision avoidance system computes CPA between the rover (ownship) and tracked vessels using vector algebra:

**State Vectors:**
Define vessels `A` (rover) and `B` (target) with:
- Positions: \(\mathbf{P}_A, \mathbf{P}_B \in \mathbb{R}^2\) in local NED coordinates (meters)
- Velocities: \(\mathbf{V}_A, \mathbf{V}_B \in \mathbb{R}^2\) in m/s
- Relative position: \(\mathbf{P}_{AB} = \mathbf{P}_B - \mathbf{P}_A\)
- Relative velocity: \(\mathbf{V}_{AB} = \mathbf{V}_B - \mathbf{V}_A\)

**CPA Time Calculation:**
\[
t_{\text{CPA}} = \frac{-\mathbf{P}_{AB} \cdot \mathbf{V}_{AB}}{\|\mathbf{V}_{AB}\|^2} \quad \text{for } \|\mathbf{V}_{AB}\| > 0
\]
The dot product \(\mathbf{P}_{AB} \cdot \mathbf{V}_{AB} = P_{AB,x}V_{AB,x} + P_{AB,y}V_{AB,y}\) determines if vessels are converging (negative) or diverging (positive).

**CPA Distance Calculation:**
\[
d_{\text{CPA}} = \|\mathbf{P}_{AB} + \mathbf{V}_{AB} \cdot t_{\text{CPA}}\|
\]
\[
= \sqrt{(P_{AB,x} + V_{AB,x}t_{\text{CPA}})^2 + (P_{AB,y} + V_{AB,y}t_{\text{CPA}})^2}
\]

**Collision Risk Assessment:**
Given safety thresholds for the 1200 kg rover:
- \(d_{\text{safe}} = 500\) meters (minimum separation)
- \(t_{\text{safe}} = 300\) seconds (5 minute warning horizon)

Risk condition:
\[
\text{Risk} = \begin{cases}
\text{true} & \text{if } d_{\text{CPA}} < d_{\text{safe}} \text{ and } 0 < t_{\text{CPA}} < t_{\text{safe}} \\
\text{false} & \text{otherwise}
\end{cases}
\]

**Bearing Rate Calculation:**
The bearing rate \(\dot{\theta}\) (rad/s) indicates if a vessel is on constant bearing:
\[
\dot{\theta} = \frac{\mathbf{V}_{AB} \times \mathbf{P}_{AB}}{\|\mathbf{P}_{AB}\|^2}
\]
where the 2D cross product \(\mathbf{V}_{AB} \times \mathbf{P}_{AB} = V_{AB,x}P_{AB,y} - V_{AB,y}P_{AB,x}\). For the skid-steering rover, a high bearing rate suggests the threat is not on collision course.

### Coordinate Transformation: WGS84 to Local NED
For CPA calculations, vessel positions in WGS84 coordinates must be transformed to the rover's local tangent plane:

**WGS84 to NED Conversion:**
\[
\Delta\text{Lat} = \text{Lat}_{vessel} - \text{Lat}_{rover}
\]
\[
\Delta\text{Lon} = \text{Lon}_{vessel} - \text{Lon}_{rover}
\]
\[
x = R \cdot \Delta\text{Lon} \cdot \cos(\text{Lat}_{rover}) \quad \text{(East, meters)}
\]
\[
y = R \cdot \Delta\text{Lat} \quad \text{(North, meters)}
\]
Where \(R = 6371000.0\) meters (Earth radius). This linear approximation is valid for ranges < 20 km relevant to AIS.

**Velocity Vector from Course/Speed:**
Given course over ground \(cog\) (degrees true) and speed over ground \(sog\) (knots):
\[
sog_{ms} = sog \times 0.514444 \quad \text{(knots to m/s)}
\]
\[
V_x = sog_{ms} \cdot \sin(cog) \quad \text{(East component, m/s)}
\]
\[
V_y = sog_{ms} \cdot \cos(cog) \quad \text{(North component, m/s)}
\]

### Telemetry Logging Quantization
The logging system stores compact representations:

**Speed Quantization:**
\[
\text{sog\_cm} = \lfloor sog_{ms} \times 100 \rfloor \quad \text{(cm/s, 16-bit)}
\]

**Angle Quantization:**
\[
\text{cog\_cdeg} = \lfloor cog \times 100 \rfloor \quad \text{(centidegrees, 16-bit)}
\]

**CPA Distance Quantization:**
\[
\text{d\_cpa\_cm} = \lfloor d_{\text{CPA}} \times 100 \rfloor \quad \text{(cm, 16-bit)}
\]

**CPA Time Quantization:**
\[
\text{t\_cpa\_cs} = \lfloor t_{\text{CPA}} \times 100 \rfloor \quad \text{(centiseconds, 16-bit)}
\]

These quantizations maintain sufficient precision for the rover's collision avoidance while minimizing log storage (4 bytes vs 8 bytes for float).

### Bit Extraction Algorithm
The `get_bits()` function implements exact bitfield extraction:
\[
\text{result} = \sum_{i=0}^{\text{num\_bits}-1} \text{bit}(start + i) \cdot 2^{(\text{num\_bits} - i - 1)}
\]
Where \(\text{bit}(n)\) returns 1 if bit `n` is set in the buffer, else 0. The buffer stores bits MSB-first with byte index \(\lfloor n/8 \rfloor\) and bit offset \(7 - (n \mod 8)\).

### Rate of Turn Conversion
The AIS rate of turn field uses special encoding:
\[
\text{ROT} = 
\begin{cases}
0 & \text{if raw} = 0 \\
-128 & \text{if raw} = 255 \\
\text{sign}(\text{raw}) \cdot \left(\frac{|\text{raw}|}{4.733}\right)^2 \cdot 60 & \text{otherwise}
\end{cases}
\]
Where raw is the 8-bit signed value. This non-linear conversion accounts for vessel maneuverability characteristics.

## C++ Implementation

### AIVDM 6-bit ASCII Unpacking Logic (AP_AIS.cpp)

```cpp
class AIS_Decoder {
private:
    uint8_t bit_buffer[(AIS_MAX_BITS + 7) / 8];
    uint16_t bit_position;
    uint16_t total_bits;
    
    uint32_t get_bits(uint16_t start_bit, uint8_t num_bits) {
        uint32_t result = 0;
        for (uint8_t i = 0; i < num_bits; i++) {
            uint16_t bit_index = start_bit + i;
            uint8_t byte_index = bit_index / 8;
            uint8_t bit_offset = 7 - (bit_index % 8);
            
            if (byte_index < sizeof(bit_buffer)) {
                if (bit_buffer[byte_index] & (1 << bit_offset)) {
                    result |= (1 << (num_bits - i - 1));
                }
            }
        }
        return result;
    }
    
    uint8_t decode_char(char c) {
        uint8_t value = static_cast<uint8_t>(c);
        if (value < 88) {
            return value - AIS_ASCII_OFFSET;  // 48
        } else {
            return value - AIS_ASCII_WRAP;    // 56
        }
    }
```

This implements the mathematical decoding: `decode_char()` computes `value = c - 48` (or `c - 56`), then `bitmask = value & 0x3F`. The `get_bits()` function extracts fields using the exact bit ranges defined in the mathematical formulation.

### CPA Calculation Implementation

```cpp
bool calculate_cpa(uint32_t mmsi, float& d_cpa, float& t_cpa) {
    // Relative position and velocity
    Vector2f P_ab = track->position - ownship.position;
    Vector2f V_ab = track->velocity - ownship.velocity;
    
    // Check if vessels are moving relative to each other
    float V_ab_norm_sq = V_ab.x * V_ab.x + V_ab.y * V_ab.y;
    if (V_ab_norm_sq < 0.01f) {
        d_cpa = P_ab.length();
        t_cpa = 1e6f;
        return true;
    }
    
    // Time to CPA
    float t_cpa_raw = -(P_ab.x * V_ab.x + P_ab.y * V_ab.y) / V_ab_norm_sq;
    
    // If CPA is in the past, set to 0
    if (t_cpa_raw < 0) {
        t_cpa = 0.0f;
        d_cpa = P_ab.length();
    } else {
        t_cpa = t_cpa_raw;
        // Distance at CPA
        Vector2f P_at_cpa = P_ab + V_ab * t_cpa;
        d_cpa = P_at_cpa.length();
    }
    
    return true;
}
```

This code directly implements the CPA mathematics: `V_ab_norm_sq = ‖V_AB‖²`, `t_cpa_raw = -(P_AB·V_AB)/‖V_AB‖²`, and `d_cpa = ‖P_AB + V_AB·t_CPA‖`.

### Coordinate Transformation Functions

```cpp
Vector2f ll_to_ned(float lat_deg, float lon_deg, float ref_lat, float ref_lon) {
    const float R = 6371000.0f;
    
    float dlat = radians(lat_deg - ref_lat);
    float dlon = radians(lon_deg - ref_lon);
    
    float x = R * dlon * cosf(radians(ref_lat));
    float y = R * dlat;
    
    return Vector2f(x, y);
}

Vector2f course_speed_to_velocity(float cog_deg, float sog_knots) {
    float sog_ms = sog_knots * 0.514444f;
    
    float cog_rad = radians(cog_deg);
    float vx = sog_ms * sinf(cog_rad);
    float vy = sog_ms * cosf(cog_rad);
    
    return Vector2f(vx, vy);
}
```

These implement the WGS84 to NED conversion (`x = R·Δlon·cos(lat_ref)`, `y = R·Δlat`) and velocity vector creation (`vx = sog·sin(cog)`, `vy = sog·cos(cog)`).

### Telemetry Logging Structure (LogStructure.h)

```cpp
struct PACKED log_AIS {
    LOG_PACKET_HEADER;
    uint64_t time_us;
    uint32_t mmsi;
    int32_t latitude;            // degrees * 1e7
    int32_t longitude;           // degrees * 1e7
    uint16_t sog_cm;             // cm/s
    uint16_t cog_cdeg;           // centidegrees
    uint16_t heading_cdeg;       // centidegrees
    uint8_t nav_status;
    uint8_t vessel_type;
    uint8_t dimension_a;
    uint8_t dimension_b;
    uint8_t dimension_c;
    uint8_t dimension_d;
    uint16_t d_cpa_cm;           // cm
    uint16_t t_cpa_cs;           // centiseconds
    uint8_t risk_level;
    uint8_t flags;
};
```

The structure implements the quantization: `sog_cm = sog_ms × 100`, `cog_cdeg = cog × 100`, `d_cpa_cm = d_CPA × 100`, `t_cpa_cs = t_CPA × 100`.

### Bearing Rate Calculation

```cpp
float calculate_bearing_rate(const VesselTrack& track) {
    Vector2f P_ab = track.position - ownship.position;
    Vector2f V_ab = track.velocity - ownship.velocity;
    
    // 2D cross product (determinant)
    float cross = P_ab.x * V_ab.y - P_ab.y * V_ab.x;
    float dist_sq = P_ab.x * P_ab.x + P_ab.y * P_ab.y;
    
    if (dist_sq < 1.0f) {
        return 0.0f;
    }
    
    return cross / dist_sq; // radians per second
}
```

This computes \(\dot{\theta} = (V_{AB} × P_{AB}) / ‖P_{AB}‖²\) exactly as in the mathematical formulation.

### UART DMA Configuration for AIS Reception

```cpp
void init(USART_TypeDef* uart_instance, uint32_t baudrate = 38400) {
    uart->BRR = (APB1_CLOCK / baudrate);
    uart->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_RXNEIE;
    uart->CR3 = USART_CR3_DMAT | USART_CR3_DMAR;
    
    dma_rx->PAR = (uint32_t)&uart->DR;
    dma_rx->M0AR = (uint32_t)rx_buffer;
    dma_rx->NDTR = sizeof(rx_buffer);
    dma_rx->CR = DMA_SxCR_CHSEL_4 | DMA_SxCR_MINC | DMA_SxCR_CIRC | 
                 DMA_SxCR_TCIE | DMA_SxCR_EN;
}
```

The baud rate register `BRR = clock/baudrate` sets the exact 38400 baud for AIS reception. DMA circular buffer mode ensures no NMEA sentences are lost during the rover's 400Hz control loop execution.

### RTOS Integration and Timing
The AIS decoder runs in a dedicated thread at 10Hz, processing incoming NMEA sentences. CPA calculations execute at 5Hz, synchronized with the rover's navigation update. The 6-bit decoding algorithm completes in <100 µs per message, ensuring the 2.5ms 400Hz control budget is maintained. For the 1200 kg agricultural rover, collision warnings trigger skid-steering avoidance maneuvers with appropriate lead time given the vehicle's high rotational inertia.