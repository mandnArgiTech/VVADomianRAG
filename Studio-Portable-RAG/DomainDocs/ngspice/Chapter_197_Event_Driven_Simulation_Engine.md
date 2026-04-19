# Event-Driven Engine: Time-Wheels and Logic Resolution

_Generated 2026-04-13 09:46 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtqueue.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtdeque.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtiter.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtnext_time.c`

# Chapter: Event-Driven Engine: Time-Wheels and Logic Resolution

## Introduction

The event-driven engine in Ngspice is the core subsystem responsible for managing discrete-time events, digital logic resolution, and time-ordered execution within mixed-signal simulations. The files `evtinit.c`, `evtsetup.c`, `evtqueue.c`, `evtdeque.c`, `evtiter.c`, and `evtnext_time.c` collectively implement a sophisticated time-wheel scheduler and logic resolution system that bridges continuous-time analog simulation with discrete-event digital simulation. This engine implements the mathematical formulations for event queue management, breakpoint handling, state integration, and convergence control, ensuring efficient and numerically stable simulation of circuits containing both analog and digital components. The system's architecture is built around a time-ordered event queue, adaptive time-step control, and a 12-state logic resolution system that handles signal strengths and conflicts according to formal digital simulation semantics.

## Mathematical Formulation

### 1. Event-Driven Simulation Algebra

The event-driven engine in Ngspice bridges continuous-time analog simulation with discrete-event digital logic through a formal mathematical framework that maintains consistency with Modified Nodal Analysis (MNA).

#### 1.1 Digital Logic State System

Digital signals are represented using a 12-state logic system that combines logic values with drive strengths:

```
S = {0, 1, X, Z} × {STRONG, RESISTIVE, HI_Z}
```

where:
- **Logic values**: `0` (low), `1` (high), `X` (unknown), `Z` (high impedance)
- **Drive strengths**: `STRONG` (gate output), `RESISTIVE` (pull-up/down), `HI_Z` (floating)

**Conflict Resolution Function**: When multiple drivers connect to a node:
```
state(node) = dominant({strength(signal₁), strength(signal₂), ...})
```

The dominance hierarchy is: `STRONG > RESISTIVE > HI_Z`. For equal strengths:
- Same logic value: value is preserved
- Different logic values: result is `X` (unknown)

**Mathematical Representation**: Each digital state can be encoded as:
```
s = (v, d) where v ∈ {0,1,X,Z}, d ∈ {S,R,H}
```
with numerical encoding for efficient computation.

#### 1.2 Time-Wheel Scheduling Algorithm

The time-wheel implements efficient event scheduling with O(1) complexity for insertion and retrieval. For simulation time horizon `T_max` and resolution `Δt_min`:

**Time-Wheel Structure**:
```
W = (W₀, W₁, ..., W_{k-1}) where k = ⌈T_max/Δt_min⌉
```

Each wheel slot `Wᵢ` contains events scheduled for time:
```
t = t_current + i·Δt_min
```

**Event Insertion**: For event at time `t_event`:
```
slot_index = ⌊(t_event - t_current)/Δt_min⌋ mod k
```

**Advancement**: When simulation time advances by `Δt`:
```
slots_to_process = ⌊Δt/Δt_min⌋
for i = 0 to slots_to_process-1:
    process_events(W[(current_slot + i) mod k])
current_slot = (current_slot + slots_to_process) mod k
```

#### 1.3 Propagation Delay Modeling

Digital gates exhibit finite propagation delays with voltage and temperature dependence:

**Basic Propagation Delay**:
```
t_pd = t_pd_base + k₁·(V_DD - V_th) + k₂·exp(-T/T₀)
```

where:
- `t_pd_base`: Nominal propagation delay
- `V_DD`: Supply voltage
- `V_th`: Threshold voltage
- `T`: Temperature in Kelvin
- `T₀`, `k₁`, `k₂`: Technology parameters

**Input Slew Rate Effect**:
```
t_pd_effective = t_pd·(1 + α·(t_rise/t_rise_nom - 1))
```

where `t_rise` is the input signal rise time and `α` is the sensitivity factor (typically 0.2-0.5).

#### 1.4 Metastability Resolution

When digital inputs change near the clock edge, metastability occurs. The resolution probability is modeled as:

**Setup/Hold Window**:
```
P(metastable) = 
    ⎧ 0 if |t_input - t_clock| > max(t_setup, t_hold)
    ⎨ 1 if t_setup < t_clock - t_input < t_hold
    ⎩ exp(-|t_input - t_clock|/τ) otherwise
