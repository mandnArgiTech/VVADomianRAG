# Task: Generate Dual-Purpose RAG Index (`rag_index.json`) for ngspice — NodalAI Kernel Reimplementation Oracle and Agentic Circuit Design Platform

You are an expert SPICE simulator implementer with deep knowledge of ngspice's numerical kernel, device modeling, sparse matrix solvers, and circuit simulation theory. Scan the ngspice source tree from the root and produce a single `rag_index.json` that serves **two distinct retrieval missions** from the same source corpus:

## The Two Missions

### Mission 1 — Kernel Reimplementation Oracle (NodalAI)
NodalAI is a Python reimplementation of ngspice's numerical kernel. The agent doing the reimplementation needs the index to surface the *exact* numerical algorithms, their invariants, and their canonical call chains. Wrong damping factor, missing limiter, off-by-one in NR convergence test, different timestep control law — these silently break a SPICE reimplementation. The index must make these invariants retrievable as structured data, not as prose to be searched.

**Mission 1 retrieval targets (in priority order):**
1. The complete DC operating point chain: parser → `CKTinit` → `CKTop` → `NIiter` → `CKTload` → `DEVload` (per device) → limiters → sparse matrix solve → convergence test → next NR iter → final converged state
2. Device model contracts (the SPICEdev plugin pattern) and concrete implementations per device family
3. Numerical limiters: `DEVpnjlim`, `DEVfetlim`, `DEVlimvds`, voltage and current limiting, the exact mathematical forms
4. Sparse matrix solver semantics: pivoting strategy, ordering, structural-singularity handling, factor/solve API
5. Numerical integration: trapezoidal, Gear order 2–6, backward Euler, LTE-based timestep control, charge-conserving capacitor stamps
6. Convergence aids: GMIN stepping, source stepping, pseudo-transient, damped Newton, RELTOL/ABSTOL/VNTOL/CHGTOL semantics
7. Per-analysis drivers: `DCop`, `DCtran`, `ACan`, `NOISEan`, `DCtrCurv`, `SENan`, `PZan`, etc.
8. Behavioral sources / expression evaluator
9. Subcircuit expansion mechanics
10. Regression test suite as ground-truth validation

### Mission 2 — Agentic Circuit Design and Validation Platform
A different agent designs circuits, runs simulations, and validates results. It produces netlists, picks component values, interprets waveforms, debugs convergence failures from a circuit-designer perspective. This agent uses the same index but emphasizes interface and behavior over implementation.

**Mission 2 retrieval targets (in priority order):**
1. Netlist syntax: device cards (R, L, C, D, Q, M, V, I, B, E, F, G, H, X, .subckt), `.option`, `.param`, `.control` blocks
2. Analysis directives: `.op`, `.dc`, `.ac`, `.tran`, `.noise`, `.disto`, `.tf`, `.sens`, `.pz`, `.fft` — what each does and what knobs it accepts
3. Device model parameters and their physical meaning (BSIM4 has hundreds; the index should surface them with semantics)
4. Output specifications: `.print`, `.plot`, `.save`, `.measure`, `.raw` file format
5. Common simulation pitfalls: convergence failure causes and fixes, numerical artifacts (ringing on stiff edges, charge non-conservation, LTE blowup), how to read SPICE error/warning messages
6. The `.control` scripting language and `nutmeg`/Spice 3 command syntax
7. Initial conditions: `.ic`, `.nodeset`, behavior across analysis types
8. Standard idioms: parametric sweeps, Monte Carlo, sensitivity, optimization
9. Interfacing patterns: shared library mode (`-pipe`, shared lib, ngspice-as-DLL), `PySpice`/`ngspyce` consumption of `.raw`

These two missions share the same source tree but lean on different parts. The index makes both retrievable simultaneously via explicit `job_relevance` tagging on each file and via separate canonical chains for each mission.

---

## Step 1: Scan & Classify

Walk every directory from the ngspice repo root. For each file, classify into ONE of:

### INCLUDE — `core_logic`

#### Tier 1: Numerical kernel core (highest weight, both missions but especially Mission 1)
- `src/spicelib/analysis/` — analysis drivers and core numerical loops
  - `cktop.c`, `cktopt.c`, `cktdest.c`, `cktinit.c`, `cktload.c`, `cktdltmod.c` — circuit lifecycle and load
  - `niiter.c`, `niinteg.c`, `niconv.c`, `nicomcof.c`, `nidiag.c`, `nipzsy.c` — NR iteration, integration, convergence
  - `dcop.c`, `dctran.c`, `dctrcurv.c`, `acan.c`, `noisean.c`, `pzan.c`, `senan.c`, `tfan.c`, `disto.c`, `sense2.c` — analysis drivers
  - `cktsetup.c`, `cktbreak.c`, `cktaccept.c`, `ckttemp.c`, `cktdelta.c` — circuit timestep / temperature / delta management
- `src/spicelib/devices/` — every device model directory (one per device family)
  - Treat each device subdirectory as a structural unit (e.g., `bsim3/`, `bsim4/`, `bjt/`, `dio/`, `cap/`, `res/`, `ind/`, `vsrc/`, `isrc/`, `mos1/`, `mos2/`, `mos3/`, `mos6/`, `mos9/`, `vbic/`, `hicum2/`, `ekv/`, `hisim2/`, `hisimhv2/`, `urc/`, `tra/`, `txl/`, `ltra/`, `mes/`, `mesa/`, `jfet/`, `jfet2/`, `swit/`, `csw/`, `asrc/`, `ccvs/`, `cccs/`, `vcvs/`, `vccs/`, etc.)
- `src/maths/sparse/` — ngspice's sparse matrix library (or KLU-related code if present in `src/spicelib/sparse/`)
- `src/maths/cmaths/` — complex math routines
- `src/maths/ni/` — numerical integration helpers (if exists)

#### Tier 1: Frontend / parser / command interpreter (highest weight, both missions but especially Mission 2)
- `src/frontend/` — the user-facing command interpreter and netlist front-end
  - `inp.c`, `inpdomod.c`, `inpdot*.c`, `inppas*.c`, `inp2*.c` — netlist parser, dotcmd handlers, device card parsers
  - `subckt.c`, `subckt2.c` — subcircuit expansion
  - `numparam/` — `.param` and parameterized expression handling
  - `parser/` — expression evaluator / lexer
  - `outitf.c`, `out.c`, `outsubs.c` — output/print interface
  - `runcoms.c`, `runcoms2.c` — `.control` block execution and simulation runners
  - `com_*.c` — interactive nutmeg/spice3 commands
  - `breakp.c`, `breakp2.c` — breakpoints
  - `display.c`, `plotting/` — plot interfaces (if textual; skip GTK/MFC backends)
  - `measure/` — `.measure` extraction commands
- `src/sharedspice.c` — the shared library entry point used by PySpice etc.

#### Tier 2: Output and waveform handling (Mission 2-heavy)
- `src/frontend/rawfile.c`, `src/frontend/raw.c` — `.raw` file reader/writer
- `src/include/ngspice/wordlist.h`, `dvec.h`, `plot.h` — vector and plot data structures
- `src/frontend/breakp.c`, `dotcards.c`

