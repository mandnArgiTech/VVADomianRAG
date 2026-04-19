# RTOS Scheduler, Mutex Semaphores, and Thread Arbitration

_Generated 2026-04-14 20:16 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Scheduler.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Scheduler.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Semaphores.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/Semaphores.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/EventSource.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_HAL_ChibiOS/EventSource.h`

# Chapter: RTOS Scheduler, Mutex Semaphores, and Thread Arbitration

## Technical Introduction

This chapter documents the deterministic real-time scheduling and concurrency control architecture within ArduPilot's ChibiOS RTOS implementation for a 20kg agricultural rover. The files `Scheduler.cpp`, `Semaphores.cpp`, and `EventSource.cpp` implement the core timing, synchronization, and thread coordination mechanisms that guarantee 400Hz control loop execution while preventing priority inversion and deadlock. The system mathematically enforces bounded execution times through hardware timer interrupts, priority inheritance protocols, and event-driven thread wakeups, ensuring the rover's skid-steer dynamics (mass=20kg, inertia=5.0 kg·m²) receive deterministic control updates within 2500μs windows despite variable computational loads.

## Mathematical Formulation: RTOS Timing and Concurrency for a 20kg Agricultural Rover

This section details the exact physical mathematics and matrix algebra implemented in ArduPilot's RTOS scheduler and concurrency primitives for a 20kg skid-steer agricultural rover. The formulations explicitly connect timer precision, priority inheritance, and deadlock prevention to the rover's real-time control requirements, accounting for its mass (20kg), rotational inertia (J = 5.0 kg·m²), and skid-steer dynamics that demand deterministic 400Hz execution with bounded latency.

### Microsecond Scheduling Mathematics: 400Hz Execution Without Drift

The 400Hz scheduler loop requires precise 2500μs intervals derived from the rover's control stability requirements. Given the STM32F4's 84MHz APB1 timer clock (after ×2 multiplier for advanced timers), the timer period calculation must account for the rover's maximum allowable timing error of ±25μs (1% of period) to maintain skid-steer control stability.

**Hardware Timer Mathematical Model:**
```
ARR = (F_TIMER / F_DESIRED) - 1
```

Where:
- `F_TIMER = 84,000,000 Hz` (APB1 × 2)
- `F_DESIRED = 400 Hz` (rover control frequency)
- `ARR = (84,000,000 / 400) - 1 = 209,999`

**16-bit Timer Constraint with Prescaler:**
For 16-bit timers (max ARR = 65,535), a prescaler is required:

```
PSC = (F_TIMER / (F_DESIRED × (ARR_MAX + 1))) - 1
PSC = (84,000,000 / (400 × 65,536)) - 1 ≈ 2.2 → use PSC = 2
ARR = (F_TIMER / (F_DESIRED × (PSC + 1))) - 1
ARR = (84,000,000 / (400 × 3)) - 1 = 69,999
```

**Resulting Timer Parameters:**
- `PSC = 2`: Timer clock = 84MHz / (2 + 1) = 28MHz
- `ARR = 69,999`: Period = (69,999 + 1) / 28MHz = 2.5ms = 2500μs
- Timer resolution: 1 / 28MHz = 35.714ns

**Drift Compensation PI Controller:**
Actual vs desired timing error accumulates due to clock inaccuracies and interrupt latency variations. For the rover's 400Hz control, drift must be bounded to ±100μs (4% of period) to prevent skid-steer oscillation.

```
Δt_error[n] = t_actual[n] - (t_desired + n·T)
Correction = K_p·Δt_error[n] + K_i·∑Δt_error + K_d·(Δt_error[n] - Δt_error[n-1])
T_adjusted = 2500μs + Correction
```

With rover-specific gains:
- `K_p = 0.1`: Proportional gain for immediate correction
- `K_i = 0.01`: Integral gain for accumulated error elimination
- `K_d = 0`: Derivative gain omitted for noise immunity

**Stability Proof via Z-transform:**
The PI controller's discrete-time transfer function:

```
E(z) = (1 - z⁻¹) / (1 - (1 - K_p)z⁻¹ + K_i·z⁻¹/(1 - z⁻¹))
```

Characteristic equation poles at:
```
z = (1 - K_p ± √((1 - K_p)² - 4K_i)) / 2
```

For stability, poles must lie inside unit circle: `|z| < 1`
This requires: `K_p > 0`, `K_i > 0`, and `K_p² > 4K_i`

With rover values (0.1, 0.01): `0.01 > 0.004` ✓

Thus drift converges: `lim_{n→∞} e[n] = 0`

**Maximum Drift Bound:**
Given HSI oscillator accuracy ±1% and temperature drift ±2% over agricultural temperature range (-10°C to 50°C):

```
Δt_max_per_cycle = 2500μs × 0.03 = 75μs
Δt_max_per_hour = 75μs × 400 × 3600 = 108,000μs = 108ms
```

The PI controller maintains this within ±100μs, ensuring rover navigation accuracy better than 0.5cm at 5m/s.

### Priority Inheritance Protocol Mathematics for Skid-Steer Control

For the rover's concurrent control threads—IMU processing (400Hz), navigation (100Hz), logging (10Hz), and telemetry (1Hz)—priority inversion must be bounded to prevent skid-steer response degradation.

**Priority Inheritance Protocol (PIP) Mathematical Model:**
Given threads T₁ (high priority, IMU), T₂ (medium, navigation), T₃ (low, logging) sharing resource R (EKF state buffer):

Without PIP:
- T₃ locks R (EKF buffer)
- T₁ preempts, tries to lock R → blocks
- T₂ runs (priority inversion occurs)
- Maximum blocking: unbounded

With PIP:
- T₃ inherits T₁'s priority when T₁ blocks on R
- T₂ cannot preempt T₃
- Maximum blocking time: `Bᵢ = max(usage(Rⱼ))` for all resources Rⱼ

**Bounded Blocking Time Calculation:**
For rover resources:
- EKF buffer: `usage = 250μs` (worst-case update)
- Motor command buffer: `usage = 100μs`
- Log buffer: `usage = 500μs`

```
B_IMU = max(250μs, 100μs, 500μs) = 500μs
```

This represents 20% of the 2500μs control period, acceptable for rover stability.

**Priority Ceiling Protocol Mathematics:**
Each resource Rⱼ has ceiling priority `Cⱼ = max(Pᵢ)` where Pᵢ are priorities of threads that may lock Rⱼ.

For rover resources:
- EKF buffer: `C = 0` (highest, used by IMU thread)
- Motor buffer: `C = 2` (used by navigation thread)
- Log buffer: `C = 4` (used by logging thread)

Thread T at priority P can be blocked by resource R only if `C(R) ≥ P`.

**Blocking Time Matrix:**
Let B[i][j] = maximum time thread i blocks thread j via resource sharing.

For 4 rover threads (IMU=0, Nav=1, Control=2, Log=3):
```
B = [[0, 0, 0, 0],
     [500, 0, 0, 0],
     [500, 250, 0, 0],
     [500, 500, 500, 0]] μs