```

where `τ` is the metastability time constant (technology dependent).

**Deterministic Resolution**: For simulation reproducibility, metastable states resolve based on a deterministic hash:
```
final_state = hash(circuit_state) mod 2
```

#### 1.5 Mixed-Signal Interface Jacobian

For components connecting analog and digital domains, the Jacobian has block structure:

```
J_mixed = [ J_aa   J_ad ]
          [ J_da   J_dd ]
```

**Analog-Digital Coupling**: For ADC models with threshold `V_th`:
```
J_ad[i,j] = ∂I_analog_i/∂V_digital_j ≈ 
    ⎧ α·sech²(α·(V_analog - V_th))·(∂V_th/∂V_digital) near threshold
    ⎨ 0 otherwise
```

where `α ≫ 1` controls the steepness of the smoothed threshold function.

**Digital-Analog Coupling**: For DAC models:
```
J_da[i,j] = ∂V_digital_i/∂I_analog_j = R_out
```
where `R_out` is the output impedance of the DAC.

### 2. Event Queue Dynamics and Time Management

#### 2.1 Event Scheduling Formalism

The event queue `Q` maintains events in temporal order:
```
Q = {(t_i, e_i) | t_i < t_{i+1} for i = 0,...,N-1}
```

Each event `e_i` is a tuple:
```
e_i = (t_i, τ_i, x_i, v_i, Δ_i)
```
where:
- `t_i ∈ ℝ⁺`: Event timestamp
- `τ_i ∈ {ANALOG_UPDATE, DIGITAL_TRANSITION, STATE_CHANGE}`: Event type
- `x_i`: Target variable (node voltage, digital state, or internal state)
- `v_i`: New value (ℝ for analog, {0,1} for digital)
- `Δ_i`: Propagation delay for this event

#### 2.2 Zeno Behavior Prevention Theorem

To prevent infinite events in finite time (Zeno behavior), enforce minimum event spacing:

**Minimum Time Step**:
```
Δt_min = max(ε_time, 10·t_step/tol, t_rise/100, t_pd_min/10)
```

where:
- `ε_time = 1e-15`: Machine precision limit
- `t_step`: Current analog integration time step
- `tol`: User-specified tolerance
- `t_rise`: Minimum rise/fall time of digital signals
- `t_pd_min`: Minimum propagation delay

**Event Merging Algorithm**: If events `e_i` and `e_j` satisfy `|t_i - t_j| < Δt_min`:
```
t_merged = (t_i + t_j)/2
v_merged = 
    ⎧ v_j if |t_j - t_current| < |t_i - t_current|
    ⎨ v_i otherwise
```

#### 2.3 Event-Driven Integration Scheme

For time intervals between events `[t_k, t_{k+1}]`, solve:
```
F(x, ẋ, t) = 0 for t ∈ [t_k, t_{k+1}]
```

with initial condition update at events:
```
x(t_k⁺) = lim_{ε→0⁺} x(t_k + ε) = g(x(t_k⁻), e_k)
```

where `g` is the event update function that may instantaneously change states.

### 3. Logic Evaluation and Resolution

#### 3.1 Boolean Algebra with Unknown States

Extend Boolean algebra to handle `X` and `Z` states:

**Truth Tables for AND Operation**:
```
AND | 0 1 X Z
----+---------
  0 | 0 0 0 0
  1 | 0 1 X X
  X | 0 X X X
  Z | 0 X X X
```

**Strength-Based Resolution**: For wire with multiple drivers:
```
result = resolve({(v₁, d₁), (v₂, d₂), ...})
```

where `resolve` applies dominance rules:
1. If any `STRONG` driver: use its value (if multiple STRONG with different values → `X`)
2. Else if any `RESISTIVE` driver: use its value (if multiple → `X`)
3. Else: `Z` (high impedance)

#### 3.2 Sequential Logic Timing Constraints

**Setup Time Violation**: Clock arrives too soon after data change:
```
if (t_clock - t_data_change < t_setup) then violation
```

**Hold Time Violation**: Data changes too soon after clock:
```
if (t_data_change - t_clock < t_hold) then violation
```

**Recovery Time**: For asynchronous signals:
```
if (t_async_change - t_clock < t_recovery) then violation
```

#### 3.3 Glitch Detection and Filtering

Short pulses narrower than minimum width are filtered:

**Pulse Width Check**:
```
if (t_high < t_min_high) then reject_high_pulse
if (t_low < t_min_low) then reject_low_pulse
```

**Glitch Filtering Function**:
```
filter(v(t)) = 
    ⎧ v(t) if pulse_width ≥ t_min
    ⎨ previous_value otherwise