#### Tier 2: XSPICE mixed-signal (decide explicitly)
- `src/xspice/` — XSPICE event-driven simulator. **Include if your NodalAI scope covers digital/mixed-signal; mark as Tier 2 if analog-only focus.** Default: include with reduced importance score.

#### Tier 2: KLU integration (if vendored)
- KLU is an external sparse solver ngspice can use. Include if vendored under `src/maths/` or similar; otherwise note as an external option in metadata.

#### Tier 3: Useful but secondary
- `src/misc/` — utilities (string handling, hashing, etc.)
- `src/spicelib/devices/asrc/` and behavioral source code if not already Tier 1
- `src/spicelib/parser/` if it exists (alternate parser path)

### INCLUDE — `support`
- **Headers (`.h`)** for all included `.c` files. Critical headers (annotate with high importance):
  - `src/include/ngspice/ifsim.h` — the `IFsimulator` and front-end interface contract
  - `src/include/ngspice/devdefs.h` — `SPICEdev` device plugin contract (THE key structure for kernel reimplementation)
  - `src/include/ngspice/cktdefs.h` — `CKTcircuit` core data structure
  - `src/include/ngspice/sparse/spdefs.h` (or equivalent) — sparse matrix interface
  - `src/include/ngspice/iferrmsg.h` — error code catalog (E_NOMEM, E_NODECON, E_SINGULAR, etc.)
  - `src/include/ngspice/typedefs.h`, `gendefs.h`
  - Per-device `*defs.h` headers (e.g., `bsim4def.h`)
- **Top-level docs**: `README`, `INSTALL`, `NEWS`, `ChangeLog`, the `manual/` directory if present
- **The regression test suite**: `tests/` directory — `.cir` netlists + reference output files. **CRITICAL for both missions** (Mission 1: ground-truth validation; Mission 2: canonical examples of correct circuits).
- **Examples**: `examples/` — keep representative circuits (1–2 per analysis type, plus all "tutorial" examples). Skip large dump-style example collections.
- **`src/include/ngspice/` other top-level** typedefs and macro definitions

### EXCLUDE
- **Build output**: `obj/`, `bin/`, `lib/` (built artifacts), `*.o`, `*.obj`, `*.a` (compiled archives), `*.so`, `*.dll`, `*.lib`, `Makefile.in` (keep `Makefile.am` only if it documents module structure)
- **Generated code**: `lex.yy.c` from flex, `*.tab.c`/`*.tab.h` from bison if generated (keep `.l`/`.y` sources)
- **Vendored third-party**: `cppdep/`, `tclscripts/` (Tcl GUI), `wbtools/`, `visualc/`, `mingw/` build scripts, vendored fft if duplicate of system fft, any `external/` directory
- **GUI implementations**: GTK/Motif/MFC UI source. Spice has multiple display backends — skip them all except the textual `nutmeg` command interface.
- **Windows-specific**: `winmain.c`, `*.rc`, `*.def`, ngspice-MFC code, MS-specific build files
- **Localization**: language packs (rare in ngspice but may exist)
- **Debian/RPM packaging**: `debian/`, `rpm/`, `*.spec`
- **CI configurations**: `.github/`, `.travis.yml`, `appveyor.yml`
- **IDE/VCS**: `.git/`, `.vscode/`, `.idea/`
- **Binary assets**: `.png`, `.gif`, `.pdf` (PDF documentation can be re-derived from manual sources)
- **Most unit tests** beyond the regression suite — but the regression suite (`tests/`) IS included as support; don't confuse with `*_test.c` files which can be skipped
- **`examples/Monte_Carlo/`** beyond a single representative example
- **Empty/stub files**: < 10 non-comment lines

**When in doubt: exclude.** Target file count: 800–1500. ngspice's value density is high but its directory tree includes a lot of build/packaging/UI noise.

---

## Step 2: Per-File Metadata

For each included file, extract the following.

### Identity & basics
- `path`: repo-relative
- `file_id`: sha1 first 12 chars
- `category`: `"core_logic"` | `"support"`
- `language`: `"c"` | `"header"` | `"flex"` (`.l`) | `"bison"` (`.y`) | `"netlist"` (`.cir`/`.sp`) | `"spice_raw"` (`.raw` reference) | `"makefile"` | `"shell"` | `"markdown"` | `"perl"` | `"tcl"` (only if part of nutmeg-relevant scripting)
- `loc`, `sloc_total`, `size_bytes`, `content_hash` (sha256), `last_modified` (ISO 8601)

### NodalAI / agentic mission relevance fields (NEW — central to this index)
- `job_relevance`: structured object indicating relevance for each mission:
```json
  {
    "kernel_reimplementation": "high" | "medium" | "low" | "none",
    "circuit_design_validation": "high" | "medium" | "low" | "none"
  }
```
  Calibration:
  - `niiter.c` → `{kernel_reimplementation: high, circuit_design_validation: low}` (it's the NR loop; designers don't read it, reimplementers must)
  - `inpdot.c` → `{kernel_reimplementation: medium, circuit_design_validation: high}` (parses dotcommands; reimplementers may stub, designers must understand)
  - `bsim4/b4ld.c` → `{kernel_reimplementation: high, circuit_design_validation: medium}` (BSIM4 load — reimplementers must port; designers care about the model behavior)
  - `tests/bsim4/<some_test>.cir` → `{kernel_reimplementation: high, circuit_design_validation: high}` (canonical test case for both)
  - `winmain.c` (excluded anyway, but illustrative) → `{kernel_reimplementation: none, circuit_design_validation: none}`

- `numerical_invariant_kind`: for kernel files, what numerical invariant this file embodies. Use these IDs:
  - `"newton_raphson_iteration"` — the NR loop
  - `"convergence_test"` — RELTOL/ABSTOL/VNTOL/CHGTOL check
  - `"junction_voltage_limiting"` — DEVpnjlim and similar
  - `"fet_voltage_limiting"` — DEVfetlim, DEVlimvds
  - `"current_limiting"` — DEVlimvds (specific cases)
  - `"trapezoidal_integration"`
  - `"gear_integration_order_2_to_6"`
  - `"backward_euler_integration"`
  - `"lte_timestep_control"`
  - `"breakpoint_handling"`
  - `"sparse_lu_factorization"`
  - `"sparse_partial_pivoting"`
  - `"sparse_ordering_heuristic"`
  - `"matrix_singularity_detection"`
  - `"gmin_stepping"`
  - `"source_stepping"`
  - `"pseudo_transient"`
  - `"damped_newton"`
  - `"charge_conserving_capacitor_stamp"`
  - `"mna_matrix_assembly"`
  - `"ac_small_signal_linearization"`
  - `"noise_analysis_psd_integration"`
  - `"sensitivity_adjoint"`
  - `"pz_pole_zero_eigensystem"`
  - `"distortion_volterra"`
  - `"behavioral_expression_evaluation"`
  - `"subcircuit_flat_expansion"`
  - `"parameter_substitution"`
  - `"raw_file_serialization"`
  - `"netlist_tokenization"`
  - `"netlist_dot_dispatch"`
  - `"output_vector_management"`
  - `"measure_extraction"`
  - `null` — file is not embodying a numerical invariant (e.g., utility, parser dispatch)
  
  Multiple allowed; encode as list.

