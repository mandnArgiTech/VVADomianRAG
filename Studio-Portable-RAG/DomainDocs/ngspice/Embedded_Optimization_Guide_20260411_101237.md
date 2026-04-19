# Embedded Optimization Guide

_Generated 2026-04-11 10:12 UTC — crewai/ngspice_book_factory_

# Embedded Optimization Guide

## Introduction
This guide provides practical techniques for optimizing memory usage in embedded systems using FreeRTOS on ESP32 and STM32 platforms. By implementing these strategies, you can significantly reduce RAM and flash consumption while maintaining system reliability.

## 1. Precise Task Stack Sizing

### Problem
Over-allocated task stacks waste RAM, while under-allocated stacks cause system crashes.

### Solution
**Empirical analysis with overflow detection:**

- **Enable stack overflow detection:**
  ```c
  // In FreeRTOSConfig.h
  #define configCHECK_FOR_STACK_OVERFLOW 2
  ```
  - Value `1`: Basic detection (checks stack pointer only)
  - Value `2`: Enhanced detection (fills stack with pattern and verifies)

- **Monitor stack usage during development:**
  ```c
  // Call this periodically during stress testing
  UBaseType_t highWaterMark = uxTaskGetStackHighWaterMark(taskHandle);
  ```

### Implementation Steps
1. Run your system through worst-case scenarios:
   - Maximum interrupt load
   - Deepest function call chains
   - Peak data processing conditions

2. Record high-water marks for each task

3. Set final stack sizes with safety margin:
   ```
   Final Stack Size = (Maximum Observed Usage) × (1.2)
   ```

### Expected Savings
- **ESP32:** 100-500 bytes per task
- **STM32:** 50-300 bytes per task

## 2. Heap Manager Selection and Configuration

### Available Heap Implementations
| Heap Version | Best For | Fragmentation | Overhead |
|--------------|----------|---------------|----------|
| heap_1       | Simple, static allocation | None | Minimal |
| heap_2       | Repeated allocation/deletion | Medium | Low |
| heap_3       | Thread-safe with malloc wrapper | Medium | Medium |
| **heap_4**   | **General purpose** | **Low** | **Medium** |
| heap_5       | Multiple memory regions | Low | Higher |

### Recommended Configuration

**For most ESP32/STM32 applications:**
```c
// Use heap_4 for balanced performance
#define configUSE_MALLOC_FAILED_HOOK 1
#define configTOTAL_HEAP_SIZE ((size_t)(16 * 1024)) // Adjust based on measurements
```

**Heap sizing procedure:**
1. Monitor heap usage during operation:
   ```c
   size_t freeHeap = xPortGetFreeHeapSize();
   size_t minimumEverFree = xPortGetMinimumEverFreeHeapSize();
   ```

2. Set `configTOTAL_HEAP_SIZE` to:
   ```
   Peak Usage + (10-20% Safety Margin)
   ```

### Advanced: Using Heap_5 for Complex Memory Layouts
**For STM32 with multiple SRAM banks:**
```c
// Define memory regions
const HeapRegion_t xHeapRegions[] = {
    { (uint8_t *)0x20000000UL, 0x10000 }, // SRAM1
    { (uint8_t *)0x20010000UL, 0x8000 },  // SRAM2
    { NULL, 0 } // Terminator
};

vPortDefineHeapRegions(xHeapRegions);
```

## 3. Disabling Unused Kernel Features

### Configuration Macros to Review
In `FreeRTOSConfig.h`, disable unnecessary features:

```c
// Disable unused components
#define configUSE_TIMERS             0    // Save ~1KB RAM if not using timers
#define configUSE_EVENT_GROUPS       0    // Save ~200 bytes
#define configUSE_MUTEXES            0    // Save per-mutex overhead
#define configUSE_RECURSIVE_MUTEXES  0
#define configUSE_COUNTING_SEMAPHORES 0

// Optimize scheduler
#define configMAX_PRIORITIES         5    // Minimum required for your app
#define configUSE_TIME_SLICING       0    // Disable if not needed
#define configUSE_QUEUE_SETS         0
```

