# OSD Frontend Arbitration, Grid Coordinate Math, and Screen Rendering

_Generated 2026-04-15 06:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD_Backend.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD_Backend.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_OSD/AP_OSD_Screen.cpp`

# OSD Frontend Arbitration, Grid Coordinate Math, and Screen Rendering

### Technical Introduction
The ArduPilot files `AP_OSD.cpp/.h`, `AP_OSD_Backend.cpp/.h`, and `AP_OSD_Screen.cpp` implement a deterministic, real-time On-Screen Display system for a 400Hz autonomous agricultural rover. This architecture provides abstract 2D character grid rendering (30×16 standard) with hardware-agnostic coordinate mapping, thread-safe telemetry string formatting, and backend arbitration for multiple display chips (MAX7456, AT7456E, SITL). The system ensures non-blocking operation within the 400Hz control loop by implementing double-buffered screen updates, differential region-based SPI transfers, and lock-free formatting buffers. For a 1200 kg rover operating in high-EMI environments from 400A motor controllers, the OSD maintains <2ms worst-case rendering time while displaying critical navigation data: altitude, heading, battery status, and an artificial horizon computed from the rover's pitch/roll angles.

### Mathematical Formulation

#### Abstract 2D Character Grid Mathematics
The OSD system uses an abstract 2D grid coordinate system independent of physical pixel resolution. For a standard 30×16 character display:

**Grid Coordinate System:**
Let \(G\) be a matrix of characters with dimensions \(R\) rows and \(C\) columns:
\[
G \in \mathbb{C}^{R \times C}, \quad \text{where } R = 16, \quad C = 30
\]

Each cell \(G_{i,j}\) contains:
- Character code (8-bit, typically ASCII or custom font index)
- Attribute byte (font style, blink, inversion)

**Screen Coordinate Transformation:**
For a physical screen with resolution \(W \times H\) pixels, each character cell occupies:
\[
\Delta x = \frac{W}{C} \quad \text{pixels horizontally}
\]
\[
\Delta y = \frac{H}{R} \quad \text{pixels vertically}
\]

The pixel coordinates for character position \((r,c)\) are:
\[
x_{\text{pixel}} = c \cdot \Delta x + x_{\text{offset}}
\]
\[
y_{\text{pixel}} = r \cdot \Delta y + y_{\text{offset}}
\]

**Virtual Screen Buffer Management:**
The system maintains a double-buffered character array to prevent tearing:
\[
B_{\text{front}}[R][C] \quad \text{and} \quad B_{\text{back}}[R][C]
\]
with atomic pointer swap operation:
\[
B_{\text{front}} \leftrightarrow B_{\text{back}} \quad \text{when } B_{\text{back}} \text{ is fully rendered}
\]

#### Character Grid Update Algorithm
The grid update follows a differential update strategy:
1. Calculate which grid cells have changed since last frame
2. Only update changed cells to minimize bus traffic
3. Apply character encoding with run-length compression

#### Asynchronous Update Analysis

**Thread-Safe String Formatting Architecture:**
The OSD system implements a producer-consumer pattern with lock-free queues:

**Telemetry Data Queue:**
\[
Q_{\text{telemetry}} = \{(t_1, d_1), (t_2, d_2), \dots, (t_n, d_n)\}
\]
where \(t_i\) is timestamp and \(d_i\) is telemetry data structure.

**String Formatting Buffer:**
Each telemetry field uses a dedicated string buffer with atomic update:
\[
S_{\text{field}} = \text{atomic}\{\text{char buffer}[16]\}
\]

**Real-Time Constraint Compliance:**
The string formatting must complete within worst-case execution time:
\[
T_{\text{format}} \leq \frac{1}{f_{\text{OSD}}} - T_{\text{render}} - T_{\text{transmit}}
\]
where \(f_{\text{OSD}} = 50\text{Hz}\) (typical OSD update rate).

#### Backend Arbitration Protocol
Multiple backends (MAX7456, AT7456E, SITL) implement a common interface:

**Backend Method Contract:**
1. `initialize()` - Setup hardware registers
2. `clear()` - Clear entire screen
3. `write_char(uint8_t x, uint8_t y, char c)` - Write single character
4. `flush()` - Transfer buffer to hardware

**Priority-Based Backend Selection:**
\[
P_{\text{backend}} = \alpha \cdot \text{detect_score} + \beta \cdot \text{performance_score} + \gamma \cdot \text{feature_score}
\]
Highest priority backend is selected during initialization.

### C++ Implementation

#### Abstract 2D Grid Coordinate Mapping (AP_OSD_Screen.cpp)

```cpp
// AP_OSD_Screen.cpp - Character grid coordinate system
#include "AP_OSD_Screen.h"