- `numerical_constants_defined`: structured list of numerical constants defined or used in this file that are part of SPICE invariants:
```json
  [
    {"name": "RELTOL", "default_value": "1e-3", "purpose": "relative tolerance for NR convergence", "source_line": 142},
    {"name": "ABSTOL", "default_value": "1e-12", "purpose": "absolute current tolerance (A)", "source_line": 143},
    {"name": "VNTOL", "default_value": "1e-6", "purpose": "absolute voltage tolerance (V)", "source_line": 144},
    {"name": "CHGTOL", "default_value": "1e-14", "purpose": "absolute charge tolerance (C)", "source_line": 145},
    {"name": "GMIN_DEFAULT", "default_value": "1e-12", "purpose": "minimum conductance added across PN junctions", "source_line": 156}
  ]
```
  **Accurate policy:** list only constants that are **actually defined** in this translation unit—numeric `sckt->CKT… = …` assignments in `cktinit.c`, strict SPICE-token `#define NAME <number>` elsewhere, and for `cktdefs.h` a **curated** list (`CKTDEFS_H_NUMERICAL_METADATA` in `build_rag_index.py`) tying `CKTcircuit` fields to `CKTinit` defaults. Files with none of the above use **`[]`** (netlists, prose, etc.).

- `device_model_kind`: set **only** for paths under `src/spicelib/devices/<dev>/` (compact / CIDER / ADMS family string, e.g. `"mosfet_bsim4"`, `"cider_numerical_1d"`, `"adms_behavioral"`). **All other indexed files use `null`** — do not use a fake `"non_device"` string.

- `spicedev_function_implemented`: for device files, which `SPICEdev` virtual function this file implements (or a documented non-vtable role):
  - Vtable slots: `"DEVparam"`, `"DEVmodParam"` (via `*mpar.c` / model param files), `"DEVload"`, `"DEVacLoad"`, `"DEVpzLoad"`, `"DEVpzSetup"`, `"DEVnoise"`, `"DEVtrunc"`, `"DEVconvTest"`, `"DEVtemperature"`, `"DEVsetic"` (initial conditions from RHS; often `*getic.c`), `"DEVask"`, `"DEVmodAsk"`, `"DEVdelete"`, `"DEVmDelete"`, `"DEVdestroy"`, `"DEVsetup"`, `"DEVunsetup"`, `"DEVsens"`, `"DEVdistortion"`, `"DEVdisto"`, `"DEVfindBranch"`, `"DEVaccept"` (including `*accept.c` except top-level `cktaccept.c`), `"DEVsoaCheck"`, `"DEVsenLoad"`, `"DEVsenUpdate"`, `"DEVsenPrint"`, `"DEVdump"` (CIDER internals), `"DEVbindCSC"` (BSIM-style sparse binding), `"DEVlimit"`, `"DEVconvergence"`, `"DEVmAsk"`
  - Descriptor / glue (not a single slot): `"SPICEdev_aggregate"` (`SPICEdev … = { … }` in `*init.c`), `"IFdevice_parameter_tables"` (`IFparm` instance/model tables only), `"devices_subsystem_glue"` (top-level `devices/*.c` dispatch/registry), `"model_internal_equations"` (`*eval.c`), `"model_geometry_parasitics"` (`*geo.c`), `"model_intrinsic_capacitance"` (`*moscap.c`), `"model_terminal_capacitance"` (e.g. coupled-line cap helpers), `"model_auxiliary_support"` (shared helpers such as `*misc.c`)
  - For **non-device** sources the list is **never empty**: tags such as `off_device_subsystem:<subsystem>`, optional `analysis_role:…`, `circuit_designer_topic:…`, and `compilation_unit:header_declarations` / `artifact:netlist_or_testbench` as applicable (SPICEdev slot N/A, but the field stays populated for uniform indexing)
  
  Multiple allowed if a single file implements multiple functions; encode as list.

- `spice_analysis_role`: set **only** for `src/spicelib/analysis/*.c` files that implement a **specific** analysis driver or its ask/set/dump helpers. Shared circuit/matrix/node glue (`cktload.c`, `cktsetup.c`, `cktdojob.c`, …) uses **`null`**.
  - Values: `"op_dc_operating_point"`, `"dc_sweep"`, `"transient"`, `"ac_small_signal"`, `"noise"`, `"distortion"`, `"transfer_function"`, `"sensitivity"`, `"pole_zero"`, `"periodic_steady_state"` (PSS: `dcpss.c` and helpers), `null`

- `circuit_designer_topic`: user-facing netlist / control / output topic. **`src/frontend/`** files use the short labels below (basename must match). **`src/spicelib/parser/`** files use **per-file** backend topics defined in `PARSER_CIRCUIT_DESIGNER_TOPIC_BY_BASENAME` in `build_rag_index.py` (e.g. `device_instance_line_parser`, `dot_command_line_parser_backend`, `parse_pass_one_dot_model`). **`src/sharedspice.c`**: `"shared_lib_api"`. Everything else: `null`.
  - Frontend examples: `"netlist_grammar_devices"`, `"netlist_grammar_dotcommands"`, `"subcircuit_definition"`, `"parameter_substitution"`, `"control_block_scripting"`, `"plot_command"`, `"measure_command"`, `"option_directive"`, `"convergence_aid_directive"`, `"output_format_raw"`, `"output_format_text"`, `"vector_manipulation"`, …

### Spectrum-style structural fields adapted for ngspice
- `module`: build module / directory grouping (e.g., `"spicelib_analysis"`, `"spicelib_devices_bsim4"`, `"frontend"`, `"sparse"`, `"include"`, `"tests"`, `"examples"`)
- `subsystem`: `"numerical_kernel"` | `"device_model"` | `"sparse_solver"` | `"frontend_parser"` | `"frontend_command"` | `"frontend_output"` | `"frontend_measure"` | `"shared_lib_api"` | `"xspice_event"` | `"raw_file_io"` | `"regression_test"` | `"example_circuit"` | `"documentation"` | `"build"` | `"utility"`
- `header_pair`: for `.c` files, the corresponding `.h` if present (e.g., `bsim4/b4ld.c` ↔ `bsim4/bsim4def.h`)
- `device_family_directory`: for files in `src/spicelib/devices/<dev>/`, the `<dev>` portion (canonical device family ID)
- `c_includes_internal`: list of repo-relative paths from `#include "..."` (skip `#include <...>` for system headers)
- `key_functions_defined`: list of top-level non-static functions with line ranges and signatures (max ~15)