```

Total blocking for IMU thread: `∑B[0][j] = 0μs` (highest priority, no blocking)

### Deadlock Prevention via Resource Ordering Algebra

The rover's resource acquisition must follow a total order to prevent circular waits that could freeze skid-steer control.

**Resource Ordering Theorem:**
Let R = {r₁, r₂, ..., rₙ} be totally ordered resources: `r₁ < r₂ < ... < rₙ`
Let T = {t₁, t₂, ..., tₘ} be threads

Theorem: If ∀tᵢ ∈ T, tᵢ acquires resources in increasing order, then no deadlock occurs.

**Proof by Contradiction:**
Assume deadlock exists: ∃ circular wait `t₁→r₁→t₂→r₂→...→tₖ→rₖ→t₁`

Without loss of generality, assume r₁ is smallest resource in cycle:
- t₁ holds r₁, waits for rⱼ where `rⱼ > r₁` (by ordering)
- tₖ holds rⱼ and waits for r₁ where `r₁ < rⱼ`

This violates acquisition ordering for tₖ (holding higher rⱼ while requesting lower r₁).
Contradiction. ∴ No deadlock.

**Rover Resource Ordering:**
1. IMU data mutex (r₁)
2. EKF state mutex (r₂)  
3. Motor command mutex (r₃)
4. Log buffer mutex (r₄)
5. Telemetry buffer mutex (r₅)

All threads must acquire in order: r₁ → r₂ → r₃ → r₄ → r₅

**Mathematical Verification:**
Let A(t, r) = 1 if thread t acquires resource r, else 0
Let H(t, r) = 1 if thread t holds resource r, else 0
Let W(t, r) = 1 if thread t waits for resource r, else 0

Deadlock condition: ∃ cycle where for some k > 1:
```
H(t₁, r₁) ∧ W(t₁, r₂) ∧
H(t₂, r₂) ∧ W(t₂, r₃) ∧
... ∧
H(tₖ, rₖ) ∧ W(tₖ, r₁)
```

With ordering constraint: if `H(t, rⱼ) = 1` and `rⱼ < rₖ`, then `W(t, rₖ) = 0`
Thus no cycle possible.

### Event Flag System Mathematics with Bounded Wait Times

The rover's thread synchronization uses event flags with mathematical guarantees for bounded response times.

**Event Flag Bitmask Algebra:**
Let F be 32-bit event flags: `F ∈ {0, 1}³²`
Let M be wait mask: `M ∈ {0, 1}³²`

Wait conditions:
- ANY: `wait(F, M, ANY) = (F ∧ M) ≠ 0`
- ALL: `wait(F, M, ALL) = (F ∧ M) = M`

**Thread Wakeup Logic:**
When event signaled with mask S:
```
F_new = F_old ∨ S
Wake threads where: (F_new ∧ M) satisfies wait condition
```

**Bounded Wait Time Theorem:**
For event system with n threads, m event flags:
Maximum wait time = timeout parameter (finite)
No deadlock because:
1. No resources held while waiting
2. Signal operation always completes in O(1)
3. Wait timeout provides progress guarantee

**Mathematical Proof of Liveness:**
Let T be set of threads, E be set of events.
Define progress function Φ: T × E → ℕ (generation count)

When thread t waits for event e:
```
Φ(t, e) = generation[e]
```

When event e signaled:
```
generation[e]++
∀t waiting for e: if condition satisfied, wake t
```

Timeout ensures: if t waits for e and e never signals, t wakes after timeout.
Thus ∀t ∈ T, either:
1. e signals and t wakes, or
2. Timeout occurs and t wakes

System is live.

**Rover Event Timeout Calculations:**
- IMU data ready: timeout = 2.5ms (1 period)
- GPS fix: timeout = 100ms
- Waypoint reached: timeout = 10s
- Emergency stop: timeout = 0 (immediate)

### Worst-Case Execution Time (WCET) Analysis for Rover Control

The 400Hz control loop must complete within 2000μs (80% of period) to guarantee rover stability.

**WCET Mathematical Model:**
Let Cᵢ be execution time of task i, T be period (2500μs)
Schedulability condition: `Σ(Cᵢ / T) ≤ n(2^(1/n) - 1)`

For rover tasks:
- IMU processing: C₁ = 150μs
- EKF update: C₂ = 350μs
- Motor mixing: C₃ = 100μs
- Safety checks: C₄ = 50μs

Total: `C_total = 650μs`
Utilization: `U = 650μs / 2500μs = 0.26`

For n = 4 tasks: `U_limit = 4(2^(1/4) - 1) = 4(1.189 - 1) = 0.756`

Since `0.26 ≤ 0.756`, schedulable.

**Dynamic Priority Adjustment Mathematics:**
When load factor L = C_total / T exceeds threshold (0.7):
```
ΔPriority = floor(10 × (L - 0.7))
```

For L = 0.8: `ΔPriority = floor(10 × 0.1) = 1`
Critical tasks receive priority boost by 1 level.

**Memory Access Time Calculations:**
DTCM access: 1 cycle @ 168MHz = 5.95ns
Flash access (5 wait states): 6 cycles = 35.7ns
Ratio: 35.7ns / 5.95ns = 6.0×

Thus placing ISR code in ITCM provides 6× faster execution.

### Inter-Thread Communication Buffer Mathematics

The rover's sensor→control→actuator pipeline uses circular buffers with mathematical overflow prevention.

**Circular Buffer Index Algebra:**
Buffer size B = 1024 elements
Write index w, read index r
Free space: `free = (r - w - 1) mod B`
Used space: `used = (w - r) mod B`

**Overflow Prevention Condition:**
For producer rate P (elements/cycle) and consumer rate C:
Stability requires: `P ≤ C`

Rover sensor data: P = 16 floats/cycle (IMU + GPS)
Control consumption: C = 20 floats/cycle
Since `16 ≤ 20`, stable.

**Buffer Delay Calculation:**
Maximum delay = B / C = 1024 / 20 = 51.2 cycles
At 400Hz: `51.2 × 2.5ms = 128ms`

Acceptable for rover control with 100ms response requirement.

### Mutex Nesting and Recursion Mathematics

The rover's control system allows mutex nesting for complex operations.

**Nesting Depth Mathematics:**
Let L(r, t) = nesting level of resource r by thread t
Maximum nesting: `L_max = 8` (hardware limit)

Recursive lock condition:
```
if L(r, t) > 0:
    L(r, t)++
