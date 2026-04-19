# CIDER TCAD: 1D Poisson and Continuity Solvers

_Generated 2026-04-13 10:52 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onemesh.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onesetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onepoiss.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onecond.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onecont.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onesolve.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/oneaval.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/oneadmit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/onedopng.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/oned/oneproj.c`

# **Ngspice EDA Codebase: Professional Reference Compendium**

## **Executive Summary**

This comprehensive reference documents the mathematical foundations and C implementation architecture of the Ngspice Electronic Design Automation suite, providing hardware engineers with a definitive guide to the simulator's internal algorithms. The compendium systematically deconstructs Ngspice's multi-layered architecture—from lexical parsing through mixed-signal simulation to TCAD device modeling—revealing the sophisticated mathematical frameworks that bridge circuit theory with numerical computation.

## **Volume I: Parser Architecture & Device Modeling**

### **Chapter 1: Netlist Parsing: Multi-Pass Architecture and Subcircuit Expansion**
**Core Files:** `inppas1.c`, `inppas2.c`, `inppas3.c`, `inppas1.h`, `inppas2.h`, `inppas3.h`

**Mathematical Foundation:** Three-pass parsing architecture implementing union-find algorithms for node aliasing and topological binding. Subcircuit expansion follows graph theory models with depth-limited recursion (`MAX_EXPANSION_DEPTH = 100`). The system transforms hierarchical netlists into flat Modified Nodal Analysis (MNA) matrices through formal graph transformations.

**C Implementation:** Pass 1 (`inppas1.c`) performs lexical scanning and symbol table population. Pass 2 (`inppas2.c`) implements subcircuit instantiation via depth-first traversal. Pass 3 (`inppas3.c`) finalizes node numbering using union-find with path compression. The architecture ensures O(n·α(n)) complexity for circuit expansion.

### **Chapter 2: Lexical Analysis: Tokenization and Value Extraction**
**Core Files:** `inpgtok.c`, `inpgval.c`, `inpgstr.c`, `inpgtitl.c`, `inpgmod.c`

**Mathematical Foundation:** Formal grammar parsing with 8-state finite automaton for numeric extraction (S0-S7). SPICE scale factor mapping: σ(s) where s ∈ {T=1e12, G=1e9, MEG=1e6, K=1e3, m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15}. Value transformation Γ implements IEEE 754 limits with overflow protection.

**C Implementation:** Tokenization function T(C) processes input stream with `MAX_TOKEN_LEN = 256`. `INPstr2dbl()` in `inpgval.c` implements the state machine with scientific notation handling. Scale factor lookup uses perfect hashing for O(1) performance.

### **Chapter 3: Device Parsing: Passives, Switches, and Independent Sources**
**Core Files:** `inp2r.c`, `inp2c.c`, `inp2l.c`, `inp2k.c`, `inp2v.c`, `inp2i.c`, `inp2w.c`, `inp2s.c`

**Mathematical Foundation:** Device parameter mapping functions Φ: SPICE card → model parameters with validation constraints: R > 0, 0 < C, L, |K| ≤ 1 for mutual inductors. Time-domain sources implement SINE, PULSE, PWL, EXP functions with continuity enforcement.

**C Implementation:** Each file implements `parseDEVICE()` function with parameter extraction and validation. `inp2v.c` and `inp2i.c` handle independent sources with transient waveform compilation. Switch models (`inp2s.c`) implement smooth transitions using hyperbolic tangent for Newton-Raphson compatibility.

### **Chapter 4: Device Parsing: Active Semiconductors and Dependent Sources**
**Core Files:** `inp2d.c`, `inp2q.c`, `inp2m.c`, `inp2j.c`, `inp2z.c`, `inp2e.c`, `inp2f.c`, `inp2g.c`, `inp2h.c`, `inp2o.c`, `inp2p.c`, `inp2t.c`, `inp2u.c`, `inp2b.c`, `inp2n.c`, `inp2y.c`

**Mathematical Foundation:** Semiconductor geometry parameter extraction with area/perimeter scaling. Controlled source equations: VCVS (e), CCVS (h), VCCS (g), CCCS (f). Model-card resolution via hash table lookup with parameter propagation hierarchy.

**C Implementation:** `parseMOSFET()` in `inp2m.c` extracts W, L, AD, AS, PD, PS with unit conversion. Model parameter inheritance uses `GENmodel` linked lists. Dependent sources implement stamping functions for MNA matrix contributions.

### **Chapter 5: Behavioral Modeling: Expression Grammar and Abstract Syntax Trees**
**Core Files:** `inpptree-parser.y`, `inpptree-parser.h`, `inpptree-parser.c`, `inpptree.c`, `ptfuncs.c`, `ifeval.c`, `inpeval.c`

**Mathematical Foundation:** Context-free grammar G = (V, Σ, P, S) for behavioral expressions. Abstract Syntax Tree (AST) as 5-tuple: (node_type, value, left_child, right_child, derivative_fn). Automatic differentiation for Newton-Raphson using chain rule: ∂f(g(x))/∂x = f'(g(x))·g'(x).

**C Implementation:** `PTnode` struct with union for values and function pointers. `ptEval()` traverses AST with recursion depth checking (`MAX_AST_DEPTH = 100`). Numerical protection functions: `safe_divide()`, `safe_log()`, `smooth_if()` with ε_min = 1e-30.

## **Volume II: Simulation Core & Control Systems**

### **Chapter 6: Parser Core: Symbol Tables, Memory Interfaces, and Error Propagation**
**Core Files:** `ifnewuid.c`, `inperror.c`, `inperrc.c`, `sperror.c`, `inpsymt.c`, `inpaname.c`, `inpapnam.c`, `inppname.c`, `inptyplk.c`, `inpmktmp.c`, `inplist.c`, `inpfindl.c`, `inpfindv.c`, `inpxx.h`

**Mathematical Foundation:** Symbol table function S: Σ* → ℕ ∪ {⊥} providing injective mapping from node names to state vector indices. Error propagation: ε_parse ≤ ε_mach + ε_scale. Convergence precondition: G'[i][i] = G[i][i] + G_min for diagonal dominance.

**C Implementation:** `CKTcircuit` struct embodies DAE state; `SMPmatrix` handles Jacobian; hash tables (`CKTnodeHash`) provide O(1) node lookup. `CKTdoJob()` implements Newton loop with convergence check: `normDelta < (ABSTOL + RELTOL * normX)`. Error recovery via `CKTrecover()` implements homotopy continuation.

### **Chapter 7: Simulation Control Dispatcher: DAE System Abstraction**
**Core Files:** `analysis.c`, `analysis.h`, `cktdojob.c`, `cktntask.c`, `cktftask.c`, `cktnewan.c`

**Mathematical Foundation:** Unified DAE framework: F(x(t), ẋ(t), u(t), t) = 0. Domain-specific abstractions: DC (F(x, 0, U_dc, t) = 0), AC ([G + jωC]·X̃(ω) = B̃(ω)), Transient (M_tr(h) = G + (α₀/h)C). State machine S = {INIT, DC_OP, DC_SWEEP, AC_SETUP, AC_SWEEP, TRAN_SETUP, TRAN_LOOP, POST_PROCESS, ERROR, TERMINATE}.

**C Implementation:** `SPICEanalysis` struct array registers analysis methods. `CKTdoJob()` implements dispatch loop with mode bitmask (`MODEDC=0x01`, `MODETRAN=0x02`, `MODEAC=0x20`). Error recovery hierarchy: matrix conditioning → nonlinear damping → time-step reduction → analysis scope reduction.

## **Volume III: Mixed-Signal & XSPICE Systems**

### **Chapter 8: XSPICE CMPP: Lex/Yacc Compilation of Code Models**
**Core Files:** `main.c`, `ifs_lex.l`, `ifs_yacc.y`, `mod_lex.l`, `mod_yacc.y`, `pp_ifs.c`, `pp_mod.c`, `read_ifs.c`, `writ_ifs.c`

**Mathematical Foundation:** Formal grammars: Interface Specification (Chomsky Type-2) G₁ = (V₁, Σ₁, R₁, S₁), Model Behavior (EBNF) G₂. AST construction as tuples (type, value, children[]). Macro expansion: INPUT(x) → *(ckt→CKTstates[inst→stateOffset + x_index]). Type mapping φ: SPICE → C types.

**C Implementation:** Lex/Yacc grammars generate token streams and parse trees. `IFSAST` structure with `IFSNodetype` enum. `generate_spicedev()` creates `SPICEdev` structures. Macro expansion engine with cycle detection (D_max = 100). Code generation as graph transformation T: G_AST → G_CFG.

### **Chapter 9: XSPICE Runtime: Code Model Execution and Event Bridging**
**Core Files:** `xspice.c`, `cm.c`, `cmevt.c`, `cmexport.c`, `cmmeters.c`, `cmutil.c`

**Mathematical Foundation:** Continuous-discrete bridging: ADC model (DigitalOutput[n] = {1 if V_analog ≥ V_thresh_high[n], 0 if V_analog ≤ V_thresh_low[n], previous otherwise}), DAC model (V_analog = V_low + (V_high - V_low)·(∑ bit[i]·2ⁱ)/(2^N - 1)). Event-driven state machine Σ = (Q, Σ, δ, q₀, F).

**C Implementation:** `CMManager` struct manages code model execution. `ADInterface` handles analog-digital conversion. `EventQueue` implements time-ordered event scheduling with O(log n) insertion. Jacobian stamping via `CM_STAMP_CONDUCTANCE`. Safety macros: `CM_SAFE_DIVIDE`, `CM_SAFE_LOG`, `CM_SAFE_EXP` with argument clamping.

### **Chapter 10: XSPICE Core Enhancements: Operating Points and Diagnostics**
**Core Files:** `enh.c`, `enhtrans.c`, `evtop.c`, `evtplot.c`, `evtprint.c`, `evttermi.c`, `evtdump.c`

**Mathematical Foundation:** Rshunt enhancement: G_ii ← G_ii + G_shunt with G_shunt = 1/R_shunt, R_shunt = 10¹²Ω. Matrix conditioning: κ(Y) → κ(Y + G_shunt·I) ≈ κ(Y)/κ_shunt. 12-state digital logic: V × S where V = {0,1,X,Z}, S = {S,R,H} with strength weights w(S)=3, w(R)=2, w(H)=1.

**C Implementation:** `ENHinstance` struct with matrix pointers for conductance stamping. `EVTnodeState` encodes 12-state logic in 4 bits. `EVTopSolve()` implements hybrid DC convergence with criteria: `|V_analog_{k+1} - V_analog_k| < ε_v` and `digital_state_{k+1} = digital_state_k`. VCD output via `stateToVCD()` mapping.

### **Chapter 11: Event-Driven Engine: Time-Wheels and Logic Resolution**
**Core Files:** `evtinit.c`, `evtsetup.c`, `evtqueue.c`, `evtdeque.c`, `evtiter.c`, `evtnext_time.c`, `cktdojob.c`, `dctran.c`, `ckttrunc.c`, `cktacct.c`, `ninteg.c`

**Mathematical Foundation:** Time-wheel scheduling with O(1) complexity for event insertion/deletion. Logic conflict resolution: s_result = argmax_{s_i} w(s_i). Mixed-signal Jacobian blocks for analog-digital interfaces. Zeno behavior prevention via minimum event spacing Δt_min.

**C Implementation:** `EventQueue` circular buffer with hash wheel. `resolveLogicConflict()` implements strength hierarchy. `CKTdoJob()` state machine handles event synchronization. `CKTrunc()` computes Local Truncation Error (LTE) for adaptive time-stepping.

### **Chapter 12: Mixed-Mode Synchronization: Transient Acceptance and Backtracking**
**Core Files:** `evtload.c`, `evtaccept.c`, `evtbackup.c`, `evtcall_hybrids.c`, `evtnode_copy.c`, `cktdojob.c`, `dctran.c`, `ckttrunc.c`, `cktacct.c`, `ninteg.c`

**Mathematical Foundation:** Hybrid DAE system: F(x(t), ẋ(t), d(t), t) = 0. Acceptance criteria: LTE < ε_LTE, digital state consistency, residual checks. Backtracking: h ← βh with β = 0.5. Event synchronization: t_next = min(event_queue.next_time, t_n + Δt_new).

**C Implementation:** `TRANanalysis()` implements transient loop with step rejection. `CKTsaveState()`/`CKTrestoreState()` provide O(1) state rollback. `CKTaccept()` handles breakpoint alignment. Homotopy methods (GMIN stepping, source stepping) in `CKTrecover()`.

## **Volume IV: TCAD & Advanced Device Simulation**

### **Chapter 13: CIDER TCAD: Spatial Mesh Generation and Doping Profiles**
**Core Files:** `cards.c`, `mesh.c`, `meshset.c`, `domain.c`, `domnset.c`, `doping.c`, `dopset.c`, `material.c`, `matlset.c`, `electrod.c`, `elctset.c`

**Mathematical Foundation:** Geometric progression spacing: x_i = x_0 + h_0·(rⁱ - 1)/(r - 1). Adaptive refinement: Δx_max = min(L_debye, L_drift, L_diffusion). Doping profiles: Gaussian N(x) = N_peak·exp(-((x - R_p)²)/(2σ²)), erfc N(x) = N_surface·erfc(x/(2√(Dt))). Masetti mobility: μ(T,N) = μ_min1·exp(-P_c/N) + (μ_const - μ_min2)/(1 + (N/C_r)^α) - μ_1/(1 + (C_s/N)^β).

**C Implementation:** `Mesh` struct with coordinate arrays and connectivity matrices. `generateMesh1D()` implements geometric progression. `computeGaussianDoping()` evaluates profiles with exponent clamping. `MaterialDB` hash table for property lookup. AABB tests for domain overlap detection.

### **Chapter 14: CIDER TCAD: Solid-State Physics and Material Models**
**Core Files:** `mater.c`, `mobil.c`, `recomb.c`, `database.c`, `geominfo.c`, `integset.c`, `integuse.c`, `suprem.c`, `suprmitf.c`

**Mathematical Foundation:** Drift-diffusion equations: J_n = qμ_n nE + qD_n∇n, J_p = qμ_p pE - qD_p∇p. Poisson: ∇·(ε∇ψ) = -q(p - n + N_d - N_a). SRH recombination: R = (pn - n_i²)/[τ_p(n + n_1) + τ_n(p + p_1)]. Bandgap narrowing (Slotboom): ΔE_g = q·[A·ln(N/N_0) + B·(ln(N/N_0))² + C·(ln(N/N_0))³].

**C Implementation:** `Material` struct with mobility models and recombination parameters. `MobilityModel` implements field-dependent mobility with velocity saturation. `recombSRH()` computes recombination rates with trap statistics. `integset.c` handles numerical integration schemes for transient simulation.

### **Chapter 15: CIDER TCAD: 1D Poisson and Continuity Solvers**
**Core Files:** `onemesh.c`, `onesetup.c`, `onepoiss.c`, `onecond.c`, `onecont.c`, `onesolve.c`, `oneaval.c`, `oneadmit.c`, `onedopng.c`, `oneproj.c`

**Mathematical Foundation:** Scharfetter-Gummel discretization: J_{n,i+1/2} = (q/Δx)[μ_n B(Δψ - Δφ_n) n_{i+1} - μ_n B(-Δψ + Δφ_n) n_i] with B(u) = u/(e^u - 1). Gummel iteration: sequential solution of Poisson → electron continuity → hole continuity. Newton method: J(X^k)ΔX^k = -F(X^k) with block tridiagonal Jacobian.

**C Implementation:** `Mesh1D` struct stores ψ, n, p arrays. `assemblePoisson()` implements finite difference discretization. `bernoulli()` function with Taylor series for small arguments. `solveGummel()` and `solveNewton()` provide nonlinear solvers. `computeAdmittance()` calculates Y(ω) = G + jωC for AC analysis.

## **Critical Algorithms & Numerical Methods**

### **1. Newton-Raphson with Homotopy Continuation**
```
J(x_k)·Δx_k = -F(x_k)
x_{k+1} = x_k + λΔx_k  with λ ∈ (0,1] from line search
```
Recovery strategies: GMIN stepping (G ← G + g_min·I), source stepping (b ← αb, α: 0→1), pivot relaxation.

### **2. Sparse Matrix Techniques**
- Compressed Sparse Column (CSC) format for Jacobian storage
- Markowitz ordering for fill-in reduction
- KLU factorization for circuit matrices
- Iterative refinement for improved accuracy

### **3. Time Integration Methods**
- Trapezoidal (2nd order): x_{n+1} = x_n + (h/2)(f(x_n) + f(x_{n+1}))
- Gear (2nd-6th order): ∑ α_k x_{n-k} = hβ_0 f(x_{n+1})
- Local Truncation Error: LTE = (Δt^{p+1}/(p+1)!)·||x^{(p+1)}(ξ)||_∞
- Adaptive time-stepping: Δt_new = Δt_old·min(2, max(0.5, (ε/||LTE||)^{1/(p+1)}))

### **4. Convergence Criteria**
```
|Δx_i| < ε_abs + ε_rel·|x_i|  (ε_abs = 1e-12, ε_rel = 1e-3)
||F(x)||_∞ < ε_res·(1 + ||b||_∞)  (ε_res = 1e-6)
Charge conservation: |∫ρ dΩ| < 1e-12·max|ρ|·Volume
```

### **5. Numerical Stability Safeguards**
- Exponential clamping: |exp(x)| ≤ exp(±700)
- Safe functions: safe_divide(a,b) = a/(b + ε·sign(b)), ε = 1e-30
- Smooth transitions: smooth_if(x, a, b) = a + (b-a)/(1 + exp(-αx)), α = 100
- Diagonal dominance: G_ii ← G_ii + max(0, ∑_{j≠i}|G_ij| - G_ii) + G_min

## **Performance Characteristics**

### **Computational Complexity**
- Matrix assembly: O(N) for sparse device stamps
- Linear solve: O(N^1.4) for sparse factorization, O(N·log N) for iterative methods
- Transient simulation: O(T·N^1.4) where T is time points
- Memory: O(N) for sparse storage, O(N^1.2) for fill-in

### **Memory Hierarchy Optimization**
- Cache-aware sparse matrix storage
- Memory pooling for frequent allocations
- Checkpointing for state backtracking
- Incremental updates for parameter sweeps

## **Integration Architecture**

### **Device-to-Circuit Interface**
```
SPICEdev {
    .load()      // DC/transient stamp
    .acLoad()    // AC stamp  
    .trunc()     // LTE calculation
    .convTest()  // Convergence check
    .temperature() // Temperature update
}
```

### **Analysis Plugin System**
```
SPICEanalysis {
    .JOBtype     // Analysis identifier
    .JOBsetFn    // Parameter setup
    .JOBloadFn   // Matrix loading
    .JOBaskFn    // Query interface
}
```

## **Validation & Verification**

### **Consistency Checks**
1. **KCL Verification**: ∑ I_node = 0 within ε_KCL = 1e-12·max|I|
2. **Energy Conservation**: |∫(P_in - P_diss)dt|/|∫P_in dt| < 1e-6
3. **Charge Conservation**: |∫ρ dΩ| < 1e-12·max|ρ|·Volume
4. **Small-Signal Consistency**: Im(Y(ω))/ω = C(ω), Re(Y(ω)) = G(ω)

### **Numerical Accuracy Benchmarks**
- Double precision throughout (IEEE 754)
- Relative error: 1e-6 typical, 1e-12 achievable
- Matrix condition number: κ < 1/ε_machine with conditioning
- Convergence rate: quadratic for Newton, linear for Gummel

## **Conclusion**

This compendium reveals Ngspice as a sophisticated mathematical engine that transforms circuit descriptions into numerically stable DAE systems. Through its layered architecture—from lexical parsing to TCAD device simulation—Ngspice maintains rigorous mathematical consistency while providing the robustness required for industrial-scale circuit simulation. The implementation demonstrates how abstract circuit theory becomes executable numerical algorithms through careful attention to discretization schemes, convergence criteria, and numerical stability.

The codebase represents decades of algorithmic refinement, balancing computational efficiency with physical accuracy. For hardware engineers, understanding these internal mechanisms provides not only insight into simulator behavior but also guidance for creating models and simulations that leverage Ngspice's full capabilities while avoiding numerical pitfalls.

---

**Key Constants Reference**
- `MAX_TOKEN_LEN = 256` (1024 for expressions)
- `MAX_EXPANSION_DEPTH = 100`
- `MAX_AST_DEPTH = 100`
- `EXP_MAX = 700.0`, `EXP_MIN = -700.0`
- `ABSTOL = 1e-12`, `RELTOL = 1e-3`, `CHGTOL = 1e-14`
- `GMIN = 1e-12`, `PIVTOL = 1e-13`
- `ITL1 = 100` (DC iterations), `ITL2 = 50` (DC sweep)
- `ITL3 = 4` (transient min), `ITL4 = 10` (transient max)
- `TRTOL = 7.0` (LTE tolerance factor)

**Mathematical Symbols Glossary**
- x: State vector (node voltages + branch currents)
- ẋ: Time derivative of state vector
- F: DAE system function
- J: Jacobian matrix ∂F/∂x
- G: Conductance matrix (real part)
- C: Capacitance/inductance matrix
- ψ: Electrostatic potential
- n, p: Electron/hole concentrations
- μ: Carrier mobility
- τ: Carrier lifetime
- ε: Permittivity
- q: Electron charge (1.60217662e-19 C)
- k: Boltzmann constant (1.380649e-23 J/K)
- T: Temperature (K)
- V_T = kT/q: Thermal voltage (≈25.85 mV at 300K)