### Semantic description (for embedding enrichment)
- `summary`: 1–3 sentences in ngspice/SPICE terminology. **For numerical kernel files, the summary must explicitly state what numerical operation this performs, what invariants it preserves, and what the input/output state is.** For device files, state the physics modeled, the equation set, and the matrix stamps produced. For frontend files, state what user-facing syntax/command this owns.
  Good (kernel): *"Implements the inner Newton-Raphson iteration for DC operating-point and transient analysis. Per iteration: calls CKTload to assemble the Jacobian and RHS via per-device DEVload calls, applies voltage/current limiters via DEVlimit if configured, performs sparse LU factor + solve, applies damping if iteration count exceeds threshold, evaluates convergence via per-node RELTOL+VNTOL/ABSTOL+CHGTOL test, and returns to caller for next iteration or convergence declaration. Implements GMIN-stepping and source-stepping fallback paths invoked when standard NR fails to converge within ITL1/ITL2 limits."*
  Good (device): *"BSIM4 v4.8 charge-based MOSFET model load function. Computes drain current Ids, transcapacitances Cgg/Cgd/Cgs/Cdd/Cds, and gate-tunneling currents from terminal voltages Vgs/Vds/Vbs and bias-dependent threshold voltage Vth. Stamps the small-signal conductance matrix and current vector into the MNA matrix at the four-terminal node positions, with charge-conserving capacitance stamps applied for transient analysis. Calls DEVfetlim to limit per-iteration voltage step."*
  Good (frontend): *"Parses .tran dot-command syntax: `.tran tstep tstop [tstart [tmax]] [UIC]`. Extracts timestep parameters into the analysis structure consumed by DCtran, validates ordering constraints, applies UIC flag for user-specified initial conditions. Errors emit E_PARMVAL with line context."*
  Bad: *"Handles transient analysis."*

- `purpose`: from extended enum: `"analysis_driver"`, `"nr_loop"`, `"convergence_test"`, `"limiter"`, `"matrix_assembly"`, `"sparse_factor"`, `"sparse_solve"`, `"sparse_ordering"`, `"integration_method"`, `"timestep_control"`, `"gmin_stepping"`, `"source_stepping"`, `"pseudo_transient"`, `"breakpoint_handler"`, `"device_param"`, `"device_load"`, `"device_acload"`, `"device_pzload"`, `"device_temperature"`, `"device_convtest"`, `"device_limiter"`, `"device_noise"`, `"device_trunc"`, `"device_setup"`, `"device_destroy"`, `"netlist_parser"`, `"dotcmd_parser"`, `"subckt_expander"`, `"param_substitution"`, `"expression_evaluator"`, `"command_interpreter"`, `"control_block_runner"`, `"output_vector"`, `"raw_file_io"`, `"plot_command"`, `"print_command"`, `"measure_command"`, `"shared_api"`, `"xspice_event"`, `"data_structure_def"`, `"interface_contract"`, `"error_catalog"`, `"utility"`, `"regression_test"`, `"example_circuit"`, `"documentation"`, `"build"`

- `domain_concepts`: 3–8 SPICE/numerical-method concepts. Use real terminology: `"newton_raphson"`, `"jacobian_matrix"`, `"mna_modified_nodal_analysis"`, `"sparse_lu_factorization"`, `"partial_pivoting"`, `"junction_voltage_limit"`, `"trapezoidal_integration"`, `"gear_method"`, `"local_truncation_error"`, `"gmin_stepping"`, `"source_stepping"`, `"pseudo_transient"`, `"convergence_tolerance"`, `"reltol_abstol_vntol_chgtol"`, `"itl1_itl2_iteration_limits"`, `"charge_conservation"`, `"transcapacitance"`, `"bsim4_charge_based_model"`, `"gummel_poon_bjt"`, `"vbic_high_frequency_bjt"`, `"behavioral_source_b_element"`, `"subcircuit_expansion"`, `"parameter_substitution"`, `"dot_control_block"`, `"raw_file_format"`, `"measure_extraction"`. Not generic terms.

- `tags`: 2–5 categorical tags

### Structural signals
- `key_symbols`: list of top-level public symbols (max ~15) with `name`, `kind` (`"function"`, `"struct"`, `"typedef"`, `"macro"`, `"enum"`, `"global_variable"`, `"function_pointer_table"`), `line_start`, `line_end`, `signature`, `doc` (first paragraph of comment if present)
- `imports_internal`: from `#include "..."` (resolve to repo paths)
- `imports_external`: from `#include <...>` — system headers; tag math-significant ones (`<math.h>`, `<float.h>`, `<complex.h>`)
- `imported_by`: list of repo-relative paths that include this file (computed in pass 2)
- `imported_by_count`
- `call_graph_outgoing`: `[{symbol, target_file, target_symbol, indirect}]` — **always non-empty** in the built index: curated kernel/device edges are merged with `#include` targets (`target_symbol` `(header_include)`), resolved calls to other indexed translation units, netlist pipeline anchors (`inp.c` / `dcop.c`), and if needed a `(file_anchor)` self edge. **For SPICEdev function-pointer dispatch (the `(*DEVload)(...)` pattern), record `indirect: true` and explain in notes that dispatch goes via `DEVices[type]->DEVload`.** This is critical for kernel-reimplementation retrieval — without it, an agent may miss that NIiter calls all device DEVloads.
- `function_pointer_tables_referenced`: for files that interact with `DEVices[]` or similar virtual dispatch tables, list the table name. Helps retrieval reconstruct the dispatch mechanism.

### Chunking hints
- `chunking_strategy`:
  - `"ast_function"` — default for `.c` files (chunk per top-level function)
  - `"by_spicedev_function"` — for device load files: chunk per implemented SPICEdev function (DEVload as one chunk, DEVacload as another, etc.) since these are the natural retrieval units
  - `"semantic_section"` — for headers with logical sections (e.g., `cktdefs.h` has substructures), markdown docs, regression test READMEs
  - `"per_dotcmd"` — for `inpdot*.c` files: chunk per dot-command handler since each is a distinct retrieval target
  - `"per_command"` — for `com_*.c` files: chunk per nutmeg command
  - `"per_test_case"` — for `tests/` directory: each `.cir` file is its own chunk; reference output is a peer chunk
  - `"whole_file"` — small cohesive files (small headers, single-purpose utilities)
  - `"fixed_window"` — fallback only
- `max_chunk_tokens`: 600–1200. **DEVload functions can be very long (BSIM4 DEVload is 2000+ lines); cap at 1200 with aggressive `preserve_together`.**
- `chunk_overlap_tokens`: 80–150
- `preserve_together`: line ranges that MUST NOT split:
  - The body of `NIiter()` — splitting destroys the NR-loop reasoning chain
  - Any individual `DEVload` function body
  - The convergence-test inner block in `NIconv`
  - GMIN-stepping main loop in `dcop.c`
  - Source-stepping main loop
  - Sparse factor/solve top-level loops
  - The `SPICEdev` struct initializer for each device (e.g., `BSIM4info` block) — never split the function-pointer assignment

### Retrieval hints
- `importance_score`: 0.0–1.0. Calibration:
  - 1.0: `niiter.c`, `cktload.c`, `dcop.c`, `dctran.c`, `devdefs.h`, `cktdefs.h`, `ifsim.h`
  - 0.9–0.95: per-analysis drivers, sparse factor/solve, NR convergence, integration methods, limiter implementations, BSIM4 load, BSIM3 load, BJT VBIC load
  - 0.8–0.9: other major device loads (MOS1/2/3, EKV, HiSIM, JFET), behavioral source eval, subcircuit expander
  - 0.7–0.8: DEVparam/DEVtemperature/DEVconvTest implementations, AC/noise/PZ analysis support
  - 0.6–0.7: parser/dotcmd handlers, output vector mgmt, raw file IO, measure extractor
  - 0.5–0.6: shared API, XSPICE, command interpreter
  - 0.4–0.5: regression test cases (high for both missions but lower than kernel core)
  - 0.3–0.4: examples, utilities, less-common device models (3Com-style legacy)
  - 0.2–0.3: docs, build, peripheral utilities

