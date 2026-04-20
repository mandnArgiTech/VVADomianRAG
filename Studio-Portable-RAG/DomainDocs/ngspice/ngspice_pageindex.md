# ngspice Codebase — PageIndex

> **Purpose:** Hierarchical tree index of the ngspice source tree, inspired by the
> [PageIndex](https://github.com/VectifyAI/PageIndex) framework. Each node summarises
> a subtree so that LLM-based retrieval can navigate to the relevant section without
> scanning the entire codebase.

---

## 0. Root (`ngspice/`)

**Summary:** ngspice is a mixed-level, mixed-signal circuit simulator descended from
Berkeley SPICE 3. The top-level tree is split into build infrastructure (`configure`,
`Makefile`, `m4/`), documentation (`doc/`, `man/`), example circuits (`examples/`),
and source code (`src/`). All simulator logic lives under `src/`.

```
ngspice/
├── src/             ← all C simulator source
├── examples/        ← .cir / .sp input deck examples
├── tests/           ← regression test suite per device model
├── doc/             ← PDF reference manuals (not C source)
├── man/             ← Unix manual pages
├── contrib/         ← third-party scripts, VBIC model patches
├── xgraph/          ← standalone X11 graph viewer
└── visualc/         ← Windows MSVC project files
```

---

## 1. `src/` — Source Tree Root

**Summary:** The `src/` tree has five major subsystems. Each maps to a distinct
phase of simulation or a support library.

| Subtree | Role |
|---------|------|
| `src/frontend/` | CLI, REPL, input deck reader, output / rawfile writer |
| `src/spicelib/` | Core simulation engine: parser, analysis, device models |
| `src/maths/` | Numerical algorithms: Newton–Raphson, sparse matrix, FFT |
| `src/xspice/` | XSPICE mixed-signal / event-driven extensions |
| `src/ciderlib/` | CIDER numerical device simulator (physics-based) |
| `src/misc/` | Utility functions (string, memory, time) |
| `src/include/ngspice/` | Shared headers (`cktdefs.h`, `devdefs.h`, …) |

---

## 2. `src/frontend/` — User Interface & I/O Layer

**Summary:** The frontend is the bridge between the user (or script) and the
simulator back-end. It reads netlist files, exposes an interactive command
interpreter (CP — Command Processor), and writes simulation results to rawfiles,
plot windows, or stdout.

### 2.1 Input reading

| File | Summary |
|------|---------|
| `inpcom.c` | `inp_readall()` — master function: opens the netlist file, expands `.include`/`.lib`, processes parameter blocks, handles subcircuit library loading, and returns a raw linked-list deck (`struct line`). |
| `inp.c` | High-level driver that calls `inpcom.c`, then hands the deck to `subckt.c` for subcircuit flattening, and finally calls the spicelib parser via `spiceif.c`. |
| `subckt.c` | Subcircuit expansion: replaces every `X…` instance with flattened element lines with renamed nodes. |
| `dotcards.c` | Parses all `.` control cards (`.tran`, `.ac`, `.dc`, `.options`, `.measure`, etc.) and creates the corresponding analysis job descriptors. |
| `inpcom.c` | Library habitat tracking, `.param` / `.func` macro expansion via `numparam/`. |

### 2.2 Subcircuit & parameter engine

| File | Summary |
|------|---------|
| `numparam/numpaif.c` | Interface to the numerical parameter / expression evaluator. Resolves `{expr}` parameter substitutions before the parser sees the deck. |
| `variable.c` | CP variable store (`set`, `unset`, `let`); used by `.options` and runtime scripting. |

### 2.3 Command interpreter (CP)

| File | Summary |
|------|---------|
| `commands.c` | Command dispatch table mapping command names to handler functions. |
| `runcoms.c` `runcoms2.c` | `com_run()`, `com_source()` — execute a circuit or script. |
| `com_set.c` | `set` command: user-visible variable assignment. |
| `com_let.c` | `let` — vector arithmetic in the CP language. |
| `com_measure2.c` | `.measure` post-processing: rise/fall time, propagation delay, min/max. |
| `com_fft.c` | `fft` / `ifft` commands, calls `maths/fft/`. |
| `control.c` | Loop/if/while control structures in ngspice scripts. |
| `evaluate.c` | Expression evaluator for vector operations inside CP. |

### 2.4 Output & results

| File | Summary |
|------|---------|
| `outitf.c` | **Central output interface**: `OUTbeginPlot()`, `OUTdata()`, `OUTendPlot()`. Called by every analysis to stream data points. Routes each point either to the in-memory plot (`dvec` list) or to the open rawfile. |
| `rawfile.c` | `raw_write()` / `raw_read()` — binary and ASCII rawfile serialiser / deserialiser. Writes the `.raw` file format (header section listing variables, followed by data points). |
| `nutinp.c` `nutmegif.c` | Nutmeg compatibility: reading old-format rawfiles. |
| `plotting/graf.c` | Terminal / X11 graphing: called after simulation to plot waveforms on screen. |
| `plotting/gnuplot.c` | Writes gnuplot command scripts for external rendering. |
| `com_gnuplot.c` | `gnuplot` command dispatcher. |
| `fourier.c` | Fourier analysis (`.four` dot card result). |

---

## 3. `src/spicelib/` — Core Simulation Engine

**Summary:** The spicelib is the heart of ngspice. It contains the netlist parser
(which builds the `CKTcircuit` struct), the device model library, and all analysis
algorithms.

### 3.1 `src/spicelib/parser/` — Netlist Parser (Pass 1 & 2)

**Summary:** Converts the preprocessed line deck from `frontend/` into the
`CKTcircuit` data structure. Two-pass design: pass 1 collects `.model` cards;
pass 2 instantiates each element.

| File | Summary |
|------|---------|
| `inppas1.c` | Pass 1: scans deck for `.model` lines, calls `INPdomodel()` to register each model into `INPtables`. |
| `inppas2.c` | Pass 2: walks every element line, dispatches to `inp2X.c` handlers by first character. |
| `inp2b.c`…`inp2z.c` | Per-letter element parsers. e.g. `inp2d.c` → diode (`D`), `inp2q.c` → BJT (`Q`), `inp2m.c` → MOSFET (`M`). Each calls `CKTmkCur()` / `CKTmkVol()` to build node connectivity, then `IFnewInstance()` to allocate the device-specific parameter block. |
| `inpdomod.c` | `INPdomodel()`: allocates a model entry, links it into the model table. |
| `inpgmod.c` | `INPgetMod()`: model lookup by name during element parse. |
| `inpeval.c` | Evaluates numerical parameter expressions in the deck. |
| `inpptree.c` `inpptree-parser.c` | Parse-tree builder for expression parameters. |
| `inpsymt.c` | Symbol table (node name → node index mapping). |

### 3.2 `src/spicelib/analysis/` — Analysis Drivers

**Summary:** Contains all analysis algorithms. Each analysis type has its own
`xxxan.c` driver plus `xxxsetp.c` (parameter setup) and `xxxaskq.c` (query
interface). The `ckt*.c` files are shared services used by every analysis.

#### 3.2.1 Shared circuit services

| File | Summary |
|------|---------|
| `cktsetup.c` | `CKTsetup()`: calls every registered device's `DEVsetup` function; allocates state vectors; builds the sparse matrix topology. Must be called once before any simulation. |
| `cktload.c` | `CKTload()`: core inner loop — clears the MNA matrix, then calls `DEVload` for every device instance to stamp conductances and currents. Called at every Newton iteration. |
| `ckttemp.c` | `CKTtemp()`: applies temperature scaling to all device parameters at each temperature point. |
| `cktic.c` | Initial condition handling (`.ic`, `IC=` syntax). |
| `ckttrunc.c` | `CKTtrunc()`: calls each device's `DEVtrunc` for time-step truncation control (LTE). |
| `cktacct.c` | AC analysis node counting; builds the AC right-hand side vector. |
| `cktnoise.c` | Noise contributions from all devices summed into noise spectral density. |
| `cktdump.c` | Debug: prints the MNA matrix and RHS vector. |

#### 3.2.2 Analysis algorithms

| File | Summary |
|------|---------|
| `dcop.c` | DC operating point (`.op`): calls `NIiter()` until convergence with `MODEDCOP`. |
| `dctrcurv.c` | DC sweep (`.dc`): outer loop over swept variable; inner loop is `dcop.c`. |
| `dctran.c` | Transient analysis (`.tran`): time-stepping loop with LTE control; calls `NIiter()` at each time point; calls `OUTdata()` to record each accepted point. |
| `acan.c` | AC analysis (`.ac`): linearises circuit at DC operating point; solves complex MNA system at each frequency; records magnitude/phase via `OUTdata()`. |
| `noisean.c` | Noise analysis (`.noise`): computes noise spectral density at each AC frequency. |
| `distoan.c` | Distortion analysis (`.disto`). |
| `pzan.c` | Pole-zero analysis (`.pz`). |
| `tfanal.c` | Transfer function analysis (`.tf`). |
| `traninit.c` | Transient setup: initial time step, breakpoint table initialisation. |
| `ninteg.c` | Time integration: trapezoidal and Gear methods. |
| `nevalsrc.c` | Evaluates independent source waveforms (PWL, SIN, PULSE, …) at each time point. |
| `analysis.c` | Analysis registration table; maps analysis type codes to driver functions. |

### 3.3 `src/spicelib/devices/` — Device Models

**Summary:** Each device family lives in its own subdirectory. All devices implement
the same interface (`DEVpublic` function table in `devdefs.h`): `DEVsetup`,
`DEVload`, `DEVconverge`, `DEVtrunc`, `DEVtemperature`, `DEVacLoad`, `DEVnoise`, etc.

#### 3.3.1 Passive & source elements

| Directory | Device | Key file | Summary |
|-----------|--------|----------|---------|
| `res/` | Resistor (R) | `resload.c` | Stamps `G=1/R` into MNA matrix diagonals. |
| `cap/` | Capacitor (C) | `capload.c` | Integration method stamps for transient; stamps `jωC` for AC. |
| `ind/` | Inductor (L) + mutual (K) | `indload.c` | State variable for flux; mutual coupling via `indmutual.c`. |
| `vsrc/` | Voltage source (V) | `vsrcload.c` | Voltage controlled branch + KCL row. |
| `isrc/` | Current source (I) | `isrcload.c` | Stamps current into RHS. |
| `vcvs/` | Voltage-controlled V (E) | `vcvsload.c` | |
| `vccs/` | Voltage-controlled I (G) | `vccsload.c` | |
| `cccs/` | Current-controlled I (F) | `cccsload.c` | |
| `ccvs/` | Current-controlled V (H) | `ccvsload.c` | |
| `sw/` | Voltage switch (S) | `swload.c` | |
| `csw/` | Current switch (W) | `cswload.c` | |

#### 3.3.2 Semiconductor devices

| Directory | Device | Key files | Summary |
|-----------|--------|-----------|---------|
| `dio/` | Diode (D) | `dioload.c`, `diosetup.c`, `diotemp.c` | Shockley exponential; junction capacitance; `DEVpnjlim()` voltage limiting. |
| `bjt/` | BJT (Q) | `bjtload.c`, `bjtsetup.c` | Gummel-Poon model; forward/reverse transport currents; base charge. |
| `jfet/` | JFET (J) | `jfetload.c` | Shichman-Hodges quadratic law. |
| `jfet2/` | JFET2 (J) | `jfet2load.c` | Parker-Skellern model. |
| `mes/` | MESFET (Z) | `mesload.c` | Statz-Pucel model. |
| `mesa/` | MESFET-A (Z) | `mesaload.c` | |
| `mos1/` | MOSFET Level 1 (M) | `mos1load.c`, `mos1setup.c` | Classic square-law MOSFET. |
| `mos2/` | MOSFET Level 2 (M) | `mos2load.c` | Physical MOS model with velocity saturation. |
| `mos3/` | MOSFET Level 3 (M) | `mos3load.c` | Semi-empirical Level 3. |
| `mos6/` | MOSFET Level 6 (M) | `mos6load.c` | |
| `bsim1/` | BSIM1 | `bsim1load.c` | First Berkeley Short-channel IGFET Model. |
| `bsim2/` | BSIM2 | `bsim2load.c` | |
| `bsim3/` `bsim3v32/` | BSIM3v3.2 | `b3v32ld.c` | Industry-standard 0.25 µm model. |
| `bsim4/` `bsim4v5/` `bsim4v6/` `bsim4v7/` | BSIM4 | `b4v7ld.c` | Deep-submicron model with quantum, stress, and RF extensions. |
| `bsimsoi/` | BSIMSOI | `b4soild.c` | SOI variant of BSIM4. |
| `hfet1/` `hfet2/` | HFET | `hfet1load.c` | Heterostructure FET. |
| `vbic/` | VBIC (Q) | `vbicload.c` | Vertical-bipolar inter-company model; advanced BJT. |
| `asrc/` | Arbitrary source (B) | `asrcload.c` | Nonlinear B element with expression parser. |
| `ltra/` `tra/` `txl/` | Transmission line (T/O) | `ltraload.c` | Lossless and lossy W-element transmission lines. |
| `urc/` | Uniform RC line | `urcload.c` | |
| `cpl/` | Coupled lossy line | `cplload.c` | |

---

## 4. `src/maths/` — Numerical Libraries

**Summary:** Pure numerical algorithms with no device or circuit knowledge.
All routines operate on abstract matrices and vectors.

### 4.1 `src/maths/ni/` — Newton–Raphson Engine

**Summary:** The numerical iteration (`NI`) subsystem drives the core SPICE
convergence loop. It owns the outer iteration shell, predictor/corrector, and
convergence checks.

| File | Summary |
|------|---------|
| `niiter.c` | `NIiter()`: main Newton–Raphson loop. Calls `CKTload()`, decomposes and solves the sparse matrix, checks convergence via `NIconv()`, applies damping. Central to every operating-point and transient solve. |
| `nicomcof.c` | `NIcomCof()`: computes companion circuit coefficients (integration method coefficients) for Gear and trapezoidal methods. Called at each accepted time step. |
| `niconv.c` | `NIconv()`: convergence test — compares `CKTrhs` differences against `VNTOL`/`RELTOL`/`ABSTOL`. |
| `nipred.c` | `NIpred()`: predictor step — uses past time-point solutions to extrapolate starting guess for next time point (reduces iterations). |
| `niinteg.c` | `NIintegrate()`: time integration for each state variable using trapezoidal or Gear-2 coefficients. |
| `niaciter.c` | `NIacIter()`: iterative solver for AC linearised system. |
| `niditer.c` | Initialisation / reinitialisation for iteration counter and damping state. |
| `niinit.c` | Allocates the NI state struct; initialises integration history arrays. |
| `nireinit.c` | Reinitialises NI state for a restart (`.ic UIC` or breakpoints). |
| `niniter.c` | Newton iteration with source stepping for tough operating-point convergence. |
| `nipzmeth.c` | Pole-zero iteration method. |

### 4.2 `src/maths/sparse/` — Sparse Matrix Solver

**Summary:** KLU-style sparse LU factorisation used by all analysis modes. The
matrix is built by `CKTsetup()` and factored / back-solved at every Newton iteration.

Key functions: `SMPpreOrder()`, `SMPluFac()`, `SMPsolve()`, `SMPclear()`.

### 4.3 `src/maths/fft/` — FFT Engine

**Summary:** Real/complex FFT for `.four` analysis and the `fft` CP command.
Implements Cooley–Tukey with optional FFTW3 backend.

### 4.4 `src/maths/deriv/` — Numerical Differentiation

**Summary:** Derivative computation for sensitivity analysis (`.sens`).

### 4.5 `src/maths/poly/` — Polynomial Evaluation

**Summary:** Polynomial evaluation for controlled-source B elements and PWL interpolation.

### 4.6 `src/maths/cmaths/` — Complex Number Arithmetic

**Summary:** Complex arithmetic primitives used in AC analysis.

---

## 5. `src/xspice/` — XSPICE Mixed-Signal Extensions

**Summary:** XSPICE adds event-driven digital simulation and mixed analogue/digital
co-simulation. The Code Model (`cm`) subsystem lets users define new C-language
models as plugins.

| Subdirectory | Summary |
|--------------|---------|
| `cm/` | Code Model interface: `CMaccept()`, model parameter passing. |
| `cmpp/` | Code model pre-processor: generates glue C from `.mod` descriptor files. |
| `mif/` | Model Interface Functions: the runtime library that code models call. |
| `evt/` | Event-driven scheduler: propagates digital events between code models. |
| `enh/` | Enhancement layer: breakpoints, source stepping for convergence. |
| `idn/` | Identifier name mangling for code model symbols. |
| `ipc/` | Inter-process communication for external simulator coupling. |
| `icm/analog/` | Built-in analogue code models (integrators, limiters, etc.). |
| `icm/digital/` | Built-in digital code models (gates, flip-flops, etc.). |

---

## 6. `src/include/ngspice/` — Shared Headers

**Summary:** All major data structures are defined here. Understanding these is
essential for navigating the source.

| Header | Defines |
|--------|---------|
| `cktdefs.h` | `CKTcircuit` struct — the master simulation state: node list, device list, MNA matrix pointer, time/voltage tolerance settings, analysis mode flags, state vectors. |
| `devdefs.h` | `DEVpublic` — the device vtable (function pointers for `DEVsetup`, `DEVload`, `DEVtemperature`, `DEVconverge`, `DEVtrunc`, `DEVacLoad`, `DEVnoise`, …). |
| `ifsim.h` | `IFsimulator` — the front-end/back-end interface vtable; `SPfrontEnd` global pointer. |
| `inpdefs.h` | `INPtables`, `card` — parser data structures for the line deck and model table. |
| `smpdefs.h` | `SMPmatrix` — sparse matrix opaque handle and operation declarations. |
| `dvec.h` | `dvec` — data vector (simulation result waveform): name, type, real/imaginary arrays, length, plot linkage. |
| `ftedefs.h` | Frontend global declarations (`cp_err`, `cp_out`, plot list). |
| `trandefs.h` | Transient analysis parameter block (`TRANan` struct). |
| `acdefs.h` | AC analysis parameter block (`ACan` struct). |
| `sperror.h` | Simulator error codes (`E_NOMEM`, `E_SINGULAR`, etc.). |
| `const.h` | Physical constants (`CHARGE`, `CONSTboltz`, `CONSTRefTemp`, etc.). |

---

## 7. `examples/` — Netlist Examples

**Summary:** Ready-to-run input decks demonstrating key features.

| Directory | Contents |
|-----------|----------|
| `examples/various/` | Resistor, RC, OP-amp, diode clamp circuits |
| `examples/TransImpedanceAmp/` | TIA with noise analysis |
| `examples/transient-noise/` | XSPICE transient noise injection |
| `examples/Monte_Carlo/` | Statistical variation sweeps |
| `examples/xspice/` | Mixed analogue/digital XSPICE demos |
| `examples/measure/` | `.measure` post-processing |
| `examples/pss/` | Periodic Steady State |

---

## 8. `tests/` — Regression Suite

**Summary:** Per-device regression circuits. Each subdirectory contains `.cir`
input decks and expected output files for automated testing. Tests cover `bsim1`
through `bsim4`, `bjt`, `jfet`, `mes`, filters, transient, transmission lines,
sensitivity, and pole-zero.

---

## Index: Function → File

| Function | File | Role |
|----------|------|------|
| `inp_readall()` | `frontend/inpcom.c` | Read and preprocess the netlist |
| `INPpas1()` | `spicelib/parser/inppas1.c` | Collect `.model` cards |
| `INPpas2()` | `spicelib/parser/inppas2.c` | Instantiate all elements |
| `CKTsetup()` | `spicelib/analysis/cktsetup.c` | Allocate state; build matrix topology |
| `CKTtemp()` | `spicelib/analysis/ckttemp.c` | Apply temperature derating |
| `NIiter()` | `maths/ni/niiter.c` | Newton–Raphson iteration loop |
| `CKTload()` | `spicelib/analysis/cktload.c` | Stamp all devices into MNA matrix |
| `DEVload` (per device) | `spicelib/devices/*/xxxload.c` | Device-level stamp |
| `NIconv()` | `maths/ni/niconv.c` | Check voltage/current convergence |
| `NIcomCof()` | `maths/ni/nicomcof.c` | Compute integration coefficients |
| `NIpred()` | `maths/ni/nipred.c` | Predictor for next time step |
| `CKTtrunc()` | `spicelib/analysis/ckttrunc.c` | LTE time-step control |
| `OUTbeginPlot()` | `frontend/outitf.c` | Open an output plot / rawfile |
| `OUTdata()` | `frontend/outitf.c` | Append one data point |
| `OUTendPlot()` | `frontend/outitf.c` | Flush and close |
| `raw_write()` | `frontend/rawfile.c` | Serialise plot to `.raw` file |
| `raw_read()` | `frontend/rawfile.c` | Read back a `.raw` file |