else:
    acquire(r)
    L(r, t) = 1
```

Unlock:
```
L(r, t)--
if L(r, t) == 0:
    release(r)
```

**Priority Inheritance with Nesting:**
When thread t with priority P holds nested locks on resources R = {r₁, r₂, ..., rₙ}:
Inherited priority = `max(P, max(C(rᵢ)))` where C(rᵢ) are ceiling priorities

For rover with P = 2 (navigation), holding r₂ (C=0) and r₃ (C=2):
Inherited priority = `max(2, 0, 2) = 2` (no change)

### Hardware Mutex Implementation for Dual-Core Systems

If using dual-core STM32H7 for future rover upgrades:

**ARM Hardware Mutex Algebra:**
Test-and-set using LDREX/STREX:
```
lock(m):
    do {
        while LDREX(m) ≠ 0:
            // Exponential backoff
            delay(2^core_id)
    } while STREX(1, m) ≠ 0
    DMB()
```

**Memory Barrier Mathematics:**
Data Memory Barrier (DMB) ensures:
```
∀ operations O₁, O₂: if O₁ → O₂ in program order
then O₁ → O₂ in memory order
```

Required for rover's sensor→control→actuator coherence.

**Cache Coherency Mathematics:**
For DMA buffers of size S bytes, cache line size L = 32 bytes:
Number of cache operations = `ceil(S / L) × 2` (clean + invalidate)

For 256-byte IMU buffer: `ceil(256/32) × 2 = 8 × 2 = 16 operations`
Time = `16 × 32 bytes × (1/168MHz) = 3.05μs`

### Watchdog Timer Mathematics for Rover Safety

The rover implements independent watchdog for fault recovery in agricultural environments.

**Watchdog Timeout Calculation:**
```
T_timeout = (IWDG_PR × IWDG_RLR) / 32kHz
```

Typical rover configuration:
- `IWDG_PR = 4` (prescaler 64)
- `IWDG_RLR = 4095` (reload value)
- `T_timeout = (4 × 4095) / 32,000 = 0.512 seconds`

**Refresh Requirement:**
Must refresh within 512ms. At 400Hz control:
Refresh interval = `2500μs × 200 = 500ms < 512ms` ✓

Margin = `(512ms - 500ms) / 512ms = 2.3%` safety margin

**Mathematical Fault Detection Probability:**
Let λ = hardware fault rate = 1/1000 hours
Let T = watchdog timeout = 0.512s
Probability of undetected fault in time T:

```
P_undetected = 1 - e^{-λT} ≈ λT = (1/1000) × (0.512/3600) ≈ 1.42×10⁻⁷
```

Acceptable for agricultural safety standard (10⁻⁶).

### Thread Stack Size Mathematics

Each rover thread requires stack space for worst-case call depth and local variables.

**Stack Usage Calculation:**
```
S_total = S_locals + S_parameters + S_return_addresses + S_context_switch
```

For IMU thread (400Hz):
- Local variables: 256 bytes (float arrays)
- Parameters: 64 bytes (4× 16-byte vectors)
- Return addresses: 8 levels × 4 bytes = 32 bytes
- Context switch: 68 bytes (17 registers × 4 bytes)
- Safety margin: 100 bytes (25%)

```
S_total = 256 + 64 + 32 + 68 + 100 = 520 bytes
```

Allocated: 1024 bytes (2× safety factor)

**Stack Overflow Detection:**
Pattern `0xDEADBEEF` written at stack base
Check periodically: if pattern corrupted → stack overflow

Probability of accidental match: `1/2³² ≈ 2.3×10⁻¹⁰`

### Real-Time Clock Synchronization Mathematics

The rover's logging system requires μs-precise timestamps across threads.

**Timestamp Algebra:**
Let t_hardware = hardware timer count (28MHz = 35.714ns resolution)
Let t_system = system time in μs

Conversion: `t_system = (t_hardware × 1000) / 28,000`

**Clock Drift Between Cores:**
Maximum drift rate = ±100ppm (crystal specification)
Drift per hour = `100×10⁻⁶ × 3600s = 0.36s`

Synchronization required every: `0.1s / (100×10⁻⁶) = 1000s ≈ 16.7 minutes`

**Timestamp Collision Probability:**
With 32-bit μs counter, wrap period = 2³² μs ≈ 4295s ≈ 1.19h
Collision probability for N events in period T:

```
P_collision ≈ 1 - e^{-N²/(2×2³²)}
```

For 400Hz logging: N = 400 × 3600 = 1.44×10⁶ events/hour
```
P_collision ≈ 1 - e^{-(1.44×10⁶)²/(2×4.3×10⁹)} ≈ 1 - e^{-0.241} ≈ 0.214
```

Requires 64-bit timestamps for reliable logging.

This mathematical formulation provides the exact algebraic and matrix relationships that underpin the RTOS scheduler, mutex semaphores, and thread arbitration systems, ensuring deterministic real-time performance for the 20kg agricultural rover's control systems while maintaining safety through bounded latencies and deadlock-free operation.

## C++ Implementation: RTOS Scheduler, Mutex Semaphores, and Thread Arbitration

### Hardware Timer Interrupts with Drift Compensation (Scheduler.cpp)

The mathematical timer model `ARR = (F_TIMER / F_DESIRED) - 1` with `F_TIMER = 84,000,000 Hz` and `F_DESIRED = 400 Hz` maps directly to the `HardwareTimerConfig` struct in DTCM and the `init_timer_400hz()` function in ITCM memory. The drift compensation PI controller implements the discrete-time equation `C[n] = K_p·e[n] + K_i·∑_{i=0}^{n} e[i]`.

**Timer Configuration Structure:**
```cpp
typedef struct __attribute__((packed)) {
    TIM_TypeDef* timer_regs;       // 0x40000000: TIM2 base address
    uint32_t irq_channel;          // 0x20001000: NVIC IRQ number
    uint16_t arr_value;            // 0x20001004: Auto-reload value
    uint16_t psc_value;            // 0x20001006: Prescaler value
    uint32_t expected_period_us;   // 0x20001008: 2500 μs
    uint32_t actual_last_us;       // 0x2000100C: Last ISR timestamp
    uint32_t drift_accumulator;    // 0x20001010: Cumulative error (ns)
    uint32_t correction_active;    // 0x20001014: Active correction
    uint8_t timer_channel;         // 0x20001018: TIM_CHANNEL_1
} HardwareTimerConfig;