### Memory Impact
| Feature Disabled | RAM Savings | Flash Savings |
|------------------|-------------|---------------|
| Software Timers  | 1-2 KB      | 3-5 KB        |
| Event Groups     | 200-400 bytes | 1-2 KB       |
| Reduced Priorities | 50 bytes per unused priority | Minimal |

### Verification
After disabling features:
1. Compile and check map file for size reduction
2. Run regression tests to ensure functionality
3. Monitor stack usage (some features share kernel task stacks)

## 4. Dynamic Peripheral Management

### Buffer Management Strategy

**Lazy Initialization Pattern:**
```c
// Example for UART peripheral
static uint8_t *uartBuffer = NULL;

void uart_send_data(const uint8_t *data, size_t length) {
    if (uartBuffer == NULL) {
        uartBuffer = pvPortMalloc(UART_BUFFER_SIZE);
        uart_init(); // Hardware initialization
    }
    
    // Use buffer for DMA or processing
    memcpy(uartBuffer, data, length);
    // ... send operation
}

void uart_enter_low_power(void) {
    if (uartBuffer != NULL) {
        uart_deinit(); // Disable hardware
        vPortFree(uartBuffer);
        uartBuffer = NULL;
    }
}
```

### Platform-Specific Techniques

**ESP32 Power Management:**
```c
// Enable peripheral wakeup for light sleep
esp_sleep_enable_peripheral_wakeup();

// Disable peripherals before sleep
periph_module_disable(PERIPH_UART0_MODULE);
periph_module_disable(PERIPH_SPI_MODULE);

// Re-enable when needed
periph_module_enable(PERIPH_UART0_MODULE);
```

**STM32 Clock Gating:**
```c
// Disable peripheral clocks when not in use
__HAL_RCC_USART1_CLK_DISABLE();
__HAL_RCC_SPI1_CLK_DISABLE();
__HAL_RCC_ADC1_CLK_DISABLE();

// Enable only when needed
__HAL_RCC_USART1_CLK_ENABLE();
```

### Implementation Checklist
- [ ] Identify peripherals with intermittent usage
- [ ] Implement initialization/deinitialization functions
- [ ] Add timeout-based power-down mechanisms
- [ ] Verify wakeup and reinitialization timing requirements
- [ ] Test power consumption in different states

## Monitoring and Validation

### Essential Debugging Tools
1. **Stack monitoring:** `uxTaskGetStackHighWaterMark()`
2. **Heap monitoring:** `xPortGetFreeHeapSize()`
3. **Runtime stats:** `vTaskGetRunTimeStats()`
4. **Task list:** `vTaskList()` (requires `configUSE_TRACE_FACILITY`)

### Testing Protocol
1. **Baseline measurement:** Record initial memory usage
2. **Stress testing:** Simulate worst-case scenarios
3. **Long-term testing:** Run for 24+ hours to detect fragmentation
4. **Power cycling:** Test initialization after deep sleep/reset

## Safety Considerations

### Minimum Safe Margins
- **Stack:** 10-20% above measured high-water mark
- **Heap:** 15-25% above minimum ever free
- **Interrupt context:** Account for nested interrupt stack usage

### Recovery Mechanisms
```c
// Implement failure hooks
void vApplicationMallocFailedHook(void) {
    // Log error, reset, or enter safe mode
}

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName) {
    // Critical error handling
}
```

## Conclusion
By systematically applying these four optimization techniques, you can achieve significant memory savings:

1. **Precise stack sizing** eliminates wasted RAM in task stacks
2. **Appropriate heap selection** reduces fragmentation overhead
3. **Feature disabling** removes unused kernel components
4. **Dynamic peripheral management** minimizes driver memory footprint

Start with stack optimization (highest impact), then proceed through each technique while continuously monitoring system stability. Document all changes and maintain the ability to revert optimizations if unexpected behavior occurs.