```

## Convergence Analysis

### 1. Newton-Raphson Stability for Event-Driven Systems

#### 1.1 Jacobian Conditioning with Discontinuities

Event-driven systems introduce discontinuities that affect Jacobian conditioning:

**Condition Number Bound**:
```
cond(J_event) ≤ cond(J_continuous) / (1 - ||ΔJ||/||J_continuous||)
```

where `ΔJ` is the Jacobian change due to event.

**Regularization at Events**: When crossing threshold at `t_event`:
```
J_reg = J + λ·I where λ = max(ε_singular, ||x(t_event⁺) - x(t_event⁻)||/Δt)
```

#### 1.2 Convergence Criteria for Mixed Signals

**Analog Convergence**:
```
||Δx_analog||₂ < ε_abs_analog + ε_rel_analog·||x_analog||₂
```
with `ε_abs_analog = 1e-12`, `ε_rel_analog = 1e-6`.

**Digital Convergence**: Digital signals must settle to valid logic levels:
```
||Δx_digital||_∞ < 0.5 AND x_digital ∈ {0, 1} ± ε_digital
```
where `ε_digital = 0.1` ensures noise margins.

**Event Timing Convergence**: Event times must be consistent:
```
|t_event_calculated - t_event_scheduled| < ε_time
```
with `ε_time = 1e-12`.

#### 1.3 Time Step Control with Events

**Event-Aware Step Control**:
```
Δt_next = min(Δt_analog, t_next_event - t_current - ε_time, Δt_max)
```

where `Δt_analog` is determined by LTE control:
```
Δt_analog = 0.9·Δt_current·(tol/LTE)^(1/(order+1))
```

**Step Refinement Near Events**: When `t_next_event - t_current < 2·Δt_current`:
```
Δt_current = (t_next_event - t_current)/2
recompute = TRUE
```

### 2. Numerical Stability of Logic Transitions

#### 2.1 Threshold Crossing Detection

For ADC models with threshold `V_th`, detect crossing using:

**Crossing Condition**:
```
sign(V(t) - V_th) ≠ sign(V(t-Δt) - V_th)
```

**False Triggering Prevention**: To avoid noise-induced false triggers:
```
|V(t) - V_th| > V_noise_margin
```
where `V_noise_margin = 6·σ_noise` and `σ_noise ≈ ε_machine·||V||`.

**Probability of False Transition**:
```
P_false ≈ erfc(V_noise_margin/(√2·σ_noise)) < 10⁻⁶
```

#### 2.2 Metastability Resolution Stability

Metastable states must resolve within bounded time:

**Resolution Time Bound**:
```
t_resolution < τ·ln(1/ε_meta)
```
where `ε_meta` is the tolerance for metastability (typically `1e-9`).

**Numerical Implementation**: Use deterministic resolution based on state hash to ensure reproducibility:
```
if (metastable) {
    uint32_t hash = hash_function(circuit_state);
    resolved_state = (hash & 1) ? 1 : 0;
}
```

### 3. Event Queue Stability Analysis

#### 3.1 Queue Size Management

**Maximum Queue Size Theorem**: For stable simulation, event queue size should satisfy:
```
N_queue ≥ N_avg_events + 3·σ_events
```

where:
- `N_avg_events`: Average concurrent events
- `σ_events`: Standard deviation of event count

**Empirical Sizing Formula**:
```
N_queue = max(1000, 2·N_gates, 10·N_flipflops)
```

#### 3.2 Event Processing Consistency

**Causality Preservation**: All events must satisfy:
```
t_cause(eᵢ) < t_effect(eᵢ)
```

**Circular Causality Detection**: For event chain `e₁ → e₂ → ... → eₙ`:
```
if (t(e₁) ≥ t(eₙ)) then circular_causality_detected
```

**Resolution**: Break cycles by:
1. Identifying strongly connected components in event dependency graph
2. Sorting events within SCC by priority
3. Processing events in priority order at same timestamp

#### 3.3 Memory Management for Event Queues

**Event Pool Sizing**: Pre-allocated event pool size:
```
N_pool = N_queue + N_margin
```
where `N_margin = 0.2·N_queue` provides buffer.

**Allocation/Deallocation Complexity**:
- Allocation: O(1) from free list
- Deallocation: O(1) to free list
- Memory fragmentation: eliminated by pool

### 4. Time-Wheel Efficiency Analysis

#### 4.1 Complexity Analysis

**Time-Wheel Operations**:
- Event insertion: O(1)
- Event retrieval: O(1) per slot
- Advance by Δt: O(⌈Δt/Δt_min⌉)

**Comparison with Priority Queue**:
- Priority queue: O(log N) insertion/retrieval
- Time-wheel: O(1) insertion/retrieval, O(k) memory where k = ⌈T_max/Δt_min⌉

**Optimal Slot Size**: Balance between memory and precision:
```
Δt_min = min(t_pd_min/10, t_rise/100, ε_time·10³)
```

#### 4.2 Memory Usage Optimization

**Slot Compression**: For sparse event distribution, use hierarchical time-wheel:
- Level 0: Δt₀ = 1 ps, 1000 slots (covers 1 ns)
- Level 1: Δt₁ = 1 ns, 1000 slots (covers 1 μs)
- Level 2: Δt₂ = 1 μs, 1000 slots (covers 1 ms)

**Event Migration**: When advancing past slot boundary, migrate events from higher levels to lower levels.

### 5. Logic Simulation Accuracy

#### 5.1 Timing Accuracy

**Propagation Delay Error**: Due to discrete time steps:
```
error_t_pd = |t_pd_discrete - t_pd_continuous| ≤ Δt_min/2
```

**Setup/Hold Time Checking**: With time quantization:
```
t_setup_effective = t_setup + Δt_min/2
t_hold_effective = t_hold + Δt_min/2
```

#### 5.2 State Accuracy

**Logic State Corruption**: Probability of bit flip due to numerical error:
```
P(corruption) ≈ ε_machine·N_gates·f_clock·T_sim
```

For typical values (ε_machine = 2e-16, N_gates = 1e6, f_clock = 1 GHz, T_sim = 1 ms):
```
P(corruption) ≈ 2e-16·1e6·1e9·1e-3 = 2e-4
```

**Mitigation**: Use deterministic hashing for metastable resolution and add parity checks for critical signals.

### 6. Mixed-Signal Convergence Acceleration

#### 6.1 Decoupled Simulation

For weakly coupled analog-digital systems, use waveform relaxation:

**Algorithm**:
1. **Analog subproblem**: Solve with digital inputs held constant
2. **Digital subproblem**: Solve with analog outputs as piecewise constant
3. **Iterate** until convergence:
```
||x_analog^{k+1} - x_analog^k|| < ε_wr
||x_digital^{k+1} - x_digital^k|| = 0
```

**Convergence Condition**:
```
ρ(J_ad·J_da) < 1
```
where ρ is spectral radius.

#### 6.2 Latency Exploitation

For digital circuits with large propagation delays compared to analog time constants:
```
if (t_event - t_current > 10·Δt_analog) {
    /* Freeze digital states, solve analog only */
    use_constant_digital_inputs = TRUE
}
```

This reduces coupled system size from (n_a + n_d) to n_a.

#### 6.3 Adaptive Model Order Reduction

For frequently triggered digital events, reduce analog model complexity:
```
if (event_rate > 1/(10·Δt_analog)) {
    /* Use simplified analog model */
    switch_to_macromodel()
}
```

The macromodel preserves input-output behavior with reduced state count.

### 7. Error Bounds and Accuracy Guarantees

#### 7.1 Local Truncation Error with Events

For transient analysis with events, LTE must account for discontinuities:
```
LTE_total = LTE_integration + LTE_event
```

where:
- `LTE_integration = (Δt^{k+1}/(k+1)!)·||x^{(k+1)}||`
- `LTE_event = ||x(t_event^+) - x(t_event^-)||`

The adaptive step controller ensures:
```
LTE_total < ε_tol·(1 + ||x||)
```

#### 7.2 Global Error Accumulation

Over simulation interval [0, T], global error is bounded by:
```
||x_numerical - x_exact|| ≤ C·(Δt^p + N_events·ε_event)
```

where:
- `p`: Integration method order
- `C`: Lipschitz constant of the DAE system
- `ε_event`: Event processing error
- `N_events`: Number of events in [0, T]

#### 7.3 Timing Error Propagation

Timing errors propagate through logic chains:

**Worst-Case Timing Error**: For chain of N gates:
```
t_error_total ≤ N·(Δt_min/2 + ε_timing)
```

where `ε_timing` is the timing model error per gate.

**Critical Path Analysis**: Identify paths where timing errors accumulate:
```
if (t_error_total > t_clock_period/10) then issue_warning
```

This mathematical formulation provides the foundation for Ngspice's event-driven engine, ensuring numerical stability, convergence, and accuracy while efficiently bridging continuous-time analog simulation with discrete-event digital logic.

## C Implementation

### 1. Event System Initialization (`evtinit.c`)

The initialization module sets up the event-driven engine's core data structures and prepares the time-wheel scheduler.

**Event System Initialization**:
```c
/* Mathematical Mapping: Initializes the event-driven engine for mixed-signal simulation */
int EVTinit(CKTcircuit *ckt) {
    /* Allocate and initialize event queue */
    ckt->CKTeventQueue = (EventQueue *)malloc(sizeof(EventQueue));
    if (!ckt->CKTeventQueue) return E_NOMEM;
    
    ckt->CKTeventQueue->head = NULL;
    ckt->CKTeventQueue->tail = NULL;
    ckt->CKTeventQueue->count = 0;
    ckt->CKTeventQueue->max_events = MAX_EVENTS;
    ckt->CKTeventQueue->last_process_time = 0.0;
    
    /* Initialize time-wheel scheduler */
    ckt->CKTtimeWheel = EVTsetupTimeWheel(ckt);
    if (!ckt->CKTtimeWheel) {
        free(ckt->CKTeventQueue);
        return E_NOMEM;
    }
    
    /* Initialize logic resolution system */
    ckt->CKTlogicSystem = EVTinitLogicSystem();
    if (!ckt->CKTlogicSystem) {
        EVTfreeTimeWheel(ckt->CKTtimeWheel);
        free(ckt->CKTeventQueue);
        return E_NOMEM;
    }
    
    /* Set initial event processing state */
    ckt->CKTmode |= MODEEVENT;
    ckt->CKTstate &= ~EVENT_PENDING;
    
    return OK;
}