- `query_hints`: 4–7 natural-language queries this file strongly answers, mixing both missions:
  - For `niiter.c`: 
    - `"how does ngspice's Newton-Raphson loop work"`
    - `"what is the convergence test in ngspice"`
    - `"how does NIiter call per-device load functions"`
    - `"what damping is applied to NR iterations in ngspice"`
    - `"how does NIiter fall back to GMIN stepping"`
  - For `bsim4/b4ld.c`:
    - `"how is BSIM4 drain current computed"`
    - `"what charge stamps does BSIM4 produce for transient analysis"`
    - `"how does BSIM4 handle voltage limiting per iteration"`
    - `"what BSIM4 model parameters affect Ids most strongly"`
  - For `inpdot.c`:
    - `"what dot-commands does ngspice support"`
    - `"how is .tran parsed"`
    - `"what is the syntax for .options in ngspice"`
  - For `tests/bsim4/<test>.cir`:
    - `"is there a regression test for BSIM4 transient analysis"`
    - `"what reference circuits validate BSIM4 charge conservation"`

- `related_files`: up to 5 semantically related paths
- `canonical_chain_tags`: list of canonical chain tags this file participates in (defined at repo level — see Step 4)

### Provenance
- `notes`: optional free text. Historical notes ("originally Berkeley SPICE 3F5"), version-specific quirks, known issues with this file's algorithm

---

## Step 3: Logical Grouping

Group by **numerical-kernel cohesion + frontend-cohesion + device-family cohesion**, not by directory. Aim for 25–40 groups.

### Tier 1 RCA-equivalent: Numerical Kernel Core (highest group_importance)
- `nr_iteration_core` — `niiter.c`, `niconv.c`, `nicomcof.c` and the convergence-test inner code
- `circuit_load_dispatch` — `cktload.c`, the `DEVices[]` table, the dispatch from CKTload to per-device DEVload
- `analysis_driver_dc_op` — `dcop.c`, `cktop.c` and the GMIN/source-stepping fallbacks
- `analysis_driver_transient` — `dctran.c`, `cktbreak.c`, `cktaccept.c`, integration setup, breakpoint handling
- `analysis_driver_ac` — `acan.c` and AC stamp routing
- `analysis_driver_noise` — `noisean.c` and noise PSD integration
- `analysis_driver_pz` — `pzan.c` and pole-zero eigenvalue
- `analysis_driver_sens` — `senan.c`, `sense2.c` (sensitivity adjoint)
- `analysis_driver_disto` — `disto.c` (distortion via Volterra)
- `analysis_driver_tf` — `tfan.c` (transfer function)
- `integration_methods` — `niinteg.c` and related (trapezoidal, Gear, BE)
- `timestep_control_lte` — LTE estimation, timestep adjustment
- `convergence_aids_gmin_source_stepping` — GMIN stepping, source stepping, pseudo-transient
- `sparse_matrix_factor_solve` — `src/maths/sparse/` files
- `sparse_matrix_ordering` — sparse ordering heuristics
- `klu_integration` (if present)

### Tier 1: Device Model Core
- `device_dispatch_contract` — `devdefs.h`, `SPICEdev` table, per-device `DEVices[]` registration
- `device_model_diode` — diode files
- `device_model_bjt_gummel_poon` — `bjt/` files
- `device_model_bjt_vbic` — `vbic/` files
- `device_model_bjt_hicum2` — `hicum2/` files
- `device_model_mosfet_levels_1_2_3_6_9` — older MOS levels
- `device_model_mosfet_bsim3` — BSIM3 files
- `device_model_mosfet_bsim4` — BSIM4 files (largest device, dedicated group)
- `device_model_mosfet_bsim6` — BSIM6 (if present)
- `device_model_mosfet_ekv` — EKV files
- `device_model_mosfet_hisim` — HiSIM2, HiSIM-HV2
- `device_model_jfet` — JFET levels 1, 2
- `device_model_mesfet` — Curtice, Statz, HFET
- `device_model_passives` — R, L, C with mutual coupling
- `device_model_sources_independent` — V, I sources
- `device_model_sources_dependent_linear` — VCVS, VCCS, CCVS, CCCS (E, G, H, F)
- `device_model_sources_behavioral` — B-source / asrc with expression evaluation
- `device_model_switches` — voltage-controlled (S), current-controlled (W) switches
- `device_model_transmission_lines` — TRA, LTRA, TXL, URC
- `device_model_xspice` — XSPICE event-driven (if scope includes)

### Tier 1: Frontend / Mission 2 Core
- `netlist_parser_main` — `inp.c` and the main netlist read loop
- `netlist_parser_devices` — `inp2*.c` device-card parsers
- `netlist_parser_dotcmds` — `inpdot*.c`, `dotcards.c`
- `subcircuit_expander` — `subckt.c`, `subckt2.c`
- `parameter_numparam` — `numparam/` directory
- `expression_parser` — frontend expression evaluator
- `command_interpreter_nutmeg` — `com_*.c`, `runcoms*.c`
- `control_block_runner` — `.control` block executor
- `output_vector_management` — `dvec.c`, `plot.c`, output vector lifecycle
- `output_command_print_plot` — `com_print.c`, `com_plot.c`, `com_setplot.c`
- `output_raw_file_io` — `rawfile.c`, `raw.c`
- `output_measure` — `measure/` directory and `com_meas.c`
- `output_dotsave_dotic_dotnodeset` — `.save`, `.ic`, `.nodeset` handlers
- `shared_library_api` — `sharedspice.c` and shared API headers

### Tier 2: Validation and Examples
- `regression_test_suite` — all of `tests/` (top-importance for both missions)
- `example_circuits_per_analysis` — representative examples for each analysis type
- `documentation_manual` — `manual/` and top-level docs

### Tier 3: Supporting
- `data_structure_definitions` — `cktdefs.h`, `ifsim.h`, key typedef headers
- `error_message_catalog` — `iferrmsg.h`
- `utility_misc` — small utilities

Per group:
- `group_id`: snake_case
- `name`: human-readable
- `description`: 1–2 sentences in SPICE/numerical terminology
- `domain_concepts`: 3–6 shared concepts
- `entry_points`: 1–3 most important files
- `files`: list of paths
- `group_importance`: 0.0–1.0
- `cross_group_dependencies`: list of `group_id`s
- `canonical_chain_tags`: list of chain tags this group participates in
- `mission_emphasis`: `"kernel_reimplementation"` | `"circuit_design_validation"` | `"both"`

---

## Step 4: Repo-Level Metadata

Top of `rag_index.json`:

