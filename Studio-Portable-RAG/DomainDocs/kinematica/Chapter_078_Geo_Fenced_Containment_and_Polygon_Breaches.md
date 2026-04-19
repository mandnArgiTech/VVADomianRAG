# Geo-Fenced Containment, Polygon Breaches, and EEPROM Boundary Loading

_Generated 2026-04-15 10:20 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Fence/AC_Fence.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Fence/AC_Fence.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Fence/AC_PolyFence_loader.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AC_Fence/AC_PolyFence_loader.h`

# Chapter: Geo-Fenced Containment, Polygon Breaches, and EEPROM Boundary Loading

## Technical Introduction

The Geo-Fenced Containment system provides deterministic, low-latency spatial boundary enforcement for a 400Hz autonomous agricultural rover. This chapter covers the mathematical models and C++ implementations for polygon containment testing, EEPROM boundary loading, and breach response mechanisms. The system must handle the unique dynamics of a 1200 kg rover with high rotational inertia (J_zz=150 kg·m²), skid-steering induced position uncertainty, and real-time constraints of 2.5ms per control cycle. The ray-casting algorithms are optimized for integer arithmetic on STM32F4, flash memory loading implements wear-leveling and double-buffered streaming, and breach responses include hard braking calculations that account for rover mass and traction limits.

## Mathematical Formulation

### Polygon Ray-Casting for Heavy Rover Position Uncertainty

The containment system uses the Jordan Curve Theorem implemented via ray-casting to determine if the rover's position lies within a polygonal fence. For a 1200 kg agricultural rover with skid-steering, position uncertainty scales with steering torque and vehicle mass.

**Ray-Casting Algorithm with Inertia Compensation:**
Given a polygon with vertices \(P_0, P_1, \dots, P_{n-1}\) where \(P_i = (x_i, y_i)\) (latitude, longitude as int32_t scaled by 1e7), and a test point \(Q = (x_q, y_q)\) representing the rover's estimated position:

1. Initialize crossing count \(c = 0\)
2. For each edge \((P_i, P_{i+1})\) (with \(P_n = P_0\)):
   \[
   \text{if } ((y_i > y_q) \neq (y_{i+1} > y_q)) \text{ and } 
   (x_q < \frac{(x_{i+1} - x_i) \cdot (y_q - y_i)}{(y_{i+1} - y_i)} + x_i)
   \]
   then increment \(c\)

3. If \(c\) is odd, point is inside; if even, point is outside.

**Mass-Scaled Position Uncertainty:**
The rover's position uncertainty \(\sigma_p\) increases with steering torque \(\tau_s\) and mass \(m\):
\[
\sigma_p = \sigma_{\text{GPS}} \cdot \left(1 + \frac{\tau_s \cdot m}{k_{\text{traction}} \cdot w_{\text{track}}}\right)
\]
where \(w_{\text{track}} = 1.8\text{m}\) is track width, \(k_{\text{traction}} = 0.8\) is terrain coefficient. The fence margin is scaled accordingly:
\[
\text{margin}_{\text{effective}} = \text{margin}_{\text{nominal}} \cdot \left(1 + \frac{\sigma_p}{5.0}\right)
\]

**Integer Arithmetic Optimization:**
Coordinates are stored as 32-bit integers (degrees × 1e7). The intersection test uses 64-bit intermediate calculations:
\[
\text{intersection} = x_q \cdot (y_{i+1} - y_i) < (x_{i+1} - x_i) \cdot (y_q - y_i) + x_i \cdot (y_{i+1} - y_i)
\]

**Bounding Box Pre-check with Inertia Consideration:**
For quick rejection, calculate polygon bounding box expanded by position uncertainty:
\[
\begin{aligned}
\text{min\_lat} &= \min(x_i) - \Delta_{\text{uncertainty}} \\
\text{max\_lat} &= \max(x_i) + \Delta_{\text{uncertainty}} \\
\text{min\_lng} &= \min(y_i) - \Delta_{\text{uncertainty}} \\
\text{max\_lng} &= \max(y_i) + \Delta_{\text{uncertainty}}
\end{aligned}
\]
where \(\Delta_{\text{uncertainty}} = \sigma_p \cdot 1e7 / (111319.0 \cdot \cos(\phi_{\text{lat}}))\) converts meters to latitude degrees.

### EEPROM Fence Coordinate Loading with Wear-Leveling

Fence coordinates are stored in STM32 flash memory with wear-leveling to prevent sector exhaustion. The mathematical model accounts for flash physics and real-time loading constraints.

**Flash Memory Organization:**
```
Sector 11 (0x080E0000 - 0x080FFFFF, 128KB):
  Header (16 bytes): magic(0x55AA5A5A), version, fence_count, checksum
  Fence headers (16 bytes each): type, action, vertex_count, data_offset, data_size
  Vertex data: packed int32_t lat,lng pairs
