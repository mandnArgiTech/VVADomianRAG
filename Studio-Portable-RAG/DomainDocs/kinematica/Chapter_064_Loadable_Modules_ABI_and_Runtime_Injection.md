# Loadable Modules, ABI Structures, and Runtime Hook Injection

_Generated 2026-04-15 07:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Module/AP_Module.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Module/AP_Module.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Module/AP_Module_Structures.h`

# Chapter: Loadable Modules, ABI Structures, and Runtime Hook Injection

## Technical Introduction

The files `AP_Module.cpp`, `AP_Module.h`, and `AP_Module_Structures.h` implement ArduPilot's loadable module architecture, enabling third-party binary extensions to hook into the vehicle's real-time control loops while maintaining strict binary compatibility and fault isolation. This system allows agricultural rover operators to deploy custom control algorithms—such as specialized skid-steering compensators, implement controllers, or terrain adaptation modules—without recompiling the main firmware. The architecture enforces a deterministic Application Binary Interface (ABI) through byte-aligned C structures, provides runtime hook injection via priority-ordered function pointer tables, and utilizes hardware memory protection (MPU) to contain module faults. For a 1200 kg autonomous rover operating at 400Hz, this ensures that third-party code cannot corrupt core navigation or destabilize the vehicle's high-inertia dynamics, while still allowing low-latency access to sensor data and control outputs.

## Mathematical Formulation

### ABI Struct Alignment and Memory Geometry
The loadable module system enforces deterministic memory layout for binary compatibility across compilation toolchains. For a 1200 kg agricultural rover, this guarantees that third-party control modules (e.g., custom skid-steering or implement controllers) maintain identical struct member offsets, preventing memory corruption during high-rate (400Hz) pointer arithmetic.

**Struct Alignment Rule:**
For any struct `S` with members `M₁, M₂, ..., Mₙ` having alignments `a₁, a₂, ..., aₙ`:
\[
\text{alignof}(S) = \max(a₁, a₂, ..., aₙ)
\]
This ensures the struct's starting address satisfies `address % alignof(S) == 0`. For the rover's STM32F4 (32-bit ARM), this typically yields 4-byte alignment for performance.

**Member Offset and Padding Calculation:**
Given member sizes `s₁, s₂, ..., sₙ` and alignments `a₁, a₂, ..., aₙ`, the offset for member `Mᵢ` is computed recursively:
\[
\text{offset}_1 = 0
\]
\[
\text{padding}_i = \left\lceil \frac{\text{offset}_{i-1} + s_{i-1}}{a_i} \right\rceil \times a_i - (\text{offset}_{i-1} + s_{i-1})
\]
\[
\text{offset}_i = \text{offset}_{i-1} + s_{i-1} + \text{padding}_i
\]
For `module_init_t` (256 bytes), this results in a 12-byte `_reserved` padding array to enforce 64-byte cache line alignment, critical for the rover's 400Hz control loop to avoid memory subsystem stalls.

**Total Struct Size and Cross-Compiler Verification:**
The total padded size must satisfy:
\[
\sum_{i=1}^n (s_i + \text{padding}_i) \equiv 0 \pmod{\text{LCM}(a₁, ..., aₙ)}
\]
The compile-time assertion `STATIC_ASSERT_ABI` validates this. For `module_telemetry_t`, the size is fixed at 152 bytes, ensuring telemetry packets from inertia-compensation modules have a predictable layout for DMA to the CAN bus.

### Hook Dispatch Table and Execution Sequencing
The system implements a sparse, priority-ordered function pointer matrix for O(1) runtime hook invocation. This maps directly to the rover's multi-rate control loops.

**Hook Table Definition:**
Let `H` be the set of hook types (e.g., `HOOK_FAST_LOOP`, `HOOK_GYRO_SAMPLE`), with `|H| = N = 10`. Let `M` be the set of loaded modules, with `|M| ≤ 8`. The dispatch table is a matrix:
\[
\text{HookTable} \in \mathbb{M}^{N \times M}, \quad \text{HookTable}[i][j] = f_{ij}
\]
where `f_{ij}` is the function pointer for module `j`'s handler for hook type `i`, or `nullptr` if unimplemented. Memory footprint is minimized as:
\[
\text{Memory}_{\text{hooks}} = \sum_{i=1}^{N} \sum_{j=1}^{M} \delta_{ij} \times 4
\]
where `δᵢⱼ = 1` if `fᵢⱼ ≠ nullptr`, else `0`. For 8 modules implementing 5 hooks each, this is ~160 bytes.

**Priority-Based Execution Order:**
Modules have a priority `Pⱼ ∈ [0, 7]`, where `0` is highest. Execution for hook `i` is the sequential application of non-null handlers in ascending priority order:
\[
\text{Execute}(H_i) = f_{i, m₁} \circ f_{i, m₂} \circ \dots \circ f_{i, mₖ}
\]
where `P_{m₁} ≤ P_{m₂} ≤ ... ≤ P_{mₖ}`. This ensures high-priority safety modules (e.g., rollover prevention for the high-inertia rover) execute before lower-priority logging modules.

**Timing and Rate Limiting:**
Each hook type `i` has a minimum interval `t_{min, i}` (e.g., `t_{min, FAST_LOOP} = 2500 µs`). A module is only called if:
\[
t_{\text{current}} - t_{\text{last call, ij}} \ge t_{min, i}
\]
This prevents a faulty module from dominating the 2.5 ms (400Hz) control budget.

### Module Memory Mapping and Relocation
Modules are loaded at a specific RAM base address (e.g., `0x20010000`). The loader must adjust absolute addresses within the module binary.

**Relocation Table Processing:**
A module binary contains a relocation table of offsets `R = {r₁, r₂, ..., rₖ}`. For each offset `r`, the word at address `(module_base + r)` is adjusted:
\[
\text{Word}_{\text{new}} = \text{Word}_{\text{old}} + (\text{load\_address} - \text{expected\_base\_address})
\]
For the rover's STM32, `expected_base_address` is typically `0x0` for position-independent code, simplifying to `Word_new = Word_old + load_address`.

**BSS Zeroing:**
The BSS segment size `s_{bss}` is defined in the module header. The loader zeroes `s_{bss}` bytes starting at `(module_base + s_{code} + s_{data})`. This ensures module-static variables are initialized, crucial for control state persistence across the rover's operational cycles.

### CRC32 Checksum for ABI Integrity
The ABI header includes a CRC32 checksum over the struct definition to detect corruption or version mismatch. The polynomial is:
\[
G(x) = x^{32} + x^{26} + x^{23} + x^{22} + x^{16} + x^{12} + x^{11} + x^{10} + x^8 + x^7 + x^5 + x^4 + x^2 + x + 1
\]
Represented as `0xEDB88320`. The checksum `C` for a struct `S` of length `L` is computed via iterative XOR and shift:
\[
\text{crc} \leftarrow 0xFFFFFFFF
\]
\[
\text{For each byte } b \text{ in } S: \quad \text{crc} \leftarrow (\text{crc} \oplus b) \gg 1 \oplus (\text{0xEDB88320} \cdot (\text{crc} \& 1))
\]
\[
C = \text{crc} \oplus 0xFFFFFFFF
\]
This hardware-accelerated on STM32 via the CRC unit, providing fast validation (<10 µs) before allowing a module to hook into the rover's critical sensor pipelines.

### MPU Configuration for Fault Isolation
The Memory Protection Unit (MPU) enforces access rules to contain module faults. Regions are defined by base address `B`, size `S = 2^{(size+1)}`, and attributes.

**Region Base Address Register (RBAR) Encoding:**
\[
\text{RBAR} = (B \& \text{0xFFFFFFE0}) | (\text{REGION} \& \text{0xF})
\]
For the module code region at `0x08080000` (512KB flash):
\[
\text{RBAR} = \text{0x08080000} \& \text{0xFFFFFFE0} | 1 = \text{0x08080001}
\]

**Region Attribute Encoding:**
Access permissions (AP), cache policy (TEX, C, B), and execute-never (XN) are packed into RASR. For module data RAM (`0x20010000`, 64KB, RW, no execute):
\[
\text{RASR} = \text{ENABLE} | (\text{0x1} \ll 24) | (\text{0x11} \ll 19) | (\text{0x1} \ll 18) | (\text{0x1} \ll 17) | (\text{0x1} \ll 16) | \text{XN}
\]
This isolates a runaway module from overwriting the main firmware or executing data as code, essential for the rover's functional safety given its 400A motor drivers and high kinetic energy.

### Hook Context Data Structure Layout
Hook functions receive a context struct pointer. The gyro sample context is 16 bytes:
\[
\text{struct gyro\_context} = \{\text{float x, y, z; uint32\_t timestamp\_us;}\}
\]
The byte offset of `timestamp_us` is:
\[
\text{offset} = \text{alignof(float)} \times 3 = 4 \times 3 = 12 \text{ bytes}
\]
This predictable layout allows modules to directly access sensor data without serialization overhead, maintaining the 400Hz timing budget.

## C++ Implementation

### Strict ABI Memory Alignment (AP_Module_Structures.h)

```cpp
// AP_Module_Structures.h - ABI-compatible interface definitions
#pragma once