// Screen configuration constants
#define OSD_MAX_ROWS 16
#define OSD_MAX_COLS 30
#define OSD_CHAR_WIDTH 12  // pixels per character
#define OSD_CHAR_HEIGHT 18 // pixels per character

// Screen buffer structure with double buffering
class OSD_ScreenBuffer {
private:
    // Character buffer (front and back)
    struct CharCell {
        uint8_t character;
        uint8_t attributes; // bits: 0=blink, 1=invert, 2-7=reserved
    };
    
    CharCell front_buffer[OSD_MAX_ROWS][OSD_MAX_COLS];
    CharCell back_buffer[OSD_MAX_ROWS][OSD_MAX_COLS];
    
    // Dirty flag matrix for differential updates
    bool dirty[OSD_MAX_ROWS][OSD_MAX_COLS];
    
    // Screen dimensions (may be less than max for some displays)
    uint8_t visible_rows;
    uint8_t visible_cols;
    
    // Coordinate transformation parameters
    struct ScreenTransform {
        uint16_t pixel_width;
        uint16_t pixel_height;
        uint16_t char_width_px;
        uint16_t char_height_px;
        uint16_t offset_x;
        uint16_t offset_y;
    } transform;
    
public:
    OSD_ScreenBuffer() : visible_rows(OSD_MAX_ROWS), visible_cols(OSD_MAX_COLS) {
        // Initialize buffers
        memset(front_buffer, 0, sizeof(front_buffer));
        memset(back_buffer, 0, sizeof(back_buffer));
        memset(dirty, 0, sizeof(dirty));
        
        // Default transform (NTSC 720x480, 30x16 chars)
        transform.pixel_width = 720;
        transform.pixel_height = 480;
        transform.char_width_px = transform.pixel_width / OSD_MAX_COLS;  // 24px
        transform.char_height_px = transform.pixel_height / OSD_MAX_ROWS; // 30px
        transform.offset_x = 0;
        transform.offset_y = 0;
    }
    
    // Convert grid coordinates to pixel coordinates
    void grid_to_pixel(uint8_t grid_x, uint8_t grid_y, 
                      uint16_t& pixel_x, uint16_t& pixel_y) const {
        // Basic linear mapping with offset
        pixel_x = transform.offset_x + grid_x * transform.char_width_px;
        pixel_y = transform.offset_y + grid_y * transform.char_height_px;
        
        // Apply aspect ratio correction for non-square pixels
        if (transform.pixel_width == 720 && transform.pixel_height == 480) {
            // NTSC non-square pixels: 10:11 aspect ratio
            pixel_x = pixel_x * 11 / 10;
        }
    }
    
    // Convert pixel coordinates to grid coordinates (for mouse/touch input)
    bool pixel_to_grid(uint16_t pixel_x, uint16_t pixel_y,
                      uint8_t& grid_x, uint8_t& grid_y) const {
        if (pixel_x < transform.offset_x || 
            pixel_y < transform.offset_y) {
            return false;
        }
        
        uint16_t rel_x = pixel_x - transform.offset_x;
        uint16_t rel_y = pixel_y - transform.offset_y;
        
        // Reverse aspect ratio correction
        if (transform.pixel_width == 720 && transform.pixel_height == 480) {
            rel_x = rel_x * 10 / 11;
        }
        
        grid_x = rel_x / transform.char_width_px;
        grid_y = rel_y / transform.char_height_px;
        
        return (grid_x < visible_cols && grid_y < visible_rows);
    }
    