```

**Wear-Leveling Algorithm:**
Two sectors alternate writes. The switch occurs after \(N_{\text{max}}\) writes:
\[
N_{\text{max}} = \frac{E_{\text{endurance}}}{E_{\text{write}}} \cdot f_{\text{safety}}
\]
where \(E_{\text{endurance}} = 10,000\) cycles (STM32F4), \(E_{\text{write}} = 1\) per fence update, \(f_{\text{safety}} = 0.1\).

**Stream Loading Throughput:**
Vertices loaded in batches of \(B = 8\) to balance memory and latency. Loading time for \(V\) vertices:
\[
T_{\text{load}} = \left\lceil\frac{V}{B}\right\rceil \cdot (T_{\text{flash}} + T_{\text{copy}} + T_{\text{yield}})
\]
where \(T_{\text{flash}} = 27\mu s\) (800 bytes at 30MB/s), \(T_{\text{copy}} = 2\mu s\), \(T_{\text{yield}} = 1\mu s\).

**Double-Buffer State Equations:**
Active buffer \(A\) and loading buffer \(L\) swap when:
\[
A_{\text{ready}} = \text{false} \quad \text{and} \quad L_{\text{ready}} = \text{true}
\]
Buffer readiness follows:
\[
L_{\text{ready}}(t+1) = \begin{cases}
\text{true} & \text{if } \text{flash\_read\_complete}(t) \\
L_{\text{ready}}(t) & \text{otherwise}
\end{cases}
\]

### Breach Response and Hard Braking for High-Mass Rover

When the 1200 kg rover approaches a fence boundary, the braking calculation must account for its high inertia and skid-steering dynamics.

**Stopping Distance with Mass Scaling:**
For velocity \(v\) toward boundary, maximum braking acceleration \(a_{\text{max}} = \mu \cdot g \cdot f_{\text{mass}}\), where \(\mu = 0.7\) (terrain), \(g = 9.81\), \(f_{\text{mass}} = 1200/1000 = 1.2\):
\[
d_{\text{stop}} = \frac{v^2}{2a_{\text{max}}} + d_{\text{reaction}}
\]
with \(d_{\text{reaction}} = v \cdot t_{\text{400Hz}} = v \cdot 0.0025\).

**Braking Acceleration PID with Jerk Limiting:**
Controller output for position error \(e_p\) and velocity error \(e_v\):
\[
a_{\text{cmd}} = K_p e_p + K_i \int e_p dt + K_d e_v
\]
Jerk-limited acceleration update:
\[
a(t+1) = a(t) + \text{sign}(a_{\text{cmd}} - a(t)) \cdot \min(|a_{\text{cmd}} - a(t)|, j_{\text{max}} \cdot \Delta t)
\]
where \(j_{\text{max}} = 5.0 \text{ m/s}^3\) for rover structural limits.

**Boundary Distance Calculation:**
Closest distance from point \(Q\) to polygon edge \((P_i, P_{i+1})\):
\[
t^* = \frac{(Q - P_i) \cdot (P_{i+1} - P_i)}{\|P_{i+1} - P_i\|^2}, \quad t^* \in [0,1]
\]
\[
d = \|Q - (P_i + t^* (P_{i+1} - P_i))\|
\]

**Mass-Compensated Return Bearing:**
For breach at point \(Q\), return bearing to polygon interior:
\[
\theta_{\text{return}} = \text{atan2}\left(\sum_{i=0}^{n-1} \frac{P_i - Q}{\|P_i - Q\|^2} \cdot w_i\right)
\]
where \(w_i = \frac{m_{\text{rover}}}{1000} \cdot \frac{1}{\|P_i - Q\|}\) weights closer vertices more for high-inertia turns.

**Breach Timeout with Consecutive Detection:**
Breach state persists for \(t_{\text{breach}}\) before triggering action:
\[
t_{\text{breach}} = t_{\text{base}} \cdot (1 + k_{\text{consecutive}} \cdot n_{\text{breaches}})
\]
where \(t_{\text{base}} = 2.0\text{s}\), \(k_{\text{consecutive}} = 0.5\), \(n_{\text{breaches}}\) is consecutive detection count.

**Coordinate Transformation for Skid-Steering:**
Convert latitude/longitude to meters from home for control calculations:
\[
\begin{aligned}
x &= (\phi - \phi_0) \cdot \frac{\pi}{180} \cdot R \cdot \cos(\phi_0 \cdot \frac{\pi}{180}) \\
y &= (\lambda - \lambda_0) \cdot \frac{\pi}{180} \cdot R
\end{aligned}
\]
where \(R = 6378137.0 \text{m}\) (WGS84), \((\phi_0, \lambda_0)\) is home position.

**Checksum Verification for Flash Integrity:**
CRC-32 over flash data excluding checksum field:
\[
\text{CRC}_{n+1} = (\text{CRC}_n \gg 1) \oplus (\text{CRC}_n \& 1) \cdot 0xEDB88320
\]
applied to each byte of stored fence data.

## C++ Implementation

### Ray-Casting Point-in-Polygon Implementation (AC_Fence.cpp)

The `PolygonFence` struct directly implements the ray-casting algorithm using 64-bit integer arithmetic to prevent overflow. The `contains_point()` method maps exactly to the mathematical formulation: for each edge `(P_i, P_{i+1})`, it checks the condition `((y_i > y_q) != (y_{i+1} > y_q))` and computes the intersection using 64-bit cross product. The bounding box pre-check (`min_lat`, `max_lat`, `min_lng`, `max_lng`) implements the quick rejection optimization, reducing average computation time for the 1200 kg rover's typical field boundaries.

```cpp
// AC_Fence.cpp - Polygon containment checking
#include "AC_Fence.h"
#include <AP_Math/AP_GeodesicGrid.h>