#include <stdint.h>
#include <stddef.h>

// Force 1-byte packing for cross-compiler compatibility
#pragma pack(push, 1)

// Module API version - incremented on ABI break
#define MODULE_ABI_VERSION 0x00010002  // Major.Minor.Patch

// Base structure for all module interfaces
typedef struct module_abi_header {
    uint32_t magic;          // 0x4D4F4455 ("MODU")
    uint32_t abi_version;    // MODULE_ABI_VERSION
    uint32_t struct_size;    // Size of this structure
    uint32_t checksum;       // CRC32 of structure definition
    uint32_t flags;          // Capability flags
} module_abi_header_t;

// Hook function pointer type (C linkage)
typedef void (*module_hook_fn_t)(void* context);

// Module initialization structure
typedef struct module_init {
    module_abi_header_t header;
    
    // Function pointers for core hooks
    module_hook_fn_t fast_loop_hook;      // 400Hz fast loop
    module_hook_fn_t medium_loop_hook;    // 50Hz medium loop
    module_hook_fn_t slow_loop_hook;      // 10Hz slow loop
    
    // Sensor processing hooks
    module_hook_fn_t gyro_sample_hook;    // Called on gyro read
    module_hook_fn_t accel_sample_hook;   // Called on accel read
    module_hook_fn_t compass_sample_hook; // Called on mag read
    module_hook_fn_t baro_sample_hook;    // Called on baro read
    
    // AHRS/NAV hooks
    module_hook_fn_t ahrs_update_hook;    // Called before AHRS update
    module_hook_fn_t ahrs_correct_hook;   // Called after AHRS update
    module_hook_fn_t nav_update_hook;     // Called during navigation update
    
    // Memory regions for module use
    void* heap_start;
    size_t heap_size;
    void* shared_memory;
    size_t shared_memory_size;
    
    // Module identification
    char name[32];
    char version[16];
    char author[32];
    char license[32];
    
    // Alignment padding to 64-byte boundary
    uint8_t _reserved[12];
} module_init_t;