- `repo_name`: `"ngspice"`
- `rag_purpose`: `"Dual-mission: (1) NodalAI kernel reimplementation oracle; (2) Agentic circuit design and validation platform"`
- `generated_at`: ISO 8601
- `index_schema_version`: `"1.0"`
- `index_kind`: `"source_code_dual_mission"`
- `primary_languages`: top languages by LOC (expect: `c`, `header`, plus some `flex`/`bison`/`makefile`)
- `build_systems`: detected (autoconf, cmake if present)
- `frameworks_libraries`: detected (sparse library variant: ngspice-native or KLU; complex math: cmaths or system; flex/bison versions if discoverable)
- `ngspice_version`: extracted from `configure.ac`/`CMakeLists.txt`/`README` if discoverable
- `domain_summary`: 4–6 sentences. Cover: ngspice as Berkeley SPICE 3F5 derivative; modified nodal analysis (MNA) numerical foundation; SPICEdev device-plugin architecture; analysis types (DC op, DC sweep, AC, transient, noise, distortion, sensitivity, PZ, transfer function); per-iteration NR loop with convergence aids (GMIN stepping, source stepping, damped Newton); sparse matrix solver; nutmeg/Spice 3 frontend with `.control` scripting; raw file output for downstream analysis. **Prepended to every chunk as global context.**

### Two missions explicit
```json
"missions": {
  "kernel_reimplementation": {
    "description": "Retrieval target: reimplementing ngspice's numerical kernel in Python (NodalAI). Emphasizes exact algorithms, invariants, and call chains. Wrong damping factor or missing limiter silently breaks correctness.",
    "primary_chains": ["dc_operating_point_chain", "transient_step_chain", "ac_analysis_chain", "device_load_dispatch_chain", "convergence_aid_chain", "sparse_solve_chain"],
    "primary_groups": ["nr_iteration_core", "circuit_load_dispatch", "analysis_driver_dc_op", "analysis_driver_transient", "device_dispatch_contract", "device_model_*", "sparse_matrix_factor_solve", "convergence_aids_gmin_source_stepping", "integration_methods", "timestep_control_lte"]
  },
  "circuit_design_validation": {
    "description": "Retrieval target: agent that designs circuits, runs simulations, interprets results. Emphasizes netlist syntax, analysis directives, output formats, common pitfalls. Less concerned with internal numerical mechanics; more concerned with what the simulator does and how to use it.",
    "primary_chains": ["netlist_to_simulation_chain", "tran_analysis_user_chain", "ac_analysis_user_chain", "convergence_failure_diagnosis_chain", "measure_extraction_chain", "raw_output_consumption_chain"],
    "primary_groups": ["netlist_parser_main", "netlist_parser_dotcmds", "subcircuit_expander", "parameter_numparam", "command_interpreter_nutmeg", "control_block_runner", "output_vector_management", "output_raw_file_io", "output_measure", "regression_test_suite", "example_circuits_per_analysis"]
  }
}
```

### Canonical chains (cross-stage retrieval targets)

```json
"canonical_chains": [
  {
    "chain_id": "dc_operating_point_chain",
    "name": "DC operating-point computation, end-to-end",
    "description": "Full chain from a netlist with no .ic to a converged DC operating point. Parser → CKTinit → CKTop (with optional GMIN stepping fallback) → NIiter → CKTload → per-device DEVload (called via DEVices[type]->DEVload function pointer) → limiters applied via DEVlimit → sparse LU factor → sparse solve → convergence test (per-node RELTOL/ABSTOL/VNTOL/CHGTOL) → next iteration or termination.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["netlist_parse", "circuit_init", "dcop_driver", "nr_iteration", "device_load", "limiter_apply", "matrix_factor", "matrix_solve", "convergence_test", "result_export"],
    "canonical_members": ["src/frontend/inp.c", "src/spicelib/analysis/cktinit.c", "src/spicelib/analysis/cktop.c", "src/spicelib/analysis/dcop.c", "src/spicelib/analysis/niiter.c", "src/spicelib/analysis/cktload.c", "src/maths/sparse/spfactor.c", "src/maths/sparse/spsolve.c", "src/spicelib/analysis/niconv.c"],
    "representative_query": "walk me through how ngspice computes a DC operating point from a netlist",
    "common_failure_modes": [
      "Convergence failure: NR doesn't reach RELTOL within ITL1 iterations → triggers GMIN stepping fallback in CKTop",
      "Singular matrix: structural zero pivot during sparse factor → returns E_SINGULAR; usually missing DC path to ground",
      "Limiter oscillation: junction voltage oscillates between iterations, prevents convergence; limiter dampens but may not always succeed",
      "Bias-dependent device parameters not yet temperature-resolved: requires DEVtemperature pass before NR loop"
    ],
    "importance": 1.0
  },
  {
    "chain_id": "transient_step_chain",
    "name": "One transient timestep, including LTE-based step control",
    "description": "Full chain for a single transient timestep: predictor (extrapolation) → DEVload with charge-conserving stamps → NR iteration to convergence → corrector → LTE estimation per device via DEVtrunc → timestep adjustment (accept/reject/grow/shrink) → next step or back to retry with smaller step.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["predictor", "device_load_with_charge", "nr_iteration", "lte_estimation", "step_accept_or_reject"],
    "canonical_members": ["src/spicelib/analysis/dctran.c", "src/spicelib/analysis/niiter.c", "src/spicelib/analysis/niinteg.c", "src/spicelib/analysis/cktaccept.c", "src/spicelib/analysis/ckttrunc.c"],
    "representative_query": "how does ngspice control transient timestep size",
    "common_failure_modes": [
      "LTE blowup: stiff dynamics produce LTE > tolerance, repeatedly shrinking step until min step reached",
      "Charge non-conservation: device load doesn't produce conservative capacitance stamps; integrator accumulates error",
      "Integrator order switching: Gear order switching at breakpoints can cause transients"
    ],
    "importance": 1.0
  },
  {
    "chain_id": "ac_analysis_chain",
    "name": "AC small-signal analysis from operating point",
    "description": "Compute DC operating point first (via dc_operating_point_chain), then linearize each device around it via DEVacLoad, assemble complex-valued admittance matrix, solve for each frequency point.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["dc_op_first", "linearization", "complex_matrix_assembly", "complex_solve_per_frequency"],
    "canonical_members": ["src/spicelib/analysis/acan.c", "src/spicelib/analysis/cktload.c"],
    "representative_query": "how does AC analysis linearize the circuit",
    "common_failure_modes": [
      "DC op not converged → AC results meaningless; AC driver should refuse to proceed",
      "Frequency sweep too coarse near resonance → missed peaks"
    ],
    "importance": 0.95
  },
  {
    "chain_id": "device_load_dispatch_chain",
    "name": "Per-iteration device-load dispatch via SPICEdev table",
    "description": "How CKTload iterates over all devices in the circuit and dispatches to DEVload via the SPICEdev function-pointer table indexed by device type. Critical structural pattern for any reimplementation.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["cktload_dispatch", "devices_table_lookup", "devload_call", "matrix_stamp"],
    "canonical_members": ["src/spicelib/analysis/cktload.c", "src/include/ngspice/devdefs.h", "src/spicelib/devices/<each>/DEVload"],
    "representative_query": "how does ngspice call each device's load function",
    "importance": 0.99
  },
  {
    "chain_id": "convergence_aid_chain",
    "name": "Convergence-aid fallback ladder",
    "description": "When standard NR fails: GMIN stepping (lift GMIN, converge, lower GMIN, repeat) → source stepping (linearly ramp sources from 0 to nominal) → pseudo-transient → if all fail, return E_NOCONV.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["standard_nr", "gmin_step", "source_step", "pseudo_transient", "abort"],
    "canonical_members": ["src/spicelib/analysis/dcop.c", "src/spicelib/analysis/cktop.c", "src/spicelib/analysis/niiter.c"],
    "representative_query": "what does ngspice do when DC analysis doesn't converge",
    "importance": 0.95
  },
  {
    "chain_id": "sparse_solve_chain",
    "name": "Sparse LU factor and solve",
    "description": "Per-iteration: sparse matrix is reordered (one-time at setup), partial-pivoted LU factored, then forward/back-substituted to solve Ax=b.",
    "mission": "kernel_reimplementation",
    "stages_traversed": ["build_or_clear", "factor", "solve"],
    "canonical_members": ["src/maths/sparse/spbuild.c", "src/maths/sparse/spfactor.c", "src/maths/sparse/spsolve.c"],
    "representative_query": "how does ngspice's sparse solver work",
    "importance": 0.95
  },
  {
    "chain_id": "netlist_to_simulation_chain",
    "name": "Netlist-to-simulation, user perspective",
    "description": "User submits netlist → parser tokenizes → device cards become device instances → dotcards become analysis requests → subcircuits expand → parameters substitute → CKTinit constructs the circuit → analysis driver runs.",
    "mission": "circuit_design_validation",
    "stages_traversed": ["tokenize", "dispatch_devices_dotcmds", "subckt_expand", "param_substitute", "ckt_init", "analysis_run"],
    "canonical_members": ["src/frontend/inp.c", "src/frontend/inpdomod.c", "src/frontend/inpdot.c", "src/frontend/subckt.c", "src/frontend/numparam/", "src/spicelib/analysis/cktinit.c"],
    "representative_query": "what happens when I run ngspice on my netlist",
    "importance": 0.95
  },
  {
    "chain_id": "convergence_failure_diagnosis_chain",
    "name": "Convergence failure diagnosis from a circuit-designer perspective",
    "description": "When ngspice reports 'Timestep too small' or 'No convergence': what error codes correspond to which failure modes, what .options can a user set to help (ITL1, ITL2, ITL4, GMIN, RELTOL, ABSTOL, VNTOL), what netlist patterns are common causes (no DC path to ground, unreasonably high gain near operating point, switch with infinite slope).",
    "mission": "circuit_design_validation",
    "stages_traversed": ["error_message_emit", "error_code_lookup", "user_remediation_options"],
    "canonical_members": ["src/include/ngspice/iferrmsg.h", "src/spicelib/analysis/dcop.c", "src/spicelib/analysis/dctran.c", "src/frontend/runcoms.c"],
    "representative_query": "my circuit doesn't converge; what should I try",
    "importance": 0.95
  },
  {
    "chain_id": "measure_extraction_chain",
    "name": "Extracting metrics from simulation results via .measure",
    "description": "After a transient or AC sim, .measure statements extract trigger-based timings, find/when crossings, integrals, peaks. The measure subsystem reads the result vector and applies extraction predicates.",
    "mission": "circuit_design_validation",
    "stages_traversed": ["sim_complete", "measure_parse", "vector_walk", "predicate_eval", "result_emit"],
    "canonical_members": ["src/frontend/measure/", "src/frontend/com_meas.c"],
    "representative_query": "how do I extract rise time and propagation delay with .measure",
    "importance": 0.85
  },
  {
    "chain_id": "raw_output_consumption_chain",
    "name": "Raw file output and external consumption (PySpice et al.)",
    "description": ".raw file format spec, what fields are written per analysis type, how PySpice/ngspyce consume it, the binary vs ASCII format choice.",
    "mission": "circuit_design_validation",
    "stages_traversed": ["sim_complete", "raw_serialize", "external_parse"],
    "canonical_members": ["src/frontend/rawfile.c", "src/frontend/raw.c"],
    "representative_query": "what is the format of ngspice's .raw output",
    "importance": 0.85
  }
]
```