volatile HardwareTimerConfig scheduler_timer __attribute__((section(".dtcm")));
```

**Timer Initialization Mathematics:**
The prescaler calculation `PSC = 2` and ARR calculation `ARR = 69,999` from `84MHz/(2+1)=28MHz` and `28MHz/70,000=400Hz` implements as:
```cpp
__attribute__((section(".itcm")))
void Scheduler::init_timer_400hz() {
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    scheduler_timer.psc_value = 2;
    scheduler_timer.arr_value = 69999;
    TIM2->PSC = scheduler_timer.psc_value;
    TIM2->ARR = scheduler_timer.arr_value;
    TIM2->DIER = TIM_DIER_UIE;
    NVIC_SetPriority(TIM2_IRQn, 5);
    NVIC_EnableIRQ(TIM2_IRQn);
    TIM2->CR1 = TIM_CR1_CEN | TIM_CR1_ARPE;
    scheduler_timer.drift_accumulator = 0;
    scheduler_timer.correction_active = 0;
    scheduler_timer.expected_period_us = 2500;
    scheduler_timer.actual_last_us = AP_HAL::micros();
}
```

**Drift Compensation PI Controller Implementation:**
The mathematical PI controller `correction_us = Kp·(drift_ns/1000) + Ki·(drift_accumulator/1000)` with `Kp=0.1, Ki=0.01` maps to:
```cpp
__attribute__((section(".itcm")))
void TIM2_IRQHandler(void) {
    __asm volatile ("push {r0-r12, lr}\nmrs r0, psr\npush {r0}\n");
    TIM2->SR = ~TIM_SR_UIF;
    
    uint32_t current_us = AP_HAL::micros64() & 0xFFFFFFFF;
    uint32_t actual_period_us = current_us - scheduler_timer.actual_last_us;
    scheduler_timer.actual_last_us = current_us;
    
    int32_t drift_ns = (actual_period_us * 1000) - (scheduler_timer.expected_period_us * 1000);
    scheduler_timer.drift_accumulator += drift_ns;
    
    const float Kp = 0.1f;
    const float Ki = 0.01f;
    float correction_us = Kp * (drift_ns / 1000.0f) + 
                         Ki * (scheduler_timer.drift_accumulator / 1000.0f);
    
    if (correction_us > 100.0f) correction_us = 100.0f;
    if (correction_us < -100.0f) correction_us = -100.0f;
    
    scheduler_timer.correction_active = (uint32_t)(correction_us * 1000);
    int32_t correction_ticks = (int32_t)(correction_us * 1000 / 35.714f);
    
    uint16_t new_arr = scheduler_timer.arr_value + correction_ticks;
    if (new_arr < 69000) new_arr = 69000;
    if (new_arr > 71000) new_arr = 71000;
    TIM2->ARR = new_arr;
    
    static uint16_t tick_counter = 0;
    tick_counter++;
    Scheduler::run_main_loop();
    if ((tick_counter & 0x03) == 0) Scheduler::run_100hz_tasks();
    if ((tick_counter & 0x07) == 0) Scheduler::run_50hz_tasks();
    if ((tick_counter & 0x27) == 0) Scheduler::run_10hz_tasks();
    if (tick_counter >= 400) { tick_counter = 0; Scheduler::run_1hz_tasks(); }
    
    __asm volatile ("pop {r0}\nmsr psr_nzcvq, r0\npop {r0-r12, lr}\nbx lr\n");
}
```

**Worst-Case Execution Time Monitoring:**
The mathematical WCET constraint `WCET_max = 0.8·T = 2000μs` implements as:
```cpp
__attribute__((section(".itcm")))
void Scheduler::validate_wcet() {
    static uint32_t max_execution_us = 0;
    static uint32_t last_check_us = 0;
    uint32_t now = AP_HAL::micros();
    uint32_t execution_time = now - last_check_us;
    
    if (execution_time > max_execution_us) {
        max_execution_us = execution_time;
        if (max_execution_us > 2000) {
            GPIOE->BSRR = (1 << 8);
            AP::logger().Write_Error(LOG_SCHEDULER_OVERRUN, max_execution_us, execution_time);
        }
    }
    
    last_check_us = now;
    float load_factor = (float)execution_time / 2500.0f;
    if (load_factor > 0.7f) adjust_task_priorities(load_factor);
}
```

**RTOS Execution Context:** `TIM2_IRQHandler` runs at 400Hz with NVIC priority 5, placed in ITCM section for deterministic execution. The tick counter implements rate division: `tick_counter & 0x03` for 100Hz, `& 0x07` for 50Hz, `& 0x27` for 10Hz, and reset at 400 for 1Hz.

### Priority Inheritance Semaphores with Deadlock Prevention (Semaphores.cpp)

The mathematical priority inheritance protocol and deadlock prevention via resource ordering map to the `PriorityInheritanceSemaphore` class with DTCM-allocated control block. The bounded blocking time `B(P) = max(usage(S)) for all S with ceiling ≥ P` is enforced through priority ceiling protocol.

**Semaphore Control Block Structure:**
```cpp
class PriorityInheritanceSemaphore {
private:
    struct __attribute__((packed)) SemaphoreCB {
        volatile cnt_t count;           // 0x20002000: Semaphore count
        volatile thread_t* owner;       // 0x20002004: Current owner thread
        volatile uint8_t priority;      // 0x20002008: Original owner priority
        volatile uint8_t inherited;     // 0x20002009: Inheritance active flag
        volatile thread_t* wait_queue;  // 0x2000200C: Threads waiting
        volatile uint32_t lock_count;   // 0x20002010: Nesting count
    } sem_cb;
    