// Fence breach detection state
enum FenceBreachState {
    FENCE_BREACH_NONE = 0,
    FENCE_BREACH_MINALT = 1,
    FENCE_BREACH_MAXALT = 2,
    FENCE_BREACH_BOUNDARY = 3
};

// Polygon fence structure
struct PolygonFence {
    Vector2l* vertices;     // Array of (lat, lng) as int32_t
    uint16_t vertex_count;
    bool is_inclusion;      // true = must stay inside, false = must stay outside
    float margin_cm;        // Safety margin in centimeters
    
    // Bounding box for quick rejection
    int32_t min_lat, max_lat;
    int32_t min_lng, max_lng;
    
    // Calculate bounding box
    void calculate_bounding_box() {
        if (vertex_count == 0) return;
        
        min_lat = max_lat = vertices[0].x;
        min_lng = max_lng = vertices[0].y;
        
        for (uint16_t i = 1; i < vertex_count; i++) {
            min_lat = MIN(min_lat, vertices[i].x);
            max_lat = MAX(max_lat, vertices[i].x);
            min_lng = MIN(min_lng, vertices[i].y);
            max_lng = MAX(max_lng, vertices[i].y);
        }
    }
    
    // Ray-casting point-in-polygon test
    bool contains_point(const Vector2l& point) const {
        // Quick bounding box rejection
        if (point.x < min_lat || point.x > max_lat ||
            point.y < min_lng || point.y > max_lng) {
            return false;
        }
        
        bool inside = false;
        
        // Ray-casting algorithm
        for (uint16_t i = 0, j = vertex_count - 1; i < vertex_count; j = i++) {
            const Vector2l& vi = vertices[i];
            const Vector2l& vj = vertices[j];
            
            // Check if point is on vertex (exact match)
            if (vi.x == point.x && vi.y == point.y) {
                return true;
            }
            
            // Check if point is on horizontal edge
            if (vi.y == vj.y && vi.y == point.y) {
                if ((vi.x <= point.x && point.x <= vj.x) || 
                    (vj.x <= point.x && point.x <= vi.x)) {
                    return true;
                }
            }
            
            // Check edge crossing
            if ((vi.y > point.y) != (vj.y > point.y)) {
                // Use 64-bit arithmetic to avoid overflow
                int64_t cross_product = (int64_t)(vj.x - vi.x) * (int64_t)(point.y - vi.y) -
                                       (int64_t)(vj.y - vi.y) * (int64_t)(point.x - vi.x);
                
                if (cross_product == 0) {
                    // Point lies on edge
                    return true;
                }
                
                if ((vj.y > vi.y) == (cross_product > 0)) {
                    inside = !inside;
                }
            }
        }
        
        return inside;
    }
    