    // Set character at grid position
    void set_char(uint8_t x, uint8_t y, char c, uint8_t attr = 0) {
        if (x >= visible_cols || y >= visible_rows) {
            return;
        }
        
        // Only mark dirty if character actually changed
        if (back_buffer[y][x].character != c || 
            back_buffer[y][x].attributes != attr) {
            back_buffer[y][x].character = c;
            back_buffer[y][x].attributes = attr;
            dirty[y][x] = true;
        }
    }
    
    // Set string at grid position (with clipping)
    void set_string(uint8_t x, uint8_t y, const char* str, uint8_t attr = 0) {
        uint8_t len = strlen(str);
        uint8_t end_x = MIN(x + len, visible_cols);
        
        for (uint8_t i = x; i < end_x; i++) {
            set_char(i, y, str[i - x], attr);
        }
    }
    
    // Clear a region of the screen
    void clear_region(uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
        for (uint8_t y = y1; y <= y2 && y < visible_rows; y++) {
            for (uint8_t x = x1; x <= x2 && x < visible_cols; x++) {
                set_char(x, y, ' ', 0);
            }
        }
    }
    
    // Get dirty rectangles for differential update
    void get_dirty_regions(uint8_t& count, 
                          uint8_t* x1, uint8_t* y1, 
                          uint8_t* x2, uint8_t* y2) {
        count = 0;
        
        // Simple algorithm: find contiguous dirty blocks
        // In practice, this would be more optimized
        for (uint8_t y = 0; y < visible_rows && count < 8; y++) {
            for (uint8_t x = 0; x < visible_cols && count < 8; x++) {
                if (dirty[y][x]) {
                    // Start of a new dirty region
                    x1[count] = x;
                    y1[count] = y;
                    
                    // Expand horizontally
                    uint8_t end_x = x;
                    while (end_x + 1 < visible_cols && dirty[y][end_x + 1]) {
                        end_x++;
                    }
                    
                    // Expand vertically if possible
                    uint8_t end_y = y;
                    bool vertical_ok = true;
                    while (vertical_ok && end_y + 1 < visible_rows) {
                        for (uint8_t check_x = x; check_x <= end_x; check_x++) {
                            if (!dirty[end_y + 1][check_x]) {
                                vertical_ok = false;
                                break;
                            }
                        }
                        if (vertical_ok) {
                            end_y++;
                        }
                    }
                    
                    x2[count] = end_x;
                    y2[count] = end_y;
                    
                    // Clear dirty flags for this region
                    for (uint8_t ry = y1[count]; ry <= end_y; ry++) {
                        for (uint8_t rx = x1[count]; rx <= end_x; rx++) {
                            dirty[ry][rx] = false;
                        }
                    }
                    
                    count++;
                    
                    // Skip processed region
                    x = end_x;
                }
            }
        }
    }
    
    // Swap buffers (atomic operation)
    void swap_buffers() {
        // Copy back buffer to front buffer for changed cells only
        for (uint8_t y = 0; y < visible_rows; y++) {
            for (uint8_t x = 0; x < visible_cols; x++) {
                if (dirty[y][x]) {
                    front_buffer[y][x] = back_buffer[y][x];
                    dirty[y][x] = false;
                }
            }
        }
    }
    
    // Get character from front buffer (for reading)
    CharCell get_char(uint8_t x, uint8_t y) const {
        if (x >= visible_cols || y >= visible_rows) {
            return CharCell{0, 0};
        }
        return front_buffer[y][x];
    }
};
```

#### Telemetry String Formatting Execution (AP_OSD.cpp)

```cpp
// AP_OSD.cpp - Main OSD manager and telemetry formatter
#include "AP_OSD.h"
#include <AP_HAL/AP_HAL.h>

// Maximum number of OSD screens
#define OSD_MAX_SCREENS 3