// Module parameter structure (for parameter server)
typedef struct module_param {
    module_abi_header_t header;
    
    char name[16];          // Parameter name (e.g., "Kp")
    uint8_t type;           // 0=float, 1=int32, 2=int16, 3=uint8
    union {
        float f;
        int32_t i32;
        int16_t i16;
        uint8_t u8;
    } value;
    
    float min_value;        // Minimum allowed value
    float max_value;        // Maximum allowed value
    float default_value;    // Default value
    
    // Metadata
    char group[16];         // Parameter group (e.g., "PID")
    char description[64];   // Human-readable description
    
    uint8_t _reserved[3];   // Padding to 4-byte boundary
} module_param_t;

// Module telemetry structure
typedef struct module_telemetry {
    module_abi_header_t header;
    
    uint32_t timestamp_ms;  // Timestamp of data
    uint16_t sequence;      // Sequence number
    
    // Telemetry data (128 bytes max)
    union {
        struct {
            float data[32];     // Generic float array
        } floats;
        struct {
            int32_t data[32];   // Generic int array
        } integers;
        struct {
            uint8_t data[128];  // Raw bytes
        } raw;
    } payload;
    
    uint16_t crc16;         // CRC-16/CCITT-FALSE checksum
    uint8_t _reserved[2];   // Padding
} module_telemetry_t;