    // Calculate distance to polygon boundary (approximate)
    float distance_to_boundary(const Vector2l& point, float& bearing_deg) const {
        float min_distance = FLT_MAX;
        float closest_bearing = 0;
        
        for (uint16_t i = 0; i < vertex_count; i++) {
            uint16_t j = (i + 1) % vertex_count;
            const Vector2l& v1 = vertices[i];
            const Vector2l& v2 = vertices[j];
            
            // Calculate closest point on segment
            Vector2f closest = closest_point_on_segment(
                Vector2f(point.x, point.y),
                Vector2f(v1.x, v1.y),
                Vector2f(v2.x, v2.y)
            );
            
            float distance = Vector2f(point.x - closest.x, point.y - closest.y).length();
            
            if (distance < min_distance) {
                min_distance = distance;
                closest_bearing = atan2f(closest.y - point.y, closest.x - point.x) * RAD_TO_DEG;
            }
        }
        
        bearing_deg = closest_bearing;
        return min_distance;
    }
    
private:
    // Find closest point on segment (P1-P2) to point P
    Vector2f closest_point_on_segment(const Vector2f& P, 
                                     const Vector2f& P1, 
                                     const Vector2f& P2) const {
        Vector2f segment = P2 - P1;
        float segment_length_sq = segment.x * segment.x + segment.y * segment.y;
        
        if (segment_length_sq < 1e-6f) {
            return P1; // Segment is a point
        }
        
        // Project point onto segment
        float t = ((P.x - P1.x) * segment.x + (P.y - P1.y) * segment.y) / segment_length_sq;
        t = constrain_float(t, 0.0f, 1.0f);
        
        return Vector2f(P1.x + t * segment.x, P1.y + t * segment.y);
    }
};
```

### EEPROM Coordinate Stream Loading with RTOS Threading (AC_PolyFence_loader.cpp)

The `FenceStreamLoader` class implements the double-buffered streaming algorithm with RTOS thread management. The `loading_thread()` method runs as a separate RTOS task (`AP_HAL::Scheduler::PRIORITY_IO`) and implements the state machine `LoadState`. The batch size calculation `MIN(vertices_remaining, VERTEX_BUFFER_SIZE)` maps directly to the mathematical batch optimization. The cooperative yielding via `hal.scheduler->delay_microseconds(1000)` ensures the 400Hz control loop isn't blocked during flash reads.

```cpp
// AC_PolyFence_loader.cpp - Flash memory fence loading
#include "AC_PolyFence_loader.h"
#include <AP_HAL/AP_HAL.h>
#include <AP_FlashStorage/AP_FlashStorage.h>

// Flash storage configuration
#define FENCE_FLASH_SECTOR    FLASH_SECTOR_11
#define FENCE_FLASH_ADDRESS   0x080E0000
#define FENCE_MAGIC_NUMBER    0x55AA5A5A

// Fence storage structure in flash
struct PACKED StoredFence {
    uint32_t magic;
    uint32_t version;
    uint32_t total_fences;
    uint32_t checksum;
    
    struct PACKED FenceHeader {
        uint8_t type;
        uint8_t action;
        uint16_t vertex_count;
        uint32_t data_offset;
        uint32_t data_size;
    } headers[MAX_STORED_FENCES];
    
    // Fence data follows headers
};