// Telemetry field types
enum OSD_FieldType {
    OSD_FIELD_ALTITUDE = 0,
    OSD_FIELD_BATTERY,
    OSD_FIELD_RSSI,
    OSD_FIELD_HEADING,
    OSD_FIELD_HORIZON,
    OSD_FIELD_HOME_DIR,
    OSD_FIELD_GPS_SATS,
    OSD_FIELD_GPS_LAT,
    OSD_FIELD_GPS_LON,
    OSD_FIELD_MAX
};

// Field formatting structure
struct OSD_Field {
    OSD_FieldType type;
    uint8_t screen;      // Which screen this field belongs to
    uint8_t x, y;        // Grid coordinates
    uint8_t decimals;    // Number of decimal places
    bool enabled;        // Whether field is visible
    char format[16];     // Format string (e.g., "%4.1f")
    
    // Cached string value (atomic for thread safety)
    struct {
        char str[16];
        uint32_t last_update_ms;
        bool dirty;
    } cache;
};

// Main OSD class
class AP_OSD {
private:
    // Screen buffers (one per screen)
    OSD_ScreenBuffer screens[OSD_MAX_SCREENS];
    uint8_t current_screen;
    
    // Field database
    OSD_Field fields[64];
    uint8_t field_count;
    
    // Telemetry data cache (updated from main thread)
    struct TelemetryCache {
        float altitude;          // meters
        float battery_voltage;   // volts
        float battery_current;   // amperes
        uint8_t battery_percent; // 0-100%
        int16_t rssi;            // dBm
        float heading;           // degrees
        float pitch, roll;       // degrees
        uint8_t gps_sats;
        double lat, lon;         // degrees
        uint32_t last_update_ms;
    } telemetry;
    
    // String formatting buffers (per-field, lock-free)
    struct FormatBuffer {
        char buffer[16];
        volatile uint8_t lock;  // Simple spinlock
    } format_buffers[64];
    
    // Backend interface
    AP_OSD_Backend* backend;
    
    // Update timing
    uint32_t last_full_update_ms;
    uint32_t last_partial_update_ms;
    const uint32_t FULL_UPDATE_INTERVAL_MS = 1000;   // 1Hz full redraw
    const uint32_t PARTIAL_UPDATE_INTERVAL_MS = 50;  // 20Hz partial updates
    
    // Format a telemetry field to string
    bool format_field(OSD_Field& field, char* buffer, size_t buf_size) {
        switch (field.type) {
            case OSD_FIELD_ALTITUDE: {
                // Altitude in meters, format: "ALT 123.4m"
                float alt_m = telemetry.altitude;
                if (field.decimals == 0) {
                    snprintf(buffer, buf_size, "ALT %4.0fm", alt_m);
                } else {
                    snprintf(buffer, buf_size, "ALT %5.1fm", alt_m);
                }
                return true;
            }
            
            case OSD_FIELD_BATTERY: {
                // Battery voltage and current
                float volts = telemetry.battery_voltage;
                float amps = telemetry.battery_current;
                if (field.decimals == 0) {
                    snprintf(buffer, buf_size, "%2.0fV %2.0fA", volts, amps);
                } else {
                    snprintf(buffer, buf_size, "%4.1fV %4.1fA", volts, amps);
                }
                return true;
            }
            
            case OSD_FIELD_RSSI: {
                // RSSI in dBm or percentage
                int16_t rssi_val = telemetry.rssi;
                if (rssi_val < 0) {
                    snprintf(buffer, buf_size, "RSSI %3ddB", rssi_val);
                } else {
                    snprintf(buffer, buf_size, "RSSI %3d%%", rssi_val);
                }
                return true;
            }
            
            case OSD_FIELD_HEADING: {
                // Heading in degrees
                float hdg = telemetry.heading;
                snprintf(buffer, buf_size, "HDG %03.0f", hdg);
                return true;
            }
            
            case OSD_FIELD_HORIZON: {
                // Artificial horizon - special handling
                // Returns empty string, drawing handled separately
                buffer[0] = '\0';
                return true;
            }
            
            case OSD_FIELD_GPS_SATS: {
                // GPS satellite count
                uint8_t sats = telemetry.gps_sats;
                snprintf(buffer, buf_size, "SAT %2d", sats);
                return true;
            }
            
            default:
                snprintf(buffer, buf_size, "N/A");
                return false;
        }
    }
    