/* Mathematical Mapping: Initializes the 12-state logic resolution system */
LogicSystem *EVTinitLogicSystem(void) {
    LogicSystem *ls = (LogicSystem *)malloc(sizeof(LogicSystem));
    if (!ls) return NULL;
    
    /* Initialize logic state tables */
    for (int i = 0; i < 4; i++) {  /* 4 logic values */
        for (int j = 0; j < 3; j++) {  /* 3 strengths */
            ls->stateTable[i][j].logic_value = i;
            ls->stateTable[i][j].strength = j;
            ls->stateTable[i][j].driven = (j != STRENGTH_HIZ);
        }
    }
    
    /* Initialize conflict resolution table */
    EVTinitConflictTable(ls);
    
    /* Initialize metastability resolution */
    ls->metastableSeed = 0xDEADBEEF;  /* Deterministic seed */
    
    return ls;
}
```

**Mathematical Mapping**: The initialization establishes the event queue `Q = {(t_i, e_i) | t_i < t_{i+1}}` and the 12-state logic system `S = {0,1,X,Z} × {STRONG,RESISTIVE,HI_Z}`.

### 2. Time-Wheel Setup and Configuration (`evtsetup.c`)

The setup module configures the hierarchical time-wheel scheduler for efficient event management.

**Time-Wheel Structure**:
```c
/* Mathematical Mapping: Hierarchical time-wheel for O(1) event scheduling */
typedef struct timewheel {
    Event *slots[TIME_WHEEL_SIZE];  /* Current wheel slots W_i */
    struct timewheel *nextWheel;    /* Next wheel for longer times */
    int currentSlot;                /* Current slot pointer */
    double slotDuration;            /* Time per slot Δt_min */
    double wheelDuration;           /* Total wheel coverage T_max */
    double baseTime;                /* Reference time for slot calculation */
} TimeWheel;