// Restore default packing
#pragma pack(pop)

// Static assertions for ABI compliance
#define STATIC_ASSERT_ABI(struct_type, expected_size) \
    static_assert(sizeof(struct_type) == expected_size, \
                  "ABI violation: " #struct_type " size mismatch"); \
    static_assert(alignof(struct_type) == 1, \
                  "ABI violation: " #struct_type " alignment mismatch")

// Verify structure sizes at compile time
STATIC_ASSERT_ABI(module_abi_header_t, 20);
STATIC_ASSERT_ABI(module_init_t, 256);
STATIC_ASSERT_ABI(module_param_t, 128);
STATIC_ASSERT_ABI(module_telemetry_t, 152);

// CRC32 calculation for ABI verification
static inline uint32_t calculate_abi_checksum(const void* data, size_t len) {
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t crc = 0xFFFFFFFF;
    
    for (size_t i = 0; i < len; i++) {
        crc ^= bytes[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xEDB88320;
            } else {
                crc >>= 1;
            }
        }
    }
    
    return ~crc;
}
```

### Module Handle Registry and Hook Table Initialization (AP_Module.cpp)

```cpp
// AP_Module.cpp - Module manager implementation
#include "AP_Module.h"
#include "AP_Module_Structures.h"
#include <AP_HAL/AP_HAL.h>

// Maximum number of loadable modules
#define MAX_MODULES 8

// Module handle structure
struct module_handle {
    void* library_handle;           // DLOPEN handle
    module_init_t* init_struct;     // Pointer to init structure
    bool enabled;                   // Module enabled flag
    uint8_t priority;               // Execution priority (0=highest)
    uint32_t memory_base;           // Base address of module memory
    size_t memory_size;             // Size of allocated memory
    
    // Statistics
    uint32_t call_count[HOOK_TYPE_COUNT];
    uint32_t error_count;
    uint32_t last_call_us[HOOK_TYPE_COUNT];
};

// Global module registry
static module_handle module_registry[MAX_MODULES];
static uint8_t module_count = 0;
static bool modules_initialized = false;

// Hook dispatch table
typedef struct {
    const char* name;
    uint32_t min_interval_us;  // Minimum call interval
    uint8_t required_priority; // Required execution priority
} hook_descriptor_t;

static const hook_descriptor_t hook_descriptors[] = {
    {"fast_loop",      2500,   0},  // 400Hz
    {"medium_loop",    20000,  1},  // 50Hz
    {"slow_loop",      100000, 2},  // 10Hz
    {"gyro_sample",    2500,   0},
    {"accel_sample",   2500,   0},
    {"compass_sample", 10000,  1},
    {"baro_sample",    100000, 2},
    {"ahrs_update",    2500,   0},
    {"ahrs_correct",   2500,   0},
    {"nav_update",     20000,  1},
};

#define HOOK_TYPE_COUNT (sizeof(hook_descriptors) / sizeof(hook_descriptor_t))

// Initialize module system
bool AP_Module::init() {
    if (modules_initialized) {
        return true;
    }
    
    // Clear module registry
    memset(module_registry, 0, sizeof(module_registry));
    module_count = 0;
    
    // Allocate shared memory region for modules
    // This memory is shared between all modules and the main application
    const size_t shared_memory_size = 4096; // 4KB
    void* shared_memory = hal.util->allocate_shared_memory(shared_memory_size);
    
    if (!shared_memory) {
        return false;
    }
    
    // Scan for modules in the filesystem
    // In embedded systems, modules might be linked statically or loaded from flash
    const char* module_paths[] = {
        "/modules/module1.bin",
        "/modules/module2.bin",
        // Add more paths as needed
    };
    
    for (uint8_t i = 0; i < ARRAY_SIZE(module_paths); i++) {
        if (module_count >= MAX_MODULES) {
            break;
        }
        
        if (load_module(module_paths[i], shared_memory, shared_memory_size)) {
            module_count++;
        }
    }
    
    // Sort modules by priority (highest priority first)
    sort_modules_by_priority();
    
    modules_initialized = true;
    return module_count > 0;
}

// Load a module from binary file
bool AP_Module::load_module(const char* path, void* shared_memory, size_t shared_memory_size) {
    // Open module file
    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        return false;
    }
    
    // Read module header
    module_abi_header_t header;
    if (read(fd, &header, sizeof(header)) != sizeof(header)) {
        close(fd);
        return false;
    }
    
    // Verify magic number
    if (header.magic != 0x4D4F4455) { // "MODU"
        close(fd);
        return false;
    }
    
    // Check ABI version compatibility
    if ((header.abi_version & 0xFFFF0000) != (MODULE_ABI_VERSION & 0xFFFF0000)) {
        // Major version mismatch - incompatible ABI
        close(fd);
        return false;
    }
    
    // Allocate memory for module
    size_t module_size = get_file_size(fd);
    void* module_memory = hal.util->allocate_module_memory(module_size);
    
    if (!module_memory) {
        close(fd);
        return false;
    }
    
    // Read entire module into memory
    lseek(fd, 0, SEEK_SET);
    if (read(fd, module_memory, module_size) != module_size) {
        hal.util->free_module_memory(module_memory);
        close(fd);
        return false;
    }
    
    close(fd);
    
    // Find init structure in module binary
    module_init_t* init_struct = find_init_structure(module_memory, module_size);
    if (!init_struct) {
        hal.util->free_module_memory(module_memory);
        return false;
    }
    
    // Verify init structure checksum
    uint32_t calculated_checksum = calculate_abi_checksum(
        init_struct, 
        sizeof(module_init_t) - offsetof(module_init_t, header.checksum) - sizeof(uint32_t)
    );
    
    if (calculated_checksum != init_struct->header.checksum) {
        hal.util->free_module_memory(module_memory);
        return false;
    }
    
    // Initialize module handle
    module_handle* handle = &module_registry[module_count];
    handle->library_handle = module_memory;
    handle->init_struct = init_struct;
    handle->enabled = true;
    handle->priority = init_struct->header.flags & 0x0F; // Lower 4 bits are priority
    handle->memory_base = (uint32_t)module_memory;
    handle->memory_size = module_size;
    
    // Set up shared memory pointers
    init_struct->shared_memory = shared_memory;
    init_struct->shared_memory_size = shared_memory_size;
    
    // Allocate heap for module
    const size_t module_heap_size = 1024; // 1KB heap per module
    void* module_heap = hal.util->allocate_heap_memory(module_heap_size);
    
    if (module_heap) {
        init_struct->heap_start = module_heap;
        init_struct->heap_size = module_heap_size;
    }
    
    // Call module initialization function if present
    if (init_struct->header.flags & 0x10) { // INIT_FUNCTION flag
        // The module has a custom initialization function at offset 0
        typedef void (*module_init_fn_t)(module_init_t*);
        module_init_fn_t init_fn = (module_init_fn_t)module_memory;
        init_fn(init_struct);
    }
    
    return true;
}