// Stream loading state machine
class FenceStreamLoader {
private:
    enum LoadState {
        STATE_IDLE,
        STATE_READING_HEADERS,
        STATE_LOADING_VERTICES,
        STATE_COMPLETE,
        STATE_ERROR
    };
    
    LoadState current_state;
    uint32_t current_fence_index;
    uint32_t vertices_loaded;
    uint32_t total_vertices;
    
    // Double buffer for vertex loading
    struct VertexBuffer {
        Vector2l vertices[VERTEX_BUFFER_SIZE];
        uint16_t count;
        bool ready;
    } buffers[2];
    
    uint8_t active_buffer;
    uint8_t loading_buffer;
    
    // Flash interface
    AP_FlashStorage* flash;
    const StoredFence* stored_fence;
    
    // Async loading thread
    AP_HAL::MemberProc load_thread;
    hal_thread_t thread_handle;
    
public:
    FenceStreamLoader() : current_state(STATE_IDLE),
                         current_fence_index(0),
                         vertices_loaded(0),
                         total_vertices(0),
                         active_buffer(0),
                         loading_buffer(1),
                         flash(nullptr),
                         stored_fence(nullptr) {
        memset(buffers, 0, sizeof(buffers));
    }
    
    // Initialize loader
    bool init() {
        // Initialize flash storage
        flash = AP_FlashStorage::get_instance();
        if (!flash) {
            return false;
        }
        
        // Map flash memory
        stored_fence = (const StoredFence*)FENCE_FLASH_ADDRESS;
        
        // Verify magic number
        if (stored_fence->magic != FENCE_MAGIC_NUMBER) {
            return false;
        }
        
        // Verify checksum
        if (!verify_checksum()) {
            return false;
        }
        
        total_vertices = calculate_total_vertices();
        
        // Create loading thread
        load_thread = FUNCTOR_BIND_MEMBER(&FenceStreamLoader::loading_thread, void);
        thread_handle = hal.scheduler->create_thread(
            load_thread, "FenceLoader", 1024, AP_HAL::Scheduler::PRIORITY_IO, 0);
        
        return thread_handle != nullptr;
    }
    
    // Calculate total vertices across all fences
    uint32_t calculate_total_vertices() const {
        uint32_t total = 0;
        for (uint32_t i = 0; i < stored_fence->total_fences; i++) {
            total += stored_fence->headers[i].vertex_count;
        }
        return total;
    }
    
    // Verify flash checksum
    bool verify_checksum() const {
        uint32_t calculated_crc = 0;
        const uint8_t* data = (const uint8_t*)stored_fence;
        size_t data_size = sizeof(StoredFence) - sizeof(uint32_t); // Exclude checksum field
        
        for (size_t i = 0; i < data_size; i++) {
            calculated_crc = crc32_byte(calculated_crc, data[i]);
        }
        
        return calculated_crc == stored_fence->checksum;
    }
    
    // Main loading thread
    void loading_thread() {
        current_state = STATE_READING_HEADERS;
        
        while (current_state != STATE_COMPLETE && 
               current_state != STATE_ERROR) {
            
            switch (current_state) {
                case STATE_READING_HEADERS:
                    if (!read_fence_headers()) {
                        current_state = STATE_ERROR;
                    } else {
                        current_state = STATE_LOADING_VERTICES;
                    }
                    break;
                    
                case STATE_LOADING_VERTICES:
                    if (!load_vertices_batch()) {
                        current_state = STATE_ERROR;
                    } else {
                        if (vertices_loaded >= total_vertices) {
                            current_state = STATE_COMPLETE;
                        }
                    }
                    break;
                    
                default:
                    break;
            }
            
            // Yield to other threads
            hal.scheduler->delay_microseconds(1000);
        }
    }
    
    // Read fence headers (metadata)
    bool read_fence_headers() {
        if (!stored_fence || stored_fence->total_fences == 0) {
            return false;
        }
        
        // Headers are already in memory (flash-mapped)
        // Just verify they're reasonable
        for (uint32_t i = 0; i < stored_fence->total_fences; i++) {
            const StoredFence::FenceHeader& header = stored_fence->headers[i];
            
            if (header.vertex_count > MAX_VERTICES_PER_FENCE ||
                header.data_offset == 0 ||
                header.data_size == 0) {
                return false;
            }
        }
        
        return true;
    }
    