typedef struct {
    TimeWheel *wheel1;              /* Wheel for short-term events (ns-μs) */
    TimeWheel *wheel2;              /* Wheel for medium-term events (μs-ms) */
    TimeWheel *wheel3;              /* Wheel for long-term events (ms-s) */
    double currentTime;             /* Current simulation time t */
    double minEventSpacing;         /* Δt_min for Zeno prevention */
} HierarchicalTimeWheel;
```

**Time-Wheel Setup**:
```c
/* Mathematical Mapping: Configures hierarchical time-wheel with optimal slot sizes */
HierarchicalTimeWheel *EVTsetupTimeWheel(CKTcircuit *ckt) {
    HierarchicalTimeWheel *htw = (HierarchicalTimeWheel *)malloc(sizeof(HierarchicalTimeWheel));
    if (!htw) return NULL;
    
    /* Mathematical: Set minimum event spacing Δt_min = max(ε_time, 10·t_step/tol, t_rise/100) */
    htw->minEventSpacing = fmax(1e-15, 10.0 * ckt->CKTdelta / ckt->CKTreltol);
    
    /* Setup wheel 1: High resolution for short-term events */
    htw->wheel1 = EVTcreateWheel(htw->minEventSpacing, TIME_WHEEL_SIZE);
    if (!htw->wheel1) {
        free(htw);
        return NULL;
    }
    htw->wheel1->wheelDuration = htw->wheel1->slotDuration * TIME_WHEEL_SIZE;
    
    /* Setup wheel 2: Medium resolution */
    htw->wheel2 = EVTcreateWheel(htw->wheel1->wheelDuration, TIME_WHEEL_SIZE);
    if (!htw->wheel2) {
        EVTfreeWheel(htw->wheel1);
        free(htw);
        return NULL;
    }
    
    /* Setup wheel 3: Low resolution for long-term events */
    htw->wheel3 = EVTcreateWheel(htw->wheel2->wheelDuration, TIME_WHEEL_SIZE);
    if (!htw->wheel3) {
        EVTfreeWheel(htw->wheel1);
        EVTfreeWheel(htw->wheel2);
        free(htw);
        return NULL;
    }
    
    htw->currentTime = ckt->CKTtime;
    
    return htw;
}