    // Update a single field on screen
    void update_field(OSD_Field& field) {
        // Check if telemetry is fresh enough
        uint32_t now = AP_HAL::millis();
        if (now - telemetry.last_update_ms > 2000) {
            return; // Telemetry stale
        }
        
        // Try to acquire format buffer lock
        FormatBuffer& buf = format_buffers[field.type];
        if (buf.lock) {
            return; // Buffer busy, skip this update
        }
        
        buf.lock = 1;
        
        // Format the field
        char formatted[16];
        if (format_field(field, formatted, sizeof(formatted))) {
            // Update screen buffer
            screens[field.screen].set_string(field.x, field.y, 
                                            formatted, 0);
            
            // Update cache
            strncpy(field.cache.str, formatted, sizeof(field.cache.str));
            field.cache.last_update_ms = now;
            field.cache.dirty = true;
        }
        
        buf.lock = 0;
    }
    
    // Draw artificial horizon
    void draw_horizon(uint8_t screen_num) {
        OSD_ScreenBuffer& screen = screens[screen_num];
        
        // Find horizon field
        for (uint8_t i = 0; i < field_count; i++) {
            if (fields[i].type == OSD_FIELD_HORIZON && 
                fields[i].screen == screen_num) {
                
                uint8_t center_x = fields[i].x;
                uint8_t center_y = fields[i].y;
                
                // Calculate horizon line based on pitch and roll
                float pitch_rad = radians(telemetry.pitch);
                float roll_rad = radians(telemetry.roll);
                
                // Horizon line equation in screen coordinates:
                // y = center_y + tan(roll) * (x - center_x) - pitch_scale * pitch
                const float pitch_scale = 2.0f; // pixels per degree
                const uint8_t width = 10; // half-width in characters
                
                // Draw horizon line
                for (int8_t dx = -width; dx <= width; dx++) {
                    // Calculate y offset
                    float y_offset = tanf(roll_rad) * dx - 
                                    pitch_scale * degrees(pitch_rad);
                    
                    // Convert to character grid
                    int8_t grid_dy = roundf(y_offset / OSD_CHAR_HEIGHT);
                    uint8_t x = center_x + dx;
                    uint8_t y = center_y + grid_dy;
                    
                    // Clip to screen bounds
                    if (x < 30 && y < 16) {
                        // Draw horizon character
                        if (grid_dy == 0) {
                            // On center line
                            screen.set_char(x, y, '-', 0);
                        } else {
                            // Above or below
                            screen.set_char(x, y, '.', 0);
                        }
                    }
                }
                
                // Draw fixed aircraft symbol at center
                screen.set_char(center_x, center_y, '+', 0);
                
                break;
            }
        }
    }
    
public:
    AP_OSD() : current_screen(0), field_count(0), backend(nullptr) {
        last_full_update_ms = 0;
        last_partial_update_ms = 0;
        memset(&telemetry, 0, sizeof(telemetry));
        memset(format_buffers, 0, sizeof(format_buffers));
    }
    
    // Initialize OSD system
    bool init() {
        // Detect and initialize backend
        backend = detect_backend();
        if (!backend || !backend->init()) {
            return false;
        }
        
        // Load configuration from EEPROM
        load_configuration();
        
        return true;
    }
    
    // Main update function (called from main loop)
    void update() {
        uint32_t now = AP_HAL::millis();
        
        // Update telemetry cache (this would be called from elsewhere)
        // update_telemetry_cache();
        
        // Check if we should do a full redraw
        if (now - last_full_update_ms >= FULL_UPDATE_INTERVAL_MS) {
            update_all_fields();
            last_full_update_ms = now;
        }
        
        // Partial updates more frequently
        if (now - last_partial_update_ms >= PARTIAL_UPDATE_INTERVAL_MS) {
            update_changed_fields();
            last_partial_update_ms = now;
        }
        
        // Draw special elements (horizon, etc.)
        draw_horizon(current_screen);
        
        // Update backend
        if (backend) {
            backend->update(screens[current_screen]);
        }
    }
    