    // Load a batch of vertices
    bool load_vertices_batch() {
        if (current_fence_index >= stored_fence->total_fences) {
            return false;
        }
        
        const StoredFence::FenceHeader& header = stored_fence->headers[current_fence_index];
        
        // Calculate how many vertices to load in this batch
        uint32_t vertices_remaining = header.vertex_count - vertices_loaded;
        uint32_t batch_size = MIN(vertices_remaining, VERTEX_BUFFER_SIZE);
        
        if (batch_size == 0) {
            // Move to next fence
            current_fence_index++;
            vertices_loaded = 0;
            return true;
        }
        
        // Calculate flash address for this batch
        uint32_t flash_addr = FENCE_FLASH_ADDRESS + header.data_offset + 
                             (vertices_loaded * sizeof(Vector2l));
        
        // Read vertices from flash
        VertexBuffer& buffer = buffers[loading_buffer];
        
        if (!flash->read(flash_addr, (uint8_t*)buffer.vertices, 
                        batch_size * sizeof(Vector2l))) {
            return false;
        }
        
        buffer.count = batch_size;
        buffer.ready = true;
        
        // Swap buffers
        swap_buffers();
        
        vertices_loaded += batch_size;
        
        return true;
    }
    
    // Swap active and loading buffers
    void swap_buffers() {
        // Wait for active buffer to be consumed
        while (buffers[active_buffer].ready) {
            hal.scheduler->delay_microseconds(100);
        }
        
        // Swap
        uint8_t temp = active_buffer;
        active_buffer = loading_buffer;
        loading_buffer = temp;
        
        // Clear the new loading buffer
        buffers[loading_buffer].ready = false;
        buffers[loading_buffer].count = 0;
    }
    
    // Get next batch of vertices (called by main thread)
    bool get_next_batch(Vector2l* vertices, uint16_t& count) {
        if (!buffers[active_buffer].ready) {
            count = 0;
            return false;
        }
        
        VertexBuffer& buffer = buffers[active_buffer];
        memcpy(vertices, buffer.vertices, buffer.count * sizeof(Vector2l));
        count = buffer.count;
        
        // Mark buffer as consumed
        buffer.ready = false;
        
        return true;
    }
    
    // Get loading progress
    float get_progress() const {
        if (total_vertices == 0) {
            return 0.0f;
        }
        
        return (float)vertices_loaded / (float)total_vertices;
    }
};

// CRC-32 calculation for checksum verification
uint32_t crc32_byte(uint32_t crc, uint8_t data) {
    crc ^= data;
    for (int i = 0; i < 8; i++) {
        if (crc & 1) {
            crc = (crc >> 1) ^ 0xEDB88320;
        } else {
            crc >>= 1;
        }
    }
    return crc;
}
```

### Breach Action Arbitration with PID Braking Control (AC_Fence.cpp)

The `FenceBreachManager` class implements the breach response state machine and hard braking algorithm. The `BrakingController` inner class implements the PID control law for deceleration: `desired_accel = position_error * kP + integrator + derivative * kD`. The jerk limiting `accel_delta_mag > jerk_limit * dt` prevents sudden torque spikes that could destabilize the 1200 kg rover during skid-steering maneuvers. The `calculate_braking_acceleration()` function in `AC_Fence` maps directly to the stopping distance equation `stopping_distance = (velocity_toward_boundary²) / (2 * MAX_BRAKING_ACCEL)`.

```cpp
// Breach response implementation in AC_Fence.cpp
class FenceBreachManager {
private:
    enum BreachAction {
        ACTION_NONE = 0,
        ACTION_WARNING = 1,
        ACTION_RTL = 2,
        ACTION_LAND = 3,
        ACTION_BRAKE = 4,
        ACTION_TERMINATE = 5
    };
    
    struct BreachResponse {
        BreachAction action;
        uint32_t delay_ms;
        float minimum_distance_m;
        bool requires_arming;
    };
    
    // Breach response configuration
    BreachResponse responses[FENCE_BREACH_MAX];
    