/* Mathematical Mapping: Creates time-wheel with given slot duration */
TimeWheel *EVTcreateWheel(double slotDuration, int size) {
    TimeWheel *tw = (TimeWheel *)malloc(sizeof(TimeWheel));
    if (!tw) return NULL;
    
    tw->slotDuration = slotDuration;
    tw->currentSlot = 0;
    tw->baseTime = 0.0;
    tw->nextWheel = NULL;
    
    /* Initialize all slots to empty */
    for (int i = 0; i < size; i++) {
        tw->slots[i] = NULL;
    }
    
    return tw;
}
```

**Mathematical Mapping**: The time-wheel setup implements the hierarchical structure `W = (W₀, W₁, ..., W_{k-1})` with `k = ⌈T_max/Δt_min⌉` and configures the minimum event spacing `Δt_min` for Zeno behavior prevention.

### 3. Event Queue Management (`evtqueue.c`)

The queue module implements the time-ordered event queue with efficient insertion and retrieval operations.

**Event Queue Structure**:
```c
/* Mathematical Mapping: Time-ordered event queue Q = {(t_i, e_i) | t_i < t_{i+1}} */
typedef struct event {
    double timestamp;               /* Event time t_i */
    int event_type;                 /* EVENT_DIGITAL, EVENT_ANALOG, EVENT_STATE */
    int node_index;                 /* Affected circuit node */
    union {
        double analog_value;        /* New analog value */
        int digital_value;          /* New digital value ∈ {0,1} */
        LogicState logic_value;     /* 12-state logic value */
    } value;
    double propagation_delay;       /* Δ_i for timing propagation */
    struct event *next;             /* Next event in queue */
    struct event *prev;             /* Previous event for O(1) removal */
} Event;