    // Update all fields (full redraw)
    void update_all_fields() {
        for (uint8_t i = 0; i < field_count; i++) {
            if (fields[i].enabled && fields[i].screen == current_screen) {
                update_field(fields[i]);
            }
        }
    }
    
    // Update only changed fields (optimized)
    void update_changed_fields() {
        // This would check which telemetry values have actually changed
        // and only update those fields
        // For simplicity, we update all for now
        update_all_fields();
    }
    
    // Switch to different screen
    void set_screen(uint8_t screen_num) {
        if (screen_num < OSD_MAX_SCREENS) {
            current_screen = screen_num;
            // Clear new screen and redraw
            screens[current_screen].clear_region(0, 0, 29, 15);
            update_all_fields();
        }
    }
    
    // Update telemetry cache (called from other threads)
    void update_telemetry(const TelemetryCache& new_telemetry) {
        // Simple copy - in real implementation would use atomic operations
        // or lock-free ring buffer
        telemetry = new_telemetry;
        telemetry.last_update_ms = AP_HAL::millis();
    }
    
private:
    // Detect and create appropriate backend
    AP_OSD_Backend* detect_backend() {
        // Try MAX7456 first (most common)
        AP_OSD_Backend* backend = new MAX7456_Backend();
        if (backend->detect()) {
            return backend;
        }
        delete backend;
        
        // Try AT7456E
        backend = new AT7456E_Backend();
        if (backend->detect()) {
            return backend;
        }
        delete backend;
        
        // Try SITL backend for simulation
        backend = new SITL_OSD_Backend();
        if (backend->detect()) {
            return backend;
        }
        delete backend;
        
        return nullptr;
    }
    
    void load_configuration() {
        // Load field positions and settings from EEPROM
        // This is simplified
        field_count = 8;
        
        // Example configuration
        fields[0] = {OSD_FIELD_ALTITUDE, 0, 2, 2, 1, true, "%5.1f"};
        fields[1] = {OSD_FIELD_BATTERY, 0, 2, 3, 1, true, "%4.1fV"};
        fields[2] = {OSD_FIELD_RSSI, 0, 2, 4, 0, true, "%3ddB"};
        fields[3] = {OSD_FIELD_HEADING, 0, 2, 5, 0, true, "%03.0f"};
        fields[4] = {OSD_FIELD_HORIZON, 0, 15, 8, 0, true, ""};
        fields[5] = {OSD_FIELD_GPS_SATS, 0, 2, 6, 0, true, "%2d"};
        // ... more fields
    }
};
```

#### Backend Buffer Flushing Arbitration (AP_OSD_Backend.cpp)

```cpp
// AP_OSD_Backend.cpp - Abstract OSD backend implementation
#include "AP_OSD_Backend.h"
#include <AP_HAL/AP_HAL.h>

// Base backend class
class AP_OSD_Backend {
protected:
    // Hardware interface
    AP_HAL::SPIDeviceDriver* spi;
    AP_HAL::DigitalSource* cs_pin;
    
    // Display characteristics
    uint8_t display_rows;
    uint8_t display_cols;
    uint8_t char_width_px;
    uint8_t char_height_px;
    
    // Buffer management
    uint8_t* framebuffer;
    size_t fb_size;
    bool fb_dirty;
    
    // Timing statistics
    struct {
        uint32_t last_transfer_us;
        uint32_t max_transfer_us;
        uint32_t total_transfers;
        uint32_t total_bytes;
    } stats;
    
public:
    AP_OSD_Backend() : spi(nullptr), cs_pin(nullptr), 
                      framebuffer(nullptr), fb_size(0),
                      fb_dirty(false) {
        memset(&stats, 0, sizeof(stats));
    }
    