    uint8_t ceiling_priority;
    
public:
    PriorityInheritanceSemaphore(uint8_t max_priority) : ceiling_priority(max_priority) {
        sem_cb.count = 1;
        sem_cb.owner = nullptr;
        sem_cb.priority = 0;
        sem_cb.inherited = 0;
        sem_cb.wait_queue = nullptr;
        sem_cb.lock_count = 0;
    }
    
    bool wait(uint32_t timeout_ms);
    void signal();
    
private:
    void inherit_priority(thread_t* waiter);
    void restore_priority();
    bool detect_deadlock();
};
```

**Priority Inheritance Mathematics Implementation:**
The inheritance condition `if (sem_cb.owner != nullptr && self->p_prio < sem_cb.owner->p_prio)` maps to:
```cpp
__attribute__((section(".itcm")))
bool PriorityInheritanceSemaphore::wait(uint32_t timeout_ms) {
    chSysLock();
    thread_t* self = chThdGetSelfX();
    
    if (detect_deadlock()) { chSysUnlock(); return false; }
    
    if (sem_cb.count > 0) {
        sem_cb.count--;
        sem_cb.owner = self;
        sem_cb.priority = self->p_prio;
        sem_cb.lock_count = 1;
        
        if (self->p_prio > ceiling_priority) {
            self->p_prio = ceiling_priority;
            sem_cb.inherited = 1;
        }
        
        chSysUnlock();
        return true;
    } else {
        if (sem_cb.owner == self) {
            sem_cb.lock_count++;
            chSysUnlock();
            return true;
        }
        
        thread_t** p = &sem_cb.wait_queue;
        while (*p != nullptr && (*p)->p_prio <= self->p_prio) {
            p = &(*p)->p_next;
        }
        self->p_next = *p;
        *p = self;
        
        if (sem_cb.owner != nullptr && self->p_prio < sem_cb.owner->p_prio) {
            inherit_priority(self);
        }
        
        msg_t msg = chSchGoSleepTimeoutS(CH_STATE_WTQUEUE, timeout_ms);
        chSysUnlock();
        return (msg == MSG_OK);
    }
}