typedef struct {
    Event *head;                    /* First event (earliest time) */
    Event *tail;                    /* Last event (latest time) */
    int count;                      /* Number of events |Q| */
    int max_events;                 /* Maximum queue size */
    double last_process_time;       /* Time of last event processing */
    Event *free_list;               /* Free list for event recycling */
} EventQueue;
```

**Event Insertion with Time-Wheel**:
```c
/* Mathematical Mapping: Inserts event into time-wheel with slot_index = ⌊(t_event - t_current)/Δt_min⌋ mod k */
int EVTqueueEvent(HierarchicalTimeWheel *htw, Event *ev) {
    double delta = ev->timestamp - htw->currentTime;
    
    if (delta < 0) {
        /* Event in past - process immediately */
        return EVTprocessImmediate(ev);
    }
    
    /* Mathematical: Determine which wheel to use based on delta */
    if (delta < htw->wheel1->wheelDuration) {
        return EVTinsertIntoWheel(htw->wheel1, ev, delta);
    } else if (delta < htw->wheel2->wheelDuration) {
        return EVTinsertIntoWheel(htw->wheel2, ev, delta);
    } else {
        return EVTinsertIntoWheel(htw->wheel3, ev, delta);
    }
}

/* Mathematical Mapping: O(1) insertion into specific time-wheel */
int EVTinsertIntoWheel(TimeWheel *tw, Event *ev, double delta) {
    /* Mathematical: slot_index = ⌊delta / slotDuration⌋ mod TIME_WHEEL_SIZE */
    int slot = (tw->currentSlot + (int)(delta / tw->slotDuration)) % TIME_WHEEL_SIZE;
    
    /* Insert at head of slot's event list */
    ev->next = tw->slots[slot];
    if (tw->slots[slot]) {
        tw->slots[slot]->prev = ev;
    }
    tw->slots[slot] = ev;
    ev->prev = NULL;
    
    return OK;
}
```

**Event Merging for Zeno Prevention**:
```c
/* Mathematical Mapping: Merges events if |t_i - t_j| < Δt_min */
int EVTmergeEvents(EventQueue *queue, Event *newEv) {
    Event *curr = queue->tail;
    
    /* Check if new event is too close to last event */
    if (curr && (newEv->timestamp - curr->timestamp) < queue->min_spacing) {
        /* Mathematical: Merge events t_merged = (t_i + t_j)/2 */
        double mergedTime = (curr->timestamp + newEv->timestamp) / 2.0;
        
        /* Mathematical: v_merged = v_j if |t_j - t_current| < |t_i - t_current| */
        if (fabs(newEv->timestamp - queue->last_process_time) < 
            fabs(curr->timestamp - queue->last_process_time)) {
            /* Keep new event's value */
            curr->timestamp = mergedTime;
            curr->value = newEv->value;
        } else {
            /* Keep old event's value, just update time */
            curr->timestamp = mergedTime;
        }
        
        /* Free the new event since it was merged */
        EVTfreeEvent(newEv);
        return MERGED;
    }
    
    /* No merge needed, insert normally */
    return NOT_MERGED;
}
```

**Mathematical Mapping**: The queue management implements the time-ordered event queue with O(1) insertion via time-wheel scheduling. Event merging implements the Zeno prevention condition `|t_i - t_j| < Δt_min` with `t_merged = (t_i + t_j)/2`.

### 4. Event Dequeue and Processing (`evtdeque.c`)

The dequeue module handles event retrieval and processing from the time-wheel scheduler.

**Event Retrieval from Time-Wheel**:
```c
/* Mathematical Mapping: Retrieves and processes all events with timestamp ≤ current_time */
int EVTdequeueEvents(HierarchicalTimeWheel *htw, double currentTime, 
                     CKTcircuit *ckt) {
    int eventsProcessed = 0;
    
    /* Mathematical: Advance time-wheel slots based on time advancement */
    double deltaTime = currentTime - htw->currentTime;
    if (deltaTime <= 0) return 0;
    
    /* Process events from wheel1 (highest resolution) */
    eventsProcessed += EVTprocessWheel(htw->wheel1, deltaTime, ckt);
    
    /* Migrate events from higher wheels to lower wheels if needed */
    EVTmigrateEvents(htw, currentTime);
    
    htw->currentTime = currentTime;
    
    return eventsProcessed;
}