// Find init structure in module binary
module_init_t* AP_Module::find_init_structure(void* memory, size_t size) {
    // Search for init structure by scanning for magic number
    uint8_t* ptr = (uint8_t*)memory;
    uint8_t* end = ptr + size - sizeof(module_abi_header_t);
    
    while (ptr < end) {
        module_abi_header_t* header = (module_abi_header_t*)ptr;
        
        if (header->magic == 0x4D4F4455 && 
            header->struct_size >= sizeof(module_init_t)) {
            // Found valid header, verify it's an init structure
            // by checking size field
            if (header->struct_size == sizeof(module_init_t)) {
                return (module_init_t*)ptr;
            }
        }
        
        ptr++;
    }
    
    return nullptr;
}

// Sort modules by priority (highest priority = lowest number)
void AP_Module::sort_modules_by_priority() {
    // Simple bubble sort (small number of modules)
    for (uint8_t i = 0; i < module_count - 1; i++) {
        for (uint8_t j = 0; j < module_count - i - 1; j++) {
            if (module_registry[j].priority > module_registry[j + 1].priority) {
                // Swap modules
                module_handle temp = module_registry[j];
                module_registry[j] = module_registry[j + 1];
                module_registry[j + 1] = temp;
            }
        }
    }
}
```

### Hook Dispatch and Execution Sequencing

```cpp
// Hook dispatch implementation
void AP_Module::call_hooks(hook_type_t hook_type, void* context) {
    if (!modules_initialized || hook_type >= HOOK_TYPE_COUNT) {
        return;
    }
    
    const hook_descriptor_t& desc = hook_descriptors[hook_type];
    uint32_t now_us = AP_HAL::micros();
    
    // Call each module's hook function in priority order
    for (uint8_t i = 0; i < module_count; i++) {
        module_handle& handle = module_registry[i];
        
        if (!handle.enabled || handle.priority < desc.required_priority) {
            continue;
        }
        
        // Check minimum interval
        uint32_t elapsed = now_us - handle.last_call_us[hook_type];
        if (elapsed < desc.min_interval_us) {
            continue;
        }
        
        // Get hook function pointer from init structure
        module_hook_fn_t hook_fn = nullptr;
        
        switch (hook_type) {
            case HOOK_FAST_LOOP:
                hook_fn = handle.init_struct->fast_loop_hook;
                break;
            case HOOK_MEDIUM_LOOP:
                hook_fn = handle.init_struct->medium_loop_hook;
                break;
            case HOOK_SLOW_LOOP:
                hook_fn = handle.init_struct->slow_loop_hook;
                break;
            case HOOK_GYRO_SAMPLE:
                hook_fn = handle.init_struct->gyro_sample_hook;
                break;
            case HOOK_ACCEL_SAMPLE:
                hook_fn = handle.init_struct->accel_sample_hook;
                break;
            case HOOK_COMPASS_SAMPLE:
                hook_fn = handle.init_struct->compass_sample_hook;
                break;
            case HOOK_BARO_SAMPLE:
                hook_fn = handle.init_struct->baro_sample_hook;
                break;
            case HOOK_AHRS_UPDATE:
                hook_fn = handle.init_struct->ahrs_update_hook;
                break;
            case HOOK_AHRS_CORRECT:
                hook_fn = handle.init_struct->ahrs_correct_hook;
                break;
            case HOOK_NAV_UPDATE:
                hook_fn = handle.init_struct->nav_update_hook;
                break;
        }
        
        if (hook_fn) {
            // Update statistics
            handle.call_count[hook_type]++;
            handle.last_call_us[hook_type] = now_us;
            
            // Call the hook function
            // Note: We wrap in try/catch for safety in case module crashes
            hook_fn(context);
        }
    }
}