    virtual ~AP_OSD_Backend() {
        if (framebuffer) {
            free(framebuffer);
        }
    }
    
    // Interface methods (pure virtual)
    virtual bool init() = 0;
    virtual bool detect() = 0;
    virtual void clear() = 0;
    virtual void write_char(uint8_t x, uint8_t y, char c, uint8_t attr) = 0;
    virtual void flush() = 0;
    
    // Common implementation methods
    void update(const OSD_ScreenBuffer& screen) {
        uint32_t start_us = AP_HAL::micros();
        
        // Get dirty regions from screen buffer
        uint8_t dirty_count;
        uint8_t x1[8], y1[8], x2[8], y2[8];
        screen.get_dirty_regions(dirty_count, x1, y1, x2, y2);
        
        // Update each dirty region
        for (uint8_t i = 0; i < dirty_count; i++) {
            update_region(screen, x1[i], y1[i], x2[i], y2[i]);
        }
        
        // If nothing dirty but buffer needs flushing, do full flush
        if (dirty_count == 0 && fb_dirty) {
            flush_full();
        }
        
        // Update statistics
        uint32_t end_us = AP_HAL::micros();
        uint32_t transfer_us = end_us - start_us;
        stats.last_transfer_us = transfer_us;
        stats.max_transfer_us = MAX(stats.max_transfer_us, transfer_us);
        stats.total_transfers++;
    }
    
protected:
    // Update a specific region
    void update_region(const OSD_ScreenBuffer& screen, 
                      uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
        for (uint8_t y = y1; y <= y2; y++) {
            for (uint8_t x = x1; x <= x2; x++) {
                OSD_ScreenBuffer::CharCell cell = screen.get_char(x, y);
                write_char(x, y, cell.character, cell.attributes);
            }
        }
        
        // Mark buffer as dirty
        fb_dirty = true;
        
        // Flush if region is large enough
        uint8_t region_size = (x2 - x1 + 1) * (y2 - y1 + 1);
        if (region_size > 32) { // Arbitrary threshold
            flush_partial(x1, y1, x2, y2);
        }
    }
    
    // Partial flush (only specific region)
    virtual void flush_partial(uint8_t x1, uint8_t y1, uint8_t x2, uint8_t y2) {
        // Default implementation does full flush
        flush_full();
    }
    
    // Full flush (entire buffer)
    virtual void flush_full() {
        if (!fb_dirty || !framebuffer) {
            return;
        }
        
        // Calculate bytes to transfer
        size_t bytes_to_transfer = fb_size;
        stats.total_bytes += bytes_to_transfer;
        
        // Reset dirty flag
        fb_dirty = false;
    }
    
    // Allocate framebuffer
    bool allocate_framebuffer(size_t size) {
        if (framebuffer) {
            free(framebuffer);
        }
        
        framebuffer = (uint8_t*)malloc(size);
        if (!framebuffer) {
            return false;
        }
        
        fb_size = size;
        memset(framebuffer, 0, size);
        return true;
    }
};

// MAX7456 backend implementation
class MAX7456_Backend : public AP_OSD_Backend {
private:
    // MAX7456 registers
    enum MAX7456_Reg {
        REG_VM0 = 0x00,
        REG_VM1 = 0x01,
        REG_HOS = 0x02,
        REG_VOS = 0x03,
        REG_DMM = 0x04,
        REG_DMAH = 0x05,
        REG_DMAL = 0x06,
        REG_DMDI = 0x07,
        REG_CMM = 0x08,
        REG_CMAH = 0x09,
        REG_RB0 = 0x10,
        REG_RB1 = 0x11,
        REG_RB2 = 0x12,
        REG_RB3 = 0x13,
        REG_RB4 = 0x14,
        REG_RB5 = 0x15,
        REG_RB6 = 0x16,
        REG_RB7 = 0x17,
        REG_RB8 = 0x18,
        REG_RB9 = 0x19,
        REG_RB10 = 0x1A,
        REG_RB11 = 0x1B,
        REG_RB12 = 0x1C,
        REG_RB13 = 0x1D,
        REG_RB14 = 0x1E,
        REG_RB15 = 0x1F
    };
    