/* Mathematical Mapping: Processes events from a specific wheel for time advancement Δt */
int EVTprocessWheel(TimeWheel *tw, double deltaTime, CKTcircuit *ckt) {
    int eventsProcessed = 0;
    
    /* Mathematical: slots_to_process = ⌊Δt / slotDuration⌋ */
    int slotsToProcess = (int)(deltaTime / tw->slotDuration);
    if (slotsToProcess > TIME_WHEEL_SIZE) {
        slotsToProcess = TIME_WHEEL_SIZE;  /* Process entire wheel */
    }
    
    for (int i = 0; i < slotsToProcess; i++) {
        int slot = (tw->currentSlot + i) % TIME_WHEEL_SIZE;
        
        /* Process all events in this slot */
        Event *ev = tw->slots[slot];
        while (ev) {
            Event *next = ev->next;
            
            /* Apply event to circuit */
            EVTapplyEvent(ckt, ev);
            eventsProcessed++;
            
            /* Free the event */
            EVTfreeEvent(ev);
            
            ev = next;
        }
        
        /* Clear the slot */
        tw->slots[slot] = NULL;
    }
    
    /* Update current slot pointer */
    tw->currentSlot = (tw->currentSlot + slotsToProcess) % TIME_WHEEL_SIZE;
    
    return eventsProcessed;
}
```

**Event Application to Circuit**:
```c
/* Mathematical Mapping: Applies event e_i = (t_i, τ_i, x_i, v_i) to circuit state */
int EVTapplyEvent(CKTcircuit *ckt, Event *ev) {
    switch (ev->event_type) {
        case EVENT_ANALOG:
            /* Mathematical: Update analog node voltage x_i = v_i */
            if (ev->node_index >= 0 && ev->node_index < ckt->CKTmaxEqnNum) {
                ckt->CKTrhs[ev->node_index] = ev->value.analog_value;
                ckt->CKTstate |= MODECHANGE;
            }
            break;
            
        case EVENT_DIGITAL:
            /* Mathematical: Update digital state with strength resolution */
            EVTapplyDigitalEvent(ckt, ev->node_index, ev->value.digital_value);
            break;
            
        case EVENT_LOGIC:
            /* Mathematical: Apply 12-state logic update with conflict resolution */
            EVTapplyLogicEvent(ckt->CKTlogicSystem, ev->node_index, 
                              ev->value.logic_value);
            break;
            
        case EVENT_STATE:
            /* Mathematical: Instantaneous state update x(t_i⁺) = g(x(t_i⁻), e_i) */
            EVTapplyStateEvent(ckt, ev);
            break;
    }
    
    return OK;
}
```

**Mathematical Mapping**: The dequeue processing implements the event-driven integration scheme where for intervals `[t_k, t_{k+1}]` we solve `F(x, ẋ, t) = 0` with initial condition updates `x(t_k⁺) = g(x(t_k⁻), e_k)` at events.

### 5. Event Iterator and Time Advancement (`evtiter.c`)

The iterator module provides efficient traversal of pending events and time advancement control.

**Event Iterator Structure**:
```c
/* Mathematical Mapping: Iterator for traversing events in time order */
typedef struct {
    Event *current;                 /* Current event in iteration */
    TimeWheel *currentWheel;        /* Current wheel being iterated */
    int currentSlot;                /* Current slot in wheel */
    HierarchicalTimeWheel *htw;     /* Reference to hierarchical time-wheel */
    double stopTime;                /* Stop iteration at this time */
} EventIterator;
```

**Event Iteration with Time-Wheel**:
```c
/* Mathematical Mapping: Iterates through events in time order t_i < t_{i+1} */
Event *EVTnextEvent(EventIterator *iter) {
    while (iter->currentWheel) {
        /* Check current event in current slot */
        if (iter->current) {
            Event *ev = iter->current;
            iter->current = ev->next;
            
            /* Mathematical: Check if event time ≤ stopTime */
            if (ev->timestamp <= iter->stopTime) {
                return ev;
            } else {
                /* Event is beyond stop time */
                return NULL;
            }
        }
        
        /* Move to next slot in current wheel */
        iter->currentSlot++;
        if (iter->currentSlot >= TIME_WHEEL_SIZE) {
            /* Move to next wheel */
            iter->currentWheel = iter->currentWheel->nextWheel;
            iter->currentSlot = 0;
        } else {
            /* Get events from next slot */
            if (iter->currentWheel) {
                iter->current = iter->currentWheel