(Add more chains discovered during scan — distortion analysis, sensitivity adjoint, behavioral source eval, subcircuit expansion mechanics, shared library API surface for embedded use cases, etc.)

### Glossary
30–60 entries covering both missions:

**Numerical kernel terms**: `Modified Nodal Analysis (MNA)`, `Newton-Raphson iteration`, `Jacobian`, `Sparse LU factorization`, `Partial pivoting`, `RELTOL`, `ABSTOL`, `VNTOL`, `CHGTOL`, `ITL1`, `ITL2`, `ITL4`, `GMIN`, `GMIN stepping`, `Source stepping`, `Pseudo-transient`, `Trapezoidal integration`, `Gear method`, `Local truncation error (LTE)`, `Charge conservation`, `Transcapacitance`, `Voltage limiter (DEVpnjlim)`, `FET limiter (DEVfetlim)`, `Damped Newton`, `Convergence test`, `Singular matrix`, `Operating point`

**Device modeling terms**: `SPICEdev contract`, `DEVload`, `DEVacLoad`, `DEVtrunc`, `DEVconvTest`, `DEVlimit`, `DEVtemperature`, `DEVparam`, `BSIM3`, `BSIM4`, `Gummel-Poon BJT`, `VBIC BJT`, `MOS Level 1/2/3`, `EKV MOSFET`, `HiSIM`, `Behavioral source (B-element)`, `Voltage-controlled source (E, G)`, `Current-controlled source (F, H)`, `URC (uniform RC)`, `LTRA (lossy transmission line)`

**Frontend / circuit design terms**: `Netlist`, `Device card`, `Dot-command`, `.tran`, `.dc`, `.ac`, `.op`, `.noise`, `.measure`, `.options`, `.subckt / .ends`, `.param`, `.control block`, `Subcircuit expansion`, `Parameter substitution`, `Initial conditions (.ic)`, `Nodeset (.nodeset)`, `nutmeg`, `Spice 3 syntax`, `Raw file (.raw)`, `Vector`, `Plot`, `Save (.save)`, `B-element expression`

**Mission-bridging terms**: `NodalAI`, `Kernel reimplementation`, `PySpice`, `Shared library mode`, `Regression test`, `Reference output`

### Stats
- `total_files_scanned`, `files_included`, `files_excluded`
- `core_logic_count`, `support_count`
- `total_loc_indexed`
- `breakdown_by_language`
- `breakdown_by_subsystem`
- `breakdown_by_device_family_directory`: `{bsim4: N, bsim3: N, bjt: N, ...}`
- `breakdown_by_numerical_invariant_kind`
- `breakdown_by_spicedev_function_implemented`
- `breakdown_by_mission_relevance`: 4-cell matrix counting `{kernel_high_design_high, kernel_high_design_low, kernel_low_design_high, kernel_low_design_low}`
- `total_devices_indexed`: distinct device families
- `total_analysis_drivers`
- `total_canonical_chains`
- `total_regression_tests`

---

## Step 5: Output Format

Single artifact: `rag_index.json` at the repo root. Follow the structure outlined above with the standard top-level + `missions` + `canonical_chains` + `glossary` + `stats` + `groups` + `files` arrays.