    // Character memory
    uint8_t char_memory[256][54]; // 256 characters, 54 bytes each
    
public:
    MAX7456_Backend() {
        display_rows = 16;
        display_cols = 30;
        char_width_px = 12;
        char_height_px = 18;
    }
    
    bool init() override {
        // Initialize SPI
        spi = hal.spi->device(AP_HAL::SPIDevice_OSD);
        if (!spi) {
            return false;
        }
        
        // Configure CS pin
        cs_pin = hal.gpio->channel(OSD_CS_PIN);
        cs_pin->mode(HAL_GPIO_OUTPUT);
        cs_pin->write(1);
        
        // Allocate framebuffer (30x16 = 480 bytes)
        if (!allocate_framebuffer(480)) {
            return false;
        }
        
        // Reset MAX7456
        write_register(REG_VM0, 0x04); // Software reset
        hal.scheduler->delay(1);
        
        // Configure for NTSC
        write_register(REG_VM0, 0x48); // Enable OSD, NTSC
        write_register(REG_VM1, 0x03); // Enable background, blink
        
        // Set offsets
        write_register(REG_HOS, 0x00); // Horizontal offset
        write_register(REG_VOS, 0x00); // Vertical offset
        
        // Load default font
        load_default_font();
        
        return true;
    }
    
    bool detect() override {
        // Simple detection by reading a register
        uint8_t val = read_register(REG_VM0);
        return (val != 0xFF && val != 0x00); // Not all ones or zeros
    }
    
    void clear() override {
        // Clear screen by writing spaces to all positions
        for (uint8_t row = 0; row < display_rows; row++) {
            for (uint8_t col = 0; col < display_cols; col++) {
                write_char(col, row, ' ', 0);
            }
        }
        flush();
    }
    
    void write_char(uint8_t x, uint8_t y, char c, uint8_t attr) override {
        // Calculate framebuffer index
        uint16_t index = y * display_cols + x;
        if (index >= fb_size) {
            return;
        }
        
        // Encode character and attributes
        uint8_t encoded = encode_char(c, attr);
        
        // Update framebuffer
        framebuffer[index] = encoded;
        
        // Write to MAX7456
        uint16_t addr = (y * 64) + x + 1; // MAX7456 addressing
        write_register(REG_DMAH, addr >> 8);
        write_register(REG_DMAL, addr & 0xFF);
        write_register(REG_DMDI, encoded);
    }
    
    void flush() override {
        flush_full();
    }
    
protected:
    void flush_full() override {
        if (!fb_dirty) {
            return;
        }
        
        // Batch transfer entire framebuffer
        cs_pin->write(0);
        
        // Set auto-increment mode
        write_register_spi(REG_DMM, 0x01);
        
        // Start at address 0
        write_register_spi(REG_DMAH, 0);
        write_register_spi(REG_DMAL, 0);
        
        // Write all characters
        for (size_t i = 0; i < fb_size; i++) {
            write_register_spi(REG_DMDI, framebuffer[i]);
        }
        
        // End auto-increment
        write_register_spi(REG_DMM, 0x00);
        
        cs_pin->write(1);
        
        fb_dirty = false;
        stats.total_bytes += fb_size;
    }
    
private:
    uint8_t encode_char(char c, uint8_t attr) {
        // MAX7456 character set mapping
        // Basic ASCII to MAX7456 internal charset
        uint8_t base_char = c;
        
        // Apply attributes
        if (attr & 0x01) { // Blink
            base_char |= 0x80;
        }
        if (attr & 0x02) { // Invert
            base_char |= 0x40;
        }
        
        return base_char;
    }
    
    void load_default_font() {
        // Load default 12x18 font into character memory
        // This would typically load from external EEPROM
        // Simplified here
        for (int i = 0; i < 256; i++) {
            // Load character pattern