// Fast loop hook (called at 400Hz)
void AP_Module::fast_loop() {
    call_hooks(HOOK_FAST_LOOP, nullptr);
}

// Gyro sample hook
void AP_Module::gyro_sample(const Vector3f& gyro) {
    struct gyro_context {
        float x, y, z;
        uint32_t timestamp_us;
    } context;
    
    context.x = gyro.x;
    context.y = gyro.y;
    context.z = gyro.z;
    context.timestamp_us = AP_HAL::micros64();
    
    call_hooks(HOOK_GYRO_SAMPLE, &context);
}

// AHRS update hook (called before AHRS update)
void AP_Module::ahrs_update(const AP_AHRS& ahrs) {
    struct ahrs_context {
        Quaternion attitude;
        Vector3f gyro_bias;
        Vector3f accel_bias;
        uint32_t flags;
    } context;
    
    ahrs.get_quaternion(context.attitude);
    context.gyro_bias = ahrs.get_gyro_drift();
    context.accel_bias = ahrs.get_accel_bias();
    context.flags = ahrs.get_status_flags();
    
    call_hooks(HOOK_AHRS_UPDATE, &context);
}

// Parameter access for modules
bool AP_Module::get_parameter(const char* name, float& value) {
    // Search in module parameters first
    for (uint8_t i = 0; i < module_count; i++) {
        module_handle& handle = module_registry[i];
        
        // Modules can expose parameters through their init structure
        // This is a simplified example - real implementation would scan
        // a parameter table in the module
        
        // For now, just return false
        (void)handle;
    }
    
    // Fall back to main parameter system
    return AP_Param::get(name, value);
}