```json
{
  "repo_name": "ngspice",
  "rag_purpose": "Dual-mission: (1) NodalAI kernel reimplementation oracle; (2) Agentic circuit design and validation platform",
  "generated_at": "2026-05-05T...",
  "index_schema_version": "1.0",
  "index_kind": "source_code_dual_mission",
  "primary_languages": ["c", "header"],
  "build_systems": ["autoconf", "cmake"],
  "frameworks_libraries": [
    {"name": "ngspice-native sparse", "role": "default sparse solver (src/maths/sparse)"},
    {"name": "KLU", "role": "optional faster sparse solver", "vendored": false}
  ],
  "ngspice_version": "<extracted>",
  "domain_summary": "...",
  "missions": { ... },
  "canonical_chains": [ ... ],
  "glossary": [ ... ],
  "stats": { ... },
  "groups": [ ... ],
  "files": [
    {
      "path": "src/spicelib/analysis/niiter.c",
      "file_id": "...",
      "category": "core_logic",
      "language": "c",
      "loc": 412,
      "sloc_total": 580,
      "size_bytes": 18540,
      "content_hash": "sha256:...",
      "last_modified": "2026-04-...",
      "job_relevance": {"kernel_reimplementation": "high", "circuit_design_validation": "low"},
      "numerical_invariant_kind": ["newton_raphson_iteration", "convergence_test"],
      "numerical_constants_defined": [],
      "device_model_kind": null,
      "spicedev_function_implemented": null,
      "spice_analysis_role": null,
      "circuit_designer_topic": null,
      "module": "spicelib_analysis",
      "subsystem": "numerical_kernel",
      "header_pair": null,
      "device_family_directory": null,
      "c_includes_internal": ["src/include/ngspice/cktdefs.h", "src/include/ngspice/devdefs.h"],
      "key_functions_defined": [
        {"name": "NIiter", "kind": "function", "line_start": 56, "line_end": 332, "signature": "int NIiter(CKTcircuit *ckt, int maxIter)", "doc": "Top-level Newton-Raphson iteration..."},
        {"name": "NIacIter", "kind": "function", "line_start": 340, "line_end": 412, "signature": "int NIacIter(CKTcircuit *ckt)", "doc": "AC iteration..."}
      ],
      "summary": "Top-level Newton-Raphson iteration for DC and transient analysis...",
      "purpose": "nr_loop",
      "domain_concepts": ["newton_raphson", "convergence_test", "reltol_abstol_vntol_chgtol", "damped_newton", "gmin_stepping"],
      "tags": ["kernel", "core", "convergence"],
      "key_symbols": [...],
      "imports_internal": ["src/include/ngspice/cktdefs.h", ...],
      "imports_external": ["<math.h>"],
      "imported_by": ["src/spicelib/analysis/dcop.c", "src/spicelib/analysis/dctran.c", "src/spicelib/analysis/acan.c"],
      "imported_by_count": 5,
      "call_graph_outgoing": [
        {"symbol": "NIiter", "target_file": "src/spicelib/analysis/cktload.c", "target_symbol": "CKTload", "indirect": false},
        {"symbol": "NIiter", "target_file": "src/maths/sparse/spfactor.c", "target_symbol": "spFactor", "indirect": false},
        {"symbol": "NIiter", "target_file": "src/spicelib/devices/<various>", "target_symbol": "DEVload", "indirect": true}
      ],
      "function_pointer_tables_referenced": ["DEVices[]"],
      "chunking_strategy": "ast_function",
      "max_chunk_tokens": 1000,
      "chunk_overlap_tokens": 100,
      "preserve_together": [[56, 332]],
      "importance_score": 1.0,
      "query_hints": [
        "how does ngspice's Newton-Raphson loop work",
        "what is the convergence test in ngspice",
        "how does NIiter call per-device load functions",
        "what damping is applied to NR iterations in ngspice",
        "how does NIiter trigger GMIN stepping fallback",
        "in NodalAI, what's the equivalent of NIiter"
      ],
      "related_files": [
        "src/spicelib/analysis/cktload.c",
        "src/spicelib/analysis/niconv.c",
        "src/spicelib/analysis/dcop.c",
        "src/include/ngspice/cktdefs.h"
      ],
      "canonical_chain_tags": ["dc_operating_point_chain", "transient_step_chain", "ac_analysis_chain", "device_load_dispatch_chain", "convergence_aid_chain"],
      "notes": null
    }
  ]
}
```

---

## Rules

1. **Do not invent.** Every function, struct, device family, analysis driver, dot-command, numerical constant, error code must trace to actual content in the source.
2. **Summaries for kernel files must state numerical operation, invariants preserved, and input/output state.** Generic "handles NR iteration" summaries are failures.
3. **`job_relevance` must be calibrated honestly.** Don't tag every file as `high` for both missions. Most files are `high` for one and `low/none` for the other; that asymmetry is the whole point.
4. **`numerical_invariant_kind` is the most critical field for Mission 1.** Be thorough. A single file may embody multiple invariants (NIiter embodies both NR iteration AND convergence test).
5. **`numerical_constants_defined` extracts SPICE-meaningful constants only.** Default tolerances, default GMIN, default ITL — not arbitrary code constants.
6. **`spicedev_function_implemented` is the contract index.** For every device file, extract which `SPICEdev` virtual functions are implemented. This lets retrieval surface "all DEVload implementations across all devices" as a single query result.
7. **Indirect dispatch in `call_graph_outgoing` must be marked `indirect: true`.** The `DEVices[]` table dispatch is the most important indirect call in ngspice; without proper marking, NodalAI agents will miss it.
8. **Regression tests are first-class for both missions.** Score them at 0.4–0.5 importance — high enough to surface, not so high they outrank kernel core. Include `.cir` source AND reference output files.
9. **`canonical_chains` must include `mission` field** so retrieval can filter by mission.
10. **Chunking BSIM4 DEVload (and other large device load functions) requires `preserve_together` for the entire function body.** These are 1000–3000 line functions but they are atomic units of physics — splitting destroys correctness.
11. **For files in `tests/`**: each `.cir` file is a separate chunk; reference output (`.raw` / `.txt`) is its peer chunk. Group as a unit via `related_files`.
12. **Output valid JSON.** No markdown, no commentary inside the file.
13. Print a progress log to stdout (per-subsystem, per-device-family). Final artifact: `rag_index.json` only.

## Execution Plan (Two Passes)

**Pass 1**: Walk the tree. For each included file, extract per-file metadata except `imported_by`/`imported_by_count` and chain `canonical_members` backfill. Per-file extract: `job_relevance`, `numerical_invariant_kind`, `numerical_constants_defined`, `device_model_kind`, `spicedev_function_implemented`, `spice_analysis_role`, `circuit_designer_topic`, all standard fields, `call_graph_outgoing` (with `indirect` flag).

**Pass 2**: Compute `imported_by` and `imported_by_count` across the file set. Backfill `canonical_chains.canonical_members` with actual indexed paths. Validate every `canonical_chain_tags` resolves. Compute all stats including the mission-relevance matrix. Write final JSON.

Begin pass 1 now. Process in this order:
1. Numerical kernel core (`src/spicelib/analysis/`)
2. Sparse solver (`src/maths/sparse/` or wherever it lives)
3. Device contracts and BSIM4 (the highest-value device, biggest reimplementation target)
4. Other device families (BSIM3, BJT, MOS levels, EKV, JFET, etc.)
5. Frontend (`src/frontend/`)
6. Shared API (`sharedspice.c`)
7. XSPICE (if scope)
8. Tests and examples
9. Headers and remaining