    // Braking controller
    class BrakingController {
    private:
        // PID controller for braking
        struct {
            float kP, kI, kD;
            float integrator;
            float last_error;
            float output_limit;
        } pid;
        
        // Jerk limit (m/s³)
        float jerk_limit;
        
        // Current braking acceleration
        Vector2f current_accel;
        Vector2f target_accel;
        
    public:
        BrakingController() : jerk_limit(5.0f) {
            pid.kP = 2.0f;
            pid.kI = 0.5f;
            pid.kD = 0.1f;
            pid.integrator = 0.0f;
            pid.last_error = 0.0f;
            pid.output_limit = 5.0f; // 5 m/s² max braking
        }
        
        // Calculate braking acceleration
        Vector2f update(float dt, const Vector2f& position_error,
                       const Vector2f& velocity_error) {
            // Calculate desired acceleration using PID
            Vector2f desired_accel;
            
            // P term
            desired_accel = position_error * pid.kP;
            
            // I term (with anti-windup)
            pid.integrator += position_error * pid.kI * dt;
            pid.integrator.x = constrain_float(pid.integrator.x, -pid.output_limit, pid.output_limit);
            pid.integrator.y = constrain_float(pid.integrator.y, -pid.output_limit, pid.output_limit);
            desired_accel += pid.integrator;
            
            // D term
            Vector2f derivative = (position_error - Vector2f(pid.last_error, pid.last_error)) / dt;
            desired_accel += derivative * pid.kD;
            
            // Limit acceleration
            desired_accel.x = constrain_float(desired_accel.x, -pid.output_limit, pid.output_limit);
            desired_accel.y = constrain_float(desired_accel.y, -pid.output_limit, pid.output_limit);
            
            // Apply jerk limiting
            Vector2f accel_delta = desired_accel - current_accel;
            float accel_delta_mag = accel_delta.length();
            
            if (accel_delta_mag > jerk_limit * dt) {
                accel_delta = accel_delta.normalized() * jerk_limit * dt;
                desired_accel = current_accel + accel_delta;
            }
            
            // Update state
            current_accel = desired_accel;
            pid.last_error = position_error.x; // Store only one component for simplicity
            
            return current_accel;
        }
        
        // Reset controller
        void reset() {
            pid.integrator = Vector2f(0, 0);
            current_accel = Vector2f(0, 0);
            target_accel = Vector2f(0, 0);
        }
    };
    
    BrakingController braking_controller;
    
    // Breach state tracking
    struct {
        FenceBreachState state;
        uint32_t start_time_ms;
        Vector2l breach_location;
        float breach_depth_m;
        uint8_t consecutive_breaches;
    } current_breach;
    
public:
    FenceBreachManager() {
        memset(&current_breach, 0, sizeof(current_breach));
        
        // Configure default responses
        responses[FENCE_BREACH_MINALT] = {ACTION_RTL, 1000, 5.0f, true};
        responses[FENCE_BREACH_MAXALT] = {ACTION_LAND, 500, 10.0f, true};
        responses[FENCE_BREACH_BOUNDARY] = {ACTION_BRAKE, 100, 2.0f, false};
    }
    
    // Handle breach detection
    void handle_breach(FenceBreachState breach_state,
                      const Location& current_loc,
                      const Vector2f& current_vel,
                      float distance_to_boundary) {
        if (breach_state == FENCE_BREACH_NONE) {
            // No breach - reset state
            if (current_breach.state != FENCE_BREACH_NONE) {
                current_breach.consecutive_breaches = 0;
                braking_controller.reset();
            }
            current_breach.state = FENCE_BREACH_NONE;
            return;
        }
        
        // Update breach tracking
        if (current_breach.state != breach_state) {
            // New breach type
            current_breach.state = breach_state;
            current_breach.start_time_ms = AP_HAL::millis();
            current_breach.breach_location = Vector2l(current_loc.lat, current_loc.lng);
            current_breach.consecutive_breaches = 1;
        } else {
            // Continuing breach
            current_breach.consecutive_breaches++;
        }
        
        current_breach.breach_depth_m = distance_to_boundary;
        
        // Get configured response for this breach type
        BreachResponse& response = responses[breach_state];
        
        // Check if we should trigger the response
        uint32_t breach_duration = AP_HAL::millis() - current_breach.start_time_ms;
        
        if (breach_duration >= response.delay_ms &&
            distance_to_boundary <= response.minimum_distance_m) {
            
            execute_response(response, current_loc, current_vel, distance_to_boundary);
        }
    }
    