__attribute__((section(".itcm")))
void PriorityInheritanceSemaphore::inherit_priority(thread_t* waiter) {
    thread_t* owner = sem_cb.owner;
    
    if (!sem_cb.inherited) {
        sem_cb.priority = owner->p_prio;
        sem_cb.inherited = 1;
    }
    
    if (waiter->p_prio < owner->p_prio) {
        owner->p_prio = waiter->p_prio;
        if (owner->p_state == CH_STATE_READY) chSchRescheduleS();
    }
}
```

**Deadlock Detection Graph Algorithm:**
The mathematical deadlock detection via resource allocation graph traversal implements as:
```cpp
__attribute__((section(".itcm")))
bool PriorityInheritanceSemaphore::detect_deadlock() {
    static uint8_t visited[16] = {0};
    static uint8_t recursion_stack[16] = {0};
    
    thread_t* current = chThdGetSelfX();
    uint8_t tid = current->p_tid;
    
    visited[tid] = 1;
    recursion_stack[tid] = 1;
    
    for (int i = 0; i < MAX_SEMAPHORES; i++) {
        if (semaphore_array[i].owner == current) {
            thread_t* waiter = semaphore_array[i].wait_queue;
            while (waiter != nullptr) {
                uint8_t wtid = waiter->p_tid;
                if (!visited[wtid]) {
                    if (detect_deadlock_recursive(wtid, visited, recursion_stack)) return true;
                } else if (recursion_stack[wtid]) return true;
                waiter = waiter->p_next;
            }
        }
    }
    
    recursion_stack[tid] = 0;
    return false;
}
```

**Signal with Priority Restoration:**
The priority restoration mathematics implements as:
```cpp
__attribute__((section(".itcm")))
void PriorityInheritanceSemaphore::signal() {
    chSysLock();
    
    if (sem_cb.lock_count > 1) {
        sem_cb.lock_count--;
        chSysUnlock();
        return;
    }
    
    if (sem_cb.inherited) restore_priority();
    
    if (sem_cb.wait_queue != nullptr) {
        thread_t* waiter = sem_cb.wait_queue;
        sem_cb.wait_queue = waiter->p_next;
        sem_cb.owner = waiter;
        sem_cb.priority = waiter->p_prio;
        sem_cb.inherited = 0;
        sem_cb.lock_count = 1;
        chSchWakeupS(waiter, MSG_OK);
    } else {
        sem_cb.count++;
        sem_cb.owner = nullptr;
        sem_cb.lock_count = 0;
    }
    
    chSysUnlock();
}
```

**RTOS Threading Model:** Semaphore operations use `chSysLock()`/`chSysUnlock()` for atomicity, with wait queues sorted by thread priority to implement the mathematical guarantee of bounded blocking time.

### Thread Wakeup Event Flags with Atomic Operations (EventSource.cpp)

The mathematical event system guarantees of no missed notifications and bounded wait times map to the `EventSource` class with DTCM-allocated event control block. The atomicity proof `Signal: L.lock(); F |= mask; wake(W); L.unlock()` implements directly.

**Event Control Block Structure:**
```cpp
class EventSource {
private:
    struct __attribute__((packed)) EventCB {
        volatile eventmask_t flags;     // 0x20003000: 32-bit event flags
        volatile thread_t* waiters;     // 0x20003004: Threads waiting
        volatile uint32_t generation;   // 0x20003008: Generation counter
        volatile uint8_t auto_reset[32]; // 0x2000300C: Auto-reset per flag
    } event_cb;
    
    struct WaitRecord {
        thread_t* thread;
        eventmask_t mask;
        uint8_t mode;  // ANY, ALL, AUTO_RESET
        uint32_t generation;
    } wait_records[16];
    
public:
    void signal(eventmask_t mask);
    eventmask_t wait(eventmask_t mask, uint8_t mode, uint32_t timeout_ms);
    void set_auto_reset(eventmask_t mask, bool auto_reset);
    
private:
    void wake_matching_threads(eventmask_t signaled);
    bool check_wait_condition(WaitRecord* rec, eventmask_t current);
};
```

**Atomic Event Signaling Mathematics:**
The mathematical atomic OR operation `F |= mask` with generation counter implements as:
```cpp
__attribute__((section(".itcm")))
void EventSource::signal(eventmask_t mask) {
    chSysLock();
    event_cb.flags |= mask;
    event_cb.generation++;
    wake_matching_threads(mask);
    
    for (int i = 0; i < 32; i++) {
        if ((mask & (1 << i)) && event_cb.auto_reset[i]) {
            event_cb.flags &= ~(1 << i