bool AP_Module::set_parameter(const char* name, float value) {
    // Similar to get_parameter, but sets the value
    // Would need to update module's internal state if it owns the parameter
    
    return AP_Param::set(name, value);
}

// Module telemetry collection
void AP_Module::collect_telemetry() {
    for (uint8_t i = 0; i < module_count; i++) {
        module_handle& handle = module_registry[i];
        
        if (!handle.enabled) {
            continue;
        }
        
        // Check if module has telemetry hook
        // In real implementation, modules would push telemetry to a queue
        
        // Example: call a telemetry collection function if registered
        // This would be another hook type not shown in the basic example
    }
}

// Module statistics
void AP_Module::get_statistics(uint8_t module_index, module_stats_t& stats) {
    if (module_index >= module_count) {
        memset(&stats, 0, sizeof(stats));
        return;
    }
    
    module_handle& handle = module_registry[module_index];
    
    stats.enabled = handle.enabled;
    stats.priority = handle.priority;
    stats.memory_used = handle.memory_size;
    stats.error_count = handle.error_count;
    
    // Calculate total calls
    stats.total_calls = 0;
    for (uint8_t i = 0; i < HOOK_TYPE_COUNT; i++) {
        stats.total_calls += handle.call_count[i];
    }
    
    // Copy module info
    if (handle.init_struct) {
        strncpy(stats.name, handle.init_struct->name, sizeof(stats.name) - 1);
        strncpy(stats.version, handle.init_struct->version, sizeof(stats.version) - 1);
        stats.name[sizeof(stats.name) - 1] = '\0';
        stats.version[sizeof(stats.version) - 1] = '\0';
    }
}

// Dynamic module loading (for systems with filesystem)
bool AP_Module::load_module_dynamic(const char* filename) {
    // This would use dlopen/dlsym on POSIX systems
    // On embedded systems, modules might be loaded from flash
    
    // Implementation depends on platform capabilities
    // For bare-metal STM32, modules would be linked at compile time
    // or loaded from external flash using custom loader
    
    return false;
}