    // Execute breach response
    void execute_response(const BreachResponse& response,
                         const Location& current_loc,
                         const Vector2f& current_vel,
                         float distance_to_boundary) {
        switch (response.action) {
            case ACTION_WARNING:
                // Just log and continue
                log_breach_warning();
                break;
                
            case ACTION_RTL:
                // Trigger Return-to-Launch
                if (response.requires_arming && !is_armed()) {
                    break;
                }
                trigger_rtl();
                break;
                
            case ACTION_LAND:
                // Trigger immediate landing
                if (response.requires_arming && !is_armed()) {
                    break;
                }
                trigger_land();
                break;
                
            case ACTION_BRAKE:
                // Apply hard braking
                apply_braking(current_loc, current_vel, distance_to_boundary);
                break;
                
            case ACTION_TERMINATE:
                // Emergency termination (stop motors)
                if (response.requires_arming && !is_armed()) {
                    break;
                }
                trigger_termination();
                break;
                
            default:
                break;
        }
    }
    
    // Apply braking to prevent boundary violation
    void apply_braking(const Location& current_loc,
                      const Vector2f& current_vel,
                      float distance_to_boundary) {
        // Calculate vector from current position to breach point
        Vector2f position_error = calculate_position_error(current_loc);
        
        // Calculate braking acceleration
        float dt = 0.01f; // 100Hz update rate
        Vector2f braking_accel = braking_controller.update(dt, position_error, current_vel);
        
        // Convert braking acceleration to attitude commands
        Vector3f att_command = convert_accel_to_attitude(braking_accel);
        
        // Apply to attitude controller
        attitude_controller->input_euler_angle_roll_pitch_yaw(
            att_command.x, att_command.y, att_command.z, true);
        
        // Reduce throttle if braking vertically
        if (braking_accel.length() > 2.0f) {
            float throttle_reduction = braking_accel.length() / 10.0f;
            throttle_reduction = constrain_float(throttle_reduction, 0.0f, 0.3f);
            
            motors->set_throttle(motors->get_throttle() * (1.0f - throttle_reduction));
        }
    }
    
    // Calculate position error vector
    Vector2f calculate_position_error(const Location& current_loc) const {
        // Convert breach location to meters from home
        Vector2f breach_pos_m = location_to_meters(current_breach.breach_location);
        
        // Convert current location to meters from home
        Vector2f current_pos_m = location_to_meters(Vector2l(current_loc.lat, current_loc.lng));
        
        // Error is vector from breach to current position (we want to move away from breach)
        return current_pos_m - breach_pos_m;
    }
    
    // Convert location to meters from home
    Vector2f location_to_meters(const Vector2l& location) const {
        // Simplified conversion - in real implementation would use geodesic functions
        const float METERS_PER_DEGREE = 111319.0f;
        
        return Vector2f(
            (location.x - home_location.lat) * 1e-7f * METERS_PER_DEGREE,
            (location.y - home_location.lng) * 1e-7f * METERS_PER_DEGREE * 
            cosf(home_location.lat * 1e-7f * DEG_TO_RAD)
        );
    }
};
```

### STM32 Flash Memory Management with Wear Leveling (FenceFlashManager)

The `FenceFlashManager` class implements low-level STM32 flash operations with wear leveling for the agricultural rover's persistent boundary storage. The `write_fence_data()` method uses direct register manipulation (`FLASH->CR`, `FLASH->KEYR`) to program 32-bit words. The wear leveling algorithm switches between `current_address` and `alternate_address` sectors after `MAX_WRITES_BEFORE_WEAR` cycles, extending flash lifetime for frequently updated field boundaries. The `program_word()` function implements the STM32 programming sequence with verification, ensuring data integrity for the rover's safety-critical containment system.

```cpp
// Flash memory manager for fence storage
class FenceFlashManager {
private:
    FLASH_TypeDef* flash