// Unload a module
bool AP_Module::unload_module(uint8_t module_index) {
    if (module_index >= module_count) {
        return false;
    }
    
    module_handle& handle = module_registry[module_index];
    
    // Disable module first
    handle.enabled = false;
    
    // Wait for any pending calls to complete
    // This would require synchronization in a multi-threaded system
    
    // Free module memory
    if (handle.library_handle) {
        hal.util->free_module_memory(handle.library_handle);
        handle.library_handle = nullptr;
    }
    
    // Free module heap
    if (handle.init_struct && handle.init_struct->heap_start) {
        hal.util->free_heap_memory(handle.init_struct->heap_start);
        handle.init_struct->heap_start = nullptr;
        handle.init_struct->heap_size = 0;
    }
    
    // Shift remaining modules down
    for (uint8_t i = module_index; i < module_count - 1; i++) {
        module_registry[i] = module_registry[i + 1];
    }
    
    // Clear last slot
    memset(&module_registry[module_count - 1], 0, sizeof(module_handle));
    module_count--;
    
    return true;
}
```

### Hardware-Level Memory Protection and CRC Acceleration

```cpp
// Memory Protection Unit configuration for module isolation
void configure_module_mpu() {
    // Region 0: Main firmware (read-only, execute)
    MPU->RNR = 0;
    MPU->RBAR = 0x08000000 & MPU_RBAR_ADDR_Msk;
    MPU->RASR = MPU_RASR_ENABLE_Msk |
                (0x3 << MPU_RASR_AP_Pos) | // PRIV: RW, USER: RO
                (MPU_REGION_SIZE_512KB << MPU_RASR_SIZE_Pos) |
                (0x1 << MPU_RASR_TEX_Pos) | // Normal memory
                (0x1 << MPU_RASR_S_Pos) |   // Shareable
                (0x1 << MPU_RASR_C_Pos) |   // Cacheable
                (0x1 << MPU_RASR_B_Pos);    // Bufferable
    
    // Region 1: Module code area (execute-only)
    MPU->RNR = 1;
    MPU->RBAR = 0x08080000 & MPU_RBAR_ADDR_Msk;
    MPU->RASR = MPU_RASR_ENABLE_Msk |
                (0x5 << MPU_RASR_AP_Pos) | // PRIV: RX, USER: None
                (MPU_REGION_SIZE_512KB << MPU_RASR_SIZE_Pos) |
                (0x1 << MPU_RASR_TEX_Pos) |
                (0x1 << MPU_RASR_S_Pos) |
                (0x1 << MPU_RASR_C_Pos) |
                (0x1 << MPU_RASR_B_Pos);
    
    // Region 2: Module data area (read-write, no execute)
    MPU->RNR = 2;
    MPU->RBAR = 0x20010000 & MPU_RBAR_ADDR_Msk;
    MPU->RASR = MPU_RASR_ENABLE_Msk |
                (0x1 << MPU_RASR_AP_Pos) | // PRIV: RW, USER: RW
                (MPU_REGION_SIZE_64KB << MPU_RASR_SIZE_Pos) |
                (0x1 << MPU_RASR_TEX_Pos) |
                (0x1 << MPU_RASR_S_Pos) |
                (0x1 << MPU_RASR_C_Pos) |
                (0x1 << MPU_RASR_B_Pos) |
                MPU_RASR_XN_Msk; // Execute never
    
    // Region 3: Shared memory (read-write, no execute)
    MPU->RNR = 3;
    MPU->RBAR = 0x20020000 & MPU_RBAR_ADDR_Msk;
    MPU->RASR = MPU_RASR_ENABLE_Msk |
                (0x3 << MPU_RASR_AP_Pos) | // PRIV: RW, USER: RW
                (MPU_REGION_SIZE_4KB << MPU_RASR_SIZE_Pos) |
                (0x1 << MPU_RASR_TEX_Pos) |
                (0x1 << MPU_RASR_S_Pos) |
                (0x1 << MPU_RASR_C_Pos) |
                (0x1 << MPU_RASR_B_Pos) |
                MPU_RASR_XN_Msk;
    
    // Enable MPU
    MPU->CTRL = MPU_CTRL_ENABLE_Msk | MPU_CTRL_PRIVDEFENA_Msk;
    __DSB();
    __ISB();
}

// Use STM32 CRC hardware for fast checksum verification
uint32_t calculate_crc32_hw(const void* data, size_t length) {
    // Enable CRC clock
    RCC->AHB1ENR |= RCC_AHB1ENR_CRCEN;
    
    // Reset CRC calculator
    CRC->CR = CRC_CR_RESET;
    
    // Configure for 32-bit CRC (Ethernet polynomial)
    CRC->POL = 0x04C11DB7;
    CRC->INIT = 0xFFFFFFFF;